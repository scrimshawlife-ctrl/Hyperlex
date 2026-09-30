"""AUTHORIZE_V5_STAGE_A_003_FOCAL_LOSS_OBJECTIVE — freeze γ=2.0, no train.

Experiment-scoped exception allowing focal for
HLX-CLASSIFICATION-V5-STAGE-A-003-FOCAL-LOSS only. Does not modify
decide_evidence, dataset, class weights, or BEST.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
SURFACE = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-negative-evidence-surface-v1r8-20260930"
)
DATASET = SURFACE / "EVIDENCE_SURFACE.jsonl"
DATASET_SHA = "c0fdd82d1734585a7d852318ac5b390cc5e2c50908c0ef9f9eba4b3f7ebedc8b"
PARENT_AUTH = Path(
    "/home/morpheus/hlx-private/classification-v5-stage-a-train-v1r8-20260930"
)
PARENT_RUN = PARENT_AUTH / "classification-v5-stage-a-002"
PARENT_CONFIG_SHA = "2ce1b29bf2be54cc03ac25d66301bf0991226dffd3a1d94bcdaa7a48559d40af"
AUTH_DEST = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-train-v1r8-003-focal-20260930"
)
REPO_ARTIFACTS = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V5-STAGE-A-003-FOCAL-LOSS"
)
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
BLOCKED_RECEIPT_REPO = (
    REPO
    / "specs"
    / "007-hyperlexical-model"
    / "classification-v5-stage-a-003-focal-loss-blocked-receipt-20260930.json"
)

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


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def write_private(path: Path, payload: dict | str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    os.chmod(path, 0o600)


def write_repo(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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


def run_implementation_tests() -> dict[str, str]:
    """Run focused pytest module; map to mission test names."""
    test_path = (
        REPO / "tests" / "shadow" / "test_classification_v5_stage_a_003_focal.py"
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            str(test_path),
            "--tb=line",
        ],
        cwd=str(REPO),
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        print(completed.stdout, file=sys.stderr)
        print(completed.stderr, file=sys.stderr)
        fail("FOCAL_LOSS_IMPLEMENTATION_TEST=FAIL")
    # Individual asserts are in the pytest module; authorize records all PASS
    # only when the module exits 0.
    return {
        "GAMMA_ZERO_EQUIVALENCE": "PASS",
        "EASY_EXAMPLE_DOWNWEIGHT": "PASS",
        "HARD_EXAMPLE_EMPHASIS": "PASS",
        "CLASS_WEIGHT_PRESERVATION": "PASS",
        "PROVENANCE_WEIGHT_PRESERVATION": "PASS",
        "FINITE_LOSS_EXTREME_LOGITS": "PASS",
        "FOCAL_LOSS_IMPLEMENTATION_TEST": "PASS",
        "pytest_returncode": "0",
    }


def verify_parent() -> dict:
    settlement = json.loads((PARENT_RUN / "SETTLEMENT.json").read_text(encoding="utf-8"))
    thresh = json.loads((PARENT_RUN / "THRESHOLD_GRID.json").read_text(encoding="utf-8"))
    parent_resolved = json.loads(
        (PARENT_AUTH / "RESOLVED_TRAINING_CONFIG.json").read_text(encoding="utf-8")
    )
    if parent_resolved.get("training_config_sha256") != PARENT_CONFIG_SHA:
        fail("parent training_config_sha256 mismatch")
    gates = settlement["acceptance_gates"]
    if not gates["false_evidence_entry_rate_on_none"]["pass"]:
        fail("parent specificity unexpectedly FAIL")
    if gates["EVIDENCE_PRESENT_recall"]["pass"]:
        fail("parent PRESENT recall unexpectedly PASS")
    if int(thresh.get("n_passing") or 0) != 0:
        fail("parent threshold grid n_passing nonzero")
    geom = json.loads(
        (
            PARENT_RUN
            / "diagnostics"
            / "architecture_investigation"
            / "PROBABILITY_GEOMETRY.json"
        ).read_text(encoding="utf-8")
    )
    fn = geom["by_condition"]["PRESENT_FALSE_NONE"]
    return {
        "SPECIFICITY_FAILURE_REMEDIATED": True,
        "false_evidence_entry_rate_on_none": gates["false_evidence_entry_rate_on_none"][
            "value"
        ],
        "PRESENT_RECALL": gates["EVIDENCE_PRESENT_recall"]["value"],
        "THRESHOLD_GRID_N_PASSING": thresh.get("n_passing"),
        "PRESENT_TO_NONE_N": fn["n"],
        "PRESENT_TO_NONE_MEDIAN_P_NONE": fn["P_NO_EVIDENCE"]["median"],
        "PRESENT_TO_NONE_CONFIDENT_NONE_FRAC": fn["confident_none_among_present_fn"],
        "PRESENT_TO_NONE_NEAR_BOUNDARY_FRAC": fn["near_boundary_band"],
        "PROMOTION": "FAIL",
        "PARENT_TRAINING_CONFIG_SHA256": PARENT_CONFIG_SHA,
    }


def main() -> int:
    from hyperlexical.classification_v5_stage_a import (
        AUTHORIZED_SURFACE_RULE,
        compute_class_weights,
    )
    from hyperlexical.classification_v5_stage_a_003_focal import (
        EXPERIMENT_ID,
        FOCAL_ALPHA_POLICY,
        FOCAL_GAMMA,
        PARENT_EXPERIMENT_ID,
        authorization_contract_003,
        build_objective_spec,
        build_resolved_training_config_003,
        single_factor_diff,
    )

    if not BLOCKED_RECEIPT_REPO.is_file():
        fail("blocked preflight receipt missing; preserve provenance chain")
    if sha256_file(DATASET) != DATASET_SHA:
        fail("dataset digest mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if not TRUNK.exists():
        fail("tokenizer trunk missing")
    if AUTH_DEST.exists() and (AUTH_DEST / "AUTHORIZATION.json").exists():
        fail(f"authorization already sealed:{AUTH_DEST}")

    parent_pins = verify_parent()
    parent_resolved = json.loads(
        (PARENT_AUTH / "RESOLVED_TRAINING_CONFIG.json").read_text(encoding="utf-8")
    )

    impl_tests = run_implementation_tests()

    rows = []
    with DATASET.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    train_rows = [row for row in rows if row.get("split") == "train"]
    class_weights = compute_class_weights(train_rows)
    # Must match parent sealed class weights exactly for single-factor.
    parent_cw = parent_resolved["class_weight_report"]["class_weights"]
    if class_weights["class_weights"] != parent_cw:
        fail("recomputed class weights diverge from Stage-A-002")

    revision = code_revision()
    tokenizer_identity = f"local_files_only:{TRUNK.name}"
    objective = build_objective_spec(dataset_sha256=DATASET_SHA)
    resolved = build_resolved_training_config_003(
        dataset_sha256=DATASET_SHA,
        class_weight_report=class_weights,
        code_revision=revision,
        tokenizer_identity=tokenizer_identity,
        surface_rule=AUTHORIZED_SURFACE_RULE,
        focal_loss_spec_sha256=objective["FOCAL_LOSS_SPEC_SHA256"],
    )
    diff = single_factor_diff(parent_resolved, resolved)
    if diff["SINGLE_FACTOR_DIFF_STATUS"] != "PASS":
        fail(f"single_factor_diff_FAIL:{json.dumps(diff, sort_keys=True)}")

    auth = authorization_contract_003(
        dataset_sha256=DATASET_SHA,
        training_config_sha256=resolved["training_config_sha256"],
        focal_loss_spec_sha256=objective["FOCAL_LOSS_SPEC_SHA256"],
        code_revision=revision,
        single_factor_diff_status=diff["SINGLE_FACTOR_DIFF_STATUS"],
        implementation_tests=impl_tests,
    )
    auth["parent_verification"] = parent_pins
    auth["blocked_preflight_receipt"] = str(BLOCKED_RECEIPT_REPO.relative_to(REPO))
    auth["private_auth_dir"] = str(AUTH_DEST)
    auth["repo_artifacts_dir"] = str(REPO_ARTIFACTS.relative_to(REPO))
    from hyperlexical.classification_v5_stage_a import canonical_json, sha256_text

    auth["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in auth.items() if k != "receipt_sha256"})
    )

    if auth["OBJECTIVE_STATE"] != "FROZEN":
        fail("OBJECTIVE_STATE=NOT_READY after authorize assembly")

    AUTH_DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(AUTH_DEST, 0o700)
    REPO_ARTIFACTS.mkdir(parents=True, exist_ok=True)

    write_private(AUTH_DEST / "OBJECTIVE_SPEC.json", objective)
    write_private(AUTH_DEST / "RESOLVED_TRAINING_CONFIG.json", resolved)
    write_private(AUTH_DEST / "SINGLE_FACTOR_DIFF.json", diff)
    write_private(AUTH_DEST / "AUTHORIZATION.json", auth)
    write_private(AUTH_DEST / "CLASS_WEIGHTS.json", class_weights)
    write_private(
        AUTH_DEST / "IMPLEMENTATION_TESTS.json",
        {
            "schema": "hyperlex.classification.v5.stage_a_003_impl_tests.v1",
            "tests": impl_tests,
        },
    )

    # Repo-visible authoritative copies (hashed objective_spec required).
    write_repo(REPO_ARTIFACTS / "objective_spec.json", objective)
    write_repo(REPO_ARTIFACTS / "resolved_training_config.json", resolved)
    write_repo(REPO_ARTIFACTS / "single_factor_diff.json", diff)
    write_repo(REPO_ARTIFACTS / "authorization.json", auth)
    write_repo(
        REPO_ARTIFACTS / "implementation_tests.json",
        {
            "schema": "hyperlex.classification.v5.stage_a_003_impl_tests.v1",
            "tests": impl_tests,
        },
    )

    hashes = {path.name: sha256_file(path) for path in sorted(AUTH_DEST.iterdir()) if path.is_file()}
    write_private(
        AUTH_DEST / "ARTIFACT_HASHES.json",
        {
            "files": hashes,
            "schema": "hyperlex.classification.v5.stage_a_003_auth_artifact_hashes.v1",
        },
    )

    summary = {
        "SPECIFICATION_STATUS": "AUTHORIZED",
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "PARENT_EXPERIMENT": PARENT_EXPERIMENT_ID,
        "FOCAL_GAMMA": FOCAL_GAMMA,
        "FOCAL_ALPHA_POLICY": FOCAL_ALPHA_POLICY,
        "CLASS_WEIGHT_POLICY": "UNCHANGED_FROM_STAGE_A_002",
        "PROVENANCE_MULTIPLIER_POLICY": "UNCHANGED_FROM_STAGE_A_002",
        "GAMMA_ZERO_EQUIVALENCE": impl_tests["GAMMA_ZERO_EQUIVALENCE"],
        "EASY_EXAMPLE_DOWNWEIGHT": impl_tests["EASY_EXAMPLE_DOWNWEIGHT"],
        "HARD_EXAMPLE_EMPHASIS": impl_tests["HARD_EXAMPLE_EMPHASIS"],
        "CLASS_WEIGHT_PRESERVATION": impl_tests["CLASS_WEIGHT_PRESERVATION"],
        "PROVENANCE_WEIGHT_PRESERVATION": impl_tests["PROVENANCE_WEIGHT_PRESERVATION"],
        "FINITE_LOSS_EXTREME_LOGITS": impl_tests["FINITE_LOSS_EXTREME_LOGITS"],
        "SINGLE_FACTOR_DIFF_STATUS": diff["SINGLE_FACTOR_DIFF_STATUS"],
        "DATASET_SHA256": DATASET_SHA,
        "FOCAL_LOSS_SPEC_SHA256": objective["FOCAL_LOSS_SPEC_SHA256"],
        "TRAINING_CONFIG_SHA256": resolved["training_config_sha256"],
        "CODE_REVISION": revision,
        "SEED": 42,
        "OBJECTIVE_STATE": auth["OBJECTIVE_STATE"],
        "TRAINING_AUTHORIZATION": auth["TRAINING_AUTHORIZATION"],
        "H1_OBJECTIVE_LOSS_PRESSURE": "NOT_TESTED",
        "UNCERTAIN_POLICY_INVESTIGATION_PENDING": True,
        "BEST": "UNCHANGED",
        "RESERVE": "unused",
        "TRAIN": False,
        "NEXT_ACTION": auth["NEXT_ACTION"],
        "AUTHORIZATION_RECEIPT_SHA256": auth["receipt_sha256"],
        "private_auth_dir": str(AUTH_DEST),
        "blocked_preflight_preserved": True,
    }
    write_private(AUTH_DEST / "SUMMARY.json", summary)
    write_repo(REPO_ARTIFACTS / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
