"""Spec 005 route-label fixtures. Offline."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hyperlex.analysis.routes import (
    RouteLabelError,
    attach_route_labels,
    label_routes,
    render_route_line,
    validate_route_block,
)


def test_lineage_only():
    block = label_routes(
        {
            "lineage": {
                "family_id": "brainrot-aura",
                "confidence": 0.48,
                "score_breakdown": {"lexical_confidence": 0.48, "hybrid_confidence": 0.48},
            }
        }
    )
    assert block["routes_fired"] == ["lexical"]
    assert block["semantic_claimed"] is False
    assert block["brier"] is None


def test_form_only_neologism():
    block = label_routes(
        {"neologisms": [{"term": "xyzzy", "formation": "platform_compression"}]}
    )
    assert block["routes_fired"] == ["form"]


def test_both():
    block = label_routes(
        {
            "lineage": {"family_id": "brainrot-aura", "confidence": 0.48},
            "neologisms": [{"term": "rizz", "formation": "platform_compression"}],
        }
    )
    assert set(block["routes_fired"]) == {"form", "lexical"}


def test_neither():
    block = label_routes({"neologisms": [], "semantic_variation": {"sense": "general"}})
    assert block["routes_fired"] == []
    assert block["semantic_claimed"] is False


def test_vector_neighbors_form_only_without_lineage():
    block = label_routes(
        {"vector_neighbors": {"hits": [{"text": "rizz", "score": 0.4}]}}
    )
    assert block["routes_fired"] == ["form"]


def test_vector_neighbors_do_not_add_token_when_lexical():
    block = label_routes(
        {
            "lineage": {"family_id": "brainrot-aura", "confidence": 0.5},
            "vector_neighbors": {"hits": [{"text": "rizz", "score": 0.4}]},
        }
    )
    assert block["routes_fired"] == ["lexical"]


def test_below_threshold_not_lexical():
    block = label_routes({"lineage": {"family_id": "x", "confidence": 0.2}})
    assert "lexical" not in block["routes_fired"]


def test_poison_semantic_token():
    with pytest.raises(RouteLabelError):
        validate_route_block(
            {
                "schema": "hyperlex.route_labels.v0.1",
                "routes_fired": ["semantic"],
                "semantic_claimed": False,
                "brier": None,
            }
        )


def test_poison_semantic_claimed():
    with pytest.raises(RouteLabelError):
        validate_route_block(
            {
                "schema": "hyperlex.route_labels.v0.1",
                "routes_fired": [],
                "semantic_claimed": True,
                "brier": None,
            }
        )


def test_poison_numeric_brier():
    with pytest.raises(RouteLabelError):
        validate_route_block(
            {
                "schema": "hyperlex.route_labels.v0.1",
                "routes_fired": [],
                "semantic_claimed": False,
                "brier": 0.1,
            }
        )


def test_coexist_semantic_variation():
    analysis = {
        "semantic_variation": {"sense": "status/irony", "provenance": "INFERRED"},
        "lineage": {"family_id": "brainrot-aura", "confidence": 0.48},
        "neologisms": [{"term": "rizz", "formation": "platform_compression"}],
    }
    attach_route_labels(analysis)
    assert "semantic_variation" in analysis
    assert analysis["routes"]["semantic_claimed"] is False
    assert "semantic" not in analysis["routes"]["routes_fired"]


def test_attach_mutates():
    analysis: dict = {}
    attach_route_labels(analysis)
    assert analysis["routes"]["schema"] == "hyperlex.route_labels.v0.1"


def test_card_line():
    line = render_route_line(label_routes({}))
    assert line == "Routes: (none). Semantic: no. Brier: null."


def test_contract_file_present():
    root = Path(__file__).resolve().parents[1]
    contract = root / "specs" / "005-route-labels" / "contracts" / "route_labels.v0.1.json"
    if not contract.is_file():
        pytest.skip("spec contract not on this tree yet")
    data = json.loads(contract.read_text())
    assert data["$id"] == "hyperlex.route_labels.v0.1"
