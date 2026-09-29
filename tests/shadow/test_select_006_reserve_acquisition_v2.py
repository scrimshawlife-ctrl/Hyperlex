"""Acquisition v2 keeps the sealed label rule and does not fetch."""

import pytest

from hyperlexical.eval_settlement import rights_of
from hyperlexical.select_006_reserve_acquisition_v2 import (
    DESIGN_PINS,
    qualifying_sense,
    search_query,
    target_names,
)
from hyperlexical.select_006_reserve_source_design_v2 import NEAR_MISS_LABELS, review_surface_row


def test_pins_match_the_sealed_v2_artifacts():
    assert DESIGN_PINS["SOURCE_DESIGN_V2.json"].startswith("7e9c323e")
    assert DESIGN_PINS["HEAD_MAPPING_WITNESS.json"].startswith("0453c63b")
    assert DESIGN_PINS["SOURCE_RIGHTS_PROVENANCE_POLICY.json"].startswith("e28d0f0f")
    assert DESIGN_PINS["FUTURE_ACQUISITION_CONTRACT.json"].startswith("acf8b802")


def test_exact_label_resolves_one_family_and_near_misses_do_not():
    text = "\n".join(
        [
            "==English==",
            "===Noun===",
            "# {{lb|en|slang|video games}} A player who wins every match.",
            "# {{lb|en|gambling|cryptocurrency}} Ignored once a unique line wins.",
        ]
    )
    sense = qualifying_sense(text)
    assert sense["status"] == "unique"
    assert sense["target_family"] == "gaming-meta"
    assert "OBSERVED" not in sense
    assert target_names(["poker"]) == []
    assert target_names(["crypto"]) == []
    assert target_names(["ai"]) == []
    assert target_names(["computing"]) == []
    for label in NEAR_MISS_LABELS:
        assert target_names([label]) == []
    ambiguous = qualifying_sense(
        "\n".join(
            [
                "==English==",
                "===Noun===",
                "# {{lb|en|gambling|cryptocurrency}} A stake and a coin.",
                "# {{lb|en|gaming}} Later.",
            ]
        )
    )
    assert ambiguous["status"] == "ambiguous"
    assert ambiguous["target_family"] is None
    later = qualifying_sense(
        "\n".join(
            [
                "==English==",
                "===Noun===",
                "# {{lb|en|poker}} A card.",
                "# {{lb|en|cryptocurrency}} A coin.",
            ]
        )
    )
    assert later["status"] == "unique"
    assert later["target_family"] == "crypto-degen"


def test_search_query_uses_the_authorized_label_only():
    assert search_query("lb", "video games") == 'insource:"{{lb|en|video games}}"'
    with pytest.raises(SystemExit, match="SOURCE_DESIGN_PIN_MISMATCH"):
        search_query("lb", "poker")


def test_review_row_hides_the_resolved_family():
    row = review_surface_row(
        {
            "candidate_id": "s006v2-example",
            "exact_definition_prose": "A coin.",
            "headword": "example",
            "page_url": "https://en.wiktionary.org/wiki/Example",
            "part_of_speech": "Noun",
            "revision_id": 1,
            "sense_label_arguments": ["cryptocurrency"],
            "source_lemma_tokens": [],
            "target_family": "crypto-degen",
        }
    )
    assert "target_family" not in row
    assert "semantic_family" not in row
    assert row["sense_label_arguments"] == ["cryptocurrency"]


def test_labeled_sense_rights_are_cleared_and_wordnet_is_not():
    assert rights_of({"source_type": "wiktionary_labeled_sense"}) == "CC-BY-SA"
    with pytest.raises(SystemExit, match="unknown rights"):
        rights_of({"source_type": "wordnet"})
