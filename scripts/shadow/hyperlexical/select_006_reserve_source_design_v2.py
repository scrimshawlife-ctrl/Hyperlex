"""SELECT-006 reserve source design v2.

This module preregisters a recipe. It does not fetch, settle, relabel,
train, or bind a ledger.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from .eval_routing import PROCEDURE_ID
from .eval_settlement import ACTIVE_FAMILIES
from .layout import FAMILIES
from .select_006_efficiency_preservation import EPSILON, EXPERIMENT_ID
from .select_006_reserve_acquisition import (
    COMPUTABLE_HEAD_FAMILIES,
    execution_loader_status,
    forbidden_training,
)

TRANSITION = "SELECT_006_RESERVE_SOURCE_DESIGN_V2"
STATE = "SOURCE_DESIGN_V2_SEALED"
SCHEMA = "hyperlex.select_006_reserve_source_design_v2.v1"
NEXT_TRANSITION = "SELECT_006_RESERVE_ACQUISITION_V2"
CLEARED_RIGHTS = "CC-BY-SA"
NO_HEAD_MAPPED_TARGET_FAMILIES = "NO_HEAD_MAPPED_TARGET_FAMILIES"
SOURCE_RIGHTS_UNRESOLVED = "SOURCE_RIGHTS_UNRESOLVED"
SOURCE_PROVENANCE_UNRESOLVED = "SOURCE_PROVENANCE_UNRESOLVED"
OBSERVED_RULE_UNDERSPECIFIED = "OBSERVED_RULE_UNDERSPECIFIED"
SOURCE_DESIGN_NOT_CAPABLE_OF_CLASSIFICATION = "SOURCE_DESIGN_NOT_CAPABLE_OF_CLASSIFICATION"
SPEC_SEAL_FAILURE = "SPEC_SEAL_FAILURE"
PROVENANCE_FIELDS = (
    "normalized_hash",
    "normalized_text",
    "revision_id",
    "revision_sha1",
    "revision_timestamp",
    "rights",
    "source_url",
)
SUPPORTING_ARTIFACTS = (
    "HEAD_MAPPING_WITNESS.json",
    "SOURCE_RIGHTS_PROVENANCE_POLICY.json",
    "FUTURE_ACQUISITION_CONTRACT.json",
    "ARTIFACT_MANIFEST.json",
    "SPEC_RECEIPT.json",
)
SOURCE_FAMILY = "wiktionary_labeled_sense"
SPENT_BATCH = "HLX-EVAL-RESERVE-SELECT-006-001"
SPENT_RECIPES = (
    "wiktionary_sense_gloss",
    "wiktionary_multiword_lemma",
    "wiktionary_category",
    "wikipedia_prose",
)
REFUSED_ALIASES = (
    "brainrot-aura",
    "kinship-address",
    "political-status",
    "workplace-corp",
)
HEAD_OUTPUTS = tuple(name for name in FAMILIES if name != "none")
TARGET_FAMILIES = tuple(name for name in HEAD_OUTPUTS if name in ACTIVE_FAMILIES)
LEGACY_HEADS = tuple(name for name in HEAD_OUTPUTS if name not in ACTIVE_FAMILIES)
# Whole sense-label arguments only. A nearby topic is not a name.
DIRECT_LABELS: dict[str, tuple[str, ...]] = {
    "ai-native": ("artificial intelligence",),
    "betting-sharp": ("betting", "gambling"),
    "crypto-degen": ("cryptocurrency",),
    "gaming-meta": ("gaming", "video game", "video games"),
}
NEAR_MISS_LABELS = (
    "ai",
    "bitcoin",
    "computing",
    "crypto",
    "cryptography",
    "esports",
    "finance",
    "internet",
    "machine learning",
    "poker",
    "slang",
    "sports",
)
DISCOVERY_PER_FAMILY = 8
ACQUISITION_FLOORS = {
    "classify": 1,
    "classify_non_none": 1,
    "classify_observed": 1,
    "head_mapped_non_none": 1,
}
SPENT_SURFACE = {
    "batch_id": SPENT_BATCH,
    "decisions": {"ACCEPT": 0, "NONE": 22, "RECLASSIFY": 0, "UNRESOLVED": 10},
    "failure": "RESERVE_METRIC_SURFACE_INSUFFICIENT",
    "failure_sha256": "51d968d5975bfc09f87954f49958c073291d75334f50837c7708535becc20523",
    "head_mapped_non_none": 0,
    "observed": 0,
    "redraw_authorized": False,
    "relabel_authorized": False,
    "reuse_authorized": False,
    "review_rows": 32,
    "review_sha256": "5f31940a73b741bfb8192c88f958e806b3abab194c36ef7153a7b41e8aaa29bc",
    "routed_slices": {
        "classify": 0,
        "classify_non_none": 0,
        "classify_observed": 0,
        "unbind_clean": 22,
    },
}
REVIEW_BANNED = (
    "attest",
    "decision",
    "desired_family",
    "head_mapping",
    "model_score",
    "prediction",
    "quota",
    "routing_status",
    "semantic_family",
    "slice",
    "slices",
    "unbind_clean",
)
_SENSE_LABEL = re.compile(
    r"\{\{\s*(lb|lbl|tlb)\s*\|\s*en\s*\|([^{}]*)\}\}",
    re.IGNORECASE,
)
_LINK = re.compile(r"\[\[([^|\]]+\|)?([^\]]+)\]\]")
_MARKUP = re.compile(r"''+")
_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_label(text: str) -> str:
    """Casefold a whole label argument. Hyphens and spaces are the same."""
    collapsed = text.casefold().replace("-", " ")
    return re.sub(r"\s+", " ", collapsed).strip()


def sense_label_arguments(definition_line: str) -> list[str]:
    """Verbatim English sense-label arguments on one definition line.

    Category links, topic templates, and labels on other lines are ignored.
    The return value is source text. It is not a family assignment.
    """
    if not definition_line.startswith("# ") or definition_line.startswith(("#:", "##")):
        return []
    found: list[str] = []
    for match in _SENSE_LABEL.finditer(definition_line):
        for part in match.group(2).split("|"):
            argument = part.strip()
            if argument:
                found.append(argument)
    return found


def named_target_family(label_arguments: Sequence[str]) -> str | None:
    """The one target family a label list names, or None when it does not.

    Zero matches and two different target families are both None.
    Calling this does not settle a row.
    """
    named: list[str] = []
    for argument in label_arguments:
        token = normalize_label(argument)
        for family, labels in DIRECT_LABELS.items():
            if token in labels and family not in named:
                named.append(family)
    if len(named) != 1:
        return None
    return named[0]


def definition_prose(definition_line: str) -> str:
    """Definition prose with templates removed. Prose is not a family."""
    text = definition_line[2:] if definition_line.startswith("# ") else definition_line
    previous = None
    while text != previous:
        previous = text
        text = _TEMPLATE.sub(" ", text)
    text = _LINK.sub(lambda match: match.group(2), text)
    text = _MARKUP.sub("", text)
    return re.sub(r"\s+", " ", text).strip(" .")


def _family() -> dict[str, Any]:
    return {
        "active_family_mapping_rule": (
            "A settled semantic_family counts toward this batch only when "
            "named_target_family of that definition's own sense-label "
            "arguments returns that family. Other ACTIVE_FAMILIES names "
            "remain legal taxonomy and do not satisfy head_mapped_non_none. "
            "Legacy head names are not families and are not aliased."
        ),
        "discovery": {
            "bound_per_target_family": DISCOVERY_PER_FAMILY,
            "method": (
                "English Wiktionary definition lines whose own {{lb}}, "
                "{{lbl}}, or {{tlb}} arguments equal a preregistered direct "
                "label. Category member lists are not the discovery method."
            ),
            "order": "mediawiki_search_order_within_each_direct_label",
            "redirects": "skip",
            "senses_per_headword": 1,
        },
        "failure_rule": (
            "The future batch fails closed when any acquisition floor is "
            "unmet after settlement. Codes remain RESERVE_SOURCE_FAILURE, "
            "RESERVE_RIGHTS_FAILURE, RESERVE_PROVENANCE_FAILURE, "
            "RESERVE_ISOLATION_FAILURE, RESERVE_METRIC_SURFACE_INSUFFICIENT, "
            "REVIEW_SURFACE_EMPTY, SETTLEMENT_FAILURE, ROUTING_FAILURE, "
            "RESERVE_QUOTA_UNFILLED, LEDGER_BINDING_CONFLICT, and "
            "LEDGER_REPLAY_FAILURE. Review results are not a reason to widen "
            "the label lexicon or to redraw the batch."
        ),
        "family_id": SOURCE_FAMILY,
        "fetch_authorized": False,
        "firecrawl": {
            "may_assign_eligibility": False,
            "may_assign_family": False,
            "may_assign_head_mapping": False,
            "may_assign_inferred": False,
            "may_assign_observed": False,
            "may_assign_routing": False,
            "role": "discovery_or_extraction_only",
        },
        "head_mapping_eligibility_rule": (
            "head_mapped_non_none is true only for a classify row whose "
            "settled family is in the frozen target-family list. That list "
            "is the layout head vocabulary excluding none, intersected with "
            "ACTIVE_FAMILIES. The head vocabulary is not changed here."
        ),
        "incidental_unbind_clean": (
            "A dedicated Family-B harvest is not part of this recipe. An "
            "otherwise eligible classification identity may carry "
            "soft_ceiling.clean_surface when that derivation keeps the row. "
            "Identities from the spent surface stay unavailable."
        ),
        "observed_rule": (
            "OBSERVED only when the sense label on that exact definition "
            "line directly names one frozen target family. The definition "
            "prose is shown and does not by itself establish a family. "
            "INFERRED is not promoted. Category membership, page-level topic "
            "tags, search snippets, source_hint, and a label that merely "
            "neighbors the domain do not establish OBSERVED."
        ),
        "provenance_mechanism": (
            "MediaWiki action=query with prop=revisions and "
            "rvprop=ids|timestamp|sha1|content. revision_id, revision_sha1, "
            "and revision_timestamp must come from that response. A generated "
            "oldid is not provenance."
        ),
        "provenance_required": [
            "normalized_hash",
            "normalized_text",
            "revision_id",
            "revision_sha1",
            "revision_timestamp",
            "rights",
            "source_url",
        ],
        "refused_aliases": list(REFUSED_ALIASES),
        "refused_evidence": [
            "category_membership",
            "definition_prose_without_a_direct_sense_label",
            "generated_oldid",
            "operator_interpretation",
            "page_level_topic_tags",
            "search_snippets",
            "source_hint",
        ],
        "rights": CLEARED_RIGHTS,
        "rights_basis": (
            "The definition line is English Wiktionary entry text and stays "
            "CC-BY-SA. The future acquisition must register this source "
            "family as CC-BY-SA before settlement. This pass does not edit "
            "the settlement rights table."
        ),
        "role": "missing_classification_surfaces",
        "routing_procedure_id": PROCEDURE_ID,
        "slices": [
            "classify",
            "classify_observed",
            "classify_non_none",
            "head_mapped_non_none",
        ],
        "wordnet_admitted": False,
    }


def _evaluated_sources() -> list[dict[str, Any]]:
    return [
        {
            "admitted": True,
            "family_id": SOURCE_FAMILY,
            "reason": (
                "A sense label attached to the exact definition is source "
                "text that can name a head-mapped domain, with MediaWiki "
                "revision provenance and CC-BY-SA rights."
            ),
        },
        {
            "admitted": False,
            "family_id": "wiktionary_sense_gloss",
            "reason": (
                "Acquisition-001 stripped sense labels and reviewed generic "
                "gloss prose. That recipe produced no OBSERVED row."
            ),
        },
        {
            "admitted": False,
            "family_id": "wiktionary_multiword_lemma",
            "reason": (
                "Family B already produced unbind_clean rows. Those "
                "identities are spent, and another unbind-only harvest is "
                "not the missing surface."
            ),
        },
        {
            "admitted": False,
            "family_id": "wikipedia_prose",
            "reason": "Generic prose without a sense-bound domain designation.",
        },
        {
            "admitted": False,
            "family_id": "wikidata_lexeme",
            "reason": (
                "A separate structured domain claim is not the definition "
                "text. Rights may be CC0, which is not the admitted basis "
                "for this recipe."
            ),
        },
        {
            "admitted": False,
            "family_id": "wordnet",
            "reason": "Princeton WordNet is not CC-BY-SA and is not admitted.",
        },
        {
            "admitted": False,
            "family_id": "gcide_freedict",
            "reason": "Rights are not pinned to CC-BY or CC-BY-SA.",
        },
        {
            "admitted": False,
            "family_id": "omegawiki",
            "reason": "Rights and revision provenance are not pinned.",
        },
    ]


def source_design() -> dict[str, Any]:
    """Frozen design. Calling it does not read the network."""
    design = {
        "acquisition_floors": dict(ACQUISITION_FLOORS),
        "direct_labels": {key: list(DIRECT_LABELS[key]) for key in TARGET_FAMILIES},
        "epsilon_unchanged": EPSILON,
        "evaluated_sources": _evaluated_sources(),
        "eventual_reserve_still_requires": [
            "classification_accuracy",
            "classify_macro_f1_nonnone",
            "observed_label_accuracy",
            "unbind_clean_exact",
        ],
        "exclusion_fences": [
            "prior_select_reserves",
            "reserve_acquisition_001_identities",
            "select_001_002_bindings",
            "select_005_eval_reserve",
            "settled_or_spent_evaluation_surfaces",
            "threshold_calibration_and_measurement",
            "training_identities",
        ],
        "experiment_id": EXPERIMENT_ID,
        "family": _family(),
        "fetch_authorized": False,
        "heads_unchanged": True,
        "legacy_heads_not_targets": list(LEGACY_HEADS),
        "loader_unchanged": True,
        "near_miss_labels_not_evidence": list(NEAR_MISS_LABELS),
        "network_in_this_module": False,
        "next_legal_transition": NEXT_TRANSITION,
        "schedules_unchanged": True,
        "schema": SCHEMA,
        "spent_recipes_not_repeated": list(SPENT_RECIPES),
        "spent_surface": dict(SPENT_SURFACE),
        "state": STATE,
        "target_families": list(TARGET_FAMILIES),
        "thresholds_unchanged": True,
        "training_launch_authorized": False,
        "transition": TRANSITION,
        "unbind_clean_acquisition_authorized": False,
        **forbidden_training(),
    }
    _validate(design)
    return design


def _validate(design: Mapping[str, Any]) -> None:
    if set(TARGET_FAMILIES) != set(COMPUTABLE_HEAD_FAMILIES):
        raise SystemExit("REFUSE: target families drifted from the computable head list")
    if set(LEGACY_HEADS) != set(REFUSED_ALIASES):
        raise SystemExit("REFUSE: legacy heads drifted from the refused aliases")
    if "none" in TARGET_FAMILIES or any(name in TARGET_FAMILIES for name in LEGACY_HEADS):
        raise SystemExit("REFUSE: a non-scoring head is in the target list")
    if design["epsilon_unchanged"] != 0 or EPSILON != 0:
        raise SystemExit("REFUSE: EPSILON moved")
    if design["fetch_authorized"] or design["family"]["fetch_authorized"]:
        raise SystemExit("REFUSE: this authorization does not fetch")
    if design["training_launch_authorized"] or design["training_started"]:
        raise SystemExit("REFUSE: training is not authorized")
    if design["unbind_clean_acquisition_authorized"]:
        raise SystemExit("REFUSE: unbind-only acquisition is not this recipe")
    family = design["family"]
    if family["family_id"] in SPENT_RECIPES:
        raise SystemExit("REFUSE: spent recipe is not the new source family")
    if family["rights"] != CLEARED_RIGHTS or family["wordnet_admitted"]:
        raise SystemExit("REFUSE: rights are not CC-BY-SA")
    if family["routing_procedure_id"] != PROCEDURE_ID:
        raise SystemExit("REFUSE: routing contract changed")
    if set(family["slices"]) != set(ACQUISITION_FLOORS):
        raise SystemExit("REFUSE: source slices are not the missing surfaces")
    if "unbind_clean" in family["slices"]:
        raise SystemExit("REFUSE: this source must not target unbind_clean")
    if set(design["direct_labels"]) != set(TARGET_FAMILIES):
        raise SystemExit("REFUSE: label lexicon does not match the target families")
    for family_name, labels in design["direct_labels"].items():
        if family_name not in TARGET_FAMILIES or not labels:
            raise SystemExit("REFUSE: label lexicon names a non-target family")
        for label in labels:
            if normalize_label(label) != label or label in NEAR_MISS_LABELS:
                raise SystemExit("REFUSE: label lexicon is not normalized direct text")
    for label in NEAR_MISS_LABELS:
        if named_target_family([label]) is not None:
            raise SystemExit("REFUSE: a near-miss label names a target family")
    spent = design["spent_surface"]
    if spent["redraw_authorized"] or spent["relabel_authorized"] or spent["reuse_authorized"]:
        raise SystemExit("REFUSE: acquisition-001 stays spent")
    if spent["decisions"]["ACCEPT"] != 0 or spent["observed"] != 0:
        raise SystemExit("REFUSE: the spent surface had no OBSERVED accept")
    if spent["routed_slices"]["unbind_clean"] != 22:
        raise SystemExit("REFUSE: spent unbind rows must stay spent")
    if design["execution_loader_status"] != "NOT_YET_IMPLEMENTED":
        raise SystemExit("REFUSE: loader status changed")
    admitted = [row for row in design["evaluated_sources"] if row["admitted"]]
    if [row["family_id"] for row in admitted] != [SOURCE_FAMILY]:
        raise SystemExit("REFUSE: admitted sources are not the labeled-sense family")
    firecrawl = family["firecrawl"]
    if any(bool(firecrawl[key]) for key in firecrawl if key.startswith("may_")):
        raise SystemExit("REFUSE: Firecrawl must not assign labels")


def review_surface_row(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Blind row. Sense labels stay verbatim and do not become a family."""
    return {
        "candidate_id": raw["candidate_id"],
        "exact_definition_prose": raw.get("exact_definition_prose"),
        "headword": raw["headword"],
        "page_url": raw["page_url"],
        "part_of_speech": raw.get("part_of_speech"),
        "revision_id": raw["revision_id"],
        "sense_label_arguments": list(raw.get("sense_label_arguments") or []),
        "source_family": SOURCE_FAMILY,
        "source_lemma_tokens": list(raw.get("source_lemma_tokens") or []),
    }


def blind_surface_errors(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    errors = []
    for row in rows:
        found = set(REVIEW_BANNED) & set(row)
        if found:
            errors.append("review surface carries " + ",".join(sorted(found)))
    return errors


def design_receipt(
    *,
    repository_commit: str | None = None,
    module_sha256: str | None = None,
) -> dict[str, Any]:
    body = source_design()
    body["network_requests"] = 0
    body["rows_fetched"] = 0
    if repository_commit is not None:
        body["repository_commit"] = repository_commit
    if module_sha256 is not None:
        body["module_sha256"] = module_sha256
    record = dict(body)
    record["record_sha256"] = sha256_text(canonical_json(body))
    return record


def freeze_design(path: str, **receipt_pins: str) -> dict[str, Any]:
    """Write the receipt. Does not create a harvest."""
    receipt = design_receipt(**receipt_pins)
    target = Path(path)
    if target.exists():
        raise SystemExit(f"REFUSE: design receipt already exists: {target}")
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(target.parent, 0o700)
    target.write_text(canonical_json(receipt), encoding="utf-8")
    os.chmod(target, 0o600)
    return receipt


def _seal_fail(code: str, detail: str) -> None:
    raise SystemExit(f"{code}: {detail}")


def design_record_matches(design: Mapping[str, Any]) -> bool:
    """True when record_sha256 covers every field except itself."""
    record = design.get("record_sha256")
    if not isinstance(record, str) or len(record) != 64:
        return False
    body = {key: value for key, value in design.items() if key != "record_sha256"}
    return sha256_text(canonical_json(body)) == record


def require_sealable(design: Mapping[str, Any]) -> None:
    """Fail closed before any companion artifact is written."""
    if not design_record_matches(design):
        _seal_fail(SPEC_SEAL_FAILURE, "source design record")
    targets = list(design.get("target_families") or [])
    if not targets or targets != list(TARGET_FAMILIES):
        _seal_fail(NO_HEAD_MAPPED_TARGET_FAMILIES, "target family list")
    family = design.get("family") or {}
    if family.get("rights") != CLEARED_RIGHTS or not str(family.get("rights_basis") or "").strip():
        _seal_fail(SOURCE_RIGHTS_UNRESOLVED, "rights basis")
    required = list(family.get("provenance_required") or [])
    if not str(family.get("provenance_mechanism") or "").strip() or required != list(PROVENANCE_FIELDS):
        _seal_fail(SOURCE_PROVENANCE_UNRESOLVED, "provenance")
    observed = str(family.get("observed_rule") or "")
    if "OBSERVED" not in observed or "sense label" not in observed or "INFERRED is not promoted" not in observed:
        _seal_fail(OBSERVED_RULE_UNDERSPECIFIED, "observed rule")
    slices = set(family.get("slices") or [])
    if not set(ACQUISITION_FLOORS) <= slices:
        _seal_fail(SOURCE_DESIGN_NOT_CAPABLE_OF_CLASSIFICATION, "slices")
    for name in TARGET_FAMILIES:
        labels = list((design.get("direct_labels") or {}).get(name) or [])
        if not labels or named_target_family([labels[0]]) != name:
            _seal_fail(SOURCE_DESIGN_NOT_CAPABLE_OF_CLASSIFICATION, name)
    if design.get("epsilon_unchanged") != 0 or design.get("fetch_authorized"):
        _seal_fail(SPEC_SEAL_FAILURE, "epsilon or fetch")
    if design.get("execution_loader_status") != "NOT_YET_IMPLEMENTED":
        _seal_fail(SPEC_SEAL_FAILURE, "loader")


def head_mapping_witness(design: Mapping[str, Any]) -> dict[str, Any]:
    require_sealable(design)
    return {
        "active_families_on_head": list(TARGET_FAMILIES),
        "derivation": (
            "layout.FAMILIES excluding none, intersected with "
            "eval_settlement.ACTIVE_FAMILIES, in head order"
        ),
        "experiment_id": EXPERIMENT_ID,
        "head_index": {name: FAMILIES.index(name) for name in TARGET_FAMILIES},
        "head_mapping_eligibility_rule": design["family"]["head_mapping_eligibility_rule"],
        "head_outputs": list(HEAD_OUTPUTS),
        "heads_unchanged": True,
        "legacy_heads_not_targets": list(LEGACY_HEADS),
        "schema": "hyperlex.select_006_head_mapping_witness.v1",
        "source_design_record_sha256": design["record_sha256"],
        "target_families": list(design["target_families"]),
    }


def rights_provenance_policy(design: Mapping[str, Any]) -> dict[str, Any]:
    require_sealable(design)
    family = design["family"]
    return {
        "direct_evidence_requirement": family["observed_rule"],
        "evaluated_sources": design["evaluated_sources"],
        "experiment_id": EXPERIMENT_ID,
        "family_id": family["family_id"],
        "firecrawl": family["firecrawl"],
        "generated_oldid_trusted": False,
        "provenance_mechanism": family["provenance_mechanism"],
        "provenance_required": list(family["provenance_required"]),
        "refused_evidence": list(family["refused_evidence"]),
        "rights": family["rights"],
        "rights_basis": family["rights_basis"],
        "schema": "hyperlex.select_006_source_rights_provenance_policy.v1",
        "source_design_record_sha256": design["record_sha256"],
        "wordnet_admitted": False,
    }


def future_acquisition_contract(design: Mapping[str, Any]) -> dict[str, Any]:
    require_sealable(design)
    family = design["family"]
    return {
        "acquisition_floors": dict(design["acquisition_floors"]),
        "direct_labels": design["direct_labels"],
        "eventual_reserve_still_requires": list(design["eventual_reserve_still_requires"]),
        "exclusion_fences": list(design["exclusion_fences"]),
        "executes_in_this_pass": False,
        "experiment_id": EXPERIMENT_ID,
        "failure_rule": family["failure_rule"],
        "fetch_authorized": False,
        "incidental_unbind_clean": family["incidental_unbind_clean"],
        "near_miss_labels_not_evidence": list(design["near_miss_labels_not_evidence"]),
        "next_legal_transition": NEXT_TRANSITION,
        "routing_procedure_id": family["routing_procedure_id"],
        "schema": "hyperlex.select_006_future_acquisition_contract.v1",
        "source_design_record_sha256": design["record_sha256"],
        "source_family": family["family_id"],
        "spent_surface": design["spent_surface"],
        "training_launch_authorized": False,
        "unbind_clean_acquisition_authorized": False,
        **forbidden_training(),
    }


def compile_supporting_artifacts(
    design: Mapping[str, Any],
    *,
    design_file_sha256: str,
    repository_commit: str,
) -> dict[str, dict[str, Any]]:
    """Witness, policy, contract, manifest, and receipt. Does not fetch."""
    require_sealable(design)
    if len(design_file_sha256) != 64 or len(repository_commit) != 40:
        _seal_fail(SPEC_SEAL_FAILURE, "design file or commit pin")
    bodies = {
        "HEAD_MAPPING_WITNESS.json": head_mapping_witness(design),
        "SOURCE_RIGHTS_PROVENANCE_POLICY.json": rights_provenance_policy(design),
        "FUTURE_ACQUISITION_CONTRACT.json": future_acquisition_contract(design),
    }
    hashes = {name: sha256_text(canonical_json(body)) for name, body in bodies.items()}
    hashes["SOURCE_DESIGN_V2.json"] = design_file_sha256
    manifest = {
        "artifacts": [{"name": name, "sha256": hashes[name]} for name in sorted(hashes)],
        "experiment_id": EXPERIMENT_ID,
        "schema": "hyperlex.select_006_source_design_v2_manifest.v1",
        "source_design_record_sha256": design["record_sha256"],
        **forbidden_training(),
    }
    hashes["ARTIFACT_MANIFEST.json"] = sha256_text(canonical_json(manifest))
    receipt = {
        "artifact_sha256": hashes,
        "experiment_id": EXPERIMENT_ID,
        "network_requests": 0,
        "next_legal_transition": NEXT_TRANSITION,
        "repository_commit": repository_commit,
        "rows_fetched": 0,
        "schema": "hyperlex.select_006_source_design_v2_receipt.v1",
        "source_design_record_sha256": design["record_sha256"],
        "state": STATE,
        "transition": TRANSITION,
        **forbidden_training(),
    }
    bodies["ARTIFACT_MANIFEST.json"] = manifest
    bodies["SPEC_RECEIPT.json"] = receipt
    return bodies


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_supporting_artifacts(
    directory: str,
    design: Mapping[str, Any],
    *,
    design_file: str,
    repository_commit: str,
) -> dict[str, str]:
    """Write companion artifacts. Refuses to rewrite the source design."""
    root = Path(directory)
    design_path = Path(design_file)
    before = design_path.read_bytes()
    bodies = compile_supporting_artifacts(
        design,
        design_file_sha256=sha256_file(design_path),
        repository_commit=repository_commit,
    )
    if design_path.name in bodies:
        _seal_fail(SPEC_SEAL_FAILURE, "companion seal must not rewrite the source design")
    for name in bodies:
        if (root / name).exists():
            _seal_fail(SPEC_SEAL_FAILURE, f"{name} already exists")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    temporary = root / ".supporting.tmp"
    if temporary.exists():
        _seal_fail(SPEC_SEAL_FAILURE, "temporary artifact directory already exists")
    temporary.mkdir(mode=0o700)
    try:
        for name, body in bodies.items():
            path = temporary / name
            path.write_text(canonical_json(body), encoding="utf-8")
            os.chmod(path, 0o600)
        manifest = json.loads((temporary / "ARTIFACT_MANIFEST.json").read_text(encoding="utf-8"))
        for item in manifest["artifacts"]:
            if item["name"] == design_path.name:
                observed = sha256_file(design_path)
            else:
                observed = sha256_file(temporary / item["name"])
            if observed != item["sha256"]:
                _seal_fail(SPEC_SEAL_FAILURE, item["name"])
        for name, body in bodies.items():
            os.replace(temporary / name, root / name)
            os.chmod(root / name, 0o600)
        temporary.rmdir()
    except BaseException:
        if temporary.exists():
            for child in temporary.iterdir():
                child.unlink()
            temporary.rmdir()
        raise
    if design_path.read_bytes() != before:
        _seal_fail(SPEC_SEAL_FAILURE, "source design bytes changed")
    return {name: sha256_file(root / name) for name in bodies}
