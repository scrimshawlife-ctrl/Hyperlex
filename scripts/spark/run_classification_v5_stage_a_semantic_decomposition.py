"""STAGE_A_SEMANTIC_DECOMPOSITION — Spark/local seal runner.

Spec + V1R1 gold-field recoverability audit only.
Does not train, create V1R2, relabel, retune, use spent reserve, or move BEST.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

SURFACE = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-generalization-surface-v1r1-20261001"
)
DATASET = SURFACE / "EVIDENCE_SURFACE.jsonl"
DATASET_SHA = "4095036e5af3ad7cfe9f038dd3e1f46e4ef0ea18db4c4b7186fc2b02e96d4274"
PRIVATE = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-semantic-decomposition-20261001"
)
REPO_ARTIFACTS = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-GENERALIZATION-001"
)
SPEC_DIR = REPO / "specs" / "007-hyperlexical-model"

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open() as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    from hyperlexical.classification_v5_stage_a_semantic_decomposition import (
        assemble_decomposition_receipt,
        assert_audit_matches_frozen,
        audit_rows,
    )

    if not DATASET.is_file():
        print(f"dataset missing: {DATASET}", file=sys.stderr)
        return 2
    dataset_sha = sha256_file(DATASET)
    if dataset_sha != DATASET_SHA:
        print(f"dataset sha mismatch: {dataset_sha}", file=sys.stderr)
        return 2

    rows = load_jsonl(DATASET)
    audit = audit_rows(rows)
    assert_audit_matches_frozen(audit)
    receipt = assemble_decomposition_receipt(audit)

    PRIVATE.mkdir(parents=True, exist_ok=True)
    REPO_ARTIFACTS.mkdir(parents=True, exist_ok=True)
    SPEC_DIR.mkdir(parents=True, exist_ok=True)

    private_path = PRIVATE / "semantic_decomposition.json"
    art_path = REPO_ARTIFACTS / "semantic_decomposition.json"
    receipt_path = (
        SPEC_DIR / "classification-v5-stage-a-semantic-decomposition-receipt-20261001.json"
    )
    payload = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    private_path.write_text(payload)
    art_path.write_text(payload)
    receipt_path.write_text(payload)

    print(
        json.dumps(
            {
                "PRIMARY_DECOMPOSITION": receipt["PRIMARY_DECOMPOSITION"],
                "NEXT_ACTION": receipt["NEXT_ACTION"],
                "NEXT_ACTION_AUTHORIZED": receipt["NEXT_ACTION_AUTHORIZED"],
                "minimum_new_gold_requirement": receipt["minimum_new_gold_requirement"],
                "dataset_consequence": receipt["dataset_consequence"],
                "receipt_sha256": receipt["receipt_sha256"],
                "private": str(private_path),
                "artifact": str(art_path),
                "spec_receipt": str(receipt_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
