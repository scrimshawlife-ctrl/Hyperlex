"""CPU tests for SETTLE_HYPERLEX_PROGRAM_END_STATE."""

from __future__ import annotations

from hyperlexical.classification_v6_program_settlement import (
    CAPABILITY_BASELINE,
    CENTRAL_ARCHITECTURAL_ANSWER,
    CORE_QUAL_METRICS,
    PHASE_RULE,
    PRIMARY_DISPOSITIONS,
    build_program_settlement_receipt,
    classify_program_disposition,
    evaluation_architecture_contract,
    grade_summary,
    minimum_viable_product_contract,
    program_settlement_contract,
    settled_audit_from_evidence,
    task_formulation_decision,
)


def test_contract_forbids_classifier_rescue_cycles():
    c = program_settlement_contract()
    assert c["PHASE_RULE"] == PHASE_RULE
    assert "train_another_classifier_head" in c["forbidden"]
    assert "rescore_spent_QUAL" in c["forbidden"]
    assert "promote_core_classifier_to_release" in c["forbidden"]
    assert CORE_QUAL_METRICS["gate_pass"] is False
    assert CORE_QUAL_METRICS["evaluation_spent"] is True
    spent = c["evaluation_architecture"]["spent_surfaces_permanently_excluded"]
    assert "HYPERLEX_V6_CORE_QUALIFICATION_001" in spent
    assert "HYPERLEX_V5_PIPELINE_QUALIFICATION_001" in spent


def test_capability_grades_cover_core_findings():
    g = grade_summary()
    assert "v6_core_production_classifier" in g["DISPROVEN_FOR_CURRENT_FORMULATION"]
    assert "function_as_required_text_only_output" in g[
        "DISPROVEN_FOR_CURRENT_FORMULATION"
    ]
    assert "hierarchical_multi_label_ontology" in g["PROVEN"]
    assert "frozen_semantic_encoder_superiority_vs_hyperlex_modernbert" in g["PROVEN"]
    assert "explicit_none_rejection_gate" in g["SUPPORTED_BUT_LIMITED"]
    assert "contextual_semantic_reasoning_as_final_judge" in g["UNRESOLVED"]
    assert CAPABILITY_BASELINE["encoder_fine_tuning_justification"]["grade"] == (
        "DISPROVEN_FOR_CURRENT_FORMULATION"
    )


def test_mvp_excludes_hard_labels_includes_representation():
    mvp = minimum_viable_product_contract()
    assert mvp["product_role"] == "HYPERLEX_REPRESENTATION_AND_MEASUREMENT_LAYER"
    assert "frozen_semantic_embedding" in mvp["required_outputs"]
    assert "semantic_candidates_and_margins" in mvp["required_outputs"]
    assert "evidence_abstention_none_signal" in mvp["required_outputs"]
    assert "final_domain_label" in mvp["deprecated_as_required_product_outputs"]
    assert "final_function_label" in mvp["deprecated_as_required_product_outputs"]
    assert mvp["encoder_policy"]["fine_tuning"] == "not_justified"


def test_task_formulation_rejects_primary_classification():
    t = task_formulation_decision()
    assert t["rejected_primary_formulation"] == "classification"
    assert t["selected_primary_formulation"] == "representation_only_output"
    assert "right classifier" in CENTRAL_ARCHITECTURAL_ANSWER or (
        "not the right job" in CENTRAL_ARCHITECTURAL_ANSWER
    )


def test_disposition_is_representation_layer():
    audit = settled_audit_from_evidence()
    assert audit["core_qual_pass"] is False
    assert audit["representation_more_stable_than_labels"] is True
    d = classify_program_disposition(audit)
    assert d["PRIMARY_DISPOSITION"] == "HYPERLEX_REPRESENTATION_AND_MEASUREMENT_LAYER"
    assert d["PRIMARY_DISPOSITION"] in PRIMARY_DISPOSITIONS
    assert d["RELEASE_STATUS"] == "SHADOW_INSTRUMENT_ONLY"
    assert d["CLASSIFIER_RELEASE_ELIGIBLE"] is False
    assert d["HUB_PUBLISH_AUTHORIZED"] is False
    assert d["classifier_candidate_result"]["result"] == "CONCLUSIVELY_REJECTED"

    # Classifier pass would flip disposition (counterfactual guard).
    alt = classify_program_disposition({**audit, "core_qual_pass": True})
    assert alt["PRIMARY_DISPOSITION"] == "HYPERLEX_PRODUCTION_CLASSIFIER"


def test_evaluation_loop_roles_and_receipt():
    ev = evaluation_architecture_contract()
    assert set(ev["stages"]) == {
        "TRAIN",
        "DEV_SELECTION",
        "REPRESENTATIVE_VALIDATION",
        "FRESH_QUALIFICATION",
    }
    assert ev["stages"]["REPRESENTATIVE_VALIDATION"]["may_tune"] is False
    assert (
        ev["classifier_fresh_qualification_status"][
            "further_classifier_qual_without_task_reformulation"
        ]
        == "FORBIDDEN"
    )
    receipt = build_program_settlement_receipt(sealed_at="2026-10-02T12:00:00Z")
    assert receipt["disposition"]["PRIMARY_DISPOSITION"] == (
        "HYPERLEX_REPRESENTATION_AND_MEASUREMENT_LAYER"
    )
    assert receipt["CLASSIFIER_RETRAINED"] is False
    assert receipt["SPENT_QUAL_RESCORED"] is False
    assert receipt["SYSTEM_PROGRAM_SETTLEMENT_RECEIPT_SHA256"]
    assert receipt["axis_roles"]["DOMAIN"] == "ADVISORY_CANDIDATES_NOT_HARD_RELEASE"
    assert receipt["axis_roles"]["evidence_NONE"] == "REQUIRED_SIGNAL"
