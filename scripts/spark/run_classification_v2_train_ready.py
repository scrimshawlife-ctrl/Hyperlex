"""Classification v2 training after the validation floor is met.

Uses the versioned validation export and the frozen prototype witness.
Does not move BEST, does not score the evaluation reserve, and does not
rebuild prototypes.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
PINS = Path("/home/morpheus/hlx-private/classification-v2-validation-20260929/VALIDATION_EXPORT.json")
WITNESS = Path("/home/morpheus/hlx-private/classification-v2-prototype-20260929/PROTOTYPE_WITNESS.json")
WITNESS_SHA = "7faa98239b2d4f39bf722c776543ded9a6c5959646c09c5db1e977cd7e69855d"
WITNESS_FILE_SHA = "fa2c1a33bb1e5a11becb113490078b4d80d4cc46b284f5aa4a819c5ccaf98dc3"
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
INIT_FROM = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004"
)
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
OUT = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-classification-v2-ready"
)
PRIVATE = Path("/home/morpheus/hlx-private/classification-v2-train-ready-20260929")
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
BEST_LINK = Path("/home/morpheus/.hyperlex/models/BEST")
SEAL = "8b30c98ad8eac7c136e391103450c9d0d20a3499220e9b48f923eab8218581f1"
RUN_ID = "HLX-CLASSIFICATION-V2-READY-20260929"

sys.path.insert(0, str(REPO / "scripts" / "shadow"))


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


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def write_private(path: Path, payload: dict) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def preflight(pins: dict) -> dict:
    export = Path(pins["export_path"])
    if sha256_file(export) != pins["export_sha256"]:
        fail("export digest mismatch")
    if pins["evidence_seal"] != SEAL:
        fail("evidence seal mismatch")
    if sha256_file(WITNESS) != WITNESS_FILE_SHA:
        fail("prototype witness file digest mismatch")
    witness_body = json.loads(WITNESS.read_text(encoding="utf-8"))
    if witness_body.get("witness_sha256") != WITNESS_SHA:
        fail("prototype witness hash mismatch")
    rows = []
    with export.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    if len(rows) != pins["export_rows"]:
        fail(f"export row count {len(rows)} != {pins['export_rows']}")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if not BEST_LINK.is_symlink() or BEST_LINK.resolve() != INIT_FROM.resolve():
        fail("BEST symlink is not the production checkpoint")
    if OUT.exists():
        fail(f"output already exists: {OUT}")
    if OUT.resolve() == INIT_FROM.resolve() or OUT.resolve() == BEST_LINK.resolve():
        fail("output resolves to BEST")
    if not (TRUNK / "config.json").is_file():
        fail("trunk config missing")
    if not (INIT_FROM / "model.safetensors").is_file():
        fail("warm start weights missing")
    from hyperlexical.classification_v2_readiness import audit
    from hyperlexical.holdout_guard import normalized_text_sha256
    from hyperlexical.identity_ledger import (
        IdentityLedger,
        assert_training_disjoint_from_reserve,
        derived_state,
    )

    ready = audit(export, prototype_witness=WITNESS)
    if not ready["ready"] or ready["blocker"] or ready["missing_support"] or ready["deficient_validation"]:
        fail(f"readiness is not READY: {ready.get('blocker')}")
    if ready["witness_sha256"] != WITNESS_SHA:
        fail("readiness witness hash drifted")
    if ready["n_classify_train"] != 4446:
        fail("training row count drifted")
    if ready["validation_support"]["internet-slang"] < 2 or ready["validation_support"]["memetic"] < 2:
        fail("validation floor is not met")
    if ready["family_weights"]["memetic"] != 2.0 or ready["family_weights"]["ai-native"] != 0.5:
        fail("family weights drifted")
    if abs(ready["applicability_weights"]["FAMILY_PRESENT"] - 0.9206266641842881) > 1e-12:
        fail("applicability weights drifted")
    ledger = IdentityLedger.load(LEDGER)
    assert_training_disjoint_from_reserve(rows, ledger)
    validation_rows = [
        row
        for row in rows
        if isinstance(row.get("provenance"), dict) and row["provenance"].get("admission") == "validation"
    ]
    if len(validation_rows) != 59:
        fail(f"expected 59 validation admissions, found {len(validation_rows)}")
    counts = {"internet-slang": 0, "memetic": 0}
    for row in validation_rows:
        if row.get("split") != "val" or row.get("class") != "OBSERVED":
            fail("validation admission left the val split")
        lineage = str(row.get("lineage") or "")
        if lineage not in counts:
            fail("validation admission left the two target families")
        counts[lineage] += 1
        digest = normalized_text_sha256(str(row.get("text") or ""))
        record = ledger.identity(digest)
        state = derived_state(record) if record else "MISSING"
        if state != "AVAILABLE":
            fail(f"validation identity is {state}")
        if record.get("training_consumed") or record.get("evaluation_reserved") or record.get("train_candidate"):
            fail("validation identity carries a training or reserve flag")
    if counts != {"internet-slang": 57, "memetic": 2}:
        fail(f"validation family counts drifted: {counts}")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if dirty:
        fail("trainer tree is dirty")
    return {
        "best_sha256": BEST_SHA,
        "best_unchanged": True,
        "export_rows": pins["export_rows"],
        "export_sha256": pins["export_sha256"],
        "git_head": head,
        "init_from": str(INIT_FROM),
        "jev": "OFF",
        "moves_best": False,
        "output": str(OUT),
        "prototype_witness": str(WITNESS),
        "prototype_witness_sha256": WITNESS_SHA,
        "readiness": ready["state"],
        "run": RUN_ID,
        "schedule": "select-006-candidate",
        "trainer_commit": head,
        "validation_rows": counts,
    }


def docker_env(pins: dict) -> dict[str, str]:
    return {
        "HF_HUB_OFFLINE": "1",
        "HLX_ALLOW_NO_HOLDOUT": "1",
        "HLX_TRAIN_EXPORT_PATH": pins["export_path"],
        "HLX_TRAIN_EXPORT_ROWS": str(pins["export_rows"]),
        "HLX_TRAIN_EXPORT_SHA256": pins["export_sha256"],
        "HLX_V2_PROTOTYPE_WITNESS": str(WITNESS),
        "HOME": "/home/morpheus",
        "HYPERLEX_ALLOW_TRAIN": "1",
        "HYPERLEX_CLASSIFICATION": "v2",
        "HYPERLEX_EXPORT_DIR": str(PRIVATE / "export"),
        "HYPERLEX_FILLER_FILTER": "strict",
        "HYPERLEX_INIT_EXPAND_VOCAB": "1",
        "HYPERLEX_INIT_FROM": str(INIT_FROM),
        "HYPERLEX_LAST_TRAINABLE": "2",
        "HYPERLEX_TRAIN_BATCH": "8",
        "HYPERLEX_TRAIN_LR": "2e-5",
        "HYPERLEX_TRAIN_OUT": str(OUT),
        "HYPERLEX_TRUNK_DIR": str(TRUNK),
        "HYPERLEX_UNBIND_CURRICULUM": "0",
        "HYPERLEX_UNBIND_EVERY_N": "1",
        "HYPERLEX_UNBIND_LOSS_WEIGHT": "1.0",
        "HYPERLEX_UNBIND_PRIMARY": "mixed",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": "/home/morpheus/Hyperlex/scripts/shadow",
        "PYTHONUNBUFFERED": "1",
        "TRANSFORMERS_OFFLINE": "1",
    }


def settle(checked: dict) -> dict:
    receipt = json.loads((OUT / "train-receipt.json").read_text(encoding="utf-8"))
    best = receipt.get("val_best") or {}
    calibration = receipt.get("classification_v2_calibration") or {}
    if calibration.get("reserve_used") or calibration.get("training_rows_used"):
        fail("calibration used the reserve or the training split")
    if calibration.get("surface") != "validation":
        fail("calibration surface is not validation")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed during training")
    primary = sudo_sha256(OUT / "model.safetensors")
    if primary != receipt.get("primary_weights_sha256"):
        fail("primary weight digest does not match the train receipt")
    per_family = best.get("per_family") or {}
    settlement = {
        "best_epoch": receipt.get("best_epoch"),
        "best_path": str(INIT_FROM),
        "best_sha256": BEST_SHA,
        "calibration": {
            "applicability_temperature": calibration.get("applicability_temperature"),
            "applicability_threshold": calibration.get("applicability_threshold"),
            "family_emit_threshold": calibration.get("family_emit_threshold"),
            "family_temperature": calibration.get("family_temperature"),
            "n_applicability": calibration.get("n_applicability"),
            "n_family": calibration.get("n_family"),
            "reserve_used": False,
            "surface": "validation",
            "training_rows_used": False,
        },
        "epochs_completed": receipt.get("epochs_completed"),
        "execution_integrity": "valid",
        "export_rows": checked["export_rows"],
        "export_sha256": checked["export_sha256"],
        "jev": "OFF",
        "last_trainable": receipt.get("last_trainable"),
        "moves_best": False,
        "output": str(OUT),
        "primary_weights_sha256": primary,
        "promotion": "later_explicit_action",
        "prototype_witness_sha256": WITNESS_SHA,
        "reserve_evaluation": {"ran": False, "reason": "the frozen reserve is not a tuning surface for this run"},
        "run": RUN_ID,
        "schedule": receipt.get("training_schedule"),
        "schema": "hyperlex.classification.v2.training_settlement.v1",
        "selection_score": best.get("selection_score"),
        "settlement": "RUN_COMPLETE",
        "stop_reason": receipt.get("stop_reason"),
        "trainer_commit": checked["trainer_commit"],
        "training_elapsed_seconds": receipt.get("training_elapsed_seconds"),
        "validation": {
            "active_family_macro_f1": best.get("active_family_macro_f1"),
            "applicability_macro_f1": best.get("applicability_macro_f1"),
            "observed_active_family_macro_f1": best.get("observed_active_family_macro_f1"),
            "per_family": per_family,
            "selection_score": best.get("selection_score"),
        },
    }
    write_private(PRIVATE / "SETTLEMENT.json", settlement)
    return settlement


def main() -> int:
    if not PINS.is_file():
        fail(f"validation export pins missing: {PINS}")
    pins = json.loads(PINS.read_text(encoding="utf-8"))
    checked = preflight(pins)
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(PRIVATE, 0o700)
    env = docker_env(pins)
    write_private(
        PRIVATE / "LAUNCH.json",
        {"schema": "hyperlex.classification.v2.launch.v1", **checked, "env": env},
    )
    command = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "--name",
        "hlx-classification-v2-train-ready",
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
        if key in {
            "HOME",
            "HF_HUB_OFFLINE",
            "PYTHONDONTWRITEBYTECODE",
            "PYTHONPATH",
            "PYTHONUNBUFFERED",
            "TRANSFORMERS_OFFLINE",
        }:
            continue
        command.extend(["-e", f"{key}={value}"])
    command.extend([IMAGE, "python", "-u", "-m", "hyperlexical.train", "--run"])
    log_path = PRIVATE / "train.log"
    print(json.dumps({"launching": str(OUT), "log": str(log_path)}, sort_keys=True), flush=True)
    with log_path.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, check=False)
    write_private(PRIVATE / "EXIT.json", {"code": completed.returncode})
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed during training")
    if completed.returncode != 0:
        fail(f"trainer exit {completed.returncode}")
    settlement = settle(checked)
    print(
        json.dumps(
            {
                "output": str(OUT),
                "primary_weights_sha256": settlement["primary_weights_sha256"],
                "selection_score": settlement["selection_score"],
                "trainer_exit": 0,
            },
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
