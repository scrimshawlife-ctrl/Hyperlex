"""V5 Stage-A train recipe + label provenance tests. No GPU train."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v5_stage_a import (  # noqa: E402
    ACCEPTANCE_GATES,
    AUTHORIZE_RULE,
    AUTHORIZED_DATASET_SHA,
    AUTHORIZED_SURFACE_RULE,
    BEST_SHA,
    EVIDENCE_LABELS,
    EXPERIMENT_ID,
    LABEL_PROVENANCE_RULE,
    STAGE_A_RULE,
    THRESHOLD_GRID,
    TRAIN_HYPERPARAMS,
    attach_and_validate_label_provenance,
    authorization_gate_checks,
    build_resolved_training_config,
    calibrate_thresholds,
    compute_class_weights,
    decide_evidence,
    derive_label_provenance,
    evaluate_decisions,
    false_evidence_entry_rate_on_none,
    softmax_logits,
    stage_a_authorization_contract,
    stage_a_macro_f1,
    validate_label_provenance,
)


def _row(
    *,
    identity: str,
    label: str,
    subtype: str,
    provenance: str = "INFERRED",
    families: list[str] | None = None,
    required: str = "false",
    missing: list[str] | None = None,
    pair_group_id: str | None = None,
    source_url: str | None = None,
    topic_domain: str | None = None,
) -> dict:
    return {
        "identity": identity,
        "evidence_label": label,
        "evidence_subtype": subtype,
        "provenance": provenance,
        "active_family_support": families or [],
        "required_evidence_present": required,
        "missing_required_semantics": missing or [],
        "pair_group_id": pair_group_id,
        "source_url": source_url,
        "topic_domain": topic_domain,
        "split": "train",
        "text": f"sample {identity}",
    }


def test_frozen_recipe_constants():
    assert STAGE_A_RULE == "HYPERLEX_CLASSIFICATION_V5_STAGE_A_TRAIN_V1"
    assert LABEL_PROVENANCE_RULE == "HYPERLEX_V5_STAGE_A_LABEL_PROVENANCE_V1"
    assert AUTHORIZE_RULE == "AUTHORIZE_V5_STAGE_A_NEXT_RUN_ON_REMEDIATED_SURFACE"
    assert EXPERIMENT_ID == "HLX-CLASSIFICATION-V5-STAGE-A-004"
    assert AUTHORIZED_DATASET_SHA.startswith("8d4be830")
    assert AUTHORIZED_SURFACE_RULE.endswith("V1R9")
    assert BEST_SHA.startswith("9fba0f66")
    assert EVIDENCE_LABELS == ("NO_EVIDENCE", "EVIDENCE_PRESENT", "UNCERTAIN")
    assert TRAIN_HYPERPARAMS["optimizer"] == "AdamW"
    assert TRAIN_HYPERPARAMS["learning_rate"] == 2e-5
    assert TRAIN_HYPERPARAMS["micro_batch_size"] == 8
    assert TRAIN_HYPERPARAMS["max_epochs"] == 12
    assert TRAIN_HYPERPARAMS["last_trainable"] == 2
    assert TRAIN_HYPERPARAMS["seed"] == 42
    assert ACCEPTANCE_GATES["false_evidence_entry_rate_on_none_max"] == 0.05
    assert ACCEPTANCE_GATES["EVIDENCE_PRESENT_recall_min"] == 0.70
    assert ACCEPTANCE_GATES["NO_EVIDENCE_recall_min"] == 0.90
    assert ACCEPTANCE_GATES["optimize_family_metrics_before_stage_a_pass"] is False
    assert THRESHOLD_GRID["require_none_lt_present"] is True
    assert 0.50 in THRESHOLD_GRID["none_thresholds"]
    assert 0.95 in THRESHOLD_GRID["present_thresholds"]


def test_decide_evidence_and_macro_f1():
    assert decide_evidence(0.9, none_threshold=0.5, present_threshold=0.75) == (
        "EVIDENCE_PRESENT"
    )
    assert decide_evidence(0.2, none_threshold=0.5, present_threshold=0.75) == (
        "NO_EVIDENCE"
    )
    assert decide_evidence(0.6, none_threshold=0.5, present_threshold=0.75) == (
        "UNCERTAIN"
    )
    probs = softmax_logits([0.0, 3.0, 0.0])
    assert probs["EVIDENCE_PRESENT"] > 0.8
    golds = ["NO_EVIDENCE", "EVIDENCE_PRESENT", "UNCERTAIN"]
    preds = ["NO_EVIDENCE", "EVIDENCE_PRESENT", "UNCERTAIN"]
    assert stage_a_macro_f1(golds, preds) == 1.0
    assert false_evidence_entry_rate_on_none(
        ["NO_EVIDENCE"] * 10, ["EVIDENCE_PRESENT"] + ["NO_EVIDENCE"] * 9
    ) == 0.1


def test_class_weights_from_train_only_policy():
    rows = (
        [_row(identity=f"n{i}", label="NO_EVIDENCE", subtype="HARD_NONE", required="false")
         for i in range(40)]
        + [
            _row(
                identity=f"p{i}",
                label="EVIDENCE_PRESENT",
                subtype="POSITIVE_EVIDENCE",
                families=["internet-slang"],
                required="true",
                provenance="OBSERVED",
                source_url="https://example.test/p",
            )
            for i in range(10)
        ]
        + [
            _row(
                identity=f"u{i}",
                label="UNCERTAIN",
                subtype="AMBIGUOUS_EVIDENCE",
                required="uncertain",
            )
            for i in range(5)
        ]
    )
    report = compute_class_weights(rows)
    weights = report["class_weights"]
    assert set(weights) == set(EVIDENCE_LABELS)
    assert all(0.50 <= weights[label] <= 2.00 for label in EVIDENCE_LABELS)
    mean = sum(weights.values()) / len(weights)
    # After clip the mean may drift from 1.0; pre-clip normalized mean is 1.0.
    assert abs(sum(report["normalized_weights"].values()) / 3 - 1.0) < 1e-9
    assert mean > 0


def test_threshold_selection_fail_closed():
    golds = ["NO_EVIDENCE"] * 20 + ["EVIDENCE_PRESENT"] * 20 + ["UNCERTAIN"] * 5
    # Scores that cannot satisfy all three gates simultaneously.
    scores = [0.6] * 45
    result = calibrate_thresholds(golds, scores)
    assert result["feasible"] is False
    assert result["disposition"] == "SETTLED_FAIL"


def test_threshold_selection_feasible_path():
    golds = ["NO_EVIDENCE"] * 100 + ["EVIDENCE_PRESENT"] * 50 + ["UNCERTAIN"] * 20
    scores = [0.05] * 100 + [0.95] * 50 + [0.55] * 20
    result = calibrate_thresholds(golds, scores)
    assert result["feasible"] is True
    assert result["chosen"]["none_threshold"] < result["chosen"]["present_threshold"]
    metrics = evaluate_decisions(
        golds,
        [
            decide_evidence(
                s,
                none_threshold=result["chosen"]["none_threshold"],
                present_threshold=result["chosen"]["present_threshold"],
            )
            for s in scores
        ],
    )
    assert metrics["acceptance_pass"] is True


def test_label_provenance_valid_combinations():
    present = _row(
        identity="pos1",
        label="EVIDENCE_PRESENT",
        subtype="POSITIVE_EVIDENCE",
        families=["internet-slang"],
        required="true",
        provenance="OBSERVED",
        source_url="https://en.wiktionary.org/wiki/yeet",
    )
    none = _row(
        identity="none1",
        label="NO_EVIDENCE",
        subtype="ORDINARY_DOMAIN_NONE",
        required="false",
        missing=["family_required_core:internet-slang"],
    )
    uncertain = _row(
        identity="unc1",
        label="UNCERTAIN",
        subtype="AMBIGUOUS_EVIDENCE",
        required="uncertain",
    )
    for row in (present, none, uncertain):
        prov = derive_label_provenance(row)
        errors = validate_label_provenance(row, prov)
        assert errors == [], (row["identity"], errors, prov)
        assert len(prov["decision_sha256"]) == 64
        assert prov["authority"] not in {
            "MODEL_PREDICTED",
            "JEV",
            "HEURISTIC_UNVERSIONED",
            "UNKNOWN",
        }


def test_label_provenance_rejects_model_authority_and_bad_combo():
    row = _row(
        identity="bad1",
        label="EVIDENCE_PRESENT",
        subtype="POSITIVE_EVIDENCE",
        families=["internet-slang"],
        required="true",
    )
    prov = derive_label_provenance(row)
    bad = dict(prov)
    bad["authority"] = "MODEL_PREDICTED"
    bad["derivation"] = "DIRECT"
    errors = validate_label_provenance(row, bad)
    assert "forbidden_authority" in errors or "authority_not_allowed" in errors


def test_attach_and_validate_label_provenance_stats():
    rows = [
        _row(
            identity="pos1",
            label="EVIDENCE_PRESENT",
            subtype="POSITIVE_EVIDENCE",
            families=["internet-slang"],
            required="true",
        ),
        _row(
            identity="none1",
            label="NO_EVIDENCE",
            subtype="HARD_NONE",
            required="false",
            missing=["no_active_family_support"],
        ),
        _row(
            identity="unc1",
            label="UNCERTAIN",
            subtype="AMBIGUOUS_EVIDENCE",
            required="uncertain",
        ),
    ]
    report = attach_and_validate_label_provenance(rows)
    assert report["pass"] is True
    assert report["invalid_provenance_rows"] == 0
    assert report["n_valid"] == 3
    assert report["rule"] == LABEL_PROVENANCE_RULE
    assert "counts_by_authority" in report["statistics"]


def test_authorization_contract_and_gate():
    class_weights = compute_class_weights(
        [
            _row(
                identity="n1",
                label="NO_EVIDENCE",
                subtype="HARD_NONE",
                required="false",
            ),
            _row(
                identity="p1",
                label="EVIDENCE_PRESENT",
                subtype="POSITIVE_EVIDENCE",
                families=["internet-slang"],
                required="true",
            ),
            _row(
                identity="u1",
                label="UNCERTAIN",
                subtype="AMBIGUOUS_EVIDENCE",
                required="uncertain",
            ),
        ]
    )
    resolved = build_resolved_training_config(
        dataset_sha256=AUTHORIZED_DATASET_SHA,
        class_weight_report=class_weights,
        code_revision="deadbeef",
        tokenizer_identity="local_files_only:ModernBERT-base",
        surface_rule="HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R7",
    )
    assert len(resolved["training_config_sha256"]) == 64
    assert resolved["best_encoder_sha256"] == BEST_SHA
    assert resolved["loss"]["name"] == "weighted_cross_entropy"
    assert resolved["trainable"]["mutate_best"] is False
    auth = stage_a_authorization_contract(
        dataset_sha256=AUTHORIZED_DATASET_SHA,
        training_config_sha256=resolved["training_config_sha256"],
        code_revision="deadbeef",
    )
    assert auth["TRAIN_AUTHORIZED"] is True
    assert auth["TRAINING_STATUS"] == "AUTHORIZED_NOT_STARTED"
    assert auth["SCIENTIFIC_RESULT"] == "NOT_COMPUTABLE"
    gate = authorization_gate_checks(
        train_authorized=True,
        dataset_sha256=AUTHORIZED_DATASET_SHA,
        surface_readiness="PASS",
        resolved_config_sha256=resolved["training_config_sha256"],
        authorized_config_sha256=resolved["training_config_sha256"],
        current_best=BEST_SHA,
        reserve_consumed=False,
    )
    assert gate["pass"] is True
    fail_gate = authorization_gate_checks(
        train_authorized=False,
        dataset_sha256=AUTHORIZED_DATASET_SHA,
        surface_readiness="PASS",
        resolved_config_sha256=resolved["training_config_sha256"],
        authorized_config_sha256=resolved["training_config_sha256"],
        current_best=BEST_SHA,
        reserve_consumed=False,
    )
    assert fail_gate["pass"] is False
