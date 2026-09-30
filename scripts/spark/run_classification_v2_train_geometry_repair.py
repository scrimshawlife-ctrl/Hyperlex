"""One Classification v2 geometry-repair training run.

Boundaries structure the supervised contrastive loss. Family logits stay on the
learned residual head. Does not score the evaluation reserve and does not move BEST.
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
BOUNDARIES = Path(
    "/home/morpheus/hlx-private/classification-v2-boundaries-20260930/FAMILY_SEMANTIC_BOUNDARIES.json"
)
BOUNDARY_SHA = "0ca6f34ce1abf68388e443371672ca36e16028079a175b6775e1968900e1c52f"
SEPARATION_SHA = "ab698d342d2d276f81d4baf3fed609bb6f8bf88cd6810bb1d1998c5e409f63c3"
WITNESS = Path("/home/morpheus/hlx-private/classification-v2-prototype-20260929/PROTOTYPE_WITNESS.json")
WITNESS_SHA = "7faa98239b2d4f39bf722c776543ded9a6c5959646c09c5db1e977cd7e69855d"
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
INIT_FROM = Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004")
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
OUT = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-classification-v2-geometry-repair"
)
PRIVATE = Path("/home/morpheus/hlx-private/classification-v2-train-geometry-repair-20260930")
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
BEST_LINK = Path("/home/morpheus/.hyperlex/models/BEST")
RUN_ID = "HLX-CLASSIFICATION-V2-GEOMETRY-REPAIR-20260930"
PRIOR_FAMILY_MACRO = 0.1960828268105939
PRIOR_PROTO_MACRO = 0.041352657004830914

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


def sudo_json(path: Path) -> dict:
    completed = subprocess.run(
        ["sudo", "-n", "cat", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def write_private(path: Path, payload: dict) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def preflight() -> dict:
    from hyperlexical.classification_v2_geometry_repair import assess_boundary_for_repair, hard_negatives_from_boundaries
    from hyperlexical.classification_v2_readiness import audit
    from hyperlexical.identity_ledger import IdentityLedger, assert_training_disjoint_from_reserve

    if sha256_file(EXPORT) != EXPORT_SHA:
        fail("export digest mismatch")
    boundaries = json.loads(BOUNDARIES.read_text(encoding="utf-8"))
    if boundaries.get("boundary_sha256") != BOUNDARY_SHA:
        fail("boundary hash mismatch")
    if boundaries.get("separation_sha256") != SEPARATION_SHA:
        fail("separation hash mismatch")
    checked = assess_boundary_for_repair(boundaries)
    if not checked.get("pass"):
        fail(f"boundary repair assess failed: {checked}")
    if json.loads(WITNESS.read_text(encoding="utf-8")).get("witness_sha256") != WITNESS_SHA:
        fail("prototype witness changed")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if not BEST_LINK.is_symlink() or BEST_LINK.resolve() != INIT_FROM.resolve():
        fail("BEST symlink is not the production checkpoint")
    if OUT.exists():
        fail(f"output already exists: {OUT}")
    ready = audit(EXPORT, prototype_witness=WITNESS)
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
        "boundary_sha256": BOUNDARY_SHA,
        "export_rows": EXPORT_ROWS,
        "export_sha256": EXPORT_SHA,
        "git_head": head,
        "hard_negatives": hard_negatives_from_boundaries(boundaries),
        "jev": "OFF",
        "moves_best": False,
        "output": str(OUT),
        "readiness": ready["state"],
        "run": RUN_ID,
        "separation_sha256": SEPARATION_SHA,
        "sparse_families": checked["sparse_families"],
    }


def docker_env() -> dict[str, str]:
    return {
        "HF_HUB_OFFLINE": "1",
        "HLX_ALLOW_NO_HOLDOUT": "1",
        "HLX_TRAIN_EXPORT_PATH": str(EXPORT),
        "HLX_TRAIN_EXPORT_ROWS": str(EXPORT_ROWS),
        "HLX_TRAIN_EXPORT_SHA256": EXPORT_SHA,
        "HLX_V2_GEOMETRY_REPAIR": str(BOUNDARIES),
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


def _breadth(per_family: dict) -> dict:
    from hyperlexical.classification_v2 import EXACT_COPY_FAMILIES

    def count(threshold: float, names=None) -> int:
        total = 0
        for name, stats in per_family.items():
            if names is not None and name not in names:
                continue
            if name == "none":
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
    from hyperlexical.classification_v2_geometry_repair import repair_readiness_gate

    receipt = sudo_json(OUT / "train-receipt.json")
    best = receipt.get("val_best") or {}
    calibration = receipt.get("classification_v2_calibration") or {}
    surface = receipt.get("classification_v2_surface") or {}
    prior = receipt.get("classification_v2_geometry_repair_prior") or sudo_json(
        OUT / "classification-v2-geometry-repair-prior.json"
    )
    post = receipt.get("classification_v2_geometry_repair") or sudo_json(
        OUT / "classification-v2-geometry-repair.json"
    )
    invariance = surface.get("invariance") or {}
    if calibration.get("reserve_used") or calibration.get("training_rows_used") or surface.get("reserve_used"):
        fail("calibration or surface diagnostic used the reserve")
    if prior.get("reserve_used") or post.get("reserve_used"):
        fail("geometry diagnostic used the reserve")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed during training")
    breadth = _breadth(best.get("per_family") or {})
    gate = repair_readiness_gate(
        active_family_macro_f1=float(best["active_family_macro_f1"]),
        prototype_family_macro_f1=float(best["prototype_family_macro_f1"]),
        new_family_f1_gt_0=int(breadth["new_family_f1_gt_0"]),
        median_margin=float(post["median_margin"]),
        prior_median_margin=float(prior["median_margin"]),
        high_collision_rows=int(post["high_collision_rows"]),
        prior_high_collision_rows=int(prior["high_collision_rows"]),
        invariance_pass=bool(invariance.get("pass")),
    )
    settlement = {
        "architecture_validation": gate["status"],
        "best_epoch": receipt.get("best_epoch"),
        "best_sha256": BEST_SHA,
        "boundary_sha256": BOUNDARY_SHA,
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
        "canonical_logits": "learned_residual",
        "epochs_completed": receipt.get("epochs_completed"),
        "export_sha256": EXPORT_SHA,
        "gate": gate,
        "geometry_post": {
            "high_collision_rows": post.get("high_collision_rows"),
            "mean_margin": post.get("mean_margin"),
            "median_margin": post.get("median_margin"),
            "n_family": post.get("n_family"),
            "per_family": post.get("per_family"),
        },
        "geometry_prior": {
            "high_collision_rows": prior.get("high_collision_rows"),
            "mean_margin": prior.get("mean_margin"),
            "median_margin": prior.get("median_margin"),
            "n_family": prior.get("n_family"),
        },
        "hard_negatives": checked["hard_negatives"],
        "invariance": invariance,
        "invariance_pass": bool(invariance.get("pass")),
        "jev": "OFF",
        "moves_best": False,
        "output": str(OUT),
        "primary_weights_sha256": sudo_sha256(OUT / "model.safetensors"),
        "prior_active_family_macro_f1": PRIOR_FAMILY_MACRO,
        "prior_prototype_family_macro_f1": PRIOR_PROTO_MACRO,
        "promotion": "not_eligible",
        "reserve_evaluation": {
            "justified": gate["reserve_justified"],
            "ran": False,
            "reason": "reserve scoring stays a later explicit action",
        },
        "run": RUN_ID,
        "schema": "hyperlex.classification.v2.geometry_repair_settlement.v1",
        "selection_score": best.get("selection_score"),
        "separation_sha256": SEPARATION_SHA,
        "sparse_families": checked["sparse_families"],
        "validation": {
            "active_family_macro_f1": best.get("active_family_macro_f1"),
            "applicability_macro_f1": best.get("applicability_macro_f1"),
            "family_macro_f1_by_surface": surface.get("family_macro_f1_by_surface"),
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
        "docker", "run", "--rm", "--gpus", "all", "--name", "hlx-classification-v2-train-geometry-repair",
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
        "gate": settlement["gate"],
        "geometry_post": {
            "high_collision_rows": settlement["geometry_post"]["high_collision_rows"],
            "median_margin": settlement["geometry_post"]["median_margin"],
        },
        "geometry_prior": settlement["geometry_prior"],
        "invariance_pass": settlement["invariance_pass"],
        "primary_weights_sha256": settlement["primary_weights_sha256"],
        "reserve_justified": settlement["reserve_evaluation"]["justified"],
        "selection_score": settlement["selection_score"],
        "validation": {
            "active_family_macro_f1": settlement["validation"]["active_family_macro_f1"],
            "prototype_family_macro_f1": settlement["validation"]["prototype_family_macro_f1"],
        },
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
