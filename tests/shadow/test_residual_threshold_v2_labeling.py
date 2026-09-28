"""Blind v2 operator labeling stays off the frozen scores and the measurement surface."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from hyperlexical.residual_threshold_v2_labeling import (
    EXPECTED_MEASUREMENT,
    LABEL_KEYS,
    PACKET_KEYS,
    assert_packet_blind,
    forbidden_key,
    label_rows,
    packet_rows,
)
from hyperlexical.screen_eval import OPERATOR_BUCKETS, REASONS


def _manifest_row(index: int) -> dict:
    return {
        "frozen_gloss": f"gloss {index}",
        "global_draw_order": index,
        "pos": "noun",
        "pwn30_synset": f"noun:{index:08d}",
        "row_id": f"row-{index}",
        "surface": f"surface {index}",
        "token_count": 2,
    }


def test_packet_rows_expose_only_canonical_review_fields() -> None:
    rows = packet_rows([_manifest_row(1), _manifest_row(2)])
    assert [row["calibration_row_id"] for row in rows] == [1, 2]
    assert set(rows[0]) == PACKET_KEYS
    for key in rows[0]:
        assert forbidden_key(key) is None


def test_packet_blindness_refuses_a_readiness_field() -> None:
    row = packet_rows([_manifest_row(1)])[0]
    row["residual_score"] = 0.1
    with pytest.raises(SystemExit):
        assert_packet_blind([row])


def test_labels_use_the_canonical_reason_ontology() -> None:
    packet = packet_rows([_manifest_row(1)])
    decision = {
        "calibration_row_id": 1,
        "operator_evidence": "STRONG_IDIOM",
        "operator_label": "HIGH",
        "operator_note": "fixed nonliteral idiom",
        "row_id": "row-1",
    }
    labels = label_rows(packet, [decision])
    assert set(labels[0]) == LABEL_KEYS
    assert labels[0]["operator_label"] == "HIGH"
    assert labels[0]["review_status"] == "REVIEWED"
    assert "UNRESOLVED" in OPERATOR_BUCKETS
    assert "INSUFFICIENT_SIGNAL" in REASONS["UNRESOLVED"]
    with pytest.raises(SystemExit):
        label_rows(packet, [{**decision, "operator_evidence": "STRONG_IDIOM", "operator_label": "REJECT"}])


def test_labeling_module_does_not_score_or_search() -> None:
    path = Path(inspect.getsourcefile(packet_rows))
    text = path.read_text(encoding="utf-8")
    assert EXPECTED_MEASUREMENT in text
    assert "select_threshold(" not in text
    assert "support_passed(" not in text
    assert "sentence-transformers" not in text
    assert "all-MiniLM" not in text
    assert "load_wordnet(" not in text
    assert "glossbert_scores_exposed" in text
    assert "joined_to_readiness" in text
    assert "LABELS_FROZEN" in text
    assert "CALIBRATION_INSUFFICIENT_SUPPORT" in text
