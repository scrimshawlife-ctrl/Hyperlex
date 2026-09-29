"""Seal the SELECT-006 source-design receipt. Does not fetch or train."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/morpheus/Hyperlex")
sys.path.insert(0, str(ROOT / "scripts/shadow"))

from hyperlexical.identity_ledger import IdentityLedger  # noqa: E402
from hyperlexical.select_006_efficiency_preservation import (  # noqa: E402
    BEST_SHA256,
    BEST_WEIGHTS,
    EPSILON,
    LEDGER_DIR,
    LEDGER_EVENTS_SHA256,
    LEDGER_PROJECTION_SHA256,
)
from hyperlexical.select_006_reserve_source_design_v2 import freeze_design  # noqa: E402

RECEIPT = (
    "/home/morpheus/hlx-private/exp-20260929-select-006/"
    "source-design-v2/SOURCE_DESIGN_V2.json"
)
PREREG = (
    "/home/morpheus/hlx-private/exp-20260929-select-006/spec-001/"
    "SELECT_006_PREREGISTRATION.json"
)
THRESHOLD = (
    "/home/morpheus/hlx-private/exp-20260929-select-006/spec-001/"
    "SELECT_006_THRESHOLD_AUTHORIZATION.json"
)
SETTLEMENT_LOG = Path(LEDGER_DIR) / "settlement" / "events.jsonl"
PREREG_SHA = "3692ac63425fcbd57e5fdc355a4e565d653ffc3c2a6703cfdda1fde7cc6404b8"
THRESHOLD_SHA = "91081de5f9b348102fa5d0359150f9aedca0d53e98c9f4275aeb127c9de3642c"
SETTLEMENT_SHA = "c048eb33cb5ac226437beb052bbb5fd6884e3f3297312776d2ae19d8c1bc316d"
MODULE = ROOT / "scripts/shadow/hyperlexical/select_006_reserve_source_design_v2.py"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sudo_sha256(path: str) -> str:
    completed = subprocess.run(
        ["sudo", "-n", "sha256sum", path],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        raise SystemExit(f"REFUSE: unreadable {path}")
    return completed.stdout.split()[0]


def main() -> None:
    status = subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain"], text=True)
    if status.strip():
        raise SystemExit("REFUSE: repository is dirty")
    if EPSILON != 0:
        raise SystemExit("REFUSE: EPSILON moved")
    if _sha256(Path(PREREG)) != PREREG_SHA or _sha256(Path(THRESHOLD)) != THRESHOLD_SHA:
        raise SystemExit("REFUSE: sealed spec hash moved")
    events = Path(LEDGER_DIR) / "events.jsonl"
    projection = Path(LEDGER_DIR) / "ledger.json"
    if _sha256(events) != LEDGER_EVENTS_SHA256 or _sha256(projection) != LEDGER_PROJECTION_SHA256:
        raise SystemExit("REFUSE: ledger hash moved")
    if _sha256(SETTLEMENT_LOG) != SETTLEMENT_SHA:
        raise SystemExit("REFUSE: settlement log moved")
    if _sudo_sha256(BEST_WEIGHTS) != BEST_SHA256:
        raise SystemExit("REFUSE: BEST moved")
    ledger = IdentityLedger.load(LEDGER_DIR)
    if ledger.active_reserve_records("HLX-EXP-2026-09-29-SELECT-006"):
        raise SystemExit("REFUSE: SELECT-006 reserve already exists")
    head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    receipt = freeze_design(
        RECEIPT,
        repository_commit=head,
        module_sha256=_sha256(MODULE),
    )
    sys.stdout.write(
        json.dumps(
            {
                "path": RECEIPT,
                "record_sha256": receipt["record_sha256"],
                "repository_commit": head,
                "rows_fetched": receipt["rows_fetched"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
