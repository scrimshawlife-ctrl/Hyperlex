"""One readiness audit for Classification v2. Does not train and does not move BEST."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .classification_v2 import (
    BEST_REFERENCE_SHA256,
    V1_HEAD,
    map_family_rows,
    readiness,
    reserve_positive_census,
)
from .training_routing import route_rows

DEFAULT_EXPORT = Path(
    "/home/morpheus/hlx-private/classification-v2-acquire-20260929/civilian.v0.1.jsonl"
)
BEST_CONFIG = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/config.json"
)
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926/ledger.json")


def load_export(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def classify_train_rows(rows: list[dict]) -> list[dict]:
    routed, _accounting = route_rows(rows)
    return list(routed["classify"]["train"])


def loader_witness_from_config(path: Path) -> dict:
    """Label witness from the readable production config. Tensors stay unread here."""
    config = json.loads(path.read_text(encoding="utf-8"))
    labels = [config["id2label"][str(index)] for index in range(len(config["id2label"]))]
    if tuple(labels) != V1_HEAD:
        return {"status": "FAIL", "reason": "v1_label_order_mismatch", "labels": labels}
    hidden = 4
    source_weight = [[float(index + 1)] * hidden for index, _name in enumerate(labels)]
    source_bias = [float(index + 1) for index, _name in enumerate(labels)]
    mapped = map_family_rows(labels, source_weight, source_bias)
    return {
        "status": mapped["status"],
        "mapped_families": mapped["mapped_families"],
        "zero_initialized_families": mapped["zero_initialized_families"],
        "legacy_not_mapped": mapped["legacy_not_mapped"],
        "legacy_remap": mapped["legacy_remap"],
        "best_reference_sha256": BEST_REFERENCE_SHA256,
        "best_bytes_mutated": False,
        "label_source": str(path),
    }


def audit(export_path: Path | None = None, config_path: Path | None = None, prototype_witness: Path | None = None) -> dict:
    from .classification_v2_prototype import (
        assess_witness,
        definition_string_report,
        validation_family_support,
    )
    from .holdout_guard import normalized_text_sha256
    from .identity_ledger import IdentityLedger, derived_state
    from .training_routing import route_rows

    export = export_path or DEFAULT_EXPORT
    config = config_path or BEST_CONFIG
    loaded = load_export(export)
    rows = classify_train_rows(loaded)
    witness = loader_witness_from_config(config)
    identity_state = {}
    ledger_dir = LEDGER.parent
    if (ledger_dir / "events.jsonl").is_file():
        ledger = IdentityLedger.load(ledger_dir)
        for row in loaded:
            if row.get("task") != "classify" or row.get("split") not in {"train", "val"}:
                continue
            digest = normalized_text_sha256(str(row.get("text") or ""))
            record = ledger.identity(digest)
            if record is not None:
                identity_state[digest] = derived_state(record)
    prototype_report = None
    if prototype_witness is not None and prototype_witness.is_file():
        prototype_report = assess_witness(json.loads(prototype_witness.read_text(encoding="utf-8")))
    report = readiness(
        rows,
        loader_status=witness["status"],
        prototype_report=prototype_report,
        validation_report=validation_family_support(route_rows(loaded)[0]["classify"]["val"], identity_state=identity_state),
        definition_report=definition_string_report(loaded),
    )
    report["loader_witness"] = witness
    report["n_classify_train"] = len(rows)
    report["export"] = str(export)
    if LEDGER.is_file():
        ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
        report["reserve_exclusion"] = reserve_positive_census(ledger.get("identities") or [])
        report["reserve_exclusion"]["ledger"] = str(LEDGER)
    return report


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    export = Path(args[0]) if args else DEFAULT_EXPORT
    prototype_witness = Path(args[1]) if len(args) > 1 else None
    report = audit(export, prototype_witness=prototype_witness)
    printable = {
        "state": report["state"],
        "ready": report["ready"],
        "blocker": report["blocker"],
        "missing_support": report["missing_support"],
        "blockers": report.get("blockers"),
        "deficient_validation": report.get("deficient_validation"),
        "validation_support": report.get("validation_support"),
        "below_preferred_validation": report.get("below_preferred_validation"),
        "exact_copy_families": report.get("exact_copy_families"),
        "prototype_families": report.get("prototype_families"),
        "prototype_source_counts": report.get("prototype_source_counts"),
        "witness_sha256": report.get("witness_sha256"),
        "target_norm": report.get("target_norm"),
        "checks": report.get("checks"),
        "n_classify_train": report["n_classify_train"],
        "mapped_families": report["loader_witness"]["mapped_families"],
        "zero_initialized_families": report["loader_witness"]["zero_initialized_families"],
        "provenance_weights": report["provenance_weights"],
        "applicability_weights": report["applicability_weights"],
        "family_weights": report["family_weights"],
        "support": report["audit"]["families"],
        "legacy_excluded": report["audit"]["legacy_excluded"],
        "none": report["audit"]["none"],
        "moves_best": report["moves_best"],
        "reserve_exclusion": report.get("reserve_exclusion"),
    }
    print(json.dumps(printable, indent=2, sort_keys=True))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
