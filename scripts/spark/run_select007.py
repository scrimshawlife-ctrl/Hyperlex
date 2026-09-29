"""Run HLX-EXP-2026-09-29-SELECT-007. Sampling is the only arm difference."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/morpheus/Hyperlex")
sys.path.insert(0, str(ROOT / "scripts/shadow"))

from hyperlexical.experiment_lifecycle import (  # noqa: E402
    begin_run,
    preregister,
    preflight,
    settle,
)
from hyperlexical.select_007 import (  # noqa: E402
    BEST_SHA256,
    CAP,
    EXPERIMENT_ID,
    INFERRED_NONE,
    LEDGER_EVENTS_BEFORE,
    LOADER_WITNESS_SHA256,
    OBSERVED_NONE,
    RULE,
    SELECT_006_ID,
    TRAINING_DATA_SHA256,
    WARM_START_SHA256,
    canonical_json,
    evaluate_acceptance,
    preregistration,
    preregistration_hash,
)

IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
PRIVATE = Path("/home/morpheus/hlx-private/exp-20260929-select-007")
RESERVE = PRIVATE / "reserve-001"
RUN = PRIVATE / "run-001"
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
EXPORT = Path("/home/morpheus/hlx-private/d1-spark-tree-20260924T213846Z/morph78-train-export.jsonl")
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
TRUNK_SHA = "340ac08b74eef0d7bdec2d7981a6a3d4249bf0e6aab60634b72ad02c2b8023a9"
WARM = Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph65")
BEST = Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/model.safetensors")
CONTROL_OUT = Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select007-control")
CANDIDATE_OUT = Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select007")
SPEC = ROOT / "specs/007-hyperlexical-model/select-007.md"
RESERVE_MD = ROOT / "specs/007-hyperlexical-model/evaluation-reserve.md"

SHARED = {
    "HLX_EXPERIMENT_ID": EXPERIMENT_ID,
    "HLX_SCIENTIFIC_VARIABLE": "classify_sampling",
    "HLX_SELECT_METRIC": "classify_macro_f1_nonnone",
    "HLX_TRAIN_EXPORT_PATH": str(EXPORT),
    "HLX_TRAIN_EXPORT_ROWS": "9150",
    "HLX_TRAIN_EXPORT_SHA256": TRAINING_DATA_SHA256,
    "HYPERLEX_EARLY_STOP": "1",
    "HYPERLEX_EARLY_STOP_MIN_EPOCHS": "4",
    "HYPERLEX_EARLY_STOP_PATIENCE": "4",
    "HYPERLEX_FILLER_FILTER": "strict",
    "HYPERLEX_INIT_EXPAND_VOCAB": "1",
    "HYPERLEX_INIT_FROM": str(WARM),
    "HYPERLEX_LAST_TRAINABLE": "2",
    "HYPERLEX_TRAIN_BATCH": "8",
    "HYPERLEX_TRAIN_EPOCHS": "12",
    "HYPERLEX_TRAIN_LR": "2e-5",
    "HYPERLEX_TRUNK_DIR": str(TRUNK),
    "HYPERLEX_UNBIND_CURRICULUM": "0",
    "HYPERLEX_UNBIND_EVERY_N": "1",
    "HYPERLEX_UNBIND_LOSS_WEIGHT": "1.0",
    "HYPERLEX_UNBIND_PRIMARY": "mixed",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sudo_sha256(path: Path) -> str:
    completed = subprocess.run(
        ["sudo", "-n", "sha256sum", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.split()[0]


def write_json(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = canonical_json(payload)
    path.write_text(text, encoding="utf-8")
    os.chmod(path, 0o600)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fail(code: str, detail: str) -> None:
    raise SystemExit(f"{code}: {detail}")


def docker(env: dict[str, str], args: list[str], log_path: Path, name: str) -> int:
    command = [
        "docker", "run", "--rm", "--gpus", "all", "--name", name,
        "-v", "/home/morpheus/Hyperlex:/home/morpheus/Hyperlex",
        "-v", "/home/morpheus/hlx-private:/home/morpheus/hlx-private",
        "-v", "/home/morpheus/.hyperlex:/home/morpheus/.hyperlex",
        "-w", "/home/morpheus/Hyperlex",
        "-e", "HOME=/home/morpheus",
        "-e", "HF_HUB_OFFLINE=1",
        "-e", "PYTHONDONTWRITEBYTECODE=1",
        "-e", "PYTHONPATH=/home/morpheus/Hyperlex/scripts/shadow",
        "-e", "PYTHONUNBUFFERED=1",
        "-e", "TRANSFORMERS_OFFLINE=1",
    ]
    for key, value in sorted(env.items()):
        command.extend(["-e", f"{key}={value}"])
    command.extend([IMAGE, *args])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, check=False)
    return completed.returncode


def last_json(text: str) -> dict:
    decoder = json.JSONDecoder()
    start = text.rfind("\n{")
    while start >= 0:
        try:
            payload, _end = decoder.raw_decode(text[start + 1 :])
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict) and (
            "expanded_loader_witness_sha256" in payload or "global_steps" in payload
        ):
            return payload
        start = text.rfind("\n{", 0, start)
    fail("TELEMETRY_PLAN_INVALID", "trainer log has no receipt")
    raise AssertionError("fail")


def arm_file(arm: str) -> dict[str, str]:
    payload = dict(SHARED)
    if arm == "control":
        payload["HYPERLEX_CLASSIFY_SAMPLING"] = "uncapped"
    elif arm == "candidate":
        payload["HYPERLEX_CLASSIFY_SAMPLING"] = f"{RULE}:{CAP}"
    else:
        fail("PREREGISTRATION_MISMATCH", arm)
    return payload


def process_env(arm: str, out: Path) -> dict[str, str]:
    env = arm_file(arm)
    env.update(
        {
            "HLX_BASELINE_ENV": str(RUN / "BASELINE_ENV.json"),
            "HLX_BEST_SHA256": BEST_SHA256,
            "HLX_BEST_WEIGHTS": str(BEST),
            "HLX_CANDIDATE_ENV": str(RUN / "CANDIDATE_ENV.json"),
            "HLX_EVAL_RESERVE_LEDGER": str(LEDGER),
            "HLX_RESERVE_BINDING": str(RESERVE / "RESERVE_BINDING.json"),
            "HLX_SCHEDULE_ARM": arm,
            "HLX_THRESHOLD_AUTHORIZATION": str(RUN / "THRESHOLD_AUTHORIZATION.json"),
            "HLX_TRUNK_SHA256": TRUNK_SHA,
            "HYPERLEX_ALLOW_TRAIN": "1",
            "HYPERLEX_EXPORT_DIR": str(RUN / f"{arm}-export"),
            "HYPERLEX_TRAIN_OUT": str(out),
        }
    )
    return env


def ensure_reserve() -> None:
    script = ROOT / "scripts/spark/select_007_reserve.py"
    if not (RESERVE / "RAW_CANDIDATES.jsonl").is_file():
        code = subprocess.run([sys.executable, str(script), "fetch"], check=False).returncode
        if code != 0:
            fail("RESERVE_INVALID", f"fetch exited {code}")
    if not (RESERVE / "RESERVE_MANIFEST.json").is_file():
        code = subprocess.run([sys.executable, str(script), "settle"], check=False).returncode
        if code != 0:
            fail("RESERVE_INVALID", f"settle exited {code}")


def sampling_rows(out: Path) -> list[dict]:
    path = out / "classify-sampling.jsonl"
    if not path.is_file():
        fail("TELEMETRY_PLAN_INVALID", f"{out.name} sampling log is absent")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate_sampling(arm: str, rows: list[dict]) -> None:
    expected_rule = "uncapped" if arm == "control" else RULE
    expected_count = INFERRED_NONE if arm == "control" else CAP
    if not rows:
        fail("TELEMETRY_PLAN_INVALID", f"{arm} recorded no epochs")
    for row in rows:
        if row.get("rule") != expected_rule:
            fail("EXPERIMENT_INVALID", f"{arm} sampling rule {row.get('rule')}")
        if row.get("inferred_none_selected") != expected_count:
            fail("EXPERIMENT_INVALID", f"{arm} inferred-none count {row.get('inferred_none_selected')}")
        if row.get("observed_none") != OBSERVED_NONE:
            fail("EXPERIMENT_INVALID", f"{arm} observed-none count")
        if row.get("inferred_none_population") != INFERRED_NONE:
            fail("EXPERIMENT_INVALID", f"{arm} inferred-none population")
        hashes = row.get("selected_identity_sha256")
        if not isinstance(hashes, list) or len(hashes) != expected_count:
            fail("EXPERIMENT_INVALID", f"{arm} identity hash list")


def validate_shared(control: dict, candidate: dict) -> None:
    for key in ("data_sha256", "init_from", "last_trainable", "unbind_loss_weight"):
        if control.get(key) != candidate.get(key):
            fail("EXPERIMENT_INVALID", f"{key} differs")
    if control.get("data_sha256") != TRAINING_DATA_SHA256:
        fail("DATA_INTEGRITY_FAILURE", "training export")
    if control.get("init_from") != str(WARM):
        fail("DATA_INTEGRITY_FAILURE", "warm start")
    if control.get("last_trainable") != 2:
        fail("EXPERIMENT_INVALID", "trainable layers")
    left = control.get("training_schedule") or {}
    right = candidate.get("training_schedule") or {}
    if left != right:
        fail("EXPERIMENT_INVALID", "schedule differs")
    if left.get("max_epochs") != 12 or left.get("patience") != 4 or left.get("minimum_epochs") != 4:
        fail("EXPERIMENT_INVALID", "schedule is not the default")
    if left.get("improvement") != "strict" or left.get("restore_best") is not True:
        fail("EXPERIMENT_INVALID", "restore-best or improvement")
    if left.get("ties") != "keep_earlier":
        fail("EXPERIMENT_INVALID", "ties")
    if control.get("classify_sampling", {}).get("policy") != "uncapped":
        fail("EXPERIMENT_INVALID", "control policy")
    if candidate.get("classify_sampling", {}).get("policy") != f"{RULE}:{CAP}":
        fail("EXPERIMENT_INVALID", "candidate policy")


def restored(out: Path, receipt: dict) -> None:
    primary = sudo_sha256(out / "model.safetensors")
    best = sudo_sha256(out / "best" / "model.safetensors")
    if primary != best:
        fail("EXPERIMENT_INVALID", f"{out.name} did not restore best")
    if receipt.get("best_checkpoint_sha256") not in (None, best):
        fail("EXPERIMENT_INVALID", f"{out.name} best hash")


def witness() -> dict:
    dest = RUN / "LOADER_WITNESS.json"
    if dest.is_file():
        return read_json(dest)
    if CONTROL_OUT.exists():
        fail("TRAINING_INITIALIZATION_FAILURE", "control output exists before the witness")
    env = process_env("control", CONTROL_OUT)
    env["HLX_STOP_BEFORE_OPTIMIZER"] = "1"
    code = docker(env, ["python", "-m", "hyperlexical.train", "--run"], RUN / "witness.log", "hlx-select007-witness")
    if CONTROL_OUT.exists():
        fail("TRAINING_INITIALIZATION_FAILURE", "witness created the output directory")
    if code != 0:
        fail("LOADER_INVALID", f"witness exited {code}")
    payload = last_json((RUN / "witness.log").read_text(encoding="utf-8"))
    if payload.get("expanded_loader_witness_sha256") != LOADER_WITNESS_SHA256:
        fail("LOADER_INVALID", "witness hash")
    if payload.get("stopped_before_optimizer") is not True or payload.get("training_started") is not False:
        fail("LOADER_INVALID", "witness ran the optimizer")
    if payload.get("execution_loader_status") != "ZERO_INIT_LOADER_VERIFIED":
        fail("LOADER_INVALID", "loader status")
    write_json(dest, payload)
    return payload


def train(arm: str, out: Path) -> dict:
    receipt_path = out / "train-receipt.json"
    if receipt_path.is_file():
        return read_json(receipt_path)
    env = process_env(arm, out)
    code = docker(env, ["python", "-m", "hyperlexical.train", "--run"], RUN / f"{arm}-train.log", f"hlx-select007-{arm}")
    if out.exists():
        subprocess.run(["sudo", "-n", "chmod", "-R", "a+rX", str(out)], check=False)
    if code != 0:
        fail("TRAINING_RUNTIME_FAILURE", f"{arm} exited {code}")
    if not receipt_path.is_file():
        fail("TELEMETRY_PLAN_INVALID", f"{arm} receipt is absent")
    return read_json(receipt_path)


def score(arm: str, out: Path) -> dict:
    dest = RUN / f"{arm}-reserve-metrics.json"
    if dest.is_file():
        return read_json(dest)
    code = docker(
        {"HYPERLEX_TRUNK_DIR": str(TRUNK)},
        ["python", "-m", "hyperlexical.select_007_reserve_eval", str(out), str(dest)],
        RUN / f"{arm}-score.log",
        f"hlx-select007-{arm}-score",
    )
    if dest.exists():
        subprocess.run(["sudo", "-n", "chmod", "a+r", str(dest)], check=False)
    if code != 0 or not dest.is_file():
        log = (RUN / f"{arm}-score.log").read_text(encoding="utf-8") if (RUN / f"{arm}-score.log").is_file() else ""
        if "METRIC_NONCOMPUTABLE" in log:
            fail("METRIC_NONCOMPUTABLE", arm)
        fail("RESERVE_SCORING_FAILURE", f"{arm} exited {code}")
    return read_json(dest)


def ready_record(stamp: str) -> dict:
    definition = preregistration()
    digest = preregistration_hash(definition)
    write_json(RUN / "PREREGISTRATION.json", definition)
    if preregistration_hash(read_json(RUN / "PREREGISTRATION.json")) != digest:
        fail("PREREGISTRATION_MISMATCH", "preregistration hash")
    record = preregister(EXPERIMENT_ID, definition)
    manifest = read_json(RESERVE / "RESERVE_MANIFEST.json")
    if manifest.get("experiment_id") != EXPERIMENT_ID:
        fail("RESERVE_INVALID", "manifest experiment")
    observations = {}
    files = {
        "preregistration": RUN / "PREREGISTRATION.json",
        "reserve": RESERVE / "RESERVE_MANIFEST.json",
        "isolation": RESERVE / "ISOLATION_REPORT.json",
        "provenance": RESERVE / "PROVENANCE_REPORT.json",
        "metric_computability": RESERVE / "METRIC_COMPUTABILITY.json",
        "loader": RUN / "LOADER_WITNESS.json",
        "schedule": RUN / "PREREGISTRATION.json",
        "telemetry_plan": RUN / "PREREGISTRATION.json",
        "thresholds": RUN / "THRESHOLD_AUTHORIZATION.json",
        "training_data": EXPORT,
        "warm_start": WARM / "model.safetensors",
        "environment": RUN / "CANDIDATE_ENV.json",
        "ledger": LEDGER / "events.jsonl",
        "operator_authorization": RUN / "OPERATOR_AUTHORIZATION.json",
    }
    for key, path in files.items():
        observations[key] = {
            "artifact": str(path),
            "decision": "AUTHORIZE" if key == "operator_authorization" else None,
            "inferred_from": None,
            "ok": True,
            "sha256": sha256_file(path) if key != "warm_start" else sudo_sha256(path),
            "timestamp": stamp,
        }
    if observations["training_data"]["sha256"] != TRAINING_DATA_SHA256:
        observations["training_data"]["ok"] = False
        observations["training_data"]["blocking_reason"] = "DATA_INTEGRITY_FAILURE"
    if observations["warm_start"]["sha256"] != WARM_START_SHA256:
        observations["warm_start"]["ok"] = False
    updated = preflight(record, observations)
    write_json(RUN / "LIFECYCLE.json", updated)
    if updated["state"] != "READY":
        fail("PREREGISTRATION_MISMATCH", json.dumps(updated.get("blocking_reasons")))
    return updated


def settle_run(control_receipt: dict, candidate_receipt: dict, control_metrics: dict, candidate_metrics: dict, running: dict) -> dict:
    from hyperlexical.identity_ledger import IdentityLedger

    ledger = IdentityLedger.load(LEDGER)
    if len(ledger.active_reserve_records(SELECT_006_ID)) != 37:
        fail("LEDGER_REPLAY_FAILURE", "SELECT-006 reserve changed")
    valid = True
    reason = None
    try:
        validate_shared(control_receipt, candidate_receipt)
        validate_sampling("control", sampling_rows(CONTROL_OUT))
        validate_sampling("candidate", sampling_rows(CANDIDATE_OUT))
        restored(CONTROL_OUT, control_receipt)
        restored(CANDIDATE_OUT, candidate_receipt)
        if sha256_file(EXPORT) != TRAINING_DATA_SHA256:
            fail("DATA_INTEGRITY_FAILURE", "export changed")
        if sudo_sha256(BEST) != BEST_SHA256:
            fail("EXPERIMENT_INVALID", "BEST moved during the run")
    except SystemExit as exc:
        valid = False
        reason = str(exc)
    acceptance = evaluate_acceptance(control_metrics, candidate_metrics)
    if not valid:
        outcome = "SETTLED_INVALID"
        passed = False
    else:
        passed = bool(acceptance["acceptance_passed"])
        outcome = "SETTLED_PASS" if passed else "SETTLED_FAIL"
    settled = settle(running, scientifically_valid=valid, acceptance_passed=passed)
    if settled["state"] != outcome:
        fail("EXPERIMENT_INVALID", f"lifecycle {settled['state']} != {outcome}")
    settled["next_action"] = "NONE"
    settled["promotion_applied"] = False
    settled["promotion_eligible"] = False
    best_after = sudo_sha256(BEST)
    report = {
        "acceptance": acceptance,
        "best_sha256_after": best_after,
        "best_sha256_before": BEST_SHA256,
        "best_moved": best_after != BEST_SHA256,
        "candidate_epochs": candidate_receipt.get("epochs_completed"),
        "candidate_metrics": control_metrics and candidate_metrics,
        "candidate_steps": candidate_receipt.get("global_steps"),
        "control_epochs": control_receipt.get("epochs_completed"),
        "control_metrics": control_metrics,
        "control_steps": control_receipt.get("global_steps"),
        "experiment_id": EXPERIMENT_ID,
        "integrity_reason": reason,
        "lifecycle_state": settled["state"],
        "preregistration_sha256": preregistration_hash(),
        "promotion_applied": False,
        "promotion_eligible": False,
        "schema": "hyperlex.select_007_experiment_settlement.v1",
    }
    report["candidate_metrics"] = candidate_metrics
    write_json(RUN / "EXPERIMENT_SETTLEMENT.json", report)
    write_json(RUN / "LIFECYCLE.json", settled)
    return report


def append_spec(report: dict) -> None:
    control = report["control_metrics"]
    candidate = report["candidate_metrics"]
    delta = None
    if control and candidate:
        delta = candidate["classify_macro_f1_nonnone"] - control["classify_macro_f1_nonnone"]
    section = f"""

## Settlement

Preregistration sha256 `{report["preregistration_sha256"]}`.

Lifecycle `{report["lifecycle_state"]}`. promotion_eligible false. promotion_applied false. BEST `{report["best_sha256_before"]}` before and `{report["best_sha256_after"]}` after.

Control epochs {report["control_epochs"]}, steps {report["control_steps"]}, macro-F1 {control.get("classify_macro_f1_nonnone")}.
Candidate epochs {report["candidate_epochs"]}, steps {report["candidate_steps"]}, macro-F1 {candidate.get("classify_macro_f1_nonnone")}.
Delta {delta}.

Gates: `{json.dumps(report["acceptance"].get("gates"), sort_keys=True)}`.
"""
    text = SPEC.read_text(encoding="utf-8")
    if "## Settlement" not in text:
        SPEC.write_text(text.rstrip() + section, encoding="utf-8")
    reserve_note = (
        "\n\n## SELECT-007\n\n"
        f"`{EXPERIMENT_ID}` built a fresh Wiktionary sense-label reserve. "
        "The SELECT-006 reserve was not reused. "
        f"Settlement is `{report['lifecycle_state']}` and BEST did not move.\n"
    )
    reserve_text = RESERVE_MD.read_text(encoding="utf-8")
    if "## SELECT-007" not in reserve_text:
        RESERVE_MD.write_text(reserve_text.rstrip() + reserve_note, encoding="utf-8")


def main() -> None:
    if (RUN / "EXPERIMENT_SETTLEMENT.json").is_file():
        sys.stdout.write((RUN / "EXPERIMENT_SETTLEMENT.json").read_text(encoding="utf-8") + "\n")
        return
    RUN.mkdir(parents=True, exist_ok=True)
    if sudo_sha256(BEST) != BEST_SHA256:
        fail("DATA_INTEGRITY_FAILURE", "BEST before the run")
    if sha256_file(LEDGER / "events.jsonl") != LEDGER_EVENTS_BEFORE and not (RESERVE / "RESERVE_MANIFEST.json").is_file():
        fail("LEDGER_REPLAY_FAILURE", "ledger drifted before acquisition")
    ensure_reserve()
    write_json(RUN / "BASELINE_ENV.json", arm_file("control"))
    write_json(RUN / "CANDIDATE_ENV.json", arm_file("candidate"))
    write_json(
        RUN / "THRESHOLD_AUTHORIZATION.json",
        {
            "decision_thresholds": {
                "early_stopping_patience": 4,
                "inferred_none_cap": CAP,
                "max_epochs": 12,
                "minimum_epochs": 4,
                "observed_none": OBSERVED_NONE,
            },
            "experiment_id": EXPERIMENT_ID,
            "schema": "hyperlex.threshold_authorization.v1",
            "sealed": True,
        },
    )
    write_json(
        RUN / "OPERATOR_AUTHORIZATION.json",
        {
            "decision": "AUTHORIZE",
            "experiment_id": EXPERIMENT_ID,
            "inferred_from": None,
            "schema": "hyperlex.select_007_operator_authorization.v1",
            "source": "operator CLEAR for SELECT-007",
        },
    )
    witness()
    if not (RUN / "LAUNCH_RECEIPT.json").is_file():
        write_json(
            RUN / "LAUNCH_RECEIPT.json",
            {
                "experiment_id": EXPERIMENT_ID,
                "optimizer_steps_before_receipt": 0,
                "preregistration_sha256": preregistration_hash(),
                "sampling_rule": f"{RULE}:{CAP}",
                "schema": "hyperlex.select_007_launch_receipt.v1",
                "training_started": False,
            },
        )
    lifecycle = ready_record(now())
    running = begin_run(lifecycle)
    write_json(RUN / "LIFECYCLE.json", running)
    try:
        control_receipt = train("control", CONTROL_OUT)
        candidate_receipt = train("candidate", CANDIDATE_OUT)
        control_metrics = score("control", CONTROL_OUT)
        candidate_metrics = score("candidate", CANDIDATE_OUT)
    except SystemExit as exc:
        invalid = settle(running, scientifically_valid=False, acceptance_passed=False)
        invalid["next_action"] = "NONE"
        invalid["promotion_applied"] = False
        invalid["promotion_eligible"] = False
        invalid["integrity_reason"] = str(exc)
        write_json(RUN / "LIFECYCLE.json", invalid)
        write_json(
            RUN / "EXPERIMENT_SETTLEMENT.json",
            {
                "experiment_id": EXPERIMENT_ID,
                "integrity_reason": str(exc),
                "lifecycle_state": invalid["state"],
                "preregistration_sha256": preregistration_hash(),
                "promotion_applied": False,
                "promotion_eligible": False,
                "schema": "hyperlex.select_007_experiment_settlement.v1",
            },
        )
        raise
    report = settle_run(control_receipt, candidate_receipt, control_metrics, candidate_metrics, running)
    append_spec(report)
    sys.stdout.write(canonical_json(report) + "\n")


if __name__ == "__main__":
    main()
