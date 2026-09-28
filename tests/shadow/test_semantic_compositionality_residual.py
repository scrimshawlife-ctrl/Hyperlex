import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.semantic_compositionality_residual import (
    AMBIGUOUS,
    EXACT,
    UNIQUE,
    UNRESOLVED,
    candidate_policy,
    distribution,
    evaluation_status,
    exact_synset_ids,
    extract_constituents,
    lexical_synset_ids,
    percentile,
    representation_text,
    residual_score,
    resolve_constituent,
    resolved_synset,
    score_record,
    select_lemma,
    vector_hash,
)
from hyperlexical.unbind_screen_v4 import rule_surface_violations

MODULE = ROOT / "scripts" / "shadow" / "hyperlexical" / "semantic_compositionality_residual.py"
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


def _extraction(surface: str = "alpha beta") -> dict:
    return extract_constituents(surface)


def test_module_has_no_phrase_exception_or_probe_surface():
    assert rule_surface_violations(MODULE.read_text(encoding="utf-8"), PROBES) == []


def test_resolution_does_not_accept_gloss_or_operator_labels():
    blocked = (
        exact_synset_ids,
        lexical_synset_ids,
        resolve_constituent,
        resolved_synset,
        score_record,
        residual_score,
    )
    for function in blocked:
        names = set(inspect.signature(function).parameters)
        assert "gloss" not in names
        assert "operator_bucket" not in names
        assert "operator_label" not in names
    policy = candidate_policy()
    assert "gloss_similarity" in policy["constituent_sense_resolution"]["forbidden"]
    assert policy["semantic_noncompositionality_threshold"] is None
    assert policy["emits_yes_no"] is False
    assert not hasattr(sys.modules["hyperlexical.semantic_compositionality_residual"], "gloss_similarity")


def test_structural_tokens_leave_content_words():
    towel = extract_constituents("throw in the towel")
    assert towel["surface_tokens"] == ["throw", "in", "the", "towel"]
    assert towel["content_constituents"] == ["throw", "towel"]
    assert towel["ignored_structural_tokens"] == ["in", "the"]
    assert towel["constituent_extraction_status"] == "EXTRACTED"
    shots = extract_constituents("call the shots")
    assert shots["content_constituents"] == ["call", "shots"]
    assert shots["ignored_structural_tokens"] == ["the"]
    luck = extract_constituents("as luck would have it")
    assert luck["content_constituents"] == ["luck"]
    assert luck["constituent_extraction_status"] == "UNKNOWN"
    folded = extract_constituents("Throw In The Towel")
    assert folded["content_constituents"] == ["Throw", "Towel"]
    assert folded["ignored_structural_tokens"] == ["In", "The"]
    hyphen = extract_constituents("well-known person")
    assert hyphen["content_constituents"] == ["well-known", "person"]
    owned = extract_constituents("one\u2019s own goal")
    assert owned["ignored_structural_tokens"] == ["one\u2019s"]
    assert owned["content_constituents"] == ["own", "goal"]


def test_exact_pointer_beats_polysemy_and_zero_target_does_not_count():
    pointers = [
        ("+", 1, "noun:1", "towel"),
        ("+", 0, "noun:9", "towel"),
        ("@", 1, "noun:8", "towel"),
        ("\\", 2, "noun:1", "towels"),
    ]
    exact = exact_synset_ids(
        pointers,
        "towel",
        {"towel": {"towels"}, "towels": {"towel"}},
    )
    assert exact == ["noun:1", "noun:1"]
    assert resolve_constituent(exact, ["noun:1", "noun:2", "verb:3"]) == EXACT
    assert resolved_synset(exact, ["noun:2"]) == "noun:1"
    many = exact_synset_ids(
        [("+", 1, "noun:1", "shot"), ("+", 1, "noun:2", "shot")],
        "shots",
        {"shots": {"shot"}},
    )
    assert resolve_constituent(many, ["noun:1"]) == AMBIGUOUS
    assert resolved_synset(many, ["noun:1"]) is None


def test_lexical_resolution_abstains_when_several_synsets_match():
    index = {"towel": ["noun:4"], "shot": ["noun:5", "noun:6"]}
    one = lexical_synset_ids(index, "towel", {})
    assert resolve_constituent([], one) == UNIQUE
    assert resolved_synset([], one) == "noun:4"
    many = lexical_synset_ids(index, "shots", {"shots": {"shot"}})
    assert resolve_constituent([], many) == AMBIGUOUS
    assert resolve_constituent([], []) == UNRESOLVED
    assert select_lemma(["towel", "bath_towel"], "towels", {"towels": {"towel"}}) == "towel"


def test_residual_is_continuous_and_deterministic():
    same = residual_score([1.0, 0.0], [[1.0, 0.0], [1.0, 0.0]])
    assert same is not None
    assert same[0] == "0.0000000000"
    orthogonal = residual_score([1.0, 0.0], [[0.0, 1.0], [0.0, 1.0]])
    assert orthogonal is not None
    assert orthogonal[0] == "1.0000000000"
    assert residual_score([0.0, 0.0], [[1.0, 0.0], [0.0, 1.0]]) is None
    assert vector_hash([1.0, 0.0]) == vector_hash([1.0, 0.0])
    assert vector_hash([1.0, 0.0]) != vector_hash([0.0, 1.0])
    assert len(vector_hash([1.0])) == 64
    text = representation_text("bath_towel", "noun", "  a towel   ")
    assert text == "bath towel (noun): a towel"


def test_ambiguous_constituent_is_unknown_and_is_not_encoded():
    extraction = _extraction("call the shots")
    record = score_record(
        row_id="row",
        surface="call the shots",
        pos="verb",
        synset="verb:00000001",
        extraction=extraction,
        resolutions=["UNIQUE", "AMBIGUOUS"],
        resolved_synsets=["verb:2", None],
        resolved_lemmas=["call", None],
        whole_representation=None,
        constituent_representations=None,
        whole_vector=None,
        constituent_vectors=None,
        candidate_spec_sha256="spec",
    )
    assert record["score_status"] == "UNKNOWN"
    assert record["primary_abstention_reason"] == "ambiguous_content_constituent"
    assert record["residual_score"] is None
    assert record["whole_vector_hash"] is None
    assert record["constituent_resolution_status"] == ["UNIQUE", "AMBIGUOUS"]
    short = score_record(
        row_id="row",
        surface="as luck would have it",
        pos="noun",
        synset="noun:00000002",
        extraction=extract_constituents("as luck would have it"),
        resolutions=[],
        resolved_synsets=[],
        resolved_lemmas=[],
        whole_representation=None,
        constituent_representations=None,
        whole_vector=None,
        constituent_vectors=None,
        candidate_spec_sha256="spec",
    )
    assert short["primary_abstention_reason"] == "fewer_than_two_content_constituents"
    assert short["resolved_constituent_synsets"] == []


def test_scored_row_keeps_a_residual_and_status_ignores_agreement():
    extraction = _extraction()
    record = score_record(
        row_id="row",
        surface="alpha beta",
        pos="noun",
        synset="noun:00000003",
        extraction=extraction,
        resolutions=["EXACT", "UNIQUE"],
        resolved_synsets=["noun:1", "noun:2"],
        resolved_lemmas=["alpha", "beta"],
        whole_representation="alpha beta (noun): a whole",
        constituent_representations=["alpha (noun): one", "beta (noun): two"],
        whole_vector=[1.0, 0.0],
        constituent_vectors=[[1.0, 0.0], [1.0, 0.0]],
        candidate_spec_sha256="spec",
    )
    assert record["score_status"] == "SCORED"
    assert record["residual_score"] == "0.0000000000"
    assert record["primary_abstention_reason"] is None
    assert record["composition_operator"] == "normalized_mean_v1"
    assert record["whole_vector_hash"]
    assert len(record["constituent_vector_hashes"]) == 2
    overflow = score_record(
        row_id="row",
        surface="alpha beta",
        pos="noun",
        synset="noun:00000003",
        extraction=extraction,
        resolutions=["EXACT", "UNIQUE"],
        resolved_synsets=["noun:1", "noun:2"],
        resolved_lemmas=["alpha", "beta"],
        whole_representation=None,
        constituent_representations=None,
        whole_vector=None,
        constituent_vectors=None,
        candidate_spec_sha256="spec",
        sequence_overflow=True,
    )
    assert overflow["primary_abstention_reason"] == "representation_exceeds_max_sequence_length"
    assert evaluation_status(0) == (
        "CANDIDATE_INSUFFICIENT",
        "NEXT_CANDIDATE_SOURCE_EVALUATION_AUTHORIZATION",
    )
    assert evaluation_status(3) == (
        "CANDIDATE_DISTRIBUTION_FROZEN",
        "RESIDUAL_THRESHOLD_FREEZE_AUTHORIZATION",
    )


def test_percentile_uses_preregistered_linear_interpolation():
    values = ["0.0000000000", "1.0000000000", "2.0000000000", "3.0000000000"]
    assert percentile(values, 25) == "0.7500000000"
    assert percentile(values, 50) == "1.5000000000"
    assert percentile(values, 75) == "2.2500000000"
    empty = distribution([])
    assert empty["status"] == "NOT_COMPUTABLE"
    assert empty["median"] is None
    filled = distribution(values)
    assert filled["status"] == "DESCRIPTIVE"
    assert filled["min"] == "0.0000000000"
    assert filled["max"] == "3.0000000000"
    assert filled["mean"] == "1.5000000000"
