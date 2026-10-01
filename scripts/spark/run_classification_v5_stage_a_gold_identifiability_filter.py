"""APPLY_GOLD_IDENTIFIABILITY_FILTER — Spark/CPU apply.

Emits V1R2 membership-filtered surface from V1R1 under the frozen
gold-identifiability contract. No train, auto-relabel, V1R1 mutation,
input expansion, Stage-B change, reserve use, or BEST moves.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

V1R1_DIR = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-generalization-surface-v1r1-20261001"
)
V1R1_DATASET = V1R1_DIR / "EVIDENCE_SURFACE.jsonl"
V1R1_SHA = "4095036e5af3ad7cfe9f038dd3e1f46e4ef0ea18db4c4b7186fc2b02e96d4274"
ANNOTATIONS = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-factorized-objective-v1-20261001/"
    "FACTORIZED_ANNOTATIONS.jsonl"
)
ANNOTATION_SHA = (
    "4ac884504e4b2fe27e0e5de159847a158c43e2c0d75832ddc5b5c657279778b6"
)
CONTRACT_RECEIPT = (
    REPO
    / "specs"
    / "007-hyperlexical-model"
    / "classification-v5-stage-a-gold-identifiability-contract-receipt-20261001.json"
)
CONTRACT_RECEIPT_SHA = (
    "4ce0e5faccef3772bbefdfc42f878446602ffa59f4d7ae9933652b687a41e3e4"
)
PRIVATE = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-identifiability-filtered-v1r2-20261001"
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def write_json(path: Path, payload: dict | list | str, *, private: bool) -> str:
    path.parent.mkdir(mode=0o700 if private else 0o755, parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    if private:
        os.chmod(path, 0o600)
    return sha256_file(path)


def write_jsonl(path: Path, rows: list[dict], *, private: bool) -> str:
    path.parent.mkdir(mode=0o700 if private else 0o755, parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    if private:
        os.chmod(path, 0o600)
    return sha256_file(path)


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main() -> int:
    from hyperlexical.classification_v5_stage_a import sha256_text, canonical_json
    from hyperlexical.classification_v5_stage_a_gold_identifiability_filter import (
        CONTRACT_RECEIPT_SHA256_PIN,
        DATASET_VERSION,
        FILTER_ID,
        FILTER_RULE,
        NEXT_ACTION,
        SURFACE_ID,
        apply_filter_to_rows,
        assemble_filter_receipt,
    )

    if sha256_file(V1R1_DATASET) != V1R1_SHA:
        fail("v1r1_sha_mismatch")
    if sha256_file(ANNOTATIONS) != ANNOTATION_SHA:
        fail("annotation_sha_mismatch")
    if not CONTRACT_RECEIPT.is_file():
        fail(f"missing_contract_receipt:{CONTRACT_RECEIPT}")
    # Verify contract receipt pin (content hash of sealed receipt without depending
    # on path). The sealed receipt embeds receipt_sha256 field.
    contract = json.loads(CONTRACT_RECEIPT.read_text(encoding="utf-8"))
    if contract.get("receipt_sha256") != CONTRACT_RECEIPT_SHA:
        fail(
            f"contract_receipt_sha_mismatch:"
            f"{contract.get('receipt_sha256')}:{CONTRACT_RECEIPT_SHA}"
        )
    if contract.get("receipt_sha256") != CONTRACT_RECEIPT_SHA256_PIN:
        fail("contract_pin_mismatch")

    if PRIVATE.exists() and (PRIVATE / "EVIDENCE_SURFACE.jsonl").exists():
        fail(f"output_already_exists:{PRIVATE}")
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)

    rows = load_jsonl(V1R1_DATASET)
    anns = {str(a["identity"]): a for a in load_jsonl(ANNOTATIONS)}
    result = apply_filter_to_rows(rows, anns)

    dataset_sha = write_jsonl(
        PRIVATE / "EVIDENCE_SURFACE.jsonl", result["kept_rows"], private=True
    )
    ann_sha = write_jsonl(
        PRIVATE / "FACTORIZED_ANNOTATIONS.jsonl",
        result["kept_annotations"],
        private=True,
    )
    excl_sha = write_jsonl(
        PRIVATE / "EXCLUSION_MANIFEST.jsonl", result["excluded"], private=True
    )

    # Compact classification witness (private)
    class_sha = write_jsonl(
        PRIVATE / "ROW_CLASSIFICATIONS.jsonl",
        result["classifications"],
        private=True,
    )

    manifest = {
        "SURFACE_ID": SURFACE_ID,
        "DATASET_VERSION": DATASET_VERSION,
        "PARENT_DATASET_SHA256": V1R1_SHA,
        "DATASET_SHA256": dataset_sha,
        "FACTORIZED_ANNOTATION_SHA256": ann_sha,
        "EXCLUSION_MANIFEST_SHA256": excl_sha,
        "ROW_CLASSIFICATIONS_SHA256": class_sha,
        "FILTER_RULE": FILTER_RULE,
        "FILTER_ID": FILTER_ID,
        "CONTRACT_RECEIPT_SHA256": CONTRACT_RECEIPT_SHA,
        "counts": result["counts"],
        "viability": result["viability"],
        "MODEL_INPUT": ["text"],
        "AUTO_RELABEL": False,
        "V1R1_MUTATED": False,
        "TRAIN_AUTHORIZED": False,
    }
    manifest["manifest_sha256"] = sha256_text(
        canonical_json({k: v for k, v in manifest.items() if k != "manifest_sha256"})
    )
    man_sha = write_json(PRIVATE / "MANIFEST.json", manifest, private=True)

    summary = {
        "FILTER_RULE": FILTER_RULE,
        "SURFACE_ID": SURFACE_ID,
        "DATASET_VERSION": DATASET_VERSION,
        "DATASET_SHA256": dataset_sha,
        "FACTORIZED_ANNOTATION_SHA256": ann_sha,
        "counts": result["counts"],
        "balance": result["balance"],
        "viability": result["viability"],
        "NEXT_ACTION": NEXT_ACTION,
        "TRAIN_AUTHORIZED": False,
        "V1R2_CREATED": True,
        "V1R1_MUTATED": False,
        "AUTO_RELABEL": False,
    }
    sum_sha = write_json(PRIVATE / "SUMMARY.json", summary, private=True)

    artifact_hashes = {
        "EVIDENCE_SURFACE.jsonl": dataset_sha,
        "FACTORIZED_ANNOTATIONS.jsonl": ann_sha,
        "EXCLUSION_MANIFEST.jsonl": excl_sha,
        "ROW_CLASSIFICATIONS.jsonl": class_sha,
        "MANIFEST.json": man_sha,
        "SUMMARY.json": sum_sha,
    }
    hashes_sha = write_json(
        PRIVATE / "ARTIFACT_HASHES.json", artifact_hashes, private=True
    )
    artifact_hashes["ARTIFACT_HASHES.json"] = hashes_sha

    receipt = assemble_filter_receipt(
        dataset_sha256=dataset_sha,
        annotation_sha256=ann_sha,
        exclusion_manifest_sha256=excl_sha,
        filter_result=result,
        artifact_hashes=artifact_hashes,
    )
    write_json(PRIVATE / "FILTER_RECEIPT.json", receipt, private=True)

    # Public repo mirrors (no full JSONL — hashes + receipt + summary only)
    REPO_ARTIFACTS.mkdir(parents=True, exist_ok=True)
    SPEC_DIR.mkdir(parents=True, exist_ok=True)
    write_json(
        REPO_ARTIFACTS / "gold_identifiability_filter.json", receipt, private=False
    )
    write_json(
        SPEC_DIR
        / "classification-v5-stage-a-gold-identifiability-filter-receipt-20261001.json",
        receipt,
        private=False,
    )
    write_json(
        REPO_ARTIFACTS / "gold_identifiability_filter_summary.json",
        summary,
        private=False,
    )

    md = f"""# Classification v5 — Apply gold identifiability filter (V1R2)

```text
RULE = {FILTER_RULE}
FILTER_ID = {FILTER_ID}
SURFACE = {SURFACE_ID}
DATASET_VERSION = {DATASET_VERSION}
PARENT = V1R1 / {V1R1_SHA[:16]}…
V1R2_DATASET = {dataset_sha[:16]}…
V1R2_ANNOTATIONS = {ann_sha[:16]}…
CONTRACT_RECEIPT = {CONTRACT_RECEIPT_SHA[:16]}…
TRAIN_AUTHORIZED = false
AUTO_RELABEL = false
V1R1_MUTATED = false
STAGE_A_BEST = cd2829c1… UNCHANGED
MODEL_WIDE_BEST = 9fba0f66… UNCHANGED
receipt = {receipt['receipt_sha256'][:16]}…
NEXT_ACTION = {NEXT_ACTION}
```

Membership filter only under `HYPERLEX_STAGE_A_GOLD_IDENTIFIABILITY_CONTRACT_V1`.
No train, auto-relabel, input expansion, Stage-B, reserve, or BEST moves.

## Counts

| Set | n |
|---|---:|
| parent V1R1 | {result['counts']['parent_v1r1']} |
| kept (V1R2) | {result['counts']['kept']} |
| excluded | {result['counts']['excluded']} |
| PRESENT | {result['counts']['by_label'].get('EVIDENCE_PRESENT', 0)} |
| NONE | {result['counts']['by_label'].get('NO_EVIDENCE', 0)} |
| UNCERTAIN | {result['counts']['by_label'].get('UNCERTAIN', 0)} |
| relation_loss_eligible | {result['counts']['relation_loss_eligible']} |
| resolvability_loss_eligible | {result['counts']['resolvability_loss_eligible']} |
| SHORT_ATOM PRESENT kept | {result['counts']['SHORT_ATOM_PRESENT']} |
| SHORT_ATOM NONE kept | {result['counts']['SHORT_ATOM_NONE']} |

## Splits

| Split | n |
|---|---:|
| train | {result['counts']['by_split'].get('train', 0)} |
| validation | {result['counts']['by_split'].get('validation', 0)} |

## Viability

```text
relation +/- = {result['balance']['relation_positive']} / {result['balance']['relation_negative']}
resolvability +/- = {result['balance']['resolvability_positive']} / {result['balance']['resolvability_negative']}
viability = {result['viability']}
```

## Decision

```text
PRIMARY_REPAIR_APPLIED = FILTER_CONTEXT_DEPENDENT_GOLD
V1R2_CREATED = true
TRAIN_AUTHORIZED = false
NEXT_ACTION = {NEXT_ACTION}
NEXT_ACTION_AUTHORIZED = false
```

Do **not** train until a fresh authorization binds this V1R2 surface.
"""
    md_path = (
        SPEC_DIR / "classification-v5-stage-a-gold-identifiability-filter-20261001.md"
    )
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(md, encoding="utf-8")
    (PRIVATE / "FILTER.md").write_text(md, encoding="utf-8")
    os.chmod(PRIVATE / "FILTER.md", 0o600)

    print(
        json.dumps(
            {
                "FILTER_RULE": FILTER_RULE,
                "DATASET_VERSION": DATASET_VERSION,
                "DATASET_SHA256": dataset_sha,
                "FACTORIZED_ANNOTATION_SHA256": ann_sha,
                "EXCLUSION_MANIFEST_SHA256": excl_sha,
                "kept": result["counts"]["kept"],
                "excluded": result["counts"]["excluded"],
                "by_label": result["counts"]["by_label"],
                "relation_loss_eligible": result["counts"]["relation_loss_eligible"],
                "viability": result["viability"],
                "NEXT_ACTION": NEXT_ACTION,
                "TRAIN_AUTHORIZED": False,
                "receipt_sha256": receipt["receipt_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
