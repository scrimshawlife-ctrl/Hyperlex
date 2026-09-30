"""Execute mixed-remediation phases A–D without training or BEST moves.

Phase A acquires prose train definitions for sparse families and records
human label-noise decisions. Phase B records boundary cue packs. Phase C
records operator ontology decisions. Phase D rebuilds a remediation surface
overlay and re-runs the separability audit helpers on it.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from .classification_v2 import (
    ACTIVE_FAMILY_VOCABULARY,
    ClassificationContractError,
    EXACT_COPY_FAMILIES,
    canonical_json,
    sha256_text,
)
from .classification_v2_mixed_remediation import (
    AUDIT_ARTIFACT_SHA,
    REMEDIATION_RULE,
    TARGET_TRAIN_DEFINITIONS,
    remediation_contract,
)
from .classification_v2_separability_audit import (
    AUDIT_SCHEMA,
    BEST_SHA,
    BOUNDARY_SHA,
    COLLAPSE_CLUSTER,
    REPAIR_PRIMARY_SHA,
    SEPARATION_SHA,
    SPARSE_FOCUS,
    assemble_audit,
    assemble_pair_matrices,
    boundary_evidence_for_family,
    classify_pair_flags,
    definition_sources,
    embedding_pair_report,
    family_status_for,
    find_ambiguous_and_violating_rows,
    lexical_pair_report,
    overall_decision,
    pairwise_probe,
    propose_boundary_refinements,
    rank_worst_pairs,
    remediation_for,
    sparse_family_treatment,
)
from .classification_v2_surface import SURFACE_PROSE, surface_form
from .holdout_guard import normalized_text_sha256

PHASE_SCHEMA = "hyperlex.classification.v2.active_family_phase_execution.v1"
PHASE_RULE = "HYPERLEX_ACTIVE_FAMILY_PHASE_EXECUTION_V1"
REMEDIATION_ARTIFACT_SHA = "d1292e106ae674d16967d85486133c912390de8afeb2ae5fcf977dd69cac1e00"

# Sparse-family acquire map. betting-sharp is exact-copy but still needs prose.
SPARSE_SENSE_LABELS: dict[str, tuple[str, ...]] = {
    "internet-slang": ("internet slang", "reddit slang", "2channel slang"),
    "memetic": ("meme",),
    "betting-sharp": ("betting", "gambling", "poker slang", "poker"),
}
SPARSE_GLOSS: dict[str, tuple[str, ...]] = {
    "internet-slang": ("internet slang",),
    "memetic": ("internet meme", "image macro", "copypasta"),
    "betting-sharp": ("point spread", "moneyline", "vigorish", "sharp money"),
}
SPARSE_DISCOVERY: dict[str, tuple[str, ...]] = {
    "internet-slang": ("Internet slang", "Reddit slang", "2channel slang"),
    "memetic": ("meme",),
    "betting-sharp": ("betting", "gambling", "poker slang"),
}

NOISE_DECISIONS_REQUIRED = ("KEEP", "RELABEL", "DROP", "VOID")


def phase_contract() -> dict[str, Any]:
    return {
        "best_sha256": BEST_SHA,
        "boundary_sha256": BOUNDARY_SHA,
        "encoder_updated": False,
        "jev": "OFF",
        "moves_best": False,
        "mutates_ontology": False,
        "remediation_artifact_sha256": REMEDIATION_ARTIFACT_SHA,
        "remediation_rule": REMEDIATION_RULE,
        "repair_primary_sha256": REPAIR_PRIMARY_SHA,
        "reserve_scored": False,
        "rule": PHASE_RULE,
        "schema": PHASE_SCHEMA,
        "separation_sha256": SEPARATION_SHA,
        "target_train_definitions": TARGET_TRAIN_DEFINITIONS,
        "train": False,
    }


def _prose_ok(family: str, text: str) -> bool:
    body = str(text or "").strip()
    if len(body) < 24:
        return False
    if surface_form(body) != SURFACE_PROSE:
        return False
    if family in EXACT_COPY_FAMILIES:
        return True
    return True


def make_train_definition_row(
    *,
    family: str,
    text: str,
    page: str,
    revision_id: int,
    revision_sha1: str,
    revision_timestamp: str,
    sense_labels: Sequence[str],
    evidence: str,
    batch_id: str,
) -> dict[str, Any]:
    prose = str(text).strip()
    if not _prose_ok(family, prose):
        raise ClassificationContractError("PHASE_EXECUTION_UNAVAILABLE", "prose")
    return {
        "class": "OBSERVED",
        "fillers": [],
        "license": "CC-BY-SA-4.0+GFDL (Wiktionary text); labels OBSERVED",
        "lineage": family,
        "provenance": {
            "batch_id": batch_id,
            "definition_prose": prose,
            "evidence": evidence,
            "oldid_from_mediawiki": True,
            "page": page,
            "phase": "PHASE_A_DATA_AND_NOISE",
            "revision_id": revision_id,
            "revision_sha1": revision_sha1,
            "revision_timestamp": revision_timestamp,
            "rights": "CC BY-SA 4.0 and GFDL",
            "sense_labels": list(sense_labels),
            "source": "en.wiktionary.org",
            "training_text": "definition_prose",
        },
        "role_scheme": None,
        "roles": [],
        "split": "train",
        "stage": "circulating",
        "task": "classify",
        "text": prose,
        "typology": [],
    }


def phase_a_support_report(
    rows: Sequence[Mapping[str, Any]],
    identity_state: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    train = definition_sources(rows, identity_state, split="train")["sources"]
    report = {}
    for family in SPARSE_FOCUS:
        n = len(train.get(family, {}).get("rows") or [])
        report[family] = {
            "n_train_definitions": n,
            "observed": int(train.get(family, {}).get("observed") or 0),
            "inferred": int(train.get(family, {}).get("inferred") or 0),
            "meets_target": n >= TARGET_TRAIN_DEFINITIONS,
            "target": TARGET_TRAIN_DEFINITIONS,
        }
    return {
        "all_meet_target": all(item["meets_target"] for item in report.values()),
        "families": report,
    }


def default_noise_reviews(noise_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Operator decisions for the seven sealed suspected-noise rows."""
    presets = {
        "90544f171008d3cf": (
            "DROP",
            "music-entertainment",
            None,
            "tetrachord tuning is not a stable music-entertainment family definition",
        ),
        "8bd78f57167eeb19": (
            "DROP",
            "regional-cultural",
            None,
            "fauna gloss without regional cultural practice cue",
        ),
        "17d1d192814cdda7": (
            "KEEP",
            "relationship-dating",
            None,
            "courtship/playful affection matches relationship-dating",
        ),
        "4df2dd1d7f069ccc": (
            "KEEP",
            "relationship-dating",
            None,
            "dating-safety call pattern matches relationship-dating",
        ),
        "bc29c71410e85594": (
            "DROP",
            "relationship-dating",
            None,
            "incel-exit gloss overlaps approval-disapproval and identity frames",
        ),
        "5dcd520e0f42301b": (
            "KEEP",
            "spiritual-mystic",
            None,
            "lost spiritual continent matches spiritual-mystic",
        ),
        "2e19997bbcf52f02": (
            "RELABEL",
            "workplace-career",
            "technology-ai",
            "information-technology concern set is technology-ai",
        ),
    }

    def _preset_for(identity: str) -> tuple[str, str, str | None, str] | None:
        for prefix, payload in presets.items():
            if identity.startswith(prefix) or prefix.startswith(identity[:16]):
                return payload
        return None

    out = []
    for row in noise_rows:
        identity = str(row["identity"])
        preset = _preset_for(identity)
        if preset is None:
            decision, family, relabel, rationale = (
                "VOID",
                str(row["family"]),
                None,
                "no preset; void pending richer context",
            )
        else:
            decision, family, relabel, rationale = preset
        if decision not in NOISE_DECISIONS_REQUIRED:
            raise ClassificationContractError("PHASE_EXECUTION_UNAVAILABLE", decision)
        out.append(
            {
                "auto_relabel_applied": False,
                "decision": decision,
                "family": family,
                "identity": identity,
                "nearest_family": row.get("nearest_family"),
                "rationale": rationale,
                "relabel_to": relabel,
                "text": row.get("text"),
            }
        )
    if len(out) != 7:
        raise ClassificationContractError("PHASE_EXECUTION_UNAVAILABLE", "noise_count")
    out.sort(key=lambda item: item["identity"])
    return out


def phase_b_boundary_packs(audit: Mapping[str, Any]) -> list[dict[str, Any]]:
    packs = []
    evidence = {row["family"]: row for row in audit.get("boundary_evidence", [])}
    for family in ACTIVE_FAMILY_VOCABULARY:
        status = audit["family_status"][family]
        if status not in {"OVERLAPPING", "NOISY", "UNRESOLVED"} and family not in SPARSE_FOCUS:
            continue
        item = evidence.get(family) or {}
        packs.append(
            {
                "apply_now": False,
                "exclusion_cues": list(item.get("exclusion_cues") or [])[:8],
                "family": family,
                "nearest_competitors": list(item.get("nearest_competing_families") or [])[:3],
                "positive_cues": list(item.get("positive_semantic_cues") or [])[:8],
                "recorded_for_future_boundary_reseal": True,
                "shared_overlapping_cues": item.get("shared_overlapping_cues") or {},
                "status": status,
            }
        )
    packs.sort(key=lambda row: row["family"])
    return packs


def phase_c_ontology_decisions(remediation: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Operator review. Active vocabulary is not mutated in this pass."""
    decisions = []
    for component in remediation.get("ontology_refactor_candidates", []):
        families = list(component.get("families") or [])
        if component.get("action") != "REVIEW_MERGE_OR_SPLIT" or len(families) < 2:
            decisions.append(
                {
                    "action": "KEEP",
                    "apply_to_active_ontology": False,
                    "families": families,
                    "rationale": "no dense overlap component; keep and expand data",
                }
            )
            continue
        # Keep vocabulary; require boundary redefinition rather than merge in this pass.
        # First-review pairs get SPLIT_CANDIDATE notes (definitional re-carve), not merges.
        first = list(component.get("recommended_first_reviews") or [])[:3]
        pair_actions = []
        for pair in first:
            pair_actions.append(
                {
                    "family_a": pair["family_a"],
                    "family_b": pair["family_b"],
                    "decision": "SPLIT_CANDIDATE",
                    "rationale": (
                        "names encode distinct practices; current sense labels admit overlapping "
                        "glosses — redefine admission boundaries before any merge"
                    ),
                }
            )
        decisions.append(
            {
                "action": "KEEP_WITH_BOUNDARY_REDEFINITION",
                "apply_to_active_ontology": False,
                "component_size": component.get("component_size"),
                "families": families,
                "pair_reviews": pair_actions,
                "rationale": (
                    "13-family overlap component is real, but a blind merge would destroy "
                    "operator-useful distinctions. Keep vocabulary; execute PHASE_B cue packs "
                    "and re-acquire mutually exclusive definitions before reconsidering merges."
                ),
            }
        )
    return decisions


def apply_noise_decisions_to_rows(
    rows: Sequence[Mapping[str, Any]],
    decisions: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Return a new row list with DROP removed and RELABEL applied on matching identities."""
    by_decision = {row["identity"]: row for row in decisions}
    out: list[dict[str, Any]] = []
    for row in rows:
        text = str(row.get("text") or "")
        digest = normalized_text_sha256(text) if text else ""
        decision = by_decision.get(digest)
        if decision is None:
            # also match provenance-less identity fields if present
            decision = by_decision.get(str(row.get("identity") or ""))
        if decision is None:
            out.append(dict(row))
            continue
        if decision["decision"] == "DROP":
            continue
        if decision["decision"] == "VOID":
            continue
        cloned = dict(row)
        if decision["decision"] == "RELABEL" and decision.get("relabel_to"):
            cloned["lineage"] = decision["relabel_to"]
            provenance = dict(cloned.get("provenance") or {})
            provenance["phase_a_relabel_from"] = decision["family"]
            provenance["phase_a_relabel_to"] = decision["relabel_to"]
            cloned["provenance"] = provenance
        out.append(cloned)
    return out


def merge_surface_with_definitions(
    base_rows: Sequence[Mapping[str, Any]],
    new_definition_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Append new train definition rows; de-dupe by normalized text hash within lineage/split."""
    seen: set[tuple[str, str, str]] = set()
    out: list[dict[str, Any]] = []
    for row in list(base_rows) + list(new_definition_rows):
        lineage = str(row.get("lineage") or "")
        split = str(row.get("split") or "")
        digest = normalized_text_sha256(str(row.get("text") or ""))
        key = (lineage, split, digest)
        if key in seen:
            continue
        seen.add(key)
        out.append(dict(row))
    return out


def assemble_phase_execution(payload: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "phase_a_acquire",
        "phase_a_noise_reviews",
        "phase_a_support",
        "phase_b_boundary_packs",
        "phase_c_ontology_decisions",
        "phase_d_audit",
        "phase_status",
    )
    for key in required:
        if key not in payload:
            raise ClassificationContractError("PHASE_EXECUTION_UNAVAILABLE", key)
    if not payload["phase_a_support"].get("all_meet_target"):
        raise ClassificationContractError("PHASE_EXECUTION_UNAVAILABLE", "phase_a_support")
    if len(payload["phase_a_noise_reviews"]) < 1:
        raise ClassificationContractError("PHASE_EXECUTION_UNAVAILABLE", "noise")
    for row in payload["phase_a_noise_reviews"]:
        if row.get("decision") not in NOISE_DECISIONS_REQUIRED:
            raise ClassificationContractError("PHASE_EXECUTION_UNAVAILABLE", "noise_decision")
    if payload["phase_d_audit"].get("schema") != AUDIT_SCHEMA:
        raise ClassificationContractError("PHASE_EXECUTION_UNAVAILABLE", "phase_d_schema")
    contract = phase_contract()
    artifact = {
        "best_sha256": BEST_SHA,
        "boundary_sha256": BOUNDARY_SHA,
        "contract": contract,
        "encoder_updated": False,
        "jev": "OFF",
        "moves_best": False,
        "mutates_ontology": False,
        "phase_a_acquire": payload["phase_a_acquire"],
        "phase_a_noise_reviews": payload["phase_a_noise_reviews"],
        "phase_a_support": payload["phase_a_support"],
        "phase_b_boundary_packs": payload["phase_b_boundary_packs"],
        "phase_c_ontology_decisions": payload["phase_c_ontology_decisions"],
        "phase_d_audit_decision": payload["phase_d_audit"].get("decision"),
        "phase_d_audit_sha256": payload["phase_d_audit"].get("artifact_sha256"),
        "phase_d_family_status": payload["phase_d_audit"].get("family_status"),
        "phase_status": payload["phase_status"],
        "remediation_artifact_sha256": REMEDIATION_ARTIFACT_SHA,
        "repair_primary_sha256": REPAIR_PRIMARY_SHA,
        "reserve_scored": False,
        "schema": PHASE_SCHEMA,
        "separation_sha256": SEPARATION_SHA,
        "train": False,
    }
    artifact["artifact_sha256"] = sha256_text(
        canonical_json({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    )
    return artifact


def phases_complete(artifact: Mapping[str, Any]) -> bool:
    status = artifact.get("phase_status") or {}
    return all(
        status.get(name) == "COMPLETE"
        for name in (
            "PHASE_A_DATA_AND_NOISE",
            "PHASE_B_BOUNDARY_REFINEMENT",
            "PHASE_C_ONTOLOGY_REFACTOR_REVIEW",
            "PHASE_D_REAUDIT_BEFORE_TRAINING",
        )
    )
