"""Evidence map for v2 training acquisition. No network and no ledger writes."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v2_acquire import (  # noqa: E402
    ACTIVE_TARGETS,
    SENSE_LABELS,
    SUPPORTED_FAMILY_LABELS,
    classify_wikitext,
    match_definition,
    training_row,
)


def test_sense_labels_reject_weak_signals():
    assert "slang" not in SENSE_LABELS["internet-slang"]
    assert "computing" not in SENSE_LABELS["technology-ai"]
    assert "artificial intelligence" in SUPPORTED_FAMILY_LABELS
    assert "artificial intelligence" not in SENSE_LABELS["technology-ai"]
    assert match_definition(["slang"], "just internet talk")["status"] == "absent"
    assert match_definition(["computing"], "a machine")["status"] == "absent"


def test_exact_and_conjoined_labels_name_one_family():
    assert match_definition(["Internet slang"], "")["family"] == "internet-slang"
    assert match_definition(["Internet", "slang"], "")["family"] == "internet-slang"
    assert match_definition(["programming"], "source code")["family"] == "technology-ai"
    assert match_definition(["derogatory"], "a term of contempt")["family"] == "approval-disapproval"
    assert match_definition(["military"], "of armies")["family"] == "conflict-aggression"
    assert match_definition(["Southern US"], "used in that region")["family"] == "regional-cultural"
    assert match_definition(["occult"], "esoteric practice")["family"] == "spiritual-mystic"


def test_two_families_and_supported_labels_do_not_admit():
    mixed = match_definition(["Internet slang", "sports"], "")
    assert mixed["status"] == "ambiguous"
    assert mixed["family"] is None
    blocked = match_definition(["programming", "artificial intelligence"], "a model")
    assert blocked["status"] == "supported_family_excluded"
    gloss_and_label = match_definition(["Internet slang"], "An internet meme.")
    assert gloss_and_label["status"] == "ambiguous"


def test_definitional_gloss_is_admitted_without_a_category():
    meme = match_definition([], "An internet meme circulated as an image macro")
    assert meme == {"status": "unique", "family": "memetic", "evidence": "definitional_gloss"}
    page = "==English==\n===Noun===\n# An internet meme.\n"
    decision = classify_wikitext(page)
    assert decision["status"] == "unique"
    assert decision["family"] == "memetic"
    row = training_row(
        "loss.jpg",
        decision,
        {"revision_id": 10, "revision_sha1": "abc", "revision_timestamp": "2026-01-01T00:00:00Z"},
    )
    assert row["class"] == "OBSERVED"
    assert row["lineage"] == "memetic"
    assert row["split"] == "train"
    assert row["provenance"]["revision_id"] == 10
    assert row["provenance"]["oldid_from_mediawiki"] is True
    assert row["text"] == "An internet meme"
    assert row["provenance"]["page"] == "loss.jpg"
    assert row["provenance"]["training_text"] == "definition_prose"


def test_conflicting_senses_on_one_page_are_not_admitted():
    page = (
        "==English==\n"
        "===Noun===\n"
        "# {{lb|en|military}} A unit.\n"
        "# {{lb|en|sports}} A play.\n"
    )
    assert classify_wikitext(page)["status"] == "ambiguous"
    assert classify_wikitext("#REDIRECT [[Other]]")["status"] == "redirect"


def test_every_target_has_a_frozen_pattern():
    for family in ACTIVE_TARGETS:
        has_label = family in SENSE_LABELS or family == "regional-cultural"
        has_gloss = family in {name for name, _pattern in (
            ("memetic", ""),
            ("social-status", ""),
            ("relationship-dating", ""),
        )}
        assert has_label or has_gloss


def test_empty_definition_prose_keeps_the_page_title():
    row = training_row(
        "u",
        {
            "status": "unique",
            "family": "internet-slang",
            "evidence": "sense_label",
            "sense_label_arguments": ["Internet slang"],
            "definition_prose": "",
        },
        {"revision_id": 11},
    )
    assert row["text"] == "u"
    assert row["provenance"]["page"] == "u"
    assert row["provenance"]["training_text"] == "title"
