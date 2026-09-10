import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.weak_tag_family import (
    COLLISION_HOLD,
    FAMILIES,
    SEED_FAMILY,
    TOPIC_FAMILY,
    build_lemma_family_map,
    family_from_kaikki_entry,
    family_from_wiktionary_categories,
    weak_family_for_text,
)


def test_eight_families_only():
    assert "none" not in FAMILIES
    assert len(FAMILIES) == 8
    for fam in TOPIC_FAMILY.values():
        assert fam in FAMILIES
    for fam in SEED_FAMILY.values():
        assert fam in FAMILIES


def test_collision_hold_skill_issue():
    assert "skill issue" in COLLISION_HOLD
    entry = {
        "word": "skill issue",
        "senses": [{"topics": ["video-games"], "tags": ["slang"]}],
    }
    assert family_from_kaikki_entry(entry) is None
    assert weak_family_for_text("skill issue", {"skill issue": "gaming-meta"}) is None


def test_gaming_slang_topic():
    entry = {
        "word": "bunny hopper",
        "senses": [{"topics": ["video-games"], "tags": ["slang"]}],
    }
    assert family_from_kaikki_entry(entry) == "gaming-meta"


def test_polysemy_denylist_bank():
    entry = {
        "word": "bank",
        "senses": [{"topics": ["gambling"], "tags": ["slang"]}],
    }
    assert family_from_kaikki_entry(entry) is None


def test_requires_slang_or_multiword():
    bare = {
        "word": "akimbo",
        "senses": [{"topics": ["video-games"], "tags": []}],
    }
    assert family_from_kaikki_entry(bare) is None
    multi = {
        "word": "boat race",
        "senses": [{"topics": ["gambling"], "tags": []}],
    }
    assert family_from_kaikki_entry(multi) == "betting-sharp"


def test_wiki_categories():
    assert family_from_wiktionary_categories(["English slang", "en:People"]) is None
    assert family_from_wiktionary_categories(["en:Video games"]) == "gaming-meta"
    assert family_from_wiktionary_categories(["en:Cryptocurrency"]) == "crypto-degen"


def test_multi_family_dropped():
    entries = [
        {"word": "moon", "senses": [{"topics": ["cryptocurrency"], "tags": ["slang"]}]},
        {"word": "moon", "senses": [{"topics": ["video-games"], "tags": ["slang"]}]},
    ]
    # denylist also blocks moon; use a synthetic non-deny lemma
    entries = [
        {
            "word": "zorpcoin",
            "senses": [{"topics": ["cryptocurrency", "video-games"], "tags": ["slang"]}],
        }
    ]
    assert family_from_kaikki_entry(entries[0]) is None


def test_build_map_seeds_and_entries():
    entries = [
        {
            "word": "achievement whore",
            "senses": [{"topics": ["video-games"], "tags": ["slang"]}],
        }
    ]
    m = build_lemma_family_map(entries, include_seeds=True)
    assert m["achievement whore"] == "gaming-meta"
    assert m["tilt"] == "gaming-meta"  # seed
    assert weak_family_for_text("TILT", m) == "gaming-meta"
