import copy

import pytest

from hyperlex.eic import build_q1_result, sha256_text, validate_q1_result


def base(**overrides):
    kwargs = dict(
        result_id="hq1-identity-001",
        source="hello world",
        output="hello world",
        transform_id="identity",
        revision="test-v1",
        parameters={},
        declared_semantic_intent="preserve all content",
        declared_invariants=["meaning"],
        expected_changed_attributes=[],
        runtime_binding={"kind": "pure-python", "revision": "test"},
    )
    kwargs.update(overrides)
    return build_q1_result(**kwargs)


def test_identity_transform_is_hash_stable():
    one = base()
    two = base()
    assert one["source_hash"] == sha256_text("hello world")
    assert one["output_hash"] == two["output_hash"] == one["source_hash"]


def test_surface_rewrite_keeps_invariant_as_declaration_only():
    result = base(
        output="hello, world!",
        transform_id="punctuation-rewrite",
        declared_invariants=["declared-semantic-intent"],
        expected_changed_attributes=["punctuation"],
    )
    assert result["epistemic_status"] == "OBSERVED"
    assert result["declared_invariants"] == ["declared-semantic-intent"]


def test_false_invariance_declaration_does_not_become_truth():
    result = base(
        output="goodbye world",
        transform_id="semantic-negative-control",
        declared_invariants=["meaning"],
        expected_changed_attributes=["lexical-form"],
    )
    assert result["epistemic_status"] == "OBSERVED"
    assert "meaning" in result["declared_invariants"]


def test_missing_required_runtime_binding_fails_closed():
    with pytest.raises(ValueError, match="runtime/model binding"):
        base(runtime_binding=None, parameters={"requires_runtime_binding": True})


def test_missing_required_seed_fails_closed():
    with pytest.raises(ValueError, match="missing seed"):
        base(parameters={"requires_seed": True}, seed=None)


def test_contamination_and_fallback_survive_serialization():
    result = base(
        contamination=["fixture-seen-during-training:unknown"],
        fallback={"used": True, "route": "mock"},
    )
    assert result["contamination"] == ["fixture-seen-during-training:unknown"]
    assert result["fallback"]["route"] == "mock"


def test_not_computable_is_explicit():
    result = base(output=None, not_computable_reason="model binding unavailable")
    assert result["status"] == "NOT_COMPUTABLE"
    assert result["epistemic_status"] == "NOT_COMPUTABLE"
    assert result["provenance"] == "NOT_COMPUTABLE"


def test_calibrated_or_settled_epistemic_status_is_rejected():
    result = base()
    for status in ("CALIBRATED", "SETTLED", "INTERPRETED"):
        invalid = copy.deepcopy(result)
        invalid["epistemic_status"] = status
        with pytest.raises(ValueError):
            validate_q1_result(invalid)


def test_registered_revision_is_accepted():
    result = base(revision="v2", parameters={"accepted_revisions": ["v2", "v3"]})
    assert result["transform"]["revision"] == "v2"


def test_stale_revision_is_rejected():
    with pytest.raises(ValueError, match="stale transform revision"):
        base(revision="v1", parameters={"accepted_revisions": ["v2", "v3"]})
