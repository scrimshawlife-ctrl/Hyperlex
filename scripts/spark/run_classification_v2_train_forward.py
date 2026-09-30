"""TRAIN_CLASSIFICATION_V2 on the forward 18-family hub-filtered surface.

Pins residual hub boundary gate OPEN. Builds/uses civilian.v0.7.hub.jsonl and
forward prototype witness. Does not score the evaluation reserve or move BEST.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
MERGE_EXPORT = Path(
    "/home/morpheus/hlx-private/classification-v2-ontology-merge-pair-20260930/"
    "civilian.v0.6.merge.jsonl"
)
MERGE_EXPORT_SHA = "a8c064151973d7b2b9f439dc9fab499c69c2dd8a22a19206d7f486d970975130"
HUB = Path(
    "/home/morpheus/hlx-private/classification-v2-residual-hub-boundary-20260930/"
    "RESIDUAL_HUB_BOUNDARY.json"
)
HUB_SHA = "96a0587c06fac352872e462445f2eaaf773e35a48ab4c987e267b479cab72a83"
PRIVATE = Path("/home/morpheus/hlx-private/classification-v2-train-forward-20260930")
EXPORT = PRIVATE / "civilian.v0.7.hub.jsonl"
WITNESS = PRIVATE / "PROTOTYPE_WITNESS.json"
BOUNDARIES = Path(
    "/home/morpheus/hlx-private/classification-v2-ontology-merge-pair-20260930/"
    "FAMILY_SEMANTIC_BOUNDARIES.json"
)
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
INIT_FROM = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004"
)
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
OUT = Path(
    "/home/morpheus/.hyperlex/models/"
    "hyperlex-encoder-modernbert-base-seed-classification-v2-forward-hub"
)
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
BEST_LINK = Path("/home/morpheus/.hyperlex/models/BEST")
RUN_ID = "HLX-CLASSIFICATION-V2-FORWARD-HUB-20260930"

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
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


def materialize_export() -> dict:
    from hyperlexical.holdout_guard import normalized_text_sha256

    if sha256_file(MERGE_EXPORT) != MERGE_EXPORT_SHA:
        fail("merge export digest mismatch")
    hub = json.loads(HUB.read_text(encoding="utf-8"))
    if hub.get("artifact_sha256") != HUB_SHA:
        fail("hub boundary hash mismatch")
    if hub.get("training_gate") != "OPEN":
        fail("training gate is not OPEN")
    drops = {
        str(row["identity"])
        for row in hub.get("classifications") or []
        if row.get("decision") == "DROP"
    }
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    kept = 0
    removed = 0
    with MERGE_EXPORT.open(encoding="utf-8") as handle, EXPORT.open(
        "w", encoding="utf-8"
    ) as out:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("task") == "classify" and row.get("split") == "train":
                identity = normalized_text_sha256(str(row.get("text") or ""))
                if identity in drops:
                    removed += 1
                    continue
            out.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
            kept += 1
    os.chmod(EXPORT, 0o644)
    return {
        "drop_identities": len(drops),
        "export_path": str(EXPORT),
        "export_rows": kept,
        "export_sha256": sha256_file(EXPORT),
        "removed_train_rows": removed,
    }


def preflight() -> dict:
    from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY, FORWARD_ONTOLOGY
    from hyperlexical.classification_v2_readiness import audit
    from hyperlexical.identity_ledger import IdentityLedger, assert_training_disjoint_from_reserve

    if not FORWARD_ONTOLOGY:
        fail("HLX_V2_FORWARD_ONTOLOGY must be enabled")
    if len(ACTIVE_FAMILY_VOCABULARY) != 18:
        fail("forward vocabulary width drift")
    export_meta = materialize_export()
    if not WITNESS.is_file():
        fail(f"forward prototype witness missing: {WITNESS}")
    witness = json.loads(WITNESS.read_text(encoding="utf-8"))
    if not witness.get("forward_ontology"):
        fail("witness is not forward ontology")
    if "social-evaluation" not in (witness.get("prototype_families") or []) and not any(
        row.get("family") == "social-evaluation" and row.get("mode") != "EXACT_COPY"
        for row in witness.get("rows") or []
    ):
        # Accept either explicit prototype family list or non-exact-copy SE row.
        se = next((row for row in witness.get("rows") or [] if row.get("family") == "social-evaluation"), None)
        if se is None or se.get("mode") == "EXACT_COPY":
            fail("social-evaluation prototype row missing")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if not BEST_LINK.is_symlink() or BEST_LINK.resolve() != INIT_FROM.resolve():
        fail("BEST symlink is not the production checkpoint")
    if OUT.exists():
        fail(f"output already exists: {OUT}")
    boundaries = json.loads(BOUNDARIES.read_text(encoding="utf-8"))
    if boundaries.get("boundary_sha256") != (
        json.loads(
            Path(
                "/home/morpheus/hlx-private/classification-v2-ontology-merge-pair-20260930/"
                "ONTOLOGY_MERGE_PAIR.json"
            ).read_text(encoding="utf-8")
        ).get("boundary_sha256")
    ):
        fail("forward boundary pin mismatch")
    ready = audit(EXPORT, prototype_witness=WITNESS)
    if not ready["ready"] or ready["blocker"]:
        fail(f"readiness is not READY: {ready.get('blocker')} {ready.get('blockers')}")
    rows = [json.loads(line) for line in EXPORT.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != export_meta["export_rows"]:
        fail("export row count drifted")
    ledger = IdentityLedger.load(LEDGER)
    assert_training_disjoint_from_reserve(rows, ledger)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO, check=True, capture_output=True, text=True
    ).stdout.strip()
    return {
        "best_sha256": BEST_SHA,
        "boundary_sha256": boundaries["boundary_sha256"],
        "export_rows": export_meta["export_rows"],
        "export_sha256": export_meta["export_sha256"],
        "forward_ontology": True,
        "git_head": head,
        "hub_boundary_sha256": HUB_SHA,
        "jev": "OFF",
        "moves_best": False,
        "output": str(OUT),
        "prototype_witness_sha256": witness.get("witness_sha256"),
        "readiness": ready["state"],
        "removed_train_rows": export_meta["removed_train_rows"],
        "reserve_scored": False,
        "run": RUN_ID,
        "schema": "hyperlex.classification.v2.forward_hub_launch.v1",
    }


def docker_env(checked: dict) -> dict[str, str]:
    return {
        "HF_HUB_OFFLINE": "1",
        "HLX_ALLOW_NO_HOLDOUT": "1",
        "HLX_TRAIN_EXPORT_PATH": str(EXPORT),
        "HLX_TRAIN_EXPORT_ROWS": str(checked["export_rows"]),
        "HLX_TRAIN_EXPORT_SHA256": checked["export_sha256"],
        "HLX_V2_FORWARD_ONTOLOGY": "1",
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
    receipt = sudo_json(OUT / "train-receipt.json")
    best = receipt.get("val_best") or {}
    calibration = receipt.get("classification_v2_calibration") or {}
    surface = receipt.get("classification_v2_surface") or {}
    if calibration.get("reserve_used") or calibration.get("training_rows_used") or surface.get(
        "reserve_used"
    ):
        fail("calibration or surface diagnostic used the reserve")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed during training")
    settlement = {
        "best_epoch": receipt.get("best_epoch"),
        "best_sha256": BEST_SHA,
        "boundary_sha256": checked["boundary_sha256"],
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
        "export_sha256": checked["export_sha256"],
        "forward_ontology": True,
        "hub_boundary_sha256": HUB_SHA,
        "jev": "OFF",
        "moves_best": False,
        "output": str(OUT),
        "primary_weights_sha256": sudo_sha256(OUT / "model.safetensors"),
        "promotion": "not_eligible",
        "prototype_witness_sha256": checked["prototype_witness_sha256"],
        "reserve_evaluation": {
            "justified": False,
            "ran": False,
            "reason": "reserve scoring stays a later explicit action",
        },
        "run": RUN_ID,
        "schema": "hyperlex.classification.v2.forward_hub_settlement.v1",
        "selection_score": best.get("selection_score"),
        "validation": {
            "active_family_macro_f1": best.get("active_family_macro_f1"),
            "applicability_macro_f1": best.get("applicability_macro_f1"),
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
    env = docker_env(checked)
    write_private(PRIVATE / "LAUNCH.json", checked)
    command = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "--name",
        "hlx-classification-v2-train-forward-hub",
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
        "-e",
        "HLX_V2_FORWARD_ONTOLOGY=1",
    ]
    skip = {
        "HOME",
        "HF_HUB_OFFLINE",
        "PYTHONDONTWRITEBYTECODE",
        "PYTHONPATH",
        "PYTHONUNBUFFERED",
        "TRANSFORMERS_OFFLINE",
        "HLX_V2_FORWARD_ONTOLOGY",
    }
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
    print(
        json.dumps(
            {
                "best_epoch": settlement["best_epoch"],
                "forward_ontology": True,
                "moves_best": False,
                "primary_weights_sha256": settlement["primary_weights_sha256"],
                "reserve_scored": False,
                "selection_score": settlement["selection_score"],
                "validation": {
                    "active_family_macro_f1": settlement["validation"]["active_family_macro_f1"],
                    "prototype_family_macro_f1": settlement["validation"][
                        "prototype_family_macro_f1"
                    ],
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
