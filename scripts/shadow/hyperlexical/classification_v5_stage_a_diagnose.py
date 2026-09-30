"""DIAGNOSE_V5_STAGE_A_SETTLED_FAIL — read-only failure diagnosis.

Includes HYPERLEX_V5_STAGE_A_CONTROLLED_COMPARISON_V1 (matched-cohort
OBSERVED vs INFERRED). Does not train, relabel, retune thresholds, use
reserve, or move BEST.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from .classification_v2_surface import SURFACE_ATOM, SURFACE_PROSE, surface_form, word_count
from .classification_v5_stage_a import (
    EVIDENCE_LABELS,
    decide_evidence,
    evaluate_decisions,
    false_evidence_entry_rate_on_none,
    prf,
    sha256_text,
    canonical_json,
    validate_label_provenance,
)
from .classification_v5_surface_readiness_gates import (
    definition_style,
    domain_key,
    source_category,
)

DIAGNOSE_RULE = "HYPERLEX_V5_STAGE_A_DIAGNOSE_SETTLED_FAIL_V1"
CONTROLLED_RULE = "HYPERLEX_V5_STAGE_A_CONTROLLED_COMPARISON_V1"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V5-STAGE-A-001"
AUTHORIZED_DATASET_SHA = (
    "a81ca68ad3310981c60d2500a83a0989adeb967cbee6ad6dff003ed2c705efa9"
)
SELECTED_CHECKPOINT_SHA = (
    "3b1b574acceea183363b8cea41e1b7e4e13dc934bacc66deb4b3b8caeabc90a7"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"

# Diagnostic decision thresholds = sealed fail-display pair (NOT a new search).
DIAGNOSTIC_NONE_THRESHOLD = 0.50
DIAGNOSTIC_PRESENT_THRESHOLD = 0.55

LENGTH_BUCKETS = ("1-2", "3-4", "5-8", "9-16", "17-32", "33+")
LENGTH_BUCKET_INDEX = {name: index for index, name in enumerate(LENGTH_BUCKETS)}
SIM_BUCKETS = ("lt_0.70", "0.70-0.80", "0.80-0.90", "0.90-0.95", "ge_0.95")
SIM_BUCKET_INDEX = {name: index for index, name in enumerate(SIM_BUCKETS)}

ERROR_COHORTS = (
    "ORDINARY_DOMAIN_FALSE_PRESENT",
    "OTHER_NONE_FALSE_PRESENT",
    "PRESENT_FALSE_NONE",
    "PRESENT_FALSE_UNCERTAIN",
    "UNCERTAIN_MISCLASSIFIED",
)

PROVENANCE_SUSPICION = (
    "LABEL_PROVENANCE_CLEAN",
    "LABEL_SEMANTICS_QUESTIONABLE",
    "SOURCE_ASSERTION_WEAK",
    "PAIR_CONTRAST_WEAK",
    "NEGATIVE_EXCLUSION_WEAK",
)

PRIMARY_DIAGNOSES = (
    "DATA_LABEL_QUALITY_FAILURE",
    "SOURCE_DOMAIN_SHIFT_FAILURE",
    "OBSERVED_ACQUISITION_FAILURE",
    "REPRESENTATION_FAILURE",
    "RESIDUAL_PRESENT_RECALL_FAILURE",
    "MIXED_STAGE_A_FAILURE",
)


def token_length_bucket(text: str) -> str:
    n = word_count(text)
    if n <= 2:
        return "1-2"
    if n <= 4:
        return "3-4"
    if n <= 8:
        return "5-8"
    if n <= 16:
        return "9-16"
    if n <= 32:
        return "17-32"
    return "33+"


def similarity_bucket(value: float | None) -> str:
    if value is None or math.isnan(float(value)):
        return "lt_0.70"
    score = float(value)
    if score < 0.70:
        return "lt_0.70"
    if score < 0.80:
        return "0.70-0.80"
    if score < 0.90:
        return "0.80-0.90"
    if score < 0.95:
        return "0.90-0.95"
    return "ge_0.95"


def source_family(row: Mapping[str, Any]) -> str:
    """Canonical source family from existing fields (no post-hoc invention)."""
    return source_category(row)


def topic_domain_key(row: Mapping[str, Any]) -> str:
    return domain_key(row)


def definition_style_label(text: str) -> str:
    return "DEFINITION" if definition_style(text) else "NON_DEFINITION"


def atom_prose(text: str) -> str:
    form = surface_form(text)
    if form == SURFACE_ATOM:
        return "ATOM"
    if form == SURFACE_PROSE:
        return "PROSE"
    return str(form)


def error_cohort(gold: str, pred: str, subtype: str) -> str | None:
    if gold == "NO_EVIDENCE" and pred == "EVIDENCE_PRESENT":
        if subtype == "ORDINARY_DOMAIN_NONE":
            return "ORDINARY_DOMAIN_FALSE_PRESENT"
        return "OTHER_NONE_FALSE_PRESENT"
    if gold == "EVIDENCE_PRESENT" and pred == "NO_EVIDENCE":
        return "PRESENT_FALSE_NONE"
    if gold == "EVIDENCE_PRESENT" and pred == "UNCERTAIN":
        return "PRESENT_FALSE_UNCERTAIN"
    if gold == "UNCERTAIN" and pred != "UNCERTAIN":
        return "UNCERTAIN_MISCLASSIFIED"
    return None


def decide_diagnostic(evidence_score: float) -> str:
    return decide_evidence(
        float(evidence_score),
        none_threshold=DIAGNOSTIC_NONE_THRESHOLD,
        present_threshold=DIAGNOSTIC_PRESENT_THRESHOLD,
    )


def l2_normalize(vec: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(float(x) * float(x) for x in vec)) or 1.0
    return [float(x) / norm for x in vec]


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(float(x) * float(y) for x, y in zip(a, b))


def nearest_label_similarity(
    index: int,
    embeddings: Sequence[Sequence[float]],
    labels: Sequence[str],
    target_label: str,
) -> float | None:
    best = None
    query = embeddings[index]
    for j, label in enumerate(labels):
        if j == index or label != target_label:
            continue
        score = cosine(query, embeddings[j])
        if best is None or score > best:
            best = score
    return best


def attach_row_features(
    rows: Sequence[Mapping[str, Any]],
    *,
    provenance_by_id: Mapping[str, Mapping[str, Any]],
    embeddings: Sequence[Sequence[float]] | None = None,
    probs: Sequence[Mapping[str, float]] | None = None,
    decisions: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    labels = [str(row["evidence_label"]) for row in rows]
    norms = None
    if embeddings is not None:
        norms = [l2_normalize(vec) for vec in embeddings]
    enriched = []
    for index, row in enumerate(rows):
        text = str(row["text"])
        identity = str(row["identity"])
        gold = labels[index]
        pred = decisions[index] if decisions is not None else gold
        prov = provenance_by_id.get(identity) or {}
        label_prov = prov.get("label_provenance") or {}
        pos_sim = None
        none_sim = None
        if norms is not None:
            pos_sim = nearest_label_similarity(index, norms, labels, "EVIDENCE_PRESENT")
            none_sim = nearest_label_similarity(index, norms, labels, "NO_EVIDENCE")
        margin = None
        if pos_sim is not None and none_sim is not None:
            margin = float(pos_sim) - float(none_sim)
        item = {
            "ATOM_PROSE": atom_prose(text),
            "active_family_support": list(row.get("active_family_support") or []),
            "decision": pred,
            "definition_style": definition_style_label(text),
            "embeddings_index": index,
            "error_cohort": error_cohort(gold, pred, str(row["evidence_subtype"])),
            "evidence_label": gold,
            "evidence_subtype": str(row["evidence_subtype"]),
            "identity": identity,
            "label_authority": str(label_prov.get("authority") or "MISSING"),
            "label_derivation": str(label_prov.get("derivation") or "MISSING"),
            "label_provenance": label_prov,
            "mean_probs": dict(probs[index]) if probs is not None else None,
            "nearest_none_similarity": none_sim,
            "nearest_positive_similarity": pos_sim,
            "pair_group_id": row.get("pair_group_id"),
            "paired_positive_identity": row.get("paired_positive_identity"),
            "positive_minus_none_margin": margin,
            "positive_neighbor_similarity_bucket": similarity_bucket(pos_sim),
            "provenance": str(row.get("provenance") or "UNKNOWN"),
            "required_evidence_present": row.get("required_evidence_present"),
            "reviewer_state": str(label_prov.get("reviewer_state") or "MISSING"),
            "rule_id": str(label_prov.get("rule_id") or "MISSING"),
            "source_family": source_family(row),
            "source_url": row.get("source_url"),
            "text": text,
            "token_length_bucket": token_length_bucket(text),
            "topic_domain": topic_domain_key(row),
            "word_count": word_count(text),
        }
        enriched.append(item)
    return enriched


def build_error_cohorts(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    cohorts: dict[str, list[dict[str, Any]]] = {name: [] for name in ERROR_COHORTS}
    for row in rows:
        name = row.get("error_cohort")
        if not name:
            continue
        cohorts[str(name)].append(
            {
                "ATOM_PROSE": row["ATOM_PROSE"],
                "identity": row["identity"],
                "label_authority": row["label_authority"],
                "label_derivation": row["label_derivation"],
                "provenance": row["provenance"],
                "rule_id": row["rule_id"],
                "source_family": row["source_family"],
                "subtype": row["evidence_subtype"],
                "token_length_bucket": row["token_length_bucket"],
                "topic_domain": row["topic_domain"],
            }
        )
    summary = {}
    for name in ERROR_COHORTS:
        items = cohorts[name]
        summary[name] = {
            "count": len(items),
            "by_ATOM_PROSE": dict(Counter(i["ATOM_PROSE"] for i in items)),
            "by_label_authority": dict(Counter(i["label_authority"] for i in items)),
            "by_label_derivation": dict(Counter(i["label_derivation"] for i in items)),
            "by_provenance": dict(Counter(i["provenance"] for i in items)),
            "by_rule_id": dict(Counter(i["rule_id"] for i in items)),
            "by_source_family": dict(Counter(i["source_family"] for i in items).most_common(12)),
            "by_subtype": dict(Counter(i["subtype"] for i in items)),
            "by_token_length_bucket": dict(
                Counter(i["token_length_bucket"] for i in items)
            ),
            "by_topic_domain": dict(Counter(i["topic_domain"] for i in items).most_common(12)),
            "identities_sample": [i["identity"] for i in items[:25]],
        }
    return summary


def metrics_for_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "EVIDENCE_PRESENT_recall": None,
            "NO_EVIDENCE_recall": None,
            "UNCERTAIN_recall": None,
            "false_entry_rate": None,
            "mean_P_NONE": None,
            "mean_P_PRESENT": None,
            "mean_P_UNCERTAIN": None,
            "n": 0,
        }
    golds = [str(r["evidence_label"]) for r in rows]
    preds = [str(r["decision"]) for r in rows]
    by_label = {label: prf(golds, preds, label) for label in EVIDENCE_LABELS}
    probs = [r.get("mean_probs") or {} for r in rows]
    return {
        "EVIDENCE_PRESENT_recall": by_label["EVIDENCE_PRESENT"]["recall"],
        "NO_EVIDENCE_recall": by_label["NO_EVIDENCE"]["recall"],
        "UNCERTAIN_recall": by_label["UNCERTAIN"]["recall"],
        "false_entry_rate": false_evidence_entry_rate_on_none(golds, preds),
        "mean_P_NONE": sum(float(p.get("NO_EVIDENCE") or 0.0) for p in probs) / len(rows),
        "mean_P_PRESENT": sum(float(p.get("EVIDENCE_PRESENT") or 0.0) for p in probs)
        / len(rows),
        "mean_P_UNCERTAIN": sum(float(p.get("UNCERTAIN") or 0.0) for p in probs)
        / len(rows),
        "n": len(rows),
    }


def exact_strata_key(row: Mapping[str, Any]) -> tuple:
    return (
        row["evidence_label"],
        row["evidence_subtype"],
        row["ATOM_PROSE"],
        row["token_length_bucket"],
        row["definition_style"],
    )


def controlled_comparison(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    observed = [r for r in rows if r["provenance"] == "OBSERVED"]
    inferred = [r for r in rows if r["provenance"] == "INFERRED"]
    raw = {
        "INFERRED": metrics_for_rows(inferred),
        "OBSERVED": metrics_for_rows(observed),
    }
    raw_deltas = {
        "EVIDENCE_PRESENT_recall": _delta(
            raw["OBSERVED"]["EVIDENCE_PRESENT_recall"],
            raw["INFERRED"]["EVIDENCE_PRESENT_recall"],
        ),
        "NO_EVIDENCE_recall": _delta(
            raw["OBSERVED"]["NO_EVIDENCE_recall"], raw["INFERRED"]["NO_EVIDENCE_recall"]
        ),
        "UNCERTAIN_recall": _delta(
            raw["OBSERVED"]["UNCERTAIN_recall"], raw["INFERRED"]["UNCERTAIN_recall"]
        ),
        "false_evidence_entry_rate": _delta(
            raw["OBSERVED"]["false_entry_rate"], raw["INFERRED"]["false_entry_rate"]
        ),
        "mean_P_EVIDENCE_PRESENT": _delta(
            raw["OBSERVED"]["mean_P_PRESENT"], raw["INFERRED"]["mean_P_PRESENT"]
        ),
    }

    # Exact strata with support floors.
    by_key: dict[tuple, dict[str, list]] = defaultdict(lambda: {"OBSERVED": [], "INFERRED": []})
    for row in rows:
        if row["provenance"] not in {"OBSERVED", "INFERRED"}:
            continue
        by_key[exact_strata_key(row)][row["provenance"]].append(row)
    strata = []
    covered_obs = covered_inf = 0
    for key, groups in sorted(by_key.items(), key=lambda item: canonical_json(list(item[0]))):
        n_obs = len(groups["OBSERVED"])
        n_inf = len(groups["INFERRED"])
        if n_obs < 5 or n_inf < 5:
            continue
        m_obs = metrics_for_rows(groups["OBSERVED"])
        m_inf = metrics_for_rows(groups["INFERRED"])
        weight = n_obs + n_inf
        strata.append(
            {
                "key": {
                    "ATOM_PROSE": key[2],
                    "definition_style": key[4],
                    "evidence_subtype": key[1],
                    "gate_label": key[0],
                    "token_length_bucket": key[3],
                },
                "n_inferred": n_inf,
                "n_observed": n_obs,
                "metrics_inferred": m_inf,
                "metrics_observed": m_obs,
                "weight": weight,
            }
        )
        covered_obs += n_obs
        covered_inf += n_inf
    strata_coverage = {
        "n_inferred_covered": covered_inf,
        "n_observed_covered": covered_obs,
        "n_strata": len(strata),
        "coverage_observed": covered_obs / max(1, len(observed)),
        "coverage_inferred": covered_inf / max(1, len(inferred)),
        "coverage_union": (covered_obs + covered_inf)
        / max(1, len(observed) + len(inferred)),
    }
    controlled_from_strata = _weighted_delta(strata)

    # Extended NN matching for unmatched OBSERVED.
    matched_obs_ids = set()
    for stratum in strata:
        key = (
            stratum["key"]["gate_label"],
            stratum["key"]["evidence_subtype"],
            stratum["key"]["ATOM_PROSE"],
            stratum["key"]["token_length_bucket"],
            stratum["key"]["definition_style"],
        )
        for row in by_key[key]["OBSERVED"]:
            matched_obs_ids.add(row["identity"])
    unmatched_obs = [r for r in observed if r["identity"] not in matched_obs_ids]
    available_inf = {
        r["identity"]: r
        for r in inferred
        if r["identity"]
        not in {
            x["identity"]
            for s in strata
            for x in by_key[
                (
                    s["key"]["gate_label"],
                    s["key"]["evidence_subtype"],
                    s["key"]["ATOM_PROSE"],
                    s["key"]["token_length_bucket"],
                    s["key"]["definition_style"],
                )
            ]["INFERRED"]
        }
    }
    # Allow matching against all INFERRED not yet used in pairs; start with all INFERRED.
    pool = {r["identity"]: r for r in inferred}
    used_inf: set[str] = set()
    pairs = []
    for obs in sorted(unmatched_obs, key=lambda r: r["identity"]):
        best = None
        best_dist = None
        for inf in pool.values():
            if inf["identity"] in used_inf:
                continue
            if not (
                obs["evidence_label"] == inf["evidence_label"]
                and obs["evidence_subtype"] == inf["evidence_subtype"]
                and obs["ATOM_PROSE"] == inf["ATOM_PROSE"]
                and obs["definition_style"] == inf["definition_style"]
            ):
                continue
            dist = _match_distance(obs, inf)
            if dist > 3:
                continue
            cand = (dist, inf["identity"], inf)
            if (
                best is None
                or cand[0] < best_dist
                or (cand[0] == best_dist and cand[1] < best[1])
            ):
                best = cand
                best_dist = cand[0]
        if best is None:
            continue
        used_inf.add(best[1])
        pairs.append({"distance": best[0], "inferred": best[2], "observed": obs})

    # Combine exact-strata synthetic pairs (all obs/inf in stratum contribute via
    # support-weighted means) with NN pairs for controlled pair bootstrap.
    pair_units = []
    for stratum in strata:
        key = (
            stratum["key"]["gate_label"],
            stratum["key"]["evidence_subtype"],
            stratum["key"]["ATOM_PROSE"],
            stratum["key"]["token_length_bucket"],
            stratum["key"]["definition_style"],
        )
        obs_list = by_key[key]["OBSERVED"]
        inf_list = by_key[key]["INFERRED"]
        # Deterministic zip of min length as stratum pair units.
        for obs, inf in zip(
            sorted(obs_list, key=lambda r: r["identity"]),
            sorted(inf_list, key=lambda r: r["identity"]),
        ):
            pair_units.append({"distance": 0, "inferred": inf, "observed": obs})
    pair_units.extend(pairs)

    matched_n = len(pair_units)
    match_coverage = matched_n / max(1, len(observed))
    controlled = _pair_deltas(pair_units)
    bootstrap = bootstrap_controlled_deltas(pair_units, seed=42, replicates=2000)

    decomposition = sequential_confounding_decomposition(rows)
    source_sensitivity = source_domain_sensitivity(rows)
    authority_sensitivity = label_authority_sensitivity(rows)

    interpretation = interpret_controlled_gap(
        raw_deltas=raw_deltas,
        controlled_deltas=controlled,
        coverage=match_coverage,
    )

    return {
        "rule": CONTROLLED_RULE,
        "raw": raw,
        "raw_deltas": raw_deltas,
        "exact_strata": {
            "coverage": strata_coverage,
            "controlled_deltas": controlled_from_strata,
            "n_strata": len(strata),
        },
        "matched_pairs": {
            "coverage": match_coverage,
            "matched_n": matched_n,
            "nn_pairs": len(pairs),
            "controlled_deltas": controlled,
        },
        "bootstrap_95": bootstrap,
        "sequential_confounding_decomposition": decomposition,
        "source_domain_sensitivity": source_sensitivity,
        "label_authority_sensitivity": authority_sensitivity,
        "interpretation": interpretation,
        "provenance_plausible_failure_driver": interpretation["state"]
        in {"PROVENANCE_GAP_PERSISTS", "PROVENANCE_GAP_PARTIALLY_EXPLAINED"},
    }


def _delta(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return float(a) - float(b)


def _weighted_delta(strata: Sequence[Mapping[str, Any]]) -> dict[str, float | None]:
    if not strata:
        return {
            "EVIDENCE_PRESENT_recall": None,
            "NO_EVIDENCE_recall": None,
            "UNCERTAIN_recall": None,
            "false_evidence_entry_rate": None,
            "mean_P_EVIDENCE_PRESENT": None,
        }
    total_w = sum(int(s["weight"]) for s in strata) or 1
    keys = [
        ("false_entry_rate", "false_evidence_entry_rate"),
        ("EVIDENCE_PRESENT_recall", "EVIDENCE_PRESENT_recall"),
        ("NO_EVIDENCE_recall", "NO_EVIDENCE_recall"),
        ("UNCERTAIN_recall", "UNCERTAIN_recall"),
        ("mean_P_PRESENT", "mean_P_EVIDENCE_PRESENT"),
    ]
    out: dict[str, float | None] = {}
    for src, dst in keys:
        acc = 0.0
        for stratum in strata:
            o = stratum["metrics_observed"].get(src)
            i = stratum["metrics_inferred"].get(src)
            if o is None or i is None:
                continue
            acc += int(stratum["weight"]) * (float(o) - float(i))
        out[dst] = acc / total_w
    return out


def _match_distance(obs: Mapping[str, Any], inf: Mapping[str, Any]) -> int:
    dist = 0
    dist += abs(
        LENGTH_BUCKET_INDEX[obs["token_length_bucket"]]
        - LENGTH_BUCKET_INDEX[inf["token_length_bucket"]]
    )
    dist += abs(
        SIM_BUCKET_INDEX[obs["positive_neighbor_similarity_bucket"]]
        - SIM_BUCKET_INDEX[inf["positive_neighbor_similarity_bucket"]]
    )
    for key in (
        "topic_domain",
        "source_family",
        "label_authority",
        "label_derivation",
    ):
        if obs[key] != inf[key]:
            dist += 1
    return dist


def _pair_deltas(pairs: Sequence[Mapping[str, Any]]) -> dict[str, float | None]:
    if not pairs:
        return {
            "EVIDENCE_PRESENT_recall": None,
            "NO_EVIDENCE_recall": None,
            "UNCERTAIN_recall": None,
            "false_evidence_entry_rate": None,
            "mean_P_EVIDENCE_PRESENT": None,
            "matched_n": 0,
        }
    obs_rows = [p["observed"] for p in pairs]
    inf_rows = [p["inferred"] for p in pairs]
    m_obs = metrics_for_rows(obs_rows)
    m_inf = metrics_for_rows(inf_rows)
    return {
        "EVIDENCE_PRESENT_recall": _delta(
            m_obs["EVIDENCE_PRESENT_recall"], m_inf["EVIDENCE_PRESENT_recall"]
        ),
        "NO_EVIDENCE_recall": _delta(
            m_obs["NO_EVIDENCE_recall"], m_inf["NO_EVIDENCE_recall"]
        ),
        "UNCERTAIN_recall": _delta(m_obs["UNCERTAIN_recall"], m_inf["UNCERTAIN_recall"]),
        "false_evidence_entry_rate": _delta(
            m_obs["false_entry_rate"], m_inf["false_entry_rate"]
        ),
        "mean_P_EVIDENCE_PRESENT": _delta(
            m_obs["mean_P_PRESENT"], m_inf["mean_P_PRESENT"]
        ),
        "matched_n": len(pairs),
        "metrics_inferred": m_inf,
        "metrics_observed": m_obs,
    }


def bootstrap_controlled_deltas(
    pairs: Sequence[Mapping[str, Any]],
    *,
    seed: int,
    replicates: int,
) -> dict[str, Any]:
    if not pairs:
        return {"replicates": 0, "intervals": {}}
    rng = random.Random(seed)
    keys = [
        "false_evidence_entry_rate",
        "EVIDENCE_PRESENT_recall",
        "NO_EVIDENCE_recall",
        "UNCERTAIN_recall",
        "mean_P_EVIDENCE_PRESENT",
    ]
    samples: dict[str, list[float]] = {key: [] for key in keys}
    n = len(pairs)
    for _ in range(replicates):
        draw = [pairs[rng.randrange(n)] for _ in range(n)]
        deltas = _pair_deltas(draw)
        for key in keys:
            value = deltas.get(key)
            if value is not None:
                samples[key].append(float(value))
    intervals = {}
    for key, values in samples.items():
        if not values:
            intervals[key] = None
            continue
        values = sorted(values)
        lo = values[int(0.025 * (len(values) - 1))]
        hi = values[int(0.975 * (len(values) - 1))]
        intervals[key] = {"ci95_high": hi, "ci95_low": lo, "n": len(values)}
    return {"replicates": replicates, "seed": seed, "intervals": intervals}


def _subset_delta(
    rows: Sequence[Mapping[str, Any]], predicate
) -> dict[str, float | None]:
    kept = [r for r in rows if predicate(r)]
    obs = [r for r in kept if r["provenance"] == "OBSERVED"]
    inf = [r for r in kept if r["provenance"] == "INFERRED"]
    return {
        "EVIDENCE_PRESENT_recall": _delta(
            metrics_for_rows(obs)["EVIDENCE_PRESENT_recall"],
            metrics_for_rows(inf)["EVIDENCE_PRESENT_recall"],
        ),
        "false_evidence_entry_rate": _delta(
            metrics_for_rows(obs)["false_entry_rate"],
            metrics_for_rows(inf)["false_entry_rate"],
        ),
        "n_inferred": len(inf),
        "n_observed": len(obs),
    }


def sequential_confounding_decomposition(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Descriptive residual deltas after successive exact matches on more covariates."""

    def stage(keys: Sequence[str]) -> dict[str, Any]:
        groups: dict[tuple, dict[str, list]] = defaultdict(
            lambda: {"OBSERVED": [], "INFERRED": []}
        )
        for row in rows:
            if row["provenance"] not in {"OBSERVED", "INFERRED"}:
                continue
            key = tuple(row[k] for k in keys)
            groups[key][row["provenance"]].append(row)
        strata = []
        for key, parts in groups.items():
            if len(parts["OBSERVED"]) < 1 or len(parts["INFERRED"]) < 1:
                continue
            strata.append(
                {
                    "metrics_inferred": metrics_for_rows(parts["INFERRED"]),
                    "metrics_observed": metrics_for_rows(parts["OBSERVED"]),
                    "weight": len(parts["OBSERVED"]) + len(parts["INFERRED"]),
                }
            )
        return {
            "controlled_deltas": _weighted_delta(strata),
            "n_strata": len(strata),
            "keys": list(keys),
        }

    return {
        "A_subtype": stage(["evidence_label", "evidence_subtype"]),
        "B_plus_surface": stage(
            ["evidence_label", "evidence_subtype", "ATOM_PROSE"]
        ),
        "C_plus_length_style": stage(
            [
                "evidence_label",
                "evidence_subtype",
                "ATOM_PROSE",
                "token_length_bucket",
                "definition_style",
            ]
        ),
        "D_plus_source_domain": stage(
            [
                "evidence_label",
                "evidence_subtype",
                "ATOM_PROSE",
                "token_length_bucket",
                "definition_style",
                "source_family",
                "topic_domain",
            ]
        ),
        "E_plus_label_provenance": stage(
            [
                "evidence_label",
                "evidence_subtype",
                "ATOM_PROSE",
                "token_length_bucket",
                "definition_style",
                "source_family",
                "topic_domain",
                "label_authority",
                "label_derivation",
            ]
        ),
        "F_plus_similarity": stage(
            [
                "evidence_label",
                "evidence_subtype",
                "ATOM_PROSE",
                "token_length_bucket",
                "definition_style",
                "source_family",
                "topic_domain",
                "label_authority",
                "label_derivation",
                "positive_neighbor_similarity_bucket",
            ]
        ),
    }


def source_domain_sensitivity(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    base = controlled_comparison_light(rows)
    base_gap = base["false_evidence_entry_rate"]
    flags = []
    leave_one = {}
    sources = Counter(r["source_family"] for r in rows)
    domains = Counter(r["topic_domain"] for r in rows)
    for source, support in sources.items():
        if support < 20:
            continue
        delta = controlled_comparison_light(
            [r for r in rows if r["source_family"] != source]
        )["false_evidence_entry_rate"]
        leave_one[f"exclude_source:{source}"] = {
            "controlled_false_entry_delta": delta,
            "support": support,
        }
        if base_gap and delta is not None and abs(delta) <= 0.5 * abs(base_gap):
            flags.append({"flag": "SOURCE_DRIVEN", "excluded": source})
    for domain, support in domains.items():
        if support < 20:
            continue
        delta = controlled_comparison_light(
            [r for r in rows if r["topic_domain"] != domain]
        )["false_evidence_entry_rate"]
        leave_one[f"exclude_domain:{domain}"] = {
            "controlled_false_entry_delta": delta,
            "support": support,
        }
        if base_gap and delta is not None and abs(delta) <= 0.5 * abs(base_gap):
            flags.append({"flag": "SOURCE_DRIVEN", "excluded": domain})
    return {
        "baseline_controlled_false_entry_delta": base_gap,
        "flags": flags,
        "leave_one_out": leave_one,
    }


def controlled_comparison_light(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Exact-strata weighted false-entry / PRESENT deltas only (for sensitivity)."""
    groups: dict[tuple, dict[str, list]] = defaultdict(
        lambda: {"OBSERVED": [], "INFERRED": []}
    )
    for row in rows:
        if row["provenance"] not in {"OBSERVED", "INFERRED"}:
            continue
        groups[exact_strata_key(row)][row["provenance"]].append(row)
    strata = []
    for parts in groups.values():
        if len(parts["OBSERVED"]) < 5 or len(parts["INFERRED"]) < 5:
            continue
        strata.append(
            {
                "metrics_inferred": metrics_for_rows(parts["INFERRED"]),
                "metrics_observed": metrics_for_rows(parts["OBSERVED"]),
                "weight": len(parts["OBSERVED"]) + len(parts["INFERRED"]),
            }
        )
    deltas = _weighted_delta(strata)
    return {
        "EVIDENCE_PRESENT_recall": deltas["EVIDENCE_PRESENT_recall"],
        "false_evidence_entry_rate": deltas["false_evidence_entry_rate"],
        "n_strata": len(strata),
    }


def label_authority_sensitivity(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    settled = controlled_comparison_light(
        [r for r in rows if r.get("reviewer_state") == "SETTLED"]
    )
    high = controlled_comparison_light(
        [
            r
            for r in rows
            if r.get("label_authority") in {"HUMAN_SETTLED", "SOURCE_ASSERTED"}
        ]
    )
    flags = []
    base = controlled_comparison_light(rows)
    for name, result in ("SETTLED", settled), ("HUMAN_OR_SOURCE_ASSERTED", high):
        gap = result["false_evidence_entry_rate"]
        if (
            base["false_evidence_entry_rate"]
            and gap is not None
            and abs(gap) < 0.2 * abs(base["false_evidence_entry_rate"])
        ):
            flags.append("LABEL_AUTHORITY_CONFOUNDED")
            break
        if gap is None and result["n_strata"] == 0:
            flags.append(f"INSUFFICIENT_SUPPORT_{name}")
    return {
        "HUMAN_OR_SOURCE_ASSERTED": high,
        "SETTLED": settled,
        "flags": flags,
    }


def interpret_controlled_gap(
    *,
    raw_deltas: Mapping[str, float | None],
    controlled_deltas: Mapping[str, Any],
    coverage: float,
) -> dict[str, Any]:
    raw = raw_deltas.get("false_evidence_entry_rate")
    controlled = controlled_deltas.get("false_evidence_entry_rate")
    if coverage < 0.60:
        state = "INSUFFICIENT_MATCHED_SUPPORT"
    elif raw is None or controlled is None or abs(raw) < 1e-12:
        state = "PROVENANCE_GAP_EXPLAINED_BY_DISTRIBUTION"
    else:
        retain = abs(controlled) / abs(raw)
        same_dir = (controlled > 0 and raw > 0) or (controlled < 0 and raw < 0)
        if retain >= 0.50 and same_dir:
            state = "PROVENANCE_GAP_PERSISTS"
        elif retain < 0.20:
            state = "PROVENANCE_GAP_EXPLAINED_BY_DISTRIBUTION"
        else:
            state = "PROVENANCE_GAP_PARTIALLY_EXPLAINED"
    return {
        "controlled_false_entry_delta": controlled,
        "coverage": coverage,
        "raw_false_entry_delta": raw,
        "retention_fraction": (
            None
            if raw in (None, 0) or controlled is None
            else abs(controlled) / abs(raw)
        ),
        "state": state,
    }


def ordinary_domain_audit(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ordinary = [r for r in rows if r["evidence_subtype"] == "ORDINARY_DOMAIN_NONE"]
    buckets = {
        "UNCERTAIN": [r for r in ordinary if r["decision"] == "UNCERTAIN"],
        "correct_NONE": [
            r
            for r in ordinary
            if r["decision"] == "NO_EVIDENCE" and r["evidence_label"] == "NO_EVIDENCE"
        ],
        "false_PRESENT": [
            r
            for r in ordinary
            if r["decision"] == "EVIDENCE_PRESENT"
            and r["evidence_label"] == "NO_EVIDENCE"
        ],
    }

    def profile(items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        if not items:
            return {"n": 0}
        return {
            "n": len(items),
            "by_ATOM_PROSE": dict(Counter(r["ATOM_PROSE"] for r in items)),
            "by_definition_style": dict(Counter(r["definition_style"] for r in items)),
            "by_label_authority": dict(Counter(r["label_authority"] for r in items)),
            "by_label_derivation": dict(Counter(r["label_derivation"] for r in items)),
            "by_provenance": dict(Counter(r["provenance"] for r in items)),
            "by_source_family": dict(
                Counter(r["source_family"] for r in items).most_common(15)
            ),
            "by_token_length_bucket": dict(
                Counter(r["token_length_bucket"] for r in items)
            ),
            "by_topic_domain": dict(
                Counter(r["topic_domain"] for r in items).most_common(15)
            ),
            "mean_P_PRESENT": sum(
                float((r.get("mean_probs") or {}).get("EVIDENCE_PRESENT") or 0.0)
                for r in items
            )
            / len(items),
            "mean_positive_neighbor_sim": _mean(
                [r.get("nearest_positive_similarity") for r in items]
            ),
            "paired_fraction": sum(
                1 for r in items if r.get("paired_positive_identity") or r.get("pair_group_id")
            )
            / len(items),
        }

    false_present = buckets["false_PRESENT"]
    ranked = sorted(
        false_present,
        key=lambda r: (
            -float((r.get("mean_probs") or {}).get("EVIDENCE_PRESENT") or 0.0),
            r["identity"],
        ),
    )
    highest = [
        {
            "P_EVIDENCE_PRESENT": (r.get("mean_probs") or {}).get("EVIDENCE_PRESENT"),
            "identity": r["identity"],
            "label_authority": r["label_authority"],
            "label_derivation": r["label_derivation"],
            "nearest_positive_similarity": r.get("nearest_positive_similarity"),
            "provenance": r["provenance"],
            "source_family": r["source_family"],
            "text": r["text"][:180],
            "topic_domain": r["topic_domain"],
        }
        for r in ranked[:30]
    ]
    return {
        "n_ordinary_domain_none": len(ordinary),
        "profiles": {name: profile(items) for name, items in buckets.items()},
        "highest_confidence_false_PRESENT": highest,
    }


def classify_provenance_suspicion(
    row: Mapping[str, Any],
    surface_row: Mapping[str, Any],
) -> str:
    prov = row.get("label_provenance") or {}
    errors = validate_label_provenance(surface_row, prov) if prov else ["missing"]
    if errors:
        return "LABEL_SEMANTICS_QUESTIONABLE"
    authority = prov.get("authority")
    derivation = prov.get("derivation")
    if authority == "SOURCE_ASSERTED" and not surface_row.get("source_url"):
        return "SOURCE_ASSERTION_WEAK"
    if derivation == "PAIRWISE_CONTRAST" and not (
        surface_row.get("pair_group_id") or surface_row.get("paired_positive_identity")
    ):
        return "PAIR_CONTRAST_WEAK"
    if derivation == "NEGATIVE_EXCLUSION":
        basis = prov.get("evidence_basis") or []
        has_reason = any(
            item.get("type") == "EXCLUSION_RULE"
            and (item.get("exclusion_reason_codes") or item.get("reference"))
            for item in basis
        )
        if not has_reason:
            return "NEGATIVE_EXCLUSION_WEAK"
        # Ordinary-domain OBSERVED NONE with only generic exclusion is weak if
        # model strongly believes PRESENT (semantics questionable, not invalid).
        p_present = float((row.get("mean_probs") or {}).get("EVIDENCE_PRESENT") or 0.0)
        if (
            surface_row.get("evidence_subtype") == "ORDINARY_DOMAIN_NONE"
            and surface_row.get("provenance") == "OBSERVED"
            and p_present >= 0.80
        ):
            return "LABEL_SEMANTICS_QUESTIONABLE"
    return "LABEL_PROVENANCE_CLEAN"


def label_provenance_audit(
    enriched: Sequence[Mapping[str, Any]],
    surface_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    mis_obs = [
        r
        for r in enriched
        if r["provenance"] == "OBSERVED" and r["evidence_label"] != r["decision"]
    ]
    classifications = Counter()
    samples: dict[str, list] = defaultdict(list)
    for row in mis_obs:
        surface = surface_by_id[row["identity"]]
        label = classify_provenance_suspicion(row, surface)
        classifications[label] += 1
        if len(samples[label]) < 15:
            samples[label].append(
                {
                    "identity": row["identity"],
                    "decision": row["decision"],
                    "evidence_label": row["evidence_label"],
                    "evidence_subtype": row["evidence_subtype"],
                    "label_authority": row["label_authority"],
                    "label_derivation": row["label_derivation"],
                    "rule_id": row["rule_id"],
                }
            )
    return {
        "n_misclassified_OBSERVED": len(mis_obs),
        "classifications": dict(classifications),
        "samples": dict(samples),
    }


def source_domain_error_table(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    def cohort_metrics(items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        m = metrics_for_rows(items)
        return {
            "EVIDENCE_PRESENT_recall": m["EVIDENCE_PRESENT_recall"],
            "false_entry_rate": m["false_entry_rate"],
            "n": m["n"],
            "flag": (
                (m["n"] >= 20)
                and (
                    (m["false_entry_rate"] is not None and m["false_entry_rate"] > 0.10)
                    or (
                        m["EVIDENCE_PRESENT_recall"] is not None
                        and m["EVIDENCE_PRESENT_recall"] < 0.60
                    )
                )
            ),
        }

    by_source: dict[str, list] = defaultdict(list)
    by_domain: dict[str, list] = defaultdict(list)
    for row in rows:
        by_source[row["source_family"]].append(row)
        by_domain[row["topic_domain"]].append(row)
    source_table = {
        name: cohort_metrics(items)
        for name, items in sorted(by_source.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    }
    domain_table = {
        name: cohort_metrics(items)
        for name, items in sorted(by_domain.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    }
    flagged = {
        "domains": {k: v for k, v in domain_table.items() if v["flag"]},
        "sources": {k: v for k, v in source_table.items() if v["flag"]},
    }
    return {"by_domain": domain_table, "by_source": source_table, "flagged": flagged}


def representation_diagnostics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    cohorts = {
        "ALL": list(rows),
        "INFERRED": [r for r in rows if r["provenance"] == "INFERRED"],
        "OBSERVED": [r for r in rows if r["provenance"] == "OBSERVED"],
        "ORDINARY_DOMAIN_NONE": [
            r for r in rows if r["evidence_subtype"] == "ORDINARY_DOMAIN_NONE"
        ],
        "ORDINARY_DOMAIN_FALSE_PRESENT": [
            r for r in rows if r.get("error_cohort") == "ORDINARY_DOMAIN_FALSE_PRESENT"
        ],
        "PRESENT": [r for r in rows if r["evidence_label"] == "EVIDENCE_PRESENT"],
    }
    out = {}
    for name, items in cohorts.items():
        if not items:
            out[name] = {"n": 0}
            continue
        out[name] = {
            "n": len(items),
            "mean_P_EVIDENCE_PRESENT": _mean(
                [(r.get("mean_probs") or {}).get("EVIDENCE_PRESENT") for r in items]
            ),
            "mean_P_NO_EVIDENCE": _mean(
                [(r.get("mean_probs") or {}).get("NO_EVIDENCE") for r in items]
            ),
            "mean_P_UNCERTAIN": _mean(
                [(r.get("mean_probs") or {}).get("UNCERTAIN") for r in items]
            ),
            "mean_nearest_NONE_similarity": _mean(
                [r.get("nearest_none_similarity") for r in items]
            ),
            "mean_nearest_positive_similarity": _mean(
                [r.get("nearest_positive_similarity") for r in items]
            ),
            "mean_positive_minus_NONE_margin": _mean(
                [r.get("positive_minus_none_margin") for r in items]
            ),
        }
    return out


def counterfactual_gate_accounting(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    golds = [r["evidence_label"] for r in rows]
    preds = [r["decision"] for r in rows]
    none_idx = [i for i, g in enumerate(golds) if g == "NO_EVIDENCE"]
    present_idx = [i for i, g in enumerate(golds) if g == "EVIDENCE_PRESENT"]
    false_present = [i for i in none_idx if preds[i] == "EVIDENCE_PRESENT"]
    present_fn = [i for i in present_idx if preds[i] != "EVIDENCE_PRESENT"]
    none_fn = [i for i in none_idx if preds[i] != "NO_EVIDENCE"]

    n_none = len(none_idx)
    n_present = len(present_idx)
    max_false_allowed = int(math.floor(0.05 * n_none)) if n_none else 0
    min_present_tp = int(math.ceil(0.70 * n_present)) if n_present else 0
    min_none_tp = int(math.ceil(0.90 * n_none)) if n_none else 0

    current_false = len(false_present)
    current_present_tp = sum(1 for i in present_idx if preds[i] == "EVIDENCE_PRESENT")
    current_none_tp = sum(1 for i in none_idx if preds[i] == "NO_EVIDENCE")

    need_false_fixes = max(0, current_false - max_false_allowed)
    need_present_fixes = max(0, min_present_tp - current_present_tp)
    need_none_fixes = max(0, min_none_tp - current_none_tp)

    # Ordinary-domain share of false PRESENT.
    ordinary_false = [
        i
        for i in false_present
        if rows[i]["evidence_subtype"] == "ORDINARY_DOMAIN_NONE"
    ]
    observed_false = [i for i in false_present if rows[i]["provenance"] == "OBSERVED"]
    return {
        "current": {
            "EVIDENCE_PRESENT_recall": current_present_tp / max(1, n_present),
            "NO_EVIDENCE_recall": current_none_tp / max(1, n_none),
            "false_entry": current_false / max(1, n_none),
            "false_present_count": current_false,
            "present_tp": current_present_tp,
            "none_tp": current_none_tp,
        },
        "targets": {
            "max_false_present_allowed": max_false_allowed,
            "min_none_tp": min_none_tp,
            "min_present_tp": min_present_tp,
        },
        "minimum_corrections": {
            "false_PRESENT_to_non_PRESENT": need_false_fixes,
            "PRESENT_false_negatives_to_PRESENT": need_present_fixes,
            "NONE_to_NONE": need_none_fixes,
            "notes": (
                "Accounting only under frozen diagnostic thresholds; "
                "not threshold optimization."
            ),
        },
        "concentration": {
            "false_PRESENT_ORDINARY_DOMAIN_NONE": len(ordinary_false),
            "false_PRESENT_OBSERVED": len(observed_false),
            "share_ordinary_among_false_PRESENT": len(ordinary_false)
            / max(1, current_false),
            "share_observed_among_false_PRESENT": len(observed_false)
            / max(1, current_false),
        },
    }


def choose_primary_diagnosis(
    *,
    controlled: Mapping[str, Any],
    ordinary: Mapping[str, Any],
    provenance_audit: Mapping[str, Any],
    source_table: Mapping[str, Any],
    accounting: Mapping[str, Any],
) -> dict[str, Any]:
    interp = controlled["interpretation"]["state"]
    ordinary_false = ordinary["profiles"]["false_PRESENT"]["n"]
    flagged_sources = source_table["flagged"]["sources"]
    flagged_domains = source_table["flagged"]["domains"]
    clean = provenance_audit["classifications"].get("LABEL_PROVENANCE_CLEAN", 0)
    questionable = provenance_audit["classifications"].get(
        "LABEL_SEMANTICS_QUESTIONABLE", 0
    )
    weak_source = provenance_audit["classifications"].get("SOURCE_ASSERTION_WEAK", 0)
    n_mis = max(1, provenance_audit["n_misclassified_OBSERVED"])

    share_ordinary = accounting["concentration"]["share_ordinary_among_false_PRESENT"]
    share_observed = accounting["concentration"]["share_observed_among_false_PRESENT"]
    need_false = int(
        accounting["minimum_corrections"]["false_PRESENT_to_non_PRESENT"]
    )
    need_present = int(
        accounting["minimum_corrections"]["PRESENT_false_negatives_to_PRESENT"]
    )

    # Binding gate is PRESENT recall while false-entry already clears.
    # Do not re-open ordinary-NONE acquisition as the primary story.
    if need_false == 0 and need_present > 0:
        primary = "RESIDUAL_PRESENT_RECALL_FAILURE"
        remediation = (
            "False-entry already clears under sealed diagnostic thresholds; "
            f"recover at least {need_present} PRESENT false negatives to meet "
            "recall ≥ 0.70. Prefer architecture/objective investigation over "
            "another ordinary-NONE dataset remediation loop."
        )
        return {
            "architecture_change_justified": True,
            "dataset_change_justified": False,
            "primary_diagnosis": primary,
            "rationale": {
                "controlled_interpretation": interp,
                "need_false_PRESENT_fixes": need_false,
                "need_PRESENT_fn_fixes": need_present,
                "share_ordinary_among_false_PRESENT": share_ordinary,
                "share_observed_among_false_PRESENT": share_observed,
                "provenance_clean_rate": clean / n_mis,
                "provenance_questionable_rate": questionable / n_mis,
                "flagged_source_count": len(flagged_sources),
                "flagged_domain_count": len(flagged_domains),
            },
            "smallest_remediation": remediation,
        }

    # Decision tree under frozen rules — smallest causal explanation.
    if share_ordinary >= 0.70 and (
        "wiktionary" in json.dumps(flagged_sources).lower()
        or any("wiktionary" in k.lower() for k in flagged_sources)
        or any("ordinary" in k.lower() for k in flagged_domains)
    ):
        # Check if source leave-one-out killed the gap.
        source_driven = any(
            f.get("flag") == "SOURCE_DRIVEN"
            for f in controlled["source_domain_sensitivity"]["flags"]
        )
        if source_driven or share_observed >= 0.80:
            primary = "SOURCE_DOMAIN_SHIFT_FAILURE"
            remediation = (
                "Remediate OBSERVED ordinary-domain / Wiktionary NONE acquisition: "
                "tighten ordinary-domain negative contract and/or replace the "
                "high false-PRESENT OBSERVED ordinary-domain slice before any retrain."
            )
        else:
            primary = "OBSERVED_ACQUISITION_FAILURE"
            remediation = (
                "Rebuild OBSERVED ordinary-domain NONE acquisition under a stricter "
                "negative-evidence contract; keep INFERRED slice fixed; no architecture change."
            )
    elif interp == "PROVENANCE_GAP_EXPLAINED_BY_DISTRIBUTION":
        primary = "SOURCE_DOMAIN_SHIFT_FAILURE"
        remediation = (
            "Rebalance validation/train ordinary-domain OBSERVED sources/domains "
            "to matched hardness; do not treat provenance as causal by itself."
        )
    elif questionable / n_mis >= 0.30 or weak_source / n_mis >= 0.20:
        primary = "DATA_LABEL_QUALITY_FAILURE"
        remediation = (
            "Human-settle or drop semantically questionable OBSERVED ordinary-domain "
            "NONE rows flagged in provenance audit; do not retrain on unchanged labels."
        )
    elif interp == "PROVENANCE_GAP_PERSISTS" and share_observed >= 0.75:
        primary = "OBSERVED_ACQUISITION_FAILURE"
        remediation = (
            "Treat OBSERVED acquisition path as defective for Stage-A NONE: "
            "replace OBSERVED ordinary-domain negatives with higher-authority "
            "settled NONE; architecture unchanged."
        )
    elif ordinary_false < 10 and share_ordinary < 0.40:
        primary = "REPRESENTATION_FAILURE"
        remediation = (
            "Representation mismatch dominates; only then consider encoder-side "
            "changes. Current error mass does not support this as primary."
        )
    else:
        primary = "MIXED_STAGE_A_FAILURE"
        remediation = (
            "Jointly remediate OBSERVED ordinary-domain NONE acquisition and "
            "source/domain skew; defer architecture change."
        )

    dataset_change = primary in {
        "DATA_LABEL_QUALITY_FAILURE",
        "SOURCE_DOMAIN_SHIFT_FAILURE",
        "OBSERVED_ACQUISITION_FAILURE",
        "MIXED_STAGE_A_FAILURE",
    }
    architecture_change = primary == "REPRESENTATION_FAILURE"
    return {
        "architecture_change_justified": architecture_change,
        "dataset_change_justified": dataset_change,
        "primary_diagnosis": primary,
        "rationale": {
            "controlled_interpretation": interp,
            "share_ordinary_among_false_PRESENT": share_ordinary,
            "share_observed_among_false_PRESENT": share_observed,
            "provenance_clean_rate": clean / n_mis,
            "provenance_questionable_rate": questionable / n_mis,
            "flagged_source_count": len(flagged_sources),
            "flagged_domain_count": len(flagged_domains),
        },
        "smallest_remediation": remediation,
    }


def _mean(values: Sequence[Any]) -> float | None:
    clean = [float(v) for v in values if v is not None]
    if not clean:
        return None
    return sum(clean) / len(clean)


def assemble_diagnosis(
    *,
    enriched: Sequence[Mapping[str, Any]],
    surface_by_id: Mapping[str, Mapping[str, Any]],
    code_revision: str,
    experiment_id: str | None = None,
    dataset_sha256: str | None = None,
    selected_checkpoint_sha256: str | None = None,
    parent_diagnosis: str | None = None,
    surface_rule: str | None = None,
) -> dict[str, Any]:
    golds = [r["evidence_label"] for r in enriched]
    preds = [r["decision"] for r in enriched]
    overall = evaluate_decisions(golds, preds)
    cohorts = build_error_cohorts(enriched)
    controlled = controlled_comparison(enriched)
    ordinary = ordinary_domain_audit(enriched)
    provenance_audit = label_provenance_audit(enriched, surface_by_id)
    source_table = source_domain_error_table(enriched)
    representation = representation_diagnostics(enriched)
    accounting = counterfactual_gate_accounting(enriched)
    decision = choose_primary_diagnosis(
        controlled=controlled,
        ordinary=ordinary,
        provenance_audit=provenance_audit,
        source_table=source_table,
        accounting=accounting,
    )
    payload = {
        "BEST": "UNCHANGED",
        "BEST_MUTATED": False,
        "CURRENT_BEST": BEST_SHA,
        "EXPERIMENT_ID": experiment_id or EXPERIMENT_ID,
        "RESERVE_CONSUMED": False,
        "SELECTED_CHECKPOINT_SHA256": (
            selected_checkpoint_sha256 or SELECTED_CHECKPOINT_SHA
        ),
        "TRAIN": False,
        "acceptance_gates_reference": overall["acceptance"],
        "code_revision": code_revision,
        "controlled_comparison": controlled,
        "counterfactual_gate_accounting": accounting,
        "dataset_sha256": dataset_sha256 or AUTHORIZED_DATASET_SHA,
        "decision": decision,
        "diagnostic_thresholds": {
            "none_threshold": DIAGNOSTIC_NONE_THRESHOLD,
            "present_threshold": DIAGNOSTIC_PRESENT_THRESHOLD,
            "note": "Sealed fail-display pair only; threshold search not reopened.",
        },
        "error_cohorts": cohorts,
        "label_provenance_audit": provenance_audit,
        "ordinary_domain_none_audit": ordinary,
        "overall_metrics": {
            "EVIDENCE_PRESENT_recall": overall["by_label"]["EVIDENCE_PRESENT"]["recall"],
            "NO_EVIDENCE_recall": overall["by_label"]["NO_EVIDENCE"]["recall"],
            "by_label": overall["by_label"],
            "false_evidence_entry_rate_on_none": overall[
                "false_evidence_entry_rate_on_none"
            ],
            "stage_a_macro_f1": overall["stage_a_macro_f1"],
        },
        "parent_diagnosis": parent_diagnosis,
        "representation_diagnostics": representation,
        "rule": DIAGNOSE_RULE,
        "schema": "hyperlex.classification.v5.stage_a_diagnose_settled_fail.v1",
        "source_domain_error_table": source_table,
        "surface_rule": surface_rule,
    }
    payload["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in payload.items() if k != "receipt_sha256"})
    )
    return payload
