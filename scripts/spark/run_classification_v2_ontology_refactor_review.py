"""Seal HYPERLEX_ACTIVE_FAMILY_ONTOLOGY_REFACTOR_REVIEW_V1.

Read-only ontology decision for the three structural families. Does not apply
the change, train, score the reserve, or move BEST.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
PHASE = Path("/home/morpheus/hlx-private/classification-v2-phase-execution-20260930")
PHASE_EXECUTION = PHASE / "PHASE_EXECUTION.json"
PHASE_EXECUTION_SHA = "6d11eab035d64a5ef8d1008ade9b565064920e6de2cc86673202cbc60753be3b"
PHASE_D = PHASE / "PHASE_D_SEPARABILITY_AUDIT.json"
PHASE_D_SHA = "d56d03420e7f7072b1798a55e7ecd8877263b1dfd4ad938d36115cba18a21d0a"
OVERLAY = PHASE / "civilian.v0.4.phase.jsonl"
OVERLAY_SHA = "8a934806885fb939f8b4ca26f10ab5bc6600c495d3be77d5a2366dc6c62146e0"
REDEF = Path(
    "/home/morpheus/hlx-private/classification-v2-boundary-redefinition-20260930/BOUNDARY_REDEFINITION.json"
)
REDEF_SHA = "4757d46aa7f0c95732378d5f710cbd1a28d048f60bee2fc35dfb6d5c0fe8cad1"
TIGHT = Path(
    "/home/morpheus/hlx-private/classification-v2-boundary-tightening-v2-20260930/BOUNDARY_TIGHTENING_V2.json"
)
TIGHT_SHA = "8c9f88b0431b3598d5336bdb7fa25b80e8201c2ad8487d5aea878997cb6aa5a9"
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
BOUNDARIES = Path(
    "/home/morpheus/hlx-private/classification-v2-boundaries-20260930/FAMILY_SEMANTIC_BOUNDARIES.json"
)
BOUNDARY_SHA = "0ca6f34ce1abf68388e443371672ca36e16028079a175b6775e1968900e1c52f"
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
DEST = Path("/home/morpheus/hlx-private/classification-v2-ontology-refactor-review-20260930")

sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sha256_file(path: Path) -> str:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except PermissionError:
        return subprocess.check_output(["sudo", "sha256sum", str(path)], text=True).split()[0]


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def main() -> int:
    from hyperlexical.classification_v2 import canonical_json, sha256_text
    from hyperlexical.classification_v2_ontology_refactor_review import (
        FOCUS_FAMILIES,
        TIGHTENING_V2_SHA,
        analyze_pair,
        assemble_ontology_review,
        build_migration_mapping,
        build_semantic_definitions,
        decide_recommendation,
        estimate_impacts,
        review_contract,
        summarize_family,
    )
    from hyperlexical.classification_v2_separability_audit import definition_sources
    from hyperlexical.identity_ledger import IdentityLedger, derived_state

    if TIGHTENING_V2_SHA != TIGHT_SHA:
        fail("tightening pin drift")
    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if sha256_file(OVERLAY) != OVERLAY_SHA:
        fail("overlay changed")
    phase = json.loads(PHASE_EXECUTION.read_text(encoding="utf-8"))
    if phase.get("artifact_sha256") != PHASE_EXECUTION_SHA:
        fail("phase execution hash mismatch")
    phase_d = json.loads(PHASE_D.read_text(encoding="utf-8"))
    if phase_d.get("artifact_sha256") != PHASE_D_SHA:
        fail("phase D hash mismatch")
    redef = json.loads(REDEF.read_text(encoding="utf-8"))
    if redef.get("artifact_sha256") != REDEF_SHA:
        fail("boundary redefinition hash mismatch")
    tight = json.loads(TIGHT.read_text(encoding="utf-8"))
    if tight.get("artifact_sha256") != TIGHT_SHA:
        fail("tightening v2 hash mismatch")
    boundaries = json.loads(BOUNDARIES.read_text(encoding="utf-8"))
    if boundaries.get("boundary_sha256") != BOUNDARY_SHA:
        fail("historical boundary hash mismatch")

    rows = [json.loads(line) for line in OVERLAY.read_text(encoding="utf-8").splitlines() if line.strip()]
    ledger = IdentityLedger.load(str(LEDGER))
    states = {digest: derived_state(record) for digest, record in ledger.identities.items()}
    train_sources = definition_sources(rows, states, split="train")["sources"]
    val_sources = definition_sources(rows, states, split="val")["sources"]

    contracts = redef.get("family_contracts") or {}
    pair_rows = phase_d.get("pair_rows") or []
    texts = {
        family: [str(row.get("text") or "") for row in train_sources[family]["rows"]]
        for family in FOCUS_FAMILIES
    }
    support_train = {family: len(texts[family]) for family in FOCUS_FAMILIES}
    support_val = {
        family: len(val_sources.get(family, {}).get("rows") or []) for family in FOCUS_FAMILIES
    }

    summaries = {}
    for family in FOCUS_FAMILIES:
        summaries[family] = summarize_family(
            family,
            contract=contracts.get(family),
            texts=texts[family],
            pair_rows=pair_rows,
        )

    pairs = [
        ("approval-disapproval", "social-status"),
        ("approval-disapproval", "relationship-dating"),
        ("social-status", "relationship-dating"),
    ]
    analyses = []
    for family_a, family_b in pairs:
        sealed = None
        for row in pair_rows:
            if {row.get("family_a"), row.get("family_b")} == {family_a, family_b}:
                sealed = row
                break
        analyses.append(
            analyze_pair(
                family_a,
                family_b,
                texts_a=texts[family_a],
                texts_b=texts[family_b],
                summary_a=summaries[family_a],
                summary_b=summaries[family_b],
                sealed_pair=sealed,
            )
        )

    recommendation = decide_recommendation(analyses)
    migration = build_migration_mapping(recommendation)
    definitions = build_semantic_definitions(recommendation)
    impacts = estimate_impacts(
        recommendation,
        support_train=support_train,
        support_val=support_val,
        pair_analyses=analyses,
    )
    # Attach sealed structural statuses from tightening for traceability.
    impacts["prior_split_candidate_assessments"] = tight.get("split_candidate_assessments")
    impacts["prior_tightening_overlap_reduction"] = tight.get("overlap_reduction")

    artifact = assemble_ontology_review(
        {
            "family_summaries": summaries,
            "pairwise_analyses": analyses,
            "recommendation": recommendation,
            "semantic_definitions": definitions,
            "migration": migration,
            "impacts": impacts,
        }
    )
    artifact["contract"] = review_contract()
    artifact["artifact_sha256"] = sha256_text(
        canonical_json({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    )

    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if boundaries.get("boundary_sha256") != BOUNDARY_SHA:
        fail("historical boundaries mutated")

    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    destination = DEST / "ONTOLOGY_REFACTOR_REVIEW.json"
    destination.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "destination": str(destination),
        "ontology_review_state": artifact["ontology_review_state"],
        "artifact_sha256": artifact["artifact_sha256"],
        "primary_recommendation": artifact["primary_recommendation"],
        "affected_families": artifact["affected_families"],
        "proposed_resulting_labels": artifact["proposed_resulting_labels"],
        "rationale": artifact["rationale"],
        "migration_mapping": artifact["migration_mapping"],
        "rows_affected_train": impacts["rows_affected_train"],
        "rows_affected_val": impacts["rows_affected_val"],
        "support_after_proposed": impacts["support_after_proposed"],
        "expected_overlap_impact": impacts["expected_overlap_impact"],
        "training_gate": artifact["training_gate"],
        "applies_ontology_change": artifact["applies_ontology_change"],
        "next_engineering_action": artifact["next_engineering_action"],
        "best_sha256": BEST_SHA,
        "train": False,
        "reserve_scored": False,
        "moves_best": False,
    }
    (DEST / "ONTOLOGY_REFACTOR_REVIEW_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
