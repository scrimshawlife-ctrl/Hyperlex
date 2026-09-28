"""Development comparison for one frozen residual replay.

The functions do not encode text, do not read operator labels, and do not
choose a threshold. Scores enter only after the replay has hashed them.
"""

from __future__ import annotations

import random
from decimal import Decimal, ROUND_HALF_EVEN

from hyperlexical.model_based_wsd_candidate_v1 import project_row_status
from hyperlexical.semantic_compositionality_residual import (
    RESIDUAL_QUANTUM,
    decimal_mean,
    percentile,
)

EXACT = "EXACT"
RESOLVED = "RESOLVED"
AMBIGUOUS = "AMBIGUOUS"
UNRESOLVED = "UNRESOLVED"
TIER1_STRUCTURAL = "TIER1_STRUCTURAL"
TIER1_UNIQUE = "TIER1_UNIQUE_LEMMA"
TIER2_LESK = "TIER2_EXTENDED_LESK"
TIER3_GLOSSBERT = "TIER3_GLOSSBERT"
TIER_UNRESOLVED = "UNRESOLVED"
READY = "RESIDUAL_READY"
ROW_UNKNOWN = "UNKNOWN"
SUPPORTED = "SUPPORTED_DIRECTION"
NO_SEPARATION = "NO_DIRECTIONAL_SEPARATION"
INVERTED = "INVERTED_DIRECTION"
PROMISING = "CANDIDATE_PROMISING"
INSUFFICIENT = "CANDIDATE_INSUFFICIENT"
NOT_COMPUTABLE = "NOT_COMPUTABLE"
NOT_DETERMINISTIC = "NOT_DETERMINISTIC"
BOOTSTRAP_SEED = 0
BOOTSTRAP_RESAMPLES = 10000
TIER3_MIN_CELL = 3
EFFECT_QUANTUM = Decimal("0.000001")
INTERVAL_LOW = Decimal("2.5")
INTERVAL_HIGH = Decimal("97.5")

_DIRECTION_RULE = (
    "The hypothesized direction is a larger HIGH residual than a SECONDARY residual. "
    "Supported requires a higher HIGH median, a positive rank-biserial, and an AUC above one half."
)
_AUC_RULE = (
    "AUC is the share of HIGH-versus-SECONDARY pairs in which the HIGH residual is larger. "
    "Ties count one half. HIGH is the positive class. SECONDARY is the negative class. "
    "REJECT is excluded."
)
_EFFECT_RULE = (
    "The rank-biserial is favorable pairs minus unfavorable pairs, divided by the "
    "number of HIGH-SECONDARY pairs. A favorable pair has the larger HIGH residual."
)
_BOOTSTRAP_RULE = (
    "Resample each class with replacement. The interval is the interpolated 2.5 and 97.5 "
    "percentiles. The seed and the resample count are fixed before the scores are joined to labels."
)
_EXTREME_RULE = (
    "Drop the largest HIGH residual and the smallest SECONDARY residual. "
    "The result is extreme-driven when the HIGH median is no longer larger."
)
_TIER3_RULE = (
    "Tier 3 concentration requires both the no-tier-3 group and the tier-3 group "
    "to have at least three HIGH rows and three SECONDARY rows, the no-tier-3 group "
    "to lack the hypothesized direction, and the tier-3 group to show it."
)
_NO_THRESHOLD = "No residual threshold is selected. No row receives a semantic yes or no."


def analysis_plan() -> dict:
    """Return the preregistered comparison. It contains no residual scores."""
    return {
        "auc": _AUC_RULE,
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "bootstrap_rule": _BOOTSTRAP_RULE,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "direction": _DIRECTION_RULE,
        "effect": _EFFECT_RULE,
        "emits_yes_no": False,
        "extreme_rule": _EXTREME_RULE,
        "high_positive_class": "HIGH",
        "json_schema_document": None,
        "reject_excluded_from_auc": True,
        "secondary_negative_class": "SECONDARY",
        "semantic_noncompositionality_threshold": None,
        "threshold_eligible": False,
        "threshold_rule": _NO_THRESHOLD,
        "tier3_min_cell": TIER3_MIN_CELL,
        "tier3_rule": _TIER3_RULE,
    }


def integrate_constituent(resolver_row: dict, model_row: dict | None) -> dict:
    """Copy one frozen constituent decision. The model row is consulted only for a Lesk tie."""
    method = resolver_row["resolution_method"]
    status = resolver_row["resolution_status"]
    if method == "STRUCTURAL_EXACT" and status == EXACT:
        _reject_model(model_row)
        return _copy(resolver_row, TIER1_STRUCTURAL, EXACT, resolver_row["selected_synset"], None)
    if method == "UNIQUE_LEMMA" and status == EXACT:
        _reject_model(model_row)
        return _copy(resolver_row, TIER1_UNIQUE, EXACT, resolver_row["selected_synset"], None)
    if method == "EXTENDED_LESK_V1" and status == RESOLVED:
        _reject_model(model_row)
        return _copy(resolver_row, TIER2_LESK, RESOLVED, resolver_row["selected_synset"], None)
    if method == "NONE" and status == UNRESOLVED:
        _reject_model(model_row)
        return _copy(resolver_row, TIER_UNRESOLVED, UNRESOLVED, None, None)
    if method == "STRUCTURAL_EXACT" and status == AMBIGUOUS:
        _reject_model(model_row)
        return _copy(resolver_row, TIER1_STRUCTURAL, AMBIGUOUS, None, None)
    if method != "EXTENDED_LESK_V1" or status != AMBIGUOUS:
        raise RuntimeError("constituent decision is outside the frozen stack")
    if model_row is None:
        raise RuntimeError("lesk tie has no frozen model row")
    if model_row["prior_resolution_status"] != AMBIGUOUS:
        raise RuntimeError("model row is not a lesk tie")
    if model_row["model_resolution_status"] == RESOLVED:
        selected = model_row["selected_synset"]
        if selected not in resolver_row["candidate_synsets"]:
            raise RuntimeError("model synset is outside the frozen candidates")
        return _copy(
            resolver_row,
            TIER3_GLOSSBERT,
            RESOLVED,
            selected,
            model_row["selected_sense_key"],
            model_row["primary_evidence_code"],
        )
    if model_row["model_resolution_status"] == AMBIGUOUS:
        if model_row["selected_synset"] is not None:
            raise RuntimeError("abstaining model row names a synset")
        return _copy(resolver_row, TIER3_GLOSSBERT, AMBIGUOUS, None, None, model_row["primary_evidence_code"])
    raise RuntimeError("model row is not a frozen resolved or abstaining decision")


def _reject_model(model_row: dict | None) -> None:
    if model_row is not None:
        raise RuntimeError("model row overrides a frozen non-tie")


def _copy(resolver_row, tier, status, synset, sense_key, provenance=None) -> dict:
    return {
        "constituent_index": resolver_row["constituent_index"],
        "constituent_pos": resolver_row["constituent_pos"],
        "constituent_surface": resolver_row["constituent_surface"],
        "parent_row_id": resolver_row["parent_row_id"],
        "parent_surface": resolver_row["parent_surface"],
        "parent_synset": resolver_row["parent_synset"],
        "resolution_provenance": provenance or resolver_row["primary_evidence_code"],
        "resolution_status": status,
        "resolution_tier": tier,
        "selected_pwn30_synset": synset,
        "selected_sense_key_if_available": sense_key,
    }


def projection_token(tier: str, status: str) -> str:
    """Map an integrated constituent onto the frozen projection vocabulary."""
    if status == EXACT:
        return EXACT
    if tier == TIER2_LESK and status == RESOLVED:
        return "LESK_RESOLVED"
    if tier == TIER3_GLOSSBERT and status == RESOLVED:
        return "MODEL_RESOLVED"
    if status == UNRESOLVED:
        return UNRESOLVED
    if status == AMBIGUOUS:
        return AMBIGUOUS
    raise RuntimeError("integrated constituent has no projection token")


def row_projection(statuses: list[str]) -> str:
    return project_row_status(statuses)


def abstention_reason(statuses: list[str]) -> str | None:
    """Return the leftmost frozen abstention. A ready row returns None."""
    if len(statuses) < 2:
        return "fewer_than_two_content_constituents"
    for status in statuses:
        if status == AMBIGUOUS:
            return "ambiguous_content_constituent"
        if status == UNRESOLVED:
            return "unresolved_content_constituent"
        if status not in {EXACT, RESOLVED}:
            raise RuntimeError("unknown integrated status")
    return None


def _ordered(scores: list[str]) -> list[str]:
    return sorted(scores, key=Decimal)


def sample_std(scores: list[str]) -> str | None:
    """Sample standard deviation at the residual quantum. One row has no dispersion."""
    if len(scores) < 2:
        return None
    mean = sum((Decimal(score) for score in scores), start=Decimal(0)) / Decimal(len(scores))
    dispersion = sum((Decimal(score) - mean) ** 2 for score in scores) / Decimal(len(scores) - 1)
    return str(dispersion.sqrt().quantize(RESIDUAL_QUANTUM, rounding=ROUND_HALF_EVEN))


def full_distribution(scores: list[str]) -> dict:
    if not scores:
        return {
            "count": 0,
            "max": None,
            "mean": None,
            "median": None,
            "min": None,
            "p10": None,
            "p25": None,
            "p75": None,
            "p90": None,
            "status": NOT_COMPUTABLE,
            "std": None,
        }
    ordered = _ordered(scores)
    return {
        "count": len(ordered),
        "max": ordered[-1],
        "mean": decimal_mean(ordered),
        "median": percentile(ordered, 50),
        "min": ordered[0],
        "p10": percentile(ordered, 10),
        "p25": percentile(ordered, 25),
        "p75": percentile(ordered, 75),
        "p90": percentile(ordered, 90),
        "status": "DESCRIPTIVE",
        "std": sample_std(ordered),
    }


def _quantize_effect(value: Decimal) -> str:
    return str(value.quantize(EFFECT_QUANTUM, rounding=ROUND_HALF_EVEN))


def _quantize_residual(value: Decimal) -> str:
    return str(value.quantize(RESIDUAL_QUANTUM, rounding=ROUND_HALF_EVEN))


def pair_comparison(high_scores: list[str], secondary_scores: list[str]) -> dict:
    """Compare HIGH with SECONDARY. REJECT is not an argument."""
    if not high_scores or not secondary_scores:
        return {"status": NOT_COMPUTABLE}
    favorable = 0
    unfavorable = 0
    ties = 0
    for high in high_scores:
        high_value = Decimal(high)
        for secondary in secondary_scores:
            secondary_value = Decimal(secondary)
            if high_value > secondary_value:
                favorable += 1
            elif high_value < secondary_value:
                unfavorable += 1
            else:
                ties += 1
    pairs = Decimal(len(high_scores) * len(secondary_scores))
    u_high = Decimal(favorable) + (Decimal(ties) / Decimal(2))
    u_secondary = Decimal(unfavorable) + (Decimal(ties) / Decimal(2))
    high_dist = full_distribution(high_scores)
    secondary_dist = full_distribution(secondary_scores)
    mean_gap = Decimal(high_dist["mean"]) - Decimal(secondary_dist["mean"])
    median_gap = Decimal(high_dist["median"]) - Decimal(secondary_dist["median"])
    auc = u_high / pairs
    effect = (Decimal(favorable) - Decimal(unfavorable)) / pairs
    return {
        "auc": _quantize_effect(auc),
        "favorable_pairs": favorable,
        "high": high_dist,
        "mean_difference": _quantize_residual(mean_gap),
        "median_difference": _quantize_residual(median_gap),
        "rank_biserial": _quantize_effect(effect),
        "secondary": secondary_dist,
        "status": "DESCRIPTIVE",
        "ties": ties,
        "u_high": _quantize_effect(u_high),
        "u_secondary": _quantize_effect(u_secondary),
        "unfavorable_pairs": unfavorable,
    }


def direction_result(comparison: dict) -> str:
    if comparison.get("status") == NOT_COMPUTABLE:
        return NOT_COMPUTABLE
    median_gap = Decimal(comparison["median_difference"])
    effect = Decimal(comparison["rank_biserial"])
    auc = Decimal(comparison["auc"])
    if median_gap > 0 and effect > 0 and auc > Decimal("0.5"):
        return SUPPORTED
    if median_gap < 0 and effect < 0 and auc < Decimal("0.5"):
        return INVERTED
    return NO_SEPARATION


def _supports(scores_high: list[str], scores_secondary: list[str]) -> bool:
    if not scores_high or not scores_secondary:
        return False
    return direction_result(pair_comparison(scores_high, scores_secondary)) == SUPPORTED


def _interpolated(sorted_values: list[Decimal], percent: Decimal) -> Decimal:
    count = len(sorted_values)
    if count == 1:
        return sorted_values[0]
    rank = Decimal(count - 1) * (percent / Decimal(100))
    low = int(rank)
    high = min(low + 1, count - 1)
    weight = rank - Decimal(low)
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * weight


def bootstrap_intervals(
    high_scores: list[str],
    secondary_scores: list[str],
    *,
    seed: int = BOOTSTRAP_SEED,
    resamples: int = BOOTSTRAP_RESAMPLES,
) -> dict:
    """Deterministic percentile intervals. The seed and count are arguments, not a search."""
    if seed != BOOTSTRAP_SEED or resamples != BOOTSTRAP_RESAMPLES:
        if resamples < 1 or seed < 0:
            raise RuntimeError("bootstrap settings are invalid")
    if not high_scores or not secondary_scores:
        return {"status": NOT_COMPUTABLE}
    generator = random.Random(seed)
    high_values = [Decimal(score) for score in high_scores]
    secondary_values = [Decimal(score) for score in secondary_scores]
    mean_gaps = []
    median_gaps = []
    aucs = []
    for _ in range(resamples):
        high_draw = [high_values[generator.randrange(len(high_values))] for _ in high_values]
        secondary_draw = [secondary_values[generator.randrange(len(secondary_values))] for _ in secondary_values]
        high_text = [format(value, "f") for value in high_draw]
        secondary_text = [format(value, "f") for value in secondary_draw]
        comparison = pair_comparison(high_text, secondary_text)
        mean_gaps.append(Decimal(comparison["mean_difference"]))
        median_gaps.append(Decimal(comparison["median_difference"]))
        aucs.append(Decimal(comparison["auc"]))
    return {
        "auc": _interval(aucs, EFFECT_QUANTUM),
        "mean_difference": _interval(mean_gaps, RESIDUAL_QUANTUM),
        "median_difference": _interval(median_gaps, RESIDUAL_QUANTUM),
        "resamples": resamples,
        "seed": seed,
        "status": "DESCRIPTIVE",
    }


def _interval(values: list[Decimal], quantum: Decimal) -> dict:
    ordered = sorted(values)
    low = _interpolated(ordered, INTERVAL_LOW).quantize(quantum, rounding=ROUND_HALF_EVEN)
    high = _interpolated(ordered, INTERVAL_HIGH).quantize(quantum, rounding=ROUND_HALF_EVEN)
    return {"high": str(high), "low": str(low)}


def _cell(rows: list[dict], bucket: str) -> list[str]:
    return [row["residual_score"] for row in rows if row["bucket"] == bucket]


def tier3_concentration(rows: list[dict]) -> dict:
    """Return whether the direction exists only inside the Tier 3 subgroup."""
    groups = {}
    concentrated = False
    flags = {}
    for name, uses_tier3 in (("no_tier3", False), ("with_tier3", True)):
        chosen = [row for row in rows if row["uses_tier3"] is uses_tier3 and row["bucket"] in {"HIGH", "SECONDARY"}]
        high = _cell(chosen, "HIGH")
        secondary = _cell(chosen, "SECONDARY")
        computable = len(high) >= TIER3_MIN_CELL and len(secondary) >= TIER3_MIN_CELL
        if not computable:
            groups[name] = {
                "high_count": len(high),
                "secondary_count": len(secondary),
                "status": NOT_COMPUTABLE,
            }
            flags[name] = None
            continue
        comparison = pair_comparison(high, secondary)
        groups[name] = {
            "comparison": comparison,
            "direction": direction_result(comparison),
            "high_count": len(high),
            "secondary_count": len(secondary),
            "status": "DESCRIPTIVE",
        }
        flags[name] = groups[name]["direction"] == SUPPORTED
    if flags["no_tier3"] is False and flags["with_tier3"] is True:
        concentrated = True
    return {"concentrated": concentrated, "groups": groups}


def extreme_driven(high_scores: list[str], secondary_scores: list[str]) -> bool:
    """True when dropping the most favorable extreme on each side removes the median gap."""
    if len(high_scores) < TIER3_MIN_CELL or len(secondary_scores) < TIER3_MIN_CELL:
        return False
    if not _supports(high_scores, secondary_scores):
        return False
    kept_high = list(high_scores)
    kept_secondary = list(secondary_scores)
    kept_high.remove(max(kept_high, key=Decimal))
    kept_secondary.remove(min(kept_secondary, key=Decimal))
    return not _supports(kept_high, kept_secondary)


def pos_partitioned(rows: list[dict]) -> bool:
    high = {row["pos"] for row in rows if row["bucket"] == "HIGH"}
    secondary = {row["pos"] for row in rows if row["bucket"] == "SECONDARY"}
    return bool(high) and bool(secondary) and high.isdisjoint(secondary)


def replay_decision(
    *,
    readiness_reproduced: bool,
    determinism: str,
    direction: str,
    tier3_concentrated: bool,
    extremes: bool,
    pos_split: bool,
) -> dict:
    """Apply the preregistered status rule. The flags are not a threshold search."""
    if not readiness_reproduced:
        status = NOT_COMPUTABLE
        transition = "RESIDUAL_REPLAY_READINESS_REVIEW_AUTHORIZATION"
    elif determinism != "IDENTICAL":
        status = NOT_DETERMINISTIC
        transition = "RESIDUAL_REPLAY_DETERMINISM_REVIEW_AUTHORIZATION"
    elif direction == NOT_COMPUTABLE:
        status = NOT_COMPUTABLE
        transition = "RESIDUAL_REPLAY_READINESS_REVIEW_AUTHORIZATION"
    elif direction == SUPPORTED and not tier3_concentrated and not extremes and not pos_split:
        status = PROMISING
        transition = "RESIDUAL_THRESHOLD_PREREGISTRATION_AUTHORIZATION"
    else:
        status = INSUFFICIENT
        transition = "RESIDUAL_V2_DESIGN_AUTHORIZATION"
    return {
        "candidate_status": status,
        "next_legal_transition": transition,
        "next_transition_authorized": False,
        "state": "RESIDUAL_DEVELOPMENT_ANALYZED_V2",
        "threshold_eligible": False,
    }


def _ranks(values: list[Decimal]) -> list[Decimal]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [Decimal(0)] * len(values)
    start = 0
    while start < len(values):
        stop = start + 1
        while stop < len(values) and values[order[stop]] == values[order[start]]:
            stop += 1
        rank = Decimal(start + 1 + stop) / Decimal(2)
        for index in order[start:stop]:
            ranks[index] = rank
        start = stop
    return ranks


def spearman(xs: list[str], ys: list[str]) -> str | None:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    x_values = [Decimal(value) for value in xs]
    y_values = [Decimal(value) for value in ys]
    x_ranks = _ranks(x_values)
    y_ranks = _ranks(y_values)
    x_mean = sum(x_ranks, start=Decimal(0)) / Decimal(len(xs))
    y_mean = sum(y_ranks, start=Decimal(0)) / Decimal(len(ys))
    covariance = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_ranks, y_ranks))
    x_scale = sum((x - x_mean) ** 2 for x in x_ranks)
    y_scale = sum((y - y_mean) ** 2 for y in y_ranks)
    if x_scale == 0 or y_scale == 0:
        return None
    correlation = covariance / (x_scale.sqrt() * y_scale.sqrt())
    return _quantize_effect(correlation)


def numeric_summary(values: list[str]) -> dict:
    if not values:
        return {"count": 0, "status": NOT_COMPUTABLE}
    ordered = _ordered(values)
    return {
        "count": len(ordered),
        "max": ordered[-1],
        "mean": decimal_mean(ordered),
        "median": percentile(ordered, 50),
        "min": ordered[0],
        "status": "DESCRIPTIVE",
    }


def confound_report(rows: list[dict]) -> dict:
    """Describe nuisance structure. It does not change a residual."""
    target = [row for row in rows if row["bucket"] in {"HIGH", "SECONDARY"}]
    tier3 = tier3_concentration(target)
    high_scores = _cell(target, "HIGH")
    secondary_scores = _cell(target, "SECONDARY")
    nuisance = {}
    for field in (
        "token_count",
        "character_length",
        "content_count",
        "max_candidate_senses",
        "min_glossbert_confidence",
        "min_glossbert_margin",
    ):
        nuisance[field] = _nuisance(target, field)
    poses = {}
    for pos in sorted({row["pos"] for row in target}):
        chosen = [row for row in target if row["pos"] == pos]
        high = _cell(chosen, "HIGH")
        secondary = _cell(chosen, "SECONDARY")
        if len(high) < TIER3_MIN_CELL or len(secondary) < TIER3_MIN_CELL:
            poses[pos] = {"high_count": len(high), "secondary_count": len(secondary), "status": NOT_COMPUTABLE}
        else:
            poses[pos] = {"comparison": pair_comparison(high, secondary), "status": "DESCRIPTIVE"}
    return {
        "extreme_driven": extreme_driven(high_scores, secondary_scores),
        "nuisance": nuisance,
        "pos": poses,
        "pos_partitioned": pos_partitioned(target),
        "tier3": tier3,
        "tier3_counts": {
            "high_with_tier3": _tier_count(rows, "HIGH", True),
            "high_without_tier3": _tier_count(rows, "HIGH", False),
            "secondary_with_tier3": _tier_count(rows, "SECONDARY", True),
            "secondary_without_tier3": _tier_count(rows, "SECONDARY", False),
        },
    }


def _tier_count(rows: list[dict], bucket: str, uses_tier3: bool) -> int:
    return sum(row["bucket"] == bucket and row["uses_tier3"] is uses_tier3 for row in rows)


def _nuisance(rows: list[dict], field: str) -> dict:
    report = {}
    for bucket in ("HIGH", "SECONDARY"):
        paired = [
            (str(row[field]), row["residual_score"])
            for row in rows
            if row["bucket"] == bucket and row[field] is not None
        ]
        if not paired:
            report[bucket] = {"status": NOT_COMPUTABLE}
            continue
        values = [item[0] for item in paired]
        report[bucket] = {
            "spearman_with_residual": spearman(values, [item[1] for item in paired]),
            "summary": numeric_summary(values),
        }
    return report


def outlier_pair(rows: list[dict], bucket: str) -> dict:
    chosen = [row for row in rows if row["bucket"] == bucket]
    if not chosen:
        return {"status": NOT_COMPUTABLE}
    low = min(chosen, key=lambda row: Decimal(row["residual_score"]))
    high = max(chosen, key=lambda row: Decimal(row["residual_score"]))
    return {"largest": _outlier(high), "smallest": _outlier(low), "status": "DESCRIPTIVE"}


def _outlier(row: dict) -> dict:
    return {
        "residual_score": row["residual_score"],
        "resolution_tiers": list(row["tiers"]),
        "row_id": row["row_id"],
        "surface": row["surface"],
        "synset": row["synset"],
    }
