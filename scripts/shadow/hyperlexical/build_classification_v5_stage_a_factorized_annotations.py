"""Build factorized Stage-A annotation sidecar from sealed V1R1 gold.

Deterministic derivation only. Does not train or human-relabel.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"

# Allow `python -m` / direct path execution.
_SHADOW = Path(__file__).resolve().parent.parent
if str(_SHADOW) not in sys.path:
    sys.path.insert(0, str(_SHADOW))

from hyperlexical.classification_v5_stage_a_factorized_objective import (  # noqa: E402
    AUTHORIZED_DATASET_SHA,
    EXPECTED_ROW_COUNT,
    assemble_objective_receipt,
    build_annotations,
)
from hyperlexical.classification_v5_stage_a import canonical_json  # noqa: E402


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def build_artifact_hashes(paths: dict[str, Path]) -> dict[str, str]:
    return {name: sha256_file(path) for name, path in sorted(paths.items())}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build V1R1 factorized Stage-A annotation sidecar"
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        required=True,
        help="Path to V1R1 EVIDENCE_SURFACE.jsonl",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Output directory for sidecar artifacts",
    )
    parser.add_argument(
        "--expect-dataset-sha256",
        default=AUTHORIZED_DATASET_SHA,
        help="Pinned source dataset SHA",
    )
    args = parser.parse_args(argv)

    dataset_sha = sha256_file(args.dataset)
    if dataset_sha != args.expect_dataset_sha256:
        print(
            f"dataset sha mismatch: {dataset_sha} != {args.expect_dataset_sha256}",
            file=sys.stderr,
        )
        return 2

    rows = load_jsonl(args.dataset)
    if len(rows) != EXPECTED_ROW_COUNT:
        print(f"row count mismatch: {len(rows)}", file=sys.stderr)
        return 2

    bundle = build_annotations(rows, source_dataset_sha256=dataset_sha)
    receipt = assemble_objective_receipt(annotation_bundle=bundle)

    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)

    ann_path = out / "FACTORIZED_ANNOTATIONS.jsonl"
    ann_path.write_text(bundle["jsonl_body"])

    paths = {
        "FACTORIZED_ANNOTATIONS.jsonl": ann_path,
        "FACTORIZED_ANNOTATION_MANIFEST.json": out
        / "FACTORIZED_ANNOTATION_MANIFEST.json",
        "DERIVATION_WITNESS.json": out / "DERIVATION_WITNESS.json",
        "OBJECTIVE_RECEIPT.json": out / "OBJECTIVE_RECEIPT.json",
    }
    write_json(paths["FACTORIZED_ANNOTATION_MANIFEST.json"], bundle["manifest"])
    write_json(paths["DERIVATION_WITNESS.json"], bundle["derivation_witness"])
    write_json(paths["OBJECTIVE_RECEIPT.json"], receipt)

    hashes = build_artifact_hashes(paths)
    hashes_payload = {
        "schema": "hyperlex.classification.v5.stage_a_factorized_artifact_hashes.v1",
        "FACTORIZED_ANNOTATION_SHA256": bundle["FACTORIZED_ANNOTATION_SHA256"],
        "hashes": hashes,
        "source_dataset_sha256": dataset_sha,
    }
    hashes_payload["artifact_hashes_sha256"] = __import__(
        "hyperlexical.classification_v5_stage_a", fromlist=["sha256_text"]
    ).sha256_text(
        canonical_json(
            {
                k: v
                for k, v in hashes_payload.items()
                if k != "artifact_hashes_sha256"
            }
        )
    )
    write_json(out / "ARTIFACT_HASHES.json", hashes_payload)

    print(
        json.dumps(
            {
                "FACTORIZED_ANNOTATION_SHA256": bundle[
                    "FACTORIZED_ANNOTATION_SHA256"
                ],
                "receipt_sha256": receipt["receipt_sha256"],
                "counts": bundle["counts"],
                "out_dir": str(out),
                "TRAIN_AUTHORIZED": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
