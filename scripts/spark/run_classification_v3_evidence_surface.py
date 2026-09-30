"""PREREGISTER v3 evidence gate and build HYPERLEX_V3_EVIDENCE_SURFACE_V1.

Fresh train/validation evidence surface only. Does not train Stage A, does not
create a v3 reserve, does not reuse the spent v2 reserve, and does not move BEST.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
PRIVATE = Path("/home/morpheus/hlx-private/classification-v3-evidence-surface-20260930")
EXPORT = Path(
    "/home/morpheus/hlx-private/classification-v2-train-forward-20260930/civilian.v0.7.hub.jsonl"
)
EXPORT_SHA = "0d8f4532f84ed9fade3fd4e69af0d1e0717fb1098d40754e95c0090d8282bfe1"
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926/ledger.json")
PRIOR_ROWS = Path(
    "/home/morpheus/hlx-private/classification-v2-train-ready-20260929/reserve-eval-rows.jsonl"
)
PRIOR_ROWS_SHA = "8c5276442ce37cf99fff597653a28917b3b4dc69ac87ad01f815fa458416ed36"
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
BEST_LINK = Path("/home/morpheus/.hyperlex/models/BEST")
INIT_FROM = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004"
)
SCHEMA_DIR = REPO / "specs/007-hyperlexical-model/schemas/classification-v3"

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
        pass
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
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def pin_inputs() -> None:
    if sha256_file(EXPORT) != EXPORT_SHA:
        fail("hub export digest mismatch")
    if sha256_file(PRIOR_ROWS) != PRIOR_ROWS_SHA:
        fail("sealed reserve-eval rows digest mismatch")
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
    mapping = {
        "evidence_example.v1": "evidence_example.v1.schema.json",
        "evidence_decision.v1": "evidence_decision.v1.schema.json",
        "family_candidates.v1": "family_candidates.v1.schema.json",
        "decision.v1": "decision.v1.schema.json",
    }
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
    from hyperlexical.classification_v3_evidence_gate import (
        CURRENT_STATE,
        FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX,
        FAMILY_EMISSION_PRECISION_MIN_AFTER_GATE,
        RULE,
    )
    from hyperlexical.classification_v3_evidence_surface import (
        SCHEMA_FILES,
        SURFACE_RULE,
        build_surface,
        load_spent_v2_reserve_ids,
        preregistration_contract,
        sha256_text,
        canonical_json,
    )

    pin_inputs()
    if CURRENT_STATE != "PREREGISTERED":
        fail(f"gate state not PREREGISTERED:{CURRENT_STATE}")
    schema_hashes = verify_schema_hashes(SCHEMA_FILES)
    prereg = preregistration_contract()
    if prereg["false_evidence_entry_rate_on_none_max"] != FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX:
        fail("primary gate drift")
    if prereg["family_emission_precision_min"] != FAMILY_EMISSION_PRECISION_MIN_AFTER_GATE:
        fail("secondary gate drift")

    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    write_private(
        PRIVATE / "PREREGISTRATION.json",
        {
            **prereg,
            "frozen_schema_sha256": schema_hashes,
            "rule": RULE,
            "surface_rule": SURFACE_RULE,
        },
    )

    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    reserve_rows = load_jsonl(PRIOR_ROWS)
    spent = load_spent_v2_reserve_ids(ledger=ledger, reserve_rows=reserve_rows)
    if len(spent) < 115:
        fail(f"spent reserve set too small:{len(spent)}")

    source_rows = load_jsonl(EXPORT)
    built = build_surface(
        source_rows,
        spent_reserve_ids=spent,
        ontology=ACTIVE_FAMILY_VOCABULARY,
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
    write_private(PRIVATE / "READINESS.json", assembled["readiness_receipt"])
    write_private(
        PRIVATE / "SUMMARY.json",
        {
            "BEST": "UNCHANGED",
            "best_sha256": BEST_SHA,
            "counts_by_provenance": assembled["diagnostics"]["diagnostics"][
                "counts_by_provenance"
            ],
            "counts_by_subtype": assembled["diagnostics"]["diagnostics"]["counts_by_subtype"],
            "dataset_sha256": assembled["dataset_sha256"],
            "disjointness_pass": assembled["disjointness"]["pass"],
            "export_sha256": EXPORT_SHA,
            "n": assembled["dataset_manifest"]["n"],
            "positive_family_support": assembled["diagnostics"]["diagnostics"][
                "positive_family_support"
            ],
            "pools": built["pools"],
            "readiness_state": readiness["state"],
            "receipt_sha256": assembled["readiness_receipt"]["receipt_sha256"],
            "spent_v2_reserve_overlap": assembled["disjointness"][
                "spent_v2_reserve_overlap_count"
            ],
            "split_counts": assembled["diagnostics"]["diagnostics"]["counts_by_split"],
            "surface_rule": SURFACE_RULE,
            "train": False,
            "validation_subtype_counts": assembled["diagnostics"]["diagnostics"][
                "validation_subtype_counts"
            ],
            "v3_reserve": None,
        },
    )

    # Fail closed only on builder hard errors; READY/PREREGISTERED both seal.
    if built["validation_errors"]:
        write_private(PRIVATE / "VALIDATION_ERRORS.json", built["validation_errors"][:200])
        fail(f"row validation errors:{len(built['validation_errors'])}")

    print(
        json.dumps(
            {
                "dataset_sha256": assembled["dataset_sha256"],
                "destination": str(PRIVATE),
                "n": assembled["dataset_manifest"]["n"],
                "readiness_state": readiness["state"],
                "receipt_sha256": assembled["readiness_receipt"]["receipt_sha256"],
                "spent_overlap": assembled["disjointness"]["spent_v2_reserve_overlap_count"],
                "summary_sha256": sha256_text(
                    canonical_json(
                        json.loads((PRIVATE / "SUMMARY.json").read_text(encoding="utf-8"))
                    )
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
