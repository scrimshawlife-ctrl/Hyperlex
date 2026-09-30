"""TRAIN_V5_STAGE_A_TWO_STAGE_ONCE — fail-closed two-stage train runner.

Requires sealed AUTHORIZATION from AUTHORIZE_V5_STAGE_A_TWO_STAGE_TRAIN_V1.
Does not move BEST. Does not consume reserve.
Set HLX_V5_STAGE_A_EXECUTE_TRAIN=1 to execute the one authorized run.

Also supports:
  --design-freeze   historical design seal helper (does not authorize/train)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

SURFACE = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-negative-evidence-surface-v1r9-20260930"
)
DATASET = SURFACE / "EVIDENCE_SURFACE.jsonl"
DATASET_SHA = "8d4be8301b89b191841342fe11ef647c838b32e56e6d133b610c232264c5d00a"
ARCHITECTURE_RECEIPT_SHA = (
    "631427cc4c1b09bac1e3a2c5e081c7e9fc0947babda26c03cb73895f47754697"
)
AUTH_DEST = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-two-stage-train-v1-20260930"
)
AUTH_FILE = AUTH_DEST / "AUTHORIZATION.json"
RESOLVED = AUTH_DEST / "RESOLVED_TRAINING_CONFIG.json"
WEIGHTS = AUTH_DEST / "TWO_STAGE_CLASS_WEIGHTS.json"
RUN_ROOT = AUTH_DEST / "classification-v5-stage-a-two-stage-001"
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
REPO_ARTIFACTS = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-001"
)
SPEC_DIR = REPO / "specs" / "007-hyperlexical-model"

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def write_repo(path: Path, payload: dict | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


def code_revision() -> str:
    override = (os.environ.get("HLX_V5_STAGE_A_CODE_REVISION") or "").strip()
    if override:
        return override
    completed = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def design_freeze() -> dict:
    from hyperlexical.classification_v5_stage_a_two_stage import (
        ARCHITECTURE_RECEIPT_SHA256,
        AUTHORIZE_RULE,
        EXPERIMENT_ID,
        TWO_STAGE_RULE,
        design_freeze_receipt,
    )

    # Design freeze is historical; do not overwrite the sealed architecture receipt.
    receipt = design_freeze_receipt(code_revision=code_revision())
    summary = {
        "AUTHORIZE_RULE_NEXT": AUTHORIZE_RULE,
        "ARCHITECTURE_RECEIPT_SHA256_PIN": ARCHITECTURE_RECEIPT_SHA256,
        "BEST": "UNCHANGED",
        "DESIGN_STATE": "FROZEN",
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "NOTE": (
            "Historical helper only. Canonical architecture pin remains "
            f"{ARCHITECTURE_RECEIPT_SHA256}; do not reseal over it."
        ),
        "RULE": TWO_STAGE_RULE,
        "TRAIN": False,
        "TRAIN_AUTHORIZED": False,
        "design_receipt_sha256_ephemeral": receipt["design_receipt_sha256"],
        "next_action": AUTHORIZE_RULE,
    }
    write_repo(REPO_ARTIFACTS / "design_freeze_helper_summary.json", summary)
    return summary


def refuse_or_gate_train() -> None:
    from hyperlexical.classification_v5_stage_a_two_stage import (
        ARCHITECTURE_RECEIPT_SHA256,
        AUTHORIZE_RULE,
        AUTHORIZED_BEST_SHA,
        AUTHORIZED_DATASET_SHA,
        EXPERIMENT_ID,
        TRAIN_ONCE_ACTION,
        runner_authorization_checks,
    )

    if not AUTH_FILE.is_file():
        fail(
            "REFUSE: no sealed AUTHORIZATION.json for two-stage Stage-A. "
            f"Next action: {AUTHORIZE_RULE}."
        )
    if not RESOLVED.is_file() or not WEIGHTS.is_file():
        fail("REFUSE: missing RESOLVED_TRAINING_CONFIG or TWO_STAGE_CLASS_WEIGHTS.")

    auth = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
    resolved = json.loads(RESOLVED.read_text(encoding="utf-8"))
    weights = json.loads(WEIGHTS.read_text(encoding="utf-8"))

    checks = runner_authorization_checks(
        train_authorized=bool(auth.get("TRAIN_AUTHORIZED") or auth.get("train_authorized")),
        experiment_id=str(auth.get("EXPERIMENT_ID") or ""),
        dataset_sha256=str(auth.get("DATASET_SHA256") or ""),
        architecture_receipt_sha256=str(
            auth.get("ARCHITECTURE_RECEIPT_SHA256") or ""
        ),
        resolved_config_sha256=str(resolved.get("training_config_sha256") or ""),
        authorized_config_sha256=str(auth.get("TRAINING_CONFIG_SHA256") or ""),
        best_sha256=str(auth.get("CURRENT_BEST") or auth.get("authorized_best_sha256") or ""),
        surface_readiness=str(auth.get("SURFACE_READINESS") or ""),
        label_mapping=str(auth.get("LABEL_MAPPING") or ""),
        label_provenance_invalid_rows=int(auth.get("label_provenance_invalid") or 0),
        prior_run_count=int(auth.get("prior_run_count") or 0),
        reserve_consumed=bool(auth.get("RESERVE_CONSUMED")),
        class_weight_artifact_sha256=str(
            weights.get("CLASS_WEIGHT_ARTIFACT_SHA256") or ""
        ),
        authorized_class_weight_artifact_sha256=str(
            auth.get("CLASS_WEIGHT_ARTIFACT_SHA256") or ""
        ),
    )
    if not checks["pass"]:
        fail(f"REFUSE: authorization gates failed:{json.dumps(checks, sort_keys=True)}")

    # Literal weight bind — runner must not recompute.
    if resolved.get("gate1_class_weights_literal") != weights.get("literal_weights", {}).get(
        "gate1"
    ):
        fail("REFUSE: gate1 literal weights mismatch vs weight artifact")
    if resolved.get("gate2_class_weights_literal") != weights.get("literal_weights", {}).get(
        "gate2"
    ):
        fail("REFUSE: gate2 literal weights mismatch vs weight artifact")
    if resolved.get("dataset_sha256") != AUTHORIZED_DATASET_SHA:
        fail("REFUSE: resolved dataset mismatch")
    if resolved.get("architecture_receipt_sha256") != ARCHITECTURE_RECEIPT_SHA256:
        fail("REFUSE: resolved architecture receipt mismatch")
    if resolved.get("best_encoder_sha256") != AUTHORIZED_BEST_SHA:
        fail("REFUSE: resolved BEST mismatch")
    if resolved.get("experiment_id") != EXPERIMENT_ID:
        fail("REFUSE: resolved experiment_id mismatch")

    if RUN_ROOT.exists() and any(RUN_ROOT.iterdir()):
        fail("REFUSE: prior run artifacts present (TRAINING_RUN_LIMIT=1)")

    if os.environ.get("HLX_V5_STAGE_A_EXECUTE_TRAIN") != "1":
        fail(
            "REFUSE: authorization sealed but execute flag unset. "
            f"Set HLX_V5_STAGE_A_EXECUTE_TRAIN=1 for {TRAIN_ONCE_ACTION}."
        )

    # Train body lands in a later CLEAR; this pass only authorizes.
    fail(
        "REFUSE: two-stage train execution body not enabled in authorize pass. "
        f"Authorization is ready for {TRAIN_ONCE_ACTION}."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stage-A two-stage train runner (fail-closed)."
    )
    parser.add_argument(
        "--design-freeze",
        action="store_true",
        help="Emit ephemeral design helper summary (does not reseal architecture).",
    )
    args = parser.parse_args(argv)
    if args.design_freeze:
        print(json.dumps(design_freeze(), indent=2, sort_keys=True))
        return 0
    refuse_or_gate_train()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
