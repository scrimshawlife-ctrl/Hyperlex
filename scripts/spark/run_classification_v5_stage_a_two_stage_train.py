"""HYPERLEX_V5_STAGE_A_TWO_STAGE_DECISION_GRAPH_V1 — train runner (fail-closed).

Spec/design modes:
  --design-freeze   seal public design receipt + summary (no train, no auth)
  (default)         refuse train unless sealed AUTHORIZATION + EXECUTE flag

Does not train in this design pass. Does not mutate V1R9, BEST, or reserve.
Authorization is a separate CLEAR: AUTHORIZE_V5_STAGE_A_TWO_STAGE_TRAIN_V1.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
# Local/worktree override for design-freeze seals outside Spark.
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

SURFACE = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-negative-evidence-surface-v1r9-20260930"
)
DATASET = SURFACE / "EVIDENCE_SURFACE.jsonl"
DATASET_SHA = "8d4be8301b89b191841342fe11ef647c838b32e56e6d133b610c232264c5d00a"
AUTH_DEST = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-two-stage-train-v1-20260930"
)
AUTH_FILE = AUTH_DEST / "AUTHORIZATION.json"
RESOLVED = AUTH_DEST / "RESOLVED_TRAINING_CONFIG.json"
RUN_ROOT = AUTH_DEST / "classification-v5-stage-a-005-two-stage"
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
PARENT_FLAT_SELECTED_SHA = (
    "82840630a89ea9e9b34fdfc010d455e6bbfce05ecfcb29abe2929505e9e21fdd"
)
REPO_ARTIFACTS = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V5-STAGE-A-005-TWO-STAGE"
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


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def design_freeze() -> dict:
    from hyperlexical.classification_v5_stage_a_two_stage import (
        AUTHORIZE_RULE,
        EXPERIMENT_ID,
        TWO_STAGE_RULE,
        design_freeze_receipt,
    )

    receipt = design_freeze_receipt(code_revision=code_revision())
    summary = {
        "AUTHORIZE_RULE_NEXT": AUTHORIZE_RULE,
        "BEST": "UNCHANGED",
        "BEST_SHA256": receipt["BEST_SHA256"],
        "DATASET_SHA256": receipt["DATASET_SHA256"],
        "DESIGN_STATE": "FROZEN",
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "PARENT_FLAT_SELECTED_CHECKPOINT_SHA256": PARENT_FLAT_SELECTED_SHA,
        "PARENT_PRIMARY_DECISION": receipt["PARENT_PRIMARY_DECISION"],
        "RESERVE": "unused",
        "RULE": TWO_STAGE_RULE,
        "TRAIN": False,
        "TRAIN_AUTHORIZED": False,
        "design_receipt_sha256": receipt["design_receipt_sha256"],
        "flat_head_status": receipt["compatibility"]["flat_head_status"],
        "lambda_gate2": receipt["loss"]["lambda_gate2"],
        "last_trainable_encoder_layers": receipt["architecture"][
            "last_trainable_encoder_layers"
        ],
        "n_threshold_combinations": 100,
        "next_action": AUTHORIZE_RULE,
    }
    write_repo(REPO_ARTIFACTS / "design_freeze_receipt.json", receipt)
    write_repo(REPO_ARTIFACTS / "design_freeze_summary.json", summary)
    write_repo(
        SPEC_DIR
        / "classification-v5-stage-a-two-stage-decision-graph-v1-receipt-20260930.json",
        receipt,
    )
    return summary


def refuse_unauthorized_train() -> None:
    from hyperlexical.classification_v5_stage_a_two_stage import AUTHORIZE_RULE

    if not AUTH_FILE.is_file():
        fail(
            "REFUSE: no sealed AUTHORIZATION.json for two-stage Stage-A. "
            f"Next action: {AUTHORIZE_RULE}. Design-only path: --design-freeze."
        )
    auth = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
    if not bool(auth.get("TRAIN_AUTHORIZED") or auth.get("train_authorized")):
        fail("REFUSE: AUTHORIZATION present but TRAIN_AUTHORIZED is false.")
    if auth.get("AUTHORIZE_RULE") != AUTHORIZE_RULE and auth.get(
        "authorize_rule"
    ) != AUTHORIZE_RULE:
        fail(f"REFUSE: AUTHORIZE_RULE must be {AUTHORIZE_RULE}.")
    if os.environ.get("HLX_V5_STAGE_A_EXECUTE_TRAIN") != "1":
        fail(
            "REFUSE: authorization sealed but execute flag unset. "
            "Set HLX_V5_STAGE_A_EXECUTE_TRAIN=1 for the single authorized run."
        )
    fail(
        "REFUSE: two-stage train body not implemented in design pass. "
        "Authorization CLEAR must precede mechanical train implementation."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stage-A two-stage decision-graph train runner (fail-closed)."
    )
    parser.add_argument(
        "--design-freeze",
        action="store_true",
        help="Seal design freeze receipt only (no train, no authorization).",
    )
    args = parser.parse_args(argv)
    if args.design_freeze:
        summary = design_freeze()
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    refuse_unauthorized_train()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
