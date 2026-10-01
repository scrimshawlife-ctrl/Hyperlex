"""Audit active runtime/specs for stale Stage-A references after canonical freeze.

Only the live canonical/pipeline/Stage-B surface is ACTIVE_*. Everything else
in Spec 007 history is HISTORICAL / EXPERIMENT_ARTIFACT / TEST_FIXTURE.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_canonical import STAGE_A_BEST_SHA256
from .classification_v5_stage_a_ident_filtered_repro_promote import (
    PREVIOUS_STAGE_A_BEST_SHA256,
)

STALE_PATTERNS = (
    ("cd2829c1", "superseded_STAGE_A_BEST"),
    ("POSSIBLE_EVIDENCE", "deprecated_training_target"),
    ("gate1_threshold", "legacy_two_stage_threshold"),
    ("gate2_threshold", "legacy_two_stage_threshold"),
    ("gate1_head", "legacy_two_stage_head"),
    ("gate2_head", "legacy_two_stage_head"),
    ("evidence_head", "legacy_flat_head"),
    ("decide_evidence", "legacy_flat_decide"),
    ("two_stage_forward", "legacy_forward_schema"),
)

# Explicit live surface after FREEZE_V5_STAGE_A_CANONICAL…
ACTIVE_RUNTIME_FILES = {
    "scripts/shadow/hyperlexical/classification_v5_stage_a_canonical.py",
    "scripts/shadow/hyperlexical/classification_v5_stage_a_b_pipeline.py",
    "scripts/shadow/hyperlexical/classification_v5_stage_b.py",
    "scripts/shadow/hyperlexical/classification_v5_stale_reference_audit.py",
    "scripts/shadow/hyperlexical/save_pretrained.py",
    "scripts/shadow/hyperlexical/classification_v5_stage_a_factorized_objective.py",
    "scripts/shadow/hyperlexical/classification_v5_stage_a_ident_filtered_repro_promote.py",
    "scripts/shadow/hyperlexical/classification_v5_stage_a_ident_filtered_promote.py",
    "scripts/spark/run_classification_v5_stage_a_canonical_freeze.py",
    "scripts/spark/run_classification_v5_stage_a_b_integration_verify.py",
}

ACTIVE_SPEC_FILES = {
    "CHANGELOG.md",
    "specs/007-hyperlexical-model/model-card.draft.md",
    "specs/007-hyperlexical-model/classification-v5-stage-a-canonical-20261001.md",
    "specs/007-hyperlexical-model/classification-v5-stage-a-canonical-receipt-20261001.json",
    "specs/007-hyperlexical-model/classification-v5-stage-a-b-pipeline-20261001.md",
    "specs/007-hyperlexical-model/classification-v5-stage-a-b-pipeline-receipt-20261001.json",
    "specs/007-hyperlexical-model/classification-v5-stage-b-active-contract-20261001.json",
    "specs/007-hyperlexical-model/classification-v5-stale-reference-audit-20261001.json",
}

ACTIVE_TEST_FILES = {
    "tests/shadow/test_classification_v5_stage_b.py",
    "tests/shadow/test_classification_v5_stage_a_canonical.py",
    "tests/shadow/test_classification_v5_stage_a_b_pipeline.py",
}


def _classify(path: str) -> str:
    norm = path.replace("\\", "/")
    if norm in ACTIVE_RUNTIME_FILES:
        return "ACTIVE_RUNTIME"
    if norm in ACTIVE_SPEC_FILES:
        return "ACTIVE_SPEC"
    if norm in ACTIVE_TEST_FILES:
        return "ACTIVE_RUNTIME"
    if norm.startswith("tests/"):
        return "TEST_FIXTURE"
    if norm.startswith("artifacts/experiments/"):
        return "EXPERIMENT_ARTIFACT"
    return "HISTORICAL"


def audit_tree(repo_root: Path) -> dict[str, Any]:
    hits: list[dict[str, Any]] = []
    files: list[Path] = []
    for rel in sorted(
        ACTIVE_RUNTIME_FILES | ACTIVE_SPEC_FILES | ACTIVE_TEST_FILES
    ):
        path = repo_root / rel
        if path.is_file():
            files.append(path)

    for path in files:
        rel = str(path.relative_to(repo_root))
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        classification = _classify(rel)
        for pattern, kind in STALE_PATTERNS:
            if pattern not in text:
                continue
            count = text.count(pattern)
            intentional = False
            if pattern == "cd2829c1" and (
                "SUPERSEDED" in text
                or "PREVIOUS_STAGE_A_BEST" in text
                or "previous_STAGE_A_BEST" in text
                or "Previous" in text
                or "superseded" in text
                or "f2b00c5d" in text
                or STAGE_A_BEST_SHA256[:8] in text
            ):
                intentional = True
            if pattern in {
                "POSSIBLE_EVIDENCE",
                "gate1_threshold",
                "gate2_threshold",
                "gate1_head",
                "gate2_head",
                "evidence_head",
                "decide_evidence",
                "two_stage_forward",
            } and re.search(
                r"DEPRECATED|HISTORICAL|legacy|superseded|NON_PROMOTABLE|"
                r"whitelist|_HEAD_NAMES|historical|deprecated_gate",
                text,
                re.I,
            ):
                intentional = True
            if pattern in {"evidence_head", "gate1_head", "gate2_head"} and (
                "save_pretrained.py" in rel
            ):
                intentional = True
            needs_fix = (
                classification in {"ACTIVE_RUNTIME", "ACTIVE_SPEC"} and not intentional
            )
            hits.append(
                {
                    "path": rel,
                    "pattern": pattern,
                    "kind": kind,
                    "classification": classification,
                    "count": count,
                    "intentional_historical_mention": intentional,
                    "needs_fix": needs_fix,
                }
            )

    active_needs_fix = [h for h in hits if h["needs_fix"]]
    return {
        "STAGE_A_BEST_canonical": STAGE_A_BEST_SHA256,
        "PREVIOUS_STAGE_A_BEST": PREVIOUS_STAGE_A_BEST_SHA256,
        "active_runtime_files": sorted(ACTIVE_RUNTIME_FILES),
        "active_spec_files": sorted(ACTIVE_SPEC_FILES),
        "hits": hits,
        "n_hits": len(hits),
        "active_needs_fix": active_needs_fix,
        "n_active_needs_fix": len(active_needs_fix),
        "pass": len(active_needs_fix) == 0,
        "policy": (
            "Fix only ACTIVE_RUNTIME / ACTIVE_SPEC stale bindings on the live "
            "canonical surface. Historical receipts/runners/artifacts retained."
        ),
    }


def seal_audit_receipt(audit: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema": "hyperlex.classification.v5.stale_reference_audit.v1",
        "audit": audit,
    }
    payload["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in payload.items() if k != "receipt_sha256"})
    )
    return payload
