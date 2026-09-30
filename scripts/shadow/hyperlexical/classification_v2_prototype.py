"""Semantic prototypes for Classification v2 family rows.

Exact-name rows are copied. Every other active family row is initialized from
the mean of frozen warm-start encoder representations of training-split
definition text. This module does not train, fetch, or read the evaluation reserve.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from .classification_v2 import (
    ACTIVE_FAMILY_VOCABULARY,
    ClassificationContractError,
    map_family_rows,
    _f32_hash,
)
from .holdout_guard import normalized_text_sha256

PROTOTYPE_WEIGHT = {"OBSERVED": 1.0, "INFERRED": 0.5}
INITIALIZATION_EXACT = "EXACT_ROW_COPY"
INITIALIZATION_PROTOTYPE = "SEMANTIC_PROTOTYPE"
SCALING_RULE = "l2_normalize_then_multiply_by_median_l2_of_exact_copy_rows"
VALIDATION_FLOOR = 2
VALIDATION_PREFERRED = 4
BLOCKED_VALIDATION_STATES = frozenset({"EVAL_RESERVE", "EVAL_SPENT", "EVAL_BOUND"})


def _finite_vector(values: Sequence[float], reason: str) -> list[float]:
    vector: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ClassificationContractError(reason)
        number = float(value)
        if not math.isfinite(number):
            raise ClassificationContractError(reason)
        vector.append(number)
    if not vector:
        raise ClassificationContractError(reason)
    return vector


def l2_norm(values: Sequence[float]) -> float:
    vector = _finite_vector(values, "FAMILY_PROTOTYPE_UNAVAILABLE")
    norm = math.sqrt(sum(value * value for value in vector))
    if not math.isfinite(norm):
        raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE")
    return norm


def _f32_round(values: Sequence[float]) -> list[float]:
    import struct

    rounded: list[float] = []
    for value in values:
        number = float(value)
        if not math.isfinite(number):
            raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE")
        rounded.append(struct.unpack("<f", struct.pack("<f", number))[0])
    return rounded


def median_l2(rows: Sequence[Sequence[float]]) -> float:
    norms = sorted(l2_norm(row) for row in rows)
    if not norms:
        raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "target_norm")
    if any(norm == 0.0 for norm in norms):
        raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "target_norm")
    mid = len(norms) // 2
    if len(norms) % 2 == 1:
        return norms[mid]
    return (norms[mid - 1] + norms[mid]) / 2.0


def weighted_mean(vectors: Sequence[Sequence[float]], weights: Sequence[float]) -> list[float]:
    if not vectors or len(vectors) != len(weights):
        raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "empty_prototype")
    hidden = len(vectors[0])
    if hidden < 1:
        raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "empty_prototype")
    total = 0.0
    accumulator = [0.0] * hidden
    for vector, weight in zip(vectors, weights):
        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
            raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE")
        scale = float(weight)
        if not math.isfinite(scale) or scale <= 0.0:
            raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE")
        if len(vector) != hidden:
            raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "width")
        for index, value in enumerate(vector):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE")
            accumulator[index] += scale * float(value)
        total += scale
    if total == 0.0:
        raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE")
    mean = _f32_round(value / total for value in accumulator)
    if l2_norm(mean) == 0.0:
        raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "zero_norm")
    return mean


def scale_prototype(prototype: Sequence[float], target_norm: float) -> list[float]:
    vector = _f32_round(prototype)
    norm = l2_norm(vector)
    if norm == 0.0 or not math.isfinite(target_norm) or target_norm <= 0.0:
        raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "scale")
    return _f32_round((value / norm) * float(target_norm) for value in vector)


def _prose(row: Mapping[str, Any]) -> str:
    provenance = row.get("provenance")
    if not isinstance(provenance, dict):
        return ""
    return str(provenance.get("definition_prose") or "").strip()


def definition_string_report(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """A stored definition is the training string unless that identity is already used."""
    texts = {normalized_text_sha256(str(row.get("text") or "")) for row in rows}
    violations: list[dict[str, str]] = []
    for row in rows:
        provenance = row.get("provenance")
        if not isinstance(provenance, dict) or not provenance.get("evidence_seal"):
            continue
        prose = _prose(row)
        text = str(row.get("text") or "")
        if not prose:
            continue
        if text == prose:
            continue
        prose_identity = normalized_text_sha256(prose)
        if prose_identity in texts:
            continue
        violations.append(
            {
                "family": str(row.get("lineage") or ""),
                "page": str(provenance.get("page") or ""),
                "reason": "title_used_for_available_definition",
            }
        )
    return {"pass": not violations, "violations": violations}


def validation_family_support(
    rows: Sequence[Mapping[str, Any]],
    *,
    identity_state: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Count validation positives that are not reserve, spent, or bound."""
    states = identity_state or {}
    support = {family: 0 for family in ACTIVE_FAMILY_VOCABULARY}
    rejected: list[str] = []
    for row in rows:
        if row.get("split") != "val":
            continue
        lineage = str(row.get("lineage") or "")
        if lineage not in support:
            continue
        if row.get("class") not in PROTOTYPE_WEIGHT:
            continue
        if row.get("evaluation_reserve") or row.get("held_out") or row.get("surface") in {
            "evaluation_reserve",
            "held_out",
            "measurement",
            "settlement",
            "test",
        }:
            rejected.append(lineage)
            continue
        digest = normalized_text_sha256(str(row.get("text") or ""))
        if states.get(digest) in BLOCKED_VALIDATION_STATES:
            rejected.append(lineage)
            continue
        support[lineage] += 1
    deficient = [family for family in ACTIVE_FAMILY_VOCABULARY if support[family] < VALIDATION_FLOOR]
    below_preferred = [family for family in ACTIVE_FAMILY_VOCABULARY if support[family] < VALIDATION_PREFERRED]
    return {
        "support": support,
        "deficient": deficient,
        "below_preferred": below_preferred,
        "rejected_families": sorted(set(rejected)),
        "pass": not deficient and not rejected,
        "floor": VALIDATION_FLOOR,
        "preferred": VALIDATION_PREFERRED,
    }


def _copy_witness(family: str, weight: Sequence[float], bias: float) -> dict[str, Any]:
    rounded = _f32_round(weight)
    rounded_bias = _f32_round((bias,))[0]
    return {
        "bias_hash": _f32_hash((rounded_bias,)),
        "bias": rounded_bias,
        "family": family,
        "inferred_count": 0,
        "initialization_mode": INITIALIZATION_EXACT,
        "l2_norm": l2_norm(rounded),
        "observed_count": 0,
        "prototype_hash": None,
        "source_identity_count": 0,
        "source_row_hash": _f32_hash([*rounded, rounded_bias]),
        "weight": rounded,
        "weight_hash": _f32_hash(rounded),
    }


def _prototype_witness(
    family: str,
    vectors: Sequence[Sequence[float]],
    weights: Sequence[float],
    identities: Sequence[str],
    *,
    observed: int,
    inferred: int,
    target_norm: float,
) -> dict[str, Any]:
    order = sorted(range(len(identities)), key=lambda index: identities[index])
    ordered_vectors = [vectors[index] for index in order]
    ordered_weights = [weights[index] for index in order]
    if len(set(identities)) != len(identities):
        raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", family)
    prototype = weighted_mean(ordered_vectors, ordered_weights)
    scaled = scale_prototype(prototype, target_norm)
    return {
        "bias_hash": _f32_hash((0.0,)),
        "bias": 0.0,
        "family": family,
        "inferred_count": inferred,
        "initialization_mode": INITIALIZATION_PROTOTYPE,
        "l2_norm": l2_norm(scaled),
        "observed_count": observed,
        "prototype_hash": _f32_hash(prototype),
        "source_identity_count": len(identities),
        "source_row_hash": None,
        "weight": scaled,
        "weight_hash": _f32_hash(scaled),
    }


def assemble_initialization(
    source_labels: Sequence[str],
    source_weight: Sequence[Sequence[float]],
    source_bias: Sequence[float],
    prototypes: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Copy exact rows and scale a prototype into every remaining family row."""
    mapped = map_family_rows(source_labels, source_weight, source_bias)
    copied = [
        mapped["weight"][index]
        for index, row in enumerate(mapped["rows"])
        if row["mapping_status"] == "EXACT_COPY"
    ]
    if not copied:
        raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "no_exact_copy_rows")
    target = median_l2(copied)
    rows: list[dict[str, Any]] = []
    weight: list[list[float]] = []
    bias: list[float] = []
    missing: list[str] = []
    for index, item in enumerate(mapped["rows"]):
        family = item["active_family"]
        if item["mapping_status"] == "EXACT_COPY":
            witness = _copy_witness(family, mapped["weight"][index], mapped["bias"][index])
        else:
            payload = prototypes.get(family)
            if not payload:
                missing.append(family)
                continue
            try:
                witness = _prototype_witness(
                    family,
                    payload["vectors"],
                    payload["weights"],
                    payload["identities"],
                    observed=int(payload["observed"]),
                    inferred=int(payload["inferred"]),
                    target_norm=target,
                )
            except ClassificationContractError:
                missing.append(family)
                continue
        rows.append(witness)
        weight.append(witness["weight"])
        bias.append(witness["bias"])
    if missing:
        raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", missing)
    if [row["family"] for row in rows] != list(ACTIVE_FAMILY_VOCABULARY):
        raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "order")
    public = [_public_row(row) for row in rows]
    return {
        "bias": bias,
        "exact_copy_families": [row["family"] for row in rows if row["initialization_mode"] == INITIALIZATION_EXACT],
        "prototype_families": [row["family"] for row in rows if row["initialization_mode"] == INITIALIZATION_PROTOTYPE],
        "rows": public,
        "scaling_rule": SCALING_RULE,
        "target_norm": target,
        "target_norm_source": "median_l2_exact_reusable_active_family_rows",
        "weight": weight,
        "witness_sha256": witness_sha256(public, target),
    }


def _public_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "bias_hash": row["bias_hash"],
        "family": row["family"],
        "inferred_count": row["inferred_count"],
        "initialization_mode": row["initialization_mode"],
        "l2_norm": row["l2_norm"],
        "observed_count": row["observed_count"],
        "prototype_hash": row["prototype_hash"],
        "source_identity_count": row["source_identity_count"],
        "source_row_hash": row["source_row_hash"],
        "weight_hash": row["weight_hash"],
    }


def witness_sha256(rows: Sequence[Mapping[str, Any]], target_norm: float) -> str:
    from .classification_v2 import canonical_json, sha256_text

    body = {"rows": list(rows), "scaling_rule": SCALING_RULE, "target_norm": target_norm}
    return sha256_text(canonical_json(body))


def training_prototype_sources(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Training-split definition strings for families that are not exact-name copies."""
    grouped: dict[str, list[tuple[str, Mapping[str, Any]]]] = {family: [] for family in ACTIVE_FAMILY_VOCABULARY}
    for row in rows:
        if row.get("split") != "train":
            continue
        lineage = str(row.get("lineage") or "")
        if lineage not in grouped:
            continue
        if row.get("class") not in PROTOTYPE_WEIGHT:
            continue
        if row.get("evaluation_reserve") or row.get("held_out"):
            raise ClassificationContractError("evaluation_isolation")
        prose = _prose(row)
        if not prose or str(row.get("text") or "") != prose:
            continue
        grouped[lineage].append((normalized_text_sha256(prose), row))
    sources: dict[str, dict[str, Any]] = {}
    for family, items in grouped.items():
        if not items:
            continue
        ordered = sorted(items, key=lambda item: item[0])
        sources[family] = {
            "identities": [digest for digest, _row in ordered],
            "observed": sum(1 for _digest, row in ordered if row.get("class") == "OBSERVED"),
            "inferred": sum(1 for _digest, row in ordered if row.get("class") == "INFERRED"),
            "rows": [row for _digest, row in ordered],
        }
    return sources


def verify_witness_against_copy(mapped: Mapping[str, Any], witness: Mapping[str, Any]) -> dict[str, Any]:
    """Refuse zero or drifted rows. Exact copies must match the live warm-start head."""
    rows = witness.get("rows")
    weight = witness.get("weight")
    bias = witness.get("bias")
    if not isinstance(rows, list) or not isinstance(weight, list) or not isinstance(bias, list):
        raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "witness")
    if len(rows) != len(weight) or len(rows) != len(bias) or len(rows) != len(ACTIVE_FAMILY_VOCABULARY):
        raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "witness")
    if witness.get("witness_sha256") != witness_sha256(rows, float(witness["target_norm"])):
        raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "witness_hash")
    modes = {INITIALIZATION_EXACT, INITIALIZATION_PROTOTYPE}
    for index, (row, live) in enumerate(zip(rows, mapped["rows"])):
        if row.get("family") != live["active_family"] or row.get("initialization_mode") not in modes:
            raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", row.get("family"))
        installed = _f32_round(weight[index])
        if _f32_hash(installed) != row.get("weight_hash"):
            raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", row.get("family"))
        if row["initialization_mode"] == INITIALIZATION_EXACT:
            if live["mapping_status"] != "EXACT_COPY":
                raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", row["family"])
            if _f32_hash(_f32_round(mapped["weight"][index])) != row["weight_hash"]:
                raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "copy_mismatch")
            if _f32_hash(_f32_round((mapped["bias"][index],))) != row["bias_hash"]:
                raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "copy_mismatch")
        else:
            if live["mapping_status"] == "EXACT_COPY":
                raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "prototype_replaced_copy")
            if l2_norm(installed) == 0.0 or row.get("source_identity_count", 0) < 1:
                raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", row["family"])
            if _f32_round((bias[index],))[0] != 0.0:
                raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "bias")
    return {
        "bias": [_f32_round((value,))[0] for value in bias],
        "exact_copy_families": witness.get("exact_copy_families"),
        "prototype_families": witness.get("prototype_families"),
        "rows": rows,
        "weight": [_f32_round(vector) for vector in weight],
        "witness_sha256": witness["witness_sha256"],
    }


def assess_witness(witness: Mapping[str, Any]) -> dict[str, Any]:
    """Check a frozen witness without reloading the encoder."""
    try:
        rows = witness["rows"]
        weight = witness["weight"]
        bias = witness["bias"]
        target = float(witness["target_norm"])
        if witness.get("witness_sha256") != witness_sha256(rows, target):
            raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "witness_hash")
        if witness.get("scaling_rule") != SCALING_RULE:
            raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "scaling")
        if [row["family"] for row in rows] != list(ACTIVE_FAMILY_VOCABULARY):
            raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "order")
        builds = list(witness.get("build_sha256") or [])
        if builds != [witness["witness_sha256"], witness["witness_sha256"]]:
            raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "nondeterministic")
        source_counts = {}
        for index, row in enumerate(rows):
            mode = row["initialization_mode"]
            if mode not in {INITIALIZATION_EXACT, INITIALIZATION_PROTOTYPE}:
                raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", row["family"])
            installed = _f32_round(weight[index])
            if _f32_hash(installed) != row["weight_hash"]:
                raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", row["family"])
            if _f32_hash(_f32_round((bias[index],))) != row["bias_hash"]:
                raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", row["family"])
            if mode == INITIALIZATION_PROTOTYPE:
                if row["source_identity_count"] < 1 or l2_norm(installed) == 0.0 or bias[index] != 0.0:
                    raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", row["family"])
                if row["source_row_hash"] is not None or not row["prototype_hash"]:
                    raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", row["family"])
            else:
                if row["source_row_hash"] is None:
                    raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", row["family"])
            source_counts[row["family"]] = {
                "inferred": row["inferred_count"],
                "observed": row["observed_count"],
                "source_identity_count": row["source_identity_count"],
            }
    except (KeyError, TypeError, ValueError) as exc:
        return {"pass": False, "reason": "FAMILY_PROTOTYPE_UNAVAILABLE", "detail": str(exc)}
    return {
        "copied_rows_match": True,
        "determinism": "pass",
        "exact_copy_families": [row["family"] for row in rows if row["initialization_mode"] == INITIALIZATION_EXACT],
        "pass": True,
        "prototype_families": [row["family"] for row in rows if row["initialization_mode"] == INITIALIZATION_PROTOTYPE],
        "source_counts": source_counts,
        "target_norm": target,
        "target_norm_source": witness.get("target_norm_source"),
        "witness_sha256": witness["witness_sha256"],
    }


FUSION_ALPHA = 1.0
FUSION_BETA = 1.0
PROTO_TAU = 0.10
LAMBDA_PROTO = 0.5
HARD_NEGATIVE_COUNT = 3
HARD_NEGATIVE_MULTIPLIER = 2.0
CONFUSABLE_COSINE = 0.80
GEOMETRY_SCHEMA = "hyperlex.classification.v2.prototype_geometry.v1"
FUSION_RULE = "population_zscore(cosine/tau)+population_zscore(residual)"


def _unit(values: Sequence[float]) -> list[float]:
    vector = _finite_vector(values, "FAMILY_PROTOTYPE_UNAVAILABLE")
    norm = l2_norm(vector)
    if norm == 0.0:
        raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "zero_norm")
    return [value / norm for value in vector]


def population_standardize(values: Sequence[float]) -> list[float]:
    """Per-example z-score across families. A constant vector becomes zeros."""
    vector = _finite_vector(values, "FAMILY_PROTOTYPE_UNAVAILABLE")
    count = len(vector)
    mean = sum(vector) / count
    variance = sum((value - mean) ** 2 for value in vector) / count
    deviation = math.sqrt(variance)
    if deviation == 0.0:
        return [0.0 for _value in vector]
    return [(value - mean) / deviation for value in vector]


def fuse_family_logits(cosine: Sequence[float], residual: Sequence[float]) -> list[float]:
    """Shared alpha and beta. Standardization removes a global magnitude advantage."""
    if len(cosine) != len(residual):
        raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "fusion_width")
    proto = population_standardize(value / PROTO_TAU for value in cosine)
    learned = population_standardize(residual)
    return [FUSION_ALPHA * left + FUSION_BETA * right for left, right in zip(proto, learned)]


def cosine_matrix(vectors: Sequence[Sequence[float]]) -> list[list[float]]:
    units = [_unit(vector) for vector in vectors]
    matrix = []
    for left in units:
        matrix.append([sum(a * b for a, b in zip(left, right)) for right in units])
    return matrix


def hard_negatives(
    matrix: Sequence[Sequence[float]],
    names: Sequence[str],
    count: int = HARD_NEGATIVE_COUNT,
) -> dict[str, list[dict[str, float | str]]]:
    """Top other prototypes. Ties break by family name. No evaluation mining."""
    if len(matrix) != len(names):
        raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "similarity")
    chosen: dict[str, list[dict[str, float | str]]] = {}
    for index, name in enumerate(names):
        order = sorted(
            (
                (-float(matrix[index][other]), names[other])
                for other in range(len(names))
                if other != index
            )
        )
        chosen[name] = [
            {"cosine": -score, "family": other}
            for score, other in order[:count]
        ]
    return chosen


def confusable_pairs(
    matrix: Sequence[Sequence[float]],
    names: Sequence[str],
    threshold: float = CONFUSABLE_COSINE,
) -> list[dict[str, float | str]]:
    pairs = []
    for left in range(len(names)):
        for right in range(left + 1, len(names)):
            score = float(matrix[left][right])
            if score >= threshold:
                first, second = sorted((names[left], names[right]))
                pairs.append({"cosine": score, "left": first, "right": second})
    pairs.sort(key=lambda item: (-float(item["cosine"]), str(item["left"]), str(item["right"])))
    return pairs


def confusion_clusters(
    pairs: Sequence[Mapping[str, Any]],
    names: Sequence[str],
) -> list[list[str]]:
    parent = {name: name for name in names}

    def find(name: str) -> str:
        while parent[name] != name:
            parent[name] = parent[parent[name]]
            name = parent[name]
        return name

    for pair in pairs:
        left = find(str(pair["left"]))
        right = find(str(pair["right"]))
        parent[left] = right
    groups: dict[str, list[str]] = {}
    for name in names:
        groups.setdefault(find(name), []).append(name)
    return sorted(
        [sorted(group) for group in groups.values() if len(group) > 1],
        key=lambda group: (group[0], len(group)),
    )


def denominator_multipliers(
    names: Sequence[str],
    negatives: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[list[float]]:
    """Gold stays 1. Recorded hard negatives are multiplied. Everyone else stays 1."""
    multipliers = []
    for name in names:
        row = []
        hard = {str(item["family"]) for item in negatives.get(name, ())}
        for other in names:
            if other != name and other in hard:
                row.append(HARD_NEGATIVE_MULTIPLIER)
            else:
                row.append(1.0)
        multipliers.append(row)
    return multipliers


def prototype_contrastive_nll(
    cosine: Sequence[float],
    gold_index: int,
    multipliers: Sequence[float],
) -> float:
    """Temperature-scaled prototype NLL. The positive denominator weight is 1."""
    if len(cosine) != len(multipliers) or not 0 <= gold_index < len(cosine):
        raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "contrastive")
    logits = [float(value) / PROTO_TAU for value in cosine]
    peak = max(logits)
    total = 0.0
    for multiplier, logit in zip(multipliers, logits):
        scale = float(multiplier)
        if scale <= 0.0:
            raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "contrastive")
        total += scale * math.exp(logit - peak)
    if multipliers[gold_index] != 1.0:
        raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "gold_weight")
    return math.log(total) + peak - logits[gold_index]


def family_margin_report(
    records: Sequence[Mapping[str, Any]],
    names: Sequence[str],
) -> dict[str, float | None]:
    """Mean similarity margin, sim(gold) minus the nearest other prototype."""
    buckets: dict[str, list[float]] = {name: [] for name in names}
    index = {name: position for position, name in enumerate(names)}
    for record in records:
        gold = str(record.get("lineage") or "")
        if gold not in index:
            continue
        similarities = [float(value) for value in record["similarities"]]
        if len(similarities) != len(names):
            raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "margin")
        gold_index = index[gold]
        others = [value for position, value in enumerate(similarities) if position != gold_index]
        buckets[gold].append(similarities[gold_index] - max(others))
    return {
        name: None if not values else sum(values) / len(values)
        for name, values in buckets.items()
    }


def _markup_text(text: str) -> bool:
    raw = str(text or "").lstrip()
    return raw.startswith(("![](", "http://", "https://", "Audio")) or "Play audio" in raw


def geometry_training_sources(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Prose training strings for families that have no stored definition prototype.

    Families with definition prose keep the verified prototype vectors. This
    collector is only for the exact-copy families, whose training string is
    the row text.
    """
    from .classification_v2 import EXACT_COPY_FAMILIES
    from .classification_v2_surface import SURFACE_PROSE, surface_form

    grouped: dict[str, list[tuple[str, Mapping[str, Any]]]] = {
        family: [] for family in EXACT_COPY_FAMILIES
    }
    for row in rows:
        if row.get("split") != "train":
            continue
        lineage = str(row.get("lineage") or "")
        if lineage not in grouped or row.get("class") not in PROTOTYPE_WEIGHT:
            continue
        if row.get("evaluation_reserve") or row.get("held_out"):
            raise ClassificationContractError("evaluation_isolation")
        text = str(row.get("text") or "").strip()
        if not text or _markup_text(text) or surface_form(text) != SURFACE_PROSE:
            continue
        grouped[lineage].append((normalized_text_sha256(text), row))
    sources: dict[str, dict[str, Any]] = {}
    for family, items in grouped.items():
        if not items:
            raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", family)
        ordered = sorted(items, key=lambda item: (item[0], 0 if item[1].get("class") == "OBSERVED" else 1))
        unique = []
        seen = set()
        for digest, row in ordered:
            if digest in seen:
                continue
            seen.add(digest)
            unique.append((digest, row))
        sources[family] = {
            "identities": [digest for digest, _row in unique],
            "inferred": sum(1 for _digest, row in unique if row.get("class") == "INFERRED"),
            "observed": sum(1 for _digest, row in unique if row.get("class") == "OBSERVED"),
            "rows": [row for _digest, row in unique],
        }
    return sources


def geometry_sha256(witness: Mapping[str, Any]) -> str:
    from .classification_v2 import canonical_json, sha256_text

    body = {
        "fusion": witness["fusion"],
        "hard_negatives": witness["hard_negatives"],
        "prototype_witness_sha256": witness["witness_sha256"],
        "residual_bias_hash": witness["residual_bias_hash"],
        "residual_modes": list(witness["residual_mode"]),
        "residual_weight_hash": list(witness["residual_weight_hash"]),
        "target_norm": witness["target_norm"],
    }
    return sha256_text(canonical_json(body))


def _fusion_contract() -> dict[str, Any]:
    return {
        "alpha": FUSION_ALPHA,
        "beta": FUSION_BETA,
        "hard_negative_multiplier": HARD_NEGATIVE_MULTIPLIER,
        "lambda_proto": LAMBDA_PROTO,
        "rule": FUSION_RULE,
        "tau": PROTO_TAU,
    }


def assess_geometry_witness(
    witness: Mapping[str, Any],
    mapped: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Frozen anchors for every active family, plus the residual initialization."""
    from .classification_v2 import ACTIVE_FAMILY_VOCABULARY, EXACT_COPY_FAMILIES

    try:
        base = assess_witness(witness)
        if not base["pass"]:
            return base
        if witness.get("schema") != GEOMETRY_SCHEMA:
            raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "schema")
        if witness.get("fusion") != _fusion_contract():
            raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "fusion")
        if witness.get("geometry_sha256") != geometry_sha256(witness):
            raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "geometry_hash")
        modes = list(witness["residual_mode"])
        residual_weight = witness["residual_weight"]
        residual_bias = list(witness["residual_bias"])
        if [row["family"] for row in witness["rows"]] != list(ACTIVE_FAMILY_VOCABULARY):
            raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "order")
        if any(row["initialization_mode"] != INITIALIZATION_PROTOTYPE for row in witness["rows"]):
            raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "prototype_missing")
        if len(modes) != len(ACTIVE_FAMILY_VOCABULARY):
            raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "residual")
        weight_hashes = []
        for index, family in enumerate(ACTIVE_FAMILY_VOCABULARY):
            installed = _f32_round(residual_weight[index])
            weight_hashes.append(_f32_hash(installed))
            if modes[index] == "ZERO":
                if any(value != 0.0 for value in installed) or float(residual_bias[index]) != 0.0:
                    raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", family)
                if family in EXACT_COPY_FAMILIES:
                    raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", family)
            elif modes[index] == INITIALIZATION_EXACT:
                if family not in EXACT_COPY_FAMILIES:
                    raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", family)
                if mapped is not None:
                    live = mapped["rows"][index]
                    if live["mapping_status"] != "EXACT_COPY" or live["active_family"] != family:
                        raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", family)
                    if _f32_hash(_f32_round(mapped["weight"][index])) != weight_hashes[-1]:
                        raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "copy_mismatch")
                    if _f32_hash(_f32_round((mapped["bias"][index],))) != _f32_hash(
                        _f32_round((residual_bias[index],))
                    ):
                        raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "copy_mismatch")
            else:
                raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", family)
        if weight_hashes != list(witness["residual_weight_hash"]):
            raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "residual_hash")
        if _f32_hash(_f32_round(residual_bias)) != witness["residual_bias_hash"]:
            raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "residual_hash")
        names = list(ACTIVE_FAMILY_VOCABULARY)
        negatives = witness["hard_negatives"]
        if set(negatives) != set(names):
            raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "hard_negatives")
        for family in names:
            others = [str(item["family"]) for item in negatives[family]]
            if len(others) != HARD_NEGATIVE_COUNT or len(set(others)) != HARD_NEGATIVE_COUNT:
                raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", family)
            if family in others:
                raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", family)
    except (ClassificationContractError, KeyError, TypeError, ValueError) as exc:
        return {"pass": False, "reason": "FAMILY_PROTOTYPE_UNAVAILABLE", "detail": str(exc)}
    base["geometry_sha256"] = witness["geometry_sha256"]
    base["pass"] = True
    base["prototypes_frozen"] = True
    base["copied_rows_match"] = mapped is not None or base.get("copied_rows_match") is True
    return base


def assemble_geometry_witness(
    base_witness: Mapping[str, Any],
    encoded_exact: Mapping[str, Mapping[str, Any]],
    mapped: Mapping[str, Any],
) -> dict[str, Any]:
    """Semantic prototype for every active family. Residual rows stay separate."""
    from .classification_v2 import ACTIVE_FAMILY_VOCABULARY, EXACT_COPY_FAMILIES

    target = float(base_witness["target_norm"])
    if base_witness.get("scaling_rule") != SCALING_RULE:
        raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", "scaling")
    by_family = {row["family"]: (index, row) for index, row in enumerate(base_witness["rows"])}
    rows: list[dict[str, Any]] = []
    weight: list[list[float]] = []
    for family in ACTIVE_FAMILY_VOCABULARY:
        if family in EXACT_COPY_FAMILIES:
            payload = encoded_exact.get(family)
            if not payload:
                raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", family)
            witness = _prototype_witness(
                family,
                payload["vectors"],
                payload["weights"],
                payload["identities"],
                observed=int(payload["observed"]),
                inferred=int(payload["inferred"]),
                target_norm=target,
            )
        else:
            index, public = by_family[family]
            if public["initialization_mode"] != INITIALIZATION_PROTOTYPE:
                raise ClassificationContractError("FAMILY_PROTOTYPE_UNAVAILABLE", family)
            witness = dict(public)
            witness["weight"] = _f32_round(base_witness["weight"][index])
        rows.append(witness)
        weight.append(list(witness["weight"]))
    public = [_public_row(row) for row in rows]
    matrix = cosine_matrix(weight)
    names = list(ACTIVE_FAMILY_VOCABULARY)
    negatives = hard_negatives(matrix, names)
    residual_weight = []
    residual_bias = []
    residual_mode = []
    width = len(weight[0])
    for index, family in enumerate(names):
        if family in EXACT_COPY_FAMILIES:
            residual_weight.append(_f32_round(mapped["weight"][index]))
            residual_bias.append(_f32_round((mapped["bias"][index],))[0])
            residual_mode.append(INITIALIZATION_EXACT)
        else:
            residual_weight.append([0.0] * width)
            residual_bias.append(0.0)
            residual_mode.append("ZERO")
    witness = {
        "bias": [0.0 for _name in names],
        "exact_copy_families": list(EXACT_COPY_FAMILIES),
        "fusion": _fusion_contract(),
        "hard_negatives": negatives,
        "prototype_families": list(names),
        "residual_bias": residual_bias,
        "residual_bias_hash": _f32_hash(_f32_round(residual_bias)),
        "residual_mode": residual_mode,
        "residual_weight": residual_weight,
        "residual_weight_hash": [_f32_hash(vector) for vector in residual_weight],
        "rows": public,
        "scaling_rule": SCALING_RULE,
        "similarity": matrix,
        "confusable_pairs": confusable_pairs(matrix, names),
        "confusion_clusters": confusion_clusters(confusable_pairs(matrix, names), names),
        "target_norm": target,
        "target_norm_source": base_witness.get("target_norm_source"),
        "weight": weight,
        "witness_sha256": witness_sha256(public, target),
    }
    witness["geometry_sha256"] = geometry_sha256(witness)
    witness["schema"] = GEOMETRY_SCHEMA
    return witness
