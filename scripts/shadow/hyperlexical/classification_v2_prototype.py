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
