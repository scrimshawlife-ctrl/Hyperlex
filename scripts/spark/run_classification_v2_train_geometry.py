"""One prototype-geometry Classification v2 training run.

The changed variables are the fused family logits and the prototype
contrastive loss. Applicability, schedule, encoder depth, and BEST stay put.
Does not score the evaluation reserve.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
EXPORT = Path("/home/morpheus/hlx-private/classification-v2-surface-20260929/civilian.v0.3.jsonl")
EXPORT_SHA = "c4677011ea61f135c8fb82bed9d973dffe3a5db582d34421403e71498c5fd243"
EXPORT_ROWS = 9485
GEOMETRY = Path("/home/morpheus/hlx-private/classification-v2-geometry-20260930/PROTOTYPE_GEOMETRY.json")
GEOMETRY_SHA = "8392da2b05a256adea98dac39503ad05c948ac9f2bd7b04883bee56019c7e390"
BASE_WITNESS = Path("/home/morpheus/hlx-private/classification-v2-prototype-20260929/PROTOTYPE_WITNESS.json")
BASE_SHA = "7faa98239b2d4f39bf722c776543ded9a6c5959646c09c5db1e977cd7e69855d"
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
INIT_FROM = Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004")
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
OUT = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-classification-v2-geometry"
)
PRIVATE = Path("/home/morpheus/hlx-private/classification-v2-train-geometry-20260930")
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
BEST_LINK = Path("/home/morpheus/.hyperlex/models/BEST")
RUN_ID = "HLX-CLASSIFICATION-V2-GEOMETRY-20260930"
PRIOR_FAMILY_MACRO = 0.1960828268105939

sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
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


def preflight() -> dict:
    from hyperlexical.classification_v2_readiness import audit
    from hyperlexical.identity_ledger import IdentityLedger, assert_training_disjoint_from_reserve

    if sha256_file(EXPORT) != EXPORT_SHA:
        fail("export digest mismatch")
    witness = json.loads(GEOMETRY.read_text(encoding="utf-8"))
    if witness.get("geometry_sha256") != GEOMETRY_SHA:
        fail("geometry witness hash mismatch")
    if witness.get("prototypes") != "FROZEN":
        fail("prototypes are not frozen")
    if json.loads(BASE_WITNESS.read_text(encoding="utf-8")).get("witness_sha256") != BASE_SHA:
        fail("base prototype witness changed")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if not BEST_LINK.is_symlink() or BEST_LINK.resolve() != INIT_FROM.resolve():
        fail("BEST symlink is not the production checkpoint")
    if OUT.exists():
        fail(f"output already exists: {OUT}")
    ready = audit(EXPORT, prototype_witness=GEOMETRY)
    if not ready["ready"] or ready["blocker"]:
        fail(f"readiness is not READY: {ready.get('blocker')}")
    rows = [json.loads(line) for line in EXPORT.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != EXPORT_ROWS:
        fail("export row count drifted")
    ledger = IdentityLedger.load(LEDGER)
    assert_training_disjoint_from_reserve(rows, ledger)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO, check=True, capture_output=True, text=True
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO, check=True, capture_output=True, text=True
    ).stdout.strip()
    if dirty:
        fail("trainer tree is dirty")
    return {
        "best_sha256": BEST_SHA,
        "export_rows": EXPORT_ROWS,
        "export_sha256": EXPORT_SHA,
        "geometry_sha256": GEOMETRY_SHA,
        "git_head": head,
        "jev": "OFF",
        "moves_best": False,
        "output": str(OUT),
        "readiness": ready["state"],
        "run": RUN_ID,
    }


def docker_env() -> dict[str, str]:
    return {
        "HF_HUB_OFFLINE": "1",
        "HLX_ALLOW_NO_HOLDOUT": "1",
        "HLX_TRAIN_EXPORT_PATH": str(EXPORT),
        "HLX_TRAIN_EXPORT_ROWS": str(EXPORT_ROWS),
        "HLX_TRAIN_EXPORT_SHA256": EXPORT_SHA,
        "HLX_V2_GEOMETRY_WITNESS": str(GEOMETRY),
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


def _breadth(per_family: dict) -> dict:
    from hyperlexical.classification_v2 import EXACT_COPY_FAMILIES

    def count(threshold: float, names=None) -> int:
        total = 0
        for name, stats in per_family.items():
            if names is not None and name not in names:
                continue
            f1 = stats.get("f1")
            if f1 is not None and float(f1) > threshold:
                total += 1
        return total

    new_names = [name for name in per_family if name not in EXACT_COPY_FAMILIES]
    return {
        "f1_gt_0": count(0.0),
        "f1_ge_0_20": count(0.20 - 1e-12),
        "f1_ge_0_50": count(0.50 - 1e-12),
        "new_family_f1_gt_0": count(0.0, new_names),
    }


def settle(checked: dict) -> dict:
    receipt = json.loads((OUT / "train-receipt.json").read_text(encoding="utf-8"))
    best = receipt.get("val_best") or {}
    calibration = receipt.get("classification_v2_calibration") or {}
    surface = receipt.get("classification_v2_surface") or {}
    geometry = receipt.get("classification_v2_family_geometry") or {}
    invariance = surface.get("invariance") or {}
    if calibration.get("reserve_used") or calibration.get("training_rows_used") or surface.get("reserve_used"):
        fail("calibration or surface diagnostic used the reserve")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed during training")
    macro = best.get("active_family_macro_f1")
    improved = macro is not None and float(macro) > PRIOR_FAMILY_MACRO
    invariance_pass = bool(invariance.get("pass"))
    breadth = _breadth(best.get("per_family") or {})
    if improved and not invariance_pass:
        architecture = "SETTLED_INVALID"
    elif improved and invariance_pass and breadth["new_family_f1_gt_0"] > 1:
        architecture = "INTERNAL_IMPROVED"
    else:
        architecture = "INTERNAL_SHORT"
    reserve_justified = architecture == "INTERNAL_IMPROVED"
    settlement = {
        "architecture_validation": architecture,
        "best_epoch": receipt.get("best_epoch"),
        "best_sha256": BEST_SHA,
        "breadth": breadth,
        "calibration": {
            "applicability_temperature": calibration.get("applicability_temperature"),
            "applicability_threshold": calibration.get("applicability_threshold"),
            "family_emit_threshold": calibration.get("family_emit_threshold"),
            "family_temperature": calibration.get("family_temperature"),
            "reserve_used": False,
            "surface": "validation",
            "training_rows_used": False,
        },
        "epochs_completed": receipt.get("epochs_completed"),
        "export_sha256": EXPORT_SHA,
        "family_similarity_margin": geometry.get("family_similarity_margin"),
        "geometry_sha256": GEOMETRY_SHA,
        "invariance": invariance,
        "invariance_pass": invariance_pass,
        "jev": "OFF",
        "moves_best": False,
        "output": str(OUT),
        "primary_weights_sha256": sudo_sha256(OUT / "model.safetensors"),
        "prior_active_family_macro_f1": PRIOR_FAMILY_MACRO,
        "promotion": "not_eligible",
        "reserve_evaluation": {
            "justified": reserve_justified,
            "ran": False,
            "reason": "reserve scoring stays a later explicit action",
        },
        "run": RUN_ID,
        "schema": "hyperlex.classification.v2.geometry_training_settlement.v1",
        "selection_score": best.get("selection_score"),
        "validation": {
            "active_family_macro_f1": macro,
            "applicability_macro_f1": best.get("applicability_macro_f1"),
            "family_macro_f1_by_surface": (surface.get("family_macro_f1_by_surface")),
            "observed_active_family_macro_f1": best.get("observed_active_family_macro_f1"),
            "per_family": best.get("per_family"),
            "prototype_family_macro_f1": best.get("prototype_family_macro_f1"),
            "selection_score": best.get("selection_score"),
        },
    }
    write_private(PRIVATE / "SETTLEMENT.json", settlement)
    return settlement


def main() -> int:
    checked = preflight()
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    env = docker_env()
    write_private(PRIVATE / "LAUNCH.json", {"schema": "hyperlex.classification.v2.launch.v1", **checked})
    command = [
        "docker", "run", "--rm", "--gpus", "all", "--name", "hlx-classification-v2-train-geometry",
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
    skip = {"HOME", "HF_HUB_OFFLINE", "PYTHONDONTWRITEBYTECODE", "PYTHONPATH", "PYTHONUNBUFFERED", "TRANSFORMERS_OFFLINE"}
    for key, value in sorted(env.items()):
        if key in skip:
            continue
        command.extend(["-e", f"{key}={value}"])
    command.extend([IMAGE, "python", "-u", "-m", "hyperlexical.train", "--run"])
    log_path = PRIVATE / "train.log"
    print(json.dumps({"launching": str(OUT), "log": str(log_path)}), flush=True)
    with log_path.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, check=False)
    write_private(PRIVATE / "EXIT.json", {"code": completed.returncode})
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed during training")
    if completed.returncode != 0:
        fail(f"trainer exit {completed.returncode}")
    settlement = settle(checked)
    print(json.dumps({
        "architecture_validation": settlement["architecture_validation"],
        "best_epoch": settlement["best_epoch"],
        "breadth": settlement["breadth"],
        "invariance_pass": settlement["invariance_pass"],
        "primary_weights_sha256": settlement["primary_weights_sha256"],
        "reserve_justified": settlement["reserve_evaluation"]["justified"],
        "selection_score": settlement["selection_score"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
