"""Prototype initialization and the definition-string rule. No training."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v2 import map_family_rows  # noqa: E402
from hyperlexical.classification_v2_prototype import (  # noqa: E402
    ACTIVE_FAMILY_VOCABULARY,  # snapshot matching prototype module internal state
    ClassificationContractError,  # matching the class used by prototype functions
    assemble_initialization,
    definition_string_report,
    median_l2,
    scale_prototype,
    training_prototype_sources,
    validation_family_support,
    weighted_mean,
)
from hyperlexical.layout import FAMILIES  # noqa: E402


def _head():
    labels = list(FAMILIES)
    weight = [[float(index + 1), float(index + 2), 0.5] for index, _name in enumerate(labels)]
    bias = [float(index + 3) for index, _name in enumerate(labels)]
    return labels, weight, bias


def _prototype(family: str, vector: list[float]) -> dict:
    return {
        "identities": [family],
        "inferred": 0,
        "observed": 1,
        "vectors": [vector],
        "weights": [1.0],
    }


def test_definition_string_rejects_a_title_when_the_definition_is_available():
    prose = "A contemptible or powerless person"
    rows = [
        {
            "lineage": "approval-disapproval",
            "text": "insect",
            "provenance": {"definition_prose": prose, "evidence_seal": "seal", "page": "insect"},
        }
    ]
    report = definition_string_report(rows)
    assert report["pass"] is False
    assert report["violations"][0]["reason"] == "title_used_for_available_definition"


def test_definition_string_accepts_the_stored_definition_and_a_duplicate_title():
    prose = "A contemptible or powerless person"
    defined = {
        "lineage": "approval-disapproval",
        "text": prose,
        "provenance": {"definition_prose": prose, "evidence_seal": "seal", "page": "insect"},
    }
    duplicate = {
        "lineage": "approval-disapproval",
        "text": "insect",
        "provenance": {"definition_prose": prose, "evidence_seal": "seal", "page": "insect-2"},
    }
    empty = {
        "lineage": "internet-slang",
        "text": "u",
        "provenance": {"definition_prose": "", "evidence_seal": "seal", "page": "u"},
    }
    report = definition_string_report([defined, duplicate, empty])
    assert report["pass"] is True
    assert report["violations"] == []


def test_weighted_mean_uses_provenance_weights_and_is_deterministic():
    first = weighted_mean([[1.0, 0.0], [0.0, 3.0]], [1.0, 0.5])
    second = weighted_mean([[0.0, 3.0], [1.0, 0.0]], [0.5, 1.0])
    assert first == pytest.approx([1.0 / 1.5, 1.5 / 1.5])
    assert second == first


def test_scale_uses_one_median_norm_and_zero_bias_for_new_rows():
    labels, weight, bias = _head()
    prototypes = {
        family: _prototype(family, [1.0, 0.0, 0.0])
        for family in ACTIVE_FAMILY_VOCABULARY
        if family not in {"ai-native", "betting-sharp", "crypto-degen", "gaming-meta"}
    }
    assembled = assemble_initialization(labels, weight, bias, prototypes)
    again = assemble_initialization(labels, weight, bias, prototypes)
    assert assembled["witness_sha256"] == again["witness_sha256"]
    assert assembled["exact_copy_families"] == [
        name for name in ACTIVE_FAMILY_VOCABULARY if name in {"ai-native", "betting-sharp", "crypto-degen", "gaming-meta"}
    ]
    assert "workplace-career" in assembled["prototype_families"]
    assert "ai-native" not in assembled["prototype_families"]
    mapped = map_family_rows(labels, weight, bias)
    by_name = {row["family"]: row for row in assembled["rows"]}
    ai = ACTIVE_FAMILY_VOCABULARY.index("ai-native")
    assert assembled["weight"][ai] == pytest.approx(mapped["weight"][ai])
    assert assembled["bias"][ai] == pytest.approx(mapped["bias"][ai])
    career = ACTIVE_FAMILY_VOCABULARY.index("workplace-career")
    assert assembled["bias"][career] == 0.0
    assert by_name["workplace-career"]["initialization_mode"] == "SEMANTIC_PROTOTYPE"
    assert by_name["ai-native"]["initialization_mode"] == "EXACT_ROW_COPY"
    expected_norm = median_l2(
        [mapped["weight"][ACTIVE_FAMILY_VOCABULARY.index(name)] for name in assembled["exact_copy_families"]]
    )
    assert assembled["target_norm"] == pytest.approx(expected_norm)
    assert l2(assembled["weight"][career]) == pytest.approx(assembled["target_norm"])
    assert by_name["workplace-career"]["source_identity_count"] == 1
    assert by_name["workplace-career"]["observed_count"] == 1


def l2(values):
    return sum(value * value for value in values) ** 0.5


def test_missing_definition_fails_instead_of_zero_initialization():
    labels, weight, bias = _head()
    with pytest.raises(ClassificationContractError) as caught:
        assemble_initialization(labels, weight, bias, {})
    assert caught.value.reason == "FAMILY_PROTOTYPE_UNAVAILABLE"


def test_zero_prototype_is_unavailable():
    with pytest.raises(ClassificationContractError) as caught:
        scale_prototype([0.0, 0.0], 1.0)
    assert caught.value.reason == "FAMILY_PROTOTYPE_UNAVAILABLE"


def test_validation_floor_reports_every_deficient_family():
    rows = []
    for family in ACTIVE_FAMILY_VOCABULARY:
        count = 1 if family in {"memetic", "internet-slang"} else 2
        rows.extend(
            {"split": "val", "lineage": family, "class": "OBSERVED", "text": f"{family}-{index}"}
            for index in range(count)
        )
    report = validation_family_support(rows)
    assert report["pass"] is False
    assert report["deficient"] == ["internet-slang", "memetic"]
    assert report["support"]["ai-native"] == 2
    reserved = [{"split": "val", "lineage": "ai-native", "class": "OBSERVED", "text": "kept", "evaluation_reserve": True}]
    blocked = validation_family_support(reserved)
    assert "ai-native" in blocked["deficient"]


def test_training_sources_skip_titles_and_validation_rows():
    prose = "A projection of intention"
    rows = [
        {
            "split": "train",
            "lineage": "spiritual-mystic",
            "class": "OBSERVED",
            "text": prose,
            "provenance": {"definition_prose": prose},
        },
        {
            "split": "train",
            "lineage": "spiritual-mystic",
            "class": "OBSERVED",
            "text": "whisper",
            "provenance": {"definition_prose": ""},
        },
        {
            "split": "val",
            "lineage": "spiritual-mystic",
            "class": "OBSERVED",
            "text": "held definition",
            "provenance": {"definition_prose": "held definition"},
        },
    ]
    sources = training_prototype_sources(rows)
    assert sources["spiritual-mystic"]["observed"] == 1
    assert sources["spiritual-mystic"]["rows"][0]["text"] == prose
    assert "memetic" not in sources
