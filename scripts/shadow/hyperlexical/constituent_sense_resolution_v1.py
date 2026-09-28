"""Deterministic constituent-sense resolution for a Hyperlex multiword row.

Structural WordNet evidence outranks contextual overlap. Extended Lesk uses
gloss text only. Operator labels, residual scores, and embeddings are not inputs.
"""

from __future__ import annotations

from hyperlexical.km_candidate_evaluation import lookup_key
from hyperlexical.semantic_compositionality_residual import (
    STRUCTURAL_TOKENS,
    neighbor_keys,
)

RULE_VERSION = "RUNE.CONSTITUENT_SENSE_RESOLUTION.v1"
EXTENDED_LESK = "EXTENDED_LESK_V1"
STRUCTURAL_EXACT = "STRUCTURAL_EXACT"
UNIQUE_LEMMA = "UNIQUE_LEMMA"
METHOD_NONE = "NONE"
EXACT = "EXACT"
RESOLVED = "RESOLVED"
AMBIGUOUS = "AMBIGUOUS"
UNRESOLVED = "UNRESOLVED"
RESIDUAL_READY = "RESIDUAL_READY"
ROW_UNKNOWN = "UNKNOWN"
MINIMUM_MARGIN = 1
RELATION_DEPTH = 1
LEXICAL_POINTER_SYMBOLS = frozenset({"!", "+", "\\", "^", "*", "&", "<", "$"})
RELATION_EXPANSION_SYMBOLS = frozenset({"@", "+", "\\", "&", "^", "="})
READY_STATUSES = frozenset({EXACT, RESOLVED})

_RESEARCH_QUESTION = (
    "Can Hyperlex deterministically resolve enough content-constituent WordNet "
    "senses to construct a semantic compositional baseline, without using "
    "operator labels or residual scores as evidence?"
)
_LESK_SCORE_RULE = (
    "Greedy longest contiguous token overlap. Each match adds the square of its "
    "length. Matched tokens are removed. Search restarts until no token matches."
)
_TIE_RULE = (
    "Integer scores. If the top score minus the second score is below the minimum "
    "margin, the constituent is AMBIGUOUS. Equal scores are a tie. No sense is chosen."
)
_STOPWORD_RULE = (
    "Tokens whose lookup form is in the residual v1 structural class are removed, "
    "as are tokens shorter than two characters. No stemmer and no lemmatizer."
)
_CONTEXT_RULE = (
    "Context is the parent frozen gloss plus the first gloss clause of every other "
    "content constituent in the row that structural evidence already resolved. "
    "Lesk output is not context."
)
_CANDIDATE_TEXT_RULE = (
    "A candidate contributes its full PWN 3.0 gloss, including quoted examples, "
    "then the first gloss clause of each depth-1 related synset."
)
_CIRCULARITY_RULE = (
    "The parent gloss is local context. It is not an embedding target. Parent sense "
    "is not constituent sense."
)
_NORMALIZATION_RULE = (
    "casefold, apostrophe fold, split on characters outside letters, digits, apostrophe, and hyphen"
)
_TARGET_ZERO = "does not name a lemma"
_TIER_CONFLICT = "more than one structural target is AMBIGUOUS and blocks Lesk"
_TIER_STRUCTURAL = (
    "one lexical pointer whose target word number is nonzero and whose lemma matches "
    "the constituent or one exception hop"
)
_TIER_UNIQUE = "no structural target and one lemma synset across noun, verb, adj, and adv"
_TIER_UNRESOLVED = "no structural target and no lemma synset"
_READY_REQUIRES = "at_least_two_content_constituents_and_each_is_EXACT_or_RESOLVED"
_EMPTY_ROW = (
    "Every content constituent is resolved. A row with fewer than two content "
    "constituents stays UNKNOWN. A row with none emits one abstention record."
)


def resolver_policy() -> dict:
    """Return the preregistered resolver. The dict has no development counts."""
    return {
        "applied_at_freeze": False,
        "candidate_text": _CANDIDATE_TEXT_RULE,
        "circularity": _CIRCULARITY_RULE,
        "context": _CONTEXT_RULE,
        "empty_row": _EMPTY_ROW,
        "encoded_at_freeze": False,
        "extended_lesk": {
            "examples_included_for_candidate": True,
            "examples_included_for_related_synsets": False,
            "method": EXTENDED_LESK,
            "minimum_margin": MINIMUM_MARGIN,
            "minimum_token_length": 2,
            "normalization": _NORMALIZATION_RULE,
            "relation_depth": RELATION_DEPTH,
            "relation_symbols": sorted(RELATION_EXPANSION_SYMBOLS),
            "related_gloss": "first_clause",
            "score": _LESK_SCORE_RULE,
            "stemming": False,
            "stopwords": _STOPWORD_RULE,
            "structural_tokens": sorted(STRUCTURAL_TOKENS),
            "tie": _TIE_RULE,
            "zero_overlap_is_a_tie": True,
        },
        "forbidden_inputs": [
            "embedding_similarity",
            "language_model_judge",
            "manual_selection",
            "operator_labels",
            "phrase_exceptions",
            "residual_scores",
            "unbind_bucket",
        ],
        "measurement_eligible": False,
        "research_question": _RESEARCH_QUESTION,
        "row_rule": {
            "ready": RESIDUAL_READY,
            "ready_requires": _READY_REQUIRES,
            "unknown": ROW_UNKNOWN,
        },
        "rule": RULE_VERSION,
        "state_at_freeze": "SPEC_FROZEN",
        "status_rule": {
            "baseline_ambiguous_not_resolved_gt_half": {
                "finding": "CONSTITUENT_WSD_COVERAGE_INSUFFICIENT",
                "next_legal_transition": "MODEL_BASED_WSD_CANDIDATE_EVALUATION_AUTHORIZATION",
                "status": "COVERAGE_INSUFFICIENT",
            },
            "else_if_residual_ready_high_and_secondary_positive": {
                "finding": None,
                "next_legal_transition": "RESIDUAL_REPLAY_WITH_RESOLVED_SENSES_AUTHORIZATION",
                "status": "COVERAGE_NECESSARY_CONDITION_MET",
            },
            "else": {
                "finding": None,
                "next_legal_transition": "CONSTITUENT_SENSE_RESOLUTION_REVISION_AUTHORIZATION",
                "status": "NECESSARY_CONDITION_UNMET",
            },
        },
        "structural_pointers": sorted(LEXICAL_POINTER_SYMBOLS),
        "target_word_number_zero": _TARGET_ZERO,
        "tier1": {
            "conflict": _TIER_CONFLICT,
            "structural": _TIER_STRUCTURAL,
            "unique_lemma": _TIER_UNIQUE,
            "unresolved": _TIER_UNRESOLVED,
        },
    }


def lesk_tokens(text: str) -> list[str]:
    """Normalize gloss text into overlap tokens."""
    folded = text.casefold().replace("\u2019", "'").replace("\u2018", "'").replace("`", "'")
    tokens = []
    current = []
    for character in folded:
        if character.isascii() and (character.isalnum() or character in "'-"):
            current.append(character)
            continue
        if current:
            tokens.append("".join(current).strip("'-"))
            current = []
    if current:
        tokens.append("".join(current).strip("'-"))
    kept = []
    for token in tokens:
        if len(token) < 2 or lookup_key(token) in STRUCTURAL_TOKENS:
            continue
        kept.append(token)
    return kept


def longest_overlap(context: list[str], candidate: list[str]) -> tuple[int, int, int] | None:
    """Return the leftmost longest contiguous match as context start, candidate start, length."""
    best_length = 0
    best = None
    for context_start, token in enumerate(context):
        for candidate_start, other in enumerate(candidate):
            if other != token:
                continue
            length = 0
            while (
                context_start + length < len(context)
                and candidate_start + length < len(candidate)
                and context[context_start + length] == candidate[candidate_start + length]
            ):
                length += 1
            if length > best_length:
                best_length = length
                best = (context_start, candidate_start, length)
    return best


def overlap_score(context: list[str], candidate: list[str]) -> int:
    """Score one candidate. The same token cannot support two matches."""
    left = list(context)
    right = list(candidate)
    score = 0
    while left and right:
        found = longest_overlap(left, right)
        if found is None:
            break
        context_start, candidate_start, length = found
        score += length * length
        del left[context_start : context_start + length]
        del right[candidate_start : candidate_start + length]
    return score


def structural_synset_ids(
    pointers: list[tuple[str, int, str, str]],
    constituent: str,
    exceptions: dict[str, set[str]],
) -> list[str]:
    """Collect lexical-pointer targets that name this constituent."""
    keys = neighbor_keys(constituent, exceptions)
    found = []
    for symbol, target_word, synset_id, lemma in pointers:
        if symbol not in LEXICAL_POINTER_SYMBOLS or target_word <= 0 or not lemma:
            continue
        if lookup_key(lemma) not in keys:
            continue
        found.append(synset_id)
    return found


def constituent_pos(selected_synset: str | None, candidate_synsets: list[str]) -> str | None:
    if selected_synset:
        return selected_synset.split(":", 1)[0]
    poses = {synset_id.split(":", 1)[0] for synset_id in candidate_synsets}
    if len(poses) == 1:
        return next(iter(poses))
    return None


def resolve_constituent_sense(
    structural_ids: list[str],
    lexical_ids: list[str],
    lesk_scores: list[tuple[str, int]] | None,
) -> dict:
    """Resolve one constituent. Structural evidence blocks contextual overlap."""
    structural = list(dict.fromkeys(structural_ids))
    lexical = list(dict.fromkeys(lexical_ids))
    if len(structural) == 1:
        return _decision(
            EXACT,
            STRUCTURAL_EXACT,
            structural[0],
            None,
            None,
            None,
            "structural_exact_pointer",
            [f"pointer_target:{structural[0]}"],
        )
    if len(structural) > 1:
        return _decision(
            AMBIGUOUS,
            STRUCTURAL_EXACT,
            None,
            None,
            None,
            None,
            "structural_pointer_conflict",
            [f"pointer_target:{synset_id}" for synset_id in structural],
        )
    if len(lexical) == 1:
        return _decision(
            EXACT,
            UNIQUE_LEMMA,
            lexical[0],
            None,
            None,
            None,
            "unique_lemma_synset",
            ["lexical_candidates:1"],
        )
    if not lexical:
        return _decision(
            UNRESOLVED,
            METHOD_NONE,
            None,
            None,
            None,
            None,
            "no_candidate_synset",
            [],
        )
    if lesk_scores is None:
        raise RuntimeError("ambiguous constituent has no Lesk scores")
    scored = {synset_id: score for synset_id, score in lesk_scores}
    if set(scored) != set(lexical) or len(lesk_scores) != len(scored):
        raise RuntimeError("Lesk scores do not match the candidate synsets")
    if any(not isinstance(score, int) for score in scored.values()):
        raise RuntimeError("Lesk scores must be integers")
    ordered = sorted(scored.items(), key=lambda item: (-item[1], item[0]))
    top_id, top_score = ordered[0]
    _second_id, second_score = ordered[1]
    margin = top_score - second_score
    if margin < MINIMUM_MARGIN:
        code = "extended_lesk_tie" if margin == 0 else "extended_lesk_margin"
        return _decision(
            AMBIGUOUS,
            EXTENDED_LESK,
            None,
            top_score,
            second_score,
            margin,
            code,
            [f"lesk_candidates:{len(ordered)}"],
        )
    return _decision(
        RESOLVED,
        EXTENDED_LESK,
        top_id,
        top_score,
        second_score,
        margin,
        "extended_lesk_margin",
        [f"lesk_candidates:{len(ordered)}"],
    )


def _decision(status, method, selected, top_score, second_score, margin, code, support) -> dict:
    return {
        "margin": margin,
        "primary_evidence_code": code,
        "resolution_method": method,
        "resolution_status": status,
        "second_score": second_score,
        "selected_synset": selected,
        "supporting_evidence": list(support),
        "top_score": top_score,
    }


def row_resolution_status(content_count: int, statuses: list[str]) -> str:
    if content_count < 2 or len(statuses) != content_count:
        return ROW_UNKNOWN
    if all(status in READY_STATUSES for status in statuses):
        return RESIDUAL_READY
    return ROW_UNKNOWN


def coverage_decision(
    *,
    baseline_ambiguous: int,
    baseline_ambiguous_not_resolved: int,
    residual_ready_high: int,
    residual_ready_secondary: int,
) -> dict:
    """Apply the preregistered coverage rule. The counts are not a threshold search."""
    if min(baseline_ambiguous, baseline_ambiguous_not_resolved, residual_ready_high, residual_ready_secondary) < 0:
        raise RuntimeError("negative coverage count")
    insufficient = baseline_ambiguous > 0 and baseline_ambiguous_not_resolved * 2 > baseline_ambiguous
    necessary = residual_ready_high > 0 and residual_ready_secondary > 0
    if insufficient:
        status = "COVERAGE_INSUFFICIENT"
        finding = "CONSTITUENT_WSD_COVERAGE_INSUFFICIENT"
        transition = "MODEL_BASED_WSD_CANDIDATE_EVALUATION_AUTHORIZATION"
    elif necessary:
        status = "COVERAGE_NECESSARY_CONDITION_MET"
        finding = None
        transition = "RESIDUAL_REPLAY_WITH_RESOLVED_SENSES_AUTHORIZATION"
    else:
        status = "NECESSARY_CONDITION_UNMET"
        finding = None
        transition = "CONSTITUENT_SENSE_RESOLUTION_REVISION_AUTHORIZATION"
    return {
        "candidate_status": status,
        "coverage_finding": finding,
        "necessary_condition_met": necessary,
        "next_legal_transition": transition,
        "next_transition_authorized": False,
        "state": "DEVELOPMENT_ANALYZED",
    }
