"""SELECT-006 reserve floors are frozen before any fetch. No training."""

from hyperlexical.select_006_efficiency_preservation import EPSILON
from hyperlexical.select_006_reserve_acquisition import (
    FLOORS,
    blind_surface_errors,
    exclusion_reason,
    extract_primary_gloss,
    frozen_floors,
    metric_surface,
    review_surface_row,
)


def test_floors_are_the_admission_minimum_and_epsilon_stays_zero():
    floors = frozen_floors()
    assert floors["floors"] == {
        "classify": 1,
        "classify_non_none": 1,
        "classify_observed": 1,
        "head_mapped_non_none": 1,
        "unbind_clean": 1,
    }
    assert floors["floors"] == FLOORS
    assert floors["select_005_counts_not_transferred"] == [51, 11, 11, 27]
    assert floors["select_005_reserve_reuse"] == "FORBIDDEN"
    assert floors["epsilon_unchanged"] == 0
    assert EPSILON == 0
    assert "wiktionary_sense_gloss" in floors["source_families"]
    assert "wiktionary_multiword_lemma" in floors["source_families"]


def test_gloss_parser_drops_topic_templates_and_keeps_prose():
    wikitext = """
==French==
# autre
==English==
===Noun===
# {{lb|en|slang|gaming}} A player who wins every match.
"""
    parsed = extract_primary_gloss(wikitext)
    assert parsed["part_of_speech"] == "Noun"
    assert parsed["exact_gloss"] == "A player who wins every match"
    assert "gaming" not in parsed["exact_gloss"]
    assert extract_primary_gloss("#REDIRECT [[Other]]")["exact_gloss"] is None


def test_review_surface_is_blind_and_select_005_identity_is_excluded():
    raw = {
        "candidate_id": "s006a-1",
        "exact_gloss": "A player who wins every match",
        "headword": "example phrase",
        "page_url": "https://en.wiktionary.org/wiki/Example_phrase",
        "part_of_speech": "Noun",
        "revision_id": 1,
        "source_family": "wiktionary_sense_gloss",
        "source_lemma_tokens": [],
    }
    surface = review_surface_row(raw)
    assert blind_surface_errors([surface]) == []
    assert "semantic_family" not in surface
    assert "unbind_clean" not in surface
    assert exclusion_reason("abc", {"abc": "SELECT_005_EVAL_RESERVE"}) == "SELECT_005_EVAL_RESERVE"


def test_metric_surface_fails_closed_without_a_head_mapped_gold():
    routed = [
        {
            "lineage": "internet-slang",
            "routing_status": "ELIGIBLE",
            "slices": ["classify", "classify_non_none", "classify_observed"],
            "task": "classify",
        },
        {
            "lineage": "none",
            "routing_status": "ELIGIBLE",
            "slices": ["unbind_clean"],
            "task": "unbind",
        },
    ]
    surface = metric_surface(routed)
    assert surface["computable"]["classification_accuracy"] is True
    assert surface["computable"]["observed_label_accuracy"] is True
    assert surface["computable"]["unbind_clean_exact"] is True
    assert surface["computable"]["classify_macro_f1_nonnone"] is False
    assert surface["floors_met"] is False
    routed[0]["lineage"] = "gaming-meta"
    passed = metric_surface(routed)
    assert passed["computable"]["classify_macro_f1_nonnone"] is True
    assert passed["floors_met"] is True


def test_loader_blocker_remains_unimplemented():
    from hyperlexical.select_006_reserve_acquisition import execution_loader_status, forbidden_training

    assert execution_loader_status() == "NOT_YET_IMPLEMENTED"
    flags = forbidden_training()
    assert flags["training_launch_authorized"] is False
    assert flags["training_started"] is False
    assert flags["epochs"] == 0
