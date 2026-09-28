"""Routing contract: slices come from settlement plus a derivative record."""

import ast
from pathlib import Path

import pytest

from hyperlexical.eval_routing import (
    CLEARED_RIGHTS,
    PROCEDURE_ID,
    SCHEMA,
    UNBIND_CLEAN_DERIVATION,
    canonical_json,
    contract_validation,
    derive_batch,
    derive_routing,
    procedure_hash,
    reference_pairs,
)
from hyperlexical.select_005_reserve import census

MODULE = Path(__file__).resolve().parents[2] / "scripts/shadow/hyperlexical/eval_routing.py"


def _by_name():
    found = {}
    for settlement, metadata in reference_pairs():
        found[settlement["row_id"]] = derive_routing(settlement, metadata)
    return found


def test_reference_corpus_is_deterministic_and_valid():
    first = contract_validation()
    second = contract_validation()
    assert first == second
    assert first["determinism"] == "IDENTICAL"
    assert first["state"] == "ROUTING_VALIDATION_COMPLETE"
    assert first["errors"] == []
    assert first["procedure_id"] == PROCEDURE_ID
    assert procedure_hash() == procedure_hash()
    assert len(procedure_hash()) == 64


def test_classify_slices_follow_the_ledger_predicate():
    rows = _by_name()
    observed = rows["route-fixture-accept-observed"]
    assert observed["routing_status"] == "ELIGIBLE"
    assert observed["slices"] == ["classify", "classify_non_none", "classify_observed"]
    assert observed["class"] == "OBSERVED"
    assert observed["lineage"] == "ai-native"
    inferred = rows["route-fixture-accept-inferred"]
    assert inferred["slices"] == ["classify", "classify_non_none"]
    assert "classify_observed" not in inferred["slices"]
    assert inferred["class"] == "INFERRED"
    non_none = rows["route-fixture-accept-non-none"]
    assert "classify_non_none" in non_none["slices"]
    assert non_none["lineage"] == "politics-civic"
    none_row = rows["route-fixture-none-classify"]
    assert none_row["settlement_decision"] == "NONE"
    assert none_row["slices"] == ["classify"]
    assert "classify_non_none" not in none_row["slices"]
    reclassified = rows["route-fixture-reclassify"]
    assert reclassified["routing_status"] == "ELIGIBLE"
    assert reclassified["slices"] == ["classify", "classify_non_none"]


def test_unbind_clean_is_a_frozen_flag_and_not_a_classify_alias():
    rows = _by_name()
    clean = rows["route-fixture-accept-unbind"]
    assert clean["routing_status"] == "ELIGIBLE"
    assert clean["task"] == "unbind"
    assert clean["unbind_clean"] is True
    assert clean["slices"] == ["unbind_clean"]
    assert "classify" not in clean["slices"]
    blocked = rows["route-fixture-classify-not-unbind"]
    assert blocked["routing_status"] == "INELIGIBLE"
    assert "UNBIND_CLEAN_TASK_MISMATCH" in blocked["routing_reason_codes"]
    assert blocked["slices"] == []
    assert UNBIND_CLEAN_DERIVATION == "soft_ceiling.clean_surface"


def test_inferred_is_not_promoted_and_blocks_stay_ineligible():
    rows = _by_name()
    promoted = rows["route-fixture-promotion-refused"]
    assert promoted["routing_status"] == "INELIGIBLE"
    assert promoted["class"] == "INFERRED"
    assert "CLASS_PROMOTION_REFUSED" in promoted["routing_reason_codes"]
    assert "classify_observed" not in promoted["slices"]
    rights = rows["route-fixture-rights-blocked"]
    assert rights["routing_status"] == "INELIGIBLE"
    assert rights["rights_state"] != CLEARED_RIGHTS
    assert "RIGHTS_NOT_CLEARED" in rights["routing_reason_codes"]
    provenance = rows["route-fixture-provenance-blocked"]
    assert provenance["routing_status"] == "INELIGIBLE"
    assert "PROVENANCE_INCOMPLETE" in provenance["routing_reason_codes"]
    unresolved = rows["route-fixture-unresolved"]
    assert unresolved["routing_status"] == "INELIGIBLE"
    assert unresolved["slices"] == []
    assert "SETTLEMENT_UNRESOLVED" in unresolved["routing_reason_codes"]
    conflict = rows["route-fixture-identity-conflict"]
    assert "IDENTITY_CONFLICT" in conflict["routing_reason_codes"]


def test_duplicate_identity_does_not_route_twice():
    settlement, metadata = reference_pairs()[0]
    records = derive_batch([(settlement, metadata), (settlement, metadata)])
    assert records[0]["routing_status"] == "ELIGIBLE"
    assert records[1]["routing_status"] == "INELIGIBLE"
    assert records[1]["routing_reason_codes"] == ["DUPLICATE_IDENTITY"]
    assert records[1]["slices"] == []


def test_quota_and_model_output_are_refused():
    settlement, metadata = reference_pairs()[0]
    with pytest.raises(SystemExit, match="quota"):
        derive_routing(settlement, {**metadata, "reserve_counts": {"unbind_clean": 0}})
    with pytest.raises(SystemExit, match="model"):
        derive_routing({**settlement, "prediction": 0.2}, metadata)
    deficit = {"unbind_clean": 0}
    first = canonical_json(derive_routing(settlement, metadata))
    deficit["unbind_clean"] = 1
    second = canonical_json(derive_routing(settlement, metadata))
    assert first == second
    assert deficit["unbind_clean"] == 1


def test_census_reads_routing_without_embedding_slices_in_the_settlement():
    settlement, metadata = reference_pairs()[3]
    assert "task" not in settlement
    routing = derive_routing(settlement, metadata)
    bare = census([settlement], {}, set())
    assert bare["failure"] == "RESERVE_QUOTA_UNFILLED"
    assert bare["reserve_row_count"] == 0
    joined = census([settlement], {}, set(), routing_by_row={settlement["row_id"]: routing})
    assert joined["determinism"] == "IDENTICAL"
    assert joined["routed_slice_counts"]["unbind_clean"] == 1
    assert joined["routed_slice_counts"]["classify"] == 0
    assert joined["failure"] == "RESERVE_QUOTA_UNFILLED"
    forged = dict(routing)
    forged["rights_state"] = "RIGHTS_UNRESOLVED"
    forged["routing_status"] = "ELIGIBLE"
    refused = census([settlement], {}, set(), routing_by_row={settlement["row_id"]: forged})
    assert refused["routed_slice_counts"]["unbind_clean"] == 0
    spent = census(
        [settlement],
        {settlement["text_hash"]: "EVAL_SPENT"},
        set(),
        routing_by_row={settlement["row_id"]: routing},
    )
    assert spent["exclusion_counts"].get("EVAL_SPENT") == 1
    assert spent["eligible_count"] == 0


def test_schema_names_and_module_fences():
    assert SCHEMA == "hyperlex.eval_routing.v1"
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert not any("residual" in name or "semantic_evidence" in name for name in imported)
    assert "persist_append" not in source
    assert "commit_settlement" not in source
    assert "PLANNING_TARGETS" not in source


def test_threshold_schema_keeps_an_unsealed_map_empty_and_admission_epochs_at_zero():
    from hyperlexical.select_contract_schema import admission_schema_errors, threshold_schema_errors

    unsealed = {
        "decision_thresholds": {},
        "experiment_id": "HLX-EXP-2026-09-27-SELECT-005",
        "schema": "hyperlex.threshold_authorization.v1",
        "sealed": False,
        "state": "BLOCKED_PENDING_OPERATOR_AUTHORIZATION",
    }
    assert threshold_schema_errors(unsealed) == []
    sealed = dict(unsealed)
    sealed["sealed"] = True
    assert threshold_schema_errors(sealed)
    receipt = {
        "admission_gate_sequence": ["experiment_binding"] * 9,
        "best_moved": False,
        "controlled_holdout_contract": "CONTROLLED_RESERVE",
        "epochs": 0,
        "gradient_steps": 0,
        "hlx_allow_no_holdout": False,
        "holdout_admitted": False,
        "launch_armed": False,
        "optimizer_loaded": False,
        "schema": "hyperlex.admission.v1",
        "training_started": False,
    }
    assert admission_schema_errors(receipt) == []
