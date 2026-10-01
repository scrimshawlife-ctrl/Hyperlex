"""Build DESIGN_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE on Spark.

Fresh Stage-A train/validation surface only. Does not train, does not score
any reserve, does not create a promotion reserve, and does not move BEST.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
PRIVATE = Path(
    "/home/morpheus/hlx-private/classification-v5-stage-a-negative-evidence-surface-20260930"
)
HUB = Path(
    "/home/morpheus/hlx-private/classification-v2-train-forward-20260930/"
    "civilian.v0.7.hub.jsonl"
)
HUB_SHA = "0d8f4532f84ed9fade3fd4e69af0d1e0717fb1098d40754e95c0090d8282bfe1"
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926/ledger.json")
SPENT_V2 = Path(
    "/home/morpheus/hlx-private/classification-v2-train-ready-20260929/"
    "reserve-eval-rows.jsonl"
)
SPENT_V2_SHA = "8c5276442ce37cf99fff597653a28917b3b4dc69ac87ad01f815fa458416ed36"
SPENT_V3 = Path(
    "/home/morpheus/hlx-private/classification-v3-reserve-20260930/reserve-rows.jsonl"
)
SPENT_V3_SHA = "abb8bf22012bb450dba05ce3129e32c2f28fabe9911030b28c68c5b99d39b937"
SPENT_V4 = Path(
    "/home/morpheus/hlx-private/classification-v4-reserve-20260930/reserve-rows.jsonl"
)
SPENT_V4_SHA = "dd224047b331cd13b5a6893519907f9998620a482b0d17f29b3444b46794eb82"
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
BEST_LINK = Path("/home/morpheus/.hyperlex/models/BEST")
INIT_FROM = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004"
)
SCHEMA_DIR = REPO / "specs/007-hyperlexical-model/schemas/classification-v5"

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sudo_sha256(path: Path) -> str:
    try:
        return sha256_file(path)
    except PermissionError:
        completed = subprocess.run(
            ["sudo", "-n", "sha256sum", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.split()[0]


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def write_private(path: Path, payload: dict | str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    os.chmod(path, 0o600)


def pin_inputs() -> None:
    if sha256_file(HUB) != HUB_SHA:
        fail("hub export digest mismatch")
    if sha256_file(SPENT_V2) != SPENT_V2_SHA:
        fail("spent v2 rows digest mismatch")
    # v4 reserve-rows body equals sealed acquire body in this lineage.
    if sha256_file(SPENT_V3) != SPENT_V3_SHA:
        fail("spent v3 rows digest mismatch")
    if sha256_file(SPENT_V4) != SPENT_V4_SHA:
        fail("spent v4 rows digest mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    try:
        best_is_link = BEST_LINK.is_symlink()
        best_target = BEST_LINK.resolve() if best_is_link else None
    except PermissionError:
        completed = subprocess.run(
            ["sudo", "-n", "readlink", "-f", str(BEST_LINK)],
            check=True,
            capture_output=True,
            text=True,
        )
        best_is_link = True
        best_target = Path(completed.stdout.strip())
    if not best_is_link or best_target != INIT_FROM.resolve():
        fail("BEST symlink is not the production checkpoint")


def verify_schema_hashes(expected: dict[str, str]) -> dict[str, str]:
    observed = {}
    mapping = {"evidence_example.v1": "evidence_example.v1.schema.json"}
    for key, filename in mapping.items():
        path = SCHEMA_DIR / filename
        digest = sha256_file(path)
        observed[key] = digest
        if digest != expected[key]:
            fail(f"schema hash drift:{key}:{digest}!={expected[key]}")
    return observed


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main() -> int:
    from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY
    from hyperlexical.classification_v5_stage_a_negative_evidence_surface import (
        BEST_SHA as MODULE_BEST,
        DESIGN_RULE,
        SCHEMA_SHA,
        SURFACE_RULE,
        build_surface,
        canonical_json,
        load_blocked_ids,
        preregistration_contract,
        sha256_text,
    )

    pin_inputs()
    if MODULE_BEST != BEST_SHA:
        fail("module BEST pin drift")
    schema_hashes = verify_schema_hashes(SCHEMA_SHA)
    prereg = preregistration_contract()

    if PRIVATE.exists() and any(PRIVATE.iterdir()):
        fail(f"destination already frozen:{PRIVATE}")
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(PRIVATE, 0o700)

    write_private(
        PRIVATE / "PREREGISTRATION.json",
        {
            **prereg,
            "frozen_schema_sha256": schema_hashes,
            "hub_sha256": HUB_SHA,
            "spent_v2_rows_sha256": SPENT_V2_SHA,
            "spent_v3_rows_sha256": SPENT_V3_SHA,
            "spent_v4_rows_sha256": SPENT_V4_SHA,
        },
    )

    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    spent_v2 = load_jsonl(SPENT_V2)
    spent_v3 = load_jsonl(SPENT_V3)
    spent_v4 = load_jsonl(SPENT_V4)
    blocked = load_blocked_ids(
        ledger=ledger,
        spent_row_files=(spent_v2, spent_v3, spent_v4),
    )
    if len(blocked) < 400:
        fail(f"blocked set too small:{len(blocked)}")
    write_private(
        PRIVATE / "ISOLATION.json",
        {
            "blocked_n": len(blocked),
            "design_rule": DESIGN_RULE,
            "spent_v2_n": len(spent_v2),
            "spent_v3_n": len(spent_v3),
            "spent_v4_n": len(spent_v4),
            "surface_rule": SURFACE_RULE,
            "train_consumed_excluded": False,
        },
    )

    source_rows = load_jsonl(HUB)
    built = build_surface(
        source_rows,
        blocked_ids=blocked,
        ontology=ACTIVE_FAMILY_VOCABULARY,
        augment=True,
    )
    assembled = built["assembled"]
    readiness = built["readiness"]

    dataset_path = PRIVATE / "EVIDENCE_SURFACE.jsonl"
    write_private(dataset_path, assembled["dataset_body"])
    if sha256_file(dataset_path) != assembled["dataset_sha256"]:
        fail("dataset body digest mismatch after write")

    write_private(PRIVATE / "DATASET_MANIFEST.json", assembled["dataset_manifest"])
    write_private(PRIVATE / "SPLIT_MANIFEST.json", assembled["split_manifest"])
    write_private(PRIVATE / "DISJOINTNESS.json", assembled["disjointness"])
    write_private(PRIVATE / "SURFACE_DIAGNOSTICS.json", assembled["diagnostics"])
    write_private(PRIVATE / "PAIR_RECORDS.json", assembled["pair_records"])
    write_private(PRIVATE / "READINESS.json", assembled["readiness_receipt"])
    if assembled["stage_a_train_contract"] is not None:
        write_private(
            PRIVATE / "STAGE_A_TRAIN_CONTRACT.json",
            assembled["stage_a_train_contract"],
        )

    summary = {
        "BEST": "UNCHANGED",
        "best_sha256": BEST_SHA,
        "counts_by_provenance": assembled["diagnostics"]["diagnostics"][
            "counts_by_provenance"
        ],
        "counts_by_subtype": assembled["diagnostics"]["diagnostics"]["counts_by_subtype"],
        "dataset_sha256": assembled["dataset_sha256"],
        "design_rule": DESIGN_RULE,
        "disjointness_pass": assembled["disjointness"]["pass"],
        "hub_sha256": HUB_SHA,
        "n": assembled["dataset_manifest"]["n"],
        "ordinary_domain_coverage": assembled["diagnostics"]["diagnostics"][
            "ordinary_domain_coverage"
        ],
        "paired_positive_negative_count": assembled["diagnostics"]["diagnostics"][
            "paired_positive_negative_count"
        ],
        "pools": built["pools"],
        "readiness_state": readiness["state"],
        "receipt_sha256": assembled["readiness_receipt"]["receipt_sha256"],
        "shallow": assembled["shallow"],
        "shortcut": assembled["shortcut"],
        "spent_reserve_overlap": assembled["disjointness"]["spent_reserve_overlap_count"],
        "split_counts": assembled["diagnostics"]["diagnostics"]["counts_by_split"],
        "stage_a_train_contract": assembled["stage_a_train_contract"] is not None,
        "surface_rule": SURFACE_RULE,
        "train": False,
        "validation_subtype_counts": assembled["diagnostics"]["diagnostics"][
            "validation_subtype_counts"
        ],
    }
    write_private(PRIVATE / "SUMMARY.json", summary)

    if built["validation_errors"]:
        write_private(PRIVATE / "VALIDATION_ERRORS.json", built["validation_errors"][:200])
        fail(f"row validation errors:{len(built['validation_errors'])}")

    print(
        json.dumps(
            {
                "dataset_sha256": assembled["dataset_sha256"],
                "destination": str(PRIVATE),
                "missing_evidence": readiness.get("missing_evidence"),
                "n": assembled["dataset_manifest"]["n"],
                "readiness_state": readiness["state"],
                "receipt_sha256": assembled["readiness_receipt"]["receipt_sha256"],
                "spent_overlap": assembled["disjointness"]["spent_reserve_overlap_count"],
                "summary_sha256": sha256_text(canonical_json(summary)),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
