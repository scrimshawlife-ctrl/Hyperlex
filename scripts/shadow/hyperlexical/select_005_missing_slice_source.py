"""Preregister SELECT-005 sources for the three empty slices.

This module does not fetch, harvest, relabel, settle, or train.
The 928-row surface from snapshot 20260929T012947Z stays spent.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

from .eval_settlement import ACTIVE_FAMILIES
from .select_005_reserve import EXPERIMENT_ID, canonical_json, sha256_text

TRANSITION = "SELECT_005_MISSING_SLICE_SOURCE_DESIGN_AUTHORIZATION"
STATE = "MISSING_SLICE_SOURCE_DESIGN_PREREGISTERED"
SCHEMA = "hyperlex.select_005_missing_slice_source_design.v1"
CLEARED_RIGHTS = "CC-BY-SA"
MISSING_SLICES = ("classify_observed", "classify_non_none", "unbind_clean")
SPENT_RECIPE = ("wiktionary_category", "wikipedia_prose")
REFUSED_ALIASES = (
    "brainrot-aura",
    "kinship-address",
    "political-status",
    "workplace-corp",
)
SPENT_SURFACE = {
    "decisions": {"ACCEPT": 0, "NONE": 40, "RECLASSIFY": 0, "UNRESOLVED": 888},
    "redraw_authorized": False,
    "relabel_authorized": False,
    "review_rows": 928,
    "routable_rows": 40,
    "routed_slices": {
        "classify": 40,
        "classify_non_none": 0,
        "classify_observed": 0,
        "unbind_clean": 0,
    },
    "settlement_events_sha256": "f02414000395225e793984bbe92d8262c9861c8a8c7d03932baa54f9d2bc3678",
    "settlement_receipt_sha256": "bd46a84a0ce6885382dac637e6f11fcd11a70fd41f1696050a0288cac063808b",
    "snapshot_id": "20260929T012947Z",
}
PINNED_EXPORT_ROWS = 9150
PINNED_EXPORT_SHA256 = "64b7d3dede25047cb6dd2e5b663f7fa72946ec82ac1a8816ae34622d1aaac430"
OBSERVED_BAR = (
    "OBSERVED only when a stored sense gloss states the settled active family "
    "as the primary sense and the atom is slang or multiword jargon. Category "
    "membership, topic tags, and source_hint do not set family or attest. "
    "INFERRED is not promoted."
)


def _family_a() -> dict[str, Any]:
    return {
        "family_id": "wiktionary_sense_gloss",
        "fetch_authorized": False,
        "lineage_rule": (
            "An active family other than none. Legacy hints are not families "
            "and are not aliased."
        ),
        "not_the_spent_recipe": list(SPENT_RECIPE),
        "observed_bar": OBSERVED_BAR,
        "provenance_required": [
            "normalized_text_sha256",
            "sense_gloss",
            "wiktionary_page_url",
            "wiktionary_revision_id",
        ],
        "refused_aliases": list(REFUSED_ALIASES),
        "rights": CLEARED_RIGHTS,
        "rights_basis": (
            "The sense gloss is Wiktionary entry text and stays CC-BY-SA. "
            "A mirror may be used only when it preserves that license and the "
            "revision id. Category listings are not this source."
        ),
        "role": "classify_observed_and_classify_non_none",
        "routing": {
            "class": "OBSERVED",
            "lineage_not_none": True,
            "procedure_id": "select_eval_routing_v1",
            "task": "classify",
            "unbind_clean": False,
        },
        "slices": ["classify", "classify_observed", "classify_non_none"],
        "wordnet_admitted": False,
    }


def _family_b() -> dict[str, Any]:
    return {
        "class_policy": (
            "Do not invent OBSERVED. A missing class stays INFERRED. An unbind "
            "row does not fill classify_observed or classify_non_none."
        ),
        "clean_against": {
            "export_rows": PINNED_EXPORT_ROWS,
            "export_sha256": PINNED_EXPORT_SHA256,
            "split": "train",
        },
        "constructor": "hyperlexical.export._unbind_dual_scheme_rows",
        "family_id": "wiktionary_multiword_lemma",
        "fetch_authorized": False,
        "fillers": "the headword's own tokens",
        "not_the_spent_recipe": list(SPENT_RECIPE),
        "provenance_required": [
            "normalized_text_sha256",
            "source_lemma_tokens",
            "wiktionary_page_url",
            "wiktionary_revision_id",
        ],
        "refused_sources": ["operator_authored_fillers", "wikipedia_prose", "wiktionary_category", "wordnet"],
        "rights": CLEARED_RIGHTS,
        "rights_basis": (
            "The headword is Wiktionary entry text and stays CC-BY-SA. "
            "Princeton WordNet is not this source and is not admitted alone."
        ),
        "role": "unbind_clean",
        "routing": {
            "procedure_id": "select_eval_routing_v1",
            "task": "unbind",
            "unbind_clean": True,
            "unbind_clean_derivation": "soft_ceiling.clean_surface",
        },
        "slices": ["unbind_clean"],
        "target_origin": "source_lemma_tokens",
        "wordnet_admitted": False,
    }


def source_design() -> dict[str, Any]:
    """Frozen design. Calling it does not read the network."""
    design = {
        "experiment_id": EXPERIMENT_ID,
        "families": {
            "A": _family_a(),
            "B": _family_b(),
        },
        "legal_lineages": list(ACTIVE_FAMILIES),
        "missing_slices": list(MISSING_SLICES),
        "schema": SCHEMA,
        "spent_recipe_not_repeated": list(SPENT_RECIPE),
        "spent_surface": dict(SPENT_SURFACE),
        "state": STATE,
        "training_authorized": False,
        "transition": TRANSITION,
    }
    _validate(design)
    return design


def _validate(design: Mapping[str, Any]) -> None:
    families = design["families"]
    family_a = families["A"]
    family_b = families["B"]
    covered = set(family_a["slices"]) | set(family_b["slices"])
    missing = set(MISSING_SLICES) - covered
    if missing:
        raise SystemExit("REFUSE: source design misses " + ",".join(sorted(missing)))
    if "classify_observed" not in family_a["slices"] or "classify_non_none" not in family_a["slices"]:
        raise SystemExit("REFUSE: family A must cover observed and non-none together")
    if family_b["slices"] != ["unbind_clean"]:
        raise SystemExit("REFUSE: family B is the unbind_clean source only")
    if any(name in family_a["slices"] for name in ("unbind_clean",)):
        raise SystemExit("REFUSE: family A must not emit unbind_clean")
    for family in (family_a, family_b):
        if family["rights"] != CLEARED_RIGHTS:
            raise SystemExit("REFUSE: source rights are not CC-BY-SA")
        if family["fetch_authorized"]:
            raise SystemExit("REFUSE: this authorization does not fetch")
        if family["wordnet_admitted"]:
            raise SystemExit("REFUSE: WordNet is not admitted")
        if family["family_id"] in SPENT_RECIPE:
            raise SystemExit("REFUSE: spent recipe is not a new source family")
    if design["spent_surface"]["redraw_authorized"] or design["spent_surface"]["relabel_authorized"]:
        raise SystemExit("REFUSE: the 928-row surface stays spent")
    if design["spent_surface"]["decisions"]["UNRESOLVED"] != 888:
        raise SystemExit("REFUSE: unresolved rows must stay unresolved")
    if design["spent_surface"]["decisions"]["NONE"] != 40:
        raise SystemExit("REFUSE: NONE rows must not be repurposed")
    if "none" in design["legal_lineages"]:
        raise SystemExit("REFUSE: none is not an active lineage for family A")


def design_receipt() -> dict[str, Any]:
    body = source_design()
    body["network_requests"] = 0
    body["rows_fetched"] = 0
    record = dict(body)
    record["record_sha256"] = sha256_text(canonical_json(body))
    return record


def freeze_design(path: str) -> dict[str, Any]:
    """Write the receipt. Does not create a harvest."""
    from pathlib import Path
    import os

    receipt = design_receipt()
    target = Path(path)
    if target.exists():
        raise SystemExit(f"REFUSE: design receipt already exists: {target}")
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(target.parent, 0o700)
    target.write_text(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")
    os.chmod(target, 0o600)
    return receipt
