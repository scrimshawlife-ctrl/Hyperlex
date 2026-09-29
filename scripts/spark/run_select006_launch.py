"""Execute SELECT_006_TRAINING_LAUNCH. Fail closed. Do not move BEST."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from hyperlexical.identity_ledger import IdentityLedger
from hyperlexical.select_006_efficiency_preservation import apply_decision
from hyperlexical.select_006_training_launch import (
    LaunchFailure,
    assert_experiment_valid,
    require_witness,
    validate_arm_telemetry,
)

REPO = Path("/home/morpheus/Hyperlex")
ROOT = Path("/home/morpheus/hlx-private/exp-20260929-select-006")
LAUNCH = ROOT / "launch-001"
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
IMAGE_SHA = "616a3e97f45191af975896cfa644279096cb31bd408a071c2e99ca7209c3cafe"
EXPERIMENT = "HLX-EXP-2026-09-29-SELECT-006"
AUTH_SHA = "4c13b58cc05a6418a1281e21fcf1d586bfacedbaa0a11354526b3ccf80c4b9db"
WARM_SHA = "96838b9656a84c3fee1773a41fdf2fbbec2f88f3bc948e4acfbe06c194ac5587"
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
TRUNK_SHA = "340ac08b74eef0d7bdec2d7981a6a3d4249bf0e6aab60634b72ad02c2b8023a9"
EXPORT_SHA = "64b7d3dede25047cb6dd2e5b663f7fa72946ec82ac1a8816ae34622d1aaac430"
ADMISSION_SHA = "7ff98e8bc9a49a8875e8c7310f18ae9c5bb53ca4ad40e9b954ca89d52a7551bd"
PREREG_SHA = "3692ac63425fcbd57e5fdc355a4e565d653ffc3c2a6703cfdda1fde7cc6404b8"
THRESHOLD_SHA = "91081de5f9b348102fa5d0359150f9aedca0d53e98c9f4275aeb127c9de3642c"
MANIFEST_SHA = "33ee588bdd13a322020e2a0105a71265899b856b44b6c3fcde40eb943b36cab6"
BASELINE_ENV_SHA = "ca26a7cb12fcd0ce96e0f198fbcd30a1fd3e61fe0164e14dad823a2d17516a9d"
CANDIDATE_ENV_SHA = "f67c45774b173d7c894177252f16e3abe39cbdbb6f20f83c4db53b8485bd3ea6"
CONFIG_SHA = "fec14e56789f1c761b5f2e6ab0ef1958a3518b3fc4b1d44d15bd1afeb8f1865b"
EVENTS_SHA = "4471e3339b3708f0f494f7fe60a0d30118609e7312d5d0334b946d2bbc4efbf1"
PROJECTION_SHA = "dad556c7f6bba58c7456a6b88b607c72ebe8149e36c176a602e0def2edfdc435"
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
EXPORT = Path("/home/morpheus/hlx-private/d1-spark-tree-20260924T213846Z/morph78-train-export.jsonl")
WARM = Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph65")
BEST = Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/model.safetensors")
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
CONTROL_CONFIG = Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select005-control/config.json")
CANDIDATE_CONFIG = Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select005/config.json")
CONTROL_OUT = Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select006-control")
CANDIDATE_OUT = Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select006")
AUTH = ROOT / "launch-authorization-001" / "TRAINING_LAUNCH_AUTHORIZATION.json"
PREREG = ROOT / "spec-001" / "SELECT_006_PREREGISTRATION.json"
THRESHOLD = ROOT / "spec-001" / "SELECT_006_THRESHOLD_AUTHORIZATION.json"
MANIFEST = ROOT / "reserve-acquisition-002" / "RESERVE_MANIFEST.json"
ADMISSION = ROOT / "admission-only-001" / "ADMISSION_RECEIPT.json"
BASELINE_ENV = ROOT / "spec-001" / "BASELINE_ENV.json"
CANDIDATE_ENV = ROOT / "spec-001" / "CANDIDATE_ENV.json"
BINDING = ROOT / "zero-init-loader-001" / "RESERVE_BINDING_FOR_INIT_DRY_RUN.json"
VOCAB_PIN = ROOT / "spec-001" / "VOCABULARY_EXPANSION_PIN.json"
VOCAB_PIN_SHA = "8e1cce3de9ca6dfd346e926cfa3c8bffd5a9d05dfdc671b7da26e01aa539f076"


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


def fail(code: str, detail: str) -> None:
    raise LaunchFailure(code, detail)


def require_hash(path: Path, expected: str, label: str, code: str = "LAUNCH_PIN_MISMATCH") -> None:
    if sha256_file(path) != expected:
        fail(code, label)


def canonical(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_private(path: Path, payload: dict) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    path.write_text(canonical(payload), encoding="utf-8")
    os.chmod(path, 0o600)


def status(payload: dict) -> None:
    write_private(LAUNCH / "STATUS.json", payload)
    print(canonical(payload), flush=True)


def arm_env(arm: str, out: Path) -> dict[str, str]:
    baseline = read_json(BASELINE_ENV)
    candidate = read_json(CANDIDATE_ENV)
    env = {key: str(value) for key, value in candidate.items()}
    if arm == "control":
        env.pop("HYPERLEX_EARLY_STOP_MIN_EPOCHS", None)
        env.pop("HYPERLEX_EARLY_STOP_PATIENCE", None)
        env["HYPERLEX_EARLY_STOP"] = str(baseline["HYPERLEX_EARLY_STOP"])
        env["HYPERLEX_TRAIN_EPOCHS"] = str(baseline["HYPERLEX_TRAIN_EPOCHS"])
    env.update(
        {
            "HLX_BASELINE_ENV": str(BASELINE_ENV),
            "HLX_BEST_SHA256": BEST_SHA,
            "HLX_BEST_WEIGHTS": str(BEST),
            "HLX_CANDIDATE_ENV": str(CANDIDATE_ENV),
            "HLX_EVAL_RESERVE_LEDGER": str(LEDGER),
            "HLX_RESERVE_BINDING": str(BINDING),
            "HLX_SCHEDULE_ARM": arm,
            "HLX_THRESHOLD_AUTHORIZATION": str(THRESHOLD),
            "HLX_TRUNK_SHA256": TRUNK_SHA,
            "HYPERLEX_ALLOW_TRAIN": "1",
            "HYPERLEX_EXPORT_DIR": str(LAUNCH / f"{arm}-export"),
            "HYPERLEX_TRAIN_OUT": str(out),
        }
    )
    return env


def docker(env: dict[str, str], args: list[str], log_path: Path, name: str) -> int:
    command = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "--name",
        name,
        "-v",
        "/home/morpheus/Hyperlex:/home/morpheus/Hyperlex",
        "-v",
        "/home/morpheus/hlx-private:/home/morpheus/hlx-private",
        "-v",
        "/home/morpheus/.hyperlex:/home/morpheus/.hyperlex",
        "-w",
        "/home/morpheus/Hyperlex",
        "-e",
        "HOME=/home/morpheus",
        "-e",
        "HF_HUB_OFFLINE=1",
        "-e",
        "PYTHONDONTWRITEBYTECODE=1",
        "-e",
        "PYTHONPATH=/home/morpheus/Hyperlex/scripts/shadow",
        "-e",
        "PYTHONUNBUFFERED=1",
        "-e",
        "TRANSFORMERS_OFFLINE=1",
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
    fail("TRAINING_INITIALIZATION_FAILURE", "trainer log has no receipt")


def publish_dir(path: Path) -> None:
    if path.exists():
        subprocess.run(["sudo", "-n", "chmod", "-R", "a+rX", str(path)], check=True)


def trainer_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    dirty = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    if dirty.stdout.strip():
        fail("TRAINING_INITIALIZATION_FAILURE", "trainer tree is dirty")
    return completed.stdout.strip()


def runtime_identity() -> dict:
    probe = (
        "import sys,torch;"
        "print(sys.version.split()[0]);"
        "print(torch.__version__);"
        "print(torch.version.cuda or '');"
        "print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu')"
    )
    log = LAUNCH / "runtime-identity.log"
    code = docker({}, ["python", "-c", probe], log, "hlx-select006-runtime")
    if code != 0:
        fail("TRAINING_INITIALIZATION_FAILURE", "runtime probe failed")
    lines = [line.strip() for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) < 4:
        fail("TRAINING_INITIALIZATION_FAILURE", "runtime probe output")
    gpu = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,uuid", "--format=csv,noheader"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return {
        "cuda": lines[2],
        "gpu": gpu,
        "image": IMAGE,
        "image_sha256": IMAGE_SHA,
        "kernel": platform.platform(),
        "python": lines[0],
        "torch": lines[1],
        "torch_device": lines[3],
    }


def preflight() -> None:
    require_hash(AUTH, AUTH_SHA, "launch authorization")
    require_hash(ADMISSION, ADMISSION_SHA, "admission")
    require_hash(PREREG, PREREG_SHA, "preregistration")
    require_hash(THRESHOLD, THRESHOLD_SHA, "threshold")
    require_hash(MANIFEST, MANIFEST_SHA, "manifest")
    require_hash(BASELINE_ENV, BASELINE_ENV_SHA, "baseline env")
    require_hash(CANDIDATE_ENV, CANDIDATE_ENV_SHA, "candidate env")
    require_hash(CONTROL_CONFIG, CONFIG_SHA, "control config")
    require_hash(CANDIDATE_CONFIG, CONFIG_SHA, "candidate config")
    require_hash(EXPORT, EXPORT_SHA, "export")
    require_hash(VOCAB_PIN, VOCAB_PIN_SHA, "vocabulary pin")
    require_hash(LEDGER / "events.jsonl", EVENTS_SHA, "ledger events", "RESERVE_INTEGRITY_FAILURE")
    require_hash(LEDGER / "ledger.json", PROJECTION_SHA, "ledger projection", "RESERVE_INTEGRITY_FAILURE")
    if sudo_sha256(WARM / "model.safetensors") != WARM_SHA:
        fail("LAUNCH_PIN_MISMATCH", "warm start")
    if sudo_sha256(BEST) != BEST_SHA:
        fail("LAUNCH_PIN_MISMATCH", "BEST")
    if sudo_sha256(TRUNK / "model.safetensors") != TRUNK_SHA:
        fail("LAUNCH_PIN_MISMATCH", "trunk")
    auth = read_json(AUTH)
    if auth.get("operator_decision") != "AUTHORIZE" or auth.get("training_launch_authorized") is not True:
        fail("LAUNCH_PIN_MISMATCH", "authorization decision")
    if auth.get("training_started") is not False or auth.get("epsilon") != 0:
        fail("LAUNCH_PIN_MISMATCH", "authorization state")
    if auth.get("experiment_id") != EXPERIMENT:
        fail("LAUNCH_PIN_MISMATCH", "experiment")
    prereg = read_json(PREREG)
    if prereg.get("epsilon") != 0:
        fail("LAUNCH_PIN_MISMATCH", "EPSILON")
    if prereg["control_schedule"]["max_epochs"] != 40 or prereg["control_schedule"]["early_stopping"] != "disabled":
        fail("LAUNCH_PIN_MISMATCH", "control schedule")
    if prereg["candidate_schedule"]["max_epochs"] != 12 or prereg["candidate_schedule"]["early_stopping_patience"] != 4:
        fail("LAUNCH_PIN_MISMATCH", "candidate schedule")
    manifest = read_json(MANIFEST)
    if manifest.get("slice_counts") != {
        "classify": 32,
        "classify_non_none": 32,
        "classify_observed": 32,
        "unbind_clean": 5,
    } or manifest.get("head_mapped_non_none") != 32:
        fail("RESERVE_INTEGRITY_FAILURE", "slice counts")
    if len(manifest.get("rows") or []) != 37:
        fail("RESERVE_INTEGRITY_FAILURE", "reserve count")
    ledger = IdentityLedger.load(LEDGER)
    replay = json.dumps(ledger.project(), indent=2, sort_keys=True) + "\n"
    if replay != (LEDGER / "ledger.json").read_text(encoding="utf-8"):
        fail("RESERVE_INTEGRITY_FAILURE", "ledger replay")
    if len(ledger.active_reserve_records(EXPERIMENT)) != 37:
        fail("RESERVE_INTEGRITY_FAILURE", "active reserve")
    if sha256_file(LEDGER / "events.jsonl") != EVENTS_SHA:
        fail("RESERVE_INTEGRITY_FAILURE", "ledger mutated by replay")
    if CONTROL_OUT.exists() or CANDIDATE_OUT.exists():
        fail("TRAINING_INITIALIZATION_FAILURE", "output directory already exists")
    if (LAUNCH / "LAUNCH_RECEIPT.json").exists():
        fail("TRAINING_INITIALIZATION_FAILURE", "launch receipt already exists")


def witness_arm(arm: str, out: Path) -> dict:
    env = arm_env(arm, out)
    env["HLX_STOP_BEFORE_OPTIMIZER"] = "1"
    code = docker(
        env,
        ["python", "-m", "hyperlexical.train", "--run"],
        LAUNCH / f"{arm}-witness.log",
        f"hlx-select006-{arm}-witness",
    )
    if out.exists():
        fail("TRAINING_INITIALIZATION_FAILURE", f"{arm} witness created the output directory")
    if code != 0:
        fail("ZERO_INIT_LOADER_MISMATCH", f"{arm} witness exited {code}")
    receipt = last_json((LAUNCH / f"{arm}-witness.log").read_text(encoding="utf-8"))
    require_witness(receipt)
    write_private(LAUNCH / f"{arm.upper()}_WITNESS.json", receipt)
    return receipt


def run_arm(arm: str, out: Path) -> dict:
    env = arm_env(arm, out)
    code = docker(
        env,
        ["python", "-m", "hyperlexical.train", "--run"],
        LAUNCH / f"{arm}-train.log",
        f"hlx-select006-{arm}",
    )
    publish_dir(out)
    if code != 0:
        if not out.exists():
            fail("TRAINING_INITIALIZATION_FAILURE", f"{arm} trainer exited {code} before an output directory")
        fail("TRAINING_RUNTIME_FAILURE", f"{arm} trainer exited {code}")
    if sha256_file(EXPORT) != EXPORT_SHA:
        fail("EXPERIMENT_INVALID", f"{arm} changed the training export")
    receipt_path = out / "train-receipt.json"
    progress_path = out / "epoch-progress.jsonl"
    if not receipt_path.is_file() or not progress_path.is_file():
        fail("TELEMETRY_INCOMPLETE", f"{arm} receipt or progress is absent")
    receipt = read_json(receipt_path)
    rows = [json.loads(line) for line in progress_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    summary = validate_arm_telemetry(
        arm,
        rows,
        receipt,
        primary_file_sha=sudo_sha256(out / "model.safetensors"),
        best_file_sha=sudo_sha256(out / "best" / "model.safetensors"),
    )
    summary["receipt"] = receipt
    summary["trace"] = rows
    summary["final_aside_sha256"] = (
        sudo_sha256(out / "model.final.safetensors") if (out / "model.final.safetensors").is_file() else None
    )
    return summary


def score(arm: str, out: Path) -> dict:
    dest = LAUNCH / f"{arm}-reserve-metrics.json"
    code = docker(
        {"HYPERLEX_TRUNK_DIR": str(TRUNK)},
        ["python", "-m", "hyperlexical.select_006_reserve_eval", str(out), str(dest)],
        LAUNCH / f"{arm}-reserve.log",
        f"hlx-select006-{arm}-score",
    )
    publish_dir(dest)
    if code != 0 or not dest.is_file():
        log = (LAUNCH / f"{arm}-reserve.log").read_text(encoding="utf-8") if (LAUNCH / f"{arm}-reserve.log").is_file() else ""
        if "METRIC_NONCOMPUTABLE" in log:
            fail("METRIC_NONCOMPUTABLE", f"{arm} reserve metric")
        fail("RESERVE_SCORING_FAILURE", f"{arm} reserve scoring exited {code}")
    return read_json(dest)


def settle(control: dict, candidate: dict, control_metrics: dict, candidate_metrics: dict) -> dict:
    try:
        assert_experiment_valid(control["receipt"], candidate["receipt"])
    except LaunchFailure:
        raise
    required = (
        "classification_accuracy",
        "classify_macro_f1_nonnone",
        "observed_label_accuracy",
        "unbind_clean_exact",
    )
    for metrics in (control_metrics, candidate_metrics):
        for key in required:
            if metrics.get(key) is None:
                fail("METRIC_NONCOMPUTABLE", key)
    if control["optimizer_steps"] <= 0:
        fail("EFFICIENCY_CALCULATION_FAILURE", "control optimizer steps")
    decision = apply_decision(
        control=control_metrics,
        candidate=candidate_metrics,
        control_steps=control["optimizer_steps"],
        candidate_steps=candidate["optimizer_steps"],
    )
    ratio = candidate["optimizer_steps"] / control["optimizer_steps"]
    efficiency = {
        "candidate_epochs": candidate["epochs_completed"],
        "candidate_optimizer_steps": candidate["optimizer_steps"],
        "candidate_wall_seconds": candidate["wall_seconds"],
        "control_epochs": control["epochs_completed"],
        "control_optimizer_steps": control["optimizer_steps"],
        "control_wall_seconds": control["wall_seconds"],
        "epochs_ratio": candidate["epochs_completed"] / control["epochs_completed"],
        "pass": bool(next(gate["pass"] for gate in decision["gates"] if gate["metric"] == "optimizer_steps")),
        "step_ratio": ratio,
        "step_reduction_percent": (1.0 - ratio) * 100.0,
        "wall_clock_is_a_gate": False,
        "wall_clock_ratio": candidate["wall_seconds"] / control["wall_seconds"],
    }
    events_after = sha256_file(LEDGER / "events.jsonl")
    projection_after = sha256_file(LEDGER / "ledger.json")
    if events_after != EVENTS_SHA or projection_after != PROJECTION_SHA:
        fail("SETTLEMENT_FAILURE", "ledger changed")
    if sudo_sha256(BEST) != BEST_SHA:
        fail("SETTLEMENT_FAILURE", "BEST changed")
    ledger = IdentityLedger.load(LEDGER)
    active = ledger.active_reserve_records(EXPERIMENT)
    if len(active) != 37:
        fail("SETTLEMENT_FAILURE", "reserve lifecycle")
    if len(ledger.active_reserve_records("HLX-EXP-2026-09-27-SELECT-005")) != 78:
        fail("SETTLEMENT_FAILURE", "SELECT-005 reserve changed")
    table = {
        "candidate": {key: candidate_metrics[key] for key in required},
        "control": {key: control_metrics[key] for key in required},
        "deltas": {
            key: float(candidate_metrics[key]) - float(control_metrics[key]) for key in required
        },
        "experiment_id": EXPERIMENT,
    }
    write_private(LAUNCH / "METRIC_TABLE.json", table)
    write_private(LAUNCH / "EFFICIENCY_CALCULATION.json", efficiency)
    write_private(LAUNCH / "THRESHOLD_EVALUATION.json", decision)
    settlement = {
        "best_moved": False,
        "best_sha256": BEST_SHA,
        "candidate_epochs": candidate["epochs_completed"],
        "candidate_optimizer_steps": candidate["optimizer_steps"],
        "candidate_stop_reason": candidate["stop_reason"],
        "control_epochs": control["epochs_completed"],
        "control_optimizer_steps": control["optimizer_steps"],
        "control_stop_reason": control["stop_reason"],
        "experiment_id": EXPERIMENT,
        "experimental_validity": "PASS",
        "ledger_events_sha256": events_after,
        "ledger_projection_sha256": projection_after,
        "next_legal_transition": "NONE",
        "outcome": decision["outcome"],
        "promotion_applied": False,
        "promotion_eligible": False,
        "reserve_active": 37,
        "reserve_lifecycle": "EVAL_RESERVE",
        "schema": "hyperlex.select_006_experiment_settlement.v1",
        "threshold_outcome": decision["outcome"],
    }
    write_private(LAUNCH / "EXPERIMENT_SETTLEMENT.json", settlement)
    for arm, summary, out in (
        ("control", control, CONTROL_OUT),
        ("candidate", candidate, CANDIDATE_OUT),
    ):
        copied = LAUNCH / f"{arm}-train-receipt.json"
        copied.write_bytes((out / "train-receipt.json").read_bytes())
        os.chmod(copied, 0o600)
        write_private(
            LAUNCH / f"{arm.upper()}_CHECKPOINT_MANIFEST.json",
            {
                "arm": arm,
                "best_checkpoint_sha256": summary["best_checkpoint_sha256"],
                "best_epoch": summary["best_epoch"],
                "final_aside_sha256": summary["final_aside_sha256"],
                "output_dir": str(out),
                "restored_checkpoint_sha256": summary["primary_weights_sha256"],
                "restore_best": summary["primary_weights_sha256"] == summary["best_checkpoint_sha256"],
            },
        )
        write_private(
            LAUNCH / f"{arm.upper()}_RUN_RECEIPT.json",
            {
                "arm": arm,
                "best_checkpoint_sha256": summary["best_checkpoint_sha256"],
                "best_epoch": summary["best_epoch"],
                "epochs_completed": summary["epochs_completed"],
                "optimizer_steps": summary["optimizer_steps"],
                "output_dir": str(out),
                "restored_checkpoint_sha256": summary["primary_weights_sha256"],
                "restore_best": True,
                "stop_reason": summary["stop_reason"],
                "train_receipt_sha256": sha256_file(copied),
                "wall_seconds": summary["wall_seconds"],
            },
        )
    write_private(
        LAUNCH / "CANDIDATE_EARLY_STOP_TRACE.json",
        {
            "improvement": "strict",
            "minimum_epochs": 4,
            "patience": 4,
            "rows": candidate["trace"],
            "stop_reason": candidate["stop_reason"],
            "ties": "keep_earlier",
        },
    )
    return {"decision": decision, "efficiency": efficiency, "settlement": settlement, "table": table}


def main() -> None:
    LAUNCH.mkdir(mode=0o700, exist_ok=True)
    os.chmod(LAUNCH, 0o700)
    preflight()
    identity = runtime_identity()
    status({"phase": "witness", "preflight": "PASS"})
    control_witness = witness_arm("control", CONTROL_OUT)
    candidate_witness = witness_arm("candidate", CANDIDATE_OUT)
    if control_witness["expanded_loader_witness_sha256"] != candidate_witness["expanded_loader_witness_sha256"]:
        fail("ZERO_INIT_LOADER_MISMATCH", "arms initialized differently")
    receipt = {
        "admission_receipt_sha256": ADMISSION_SHA,
        "baseline_env_sha256": BASELINE_ENV_SHA,
        "best_sha256": BEST_SHA,
        "candidate_env_sha256": CANDIDATE_ENV_SHA,
        "candidate_schedule": {
            "early_stopping_patience": 4,
            "improvement": "strict",
            "max_epochs": 12,
            "minimum_epochs": 4,
            "restore_best": True,
            "ties": "keep_earlier",
        },
        "config_sha256": CONFIG_SHA,
        "control_schedule": {
            "early_stopping": "disabled",
            "max_epochs": 40,
            "restore_best": True,
        },
        "epsilon": 0,
        "experiment_id": EXPERIMENT,
        "hardware": identity,
        "input_export_rows": 9150,
        "input_export_sha256": EXPORT_SHA,
        "launch_authorization_sha256": AUTH_SHA,
        "launched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "optimizer_steps_before_receipt": 0,
        "preregistration_sha256": PREREG_SHA,
        "reserve_manifest_sha256": MANIFEST_SHA,
        "runtime": identity,
        "schema": "hyperlex.select_006_training_launch_receipt.v1",
        "threshold_authorization_sha256": THRESHOLD_SHA,
        "trainer_commit": trainer_commit(),
        "training_started": False,
        "warm_start_sha256": WARM_SHA,
        "zero_init": {
            "combined_witness_sha256": control_witness["expanded_loader_witness_sha256"],
            "execution_loader_status": "ZERO_INIT_LOADER_VERIFIED",
            "filler_bias_sha256": control_witness["expanded_filler_bias_sha256"],
            "filler_weight_sha256": control_witness["expanded_filler_weight_sha256"],
            "role_bias_sha256": control_witness["expanded_role_bias_sha256"],
            "role_weight_sha256": control_witness["expanded_role_weight_sha256"],
        },
    }
    write_private(LAUNCH / "LAUNCH_RECEIPT.json", receipt)
    launch_sha = sha256_file(LAUNCH / "LAUNCH_RECEIPT.json")
    status({"launch_receipt_sha256": launch_sha, "phase": "control"})
    control = run_arm("control", CONTROL_OUT)
    status({"control_epochs": control["epochs_completed"], "control_steps": control["optimizer_steps"], "phase": "candidate"})
    candidate = run_arm("candidate", CANDIDATE_OUT)
    status({"candidate_epochs": candidate["epochs_completed"], "candidate_steps": candidate["optimizer_steps"], "phase": "score"})
    control_metrics = score("control", CONTROL_OUT)
    candidate_metrics = score("candidate", CANDIDATE_OUT)
    result = settle(control, candidate, control_metrics, candidate_metrics)
    summary = {
        "candidate_epochs": candidate["epochs_completed"],
        "candidate_steps": candidate["optimizer_steps"],
        "control_epochs": control["epochs_completed"],
        "control_steps": control["optimizer_steps"],
        "launch_receipt_sha256": launch_sha,
        "outcome": result["settlement"]["outcome"],
        "promotion_applied": False,
        "threshold": result["decision"]["outcome"],
    }
    write_private(LAUNCH / "LAUNCH_SUMMARY.json", summary)
    status(summary)


if __name__ == "__main__":
    try:
        main()
    except LaunchFailure as exc:
        LAUNCH.mkdir(mode=0o700, exist_ok=True)
        os.chmod(LAUNCH, 0o700)
        failure = LAUNCH / "FAILURE.json"
        if failure.exists():
            failure = LAUNCH / "FAILURE_CONTINUATION.json"
        if not failure.exists():
            best_now = None
            try:
                best_now = sudo_sha256(BEST)
            except subprocess.CalledProcessError:
                best_now = None
            failure.write_text(
                canonical(
                    {
                        "best_moved": best_now not in (None, BEST_SHA),
                        "best_sha256": best_now,
                        "code": exc.code,
                        "message": str(exc),
                        "promotion_applied": False,
                    }
                ),
                encoding="utf-8",
            )
            os.chmod(failure, 0o600)
        raise
