"""Tier-3 model decision for constituent senses that Extended Lesk left tied.

The function selects only among supplied PWN 3.0 candidates, or it abstains.
It does not see operator labels, residual scores, or a residual embedding.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN

from hyperlexical.km_candidate_evaluation import lookup_key
from hyperlexical.semantic_compositionality_residual import (
    STRUCTURAL_TOKENS,
    extract_constituents,
    neighbor_keys,
)

RULE_VERSION = "MODEL_BASED_WSD_CANDIDATE_V1"
MODEL_NAME = "kanishka/GlossBERT"
MODEL_FAMILY = "GlossBERT"
MODEL_REVISION = "0cc3b83af5496e27ebcc95ef0cf37ea0a9281a7a"
CANONICAL_SOURCE = "https://huggingface.co/kanishka/GlossBERT"
LICENSE_NAME = "MIT"
POSITIVE_CLASS_INDEX = 1
MAX_TOKENS = 512
SCORE_QUANTUM = Decimal("0.000001")
MINIMUM_CONFIDENCE = Decimal("0.50")
MINIMUM_MARGIN = Decimal("0.10")
BASELINE_HIGH_READY = 4
BASELINE_SECONDARY_READY = 4
BASELINE_TOTAL_READY = 20
RESOLVED = "RESOLVED"
AMBIGUOUS = "AMBIGUOUS"
INVALID = "INVALID"
ERROR = "ERROR"
EXACT = "EXACT"
LESK_RESOLVED = "LESK_RESOLVED"
MODEL_RESOLVED = "MODEL_RESOLVED"
UNRESOLVED = "UNRESOLVED"
RESIDUAL_READY = "RESIDUAL_READY"
ROW_UNKNOWN = "UNKNOWN"
IDENTICAL = "IDENTICAL"
PROMISING = "CANDIDATE_PROMISING"
INSUFFICIENT = "CANDIDATE_INSUFFICIENT"
REJECTED = "CANDIDATE_REJECTED"
NOT_DETERMINISTIC = "NOT_DETERMINISTIC"
NOT_COMPUTABLE = "NOT_COMPUTABLE"
LICENSE_UNRESOLVED = "SOURCE_LICENSE_UNRESOLVED"
READY_CONSTITUENT = frozenset({EXACT, LESK_RESOLVED, MODEL_RESOLVED})
NEXT_PROMISING = "RESIDUAL_REPLAY_WITH_MODEL_RESOLVED_SENSES_AUTHORIZATION"
NEXT_REVISION = "MODEL_BASED_WSD_CANDIDATE_REVISION_AUTHORIZATION"
NEXT_DETERMINISM = "MODEL_BASED_WSD_DETERMINISM_REVIEW_AUTHORIZATION"
NEXT_RUNTIME = "MODEL_BASED_WSD_RUNTIME_REVIEW_AUTHORIZATION"
NEXT_LICENSE = "MODEL_BASED_WSD_LICENSE_REVIEW_AUTHORIZATION"

_RESEARCH_QUESTION = (
    "Can one pinned WordNet-native WSD model resolve enough Extended Lesk ties "
    "to make a later semantic-residual replay meaningful, without claiming accuracy?"
)
_INPUT_RULE = (
    "Sent-CLS. The context is the parent surface with the target content token in "
    "double quotes. The paired text is the matched lemma, a colon, and the first "
    "PWN 3.0 gloss clause. The parent gloss is not appended. Structural tokens "
    "locate the quoted token and are not a score."
)
_CANDIDATE_RULE = (
    "Candidates are the frozen Extended Lesk synsets for that constituent. "
    "Each gloss uses one matching lemma. Sense keys come from the local index.sense."
)
_SCORE_RULE = (
    "The score is the softmax probability of class index 1, quantized to six "
    "decimal places, half even. Class index 1 is the gloss-fits class."
)
_SELECTION_RULE = (
    "Select the unique highest score among the candidate synsets. Do not break a "
    "tie by synset order. A selected synset must be one of the candidates."
)
_CONFIDENCE_RULE = (
    "Confidence is the quantized top probability. It is recorded when the model "
    "returns scores. Overflow and execution errors leave it empty."
)
_ABSTENTION_RULE = (
    "Abstain unless the top probability is at least one half and the top-versus-second "
    "margin is at least one tenth. Do not truncate a pair longer than 512 tokens. "
    "If any pair overflows, abstain the constituent."
)
_TIE_RULE = (
    "Equal quantized top scores are AMBIGUOUS. Near ties follow the margin rule. "
    "No sense is chosen by list order."
)
_MAPPING_RULE = (
    "The checkpoint is SemCor 3.0 and WordNet 3.0. There is no cross-version map. "
    "A winner with zero or several matching sense keys is AMBIGUOUS. Do not migrate a sense by hand."
)
_CIRCULARITY_RULE = (
    "Do not choose a constituent sense because a residual embedding is near the "
    "parent gloss. This candidate does not read residual scores or residual vectors."
)
_POOL_RULE = (
    "Tier 3 sees only constituents that Extended Lesk v1 left AMBIGUOUS. "
    "It does not replace structural exact, unique lemma, or a Lesk decision that cleared its margin."
)
_GATE_RULE = (
    "Promising only when ready HIGH rows, ready SECONDARY rows, and ready rows "
    "are each strictly above the frozen lexical baseline, with no invalid output, "
    "no execution error, and identical repeats. This is coverage, not accuracy."
)
_READY_RULE = (
    "A row is projected ready only when at least two content constituents exist "
    "and every one is exact, Lesk-resolved, or model-resolved."
)
_NO_GOLD_RULE = (
    "There is no independent constituent-sense gold. Do not report accuracy, "
    "precision, recall, or F1."
)


def candidate_policy() -> dict:
    """Return the preregistered model rule. Outcome counts are not included."""
    return {
        "abstention": {
            "minimum_margin": "0.10",
            "minimum_positive_probability": "0.50",
            "on_overflow": "ABSTAIN",
            "prose": _ABSTENTION_RULE,
            "truncate": False,
        },
        "applied_to_hyperlex_at_freeze": False,
        "candidate_senses": _CANDIDATE_RULE,
        "canonical_source": CANONICAL_SOURCE,
        "circularity": _CIRCULARITY_RULE,
        "confidence": _CONFIDENCE_RULE,
        "determinism": {
            "batch_size": 1,
            "device": "cpu",
            "dtype": "float32",
            "eval_mode": True,
            "inference_mode": True,
            "inter_op_threads": 1,
            "intra_op_threads": 1,
            "manual_seed": 0,
            "mkldnn": False,
            "score_quantum": "0.000001",
            "use_deterministic_algorithms": False,
        },
        "device": "cpu",
        "dtype": "float32",
        "encoded_at_freeze": False,
        "evaluation_only": True,
        "forbidden_inputs": [
            "idiomaticity_expectation",
            "korkontzelos_manandhar_labels",
            "magpie_labels",
            "measurement_labels",
            "operator_labels",
            "residual_embeddings",
            "residual_scores",
            "semantic_yes_no",
            "unbind_bucket",
        ],
        "input_construction": _INPUT_RULE,
        "license": LICENSE_NAME,
        "max_tokens": MAX_TOKENS,
        "model_family": MODEL_FAMILY,
        "model_name": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "no_accuracy_claim": _NO_GOLD_RULE,
        "no_gold_constituent_senses": True,
        "pool": _POOL_RULE,
        "positive_class_index": POSITIVE_CLASS_INDEX,
        "pwn_mapping": {
            "cross_version_map": False,
            "manual_migration": False,
            "nonunique_sense_key": AMBIGUOUS,
            "prose": _MAPPING_RULE,
            "source_wordnet": "PWN3.0",
            "target_wordnet": "PWN3.0",
        },
        "readiness": _READY_RULE,
        "readiness_gate": {
            "baseline_high_ready": BASELINE_HIGH_READY,
            "baseline_secondary_ready": BASELINE_SECONDARY_READY,
            "baseline_total_ready": BASELINE_TOTAL_READY,
            "comparison": "strictly_greater",
            "error_count_must_be": 0,
            "invalid_output_count_must_be": 0,
            "prose": _GATE_RULE,
            "required_determinism": IDENTICAL,
        },
        "research_question": _RESEARCH_QUESTION,
        "residual_replay_authorized": False,
        "rule": RULE_VERSION,
        "runtime_integration": False,
        "scoring": _SCORE_RULE,
        "selected_source": "none",
        "selection": _SELECTION_RULE,
        "state_at_freeze": "SPEC_FROZEN",
        "tie": {
            "equal_top_scores": AMBIGUOUS,
            "order_break": False,
            "prose": _TIE_RULE,
        },
        "tokenizer_revision": MODEL_REVISION,
    }


def format_probability(value: float) -> str:
    """Quantize one positive-class probability at the frozen quantum."""
    if value != value or value in {float("inf"), float("-inf")}:
        raise RuntimeError("probability is not finite")
    number = Decimal(value).quantize(SCORE_QUANTUM, rounding=ROUND_HALF_EVEN)
    if number < 0 or number > 1:
        raise RuntimeError("probability is outside the unit interval")
    return format(number, "f")


def quoted_context(surface: str, constituent_index: int, constituent_surface: str) -> str:
    """Quote the content token Extended Lesk already indexed. Structural tokens stay bare."""
    extraction = extract_constituents(surface)
    content = extraction["content_constituents"]
    if constituent_index < 0 or constituent_index >= len(content):
        raise RuntimeError("constituent index is outside the content list")
    if content[constituent_index] != constituent_surface:
        raise RuntimeError("constituent surface does not match the frozen index")
    seen = -1
    tokens = []
    for token in extraction["surface_tokens"]:
        if lookup_key(token) in STRUCTURAL_TOKENS:
            tokens.append(token)
            continue
        seen += 1
        if seen == constituent_index:
            tokens.append('"' + token + '"')
        else:
            tokens.append(token)
    if seen != len(content) - 1:
        raise RuntimeError("quoted context did not land on the constituent")
    return " ".join(tokens)


def gloss_lemma(lemmas: list[str], constituent: str, exceptions: dict[str, set[str]]) -> str | None:
    """Pick the matching WordNet lemma. Display underscores as spaces."""
    keys = neighbor_keys(constituent, exceptions)
    matched = [lemma for lemma in lemmas if lookup_key(lemma) in keys]
    if not matched:
        return None
    own = lookup_key(constituent)
    preferred = [lemma for lemma in matched if lookup_key(lemma) == own] or matched
    chosen = sorted(preferred, key=lambda lemma: (lookup_key(lemma), lemma))[0]
    return chosen.replace("_", " ")


def candidate_gloss_text(lemma: str, gloss_clause: str) -> str:
    """Build the gloss side of a Sent-CLS pair."""
    return lemma + ": " + gloss_clause


def _decimal_score(text: str) -> Decimal:
    value = Decimal(text)
    if value != value.quantize(SCORE_QUANTUM):
        raise RuntimeError("score is not at the frozen precision")
    if value < 0 or value > 1:
        raise RuntimeError("score is outside the unit interval")
    return value


def _blank(status: str, code: str, scores: list[dict], confidence: str | None, margin: str | None) -> dict:
    return {
        "model_candidate_scores": scores,
        "model_confidence": confidence,
        "model_margin": margin,
        "model_resolution_status": status,
        "primary_evidence_code": code,
        "selected_sense_key": None,
        "selected_synset": None,
    }


def resolve_model_scores(
    candidate_synsets: list[str],
    candidate_sense_keys: dict[str, list[str]],
    positive_probabilities: dict[str, str] | None,
    *,
    overflow: bool = False,
    error: str | None = None,
) -> dict:
    """Apply the frozen abstention rule. The arguments are scores, not labels."""
    candidates = list(candidate_synsets)
    if error:
        return _blank(ERROR, "model_error", [], None, None)
    if overflow:
        return _blank(AMBIGUOUS, "context_overflow", [], None, None)
    if len(candidates) < 2 or len(set(candidates)) != len(candidates):
        return _blank(INVALID, "candidate_inventory_invalid", [], None, None)
    if positive_probabilities is None or set(positive_probabilities) != set(candidates):
        return _blank(INVALID, "invalid_model_output", [], None, None)
    scored = {synset_id: _decimal_score(positive_probabilities[synset_id]) for synset_id in candidates}
    rows = []
    for synset_id in sorted(scored):
        keys = list(candidate_sense_keys.get(synset_id, []))
        rows.append(
            {
                "positive_probability": format(scored[synset_id], "f"),
                "sense_keys": sorted(keys),
                "synset": synset_id,
            }
        )
    ordered = sorted(scored.values(), reverse=True)
    top = ordered[0]
    second = ordered[1]
    margin = top - second
    confidence = format(top, "f")
    margin_text = format(margin, "f")
    winners = [synset_id for synset_id, score in scored.items() if score == top]
    if len(winners) != 1:
        return _blank(AMBIGUOUS, "model_score_tie", rows, confidence, margin_text)
    if top < MINIMUM_CONFIDENCE or margin < MINIMUM_MARGIN:
        return _blank(AMBIGUOUS, "model_abstention", rows, confidence, margin_text)
    selected = winners[0]
    if selected not in candidates:
        return _blank(INVALID, "invalid_model_output", rows, confidence, margin_text)
    keys = sorted(candidate_sense_keys.get(selected, []))
    if len(keys) != 1:
        return _blank(AMBIGUOUS, "pwn30_sense_key_not_unique", rows, confidence, margin_text)
    return {
        "model_candidate_scores": rows,
        "model_confidence": confidence,
        "model_margin": margin_text,
        "model_resolution_status": RESOLVED,
        "primary_evidence_code": "model_margin",
        "selected_sense_key": keys[0],
        "selected_synset": selected,
    }


def overlay_status(frozen_status: str, frozen_method: str, model_status: str | None) -> str:
    """Combine one frozen tier with an optional tier-3 status. Tier 3 cannot replace a decision."""
    if frozen_status == EXACT:
        if model_status is not None:
            raise RuntimeError("tier 3 overrode an exact constituent")
        return EXACT
    if frozen_status == RESOLVED:
        if model_status is not None:
            raise RuntimeError("tier 3 overrode a resolved constituent")
        return LESK_RESOLVED
    if frozen_status == UNRESOLVED:
        if model_status is not None:
            raise RuntimeError("tier 3 overrode an unresolved constituent")
        return UNRESOLVED
    if frozen_status != AMBIGUOUS:
        raise RuntimeError("unknown frozen constituent status")
    if frozen_method != "EXTENDED_LESK_V1":
        if model_status is not None:
            raise RuntimeError("tier 3 overrode a non-lesk constituent")
        return AMBIGUOUS
    if model_status is None:
        raise RuntimeError("ambiguous lesk constituent has no tier 3 result")
    if model_status == RESOLVED:
        return MODEL_RESOLVED
    if model_status in {AMBIGUOUS, INVALID, ERROR}:
        return model_status
    raise RuntimeError("unknown model status")


def project_row_status(statuses: list[str]) -> str:
    """Project one row. Fewer than two content constituents stays unknown."""
    if len(statuses) < 2 or any(status not in READY_CONSTITUENT for status in statuses):
        return ROW_UNKNOWN
    return RESIDUAL_READY


def coverage_gate(
    *,
    high_ready: int,
    secondary_ready: int,
    total_ready: int,
    invalid_output_count: int,
    error_count: int,
    determinism: str,
) -> dict:
    """Apply the preregistered coverage gate. The thresholds are not fit to this run."""
    counts = (high_ready, secondary_ready, total_ready, invalid_output_count, error_count)
    if min(counts) < 0:
        raise RuntimeError("negative coverage count")
    if determinism != IDENTICAL:
        status = NOT_DETERMINISTIC
        transition = NEXT_DETERMINISM
    elif invalid_output_count > 0 or error_count > 0:
        status = REJECTED
        transition = NEXT_REVISION
    elif (
        high_ready > BASELINE_HIGH_READY
        and secondary_ready > BASELINE_SECONDARY_READY
        and total_ready > BASELINE_TOTAL_READY
        and invalid_output_count == 0
        and error_count == 0
        and determinism == IDENTICAL
    ):
        status = PROMISING
        transition = NEXT_PROMISING
    else:
        status = INSUFFICIENT
        transition = NEXT_REVISION
    return {
        "candidate_status": status,
        "next_legal_transition": transition,
        "next_transition_authorized": False,
        "state": "CANDIDATE_EVALUATED",
    }


def _confidence_bin(value: Decimal) -> str:
    if value < Decimal("0.50"):
        return "below_0.50"
    if value < Decimal("0.60"):
        return "0.50_to_0.60"
    if value < Decimal("0.70"):
        return "0.60_to_0.70"
    if value < Decimal("0.80"):
        return "0.70_to_0.80"
    if value < Decimal("0.90"):
        return "0.80_to_0.90"
    return "0.90_to_1.00"


def _margin_bin(value: Decimal) -> str:
    if value == 0:
        return "exact_tie"
    if value < Decimal("0.10"):
        return "below_0.10"
    if value < Decimal("0.25"):
        return "0.10_to_0.25"
    if value < Decimal("0.50"):
        return "0.25_to_0.50"
    return "0.50_or_more"


def summarize_confidence(rows: list[dict]) -> dict:
    """Summarize tier-3 scores. Operator buckets are not an argument."""
    confidence_bins = {
        "0.50_to_0.60": 0,
        "0.60_to_0.70": 0,
        "0.70_to_0.80": 0,
        "0.80_to_0.90": 0,
        "0.90_to_1.00": 0,
        "below_0.50": 0,
    }
    margin_bins = {
        "0.10_to_0.25": 0,
        "0.25_to_0.50": 0,
        "0.50_or_more": 0,
        "below_0.10": 0,
        "exact_tie": 0,
    }
    by_count: dict[str, dict[str, int]] = {}
    resolved = 0
    abstained = 0
    invalid = 0
    errors = 0
    for row in rows:
        status = row["model_resolution_status"]
        if status == RESOLVED:
            resolved += 1
        elif status == AMBIGUOUS:
            abstained += 1
        elif status == INVALID:
            invalid += 1
        elif status == ERROR:
            errors += 1
        else:
            raise RuntimeError("unknown model status in the confidence summary")
        key = str(len(row["candidate_pwn30_synsets"]))
        bucket = by_count.setdefault(
            key,
            {"abstained": 0, "attempts": 0, "error": 0, "invalid": 0, "resolved": 0},
        )
        bucket["attempts"] += 1
        if status == RESOLVED:
            bucket["resolved"] += 1
        elif status == AMBIGUOUS:
            bucket["abstained"] += 1
        elif status == INVALID:
            bucket["invalid"] += 1
        else:
            bucket["error"] += 1
        if row["model_confidence"] is not None:
            confidence_bins[_confidence_bin(Decimal(row["model_confidence"]))] += 1
        if row["model_margin"] is not None:
            margin_bins[_margin_bin(Decimal(row["model_margin"]))] += 1
    return {
        "abstained": abstained,
        "by_candidate_count": dict(sorted(by_count.items(), key=lambda item: int(item[0]))),
        "confidence_bins": confidence_bins,
        "error": errors,
        "invalid": invalid,
        "margin_bins": margin_bins,
        "resolved": resolved,
    }
