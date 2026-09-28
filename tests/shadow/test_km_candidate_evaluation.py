import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.km_candidate_evaluation import (
    AMBIGUOUS_MULTIPLE_SYNSETS,
    EXACT_UNIQUE_RECONSTRUCTION,
    NO_PWN3_MATCH,
    UNKNOWN,
    align_item,
    join_synset,
    lookup_key,
)
from hyperlexical.unbind_screen_v4 import rule_surface_violations

MODULE = ROOT / "scripts" / "shadow" / "hyperlexical" / "km_candidate_evaluation.py"
PROBES = (
    "road to damascus",
    "as far as possible",
    "independent state of papua new guinea",
    "full phase of the moon",
    "union jack",
    "atomic number 98",
    "law of definite proportions",
    "round the bend",
    "throw in the towel",
    "flip one's lid",
    "luck through",
    "now and then",
)


def test_module_has_no_phrase_exception_or_probe_surface():
    assert rule_surface_violations(MODULE.read_text(encoding="utf-8"), PROBES) == []


def test_join_does_not_accept_surface_gloss_or_operator_label():
    names = set(inspect.signature(join_synset).parameters)
    assert names == {"synset", "exact", "ambiguous"}
    assert "gloss" not in inspect.signature(align_item).parameters


def test_lookup_key_folds_case_and_apostrophe_and_keeps_hyphen():
    assert lookup_key("Prince Albert") == "prince_albert"
    assert lookup_key("fool\u2019s paradise") == "fool's_paradise"
    assert lookup_key("parenthesis-free notation") == "parenthesis-free_notation"
    assert lookup_key("parenthesis-free notation") != lookup_key("parenthesis free notation")


def test_unique_reconstruction_maps_labels_and_polysemy_does_not():
    one = align_item("NONCOMPOSITIONAL", None, ["noun:1"])
    assert one["alignment_status"] == EXACT_UNIQUE_RECONSTRUCTION
    assert one["semantic_noncompositional"] == "YES"
    assert one["primary_evidence_code"] == "km_exact_noncompositional"
    assert one["aligned_pwn30_synset"] == "noun:1"
    other = align_item("COMPOSITIONAL", None, ["noun:2"])
    assert other["semantic_noncompositional"] == "NO"
    assert other["primary_evidence_code"] == "km_exact_compositional"
    many = align_item("NONCOMPOSITIONAL", None, ["noun:3", "noun:4"])
    assert many["alignment_status"] == AMBIGUOUS_MULTIPLE_SYNSETS
    assert many["semantic_noncompositional"] == UNKNOWN
    assert many["aligned_pwn30_synset"] is None
    assert many["primary_evidence_code"] == "km_ambiguous_synset"
    missing = align_item("NONCOMPOSITIONAL", None, [])
    assert missing["alignment_status"] == NO_PWN3_MATCH
    assert missing["semantic_noncompositional"] == UNKNOWN
    assert missing["primary_evidence_code"] == "km_no_match"


def test_a_source_identifier_must_name_one_synset():
    found = align_item("COMPOSITIONAL", "noun:9", ["noun:9"])
    assert found["alignment_status"] == "EXACT_SOURCE_ID"
    assert found["semantic_noncompositional"] == "NO"
    conflict = align_item("NONCOMPOSITIONAL", "noun:8", ["noun:9"])
    assert conflict["alignment_status"] == "VERSION_CONFLICT"
    assert conflict["semantic_noncompositional"] == UNKNOWN
    assert conflict["primary_evidence_code"] == "km_version_conflict"
    tied = align_item("NONCOMPOSITIONAL", "noun:3", ["noun:3", "noun:4"])
    assert tied["alignment_status"] == AMBIGUOUS_MULTIPLE_SYNSETS
    assert tied["semantic_noncompositional"] == UNKNOWN


def test_hyperlex_join_is_synset_identity_only():
    exact = {
        "noun:1": {
            "alignment_status": EXACT_UNIQUE_RECONSTRUCTION,
            "semantic_noncompositional": "YES",
            "source_item_id": "KM-1",
            "aligned_pwn30_synset": "noun:1",
        }
    }
    ambiguous = {"noun:2": ["KM-2"]}
    hit = join_synset("noun:1", exact, ambiguous)
    assert hit["semantic_noncompositional"] == "YES"
    assert hit["candidate_source_item_id"] == "KM-1"
    other_sense = join_synset("noun:9", exact, ambiguous)
    assert other_sense["semantic_noncompositional"] == UNKNOWN
    assert other_sense["primary_evidence_code"] == "km_no_match"
    assert other_sense["candidate_aligned_synset"] is None
    polyseme = join_synset("noun:2", exact, ambiguous)
    assert polyseme["alignment_status"] == AMBIGUOUS_MULTIPLE_SYNSETS
    assert polyseme["semantic_noncompositional"] == UNKNOWN
    assert polyseme["candidate_aligned_synset"] is None
    assert polyseme["primary_evidence_code"] == "km_ambiguous_synset"
