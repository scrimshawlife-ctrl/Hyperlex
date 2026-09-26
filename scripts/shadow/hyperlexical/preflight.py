"""U3 preflight. No Hub. No train.

A controlled experiment is ``TRAINING_READY`` only when the same loader the
trainer uses has read the pinned export. File existence alone is not enough.
"""

from __future__ import annotations

import json
import os
import platform
import sys
from pathlib import Path

from .export import export_dataset, repo_root
from .holdout_guard import disjoint_report, operational_status, require_holdout_for_training
from .train_input import load_training_bundle, train_input_receipt

TRUNK = "answerdotai/ModernBERT-base"


def _trunk_ok(trunk: Path) -> bool:
    return bool(trunk) and trunk.is_dir() and (trunk / "config.json").is_file()


def _print(report: dict) -> None:
    print(json.dumps(report, indent=2, sort_keys=True))


def main(argv=None) -> int:
    del argv
    root = repo_root()
    allow = os.environ.get("HYPERLEX_ALLOW_TRAIN") == "1"
    trunk = Path(os.environ.get("HYPERLEX_TRUNK_DIR") or "")
    experiment_id = os.environ.get("HLX_EXPERIMENT_ID", "").strip()
    trunk_ready = _trunk_ok(trunk)
    base = {
        "schema": "hyperlex.hyperlexical.preflight.v0.1",
        "machine": platform.machine(),
        "python": sys.version.split()[0],
        "allow_train": allow,
        "trunk_id": TRUNK,
        "trunk_dir": str(trunk) if trunk else None,
        "trunk_dir_exists": trunk.is_dir() if trunk else False,
        "trunk_config": (trunk / "config.json").is_file() if trunk else False,
        "name_gate": False,
        "brier": None,
        "experiment_id": experiment_id or None,
    }
    try:
        bundle = load_training_bundle(
            root,
            include_live=False,
            live_store=None,
            export_dataset=export_dataset,
        )
    except SystemExit as exc:
        report = {
            **base,
            "ready_to_train": False,
            "status": "ADMISSION_FAIL",
            "error": str(exc),
            "data_sha256": None,
            "data_counts": None,
            "training_input_mode": None,
            "training_export_path": os.environ.get("HLX_TRAIN_EXPORT_PATH", "").strip() or None,
            "training_export_sha256_expected": os.environ.get("HLX_TRAIN_EXPORT_SHA256", "").strip() or None,
            "training_export_sha256_actual": None,
            "training_export_rows": None,
            "live_export_generation_enabled": False,
            "note": "ADMISSION FAIL. Training input was not bound. No live export was generated.",
        }
        _print(report)
        return 2
    proof = train_input_receipt(bundle)
    pinned_ok = (
        proof["training_input_mode"] == "PINNED_EXPORT"
        and proof["live_export_generation_enabled"] is False
        and proof["training_export_sha256_actual"]
        and proof["training_export_sha256_actual"] == proof["training_export_sha256_expected"]
    )
    holdout = {
        "holdout_admitted": False,
        "holdout_state": None,
        "holdout_operational_status": None,
        "holdout_experiment_id": None,
        "holdout_manifest_sha256": None,
    }
    holdout_error = None
    spec = None
    if os.environ.get("HLX_ALLOW_NO_HOLDOUT") == "1":
        holdout_error = "ADMISSION FAIL: HLX_ALLOW_NO_HOLDOUT is set"
    elif experiment_id and allow and pinned_ok:
        try:
            spec = require_holdout_for_training()
        except SystemExit as exc:
            holdout_error = str(exc)
            spec = None
        if spec is not None and spec.manifests:
            holdout = {
                "holdout_admitted": True,
                "holdout_state": spec.manifests[0].get("status"),
                "holdout_operational_status": operational_status(spec.manifests[0]),
                "holdout_experiment_id": spec.manifests[0].get("experiment_id"),
                "holdout_manifest_sha256": ",".join(
                    str(item.get("sha256")) for item in spec.manifests
                ),
            }
        elif holdout_error is None:
            holdout_error = "ADMISSION FAIL: no holdout manifest"
    disjoint = {
        "holdout_train_row_id_overlap": None,
        "holdout_train_text_hash_overlap": None,
        "holdout_filter_training_rows_removed": None,
        "holdout_training_disjoint": None,
    }
    if spec is not None:
        disjoint = disjoint_report(bundle["rows"], spec)
        if experiment_id and not disjoint["holdout_training_disjoint"]:
            holdout_error = (
                "ADMISSION FAIL: holdout would remove "
                f"{disjoint['holdout_filter_training_rows_removed']} pinned training rows"
            )
            holdout["holdout_admitted"] = False
    if experiment_id:
        ready = bool(
            allow
            and trunk_ready
            and pinned_ok
            and holdout["holdout_admitted"]
            and not holdout_error
        )
        status = "ADMISSION_FAIL" if holdout_error else ("TRAINING_READY" if ready else "NOT_READY")
    else:
        ready = bool(allow and trunk_ready)
        status = None
    report = {
        **base,
        "data_sha256": bundle.get("sha256"),
        "data_counts": bundle.get("counts"),
        "ready_to_train": ready,
        "status": status,
        "training_input_mode": proof["training_input_mode"],
        "training_export_path": proof["training_export_path"],
        "training_export_sha256_expected": proof["training_export_sha256_expected"],
        "training_export_sha256_actual": proof["training_export_sha256_actual"],
        "training_export_rows": proof["training_export_rows"],
        "live_export_generation_enabled": proof["live_export_generation_enabled"],
        **holdout,
        **disjoint,
        "note": (
            "ready_to_train is a gate check, not E2 and not a Hyperlexical name. "
            "TRAINING_READY for a controlled experiment requires the trainer loader "
            "to consume the pinned export and require_holdout_for_training to admit."
        ),
    }
    if holdout_error:
        report["error"] = holdout_error
    _print(report)
    if not report["ready_to_train"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
