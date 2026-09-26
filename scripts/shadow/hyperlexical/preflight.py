"""U3 preflight. No Hub. No train.

``TRAINING_READY`` exists only when the scientific contract passed,
the decision rule is sealed, and ``admit_training_run`` returns
``ADMISSION_PASS``. An admission pass without a sealed decision rule
stays ``PREREGISTERED``. The trainer entrypoint with
``HLX_ADMISSION_ONLY=1`` stops after those gates.
"""

from __future__ import annotations

import json
import os
import platform
import sys
from pathlib import Path

from .admission import AdmissionError, admit_training_run
from .export import export_dataset

TRUNK = "answerdotai/ModernBERT-base"


def _print(report: dict) -> None:
    print(json.dumps(report, indent=2, sort_keys=True))


def _base() -> dict:
    trunk_raw = os.environ.get("HYPERLEX_TRUNK_DIR", "").strip()
    trunk = Path(trunk_raw) if trunk_raw else None
    experiment_id = os.environ.get("HLX_EXPERIMENT_ID", "").strip()
    return {
        "schema": "hyperlex.hyperlexical.preflight.v0.1",
        "machine": platform.machine(),
        "python": sys.version.split()[0],
        "allow_train": os.environ.get("HYPERLEX_ALLOW_TRAIN") == "1",
        "trunk_id": TRUNK,
        "trunk_dir": str(trunk) if trunk else None,
        "trunk_dir_exists": trunk.is_dir() if trunk else False,
        "trunk_config": (trunk / "config.json").is_file() if trunk else False,
        "name_gate": False,
        "brier": None,
        "experiment_id": experiment_id or None,
        "note": (
            "TRAINING_READY requires a sealed scientific contract, a sealed "
            "decision rule, and admit_training_run. Admission without a "
            "decision rule stays PREREGISTERED. It is not E2 and not a "
            "Hyperlexical name."
        ),
    }


def _paths() -> tuple[Path | None, Path | None]:
    trunk_raw = os.environ.get("HYPERLEX_TRUNK_DIR", "").strip()
    out_raw = os.environ.get("HYPERLEX_TRAIN_OUT", "").strip()
    trunk = Path(trunk_raw) if trunk_raw else None
    out = Path(out_raw) if out_raw else None
    return trunk, out


def main(argv=None) -> int:
    del argv
    trunk, out = _paths()
    include_live = os.environ.get("HYPERLEX_INCLUDE_LIVE") == "1"
    try:
        result = admit_training_run(
            include_live=include_live,
            live_store=None,
            export_dataset=export_dataset,
            trunk=trunk,
            out_dir=out,
        )
    except AdmissionError as exc:
        report = _base()
        report.update(exc.receipt)
        report["error"] = str(exc)
        report["ready_to_train"] = False
        report["status"] = "ADMISSION_FAIL"
        report["admission_result"] = "ADMISSION_FAIL"
        _print(report)
        return 2
    except SystemExit as exc:
        report = _base()
        report["error"] = str(exc)
        report["ready_to_train"] = False
        report["status"] = "ADMISSION_FAIL"
        report["admission_result"] = "ADMISSION_FAIL"
        report["holdout_admitted"] = False
        _print(report)
        return 2
    report = _base()
    report.update(result.receipt)
    if result.contract == "CONTROLLED_RESERVE" and not result.launch_armed:
        report["status"] = "NOT_READY"
        report["admission_result"] = "NOT_ARMED"
        report["ready_to_train"] = False
    _print(report)
    return 0 if result.ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
