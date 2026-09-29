"""Seal the SELECT-006 source-design companion artifacts. Does not fetch."""

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
from hyperlexical.select_006_reserve_source_design_v2 import (  # noqa: E402
    SPEC_SEAL_FAILURE,
    write_supporting_artifacts,
)

DESIGN = Path(
    "/home/morpheus/hlx-private/exp-20260929-select-006/source-design-v2/SOURCE_DESIGN_V2.json"
)
DESIGN_SHA = "7e9c323ea4fb6683f160f548f66bc517876cbb64d6fce55e1cf6a691333d0e99"
RECORD_SHA = "429af436c672ab20d048dcfcc2a3ff0fc933817a6b814a0e9481d3af25452419"
PREREG = Path(
    "/home/morpheus/hlx-private/exp-20260929-select-006/spec-001/SELECT_006_PREREGISTRATION.json"
)
THRESHOLD = Path(
    "/home/morpheus/hlx-private/exp-20260929-select-006/spec-001/"
    "SELECT_006_THRESHOLD_AUTHORIZATION.json"
)
SETTLEMENT_LOG = Path(LEDGER_DIR) / "settlement" / "events.jsonl"
PREREG_SHA = "3692ac63425fcbd57e5fdc355a4e565d653ffc3c2a6703cfdda1fde7cc6404b8"
THRESHOLD_SHA = "91081de5f9b348102fa5d0359150f9aedca0d53e98c9f4275aeb127c9de3642c"
SETTLEMENT_SHA = "c048eb33cb5ac226437beb052bbb5fd6884e3f3297312776d2ae19d8c1bc316d"


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
        raise SystemExit(f"{SPEC_SEAL_FAILURE}: unreadable {path}")
    return completed.stdout.split()[0]


def main() -> None:
    status = subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain"], text=True)
    if status.strip():
        raise SystemExit(f"{SPEC_SEAL_FAILURE}: repository is dirty")
    if EPSILON != 0:
        raise SystemExit(f"{SPEC_SEAL_FAILURE}: EPSILON moved")
    if _sha256(DESIGN) != DESIGN_SHA:
        raise SystemExit(f"{SPEC_SEAL_FAILURE}: source design file moved")
    if _sha256(PREREG) != PREREG_SHA or _sha256(THRESHOLD) != THRESHOLD_SHA:
        raise SystemExit(f"{SPEC_SEAL_FAILURE}: sealed spec hash moved")
    events = Path(LEDGER_DIR) / "events.jsonl"
    projection = Path(LEDGER_DIR) / "ledger.json"
    if _sha256(events) != LEDGER_EVENTS_SHA256 or _sha256(projection) != LEDGER_PROJECTION_SHA256:
        raise SystemExit(f"{SPEC_SEAL_FAILURE}: ledger hash moved")
    if _sha256(SETTLEMENT_LOG) != SETTLEMENT_SHA:
        raise SystemExit(f"{SPEC_SEAL_FAILURE}: settlement log moved")
    if _sudo_sha256(BEST_WEIGHTS) != BEST_SHA256:
        raise SystemExit(f"{SPEC_SEAL_FAILURE}: BEST moved")
    ledger = IdentityLedger.load(LEDGER_DIR)
    if ledger.active_reserve_records("HLX-EXP-2026-09-29-SELECT-006"):
        raise SystemExit(f"{SPEC_SEAL_FAILURE}: SELECT-006 reserve already exists")
    design = json.loads(DESIGN.read_text(encoding="utf-8"))
    if design.get("record_sha256") != RECORD_SHA:
        raise SystemExit(f"{SPEC_SEAL_FAILURE}: source design record moved")
    head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    hashes = write_supporting_artifacts(
        str(DESIGN.parent),
        design,
        design_file=str(DESIGN),
        repository_commit=head,
    )
    if _sha256(DESIGN) != DESIGN_SHA:
        raise SystemExit(f"{SPEC_SEAL_FAILURE}: source design bytes changed")
    sys.stdout.write(json.dumps(hashes, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
