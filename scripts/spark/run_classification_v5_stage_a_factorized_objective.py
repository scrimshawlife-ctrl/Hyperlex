"""SPEC_STAGE_A_FACTORIZED_OBJECTIVE — Spark seal runner.

Builds factorized annotation sidecar from V1R1 and seals receipts.
Does not train, create V1R2, human-relabel, alter Stage B, or move BEST.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
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
PRIVATE = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-factorized-objective-v1-20261001"
)
REPO_ARTIFACTS = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-001"
)
SPEC_DIR = REPO / "specs" / "007-hyperlexical-model"

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def main() -> int:
    builder = (
        REPO
        / "scripts"
        / "shadow"
        / "hyperlexical"
        / "build_classification_v5_stage_a_factorized_annotations.py"
    )
    PRIVATE.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [
            sys.executable,
            str(builder),
            "--dataset",
            str(DATASET),
            "--out-dir",
            str(PRIVATE),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        sys.stderr.write(completed.stdout)
        sys.stderr.write(completed.stderr)
        return completed.returncode

    summary = json.loads(completed.stdout)
    receipt = json.loads((PRIVATE / "OBJECTIVE_RECEIPT.json").read_text())

    REPO_ARTIFACTS.mkdir(parents=True, exist_ok=True)
    for name in (
        "FACTORIZED_ANNOTATIONS.jsonl",
        "FACTORIZED_ANNOTATION_MANIFEST.json",
        "DERIVATION_WITNESS.json",
        "ARTIFACT_HASHES.json",
        "OBJECTIVE_RECEIPT.json",
    ):
        shutil.copy2(PRIVATE / name, REPO_ARTIFACTS / name)

    spec_receipt = (
        SPEC_DIR
        / "classification-v5-stage-a-factorized-objective-receipt-20261001.json"
    )
    SPEC_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PRIVATE / "OBJECTIVE_RECEIPT.json", spec_receipt)

    print(
        json.dumps(
            {
                **summary,
                "spec_receipt": str(spec_receipt),
                "repo_artifacts": str(REPO_ARTIFACTS),
                "PRIMARY_DECOMPOSITION_PARENT": receipt.get("PARENT_DECOMPOSITION"),
                "NEXT_ACTION": receipt.get("NEXT_ACTION"),
                "receipt_sha256": receipt.get("receipt_sha256"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
