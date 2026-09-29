"""SELECT-006 source design v2 is a preregistration, not a harvest."""

from pathlib import Path

import pytest

from hyperlexical.layout import FAMILIES
from hyperlexical.select_006_efficiency_preservation import EPSILON
from hyperlexical.select_006_reserve_acquisition import COMPUTABLE_HEAD_FAMILIES
from hyperlexical.select_006_reserve_source_design_v2 import (
    NEAR_MISS_LABELS,
    SOURCE_FAMILY,
    SPENT_RECIPES,
    TARGET_FAMILIES,
    blind_surface_errors,
    definition_prose,
    design_receipt,
    named_target_family,
    review_surface_row,
    sense_label_arguments,
    source_design,
)

REPO = Path(__file__).resolve().parents[2]
LINE = "# {{lb|en|slang|video games}} A player who wins every match."


def test_target_families_are_the_scoring_heads():
    design = source_design()
    assert list(TARGET_FAMILIES) == [name for name in FAMILIES if name in COMPUTABLE_HEAD_FAMILIES]
    assert set(TARGET_FAMILIES) == set(COMPUTABLE_HEAD_FAMILIES)
    assert design["target_families"] == list(TARGET_FAMILIES)
    assert "brainrot-aura" in design["legacy_heads_not_targets"]
    assert EPSILON == 0
    assert design["epsilon_unchanged"] == 0
    assert design["execution_loader_status"] == "NOT_YET_IMPLEMENTED"
    assert design["training_launch_authorized"] is False
    assert design["training_started"] is False


def test_recipe_is_not_the_spent_gloss_or_unbind_harvest():
    design = source_design()
    assert design["family"]["family_id"] == SOURCE_FAMILY
    assert design["family"]["family_id"] not in SPENT_RECIPES
    assert design["fetch_authorized"] is False
    assert design["unbind_clean_acquisition_authorized"] is False
    assert "unbind_clean" not in design["family"]["slices"]
    assert design["spent_surface"]["redraw_authorized"] is False
    assert design["spent_surface"]["relabel_authorized"] is False
    assert design["spent_surface"]["reuse_authorized"] is False
    assert design["spent_surface"]["decisions"]["UNRESOLVED"] == 10
    assert design["spent_surface"]["routed_slices"]["unbind_clean"] == 22
    assert design["spent_surface"]["observed"] == 0
    assert design["family"]["wordnet_admitted"] is False
    admitted = [row["family_id"] for row in design["evaluated_sources"] if row["admitted"]]
    assert admitted == [SOURCE_FAMILY]


def test_sense_label_names_one_target_and_near_misses_do_not():
    assert sense_label_arguments(LINE) == ["slang", "video games"]
    assert named_target_family(sense_label_arguments(LINE)) == "gaming-meta"
    assert named_target_family(["Video-Games"]) == "gaming-meta"
    assert named_target_family(["cryptocurrency"]) == "crypto-degen"
    assert named_target_family(["artificial intelligence"]) == "ai-native"
    assert named_target_family(["gambling", "cryptocurrency"]) is None
    for label in NEAR_MISS_LABELS:
        assert named_target_family([label]) is None
    assert "video games" not in definition_prose(LINE)
    assert definition_prose(LINE) == "A player who wins every match"


def test_review_surface_keeps_labels_and_hides_the_family():
    row = review_surface_row(
        {
            "candidate_id": "s006v2-example",
            "exact_definition_prose": definition_prose(LINE),
            "headword": "example headword",
            "page_url": "https://en.wiktionary.org/wiki/Example",
            "part_of_speech": "Noun",
            "revision_id": "1",
            "sense_label_arguments": sense_label_arguments(LINE),
            "source_lemma_tokens": ["example", "headword"],
        }
    )
    assert row["sense_label_arguments"] == ["slang", "video games"]
    assert "semantic_family" not in row
    assert blind_surface_errors([row]) == []
    leaked = dict(row)
    leaked["semantic_family"] = "gaming-meta"
    assert blind_surface_errors([leaked])


def test_receipt_records_no_fetch_and_is_deterministic():
    first = design_receipt()
    second = design_receipt()
    assert first == second
    assert first["network_requests"] == 0
    assert first["rows_fetched"] == 0
    assert len(first["record_sha256"]) == 64
    assert first["next_legal_transition"] == "SELECT_006_RESERVE_ACQUISITION_V2"


def test_module_has_no_fetch_client():
    text = (REPO / "scripts/shadow/hyperlexical/select_006_reserve_source_design_v2.py").read_text()
    for banned in ("urllib", "import requests", "httpx", "urlopen", "import firecrawl", "Popen"):
        assert banned not in text
    assert "does not fetch" in text


def test_wordnet_and_fetch_fail_closed(monkeypatch):
    import hyperlexical.select_006_reserve_source_design_v2 as module

    original = module._family

    def admit_wordnet():
        row = original()
        row["wordnet_admitted"] = True
        return row

    monkeypatch.setattr(module, "_family", admit_wordnet)
    with pytest.raises(SystemExit, match="CC-BY-SA"):
        module.source_design()
