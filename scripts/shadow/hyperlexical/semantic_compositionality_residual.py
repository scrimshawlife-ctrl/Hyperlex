"""Continuous semantic residual for one bound PWN 3.0 sense.

The score compares the supplied synset with a normalized mean of resolved
constituent synsets. It is not a yes/no label, and it does not select a source.
"""

from __future__ import annotations

import hashlib
import math
import struct
from decimal import Decimal, ROUND_HALF_EVEN

from hyperlexical.km_candidate_evaluation import lookup_key

CANDIDATE = "RUNE.SEMANTIC_COMPOSITIONALITY_RESIDUAL.v1"
COMPOSITION_OPERATOR = "normalized_mean_v1"
DISTANCE_METRIC = "one_minus_cosine_v1"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
RESIDUAL_QUANTUM = Decimal("0.0000000001")
RELATION_SYMBOLS = frozenset({"+", "\\"})
MIN_CONTENT_CONSTITUENTS = 2
EXTRACTED = "EXTRACTED"
UNKNOWN = "UNKNOWN"
EXACT = "EXACT"
UNIQUE = "UNIQUE"
AMBIGUOUS = "AMBIGUOUS"
UNRESOLVED = "UNRESOLVED"
SCORED = "SCORED"
RESOLVED = frozenset({EXACT, UNIQUE})

STRUCTURAL_TOKENS = frozenset(
    {
        "a",
        "about",
        "across",
        "after",
        "against",
        "all",
        "amid",
        "among",
        "amongst",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "been",
        "before",
        "behind",
        "being",
        "below",
        "beside",
        "between",
        "beyond",
        "both",
        "but",
        "by",
        "can",
        "could",
        "did",
        "do",
        "does",
        "down",
        "during",
        "each",
        "every",
        "except",
        "for",
        "from",
        "had",
        "has",
        "have",
        "her",
        "his",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "least",
        "less",
        "may",
        "might",
        "more",
        "most",
        "must",
        "my",
        "no",
        "none",
        "nor",
        "not",
        "of",
        "off",
        "on",
        "one's",
        "onto",
        "or",
        "our",
        "out",
        "over",
        "per",
        "shall",
        "should",
        "some",
        "than",
        "that",
        "the",
        "their",
        "them",
        "then",
        "these",
        "this",
        "those",
        "through",
        "to",
        "toward",
        "towards",
        "under",
        "up",
        "upon",
        "via",
        "versus",
        "was",
        "were",
        "will",
        "with",
        "within",
        "without",
        "would",
        "your",
    }
)


_RULE_AMBIGUOUS = (
    "A content constituent with two or more exact targets, or with no exact "
    "target and two or more lexical synsets, abstains the row."
)
_RULE_SHORT = (
    "Whitespace tokenization must leave at least two tokens outside the frozen structural class."
)
_RULE_OVERFLOW = (
    "A whole-sense or constituent text longer than the pinned max sequence length "
    "abstains the row. The encoder must not truncate it."
)
_RULE_UNRESOLVED = "A content constituent with no exact target and no lexical synset abstains the row."
_RULE_ZERO = "A non-finite or zero encoder vector, or a zero composed vector, abstains the row."
_HIGH_PROXY = "a proxy for expected noncompositionality"
_SECONDARY_PROXY = "a proxy for expected compositionality"
_REJECT_AXIS = "a referential axis, not semantic no"
_QUARANTINE_AXIS = "not semantic evidence"
_PERCENTILE_RULE = (
    "linear interpolation at rank (n-1)*(p/100), then round-half-even to 10 decimal places"
)
_COMPOSITION_PROCEDURE = (
    "L2-normalize each constituent vector in binary64, take the arithmetic mean, "
    "then L2-normalize that mean"
)
_DUPLICATE_SYNSETS = "kept once per content token"
_HYPHEN_RULE = "kept as one token"
_MEMBERSHIP_RULE = "lookup_key of the whitespace token is in the structural class"
_EXACT_RULE = (
    "one synset reached by a derivation or pertainym pointer whose target word "
    "number is nonzero and whose target lemma matches the constituent or a one-hop "
    "exception neighbor"
)
_AMBIGUOUS_RULE = (
    "more than one exact target synset, or no exact target and more than one lexical synset"
)
_LEXICAL_SCOPE = (
    "one lookup key plus one-hop bidirectional exception neighbors, across noun, verb, adj, and adv"
)
_SOURCE_WORD = "not a filter"
_TARGET_ZERO = "does not name a lemma"
_UNIQUE_RULE = "no exact target, and the lexical keys name one synset"
_UNRESOLVED_RULE = "no exact target and no lexical synset"
_DISTANCE_FORMULA = "1 - binary64_dot(l2_normalize(whole), l2_normalize(composed))"
_DISTANCE_RECORD = "format(value, '.10f'), round-half-even, no clamp"
_TEMPLATE = "{surface} ({pos}): {gloss}"
_TEXT_NORMALIZATION = "underscores become spaces; whitespace collapses; gloss is the supplied first clause"
_VECTOR_HASH_RULE = "sha256 of little-endian binary32 bytes in dimension order"
_WHOLE_SENSE_RULE = "the supplied Hyperlex surface, POS, and frozen gloss; no substitute synset"


def candidate_policy() -> dict:
    """Return the preregistered design. The dict has no row scores."""
    return {
        "abstention_priority": [
            "fewer_than_two_content_constituents",
            "leftmost_unresolved_or_ambiguous_content_constituent",
            "representation_exceeds_max_sequence_length",
            "zero_vector",
        ],
        "abstention_rules": {
            "ambiguous_content_constituent": _RULE_AMBIGUOUS,
            "fewer_than_two_content_constituents": _RULE_SHORT,
            "representation_exceeds_max_sequence_length": _RULE_OVERFLOW,
            "unresolved_content_constituent": _RULE_UNRESOLVED,
            "zero_vector": _RULE_ZERO,
        },
        "analysis_plan": {
            "high_comparison_if_no_high_row_is_scored": "NOT_COMPUTABLE",
            "high_is": _HIGH_PROXY,
            "join_operator_labels_only_after_score_artifact_is_hashed": True,
            "operator_labels_are_scoring_inputs": False,
            "percentile": _PERCENTILE_RULE,
            "primary_bucket": "HIGH",
            "quarantine_is": _QUARANTINE_AXIS,
            "reject_is": _REJECT_AXIS,
            "secondary_is": _SECONDARY_PROXY,
            "semantic_noncompositionality_threshold": None,
        },
        "candidate": CANDIDATE,
        "composition_operator": {
            "duplicate_constituent_synsets": _DUPLICATE_SYNSETS,
            "name": COMPOSITION_OPERATOR,
            "procedure": _COMPOSITION_PROCEDURE,
            "weights": None,
        },
        "constituent_extraction": {
            "content_minimum": MIN_CONTENT_CONSTITUENTS,
            "hyphenated_token": _HYPHEN_RULE,
            "membership": _MEMBERSHIP_RULE,
            "structural_tokens": sorted(STRUCTURAL_TOKENS),
            "tokenizer": "str.split",
        },
        "constituent_sense_resolution": {
            "ambiguous": _AMBIGUOUS_RULE,
            "exact": _EXACT_RULE,
            "forbidden": [
                "arbitrary_first_sense",
                "embedding_similarity",
                "gloss_similarity",
                "language_model_judge",
                "manual_selection",
                "operator_labels",
            ],
            "lexical_scope": _LEXICAL_SCOPE,
            "source_word_number": _SOURCE_WORD,
            "target_word_number_zero": _TARGET_ZERO,
            "unique": _UNIQUE_RULE,
            "unresolved": _UNRESOLVED_RULE,
        },
        "distance_metric": {
            "formula": _DISTANCE_FORMULA,
            "name": DISTANCE_METRIC,
            "record": _DISTANCE_RECORD,
        },
        "emits_yes_no": False,
        "model_identity": {
            "name": MODEL_NAME,
            "revision": MODEL_REVISION,
        },
        "representation_template": _TEMPLATE,
        "representation_text_normalization": _TEXT_NORMALIZATION,
        "row_unknown_if_any_required_content_constituent_is_not_exact_or_unique": True,
        "semantic_noncompositionality_threshold": None,
        "status_rule": {
            "scored_count_eq_0": {
                "next_legal_transition": "NEXT_CANDIDATE_SOURCE_EVALUATION_AUTHORIZATION",
                "status": "CANDIDATE_INSUFFICIENT",
            },
            "scored_count_gt_0": {
                "next_legal_transition": "RESIDUAL_THRESHOLD_FREEZE_AUTHORIZATION",
                "status": "CANDIDATE_DISTRIBUTION_FROZEN",
            },
        },
        "vector_hash": _VECTOR_HASH_RULE,
        "whole_sense": _WHOLE_SENSE_RULE,
    }


def extract_constituents(surface: str) -> dict:
    """Split a surface on whitespace and apply the frozen structural class."""
    tokens = surface.split()
    content = []
    structural = []
    for token in tokens:
        if lookup_key(token) in STRUCTURAL_TOKENS:
            structural.append(token)
        else:
            content.append(token)
    status = EXTRACTED if len(content) >= MIN_CONTENT_CONSTITUENTS else UNKNOWN
    return {
        "constituent_extraction_status": status,
        "content_constituents": content,
        "ignored_structural_tokens": structural,
        "surface_tokens": tokens,
    }


def neighbor_keys(text: str, exceptions: dict[str, set[str]]) -> set[str]:
    """Return the lookup key plus one-hop exception neighbors."""
    own = lookup_key(text)
    keys = {own}
    raw = text.casefold().replace("\u2019", "'").replace("\u2018", "'").replace("`", "'")
    related: set[str] = set()
    for form in (raw, own, own.replace("_", " ")):
        related.update(exceptions.get(form, ()))
    for item in related:
        keys.add(lookup_key(item))
    return keys


def exact_synset_ids(
    pointers: list[tuple[str, int, str, str]],
    constituent: str,
    exceptions: dict[str, set[str]],
) -> list[str]:
    """Collect derivation and pertainym targets that name this constituent."""
    keys = neighbor_keys(constituent, exceptions)
    found = []
    for symbol, target_word, synset_id, lemma in pointers:
        if symbol not in RELATION_SYMBOLS or target_word <= 0 or not lemma:
            continue
        if lookup_key(lemma) not in keys:
            continue
        found.append(synset_id)
    return found


def lexical_synset_ids(
    index: dict[str, list[str]],
    constituent: str,
    exceptions: dict[str, set[str]],
) -> list[str]:
    """Collect synsets named by the constituent key or one exception hop."""
    found = []
    for key in sorted(neighbor_keys(constituent, exceptions)):
        found.extend(index.get(key, ()))
    return found


def resolve_constituent(exact_synset_ids_found: list[str], lexical_synset_ids_found: list[str]) -> str:
    """Resolve one constituent. Exact evidence outranks lemma polysemy."""
    exact = list(dict.fromkeys(exact_synset_ids_found))
    if len(exact) == 1:
        return EXACT
    if len(exact) > 1:
        return AMBIGUOUS
    lexical = list(dict.fromkeys(lexical_synset_ids_found))
    if len(lexical) == 1:
        return UNIQUE
    if len(lexical) > 1:
        return AMBIGUOUS
    return UNRESOLVED


def resolved_synset(exact_synset_ids_found: list[str], lexical_synset_ids_found: list[str]) -> str | None:
    status = resolve_constituent(exact_synset_ids_found, lexical_synset_ids_found)
    if status == EXACT:
        return list(dict.fromkeys(exact_synset_ids_found))[0]
    if status == UNIQUE:
        return list(dict.fromkeys(lexical_synset_ids_found))[0]
    return None


def select_lemma(lemmas: list[str], constituent: str, exceptions: dict[str, set[str]]) -> str:
    """Pick one lemma. Matching keys win, and lookup order breaks remaining ties."""
    keys = neighbor_keys(constituent, exceptions)
    matches = [lemma for lemma in lemmas if lookup_key(lemma) in keys]
    pool = matches or list(lemmas)
    if not pool:
        raise RuntimeError("resolved synset has no lemma")
    return min(pool, key=lookup_key)


def representation_text(surface: str, pos: str, gloss: str) -> str:
    shown = " ".join(surface.replace("_", " ").split())
    gloss_text = " ".join(gloss.split())
    return f"{shown} ({pos}): {gloss_text}"


def l2_normalize(values: list[float]) -> list[float] | None:
    if not values or any(not math.isfinite(value) for value in values):
        return None
    norm = math.sqrt(sum(value * value for value in values))
    if not math.isfinite(norm) or norm == 0.0:
        return None
    return [value / norm for value in values]


def composed_vector(parts: list[list[float]]) -> list[float] | None:
    """Normalized mean. Each input vector is normalized again in binary64."""
    if len(parts) < MIN_CONTENT_CONSTITUENTS:
        return None
    width = len(parts[0])
    if any(len(part) != width for part in parts):
        raise RuntimeError("constituent vectors differ in width")
    normalized = []
    for part in parts:
        unit = l2_normalize(part)
        if unit is None:
            return None
        normalized.append(unit)
    count = float(len(normalized))
    mean = [sum(part[index] for part in normalized) / count for index in range(width)]
    return l2_normalize(mean)


def format_residual(dot: float) -> str:
    value = 1.0 - dot
    if not math.isfinite(value):
        raise RuntimeError("non-finite residual")
    if value == 0.0:
        value = 0.0
    return format(value, ".10f")


def residual_score(whole: list[float], constituents: list[list[float]]) -> tuple[str, list[float]] | None:
    """Return the 10-decimal residual and the composed vector."""
    whole_unit = l2_normalize(whole)
    composed = composed_vector(constituents)
    if whole_unit is None or composed is None:
        return None
    dot = sum(left * right for left, right in zip(whole_unit, composed))
    if not math.isfinite(dot):
        return None
    return format_residual(dot), composed


def vector_hash(values: list[float]) -> str:
    blob = b"".join(struct.pack("<f", float(value)) for value in values)
    return hashlib.sha256(blob).hexdigest()


def primary_abstention(extraction_status: str, resolutions: list[str]) -> str | None:
    if extraction_status != EXTRACTED or len(resolutions) < MIN_CONTENT_CONSTITUENTS:
        return "fewer_than_two_content_constituents"
    for status in resolutions:
        if status == AMBIGUOUS:
            return "ambiguous_content_constituent"
        if status == UNRESOLVED:
            return "unresolved_content_constituent"
        if status not in RESOLVED:
            raise RuntimeError(f"unknown resolution status {status}")
    return None


def score_record(
    *,
    row_id: str,
    surface: str,
    pos: str,
    synset: str,
    extraction: dict,
    resolutions: list[str],
    resolved_synsets: list[str | None],
    resolved_lemmas: list[str | None],
    whole_representation: str | None,
    constituent_representations: list[str] | None,
    whole_vector: list[float] | None,
    constituent_vectors: list[list[float]] | None,
    candidate_spec_sha256: str,
    sequence_overflow: bool = False,
) -> dict:
    """Score one row. Operator labels are not parameters."""
    reason = primary_abstention(extraction["constituent_extraction_status"], resolutions)
    if reason is None and sequence_overflow:
        reason = "representation_exceeds_max_sequence_length"
    residual = None
    whole_hash = None
    constituent_hashes = None
    composed_hash = None
    if reason is None:
        if whole_vector is None or constituent_vectors is None:
            raise RuntimeError("a resolvable row has no vectors")
        if len(constituent_vectors) != len(resolutions):
            raise RuntimeError("constituent vector count does not match resolutions")
        scored = residual_score(whole_vector, constituent_vectors)
        whole_hash = vector_hash(whole_vector)
        constituent_hashes = [vector_hash(vector) for vector in constituent_vectors]
        if scored is None:
            reason = "zero_vector"
        else:
            residual, composed = scored
            composed_hash = vector_hash(composed)
    elif whole_vector is not None or constituent_vectors is not None:
        raise RuntimeError("an abstaining row was encoded")
    extracted = extraction["constituent_extraction_status"] == EXTRACTED
    return {
        "candidate_spec_sha256": candidate_spec_sha256,
        "composition_operator": COMPOSITION_OPERATOR,
        "composed_vector_hash": composed_hash,
        "constituent_extraction_status": extraction["constituent_extraction_status"],
        "constituent_representations": constituent_representations if residual is not None else None,
        "constituent_resolution_status": list(resolutions),
        "constituent_vector_hashes": constituent_hashes,
        "content_constituents": list(extraction["content_constituents"]),
        "distance_metric": DISTANCE_METRIC,
        "ignored_structural_tokens": list(extraction["ignored_structural_tokens"]),
        "pos": pos,
        "primary_abstention_reason": reason,
        "residual_score": residual,
        "resolved_constituent_lemmas": list(resolved_lemmas) if extracted else [],
        "resolved_constituent_synsets": list(resolved_synsets) if extracted else [],
        "row_id": row_id,
        "score_status": SCORED if residual is not None else UNKNOWN,
        "surface": surface,
        "surface_tokens": list(extraction["surface_tokens"]),
        "synset": synset,
        "whole_representation": whole_representation if residual is not None else None,
        "whole_vector_hash": whole_hash,
    }


def evaluation_status(scored_count: int) -> tuple[str, str]:
    """Map the scored count to a status. The count is not a label agreement."""
    if scored_count < 0:
        raise RuntimeError("negative scored count")
    if scored_count == 0:
        return "CANDIDATE_INSUFFICIENT", "NEXT_CANDIDATE_SOURCE_EVALUATION_AUTHORIZATION"
    return "CANDIDATE_DISTRIBUTION_FROZEN", "RESIDUAL_THRESHOLD_FREEZE_AUTHORIZATION"


def percentile(sorted_values: list[str], percent: int) -> str:
    """Linear interpolation on already-sorted 10-decimal residual strings."""
    count = len(sorted_values)
    if count == 0:
        raise RuntimeError("percentile of an empty sample")
    if count == 1:
        return sorted_values[0]
    rank = Decimal(count - 1) * (Decimal(percent) / Decimal(100))
    low = int(rank)
    high = min(low + 1, count - 1)
    weight = rank - Decimal(low)
    blended = Decimal(sorted_values[low]) + (Decimal(sorted_values[high]) - Decimal(sorted_values[low])) * weight
    return str(blended.quantize(RESIDUAL_QUANTUM, rounding=ROUND_HALF_EVEN))


def decimal_mean(values: list[str]) -> str:
    total = sum((Decimal(value) for value in values), start=Decimal(0))
    mean = total / Decimal(len(values))
    return str(mean.quantize(RESIDUAL_QUANTUM, rounding=ROUND_HALF_EVEN))


def distribution(scores: list[str]) -> dict:
    if not scores:
        return {
            "count": 0,
            "max": None,
            "mean": None,
            "median": None,
            "min": None,
            "p25": None,
            "p75": None,
            "status": "NOT_COMPUTABLE",
        }
    ordered = sorted(scores, key=Decimal)
    return {
        "count": len(ordered),
        "max": ordered[-1],
        "mean": decimal_mean(ordered),
        "median": percentile(ordered, 50),
        "min": ordered[0],
        "p25": percentile(ordered, 25),
        "p75": percentile(ordered, 75),
        "status": "DESCRIPTIVE",
    }
