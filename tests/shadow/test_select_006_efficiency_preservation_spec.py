"""SELECT-006 spec seals non-inferiority. It does not train or score."""

import inspect
from pathlib import Path

import pytest

from hyperlexical.select_006_efficiency_preservation import (
    EPSILON,
    EXPERIMENT_ID,
    HYPOTHESIS,
    NEW_ROLES,
    NEXT_TRANSITION,
    QUESTION,
    _expected_observations,
    apply_decision,
    baseline_env,
    candidate_env,
    preregistration,
    schema_errors,
    seal_specification,
    threshold_authorization,
    vocabulary_expansion_pin,
    sha256_text,
    canonical_json,
)

HEAD = "a" * 40


def _metrics(**overrides):
    base = {
        "classification_accuracy": 0.5,
        "classify_macro_f1_nonnone": 0.5,
        "observed_label_accuracy": 0.5,
        "unbind_clean_exact": 0.5,
    }
    base.update(overrides)
    return base


def test_preregistration_is_exact_non_inferiority_and_does_not_train():
    pre = preregistration()
    assert pre["experiment_id"] == EXPERIMENT_ID
    assert pre["hypothesis"] == HYPOTHESIS
    assert pre["question"] == QUESTION
    assert pre["epsilon"] == 0
    assert EPSILON == 0
    assert "exact non-inferiority" in pre["epsilon_justification"]
    assert pre["inherited_from_select_005_settlement"] is False
    assert pre["select_005_citation"]["use_as_authorization"] is False
    assert pre["training_launch_authorized"] is False
    assert pre["training_started"] is False
    assert pre["evaluation_reserve"]["decision"] == "REUSE_FORBIDDEN"
    assert pre["evaluation_reserve"]["select_006_reserve"] is None
    assert pre["efficiency_gate"]["wall_clock_is_a_gate"] is False
    assert schema_errors(pre, "select-006-preregistration.schema.json") == []


def test_schema_rejects_a_nonzero_epsilon():
    pre = preregistration()
    pre["epsilon"] = 0.01
    assert schema_errors(pre, "select-006-preregistration.schema.json")


def test_vocabulary_pin_names_the_three_new_roles_and_blocks_the_loader():
    pin = vocabulary_expansion_pin()
    assert pin["new_role_names_in_sorted_order"] == ["pos_6", "pos_7", "unknown"]
    assert list(NEW_ROLES) == pin["new_role_names_in_sorted_order"]
    assert pin["warm_start_role_count"] == 10
    assert pin["target_role_count"] == 13
    assert pin["mapped_existing_roles"] == 10
    assert pin["newly_initialized_roles"] == 3
    assert pin["init_expand_vocab"] is True
    assert pin["initialization_policy"]["new_rows"] == "zeros"
    assert pin["initialization_policy"]["seed_used"] is False
    assert pin["execution_loader_status"] == "NOT_YET_IMPLEMENTED"
    assert pin["launch_blocked_until_loader_honors_zeros"] is True
    assert pin["unk_token_is_not_a_new_role"] is True
    assert pin["filler_expansion"]["newly_initialized_fillers"] == 29


def test_schedules_and_shared_settings_stay_pinned():
    pre = preregistration()
    assert pre["control_schedule"] == {
        "early_stopping": "disabled",
        "max_epochs": 40,
        "restore_best": True,
    }
    assert pre["candidate_schedule"]["max_epochs"] == 12
    assert pre["candidate_schedule"]["minimum_epochs"] == 4
    assert pre["candidate_schedule"]["early_stopping_patience"] == 4
    assert pre["candidate_schedule"]["improvement"] == "strict"
    assert pre["candidate_schedule"]["ties"] == "keep_earlier"
    shared = pre["shared_settings"]
    assert shared["learning_rate"] == "2e-5"
    assert shared["batch_size"] == 8
    assert shared["gradient_accumulation"] == 1
    assert shared["seed_policy"] == "HLX_SEED_UNSET_FROZEN"
    assert shared["selection_metric"] == "classify_macro_f1_nonnone"
    assert "HLX_SEED" in shared["must_remain_unset"]
    assert "HYPERLEX_EARLY_STOP_PATIENCE" not in baseline_env()
    assert candidate_env()["HYPERLEX_EARLY_STOP_PATIENCE"] == "4"
    assert candidate_env()["HYPERLEX_INIT_EXPAND_VOCAB"] == "1"
    assert "HYPERLEX_TRAIN_OUT" not in baseline_env()
    assert "HYPERLEX_TRAIN_OUT" not in candidate_env()


def test_invalid_loader_is_excluded_from_results():
    exclusion = preregistration()["invalid_loader_exclusion"]
    assert exclusion["path"].endswith("launch-001/invalid-loader-001")
    assert exclusion["status"] == "PERMANENTLY_NON_RESULT"
    assert "baseline comparison" in exclusion["forbidden_uses"]
    assert "threshold calculation" in exclusion["forbidden_uses"]
    assert "BEST selection" in exclusion["forbidden_uses"]
    assert "SELECT-006 initialization" in exclusion["forbidden_uses"]
    assert "aggregate reporting" in exclusion["forbidden_uses"]


def test_threshold_passes_only_when_every_gate_passes():
    threshold = threshold_authorization("b" * 64)
    assert threshold["epsilon"] == 0
    assert threshold["training_launch_authorized"] is False
    assert threshold["decision_rule"]["primary_equality"] == "PASS"
    assert threshold["decision_rule"]["primary_strict_increase_required"] is False
    assert threshold["decision_rule"]["compensation"] is False
    assert schema_errors(threshold, "select-006-threshold-authorization.schema.json") == []
    tie = apply_decision(
        control=_metrics(),
        candidate=_metrics(),
        control_steps=100,
        candidate_steps=25,
    )
    assert tie["pass"] is True
    assert tie["outcome"] == "PASS"
    drop = apply_decision(
        control=_metrics(),
        candidate=_metrics(classify_macro_f1_nonnone=0.499),
        control_steps=100,
        candidate_steps=25,
    )
    assert drop["pass"] is False
    degraded = apply_decision(
        control=_metrics(),
        candidate=_metrics(classification_accuracy=0.49),
        control_steps=100,
        candidate_steps=25,
    )
    assert degraded["pass"] is False
    boundary = apply_decision(
        control=_metrics(),
        candidate=_metrics(),
        control_steps=100,
        candidate_steps=26,
    )
    assert boundary["pass"] is False
    missing = apply_decision(
        control=_metrics(),
        candidate={"classify_macro_f1_nonnone": 0.5},
        control_steps=100,
        candidate_steps=25,
    )
    assert missing["pass"] is False
    assert any(gate["reason"] == "MISSING" for gate in missing["gates"])


def test_noncomputable_metrics_fail_closed():
    result = apply_decision(
        control=_metrics(unbind_clean_exact=None),
        candidate=_metrics(unbind_clean_exact=None),
        control_steps=100,
        candidate_steps=25,
    )
    assert result["pass"] is False
    assert any(gate["reason"] == "NON_COMPUTABLE" for gate in result["gates"])
    steps = apply_decision(
        control=_metrics(),
        candidate=_metrics(),
        control_steps=0,
        candidate_steps=0,
    )
    assert steps["pass"] is False


def test_seal_writes_private_artifacts_and_refuses_a_pin_mismatch(tmp_path: Path):
    observations = _expected_observations()
    hashes = seal_specification(tmp_path / "spec-001", observations=observations, repository_head=HEAD)
    written = sorted(path.name for path in (tmp_path / "spec-001").iterdir())
    assert written == [
        "ARTIFACT_MANIFEST.json",
        "BASELINE_ENV.json",
        "CANDIDATE_ENV.json",
        "DATA_EVALUATION_DEPENDENCIES.json",
        "SELECT_006_PREREGISTRATION.json",
        "SELECT_006_THRESHOLD_AUTHORIZATION.json",
        "SPEC_RECEIPT.json",
        "VOCABULARY_EXPANSION_PIN.json",
    ]
    pre_text = (tmp_path / "spec-001" / "SELECT_006_PREREGISTRATION.json").read_text(encoding="utf-8")
    assert hashes["SELECT_006_PREREGISTRATION.json"] == sha256_text(pre_text)
    receipt = (tmp_path / "spec-001" / "SPEC_RECEIPT.json").read_text(encoding="utf-8")
    assert NEXT_TRANSITION in receipt
    assert "training_launch_authorized" in receipt
    assert '"training_started": false' in receipt
    mismatched = dict(observations)
    mismatched["warm_start_sha256"] = "c" * 64
    with pytest.raises(SystemExit, match="WARM_START_PIN_MISMATCH"):
        seal_specification(tmp_path / "spec-002", observations=mismatched, repository_head=HEAD)
    assert not (tmp_path / "spec-002").exists()
    with pytest.raises(SystemExit, match="SPEC_SEAL_FAILURE"):
        seal_specification(
            tmp_path / "spec-003",
            observations=observations,
            repository_head=HEAD,
            repository_dirty=True,
        )
    assert not (tmp_path / "spec-003").exists()


def test_threshold_binds_the_preregistration_bytes():
    pre = preregistration()
    digest = sha256_text(canonical_json(pre))
    assert threshold_authorization(digest)["preregistration_sha256"] == digest


def test_module_does_not_import_torch():
    source = inspect.getsource(apply_decision)
    module = inspect.getsource(preregistration)
    assert "import torch" not in source
    assert "import torch" not in module
