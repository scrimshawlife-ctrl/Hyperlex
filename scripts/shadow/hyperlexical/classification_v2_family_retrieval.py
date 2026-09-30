"""Classification v2 canonical family decision via training-side retrieval.

Builds a deterministic embedding index from admissible train positives and
ranks families by mean top-M cosine similarity. The residual 18-way head is
diagnostic only. This module does not train, does not score the evaluation
reserve, and does not move BEST.
"""

from __future__ import annotations

import math
import struct
from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from .classification_v2 import (
    ACTIVE_FAMILY_VOCABULARY,
    APPLICABILITY_NONE,
    APPLICABILITY_PRESENT,
    PROHIBITED_SURFACES,
    V1_NONE_CLASS,
    V2_ABSTAIN,
    V2_AMBIGUOUS,
    V2_FAMILY,
    V2_NONE,
    canonical_json,
    prf_table,
    sha256_text,
)
from .holdout_guard import normalized_text_sha256

RULE = "HYPERLEX_FAMILY_RETRIEVAL_DECISION_V1"
SCHEMA = "hyperlex.classification.v2.family_retrieval.v1"
RUN_ID = "HLX-CLASSIFICATION-V2-FAMILY-RETRIEVAL-20260930"
INDEX_SCHEMA = "hyperlex.classification.v2.family_retrieval_index.v1"
CALIBRATION_SCHEMA = "hyperlex.classification.v2.family_retrieval_calibration.v1"

TOP_M_CAP = 3
TOP_CANDIDATES = 3
EMISSION_PRECISION_MIN = 0.80
CANONICAL_FAMILY_DECISION = "retrieval_mean_top_m_cosine"
RESIDUAL_HEAD_ROLE = "diagnostic_compatibility_research_only"

FORWARD_HUB_WEIGHTS_SHA256 = (
    "adf5db93dfe258290be531f0a25035dfaae03873bd800fd929bee43b38c9f89c"
)
FORWARD_HUB_EXPORT_SHA256 = (
    "0d8f4532f84ed9fade3fd4e69af0d1e0717fb1098d40754e95c0090d8282bfe1"
)
BEST_SHA256 = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
HUB_BOUNDARY_SHA256 = (
    "96a0587c06fac352872e462445f2eaaf773e35a48ab4c987e267b479cab72a83"
)

SCORE_THRESHOLD_GRID = tuple(round(i / 100.0, 2) for i in range(0, 101))
MARGIN_THRESHOLD_GRID = tuple(round(i / 100.0, 2) for i in range(0, 51))


def retrieval_contract() -> dict[str, Any]:
    return {
        "best_sha256": BEST_SHA256,
        "canonical_family_decision": CANONICAL_FAMILY_DECISION,
        "changes_ontology": False,
        "emission_precision_min": EMISSION_PRECISION_MIN,
        "export_sha256": FORWARD_HUB_EXPORT_SHA256,
        "forward_hub_weights_sha256": FORWARD_HUB_WEIGHTS_SHA256,
        "hub_boundary_sha256": HUB_BOUNDARY_SHA256,
        "jev": "OFF",
        "moves_best": False,
        "residual_head_role": RESIDUAL_HEAD_ROLE,
        "reserve_scored": False,
        "rule": RULE,
        "run": RUN_ID,
        "schema": SCHEMA,
        "top_m_cap": TOP_M_CAP,
        "train": False,
        "uses_family_centroid": False,
    }


def _f32(values: Sequence[float]) -> list[float]:
    out = []
    for value in values:
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("non_finite_embedding")
        out.append(struct.unpack("<f", struct.pack("<f", number))[0])
    return out


def _l2_normalize(values: Sequence[float]) -> list[float]:
    vector = _f32(values)
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        raise ValueError("zero_norm_embedding")
    return _f32(value / norm for value in vector)


def embedding_hash(values: Sequence[float]) -> str:
    payload = canonical_json(_f32(values))
    return sha256_text(payload)


def source_hash(text: str) -> str:
    return sha256_text(str(text))


def is_admissible_index_row(row: Mapping[str, Any]) -> bool:
    """Train-side positives only. Validation/reserve/held-out/measurement/Jev out."""
    if row.get("split") != "train":
        return False
    if row.get("task") not in {"classify", "classify+unbind"}:
        return False
    lineage = row.get("lineage")
    if lineage not in ACTIVE_FAMILY_VOCABULARY:
        return False
    if row.get("evaluation_reserve") or row.get("held_out"):
        return False
    surface = row.get("surface")
    if surface in PROHIBITED_SURFACES:
        return False
    if row.get("jev") not in {None, False, "OFF", "off"}:
        return False
    if row.get("dropped") or row.get("ambiguous") or row.get("ambiguity"):
        return False
    if row.get("class") not in {"OBSERVED", "INFERRED"}:
        return False
    text = str(row.get("text") or "").strip()
    if not text:
        return False
    return True


def family_support_m(support: int) -> int:
    if support < 1:
        raise ValueError("family_without_exemplars")
    return min(TOP_M_CAP, int(support))


def mean_top_m(similarities: Sequence[float], m: int) -> float:
    if m < 1:
        raise ValueError("m_invalid")
    if len(similarities) < m:
        raise ValueError("insufficient_similarities")
    ordered = sorted((float(value) for value in similarities), reverse=True)
    return sum(ordered[:m]) / m


def cosine(left: Sequence[float], right: Sequence[float]) -> float:
    a = _l2_normalize(left)
    b = _l2_normalize(right)
    if len(a) != len(b):
        raise ValueError("embedding_width_mismatch")
    return float(sum(x * y for x, y in zip(a, b)))


def build_index_records(
    rows: Sequence[Mapping[str, Any]],
    embeddings_by_identity: Mapping[str, Sequence[float]],
) -> dict[str, Any]:
    """Assemble the sealed training-side index. Embeddings are supplied externally."""
    chosen: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not is_admissible_index_row(row):
            continue
        identity = normalized_text_sha256(str(row["text"]))
        if identity in seen:
            continue
        embedding = embeddings_by_identity.get(identity)
        if embedding is None:
            raise ValueError(f"missing_embedding:{identity}")
        unit = _l2_normalize(embedding)
        record = {
            "embedding": unit,
            "embedding_hash": embedding_hash(unit),
            "family": str(row["lineage"]),
            "provenance": str(row["class"]),
            "source_hash": source_hash(str(row["text"])),
            "source_identity": identity,
        }
        chosen.append(record)
        seen.add(identity)
    chosen.sort(key=lambda item: (item["family"], item["source_identity"]))
    by_family: dict[str, list[dict[str, Any]]] = {name: [] for name in ACTIVE_FAMILY_VOCABULARY}
    for record in chosen:
        by_family[record["family"]].append(record)
    missing = [name for name in ACTIVE_FAMILY_VOCABULARY if not by_family[name]]
    if missing:
        raise ValueError(f"families_without_exemplars:{missing}")
    supports = {name: len(by_family[name]) for name in ACTIVE_FAMILY_VOCABULARY}
    index = {
        "canonical_family_decision": CANONICAL_FAMILY_DECISION,
        "export_sha256": FORWARD_HUB_EXPORT_SHA256,
        "family_support": supports,
        "forward_hub_weights_sha256": FORWARD_HUB_WEIGHTS_SHA256,
        "jev": "OFF",
        "n_embeddings": len(chosen),
        "records": chosen,
        "retrieval_formula": (
            "family_score(f)=mean(top M cosine(h, exemplars_f)); "
            f"M=min({TOP_M_CAP}, family_support)"
        ),
        "rule": RULE,
        "schema": INDEX_SCHEMA,
        "top_m_cap": TOP_M_CAP,
        "uses_family_centroid": False,
    }
    bare = {key: value for key, value in index.items() if key != "index_sha256"}
    index["index_sha256"] = sha256_text(canonical_json(bare))
    return index


def family_scores(
    query_embedding: Sequence[float],
    index_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    hidden = _l2_normalize(query_embedding)
    by_family: dict[str, list[float]] = defaultdict(list)
    for record in index_records:
        family = str(record["family"])
        by_family[family].append(cosine(hidden, record["embedding"]))
    scores: dict[str, float] = {}
    m_used: dict[str, int] = {}
    for family in ACTIVE_FAMILY_VOCABULARY:
        sims = by_family.get(family) or []
        if not sims:
            raise ValueError(f"family_without_exemplars:{family}")
        m = family_support_m(len(sims))
        scores[family] = mean_top_m(sims, m)
        m_used[family] = m
    ranked = sorted(
        scores.items(),
        key=lambda item: (-item[1], ACTIVE_FAMILY_VOCABULARY.index(item[0])),
    )
    return {
        "candidates": [
            {"family": family, "score": score} for family, score in ranked[:TOP_CANDIDATES]
        ],
        "m_used": m_used,
        "ranked": [{"family": family, "score": score} for family, score in ranked],
        "scores": scores,
        "top1": {"family": ranked[0][0], "score": ranked[0][1]},
        "top2": {"family": ranked[1][0], "score": ranked[1][1]},
    }


def decide_retrieval(
    *,
    applicability: str,
    top1_family: str,
    top1_score: float,
    top2_family: str,
    top2_score: float,
    minimum_family_score: float,
    minimum_top1_top2_margin: float,
) -> dict[str, Any]:
    if applicability not in {APPLICABILITY_NONE, APPLICABILITY_PRESENT}:
        raise ValueError("applicability_invalid")
    if top1_family not in ACTIVE_FAMILY_VOCABULARY or top2_family not in ACTIVE_FAMILY_VOCABULARY:
        raise ValueError("family_invalid")
    margin = float(top1_score) - float(top2_score)
    if applicability == APPLICABILITY_NONE:
        return {
            "ambiguous_pair": None,
            "decision": V2_NONE,
            "family": None,
            "margin": margin,
            "stage": "APPLICABILITY_NONE",
            "top1_score": float(top1_score),
        }
    if float(top1_score) < float(minimum_family_score):
        return {
            "ambiguous_pair": None,
            "decision": V2_ABSTAIN,
            "family": None,
            "margin": margin,
            "stage": "FAMILY_SCORE_FLOOR",
            "top1_score": float(top1_score),
        }
    if margin < float(minimum_top1_top2_margin):
        return {
            "ambiguous_pair": [top1_family, top2_family],
            "decision": V2_AMBIGUOUS,
            "family": None,
            "margin": margin,
            "stage": "TOP1_TOP2_MARGIN",
            "top1_score": float(top1_score),
        }
    return {
        "ambiguous_pair": None,
        "decision": V2_FAMILY,
        "family": top1_family,
        "margin": margin,
        "stage": "FAMILY_RETRIEVAL",
        "top1_score": float(top1_score),
    }


def _emission_stats(
    rows: Sequence[Mapping[str, Any]],
    *,
    minimum_family_score: float,
    minimum_top1_top2_margin: float,
) -> dict[str, Any]:
    """rows carry applicability, gold_lineage, top1/top2 family+score."""
    present_gold = [
        row for row in rows if row.get("gold_lineage") in ACTIVE_FAMILY_VOCABULARY
    ]
    n_present = len(present_gold)
    emitted = []
    correct = 0
    for row in rows:
        decided = decide_retrieval(
            applicability=str(row["applicability"]),
            top1_family=str(row["top1_family"]),
            top1_score=float(row["top1_score"]),
            top2_family=str(row["top2_family"]),
            top2_score=float(row["top2_score"]),
            minimum_family_score=minimum_family_score,
            minimum_top1_top2_margin=minimum_top1_top2_margin,
        )
        if decided["decision"] != V2_FAMILY:
            continue
        gold = row.get("gold_lineage")
        hit = gold == decided["family"]
        emitted.append({"family": decided["family"], "gold": gold, "correct": hit})
        if hit:
            correct += 1
    n_emitted = len(emitted)
    precision = None if n_emitted == 0 else correct / n_emitted
    coverage = None if n_present == 0 else n_emitted / n_present
    recall = None if n_present == 0 else correct / n_present
    return {
        "correct": correct,
        "correct_family_emission_rate": recall,
        "coverage": coverage,
        "n_emitted": n_emitted,
        "n_present": n_present,
        "precision": precision,
        "recall": recall,
    }


def calibrate_thresholds(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Deterministic global threshold search on validation retrieval scores."""
    if not rows:
        raise ValueError("calibration_empty")
    best: dict[str, Any] | None = None
    for score_threshold in SCORE_THRESHOLD_GRID:
        for margin_threshold in MARGIN_THRESHOLD_GRID:
            stats = _emission_stats(
                rows,
                minimum_family_score=score_threshold,
                minimum_top1_top2_margin=margin_threshold,
            )
            precision = stats["precision"]
            if precision is None or precision + 1e-12 < EMISSION_PRECISION_MIN:
                continue
            rank = (
                float(stats["correct_family_emission_rate"] or 0.0),
                float(stats["coverage"] or 0.0),
                float(precision),
                float(margin_threshold),
                float(score_threshold),
            )
            candidate = {
                "correct_family_emission_rate": stats["correct_family_emission_rate"],
                "coverage": stats["coverage"],
                "minimum_family_score": score_threshold,
                "minimum_top1_top2_margin": margin_threshold,
                "precision": precision,
                "rank": rank,
                "recall": stats["recall"],
            }
            if best is None or candidate["rank"] > best["rank"]:
                best = candidate
    if best is None:
        return {
            "feasible": False,
            "minimum_family_score": None,
            "minimum_top1_top2_margin": None,
            "reason": "no_threshold_pair_met_emission_precision_min",
            "schema": CALIBRATION_SCHEMA,
            "surface": "validation",
            "reserve_used": False,
            "training_rows_used": False,
        }
    return {
        "correct_family_emission_rate": best["correct_family_emission_rate"],
        "coverage": best["coverage"],
        "feasible": True,
        "minimum_family_score": best["minimum_family_score"],
        "minimum_top1_top2_margin": best["minimum_top1_top2_margin"],
        "precision": best["precision"],
        "recall": best["recall"],
        "schema": CALIBRATION_SCHEMA,
        "surface": "validation",
        "reserve_used": False,
        "training_rows_used": False,
    }


def evaluate_retrieval_decisions(
    rows: Sequence[Mapping[str, Any]],
    *,
    minimum_family_score: float,
    minimum_top1_top2_margin: float,
) -> dict[str, Any]:
    decisions = []
    present_gold = []
    emitted_gold = []
    emitted_pred = []
    ranks_top1 = []
    ranks_top2 = []
    counts = Counter()
    for row in rows:
        decided = decide_retrieval(
            applicability=str(row["applicability"]),
            top1_family=str(row["top1_family"]),
            top1_score=float(row["top1_score"]),
            top2_family=str(row["top2_family"]),
            top2_score=float(row["top2_score"]),
            minimum_family_score=minimum_family_score,
            minimum_top1_top2_margin=minimum_top1_top2_margin,
        )
        gold = row.get("gold_lineage")
        decisions.append(
            {
                "ambiguous_pair": decided["ambiguous_pair"],
                "decision": decided["decision"],
                "family": decided["family"],
                "gold_lineage": gold,
                "margin": decided["margin"],
                "stage": decided["stage"],
                "top1_family": row["top1_family"],
                "top1_score": row["top1_score"],
                "top2_family": row["top2_family"],
                "top2_score": row["top2_score"],
            }
        )
        counts[decided["decision"]] += 1
        if gold in ACTIVE_FAMILY_VOCABULARY:
            present_gold.append(gold)
            ranks_top1.append(1 if row["top1_family"] == gold else 0)
            ranks_top2.append(
                1 if gold in {row["top1_family"], row["top2_family"]} else 0
            )
            if decided["decision"] == V2_FAMILY:
                emitted_gold.append(gold)
                emitted_pred.append(decided["family"])
    stats = _emission_stats(
        rows,
        minimum_family_score=minimum_family_score,
        minimum_top1_top2_margin=minimum_top1_top2_margin,
    )
    n = len(rows)
    n_present = len(present_gold)
    confusion = {}
    if emitted_gold:
        matrix = prf_table(emitted_gold, emitted_pred, ACTIVE_FAMILY_VOCABULARY)
        confusion = _confusion(emitted_gold, emitted_pred, ACTIVE_FAMILY_VOCABULARY)
        per_family = matrix["per_label"]
    else:
        per_family = {
            name: {"precision": None, "recall": None, "f1": None, "support": 0, "predicted": 0}
            for name in ACTIVE_FAMILY_VOCABULARY
        }
    # Per-family emitted precision/recall among gold-present rows for that family.
    emitted_metrics = {}
    for family in ACTIVE_FAMILY_VOCABULARY:
        gold_n = sum(1 for item in present_gold if item == family)
        pred_n = sum(
            1
            for item in decisions
            if item["decision"] == V2_FAMILY and item["family"] == family
        )
        hit = sum(
            1
            for item in decisions
            if item["decision"] == V2_FAMILY
            and item["family"] == family
            and item["gold_lineage"] == family
        )
        precision = None if pred_n == 0 else hit / pred_n
        recall = None if gold_n == 0 else hit / gold_n
        f1 = None
        if precision is not None and recall is not None:
            f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
        elif gold_n == 0 and pred_n == 0:
            f1 = None
        else:
            f1 = 0.0 if gold_n else None
        emitted_metrics[family] = {
            "f1": f1,
            "precision": precision,
            "predicted_count": pred_n,
            "recall": recall,
            "support": gold_n,
        }
    return {
        "abstain_rate": counts[V2_ABSTAIN] / n if n else None,
        "ambiguous_rate": counts[V2_AMBIGUOUS] / n if n else None,
        "confusion_matrix": confusion,
        "confusion_matrix_sha256": sha256_text(canonical_json(confusion)),
        "correct_family_emission_rate": stats["correct_family_emission_rate"],
        "coverage": stats["coverage"],
        "decision_counts": dict(counts),
        "decisions": decisions,
        "family_emission_precision": stats["precision"],
        "family_emission_recall": stats["recall"],
        "n": n,
        "n_present": n_present,
        "none_rate": counts[V2_NONE] / n if n else None,
        "per_family_emitted": emitted_metrics,
        "top1_accuracy": None if not ranks_top1 else sum(ranks_top1) / len(ranks_top1),
        "top2_accuracy": None if not ranks_top2 else sum(ranks_top2) / len(ranks_top2),
        # keep table alias for callers that expect prf-shaped rows
        "per_family_table": per_family,
    }


def _confusion(
    golds: Sequence[str], preds: Sequence[str], labels: Sequence[str]
) -> dict[str, dict[str, int]]:
    table = {gold: {pred: 0 for pred in labels} for gold in labels}
    for gold, pred in zip(golds, preds, strict=True):
        if gold in table and pred in table[gold]:
            table[gold][pred] += 1
    return {
        gold: {pred: count for pred, count in row.items() if count}
        for gold, row in table.items()
        if any(row.values())
    }


def compare_residual(
    *,
    golds: Sequence[str],
    residual_preds: Sequence[str],
    retrieval_eval: Mapping[str, Any],
) -> dict[str, Any]:
    if len(golds) != len(residual_preds):
        raise ValueError("residual_compare_length_mismatch")
    residual = prf_table(golds, residual_preds, ACTIVE_FAMILY_VOCABULARY)
    residual_top1 = sum(1 for gold, pred in zip(golds, residual_preds) if gold == pred) / max(
        len(golds), 1
    )
    return {
        "canonical": CANONICAL_FAMILY_DECISION,
        "residual_active_family_macro_f1": residual["macro_f1"],
        "residual_head_role": RESIDUAL_HEAD_ROLE,
        "residual_top1_accuracy": residual_top1,
        "retrieval_coverage": retrieval_eval.get("coverage"),
        "retrieval_family_emission_precision": retrieval_eval.get("family_emission_precision"),
        "retrieval_family_emission_recall": retrieval_eval.get("family_emission_recall"),
        "retrieval_top1_accuracy": retrieval_eval.get("top1_accuracy"),
        "retrieval_top2_accuracy": retrieval_eval.get("top2_accuracy"),
    }


def reserve_gate(
    *,
    family_emission_precision: float | None,
    applicability_invariance_pass: bool,
) -> dict[str, Any]:
    precision_ok = (
        family_emission_precision is not None
        and float(family_emission_precision) + 1e-12 >= EMISSION_PRECISION_MIN
    )
    if precision_ok and applicability_invariance_pass:
        return {
            "decision": "RESERVE_EVAL_JUSTIFIED",
            "family_emission_precision": family_emission_precision,
            "applicability_invariance_pass": True,
            "precision_ok": True,
            "remaining_failure": None,
        }
    failures = []
    if not precision_ok:
        failures.append(
            f"family_emission_precision={family_emission_precision} < {EMISSION_PRECISION_MIN}"
        )
    if not applicability_invariance_pass:
        failures.append("applicability_invariance_failed")
    return {
        "decision": "RESERVE_EVAL_NOT_JUSTIFIED",
        "family_emission_precision": family_emission_precision,
        "applicability_invariance_pass": bool(applicability_invariance_pass),
        "precision_ok": precision_ok,
        "remaining_failure": "; ".join(failures),
    }


def assemble_family_retrieval_artifact(payload: Mapping[str, Any]) -> dict[str, Any]:
    artifact = {
        "applicability_invariance": payload["applicability_invariance"],
        "audit_state": {
            "best_moved": False,
            "canonical_family_decision": CANONICAL_FAMILY_DECISION,
            "checkpoint_sha256": FORWARD_HUB_WEIGHTS_SHA256,
            "export_sha256": FORWARD_HUB_EXPORT_SHA256,
            "read_only_encoder": True,
            "reserve_scored": False,
            "residual_head_role": RESIDUAL_HEAD_ROLE,
            "run": RUN_ID,
            "surface": "validation",
            "train": False,
        },
        "calibration": payload["calibration"],
        "comparison_with_residual": payload["comparison_with_residual"],
        "contract": retrieval_contract(),
        "evaluation": {
            key: value
            for key, value in payload["evaluation"].items()
            if key != "decisions"
        },
        "family_support": payload["family_support"],
        "index_sha256": payload["index_sha256"],
        "n_index_embeddings": payload["n_index_embeddings"],
        "next_action": payload["next_action"],
        "reserve_gate": payload["reserve_gate"],
        "retrieval_formula": (
            "family_score(f)=mean(top M cosine(h, exemplars_f)); "
            f"M=min({TOP_M_CAP}, family_support); no centroid"
        ),
        "rule": RULE,
        "schema": SCHEMA,
        "thresholds": {
            "minimum_family_score": payload["calibration"].get("minimum_family_score"),
            "minimum_top1_top2_margin": payload["calibration"].get(
                "minimum_top1_top2_margin"
            ),
        },
    }
    bare = {key: value for key, value in artifact.items() if key != "artifact_sha256"}
    artifact["artifact_sha256"] = sha256_text(canonical_json(bare))
    return artifact


def next_action_for_gate(gate: Mapping[str, Any]) -> str:
    if gate.get("decision") == "RESERVE_EVAL_JUSTIFIED":
        return (
            "OPERATOR_AUTHORIZE_RESERVE_EVAL — validation emission precision and "
            "applicability invariance passed; do not move BEST automatically."
        )
    failure = gate.get("remaining_failure") or "validation_gate_failed"
    return (
        f"STOP_OR_REMEDIATE — reserve not justified ({failure}); do not score reserve; "
        "do not move BEST; do not open another global softmax experiment."
    )


RESERVE_EVAL_SCHEMA = "hyperlex.classification.v2.family_retrieval_reserve_eval.v1"
RESERVE_EVAL_RUN = "HLX-CLASSIFICATION-V2-FAMILY-RETRIEVAL-RESERVE-20260930"
FROZEN_MINIMUM_FAMILY_SCORE = 0.85
FROZEN_MINIMUM_TOP1_TOP2_MARGIN = 0.03
RETRIEVAL_ARTIFACT_SHA256 = (
    "4030e6a36ca1fea34dc728ae913bc96697e7484be532260f7b580ba5eadf2c8f"
)
RETRIEVAL_INDEX_SHA256 = (
    "b1cd64d9e50e35f2c195f2e115ffdbd77f0a28089f8bd90792f36f1abc4b0177"
)
DISPOSITIONS = ("RESERVE_PASS", "RESERVE_FAIL", "RESERVE_INVALID")


def reserve_eval_contract() -> dict[str, Any]:
    return {
        "authorization": "OPERATOR_AUTHORIZE_RESERVE_EVAL",
        "best_sha256": BEST_SHA256,
        "canonical_family_decision": CANONICAL_FAMILY_DECISION,
        "index_sha256": RETRIEVAL_INDEX_SHA256,
        "jev": "OFF",
        "minimum_family_score": FROZEN_MINIMUM_FAMILY_SCORE,
        "minimum_top1_top2_margin": FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
        "moves_best": False,
        "recalibrate": False,
        "rebuild_index": False,
        "retrieval_artifact_sha256": RETRIEVAL_ARTIFACT_SHA256,
        "rule": RULE,
        "run": RESERVE_EVAL_RUN,
        "schema": RESERVE_EVAL_SCHEMA,
        "train": False,
    }


def wrong_family_emissions(decisions: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    wrong = []
    for row in decisions:
        if row.get("decision") != V2_FAMILY:
            continue
        if row.get("family") == row.get("gold_lineage"):
            continue
        top1 = float(row["top1_score"])
        top2 = float(row["top2_score"])
        wrong.append(
            {
                "gold_family": row.get("gold_lineage"),
                "margin": top1 - top2,
                "predicted_family": row.get("family"),
                "source_identity": row.get("source_identity"),
                "top1_score": top1,
                "top2_score": top2,
            }
        )
    wrong.sort(
        key=lambda item: (
            str(item["gold_family"] or ""),
            str(item["predicted_family"] or ""),
            str(item["source_identity"] or ""),
        )
    )
    return wrong


def validation_vs_reserve(
    validation: Mapping[str, Any], reserve: Mapping[str, Any]
) -> dict[str, Any]:
    keys = (
        "family_emission_precision",
        "coverage",
        "family_emission_recall",
        "abstain_rate",
        "ambiguous_rate",
        "top1_accuracy",
        "top2_accuracy",
    )
    comparison = {}
    for key in keys:
        left = validation.get(key)
        right = reserve.get(key)
        comparison[key] = {
            "delta_reserve_minus_validation": None
            if left is None or right is None
            else float(right) - float(left),
            "reserve": right,
            "validation": left,
        }
    return comparison


def selective_contract_generalizes(
    *,
    reserve_precision: float | None,
    validation_precision: float | None,
) -> dict[str, Any]:
    reserve_ok = (
        reserve_precision is not None
        and float(reserve_precision) + 1e-12 >= EMISSION_PRECISION_MIN
    )
    validation_ok = (
        validation_precision is not None
        and float(validation_precision) + 1e-12 >= EMISSION_PRECISION_MIN
    )
    return {
        "emission_precision_min": EMISSION_PRECISION_MIN,
        "generalizes": bool(reserve_ok and validation_ok),
        "reserve_precision_ok": reserve_ok,
        "validation_precision_ok": validation_ok,
    }


def decide_reserve_disposition(
    *,
    invalid_reasons: Sequence[str],
    family_emission_precision: float | None,
) -> dict[str, Any]:
    if invalid_reasons:
        return {
            "disposition": "RESERVE_INVALID",
            "emission_precision_min": EMISSION_PRECISION_MIN,
            "family_emission_precision": family_emission_precision,
            "reasons": list(invalid_reasons),
        }
    precision_ok = (
        family_emission_precision is not None
        and float(family_emission_precision) + 1e-12 >= EMISSION_PRECISION_MIN
    )
    if precision_ok:
        return {
            "disposition": "RESERVE_PASS",
            "emission_precision_min": EMISSION_PRECISION_MIN,
            "family_emission_precision": family_emission_precision,
            "production_family_decision_recommended": True,
            "reasons": [
                "family_emission_precision_met_frozen_acceptance_metric",
                "no_contamination_or_contract_failure",
            ],
        }
    return {
        "disposition": "RESERVE_FAIL",
        "emission_precision_min": EMISSION_PRECISION_MIN,
        "family_emission_precision": family_emission_precision,
        "production_family_decision_recommended": False,
        "reasons": [
            f"family_emission_precision={family_emission_precision} "
            f"< frozen_min={EMISSION_PRECISION_MIN}"
        ],
    }


def assemble_reserve_eval_artifact(payload: Mapping[str, Any]) -> dict[str, Any]:
    artifact = {
        "applicability": payload["applicability"],
        "audit_state": {
            "authorization": "OPERATOR_AUTHORIZE_RESERVE_EVAL",
            "best_moved": False,
            "index_rebuilt": False,
            "recalibrated": False,
            "thresholds_changed": False,
            "train": False,
        },
        "contract": reserve_eval_contract(),
        "disposition": payload["disposition"],
        "evaluation": {
            key: value
            for key, value in payload["evaluation"].items()
            if key != "decisions"
        },
        "generalization": payload["generalization"],
        "next_action": payload["next_action"],
        "pinned": payload["pinned"],
        "reserve_identity": payload["reserve_identity"],
        "rule": RULE,
        "schema": RESERVE_EVAL_SCHEMA,
        "selective_contract_generalizes": payload["generalization"].get("generalizes"),
        "validation_vs_reserve": payload["validation_vs_reserve"],
        "wrong_family_emissions": payload["wrong_family_emissions"],
    }
    bare = {key: value for key, value in artifact.items() if key != "artifact_sha256"}
    artifact["artifact_sha256"] = sha256_text(canonical_json(bare))
    return artifact


def next_action_for_disposition(disposition: Mapping[str, Any]) -> str:
    name = disposition.get("disposition")
    if name == "RESERVE_PASS":
        return (
            "RETRIEVAL_V1_PRODUCTION_CANDIDATE — selective contract generalized; "
            "BEST unchanged until a separate explicit promotion authorization."
        )
    if name == "RESERVE_FAIL":
        return (
            "STOP — preserve reserve result; do not reopen scorer tuning against the "
            "reserve; do not move BEST."
        )
    return (
        "RESERVE_INVALID — fix contamination/execution/provenance/contract failure; "
        "do not treat metrics as the failure mode; do not move BEST."
    )
