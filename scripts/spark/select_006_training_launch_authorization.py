"""Seal the SELECT-006 training-launch authorization. Does not train."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from hyperlexical.select_006_efficiency_preservation import BEST_WEIGHTS, sha256_file
from hyperlexical.select_006_training_launch_authorization import (
    FORBIDDEN_OUTPUTS,
    LEDGER_EVENTS_SHA256,
    LEDGER_PROJECTION_SHA256,
    SEAL_FAILURE,
    LaunchAuthorizationError,
    observe_launch_authorization,
    seal_training_launch_authorization,
)

TARGET = Path(
    "/home/morpheus/hlx-private/exp-20260929-select-006/"
    "launch-authorization-001/TRAINING_LAUNCH_AUTHORIZATION.json"
)
LEDGER_EVENTS = Path("/home/morpheus/hlx-private/eval-reserve-20260926/events.jsonl")
LEDGER_PROJECTION = Path("/home/morpheus/hlx-private/eval-reserve-20260926/ledger.json")


def _snapshot() -> dict[str, str]:
    return {
        "best_sha256": sha256_file(Path(BEST_WEIGHTS)),
        "ledger_events_sha256": sha256_file(LEDGER_EVENTS),
        "ledger_projection_sha256": sha256_file(LEDGER_PROJECTION),
    }


def main() -> None:
    before = _snapshot()
    if before["ledger_events_sha256"] != LEDGER_EVENTS_SHA256:
        raise LaunchAuthorizationError(SEAL_FAILURE, "ledger events drifted before seal")
    if before["ledger_projection_sha256"] != LEDGER_PROJECTION_SHA256:
        raise LaunchAuthorizationError(SEAL_FAILURE, "ledger projection drifted before seal")
    evidence = observe_launch_authorization()
    record = seal_training_launch_authorization(str(TARGET), evidence)
    after = _snapshot()
    if before != after:
        TARGET.unlink()
        raise LaunchAuthorizationError(SEAL_FAILURE, "ledger or BEST changed during seal")
    for output in FORBIDDEN_OUTPUTS:
        if output.exists():
            TARGET.unlink()
            raise LaunchAuthorizationError(SEAL_FAILURE, f"training output appeared: {output}")
    report = {
        "authorization_sha256": sha256_file(TARGET),
        "best_sha256_after": after["best_sha256"],
        "best_sha256_before": before["best_sha256"],
        "epochs": record["epochs"],
        "gradient_steps": record["gradient_steps"],
        "ledger_events_sha256_after": after["ledger_events_sha256"],
        "ledger_events_sha256_before": before["ledger_events_sha256"],
        "ledger_projection_sha256_after": after["ledger_projection_sha256"],
        "ledger_projection_sha256_before": before["ledger_projection_sha256"],
        "ledger_replay": record["ledger"]["replay"],
        "next_legal_transition": record["next_legal_transition"],
        "operator_decision": record["operator_decision"],
        "optimizer_constructed": record["optimizer_constructed"],
        "path": str(TARGET),
        "reserve_active": record["reserve"]["active_select_006_eval_reserve"],
        "slice_counts": record["reserve"]["slice_counts"],
        "state": record["state"],
        "training_launch_authorized": record["training_launch_authorized"],
        "training_started": record["training_started"],
        "weights_mutated_by_training": record["weights_mutated_by_training"],
    }
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
