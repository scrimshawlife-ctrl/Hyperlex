"""Seal SELECT-006 governance. Does not train, score, or move BEST."""

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
    CANDIDATE_CONFIG,
    CONTROL_CONFIG,
    EVALUATION_RESERVE_STATE_UNRESOLVED,
    EXPORT_PATH,
    EXPORT_SHA256,
    LEDGER_DIR,
    LEDGER_EVENTS_SHA256,
    LEDGER_PROJECTION_SHA256,
    SELECT_005_ID,
    SPEC_DIR,
    SPEC_SEAL_FAILURE,
    TRUNK_DIR,
    TRUNK_SHA256,
    VOCAB_EXPANSION_SPEC_INCOMPLETE,
    WARM_START_PIN_MISMATCH,
    WARM_START_SHA256,
    WARM_START_WEIGHTS,
    evaluation_reserve_decision,
    seal_specification,
    vocabulary_expansion_pin,
)

WITNESS = ROOT / "scripts/spark/select_006_vocab_witness.py"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sudo_sha256(path: str, code: str) -> str:
    completed = subprocess.run(
        ["sudo", "-n", "sha256sum", path],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        raise SystemExit(f"{code}: unreadable {path}")
    return completed.stdout.split()[0]


def _witness(left: str, right: str) -> dict:
    completed = subprocess.run(
        ["sudo", "-n", "python3", str(WITNESS), left, right],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "witness failed").strip()
        raise SystemExit(f"{VOCAB_EXPANSION_SPEC_INCOMPLETE}: {detail}")
    return json.loads(completed.stdout)


def _reserve_observation() -> dict:
    events = Path(LEDGER_DIR) / "events.jsonl"
    projection = Path(LEDGER_DIR) / "ledger.json"
    if _sha256(events) != LEDGER_EVENTS_SHA256 or _sha256(projection) != LEDGER_PROJECTION_SHA256:
        raise SystemExit(f"{EVALUATION_RESERVE_STATE_UNRESOLVED}: ledger hash")
    ledger = IdentityLedger.load(LEDGER_DIR)
    counts = ledger.active_reserve_counts(SELECT_005_ID)
    expected = evaluation_reserve_decision()["select_005_slice_counts"]
    if counts != expected or len(ledger.active_reserve_records(SELECT_005_ID)) != 78:
        raise SystemExit(f"{EVALUATION_RESERVE_STATE_UNRESOLVED}: SELECT-005 reserve")
    if ledger.active_reserve_records("HLX-EXP-2026-09-29-SELECT-006"):
        raise SystemExit(f"{EVALUATION_RESERVE_STATE_UNRESOLVED}: SELECT-006 reserve exists")
    return {
        "ledger_events_sha256": LEDGER_EVENTS_SHA256,
        "ledger_projection_sha256": LEDGER_PROJECTION_SHA256,
        "select_005_active_count": 78,
        "select_005_slice_counts": counts,
        "select_006_active_count": 0,
    }


def main() -> None:
    status = subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain"], text=True)
    if status.strip():
        raise SystemExit(f"{SPEC_SEAL_FAILURE}: repository is dirty")
    head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    warm = _sudo_sha256(WARM_START_WEIGHTS, WARM_START_PIN_MISMATCH)
    if warm != WARM_START_SHA256:
        raise SystemExit(f"{WARM_START_PIN_MISMATCH}: {warm}")
    best = _sudo_sha256(BEST_WEIGHTS, SPEC_SEAL_FAILURE)
    if best != BEST_SHA256:
        raise SystemExit(f"{SPEC_SEAL_FAILURE}: BEST pin")
    export = _sha256(Path(EXPORT_PATH))
    trunk = _sha256(Path(TRUNK_DIR) / "model.safetensors")
    if export != EXPORT_SHA256 or trunk != TRUNK_SHA256:
        raise SystemExit(f"{SPEC_SEAL_FAILURE}: export or trunk pin")
    control = _witness(WARM_START_WEIGHTS.rsplit("/", 1)[0] + "/config.json", CONTROL_CONFIG)
    candidate = _witness(WARM_START_WEIGHTS.rsplit("/", 1)[0] + "/config.json", CANDIDATE_CONFIG)
    pin = vocabulary_expansion_pin()
    comparable = (
        "mapped_existing_fillers",
        "mapped_existing_roles",
        "new_role_names_in_sorted_order",
        "newly_initialized_fillers",
        "newly_initialized_roles",
        "role_order_ok",
        "skipped_warm_start_only",
        "target_filler_count",
        "target_role_count",
        "warm_start_filler_count",
        "warm_start_only_roles",
        "warm_start_role_count",
    )
    expected_filler = pin["filler_expansion"]
    for observed in (control, candidate):
        if not observed.get("configs_agree") or not observed.get("role_order_ok"):
            raise SystemExit(f"{VOCAB_EXPANSION_SPEC_INCOMPLETE}: ordering")
        if observed["new_role_names_in_sorted_order"] != pin["new_role_names_in_sorted_order"]:
            raise SystemExit(f"{VOCAB_EXPANSION_SPEC_INCOMPLETE}: role names")
        for key in comparable:
            if key == "role_order_ok":
                wanted = True
            elif key in expected_filler:
                wanted = expected_filler[key]
            elif key in pin:
                wanted = pin[key]
            else:
                raise SystemExit(f"{VOCAB_EXPANSION_SPEC_INCOMPLETE}: unpinned {key}")
            if observed[key] != wanted:
                raise SystemExit(f"{VOCAB_EXPANSION_SPEC_INCOMPLETE}: {key}")
    if control["new_role_names_in_sorted_order"] != candidate["new_role_names_in_sorted_order"]:
        raise SystemExit(f"{VOCAB_EXPANSION_SPEC_INCOMPLETE}: arm configs disagree")
    observations = {
        "best_sha256": best,
        "candidate_config": CANDIDATE_CONFIG,
        "configs_agree": True,
        "control_config": CONTROL_CONFIG,
        "export_sha256": export,
        "filler_expansion": pin["filler_expansion"],
        "mapped_existing_roles": 10,
        "new_role_names_in_sorted_order": pin["new_role_names_in_sorted_order"],
        "newly_initialized_roles": 3,
        "role_order_ok": True,
        "target_role_count": 13,
        "trunk_sha256": trunk,
        "warm_start_only_roles": 0,
        "warm_start_role_count": 10,
        "warm_start_sha256": warm,
        **_reserve_observation(),
    }
    hashes = seal_specification(
        SPEC_DIR,
        observations=observations,
        repository_head=head,
        repository_dirty=False,
    )
    sys.stdout.write(json.dumps({"repository_commit": head, "sha256": hashes}, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
