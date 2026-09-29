"""Inspectable semantic-evidence function for the successor lane.

The function is a contract, not an evaluation. It does not load a model, run
word-sense disambiguation, read a measurement surface, or authorize training.
"""

from __future__ import annotations

import hashlib
import math
from decimal import Decimal, ROUND_HALF_EVEN

RULE = "RUNE.SEMANTIC_COMPOSITIONALITY_EVIDENCE.v2"
STATE = "SEMANTIC_EVIDENCE_V2_SPEC_DRAFTED"
MEASUREMENT_DISPOSITION = "RETAIN_FOR_V2_ONLY"
TRAINING_AUTHORIZED = False
BASELINE_COMPARISON = "BASELINE_COMPARISON_REQUIRED"

PARENT_TEMPLATE = "surface: {surface}\npart_of_speech: {pos}\ndefinition: {gloss}\n"
CONSTITUENT_TEMPLATE = "surface: {surface}\ndefinition: {gloss}\n"
QUANTUM = Decimal("0.0000000001")

FEATURE_NAMES = (
    "whole_vs_constituent_mean_cosine",
    "whole_vs_constituent_mean_residual",
    "whole_vs_each_constituent_min_similarity",
    "whole_vs_each_constituent_max_similarity",
    "whole_vs_each_constituent_mean_similarity",
    "whole_vs_each_constituent_similarity_variance",
    "constituent_pair_mean_similarity",
    "constituent_pair_min_similarity",
    "constituent_pair_variance",
    "whole_gloss_vs_composed_gloss_similarity",
    "whole_lemma_vs_composed_constituent_similarity",
    "constituent_count",
    "token_count",
)

STRUCTURAL_CONTROLS = frozenset({"constituent_count", "token_count"})
REPRESENTATION_FAMILIES = (
    "minilm_baseline",
    "modernbert_gloss_pooling",
    "sts_semantic_encoder",
)
MAX_REPRESENTATION_FAMILIES = 3
BASELINE_FAMILY = "minilm_baseline"
BASELINE_COMPOSITION = "normalized_mean_v1"
COMPOSITION_FUNCTIONS = (
    "normalized_mean_v1",
    "weighted_mean_by_constituent_token_span",
    "pairwise_relation_summary",
)
OUTPUT_LABELS = ("YES", "UNKNOWN")


def template_sha256() -> str:
    payload = PARENT_TEMPLATE + CONSTITUENT_TEMPLATE
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parent_text(surface: str, pos: str, gloss: str) -> str:
    return PARENT_TEMPLATE.format(surface=surface, pos=pos, gloss=gloss)


def constituent_text(surface: str, gloss: str) -> str:
    return CONSTITUENT_TEMPLATE.format(surface=surface, gloss=gloss)


def quantize(value: float) -> str:
    decimal = Decimal(str(value)).quantize(QUANTUM, rounding=ROUND_HALF_EVEN)
    return f"{decimal:.10f}"


def _dot(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("vectors must be the same non-empty length")
    return sum(a * b for a, b in zip(left, right))


def _norm(vector: tuple[float, ...]) -> float:
    return math.sqrt(_dot(vector, vector))


def cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    denominator = _norm(left) * _norm(right)
    if denominator == 0:
        raise ValueError("cosine is undefined for a zero vector")
    return _dot(left, right) / denominator


def normalized_mean(vectors: tuple[tuple[float, ...], ...]) -> tuple[float, ...]:
    if len(vectors) < 2:
        raise ValueError("normalized mean requires at least two constituents")
    width = len(vectors[0])
    if any(len(vector) != width for vector in vectors):
        raise ValueError("constituent vectors must share a width")
    mean = tuple(sum(vector[index] for vector in vectors) / len(vectors) for index in range(width))
    scale = _norm(mean)
    if scale == 0:
        raise ValueError("normalized mean is undefined for a zero mean")
    return tuple(value / scale for value in mean)


def weighted_mean(vectors: tuple[tuple[float, ...], ...], weights: tuple[int, ...]) -> tuple[float, ...]:
    if len(vectors) != len(weights) or len(vectors) < 2:
        raise ValueError("weights must match at least two constituents")
    if any(weight <= 0 for weight in weights):
        raise ValueError("token-span weights must be positive")
    width = len(vectors[0])
    total = sum(weights)
    mean = tuple(
        sum(vector[index] * weight for vector, weight in zip(vectors, weights)) / total
        for index in range(width)
    )
    scale = _norm(mean)
    if scale == 0:
        raise ValueError("weighted mean is undefined for a zero mean")
    return tuple(value / scale for value in mean)


def _population_variance(values: tuple[float, ...]) -> float:
    if not values:
        raise ValueError("variance requires values")
    center = sum(values) / len(values)
    return sum((value - center) ** 2 for value in values) / len(values)


def pairwise_cosines(vectors: tuple[tuple[float, ...], ...]) -> tuple[float, ...]:
    if len(vectors) < 2:
        raise ValueError("pairwise summary requires at least two constituents")
    return tuple(
        cosine(vectors[left], vectors[right])
        for left in range(len(vectors))
        for right in range(left + 1, len(vectors))
    )


def baseline_residual(whole: tuple[float, ...], constituents: tuple[tuple[float, ...], ...]) -> str:
    """Historical scalar: 1 - cosine(whole, normalized mean of constituents)."""
    return quantize(1 - cosine(whole, normalized_mean(constituents)))


def evidence_record(
    *,
    whole: tuple[float, ...] | None,
    constituents: tuple[tuple[float, ...], ...] | None,
    gloss_whole: tuple[float, ...] | None,
    gloss_composed: tuple[float, ...] | None,
    lemma_whole: tuple[float, ...] | None,
    lemma_composed: tuple[float, ...] | None,
    token_count: int,
    resolved: bool,
) -> dict:
    """Return UNKNOWN when constituent structure is unresolved or incomplete."""
    if (
        not resolved
        or whole is None
        or constituents is None
        or len(constituents) < 2
        or gloss_whole is None
        or gloss_composed is None
        or lemma_whole is None
        or lemma_composed is None
        or token_count < 1
    ):
        return {
            "evidence_status": "UNKNOWN",
            "features": None,
            "output": "UNKNOWN",
            "rule": RULE,
        }
    composed = normalized_mean(constituents)
    to_each = tuple(cosine(whole, vector) for vector in constituents)
    pairs = pairwise_cosines(constituents)
    values = {
        "whole_vs_constituent_mean_cosine": cosine(whole, composed),
        "whole_vs_constituent_mean_residual": 1 - cosine(whole, composed),
        "whole_vs_each_constituent_min_similarity": min(to_each),
        "whole_vs_each_constituent_max_similarity": max(to_each),
        "whole_vs_each_constituent_mean_similarity": sum(to_each) / len(to_each),
        "whole_vs_each_constituent_similarity_variance": _population_variance(to_each),
        "constituent_pair_mean_similarity": sum(pairs) / len(pairs),
        "constituent_pair_min_similarity": min(pairs),
        "constituent_pair_variance": _population_variance(pairs),
        "whole_gloss_vs_composed_gloss_similarity": cosine(gloss_whole, gloss_composed),
        "whole_lemma_vs_composed_constituent_similarity": cosine(lemma_whole, lemma_composed),
    }
    features = [
        {
            "control": name in STRUCTURAL_CONTROLS,
            "name": name,
            "value": values[name] if name in STRUCTURAL_CONTROLS else quantize(values[name]),
        }
        for name in FEATURE_NAMES
        if name not in STRUCTURAL_CONTROLS
    ]
    features.extend(
        [
            {"control": True, "name": "constituent_count", "value": len(constituents)},
            {"control": True, "name": "token_count", "value": token_count},
        ]
    )
    return {
        "evidence_status": "READY",
        "features": features,
        "output": "UNKNOWN",
        "rule": RULE,
    }
