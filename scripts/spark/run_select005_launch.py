"""Execute SELECT_005_TRAINING_LAUNCH. Fail closed. Do not move BEST."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from hyperlexical.admission import effective_environment_hash
from hyperlexical.identity_ledger import IdentityLedger
from hyperlexical.select_005_reserve_eval import reserve_examples
from hyperlexical.select_005_threshold import apply_decision

REPO = Path("/home/morpheus/Hyperlex")
ROOT = Path("/home/morpheus/hlx-private/exp-20260927-select-005")
LAUNCH = ROOT / "launch-001"
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
EXPERIMENT = "HLX-EXP-2026-09-27-SELECT-005"
ENV_HASH = "ad253140ed539fd664188c472ff95ed42a98a8b6e7cf6389d6188dde8b83206d"
AUTH_SHA = "82595c98b1650313bb465057da9456e24a59ccdb6b249e4b9ee737cdd95cd23b"
WARM_SHA = "96838b9656a84c3fee1773a41fdf2fbbec2f88f3bc948e4acfbe06c194ac5587"
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
TRUNK_SHA = "340ac08b74eef0d7bdec2d7981a6a3d4249bf0e6aab60634b72ad02c2b8023a9"
EXPORT_SHA = "64b7d3dede25047cb6dd2e5b663f7fa72946ec82ac1a8816ae34622d1aaac430"
ADMISSION_SHA = "874ac309f1a51a677a692705aebd8fd48ae25dbdb5ca4d1e5c08c7870bdef382"
PREREG_SHA = "c2dcf3b703f50cb8eb80bb6c2c45335071ded3c4ce89cc669e8a869eb3498baf"
THRESHOLD_SHA = "e0d8d81b6392692784d92542d0cc5aa6ee6756b93c44bab86e2167ef57cfbc55"
MANIFEST_SHA = "2567b3e2d1a3b95b8ea4a474d4dda3ccbe2b6d55b016dd999b5eedcacd4b1f79"
EVENTS_SHA = "4ec441f545e37cd9e691ab322fa438269c79b6a6ed82f56b58ce740e94665763"
PROJECTION_SHA = "83d7dde24f723e750b487819aa1a5b6c7d847ca55fa5b1bf2dcd8b8157cc50d2"
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
EXPORT = Path("/home/morpheus/hlx-private/d1-spark-tree-20260924T213846Z/morph78-train-export.jsonl")
WARM = Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph65")
BEST = Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/model.safetensors")
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
CONTROL_OUT = Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select005-control")
CANDIDATE_OUT = Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select005")
AUTH = ROOT / "launch-authorization-001" / "TRAINING_LAUNCH_AUTHORIZATION.json"
PREREG = ROOT / "source-001" / "SELECT_005_PREREGISTRATION.json"
THRESHOLD = ROOT / "threshold-001" / "HLX_THRESHOLD_AUTHORIZATION.json"
MANIFEST = ROOT / "source-fetch-001" / "RESERVE_MANIFEST.json"
ADMISSION = ROOT / "admission-only-001" / "ADMISSION_RECEIPT.json"
BASELINE_ENV = ROOT / "baseline-env.json"
CANDIDATE_ENV = ROOT / "candidate-env.json"
BINDING = ROOT / "reserve-binding.json"
SPEC_MD = REPO / "specs/007-hyperlexical-model/evaluation-reserve.md"


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


def fail(state: str, reason: str) -> None:
    raise SystemExit(f"{state}: {reason}")


def require_hash(path: Path, expected: str, label: str) -> None:
    if sha256_file(path) != expected:
        fail("LAUNCH_PIN_MISMATCH", label)


def canonical(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def base_env(arm: str, out: Path) -> dict[str, str]:
    env = {
        "HYPERLEX_EXPORT_DIR": str(LAUNCH / f"{arm}-export"),
        "HLX_BASELINE_ENV": str(BASELINE_ENV),
        "HLX_BEST_SHA256": BEST_SHA,
        "HLX_BEST_WEIGHTS": str(BEST),
        "HLX_CANDIDATE_ENV": str(CANDIDATE_ENV),
        "HLX_EVAL_RESERVE_LEDGER": str(LEDGER),
        "HLX_EXPERIMENT_ID": EXPERIMENT,
        "HLX_RESERVE_BINDING": str(BINDING),
        "HLX_SCHEDULE_ARM": arm,
        "HLX_SCIENTIFIC_VARIABLE": "train_schedule",
        "HLX_SELECT_METRIC": "classify_macro_f1_nonnone",
        "HLX_THRESHOLD_AUTHORIZATION": str(THRESHOLD),
        "HLX_TRAIN_EXPORT_PATH": str(EXPORT),
        "HLX_TRAIN_EXPORT_ROWS": "9150",
        "HLX_TRAIN_EXPORT_SHA256": EXPORT_SHA,
        "HLX_TRUNK_SHA256": TRUNK_SHA,
        "HYPERLEX_ALLOW_TRAIN": "1",
        "HYPERLEX_INIT_EXPAND_VOCAB": "1",
        "HYPERLEX_INIT_FROM": str(WARM),
        "HYPERLEX_TRAIN_BATCH": "8",
        "HYPERLEX_TRAIN_LR": "2e-5",
        "HYPERLEX_TRAIN_OUT": str(out),
        "HYPERLEX_TRUNK_DIR": str(TRUNK),
    }
    if arm == "control":
        env["HYPERLEX_EARLY_STOP"] = "0"
        env["HYPERLEX_TRAIN_EPOCHS"] = "40"
    else:
        env["HYPERLEX_EARLY_STOP"] = "1"
        env["HYPERLEX_EARLY_STOP_MIN_EPOCHS"] = "4"
        env["HYPERLEX_EARLY_STOP_PATIENCE"] = "4"
        env["HYPERLEX_TRAIN_EPOCHS"] = "12"
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


def publish_dir(path: Path) -> None:
    if path.exists():
        subprocess.run(["sudo", "-n", "chmod", "-R", "a+rX", str(path)], check=True)


def adopt(path: Path) -> None:
    """Root-owned docker output becomes a private morpheus artifact."""
    if not path.exists():
        return
    subprocess.run(["sudo", "-n", "chown", "morpheus:morpheus", str(path)], check=True)
    os.chmod(path, 0o600)


def write_private(path: Path, payload: dict) -> None:
    path.write_text(canonical(payload), encoding="utf-8")
    os.chmod(path, 0o600)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_arm(name: str, out: Path) -> dict:
    receipt_path = out / "train-receipt.json"
    progress_path = out / "epoch-progress.jsonl"
    if not receipt_path.is_file() or not progress_path.is_file():
        fail("TELEMETRY_INCOMPLETE", f"{name} receipt or progress is absent")
    receipt = read_json(receipt_path)
    rows = [json.loads(line) for line in progress_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    required = [
        "checkpoint_sha256",
        "classification_accuracy",
        "classify_macro_f1_nonnone",
        "early_stop",
        "epoch",
        "global_step",
        "improved",
        "learning_rate",
        "observed_label_accuracy",
        "tie",
        "training_loss",
        "unbind_clean_exact",
    ]
    for row in rows:
        missing = [key for key in required if key not in row]
        if missing:
            fail("TELEMETRY_INCOMPLETE", f"{name} missing {','.join(missing)}")
        if row["training_loss"] is None or row["classify_macro_f1_nonnone"] is None:
            fail("TELEMETRY_INCOMPLETE", f"{name} epoch {row['epoch']} metric")
        if row["observed_label_accuracy"] is None:
            fail("TELEMETRY_INCOMPLETE", f"{name} observed accuracy")
        if row["unbind_clean_exact"] is not None:
            fail("TELEMETRY_INCOMPLETE", f"{name} inferred unbind_clean_exact from val")
        if row["learning_rate"] != 2e-5:
            fail("SCHEDULE_VIOLATION", f"{name} learning rate")
    if not rows or rows[-1]["global_step"] <= 0:
        fail("TRAINING_RUNTIME_FAILURE", f"{name} took no optimizer steps")
    if receipt.get("global_steps") != rows[-1]["global_step"]:
        fail("TELEMETRY_INCOMPLETE", f"{name} global step mismatch")
    primary = receipt.get("primary_weights_sha256")
    best = receipt.get("best_checkpoint_sha256")
    if not primary or primary != best:
        fail("RESTORE_BEST_FAILURE", f"{name} primary weights are not the best checkpoint")
    if sudo_sha256(out / "model.safetensors") != primary:
        fail("CHECKPOINT_FAILURE", f"{name} primary file hash")
    if sudo_sha256(out / "best" / "model.safetensors") != best:
        fail("CHECKPOINT_FAILURE", f"{name} best file hash")
    previous = None
    best_score = None
    for row in rows:
        score = float(row["classify_macro_f1_nonnone"])
        if row["improved"]:
            if best_score is not None and score <= best_score:
                fail("EARLY_STOPPING_VIOLATION", f"{name} non-strict improvement")
            best_score = score
        elif row["tie"]:
            if best_score is None or score != best_score:
                fail("EARLY_STOPPING_VIOLATION", f"{name} tie")
            if previous and row["checkpoint_sha256"] != previous["checkpoint_sha256"]:
                fail("EARLY_STOPPING_VIOLATION", f"{name} tie replaced the checkpoint")
        previous = row
    if name == "control":
        if len(rows) != 40 or receipt.get("stop_reason") != "max_epochs":
            fail("SCHEDULE_VIOLATION", "control did not complete 40 epochs")
        if any(row["early_stop"] for row in rows):
            fail("SCHEDULE_VIOLATION", "control early-stopped")
    else:
        if len(rows) < 4 or len(rows) > 12:
            fail("SCHEDULE_VIOLATION", "candidate epoch count")
        if any(row["early_stop"] and row["epoch"] < 3 for row in rows):
            fail("EARLY_STOPPING_VIOLATION", "candidate stopped before 4 scored epochs")
        if receipt.get("stop_reason") == "early_stopping":
            if rows[-1]["epochs_since_best"] < 4:
                fail("EARLY_STOPPING_VIOLATION", "candidate patience")
        elif receipt.get("stop_reason") != "max_epochs" or len(rows) != 12:
            fail("SCHEDULE_VIOLATION", "candidate stop reason")
    return {
        "best_checkpoint_sha256": best,
        "best_epoch": receipt.get("best_epoch"),
        "epochs_completed": len(rows),
        "global_steps": receipt.get("global_steps"),
        "primary_weights_sha256": primary,
        "stop_reason": receipt.get("stop_reason"),
        "trace": rows,
    }


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


def preflight() -> dict[str, str]:
    require_hash(AUTH, AUTH_SHA, "launch authorization")
    require_hash(PREREG, PREREG_SHA, "preregistration")
    require_hash(THRESHOLD, THRESHOLD_SHA, "threshold")
    require_hash(MANIFEST, MANIFEST_SHA, "manifest")
    require_hash(ADMISSION, ADMISSION_SHA, "admission")
    require_hash(EXPORT, EXPORT_SHA, "export")
    require_hash(LEDGER / "events.jsonl", EVENTS_SHA, "ledger events")
    require_hash(LEDGER / "ledger.json", PROJECTION_SHA, "ledger projection")
    if sudo_sha256(WARM / "model.safetensors") != WARM_SHA:
        fail("LAUNCH_PIN_MISMATCH", "warm start")
    if sudo_sha256(BEST) != BEST_SHA:
        fail("LAUNCH_PIN_MISMATCH", "BEST")
    if sudo_sha256(TRUNK / "model.safetensors") != TRUNK_SHA:
        fail("LAUNCH_PIN_MISMATCH", "trunk")
    auth = read_json(AUTH)
    if auth.get("operator_decision") != "AUTHORIZE" or auth.get("training_launch_authorized") is not True:
        fail("LAUNCH_PIN_MISMATCH", "authorization decision")
    if auth.get("training_started") is not False or auth.get("environment_sha256") != ENV_HASH:
        fail("LAUNCH_PIN_MISMATCH", "authorization pins")
    prereg = read_json(PREREG)
    if prereg["schedule"]["baseline"]["HYPERLEX_TRAIN_EPOCHS"] != "40":
        fail("LAUNCH_PIN_MISMATCH", "control schedule")
    if prereg["schedule"]["candidate"]["HYPERLEX_TRAIN_EPOCHS"] != "12":
        fail("LAUNCH_PIN_MISMATCH", "candidate schedule")
    if prereg["schedule"]["candidate"]["HYPERLEX_EARLY_STOP_PATIENCE"] != "4":
        fail("LAUNCH_PIN_MISMATCH", "patience")
    saved = os.environ.copy()
    try:
        os.environ.clear()
        os.environ.update(base_env("candidate", CANDIDATE_OUT))
        if effective_environment_hash() != ENV_HASH:
            fail("LAUNCH_PIN_MISMATCH", "environment")
        os.environ.update(base_env("control", CONTROL_OUT))
        control_hash = effective_environment_hash()
    finally:
        os.environ.clear()
        os.environ.update(saved)
    if CONTROL_OUT.exists() or CANDIDATE_OUT.exists():
        fail("TRAINING_INITIALIZATION_FAILURE", "output directory already exists")
    ledger = IdentityLedger.load(LEDGER)
    replay = json.dumps(ledger.project(), indent=2, sort_keys=True) + "\n"
    if replay != (LEDGER / "ledger.json").read_text(encoding="utf-8"):
        fail("LAUNCH_PIN_MISMATCH", "ledger replay")
    if len(ledger.active_reserve_records(EXPERIMENT)) != 78:
        fail("LAUNCH_PIN_MISMATCH", "reserve count")
    if sha256_file(LEDGER / "events.jsonl") != EVENTS_SHA:
        fail("LAUNCH_PIN_MISMATCH", "ledger mutated by replay")
    examples = reserve_examples()
    if len(examples) != 78:
        fail("EVALUATION_FAILURE", "reserve join")
    return {"control_environment_sha256": control_hash}


def write_launch_receipt(control_hash: str) -> str:
    target = LAUNCH / "LAUNCH_RECEIPT.json"
    if target.exists():
        return write_continuation_receipt(control_hash, sha256_file(target))
    payload = {
        "admission_receipt_sha256": ADMISSION_SHA,
        "authorized_environment_sha256": ENV_HASH,
        "control_environment_sha256": control_hash,
        "control_schedule": {
            "early_stopping": "disabled",
            "max_epochs": 40,
            "restore_best": True,
        },
        "candidate_schedule": {
            "early_stopping_patience": 4,
            "improvement": "strict",
            "max_epochs": 12,
            "minimum_epochs": 4,
            "restore_best": True,
            "ties": "keep_earlier",
        },
        "experiment_id": EXPERIMENT,
        "input_export_rows": 9150,
        "input_export_sha256": EXPORT_SHA,
        "launch_authorization_sha256": AUTH_SHA,
        "launched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "preregistration_sha256": PREREG_SHA,
        "reserve_manifest_sha256": MANIFEST_SHA,
        "schema": "hyperlex.select_005_training_launch_receipt.v1",
        "threshold_authorization_sha256": THRESHOLD_SHA,
        "trainer_commit": trainer_commit(),
        "training_started": False,
        "warm_start_sha256": WARM_SHA,
    }
    LAUNCH.mkdir(mode=0o700, exist_ok=True)
    os.chmod(LAUNCH, 0o700)
    target.write_text(canonical(payload), encoding="utf-8")
    os.chmod(target, 0o600)
    return sha256_file(target)


def write_continuation_receipt(control_hash: str, prior_sha: str) -> str:
    """Same sealed launch after the warm-start loader refused a larger vocab.

    The original receipt stays in place. No schedule, data, or threshold pin changes.
    """
    target = LAUNCH / "CONTINUATION_RECEIPT.json"
    if target.exists():
        fail("LAUNCH_PIN_MISMATCH", "continuation receipt already exists")
    payload = {
        "admission_receipt_sha256": ADMISSION_SHA,
        "authorized_environment_sha256": ENV_HASH,
        "control_environment_sha256": control_hash,
        "control_schedule": {
            "early_stopping": "disabled",
            "max_epochs": 40,
            "restore_best": True,
        },
        "candidate_schedule": {
            "early_stopping_patience": 4,
            "improvement": "strict",
            "max_epochs": 12,
            "minimum_epochs": 4,
            "restore_best": True,
            "ties": "keep_earlier",
        },
        "experiment_id": EXPERIMENT,
        "init_expand_vocab": "1",
        "input_export_rows": 9150,
        "input_export_sha256": EXPORT_SHA,
        "launch_authorization_sha256": AUTH_SHA,
        "launched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "loader_reason": "warm-start role vocab 10 does not match the export; expand loader copies overlapping rows",
        "preregistration_sha256": PREREG_SHA,
        "prior_failure": "TRAINING_INITIALIZATION_FAILURE",
        "prior_launch_receipt_sha256": prior_sha,
        "reserve_manifest_sha256": MANIFEST_SHA,
        "schema": "hyperlex.select_005_training_launch_continuation.v1",
        "threshold_authorization_sha256": THRESHOLD_SHA,
        "trainer_commit": trainer_commit(),
        "training_started": False,
        "warm_start_sha256": WARM_SHA,
    }
    target.write_text(canonical(payload), encoding="utf-8")
    os.chmod(target, 0o600)
    return sha256_file(target)


def run_arm(name: str, out: Path) -> dict:
    env = base_env(name, out)
    code = docker(
        {**env, "HLX_ADMISSION_ONLY": "1"},
        ["python", "-m", "hyperlexical.train", "--run"],
        LAUNCH / f"{name}-admission.log",
        f"hlx-select005-{name}-admit",
    )
    if code != 0 or out.exists():
        fail("TRAINING_INITIALIZATION_FAILURE", f"{name} admission exited {code}")
    code = docker(
        env,
        ["python", "-m", "hyperlexical.train", "--run"],
        LAUNCH / f"{name}-train.log",
        f"hlx-select005-{name}",
    )
    publish_dir(out)
    if code != 0:
        if not out.exists():
            fail(
                "TRAINING_INITIALIZATION_FAILURE",
                f"{name} trainer exited {code} before an output directory",
            )
        fail("TRAINING_RUNTIME_FAILURE", f"{name} trainer exited {code}")
    return validate_arm(name, out)


def settle(control: dict, candidate: dict) -> dict:
    for name, out in (("control", CONTROL_OUT), ("candidate", CANDIDATE_OUT)):
        dest = LAUNCH / f"{name}-reserve-metrics.json"
        code = docker(
            {"HYPERLEX_TRUNK_DIR": str(TRUNK)},
            ["python", "-m", "hyperlexical.select_005_reserve_eval", str(out), str(dest)],
            LAUNCH / f"{name}-reserve.log",
            f"hlx-select005-{name}-score",
        )
        adopt(dest)
        if code != 0 or not dest.is_file():
            fail("EVALUATION_FAILURE", f"{name} reserve scoring exited {code}")
    control_metrics = read_json(LAUNCH / "control-reserve-metrics.json")
    candidate_metrics = read_json(LAUNCH / "candidate-reserve-metrics.json")
    decision = apply_decision(control_metrics, candidate_metrics)
    events_after = sha256_file(LEDGER / "events.jsonl")
    projection_after = sha256_file(LEDGER / "ledger.json")
    if events_after != EVENTS_SHA or projection_after != PROJECTION_SHA:
        fail("SETTLEMENT_FAILURE", "ledger changed during evaluation")
    if sudo_sha256(BEST) != BEST_SHA:
        fail("SETTLEMENT_FAILURE", "BEST changed")
    table = {
        "candidate": {key: candidate_metrics[key] for key in (
            "classification_accuracy",
            "classify_macro_f1_nonnone",
            "observed_label_accuracy",
            "unbind_clean_exact",
        )},
        "control": {key: control_metrics[key] for key in (
            "classification_accuracy",
            "classify_macro_f1_nonnone",
            "observed_label_accuracy",
            "unbind_clean_exact",
        )},
        "decision": decision,
    }
    write_private(LAUNCH / "METRIC_TABLE.json", table)
    write_private(LAUNCH / "THRESHOLD_EVALUATION.json", decision)
    settlement = {
        "best_moved": False,
        "candidate_epochs": candidate["epochs_completed"],
        "candidate_global_steps": candidate["global_steps"],
        "candidate_stop_reason": candidate["stop_reason"],
        "control_epochs": control["epochs_completed"],
        "control_global_steps": control["global_steps"],
        "control_stop_reason": control["stop_reason"],
        "experiment_id": EXPERIMENT,
        "outcome": "PROMOTION_ELIGIBLE" if decision["pass"] else "REJECT",
        "promotion_applied": False,
        "schema": "hyperlex.select_005_experiment_settlement.v1",
        "threshold_outcome": decision["outcome"],
    }
    write_private(LAUNCH / "EXPERIMENT_SETTLEMENT.json", settlement)
    manifest = {
        "candidate_best_sha256": candidate["best_checkpoint_sha256"],
        "candidate_primary_sha256": candidate["primary_weights_sha256"],
        "control_best_sha256": control["best_checkpoint_sha256"],
        "control_primary_sha256": control["primary_weights_sha256"],
        "warm_start_sha256": WARM_SHA,
    }
    write_private(LAUNCH / "CHECKPOINT_MANIFEST.json", manifest)
    for name, summary, out in (
        ("control", control, CONTROL_OUT),
        ("candidate", candidate, CANDIDATE_OUT),
    ):
        receipt_src = out / "train-receipt.json"
        receipt_dest = LAUNCH / f"{name}-train-receipt.json"
        receipt_dest.write_bytes(receipt_src.read_bytes())
        os.chmod(receipt_dest, 0o600)
        write_private(
            LAUNCH / f"{name.upper()}_RUN_RECEIPT.json",
            {
                "arm": name,
                "best_checkpoint_sha256": summary["best_checkpoint_sha256"],
                "best_epoch": summary["best_epoch"],
                "epochs_completed": summary["epochs_completed"],
                "global_steps": summary["global_steps"],
                "output_dir": str(out),
                "primary_weights_sha256": summary["primary_weights_sha256"],
                "restore_best": summary["primary_weights_sha256"] == summary["best_checkpoint_sha256"],
                "stop_reason": summary["stop_reason"],
                "train_receipt_sha256": sha256_file(receipt_dest),
            },
        )
    write_private(
        LAUNCH / "CANDIDATE_EARLY_STOP_TRACE.json",
        {
            "improvement": "strict",
            "minimum_epochs": 4,
            "patience": 4,
            "rows": [
                {
                    "checkpoint_sha256": row.get("checkpoint_sha256"),
                    "classify_macro_f1_nonnone": row.get("classify_macro_f1_nonnone"),
                    "early_stop": row.get("early_stop"),
                    "epoch": row.get("epoch"),
                    "epochs_since_best": row.get("epochs_since_best"),
                    "global_step": row.get("global_step"),
                    "improved": row.get("improved"),
                    "tie": row.get("tie"),
                }
                for row in candidate["trace"]
            ],
            "ties": "keep_earlier",
        },
    )
    return {
        "decision": decision,
        "metrics": table,
        "settlement": settlement,
    }


def main() -> None:
    hashes = preflight()
    launch_sha = write_launch_receipt(hashes["control_environment_sha256"])
    print(json.dumps({"launch_receipt_sha256": launch_sha, "preflight": "PASS"}), flush=True)
    control = run_arm("control", CONTROL_OUT)
    print(json.dumps({"control_epochs": control["epochs_completed"], "control_steps": control["global_steps"]}), flush=True)
    candidate = run_arm("candidate", CANDIDATE_OUT)
    print(json.dumps({"candidate_epochs": candidate["epochs_completed"], "candidate_steps": candidate["global_steps"]}), flush=True)
    result = settle(control, candidate)
    summary = {
        "candidate_epochs": candidate["epochs_completed"],
        "candidate_steps": candidate["global_steps"],
        "control_epochs": control["epochs_completed"],
        "control_steps": control["global_steps"],
        "launch_receipt_sha256": launch_sha,
        "outcome": result["settlement"]["outcome"],
        "threshold": result["decision"]["outcome"],
    }
    write_private(LAUNCH / "LAUNCH_SUMMARY.json", summary)
    print(canonical(summary), flush=True)


if __name__ == "__main__":
    try:
        main()
    except SystemExit as exc:
        LAUNCH.mkdir(mode=0o700, exist_ok=True)
        os.chmod(LAUNCH, 0o700)
        failure = LAUNCH / "FAILURE.json"
        if failure.exists():
            failure = LAUNCH / "FAILURE_CONTINUATION.json"
        if not failure.exists():
            failure.write_text(
                canonical(
                    {
                        "best_moved": False,
                        "message": str(exc),
                        "training_launch_authorized": True,
                    }
                ),
                encoding="utf-8",
            )
            os.chmod(failure, 0o600)
        raise
