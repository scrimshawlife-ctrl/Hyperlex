"""REPAIR_IDENT_FILTERED_FACTORIZED_CHECKPOINT_SERIALIZATION — Spark seal.

Artifact-repair only. Scans retained selected-run weight artifacts for exact
epoch-11 factorized heads. If absent, seals REPAIR_NOT_POSSIBLE_WITHOUT_RETRAIN
without manufacturing a candidate. Does not retrain, move BEST, or alter V1R2.
"""

from __future__ import annotations

import hashlib
import json
import os
import struct
import subprocess
import sys
from pathlib import Path

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

AUTH_DEST = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-ident-filtered-factorized-train-v1-20261001"
)
RUN_ROOT = AUTH_DEST / "classification-v5-stage-a-ident-filtered-factorized-001"
REPAIR_DEST = AUTH_DEST / "checkpoint_repair"
SELECTED = RUN_ROOT / "selected" / "model.safetensors"
SELECTED_PUBLISHED = Path(
    "/home/morpheus/.hyperlex/models/"
    "hyperlex-encoder-modernbert-base-seed-classification-v5-stage-a-ident-filtered-factorized-001"
    "/model.safetensors"
)
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
PREVIOUS_STAGE_A_BEST_SHA = (
    "cd2829c1b5fb823fc03f18efe66a7387124ef44be2545b9e385a17eb6237bf5c"
)
STAGE_A_BEST_PATH_FILE = Path("/home/morpheus/.hyperlex/models/STAGE_A_BEST.path")
REPO_ARTIFACTS = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-001"
)
SPEC_DIR = REPO / "specs" / "007-hyperlexical-model"

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sudo_sha256(path: Path) -> str:
    try:
        return sha256_file(path)
    except PermissionError:
        completed = subprocess.run(
            ["sudo", "-n", "sha256sum", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.split()[0]


def safetensors_keys(path: Path) -> list[str]:
    opener = path.open
    try:
        handle = opener("rb")
    except PermissionError:
        completed = subprocess.run(
            ["sudo", "-n", "python3", "-c",
             "import struct,json,sys; p=sys.argv[1]; f=open(p,'rb'); "
             "n=struct.unpack('<Q',f.read(8))[0]; h=json.loads(f.read(n)); "
             "print(json.dumps([k for k in h if k!='__metadata__']))",
             str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return list(json.loads(completed.stdout))
    with handle:
        header_len = struct.unpack("<Q", handle.read(8))[0]
        header = json.loads(handle.read(header_len))
    return [k for k in header.keys() if k != "__metadata__"]


def write_private(path: Path, payload: dict | str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        if isinstance(payload, str):
            path.write_text(payload, encoding="utf-8")
        else:
            path.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        os.chmod(path, 0o600)
    except PermissionError:
        text = (
            payload
            if isinstance(payload, str)
            else json.dumps(payload, indent=2, sort_keys=True) + "\n"
        )
        subprocess.run(
            ["sudo", "-n", "tee", str(path)],
            input=text,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(["sudo", "-n", "chmod", "600", str(path)], check=True)


def write_repo(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def code_revision() -> str:
    env = os.environ.get("HLX_V5_STAGE_A_CODE_REVISION")
    if env:
        return env
    completed = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        return completed.stdout.strip()
    return "UNKNOWN"


def live_trainer_present() -> bool:
    completed = subprocess.run(["ps", "aux"], check=True, capture_output=True, text=True)
    needles = (
        "ident_filtered_factorized",
        "ident-filtered-factorized",
        "run_classification_v5_stage_a_ident_filtered_factorized_train",
    )
    hits = []
    for line in completed.stdout.splitlines():
        if any(n in line for n in needles) and "checkpoint_repair" not in line:
            hits.append(line)
    return bool(hits)


def collect_candidate_artifacts() -> list[dict]:
    artifacts: list[dict] = []
    completed = subprocess.run(
        [
            "sudo",
            "-n",
            "find",
            str(RUN_ROOT / "tmp_checkpoints"),
            "-name",
            "model.safetensors",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    paths = [Path(p) for p in completed.stdout.splitlines() if p.strip()]
    for path in sorted(paths):
        meta_path = path.parent / "meta.json"
        epoch = None
        role = "tmp_selected_candidate"
        meta_raw = subprocess.run(
            ["sudo", "-n", "cat", str(meta_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        if meta_raw.returncode == 0 and meta_raw.stdout.strip():
            meta = json.loads(meta_raw.stdout)
            epoch = meta.get("epoch")
            role = meta.get("role") or role
        artifacts.append(
            {
                "path": str(path),
                "role": role,
                "epoch": epoch,
                "sha256": sudo_sha256(path),
                "keys": safetensors_keys(path),
            }
        )
    for path, role, epoch in (
        (SELECTED, "selected_persisted", 11),
        (SELECTED_PUBLISHED, "selected_published", 11),
    ):
        try:
            sha = sudo_sha256(path)
            keys = safetensors_keys(path)
        except Exception as exc:
            artifacts.append(
                {
                    "path": str(path),
                    "role": role,
                    "epoch": epoch,
                    "sha256": None,
                    "keys": [],
                    "error": str(exc),
                }
            )
            continue
        artifacts.append(
            {
                "path": str(path),
                "role": role,
                "epoch": epoch,
                "sha256": sha,
                "keys": keys,
            }
        )
    return artifacts


def current_stage_a_best_sha() -> str:
    if STAGE_A_BEST_PATH_FILE.exists():
        target = Path(STAGE_A_BEST_PATH_FILE.read_text(encoding="utf-8").strip())
        weights = target / "model.safetensors"
        try:
            return sudo_sha256(weights)
        except Exception:
            pass
    return PREVIOUS_STAGE_A_BEST_SHA


def main() -> int:
    from hyperlexical.classification_v5_stage_a_gold_identifiability_filter import (
        V1R2_DATASET_SHA256_PIN,
    )
    from hyperlexical.classification_v5_stage_a_ident_filtered_authorize import (
        AUTHORIZED_AUTH_RECEIPT_SHA256,
        AUTHORIZED_TRAINING_CONFIG_SHA256,
        EXPERIMENT_ID,
    )
    from hyperlexical.classification_v5_stage_a_ident_filtered_checkpoint_repair import (
        INCOMPLETE_CHECKPOINT_PROMOTABILITY,
        INCOMPLETE_CHECKPOINT_STATUS,
        INCOMPLETE_SELECTED_CHECKPOINT_SHA256,
        REPAIR_RULE,
        SELECTED_EPOCH,
        audit_candidate_sources,
        build_repair_receipt,
        serialization_regression_report,
        verify_selected_epoch_identity,
    )
    from hyperlexical.classification_v5_stage_a_ident_filtered_promote import (
        PREVIOUS_STAGE_A_BEST_SHA256,
    )

    REPAIR_DEST.mkdir(mode=0o700, parents=True, exist_ok=True)

    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        print("BEST_mutated_preflight", file=sys.stderr)
        return 2
    stage_a_now = current_stage_a_best_sha()
    if stage_a_now != PREVIOUS_STAGE_A_BEST_SHA256:
        print(f"STAGE_A_BEST_unexpected:{stage_a_now}", file=sys.stderr)
        return 2

    artifacts = collect_candidate_artifacts()
    source_audit = audit_candidate_sources(artifacts=artifacts)
    source_audit["live_trainer_present"] = live_trainer_present()
    source_audit["hit_count"] = len(source_audit.get("recoverable_sources") or [])
    source_audit["A_retained_trainer_state_before_flatten"] = False
    source_audit["B_retained_in_memory_or_export"] = False
    source_audit["C_deterministic_selected_epoch_state"] = bool(
        source_audit.get("exact_selected_epoch_heads_available")
    )
    source_audit["NO_LIVE_TRAINER"] = not source_audit["live_trainer_present"]

    identity = verify_selected_epoch_identity(
        experiment_id=EXPERIMENT_ID,
        selected_epoch=SELECTED_EPOCH,
        selected_encoder_sha256=INCOMPLETE_SELECTED_CHECKPOINT_SHA256,
        dataset_sha256=V1R2_DATASET_SHA256_PIN,
        training_config_sha256=AUTHORIZED_TRAINING_CONFIG_SHA256,
        authorization_sha256=AUTHORIZED_AUTH_RECEIPT_SHA256,
    )
    serialization_tests = serialization_regression_report()
    revision = code_revision()

    historical_status = {
        "sha256": INCOMPLETE_SELECTED_CHECKPOINT_SHA256,
        "status": INCOMPLETE_CHECKPOINT_STATUS,
        "promotability": INCOMPLETE_CHECKPOINT_PROMOTABILITY,
        "deleted": False,
        "note": (
            "encoder-only packaging artifact from SETTLED_PASS selected epoch 11; "
            "exact relation_head/resolvability_head tensors were not retained"
        ),
        "repair_rule": REPAIR_RULE,
    }

    # Mark historical incomplete artifacts without overwriting weights.
    write_private(
        RUN_ROOT / "selected" / "HISTORICAL_PACKAGING_STATUS.json",
        historical_status,
    )
    write_private(
        SELECTED_PUBLISHED.parent / "HISTORICAL_PACKAGING_STATUS.json",
        historical_status,
    )
    write_private(REPAIR_DEST / "SOURCE_AUDIT.json", source_audit)
    write_private(REPAIR_DEST / "IDENTITY.json", identity)
    write_private(REPAIR_DEST / "SERIALIZATION_REGRESSION.json", serialization_tests)

    receipt = build_repair_receipt(
        source_audit=source_audit,
        identity=identity,
        serialization_tests=serialization_tests,
        code_revision=revision,
        repaired_checkpoint_sha256=None,
        tensor_parity=None,
        cold_load={
            "pass": False,
            "attempted": False,
            "reason": "no_authoritative_selected_epoch_heads",
            "trainer_memory_used": False,
        },
        validation_replay={
            "pass": False,
            "attempted": False,
            "reason": "reconstruction_not_attempted",
        },
        logit_parity={
            "pass": False,
            "attempted": False,
            "reason": "no_selected_run_logits_retained_with_heads",
            "decision_mismatch_count": None,
            "max_abs_logit_delta": None,
        },
    )
    # Preserve scientific result as SETTLED_PASS source of truth, while repair fails.
    assert receipt["SCIENTIFIC_RESULT"] == "SETTLED_PASS"
    assert receipt["STAGE_A_BEST_MUTATED"] is False
    assert receipt["MODEL_WIDE_BEST_MUTATED"] is False
    assert receipt["PROMOTION_LOADABLE"] is False

    write_private(REPAIR_DEST / "CHECKPOINT_REPAIR_RECEIPT.json", receipt)
    write_private(REPAIR_DEST / "SUMMARY.json", {
        "CHECKPOINT_REPAIR": receipt["CHECKPOINT_REPAIR"],
        "REPAIR_STATUS": receipt["REPAIR_STATUS"],
        "PROMOTION_LOADABLE": receipt["PROMOTION_LOADABLE"],
        "NEXT_ACTION": receipt["NEXT_ACTION"],
        "STAGE_A_BEST": receipt["STAGE_A_BEST"],
        "MODEL_WIDE_BEST": receipt["MODEL_WIDE_BEST"],
        "CHECKPOINT_REPAIR_RECEIPT_SHA256": receipt[
            "CHECKPOINT_REPAIR_RECEIPT_SHA256"
        ],
        "hit_count": source_audit["hit_count"],
        "exact_selected_epoch_heads_available": source_audit[
            "exact_selected_epoch_heads_available"
        ],
    })
    write_private(AUTH_DEST / "CHECKPOINT_REPAIR.json", receipt)

    write_repo(REPO_ARTIFACTS / "checkpoint_repair_receipt.json", receipt)
    write_repo(REPO_ARTIFACTS / "checkpoint_repair_summary.json", {
        "CHECKPOINT_REPAIR": receipt["CHECKPOINT_REPAIR"],
        "REPAIR_STATUS": receipt["REPAIR_STATUS"],
        "PROMOTION_LOADABLE": receipt["PROMOTION_LOADABLE"],
        "NEXT_ACTION": receipt["NEXT_ACTION"],
        "STAGE_A_BEST": receipt["STAGE_A_BEST"],
        "MODEL_WIDE_BEST": receipt["MODEL_WIDE_BEST"],
        "CHECKPOINT_REPAIR_RECEIPT_SHA256": receipt[
            "CHECKPOINT_REPAIR_RECEIPT_SHA256"
        ],
    })
    write_repo(
        SPEC_DIR
        / "classification-v5-stage-a-ident-filtered-factorized-checkpoint-repair-receipt-20261001.json",
        receipt,
    )

    print(json.dumps({
        "CHECKPOINT_REPAIR": receipt["CHECKPOINT_REPAIR"],
        "REPAIR_STATUS": receipt["REPAIR_STATUS"],
        "PROMOTION_LOADABLE": receipt["PROMOTION_LOADABLE"],
        "NEXT_ACTION": receipt["NEXT_ACTION"],
        "hit_count": source_audit["hit_count"],
        "CHECKPOINT_REPAIR_RECEIPT_SHA256": receipt[
            "CHECKPOINT_REPAIR_RECEIPT_SHA256"
        ],
        "serialization_regression_pass": serialization_tests["pass"],
        "STAGE_A_BEST": receipt["STAGE_A_BEST"],
        "MODEL_WIDE_BEST": receipt["MODEL_WIDE_BEST"],
    }, indent=2, sort_keys=True))
    return 0 if receipt["CHECKPOINT_REPAIR"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
