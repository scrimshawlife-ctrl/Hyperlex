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
)
from .training_routing import route_rows

DEFAULT_EXPORT = Path(
    "/home/morpheus/hlx-private/d1-spark-tree-20260924T213846Z/morph78-train-export.jsonl"
)
BEST_CONFIG = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/config.json"
)


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


def audit(export_path: Path | None = None, config_path: Path | None = None) -> dict:
    export = export_path or DEFAULT_EXPORT
    config = config_path or BEST_CONFIG
    rows = classify_train_rows(load_export(export))
    witness = loader_witness_from_config(config)
    report = readiness(rows, loader_status=witness["status"])
    report["loader_witness"] = witness
    report["n_classify_train"] = len(rows)
    report["export"] = str(export)
    return report


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    export = Path(args[0]) if args else DEFAULT_EXPORT
    report = audit(export)
    printable = {
        "state": report["state"],
        "ready": report["ready"],
        "blocker": report["blocker"],
        "missing_support": report["missing_support"],
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
    }
    print(json.dumps(printable, indent=2, sort_keys=True))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
