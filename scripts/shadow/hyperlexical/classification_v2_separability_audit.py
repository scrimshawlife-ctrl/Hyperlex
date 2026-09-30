"""Read-only active-family ontology/data separability audit.

Determines whether the 19 active families are distinguishable from existing
training definition text. Does not train, does not score the evaluation
reserve, and does not move BEST.
"""

from __future__ import annotations

import math
import re
from typing import Any, Mapping, Sequence

from .classification_v2 import (
    ACTIVE_FAMILY_VOCABULARY,
    ClassificationContractError,
    EXACT_COPY_FAMILIES,
    canonical_json,
    sha256_text,
)
from .classification_v2_boundaries import (
    BLOCKED_IDENTITY_STATES,
    BLOCKED_SURFACES,
    CLASSIFICATION_TASKS,
    COLLISION_COSINE,
    boundary_training_sources,
)
from .classification_v2_prototype import (
    PROTOTYPE_WEIGHT,
    _f32_round,
    _markup_text,
    _prose,
    _unit,
    weighted_mean,
)


def _scalar(value: float | None) -> float | None:
    if value is None:
        return None
    return _f32_round((float(value),))[0]
from .classification_v2_surface import SURFACE_PROSE, surface_form
from .holdout_guard import normalized_text_sha256

AUDIT_SCHEMA = "hyperlex.classification.v2.active_family_separability_audit.v1"
AUDIT_RULE = "HYPERLEX_ACTIVE_FAMILY_SEPARABILITY_AUDIT_V1"
SOURCE_RULE = "training_definition_text_classify_split_only"
PROBE_SURFACE = "train_fit_val_eval_definitions_only"
COLLAPSE_CLUSTER: tuple[str, ...] = (
    "internet-slang",
    "memetic",
    "social-status",
    "relationship-dating",
    "approval-disapproval",
    "conflict-aggression",
    "technology-ai",
    "workplace-career",
    "sports-competition",
    "music-entertainment",
    "fashion-aesthetic",
    "regional-cultural",
    "spiritual-mystic",
    "identity-affiliation",
    "politics-civic",
)
SPARSE_FOCUS: tuple[str, ...] = ("betting-sharp", "internet-slang", "memetic")
FAMILY_STATUSES = (
    "SEPARABLE",
    "UNDER_SUPPORTED",
    "OVERLAPPING",
    "NOISY",
    "UNRESOLVED",
)
COLLISION_FLAGS = (
    "DATA_TOO_SPARSE",
    "DEFINITION_TOO_GENERIC",
    "ONTOLOGY_OVERLAP",
    "LABEL_NOISE",
    "REPRESENTATION_COLLAPSE",
    "SEPARABLE",
)
AUDIT_DECISIONS = (
    "CURRENT_ONTOLOGY_DATA_SEPARABLE",
    "DATA_EXPANSION_REQUIRED",
    "BOUNDARY_REFINEMENT_REQUIRED",
    "ONTOLOGY_REFACTOR_REQUIRED",
    "MIXED_REMEDIATION_REQUIRED",
)

SPARSE_SUPPORT_MAX = 2
PROBE_MIN_TRAIN = 2
PROBE_MIN_VAL = 1
HIGH_CROSS_SIM = 0.85
HIGH_NN_CONFUSION = 0.40
LOW_CENTROID_DISTANCE = 0.20
SEPARABLE_PROBE_F1 = 0.80
GENERIC_SHARED_RATIO = 0.45
LEXICAL_TOP_K = 8
PHRASE_TOP_K = 6
NEAREST_COMPETITORS = 3
LOG_ODDS_PRIOR = 0.01
LOG_ODDS_ENRICHED = 1.0
AMBIGUOUS_MARGIN = 0.02
BOUNDARY_SHA = "0ca6f34ce1abf68388e443371672ca36e16028079a175b6775e1968900e1c52f"
SEPARATION_SHA = "ab698d342d2d276f81d4baf3fed609bb6f8bf88cd6810bb1d1998c5e409f63c3"
REPAIR_PRIMARY_SHA = "449bf3b303c95bc5d6b7d87173d50315616556c1379057414b970f3e5f0b18cf"
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"

_TOKEN = re.compile(r"[a-z]{3,}")
_STOPWORDS = frozenset(
    {
        "about",
        "above",
        "after",
        "again",
        "against",
        "all",
        "also",
        "among",
        "and",
        "another",
        "any",
        "are",
        "around",
        "because",
        "been",
        "before",
        "being",
        "below",
        "between",
        "both",
        "but",
        "can",
        "could",
        "does",
        "doing",
        "down",
        "during",
        "each",
        "else",
        "especially",
        "every",
        "from",
        "further",
        "generally",
        "have",
        "having",
        "here",
        "hers",
        "herself",
        "himself",
        "into",
        "itself",
        "just",
        "more",
        "most",
        "much",
        "must",
        "none",
        "only",
        "onto",
        "other",
        "others",
        "otherwise",
        "over",
        "same",
        "shall",
        "should",
        "some",
        "someone",
        "something",
        "such",
        "than",
        "that",
        "their",
        "theirs",
        "them",
        "themselves",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "under",
        "until",
        "used",
        "using",
        "usually",
        "very",
        "what",
        "when",
        "where",
        "which",
        "while",
        "whom",
        "whose",
        "will",
        "with",
        "within",
        "without",
        "would",
        "your",
        "the",
        "for",
        "not",
        "one",
        "two",
        "who",
        "how",
        "was",
        "were",
        "his",
        "her",
        "its",
        "our",
        "out",
        "own",
        "may",
        "person",
        "people",
        "term",
        "word",
        "slang",
        "informal",
        "chiefly",
        "referring",
        "denoting",
        "meaning",
    }
)


def audit_contract() -> dict[str, Any]:
    return {
        "best_sha256": BEST_SHA,
        "boundary_sha256": BOUNDARY_SHA,
        "collapse_cluster": list(COLLAPSE_CLUSTER),
        "encoder_updated": False,
        "jev": "OFF",
        "moves_best": False,
        "probe_surface": PROBE_SURFACE,
        "repair_primary_sha256": REPAIR_PRIMARY_SHA,
        "reserve_scored": False,
        "rule": AUDIT_RULE,
        "schema": AUDIT_SCHEMA,
        "separation_sha256": SEPARATION_SHA,
        "source_rule": SOURCE_RULE,
        "sparse_focus": list(SPARSE_FOCUS),
        "train": False,
    }


def _blocked_row(row: Mapping[str, Any], states: Mapping[str, str]) -> str | None:
    digest = normalized_text_sha256(str(row.get("text") or ""))
    state = states.get(digest)
    if state in BLOCKED_IDENTITY_STATES:
        return str(state)
    if row.get("evaluation_reserve") or row.get("held_out"):
        return "held_out_or_reserve_flag"
    surface = str(row.get("surface") or "")
    if surface in BLOCKED_SURFACES:
        return surface
    if row.get("split") == "test":
        return "test"
    return None


def definition_sources(
    rows: Sequence[Mapping[str, Any]],
    identity_state: Mapping[str, str] | None = None,
    *,
    split: str,
) -> dict[str, Any]:
    """Definition prose for one split. Train uses the sealed boundary filter."""
    if split == "train":
        return boundary_training_sources(rows, identity_state)
    if split != "val":
        raise ClassificationContractError("SEPARABILITY_AUDIT_UNAVAILABLE", "split")
    states = identity_state or {}
    grouped: dict[str, dict[str, Mapping[str, Any]]] = {
        family: {} for family in ACTIVE_FAMILY_VOCABULARY
    }
    excluded: list[dict[str, str]] = []
    for row in rows:
        if row.get("split") != "val":
            continue
        lineage = str(row.get("lineage") or "")
        if lineage not in grouped or row.get("class") not in PROTOTYPE_WEIGHT:
            continue
        if str(row.get("task") or "") not in CLASSIFICATION_TASKS:
            continue
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        if lineage in EXACT_COPY_FAMILIES:
            if _markup_text(text) or surface_form(text) != SURFACE_PROSE:
                continue
        else:
            prose = _prose(row)
            if not prose or text != prose:
                continue
        digest = normalized_text_sha256(text)
        reason = _blocked_row(row, states)
        if reason is not None:
            excluded.append({"identity": digest, "reason": reason})
            continue
        current = grouped[lineage].get(digest)
        if current is not None and current.get("class") == "OBSERVED":
            continue
        if current is not None and row.get("class") != "OBSERVED":
            continue
        grouped[lineage][digest] = row
    sources: dict[str, dict[str, Any]] = {}
    for family in ACTIVE_FAMILY_VOCABULARY:
        items = sorted(grouped[family].items(), key=lambda item: item[0])
        if not items:
            continue
        sources[family] = {
            "identities": [digest for digest, _row in items],
            "inferred": sum(1 for _digest, row in items if row.get("class") == "INFERRED"),
            "observed": sum(1 for _digest, row in items if row.get("class") == "OBSERVED"),
            "rows": [row for _digest, row in items],
            "weights": [PROTOTYPE_WEIGHT[str(row.get("class"))] for _digest, row in items],
        }
    return {
        "excluded_identities": sorted({item["identity"] for item in excluded}),
        "exclusions": excluded,
        "sources": sources,
    }


def _tokenize(text: str) -> list[str]:
    return [
        token
        for token in _TOKEN.findall(str(text).lower())
        if token not in _STOPWORDS and len(token) >= 3
    ]


def token_document_counts(texts: Sequence[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for text in texts:
        seen: set[str] = set()
        for token in _tokenize(text):
            if token in seen:
                continue
            seen.add(token)
            counts[token] = counts.get(token, 0) + 1
    return counts


def phrase_counts(texts: Sequence[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for text in texts:
        tokens = _tokenize(text)
        seen: set[str] = set()
        for index in range(len(tokens) - 1):
            phrase = f"{tokens[index]} {tokens[index + 1]}"
            if phrase in seen:
                continue
            seen.add(phrase)
            counts[phrase] = counts.get(phrase, 0) + 1
    return counts


def log_odds_scores(
    left_counts: Mapping[str, int],
    right_counts: Mapping[str, int],
    *,
    prior: float = LOG_ODDS_PRIOR,
) -> dict[str, float]:
    """Monroe et al. informative Dirichlet prior log-odds (deterministic)."""
    tokens = sorted(set(left_counts) | set(right_counts))
    left_n = sum(left_counts.values())
    right_n = sum(right_counts.values())
    scores: dict[str, float] = {}
    for token in tokens:
        left = float(left_counts.get(token, 0))
        right = float(right_counts.get(token, 0))
        left_odds = (left + prior) / (left_n + prior * max(len(tokens), 1) - left - prior)
        right_odds = (right + prior) / (right_n + prior * max(len(tokens), 1) - right - prior)
        scores[token] = math.log(left_odds) - math.log(right_odds)
    return scores


def lexical_pair_report(left_texts: Sequence[str], right_texts: Sequence[str]) -> dict[str, Any]:
    left_counts = token_document_counts(left_texts)
    right_counts = token_document_counts(right_texts)
    scores = log_odds_scores(left_counts, right_counts)
    enrich_a = sorted(
        (token for token, score in scores.items() if score >= LOG_ODDS_ENRICHED),
        key=lambda token: (-scores[token], token),
    )[:LEXICAL_TOP_K]
    enrich_b = sorted(
        (token for token, score in scores.items() if score <= -LOG_ODDS_ENRICHED),
        key=lambda token: (scores[token], token),
    )[:LEXICAL_TOP_K]
    shared = sorted(
        set(left_counts) & set(right_counts),
        key=lambda token: (-(left_counts[token] + right_counts[token]), token),
    )
    union = set(left_counts) | set(right_counts)
    shared_ratio = (len(shared) / len(union)) if union else 1.0
    left_phrases = phrase_counts(left_texts)
    right_phrases = phrase_counts(right_texts)
    distinctive_a = [
        phrase
        for phrase, _count in sorted(left_phrases.items(), key=lambda item: (-item[1], item[0]))
        if phrase not in right_phrases
    ][:PHRASE_TOP_K]
    distinctive_b = [
        phrase
        for phrase, _count in sorted(right_phrases.items(), key=lambda item: (-item[1], item[0]))
        if phrase not in left_phrases
    ][:PHRASE_TOP_K]
    return {
        "distinctive_phrases_a": distinctive_a,
        "distinctive_phrases_b": distinctive_b,
        "shared_high_frequency_tokens": shared[:LEXICAL_TOP_K],
        "shared_token_ratio": _scalar(shared_ratio),
        "tokens_enriched_in_a": enrich_a,
        "tokens_enriched_in_b": enrich_b,
    }


def _mean_pairwise(vectors: Sequence[Sequence[float]]) -> float | None:
    if len(vectors) < 2:
        return None
    total = 0.0
    count = 0
    for left in range(len(vectors)):
        for right in range(left + 1, len(vectors)):
            total += sum(a * b for a, b in zip(_unit(vectors[left]), _unit(vectors[right])))
            count += 1
    return _scalar(total / count)


def _cross_mean(left: Sequence[Sequence[float]], right: Sequence[Sequence[float]]) -> float | None:
    if not left or not right:
        return None
    total = 0.0
    count = 0
    left_u = [_unit(vector) for vector in left]
    right_u = [_unit(vector) for vector in right]
    for a in left_u:
        for b in right_u:
            total += sum(x * y for x, y in zip(a, b))
            count += 1
    return _scalar(total / count)


def _centroid(vectors: Sequence[Sequence[float]], weights: Sequence[float] | None = None) -> list[float]:
    if not vectors:
        raise ClassificationContractError("SEPARABILITY_AUDIT_UNAVAILABLE", "centroid")
    if weights is None:
        weights = [1.0 for _vector in vectors]
    return weighted_mean(list(vectors), list(weights))


def nearest_neighbor_confusion(
    left: Sequence[Sequence[float]],
    right: Sequence[Sequence[float]],
) -> dict[str, Any]:
    if not left or not right:
        return {"confused": 0, "rate": None, "support": 0}
    left_u = [_unit(vector) for vector in left]
    right_u = [_unit(vector) for vector in right]
    confused = 0
    for index, query in enumerate(left_u):
        best_same = -2.0
        for other_index, other in enumerate(left_u):
            if other_index == index:
                continue
            best_same = max(best_same, sum(a * b for a, b in zip(query, other)))
        best_cross = max(sum(a * b for a, b in zip(query, other)) for other in right_u)
        if len(left_u) == 1:
            if best_cross >= COLLISION_COSINE:
                confused += 1
            continue
        if best_cross > best_same:
            confused += 1
    rate = confused / len(left_u)
    return {"confused": confused, "rate": _scalar(rate), "support": len(left_u)}


def anchor_collision_rate(
    left_anchors: Sequence[Sequence[float]],
    right_anchors: Sequence[Sequence[float]],
    *,
    threshold: float = COLLISION_COSINE,
) -> dict[str, Any]:
    if not left_anchors or not right_anchors:
        return {"colliding_pairs": 0, "max_cosine": None, "rate": None, "support_pairs": 0}
    colliding = 0
    support = 0
    peak = -2.0
    for left in left_anchors:
        left_u = _unit(left)
        for right in right_anchors:
            cosine = sum(a * b for a, b in zip(left_u, _unit(right)))
            peak = max(peak, cosine)
            support += 1
            if cosine >= threshold:
                colliding += 1
    return {
        "colliding_pairs": colliding,
        "max_cosine": _scalar(peak),
        "rate": _scalar(colliding / support),
        "support_pairs": support,
    }


def pairwise_probe(
    train_left: Sequence[Sequence[float]],
    train_right: Sequence[Sequence[float]],
    val_left: Sequence[Sequence[float]],
    val_right: Sequence[Sequence[float]],
    *,
    train_left_weights: Sequence[float] | None = None,
    train_right_weights: Sequence[float] | None = None,
) -> dict[str, Any]:
    """Deterministic LDA-style probe. Encoder weights are not updated."""
    if (
        len(train_left) < PROBE_MIN_TRAIN
        or len(train_right) < PROBE_MIN_TRAIN
        or len(val_left) < PROBE_MIN_VAL
        or len(val_right) < PROBE_MIN_VAL
    ):
        return {
            "accuracy": None,
            "f1": None,
            "n_train": len(train_left) + len(train_right),
            "n_val": len(val_left) + len(val_right),
            "status": "NOT_COMPUTABLE",
        }
    mean_left = _centroid(train_left, train_left_weights)
    mean_right = _centroid(train_right, train_right_weights)
    direction = _unit([a - b for a, b in zip(mean_left, mean_right)])
    left_proj = sum(a * b for a, b in zip(mean_left, direction))
    right_proj = sum(a * b for a, b in zip(mean_right, direction))
    threshold = 0.5 * (left_proj + right_proj)
    golds: list[str] = []
    preds: list[str] = []
    for vector in val_left:
        score = sum(a * b for a, b in zip(_unit(vector), direction))
        preds.append("A" if score >= threshold else "B")
        golds.append("A")
    for vector in val_right:
        score = sum(a * b for a, b in zip(_unit(vector), direction))
        preds.append("A" if score >= threshold else "B")
        golds.append("B")
    correct = sum(1 for gold, pred in zip(golds, preds) if gold == pred)
    accuracy = correct / len(golds)
    f1s: list[float] = []
    for label in ("A", "B"):
        gold = sum(1 for item in golds if item == label)
        predicted = sum(1 for item in preds if item == label)
        hit = sum(1 for g, p in zip(golds, preds) if g == label and p == label)
        if gold == 0 and predicted == 0:
            continue
        precision = hit / predicted if predicted else 0.0
        recall = hit / gold if gold else 0.0
        f1s.append(0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall))
    return {
        "accuracy": _scalar(accuracy),
        "f1": _scalar(sum(f1s) / len(f1s)) if f1s else None,
        "n_train": len(train_left) + len(train_right),
        "n_val": len(val_left) + len(val_right),
        "status": "OK",
        "threshold": _scalar(threshold),
    }


def embedding_pair_report(
    left_vectors: Sequence[Sequence[float]],
    right_vectors: Sequence[Sequence[float]],
    left_anchors: Sequence[Sequence[float]],
    right_anchors: Sequence[Sequence[float]],
    *,
    left_weights: Sequence[float] | None = None,
    right_weights: Sequence[float] | None = None,
) -> dict[str, Any]:
    within_a = _mean_pairwise(left_vectors)
    within_b = _mean_pairwise(right_vectors)
    cross = _cross_mean(left_vectors, right_vectors)
    centroid_a = _centroid(left_vectors, left_weights) if left_vectors else None
    centroid_b = _centroid(right_vectors, right_weights) if right_vectors else None
    if centroid_a is None or centroid_b is None:
        centroid_distance = None
        centroid_cosine = None
    else:
        centroid_cosine = sum(a * b for a, b in zip(_unit(centroid_a), _unit(centroid_b)))
        centroid_distance = _scalar(1.0 - centroid_cosine)
        centroid_cosine = _scalar(centroid_cosine)
    nn_a = nearest_neighbor_confusion(left_vectors, right_vectors)
    nn_b = nearest_neighbor_confusion(right_vectors, left_vectors)
    collision = anchor_collision_rate(left_anchors, right_anchors)
    return {
        "anchor_collision_max_cosine": collision["max_cosine"],
        "anchor_collision_rate": collision["rate"],
        "centroid_cosine": centroid_cosine,
        "centroid_distance": centroid_distance,
        "cross_family_similarity": cross,
        "nearest_neighbor_confusion_a": nn_a["rate"],
        "nearest_neighbor_confusion_b": nn_b["rate"],
        "within_family_similarity_a": within_a,
        "within_family_similarity_b": within_b,
    }


def classify_pair_flags(
    *,
    n_a: int,
    n_b: int,
    lexical: Mapping[str, Any],
    embedding: Mapping[str, Any],
    probe: Mapping[str, Any],
) -> list[str]:
    flags: list[str] = []
    sparse = n_a <= SPARSE_SUPPORT_MAX or n_b <= SPARSE_SUPPORT_MAX
    if sparse:
        flags.append("DATA_TOO_SPARSE")
    shared_ratio = float(lexical.get("shared_token_ratio") or 0.0)
    enrich_a = list(lexical.get("tokens_enriched_in_a") or [])
    enrich_b = list(lexical.get("tokens_enriched_in_b") or [])
    generic = shared_ratio >= GENERIC_SHARED_RATIO or (len(enrich_a) < 2 and len(enrich_b) < 2)
    if generic:
        flags.append("DEFINITION_TOO_GENERIC")
    cross = embedding.get("cross_family_similarity")
    centroid_distance = embedding.get("centroid_distance")
    nn = max(
        float(embedding.get("nearest_neighbor_confusion_a") or 0.0),
        float(embedding.get("nearest_neighbor_confusion_b") or 0.0),
    )
    collision = float(embedding.get("anchor_collision_rate") or 0.0)
    probe_f1 = probe.get("f1")
    probe_ok = probe.get("status") == "OK" and probe_f1 is not None and float(probe_f1) >= SEPARABLE_PROBE_F1
    lexical_ok = len(enrich_a) >= 2 and len(enrich_b) >= 2 and shared_ratio < GENERIC_SHARED_RATIO
    embedding_collapsed = (
        (cross is not None and float(cross) >= HIGH_CROSS_SIM)
        or (centroid_distance is not None and float(centroid_distance) <= LOW_CENTROID_DISTANCE)
        or nn >= HIGH_NN_CONFUSION
        or collision >= 0.5
    )
    if lexical_ok and embedding_collapsed:
        flags.append("REPRESENTATION_COLLAPSE")
    if (not sparse) and generic and embedding_collapsed and not lexical_ok:
        flags.append("ONTOLOGY_OVERLAP")
    if (not sparse) and lexical_ok and embedding_collapsed and probe.get("status") == "OK" and not probe_ok:
        if "ONTOLOGY_OVERLAP" not in flags:
            flags.append("ONTOLOGY_OVERLAP")
    if probe.get("status") == "OK" and probe_f1 is not None and float(probe_f1) < 0.55 and not sparse:
        flags.append("LABEL_NOISE")
    if probe_ok and not embedding_collapsed and not sparse and not generic:
        return ["SEPARABLE"]
    if probe_ok and not sparse and lexical_ok and not embedding_collapsed:
        return ["SEPARABLE"]
    cleaned = [flag for flag in flags if flag in COLLISION_FLAGS]
    if cleaned:
        return cleaned
    if sparse:
        return ["DATA_TOO_SPARSE"]
    return ["DEFINITION_TOO_GENERIC"]


def family_status_for(
    family: str,
    *,
    n_train: int,
    pair_flags: Sequence[Sequence[str]],
    noisy_rows: int,
) -> str:
    if n_train <= SPARSE_SUPPORT_MAX:
        return "UNDER_SUPPORTED"
    flat = [flag for flags in pair_flags for flag in flags]
    overlap_hits = sum(1 for flag in flat if flag == "ONTOLOGY_OVERLAP")
    generic_hits = sum(1 for flag in flat if flag == "DEFINITION_TOO_GENERIC")
    separable_hits = sum(1 for flag in flat if flag == "SEPARABLE")
    collapse_hits = sum(1 for flag in flat if flag == "REPRESENTATION_COLLAPSE")
    if noisy_rows >= max(1, n_train // 3):
        return "NOISY"
    if overlap_hits >= max(2, len(pair_flags) // 4):
        return "OVERLAPPING"
    if separable_hits >= max(1, len(pair_flags) // 2) and overlap_hits == 0 and collapse_hits == 0:
        return "SEPARABLE"
    if generic_hits >= max(2, len(pair_flags) // 3) and family in COLLAPSE_CLUSTER:
        return "OVERLAPPING"
    if collapse_hits and not overlap_hits:
        return "UNRESOLVED"
    return "UNRESOLVED"


def overall_decision(
    statuses: Mapping[str, str],
    pair_flag_counts: Mapping[str, int],
) -> str:
    status_counts = {name: 0 for name in FAMILY_STATUSES}
    for status in statuses.values():
        status_counts[status] = status_counts.get(status, 0) + 1
    non_separable = sum(count for name, count in status_counts.items() if name != "SEPARABLE")
    if non_separable == 0:
        return "CURRENT_ONTOLOGY_DATA_SEPARABLE"
    sparse = status_counts["UNDER_SUPPORTED"]
    overlapping = status_counts["OVERLAPPING"]
    noisy = status_counts["NOISY"]
    ontology_pairs = int(pair_flag_counts.get("ONTOLOGY_OVERLAP", 0))
    generic_pairs = int(pair_flag_counts.get("DEFINITION_TOO_GENERIC", 0))
    sparse_pairs = int(pair_flag_counts.get("DATA_TOO_SPARSE", 0))
    collapse_pairs = int(pair_flag_counts.get("REPRESENTATION_COLLAPSE", 0))
    signals = {
        "DATA_EXPANSION_REQUIRED": sparse + sparse_pairs,
        "BOUNDARY_REFINEMENT_REQUIRED": generic_pairs + status_counts["UNRESOLVED"],
        "ONTOLOGY_REFACTOR_REQUIRED": overlapping * 3 + ontology_pairs * 2,
    }
    active_kinds = sum(
        1
        for key in (
            sparse > 0,
            overlapping > 0,
            generic_pairs >= 8,
            ontology_pairs >= 8,
            noisy > 0,
        )
        if key
    )
    if active_kinds >= 3 or (collapse_pairs > 0 and sparse > 0 and overlapping > 0):
        return "MIXED_REMEDIATION_REQUIRED"
    ranked = sorted(
        (
            ("ONTOLOGY_REFACTOR_REQUIRED", signals["ONTOLOGY_REFACTOR_REQUIRED"]),
            ("DATA_EXPANSION_REQUIRED", signals["DATA_EXPANSION_REQUIRED"]),
            ("BOUNDARY_REFINEMENT_REQUIRED", signals["BOUNDARY_REFINEMENT_REQUIRED"]),
        ),
        key=lambda item: (-item[1], item[0]),
    )
    if ranked[0][1] == 0:
        return "MIXED_REMEDIATION_REQUIRED"
    if ranked[0][0] == "ONTOLOGY_REFACTOR_REQUIRED" and sparse >= 3 and ontology_pairs < 10:
        return "MIXED_REMEDIATION_REQUIRED"
    return ranked[0][0]


def remediation_for(family: str, status: str, dominant_flags: Sequence[str]) -> dict[str, Any]:
    actions: list[str] = []
    if status == "SEPARABLE":
        return {"family": family, "actions": [], "status": status}
    if status == "UNDER_SUPPORTED" or "DATA_TOO_SPARSE" in dominant_flags:
        actions.append("more direct positive examples")
    if "DEFINITION_TOO_GENERIC" in dominant_flags:
        actions.append("better definition text")
        actions.append("explicit exclusion examples")
        actions.append("boundary refinement")
    if "LABEL_NOISE" in dominant_flags or status == "NOISY":
        actions.append("label cleanup")
    if "ONTOLOGY_OVERLAP" in dominant_flags or status == "OVERLAPPING":
        actions.append("boundary refinement")
        if family in COLLAPSE_CLUSTER:
            actions.append("family merge candidate")
            actions.append("family split")
    if "REPRESENTATION_COLLAPSE" in dominant_flags and "better definition text" not in actions:
        actions.append("better definition text")
    if not actions:
        actions.append("boundary refinement")
    seen: set[str] = set()
    ordered = []
    for action in actions:
        if action in seen:
            continue
        seen.add(action)
        ordered.append(action)
    return {"family": family, "actions": ordered, "status": status}


def sparse_family_treatment(
    family: str,
    *,
    n_train: int,
    n_val: int,
    lexical_pair_best: Mapping[str, Any] | None,
    probe_best: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Do not infer ontology failure from low support alone."""
    additional_data_plausible = False
    rationale = []
    if n_train <= SPARSE_SUPPORT_MAX:
        rationale.append("training_definition_support_sparse")
    if n_val >= 2:
        rationale.append("validation_definitions_exist")
        additional_data_plausible = True
    if lexical_pair_best is not None:
        enrich = len(lexical_pair_best.get("tokens_enriched_in_a") or []) + len(
            lexical_pair_best.get("tokens_enriched_in_b") or []
        )
        if enrich >= 4 and float(lexical_pair_best.get("shared_token_ratio") or 1.0) < 0.6:
            rationale.append("lexical_cues_exist_despite_sparse_train")
            additional_data_plausible = True
        elif float(lexical_pair_best.get("shared_token_ratio") or 0.0) >= 0.6:
            rationale.append("definitions_still_generic_even_with_available_text")
    if probe_best is not None and probe_best.get("status") == "OK":
        if float(probe_best.get("f1") or 0.0) >= 0.75:
            rationale.append("pairwise_probe_succeeds_when_support_allows")
            additional_data_plausible = True
    if family == "internet-slang" and n_val >= 20:
        additional_data_plausible = True
        rationale.append("large_val_definition_pool_suggests_train_expansion_can_help")
    if family == "memetic" and n_train <= 1:
        rationale.append("single_train_definition_blocks_ontology_judgment")
        additional_data_plausible = True
    if family == "betting-sharp" and n_train <= 2:
        rationale.append("two_train_definitions_insufficient_for_ontology_failure_claim")
        additional_data_plausible = True
    return {
        "additional_data_plausibly_resolves": additional_data_plausible,
        "family": family,
        "n_train_definitions": n_train,
        "n_val_definitions": n_val,
        "ontology_failure_from_support_alone": False,
        "rationale": rationale,
    }


def matrix_sha256(matrix: Mapping[str, Any]) -> str:
    return sha256_text(canonical_json(matrix))


def assemble_pair_matrices(
    families: Sequence[str],
    pair_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    embedding: dict[str, Any] = {
        "families": list(families),
        "pairs": {},
    }
    lexical: dict[str, Any] = {
        "families": list(families),
        "pairs": {},
    }
    for row in pair_rows:
        key = f"{row['family_a']}||{row['family_b']}"
        embedding["pairs"][key] = {
            "anchor_collision_rate": row["embedding"]["anchor_collision_rate"],
            "centroid_distance": row["embedding"]["centroid_distance"],
            "cross_family_similarity": row["embedding"]["cross_family_similarity"],
            "family_a": row["family_a"],
            "family_b": row["family_b"],
            "nearest_neighbor_confusion_a": row["embedding"]["nearest_neighbor_confusion_a"],
            "nearest_neighbor_confusion_b": row["embedding"]["nearest_neighbor_confusion_b"],
            "probe_accuracy": row["probe"]["accuracy"],
            "probe_f1": row["probe"]["f1"],
            "probe_status": row["probe"]["status"],
            "within_family_similarity_a": row["embedding"]["within_family_similarity_a"],
            "within_family_similarity_b": row["embedding"]["within_family_similarity_b"],
        }
        lexical["pairs"][key] = {
            "distinctive_phrases_a": row["lexical"]["distinctive_phrases_a"],
            "distinctive_phrases_b": row["lexical"]["distinctive_phrases_b"],
            "family_a": row["family_a"],
            "family_b": row["family_b"],
            "shared_high_frequency_tokens": row["lexical"]["shared_high_frequency_tokens"],
            "shared_token_ratio": row["lexical"]["shared_token_ratio"],
            "tokens_enriched_in_a": row["lexical"]["tokens_enriched_in_a"],
            "tokens_enriched_in_b": row["lexical"]["tokens_enriched_in_b"],
        }
    return {
        "embedding_matrix": embedding,
        "embedding_matrix_sha256": matrix_sha256(embedding),
        "lexical_matrix": lexical,
        "lexical_matrix_sha256": matrix_sha256(lexical),
    }


def boundary_evidence_for_family(
    family: str,
    texts: Sequence[str],
    competitor_texts: Mapping[str, Sequence[str]],
    *,
    sealed_boundary: Mapping[str, Any] | None = None,
    ambiguous_rows: Sequence[Mapping[str, Any]] | None = None,
    violating_rows: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    own_counts = token_document_counts(texts)
    positive = sorted(own_counts, key=lambda token: (-own_counts[token], token))[:LEXICAL_TOP_K]
    nearest = []
    distinguishing: dict[str, list[str]] = {}
    overlapping: dict[str, list[str]] = {}
    for competitor, other_texts in competitor_texts.items():
        report = lexical_pair_report(texts, other_texts)
        nearest.append(
            {
                "family": competitor,
                "shared_token_ratio": report["shared_token_ratio"],
            }
        )
        distinguishing[competitor] = report["tokens_enriched_in_a"][:4]
        overlapping[competitor] = report["shared_high_frequency_tokens"][:4]
    nearest = sorted(nearest, key=lambda item: (-float(item["shared_token_ratio"]), item["family"]))[
        :NEAREST_COMPETITORS
    ]
    exclude_when = []
    if sealed_boundary is not None:
        exclude_when = list(sealed_boundary.get("exclude_when") or [])
        if sealed_boundary.get("distinguishing_cues"):
            positive = list(dict.fromkeys(list(sealed_boundary["distinguishing_cues"]) + positive))[
                :LEXICAL_TOP_K
            ]
    return {
        "ambiguous_training_rows": list(ambiguous_rows or [])[:8],
        "boundary_violating_rows": list(violating_rows or [])[:8],
        "distinguishing_cues": {
            item["family"]: distinguishing.get(item["family"], []) for item in nearest
        },
        "exclusion_cues": exclude_when,
        "family": family,
        "nearest_competing_families": [item["family"] for item in nearest],
        "positive_semantic_cues": positive,
        "shared_overlapping_cues": {
            item["family"]: overlapping.get(item["family"], []) for item in nearest
        },
    }


def find_ambiguous_and_violating_rows(
    family_vectors: Mapping[str, Sequence[Sequence[float]]],
    family_identities: Mapping[str, Sequence[str]],
    family_texts: Mapping[str, Sequence[str]],
    family_centroids: Mapping[str, Sequence[float]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    ambiguous: dict[str, list[dict[str, Any]]] = {family: [] for family in ACTIVE_FAMILY_VOCABULARY}
    violating: dict[str, list[dict[str, Any]]] = {family: [] for family in ACTIVE_FAMILY_VOCABULARY}
    families = [family for family in ACTIVE_FAMILY_VOCABULARY if family in family_centroids]
    for family in families:
        vectors = family_vectors.get(family) or []
        identities = family_identities.get(family) or []
        texts = family_texts.get(family) or []
        for index, vector in enumerate(vectors):
            unit = _unit(vector)
            scores = {
                other: sum(a * b for a, b in zip(unit, _unit(family_centroids[other])))
                for other in families
            }
            ordered = sorted(
                scores.items(),
                key=lambda item: (-item[1], ACTIVE_FAMILY_VOCABULARY.index(item[0])),
            )
            best_family, best_score = ordered[0]
            second_family, second_score = ordered[1] if len(ordered) > 1 else (None, None)
            identity = identities[index] if index < len(identities) else ""
            text = texts[index] if index < len(texts) else ""
            row = {
                "best_family": best_family,
                "best_score": _scalar(best_score),
                "identity": identity,
                "second_family": second_family,
                "second_score": None if second_score is None else _scalar(second_score),
                "text": text,
            }
            if best_family != family:
                violating[family].append(row)
            if second_score is not None and abs(best_score - second_score) <= AMBIGUOUS_MARGIN:
                ambiguous[family].append(row)
    return ambiguous, violating


def assemble_audit(payload: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "boundary_evidence",
        "decision",
        "embedding_matrix_sha256",
        "family_status",
        "lexical_matrix_sha256",
        "pair_rows",
        "remediation",
        "sparse_treatment",
        "support",
        "suspected_label_noise",
        "worst_collision_pairs",
    )
    for key in required:
        if key not in payload:
            raise ClassificationContractError("SEPARABILITY_AUDIT_UNAVAILABLE", key)
    if payload["decision"] not in AUDIT_DECISIONS:
        raise ClassificationContractError("SEPARABILITY_AUDIT_UNAVAILABLE", "decision")
    if set(payload["family_status"]) != set(ACTIVE_FAMILY_VOCABULARY):
        raise ClassificationContractError("SEPARABILITY_AUDIT_UNAVAILABLE", "family_status")
    for status in payload["family_status"].values():
        if status not in FAMILY_STATUSES:
            raise ClassificationContractError("SEPARABILITY_AUDIT_UNAVAILABLE", "status")
    contract = audit_contract()
    artifact = {
        "audit_state": "SEALED",
        "best_sha256": BEST_SHA,
        "boundary_evidence": payload["boundary_evidence"],
        "boundary_sha256": BOUNDARY_SHA,
        "collapse_cluster": list(COLLAPSE_CLUSTER),
        "contract": contract,
        "decision": payload["decision"],
        "embedding_matrix_sha256": payload["embedding_matrix_sha256"],
        "encoder_updated": False,
        "family_status": {
            family: payload["family_status"][family] for family in ACTIVE_FAMILY_VOCABULARY
        },
        "jev": "OFF",
        "lexical_matrix_sha256": payload["lexical_matrix_sha256"],
        "moves_best": False,
        "pair_flag_counts": payload.get("pair_flag_counts", {}),
        "pair_rows": payload["pair_rows"],
        "proposed_boundary_refinements": payload.get("proposed_boundary_refinements", []),
        "remediation": payload["remediation"],
        "repair_primary_sha256": REPAIR_PRIMARY_SHA,
        "reserve_scored": False,
        "schema": AUDIT_SCHEMA,
        "separation_sha256": SEPARATION_SHA,
        "sparse_focus": list(SPARSE_FOCUS),
        "sparse_treatment": payload["sparse_treatment"],
        "support": payload["support"],
        "suspected_label_noise": payload["suspected_label_noise"],
        "train": False,
        "worst_collision_pairs": payload["worst_collision_pairs"],
    }
    artifact["artifact_sha256"] = sha256_text(
        canonical_json({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    )
    return artifact


def rank_worst_pairs(pair_rows: Sequence[Mapping[str, Any]], *, limit: int = 20) -> list[dict[str, Any]]:
    def severity(row: Mapping[str, Any]) -> tuple[Any, ...]:
        flags = list(row.get("flags") or [])
        score = 0
        if "ONTOLOGY_OVERLAP" in flags:
            score += 8
        if "DEFINITION_TOO_GENERIC" in flags:
            score += 5
        if "REPRESENTATION_COLLAPSE" in flags:
            score += 4
        if "LABEL_NOISE" in flags:
            score += 3
        if "DATA_TOO_SPARSE" in flags:
            score += 1
        if "SEPARABLE" in flags:
            score -= 10
        cross = float(row.get("embedding", {}).get("cross_family_similarity") or 0.0)
        probe_f1 = row.get("probe", {}).get("f1")
        probe_penalty = 0.0 if probe_f1 is None else (1.0 - float(probe_f1))
        return (-score, -cross, -probe_penalty, row["family_a"], row["family_b"])

    ranked = sorted(pair_rows, key=severity)
    out = []
    for row in ranked[:limit]:
        out.append(
            {
                "centroid_distance": row["embedding"]["centroid_distance"],
                "cross_family_similarity": row["embedding"]["cross_family_similarity"],
                "family_a": row["family_a"],
                "family_b": row["family_b"],
                "flags": list(row["flags"]),
                "probe_f1": row["probe"]["f1"],
                "probe_status": row["probe"]["status"],
                "shared_token_ratio": row["lexical"]["shared_token_ratio"],
            }
        )
    return out


def propose_boundary_refinements(
    family_status: Mapping[str, str],
    boundary_evidence: Sequence[Mapping[str, Any]],
    worst_pairs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    evidence = {item["family"]: item for item in boundary_evidence}
    proposals: list[dict[str, Any]] = []
    for family, status in family_status.items():
        if status == "SEPARABLE":
            continue
        item = evidence.get(family) or {}
        competitors = list(item.get("nearest_competing_families") or [])
        proposals.append(
            {
                "family": family,
                "nearest_competitors": competitors,
                "require_exclusion_cues": list(item.get("exclusion_cues") or [])[:4],
                "require_positive_cues": list(item.get("positive_semantic_cues") or [])[:4],
                "status": status,
                "suggestion": (
                    "tighten definition prose and add exclusion examples against nearest competitors"
                    if status in {"OVERLAPPING", "UNRESOLVED"}
                    else "expand direct positive definition support before ontology edits"
                ),
            }
        )
    for pair in worst_pairs:
        flags = set(pair.get("flags") or [])
        if "ONTOLOGY_OVERLAP" not in flags:
            continue
        a = pair["family_a"]
        b = pair["family_b"]
        if a in COLLAPSE_CLUSTER and b in COLLAPSE_CLUSTER:
            proposals.append(
                {
                    "family": a,
                    "merge_candidate_with": b,
                    "status": family_status.get(a, "UNRESOLVED"),
                    "suggestion": (
                        "evaluate mutual exclusivity; merge only if definitions are not "
                        "operationally distinct"
                    ),
                }
            )
    seen: set[str] = set()
    unique = []
    for proposal in proposals:
        key = sha256_text(canonical_json(proposal))
        if key in seen:
            continue
        seen.add(key)
        unique.append(proposal)
    return unique
