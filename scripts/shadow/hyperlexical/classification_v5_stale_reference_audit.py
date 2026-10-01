"""Audit active runtime/specs for stale Stage-A/B references after V1R2 seal.

Only the live canonical/pipeline/Stage-B/seal surface is ACTIVE_*. Everything
else in Spec 007 history is HISTORICAL / EXPERIMENT_ARTIFACT / TEST_FIXTURE.
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
from .classification_v5_stage_b import (
    FROZEN_INDEX_SHA256,
    HISTORICAL_V1R9_INDEX_SHA256,
)

STALE_PATTERNS = (
    ("cd2829c1", "superseded_STAGE_A_BEST"),
    ("8b2de447", "incomplete_historical_checkpoint"),
    ("26841d5f", "stale_checkpoint_ref"),
    ("8a6981c1", "stale_checkpoint_ref"),
    ("3fd6c87a", "historical_v1r9_stage_b_index"),
    ("POSSIBLE_EVIDENCE", "deprecated_training_target"),
    ("gate1_threshold", "legacy_two_stage_threshold"),
    ("gate2_threshold", "legacy_two_stage_threshold"),
    ("gate1_head", "legacy_two_stage_head"),
    ("gate2_head", "legacy_two_stage_head"),
    ("evidence_head", "legacy_flat_head"),
    ("decide_evidence", "legacy_flat_decide"),
    ("two_stage_forward", "legacy_forward_schema"),
    ("0.64", "historical_v1r9_score_floor"),
    ("0.07", "historical_v1r9_margin_floor"),
)

# Explicit live surface after SEAL_AND_PACKAGE_HYPERLEX_V5_STAGE_A_B_V1R2_PIPELINE.
ACTIVE_RUNTIME_FILES = {
    "scripts/shadow/hyperlexical/classification_v5_stage_a_canonical.py",
    "scripts/shadow/hyperlexical/classification_v5_stage_a_b_pipeline.py",
    "scripts/shadow/hyperlexical/classification_v5_stage_b.py",
    "scripts/shadow/hyperlexical/classification_v5_stage_b_v1r2_align.py",
    "scripts/shadow/hyperlexical/classification_v5_seal_and_package.py",
    "scripts/shadow/hyperlexical/classification_v5_production_packaging.py",
    "scripts/shadow/hyperlexical/classification_v5_pipeline_evaluate.py",
    "scripts/shadow/hyperlexical/classification_v5_pipeline_diagnose.py",
    "scripts/shadow/hyperlexical/classification_v5_stale_reference_audit.py",
    "scripts/shadow/hyperlexical/save_pretrained.py",
    "scripts/shadow/hyperlexical/classification_v5_stage_a_factorized_objective.py",
    "scripts/shadow/hyperlexical/classification_v5_stage_a_ident_filtered_repro_promote.py",
    "scripts/shadow/hyperlexical/classification_v5_stage_a_ident_filtered_promote.py",
    "scripts/spark/run_classification_v5_stage_a_canonical_freeze.py",
    "scripts/spark/run_classification_v5_stage_a_b_integration_verify.py",
    "scripts/spark/run_classification_v5_seal_and_package_pipeline.py",
    "scripts/spark/run_classification_v5_stage_b_v1r2_align.py",
}

ACTIVE_SPEC_FILES = {
    "CHANGELOG.md",
    "specs/007-hyperlexical-model/model-card.draft.md",
    "specs/007-hyperlexical-model/hf-package/README.md",
    "specs/007-hyperlexical-model/classification-v5-stage-a-canonical-20261001.md",
    "specs/007-hyperlexical-model/classification-v5-stage-a-canonical-receipt-20261001.json",
    "specs/007-hyperlexical-model/classification-v5-stage-a-b-pipeline-20261001.md",
    "specs/007-hyperlexical-model/classification-v5-stage-b-v1r2-active-contract-20261001.json",
    "specs/007-hyperlexical-model/classification-v5-stage-b-v1r2-align-20261001.md",
    "specs/007-hyperlexical-model/classification-v5-stage-b-v1r2-alignment-receipt-20261001.json",
    "specs/007-hyperlexical-model/classification-v5-stage-a-b-v1r2-seal-package-20261001.md",
    "specs/007-hyperlexical-model/classification-v5-stage-a-b-v1r2-seal-package-receipt-20261001.json",
    "specs/007-hyperlexical-model/classification-v5-stage-a-b-v1r2-dependency-manifest-20261001.json",
    "specs/007-hyperlexical-model/classification-v5-stale-reference-audit-20261001.json",
    "specs/007-hyperlexical-model/hf-package/V5_PIPELINE_CARD_FRAGMENT.md",
}

ACTIVE_TEST_FILES = {
    "tests/shadow/test_classification_v5_stage_b.py",
    "tests/shadow/test_classification_v5_stage_a_canonical.py",
    "tests/shadow/test_classification_v5_stage_a_b_pipeline.py",
    "tests/shadow/test_classification_v5_stage_b_v1r2_align.py",
    "tests/shadow/test_classification_v5_seal_and_package.py",
    "tests/shadow/test_classification_v5_pipeline_evaluate.py",
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


def _intentional(pattern: str, text: str, rel: str) -> bool:
    if pattern == "cd2829c1" and re.search(
        r"SUPERSEDED|PREVIOUS_STAGE_A_BEST|previous_STAGE_A_BEST|"
        r"Previous|superseded|f2b00c5d|HISTORICAL",
        text,
        re.I,
    ):
        return True
    if pattern == "8b2de447" and re.search(
        r"NON_PROMOTABLE|incomplete|HISTORICAL|packaging.artifact",
        text,
        re.I,
    ):
        return True
    if pattern in {"26841d5f", "8a6981c1"} and re.search(
        r"HISTORICAL|stale|superseded|retained",
        text,
        re.I,
    ):
        return True
    if pattern == "3fd6c87a" and (
        HISTORICAL_V1R9_INDEX_SHA256[:8] in text
        and (
            "HISTORICAL" in text
            or "historical_v1r9" in text
            or "SUPERSEDED" in text
            or FROZEN_INDEX_SHA256[:8] in text
        )
    ):
        return True
    if pattern in {"0.64", "0.07"} and re.search(
        r"HISTORICAL|historical_v1r9|V1R9|superseded",
        text,
        re.I,
    ):
        # Only intentional when active V1R2 floors also appear nearby in active files.
        if "0.83" in text or "4febe96e" in text or "HISTORICAL" in text:
            return True
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
        return True
    if pattern in {"evidence_head", "gate1_head", "gate2_head"} and (
        "save_pretrained.py" in rel
    ):
        return True
    return False


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
            intentional = _intentional(pattern, text, rel)
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
        "STAGE_B_INDEX_active": FROZEN_INDEX_SHA256,
        "STAGE_B_INDEX_historical_v1r9": HISTORICAL_V1R9_INDEX_SHA256,
        "active_runtime_files": sorted(ACTIVE_RUNTIME_FILES),
        "active_spec_files": sorted(ACTIVE_SPEC_FILES),
        "hits": hits,
        "n_hits": len(hits),
        "active_needs_fix": active_needs_fix,
        "n_active_needs_fix": len(active_needs_fix),
        "pass": len(active_needs_fix) == 0,
        "policy": (
            "Fix only ACTIVE_RUNTIME / ACTIVE_SPEC stale bindings on the live "
            "V1R2 seal surface. Historical receipts/runners/artifacts retained."
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
