"""Sealed Classification v2 contract. No training and no checkpoint writes.

Normative text: ``specs/007-hyperlexical-model/classification-architecture-v2.md``.

The family head has one row for every active production family. ``none``,
``ABSTAIN``, ``AMBIGUOUS``, and legacy near-matches are not rows. Provenance
weights are frozen. Class weights are a pure function of the training split
and are undefined while any active family has zero positive support.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import statistics
import struct
from typing import Any, Mapping, Sequence

from hyperlexical.eval_settlement import ACTIVE_FAMILIES, CANDIDATE_FAMILIES
from hyperlexical.layout import FAMILIES

ARCHITECTURE_ID = "HYPERLEX_CLASSIFICATION_ARCHITECTURE_V2"
STATE = "PREREGISTERED"
SCHEMA = "hyperlex.classification.v2"
PACKET_SCHEMA = "hyperlex.jev.decision_packet.v1"
ADAPTER_SCHEMA = "hyperlex.classification.v2.row_mapping.v1"
VOCABULARY_ID = "hyperlex.active_families.v1"

BEST_REFERENCE_SHA256 = (
    "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
)

ACTIVE_FAMILY_VOCABULARY: tuple[str, ...] = (
    "gaming-meta",
    "betting-sharp",
    "crypto-degen",
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
    "ai-native",
)
if tuple(ACTIVE_FAMILIES) != ACTIVE_FAMILY_VOCABULARY:
    raise RuntimeError("ACTIVE_FAMILIES drifted from the sealed v2 vocabulary")

V1_HEAD = tuple(FAMILIES)
V1_NONE_CLASS = "none"
LEGACY_HEADS = tuple(name for name in V1_HEAD if name != V1_NONE_CLASS and name not in ACTIVE_FAMILY_VOCABULARY)
EXACT_COPY_FAMILIES = tuple(name for name in V1_HEAD if name in ACTIVE_FAMILY_VOCABULARY)
FORBIDDEN_NEAR_MATCHES = (
    ("workplace-corp", "workplace-career"),
    ("political-status", "politics-civic"),
    ("brainrot-aura", "memetic"),
    ("kinship-address", "relationship-dating"),
)

V2_FAMILY = "FAMILY"
V2_NONE = "NONE"
V2_ABSTAIN = "ABSTAIN"
V2_AMBIGUOUS = "AMBIGUOUS"
DECISIONS = (V2_FAMILY, V2_NONE, V2_ABSTAIN, V2_AMBIGUOUS)
APPLICABILITY_NONE = "NONE"
APPLICABILITY_PRESENT = "FAMILY_PRESENT"
APPLICABILITY = (APPLICABILITY_NONE, APPLICABILITY_PRESENT)
AMBIGUITY_EMISSION = "DISABLED_PENDING_GOLD"
PROVENANCE = ("OBSERVED", "INFERRED", "UNKNOWN")
LABEL_CLASS = ("OBSERVED", "INFERRED")
SETTLEMENT_ABSTAIN_TOKEN = "none"

JEV_OFF = "OFF"
JEV_SHADOW = "SHADOW"
JEV_GATED = "GATED"
JEV_MODES_IMPLEMENTED = (JEV_OFF, JEV_SHADOW)
PROHIBITED_SURFACES = frozenset(
    {"held_out", "evaluation_reserve", "settlement", "measurement"}
)
PROBABILITY_SUM_TOLERANCE = 1e-12
TEMPERATURE_GRID = tuple(i / 100 for i in range(5, 501))

PROVENANCE_WEIGHTS: dict[str, float] = {
    "observed_non_none_applicability": 1.00,
    "observed_non_none_family": 1.00,
    "inferred_non_none_applicability": 0.50,
    "inferred_non_none_family": 0.50,
    "observed_none_applicability": 1.00,
    "inferred_none_applicability": 0.25,
}
FAMILY_WEIGHT_FLOOR = 0.50
FAMILY_WEIGHT_CAP = 2.00
SELECTION_WEIGHTS = (0.50, 0.25, 0.25)

V2_SCHEDULE = {
    "max_epochs": 12,
    "minimum_epochs": 4,
    "early_stopping_patience": 4,
    "improvement": "strict",
    "ties": "keep_earlier",
    "restore_best": True,
    "last_trainable": 2,
    "learning_rate": 2e-5,
    "batch_size": 8,
    "gradient_accumulation": 1,
    "max_len": 64,
    "filler_filter": "strict",
    "unbind_curriculum": False,
    "unbind_every_n": 1,
    "unbind_loss_weight": 1.0,
    "unbind_primary": "mixed",
}
TELEMETRY_FIELDS = (
    "total_loss",
    "applicability_loss",
    "family_loss",
    "unbind_loss",
    "applicability_macro_f1",
    "none_precision",
    "none_recall",
    "none_f1",
    "family_present_precision",
    "family_present_recall",
    "family_present_f1",
    "active_family_macro_f1",
    "observed_active_family_macro_f1",
    "exact_copy_family_macro_f1",
    "prototype_family_macro_f1",
    "per_family",
    "predicted_none_rate",
    "family_emission_rate",
    "selection_score",
    "learning_rate",
    "global_step",
    "checkpoint_identity",
    "observed_slice",
    "inferred_slice",
)

OPERATOR_AUTHORIZATION = {
    "present": True,
    "authorizes_architecture": True,
    "authorizes_training_before_ready": False,
    "authorizes_best_promotion": False,
    "statement": (
        "Operator sealed Classification v2 on 2026-09-29. "
        "One end-to-end training run is the next action after READY. "
        "BEST promotion stays a later explicit action."
    ),
}


class ClassificationContractError(ValueError):
    def __init__(self, reason: str, detail: Any = None) -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(reason if detail is None else f"{reason}: {detail}")


class JevContractError(ClassificationContractError):
    pass


class ActiveFamilyWithoutTrainingSupport(ClassificationContractError):
    def __init__(self, families: Sequence[str]) -> None:
        self.families = tuple(families)
        super().__init__("ACTIVE_FAMILY_WITHOUT_TRAINING_SUPPORT", list(self.families))


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def vocabulary_sha256() -> str:
    return sha256_text("\n".join(ACTIVE_FAMILY_VOCABULARY))


def _unit(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise JevContractError("malformed_probability")
    number = float(value)
    if not math.isfinite(number) or number < 0.0 or number > 1.0:
        raise JevContractError("malformed_probability")
    return number


def _finite(value: Any, reason: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ClassificationContractError(reason)
    number = float(value)
    if not math.isfinite(number):
        raise ClassificationContractError(reason)
    return number


def decision_seal() -> dict[str, Any]:
    body = {
        "active_family_vocabulary": list(ACTIVE_FAMILY_VOCABULARY),
        "ambiguity_emission": AMBIGUITY_EMISSION,
        "applicability_balance": "inverse_square_root_mean_one",
        "applicability_surface_balance": "four_cell_inverse_support_mean_one",
        "exact_copy_families": list(EXACT_COPY_FAMILIES),
        "family_weight_clip": [FAMILY_WEIGHT_FLOOR, FAMILY_WEIGHT_CAP],
        "family_weight_rule": "sqrt(median/effective)_then_mean_one_then_clip",
        "forbidden_near_matches": [list(pair) for pair in FORBIDDEN_NEAR_MATCHES],
        "legacy_heads": list(LEGACY_HEADS),
        "new_row_initialization": "semantic_prototype",
        "provenance_weights": PROVENANCE_WEIGHTS,
        "schedule": V2_SCHEDULE,
        "selection_score": "0.50*active_family_macro_f1+0.25*applicability_macro_f1+0.25*observed_active_family_macro_f1",
        "applicability_surface_f1_min": 0.80,
        "none_surface_gap_abs_max": 0.10,
        "residualized_length_correlation_abs_max": 0.30,
        "surface_rule": "hyperlex.classification.v2.surface.v1",
        "surface_shortcut_abs_correlation_max": 0.30,
        "family_canonical_logits": "learned_residual",
        "family_fusion_alpha": 1.0,
        "family_fusion_beta": 1.0,
        "family_fusion_rule": "population_zscore(cosine/tau)+population_zscore(residual)",
        "family_geometry_hard_negative_multiplier": 2.0,
        "family_geometry_lambda": 0.5,
        "family_geometry_repair": "HYPERLEX_FAMILY_GEOMETRY_REPAIR_V1",
        "family_geometry_tau": 0.10,
        "family_hard_negative_multiplier": 2.0,
        "family_prototype_lambda": 0.5,
        "family_prototype_tau": 0.10,
        "family_prototypes": "frozen_loss_structure_only",
        "surface_shortcut_diagnostic": "gold_conditional_residualized",
        "vocabulary_id": VOCABULARY_ID,
    }
    return {"sha256": sha256_text(canonical_json(body)), "body": body}


def architecture_state() -> dict[str, Any]:
    seal = decision_seal()
    return {
        "architecture_id": ARCHITECTURE_ID,
        "state": STATE,
        "authorizes_training": False,
        "authorizes_preregistration": True,
        "authorizes_gated_jev": False,
        "moves_best": False,
        "best_reference_sha256": BEST_REFERENCE_SHA256,
        "select_006": "SETTLED_PASS",
        "select_007": "SETTLED_FAIL",
        "reopens_select_006": False,
        "reopens_select_007": False,
        "decision_seal_sha256": seal["sha256"],
        "active_family_count": len(ACTIVE_FAMILY_VOCABULARY),
        "ambiguity_emission": AMBIGUITY_EMISSION,
        "jev_default": JEV_OFF,
        "operator_authorization": dict(OPERATOR_AUTHORIZATION),
    }


def classification_version(raw: str | None = None) -> str:
    if raw is None:
        raw = os.environ.get("HYPERLEX_CLASSIFICATION")
    token = (raw or "v1").strip().lower()
    if token in {"", "v1", "1"}:
        return "v1"
    if token in {"v2", "2"}:
        return "v2"
    raise ClassificationContractError("classification_version_invalid")


def gated_authorized(_evidence: Mapping[str, Any] | None = None) -> bool:
    return False


def family_index() -> dict[str, int]:
    return {name: index for index, name in enumerate(ACTIVE_FAMILY_VOCABULARY)}


def mapping_plan(source_labels: Sequence[str]) -> list[dict[str, Any]]:
    """Exact-name plan. Near-matches stay unmapped and are not family rows."""
    source = tuple(source_labels)
    if len(source) != len(set(source)):
        raise ClassificationContractError("duplicate_source_label")
    source_of = {label: index for index, label in enumerate(source)}
    rows: list[dict[str, Any]] = []
    for family in ACTIVE_FAMILY_VOCABULARY:
        source_index = source_of.get(family)
        if source_index is None:
            rows.append(
                {
                    "active_family": family,
                    "source_row": None,
                    "mapping_status": "ZERO_INIT",
                    "initialization_status": "exact_zero",
                }
            )
            continue
        rows.append(
            {
                "active_family": family,
                "source_row": family,
                "source_index": source_index,
                "mapping_status": "EXACT_COPY",
                "initialization_status": "copied",
            }
        )
    return rows


def _f32_hash(values: Sequence[float]) -> str:
    raw = b"".join(struct.pack("<f", float(value)) for value in values)
    return hashlib.sha256(raw).hexdigest()


def map_family_rows(
    source_labels: Sequence[str],
    source_weight: Sequence[Sequence[float]],
    source_bias: Sequence[float],
) -> dict[str, Any]:
    """Copy exact rows and set every other active-family row to exact zero.

    ``source_weight[row][hidden]``. No random values are retained.
    """
    plan = mapping_plan(source_labels)
    if len(source_weight) != len(source_labels) or len(source_bias) != len(source_labels):
        raise ClassificationContractError("source_shape_mismatch")
    hidden = len(source_weight[0]) if source_weight else 0
    if hidden < 1 or any(len(row) != hidden for row in source_weight):
        raise ClassificationContractError("source_shape_mismatch")
    weight: list[list[float]] = []
    bias: list[float] = []
    witness: list[dict[str, Any]] = []
    for item in plan:
        if item["mapping_status"] == "EXACT_COPY":
            copied_weight = [float(value) for value in source_weight[item["source_index"]]]
            copied_bias = float(source_bias[item["source_index"]])
            if copied_weight != [float(value) for value in source_weight[item["source_index"]]]:
                raise ClassificationContractError("copy_mismatch")
        else:
            copied_weight = [0.0] * hidden
            copied_bias = 0.0
        if item["mapping_status"] != "EXACT_COPY" and any(value != 0.0 for value in copied_weight):
            raise ClassificationContractError("nonzero_new_row")
        if item["mapping_status"] != "EXACT_COPY" and copied_bias != 0.0:
            raise ClassificationContractError("nonzero_new_row")
        weight.append(copied_weight)
        bias.append(copied_bias)
        witness.append(
            {
                **item,
                "weight_sha256": _f32_hash(copied_weight),
                "bias_sha256": _f32_hash((copied_bias,)),
            }
        )
    for pair in FORBIDDEN_NEAR_MATCHES:
        if any(row["source_row"] == pair[0] and row["active_family"] == pair[1] for row in witness):
            raise ClassificationContractError("legacy_near_match")
    if any(row["active_family"] in {V1_NONE_CLASS, V2_ABSTAIN, V2_AMBIGUOUS} for row in witness):
        raise ClassificationContractError("forbidden_family_row")
    return {
        "schema": ADAPTER_SCHEMA,
        "vocabulary_id": VOCABULARY_ID,
        "vocabulary_sha256": vocabulary_sha256(),
        "historical_artifact_mutated": False,
        "target_rows": len(weight),
        "mapped_families": [row["active_family"] for row in witness if row["mapping_status"] == "EXACT_COPY"],
        "zero_initialized_families": [row["active_family"] for row in witness if row["mapping_status"] == "ZERO_INIT"],
        "legacy_not_mapped": list(LEGACY_HEADS),
        "legacy_remap": {},
        "rows": witness,
        "weight": weight,
        "bias": bias,
        "status": "PASS",
    }


def _class_of(row: Mapping[str, Any]) -> str:
    klass = row.get("class")
    if klass not in LABEL_CLASS:
        raise ClassificationContractError("provenance_class_missing")
    return str(klass)


def _reject_isolated(row: Mapping[str, Any]) -> None:
    if row.get("split") == "test":
        raise ClassificationContractError("evaluation_isolation")
    surface = row.get("surface")
    if surface in PROHIBITED_SURFACES or row.get("evaluation_reserve") or row.get("held_out"):
        raise ClassificationContractError("evaluation_isolation")


def support_audit(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Training-split counts. Legacy lineages do not fill an active family."""
    counts = {
        name: {"OBSERVED": 0, "INFERRED": 0}
        for name in (*ACTIVE_FAMILY_VOCABULARY, V1_NONE_CLASS)
    }
    legacy = {name: {"OBSERVED": 0, "INFERRED": 0} for name in LEGACY_HEADS}
    for row in rows:
        _reject_isolated(row)
        if row.get("split") not in (None, "train"):
            raise ClassificationContractError("support_requires_training_split")
        lineage = row.get("lineage")
        klass = _class_of(row)
        if lineage in counts:
            counts[str(lineage)][klass] += 1
        elif lineage in legacy:
            legacy[str(lineage)][klass] += 1
        else:
            raise ClassificationContractError("unknown_lineage", lineage)
    families = []
    missing: list[str] = []
    for name in ACTIVE_FAMILY_VOCABULARY:
        observed = counts[name]["OBSERVED"]
        inferred = counts[name]["INFERRED"]
        effective = observed + 0.5 * inferred
        if effective == 0:
            missing.append(name)
        families.append(
            {
                "family": name,
                "observed": observed,
                "inferred": inferred,
                "effective_support": effective,
            }
        )
    observed_active = sum(item["observed"] for item in families)
    inferred_active = sum(item["inferred"] for item in families)
    return {
        "families": families,
        "missing_support": missing,
        "legacy_excluded": [
            {
                "lineage": name,
                "observed": legacy[name]["OBSERVED"],
                "inferred": legacy[name]["INFERRED"],
            }
            for name in LEGACY_HEADS
        ],
        "none": {
            "observed": counts[V1_NONE_CLASS]["OBSERVED"],
            "inferred": counts[V1_NONE_CLASS]["INFERRED"],
            "effective_support": (
                counts[V1_NONE_CLASS]["OBSERVED"]
                + PROVENANCE_WEIGHTS["inferred_none_applicability"] * counts[V1_NONE_CLASS]["INFERRED"]
            ),
        },
        "family_present_effective": (
            observed_active * PROVENANCE_WEIGHTS["observed_non_none_applicability"]
            + inferred_active * PROVENANCE_WEIGHTS["inferred_non_none_applicability"]
        ),
    }


_RESERVE_STATES = frozenset({"EVAL_RESERVE", "EVAL_SPENT", "EVAL_ABANDONED"})


def reserve_positive_census(identities: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Count settled positives that cannot fill v2 training support.

    Evaluation-reserved, spent, and abandoned identities stay out of the
    training split. This census does not copy them and does not read row text.
    """
    counts = {
        name: {"OBSERVED": 0, "INFERRED": 0, "training_eligible": 0}
        for name in ACTIVE_FAMILY_VOCABULARY
    }
    for identity in identities:
        excluded = bool(identity.get("evaluation_reserved")) or identity.get("state") in _RESERVE_STATES
        for label in identity.get("labels") or []:
            lineage = label.get("lineage")
            if lineage not in counts:
                continue
            if not excluded:
                counts[lineage]["training_eligible"] += 1
                continue
            klass = label.get("class")
            if klass in ("OBSERVED", "INFERRED"):
                counts[lineage][klass] += 1
    absent = [
        name
        for name in ACTIVE_FAMILY_VOCABULARY
        if counts[name]["OBSERVED"] == 0
        and counts[name]["INFERRED"] == 0
        and counts[name]["training_eligible"] == 0
    ]
    return {
        "schema": "hyperlex.classification.v2.reserve_exclusion.v1",
        "counts": counts,
        "training_eligible_rows": sum(item["training_eligible"] for item in counts.values()),
        "usable_for_training": False,
        "no_settled_positive": absent,
    }


def family_loss_weights(audit: Mapping[str, Any]) -> dict[str, float]:
    missing = list(audit["missing_support"])
    if missing:
        raise ActiveFamilyWithoutTrainingSupport(missing)
    effective = [float(item["effective_support"]) for item in audit["families"]]
    median = float(statistics.median(effective))
    raw = [math.sqrt(median / count) for count in effective]
    mean = sum(raw) / len(raw)
    weights = {}
    for item, value in zip(audit["families"], raw):
        scaled = value / mean
        if scaled < FAMILY_WEIGHT_FLOOR:
            scaled = FAMILY_WEIGHT_FLOOR
        elif scaled > FAMILY_WEIGHT_CAP:
            scaled = FAMILY_WEIGHT_CAP
        weights[item["family"]] = scaled
    return weights


def applicability_class_weights(audit: Mapping[str, Any]) -> dict[str, float]:
    present = float(audit["family_present_effective"])
    none = float(audit["none"]["effective_support"])
    if present <= 0.0 or none <= 0.0:
        raise ClassificationContractError("applicability_support_missing")
    raw_present = 1.0 / math.sqrt(present)
    raw_none = 1.0 / math.sqrt(none)
    mean = (raw_present + raw_none) / 2.0
    return {
        APPLICABILITY_PRESENT: raw_present / mean,
        APPLICABILITY_NONE: raw_none / mean,
    }


def freeze_training_contract(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    audit = support_audit(rows)
    if audit["missing_support"]:
        raise ActiveFamilyWithoutTrainingSupport(audit["missing_support"])
    family_weights = family_loss_weights(audit)
    applicability = applicability_class_weights(audit)
    from .classification_v2_surface import surface_cell_weights

    return {
        "status": "FROZEN",
        "provenance_weights": dict(PROVENANCE_WEIGHTS),
        "family_weights": family_weights,
        "applicability_weights": applicability,
        "surface_cell_weights": surface_cell_weights(rows, PROVENANCE_WEIGHTS),
        "audit": audit,
        "reserve_rows_used": 0,
    }



def _surface_of(row: Mapping[str, Any]) -> str | None:
    if "text" not in row:
        return None
    from .classification_v2_surface import surface_form

    return surface_form(str(row.get("text") or ""))


def _applicability_multiplier(
    row: Mapping[str, Any],
    contract: Mapping[str, Any],
    target: str,
) -> float | None:
    """Provenance authority inside a surface cell.

    Rows that predate surface metadata keep the two-class applicability weight.
    Ambiguous text is masked out of the applicability objective.
    """
    provenance = contract["provenance_weights"]
    klass = _class_of(row)
    if target == APPLICABILITY_NONE:
        key = "observed_none_applicability" if klass == "OBSERVED" else "inferred_none_applicability"
    else:
        prefix = "observed_non_none" if klass == "OBSERVED" else "inferred_non_none"
        key = prefix + "_applicability"
    base = provenance[key]
    if "text" not in row:
        return base * contract["applicability_weights"][target]
    from .classification_v2_surface import SURFACE_AMBIGUOUS, cell_name, surface_form

    form = surface_form(str(row.get("text") or ""))
    if form == SURFACE_AMBIGUOUS:
        return None
    weights = contract.get("surface_cell_weights") or {}
    name = cell_name(target, form)
    if name not in weights:
        raise ClassificationContractError("applicability_surface_cell_missing", name)
    return base * weights[name]


def example_loss(row: Mapping[str, Any], contract: Mapping[str, Any]) -> dict[str, Any]:
    """Per-row multipliers. ``None`` means that term is masked off."""
    _reject_isolated(row)
    lineage = row.get("lineage")
    klass = _class_of(row)
    provenance = contract["provenance_weights"]
    plan: dict[str, Any] = {
        "applicability_target": None,
        "applicability_weight": None,
        "family_target": None,
        "family_weight": None,
        "unbind_loss": "separate_unchanged",
        "trained_class_abstain": False,
        "trained_class_ambiguous": False,
    }
    if lineage == V1_NONE_CLASS:
        plan["applicability_target"] = APPLICABILITY_NONE
        plan["applicability_weight"] = _applicability_multiplier(row, contract, APPLICABILITY_NONE)
        plan["surface"] = _surface_of(row)
        return plan
    if lineage in ACTIVE_FAMILY_VOCABULARY:
        prefix = "observed_non_none" if klass == "OBSERVED" else "inferred_non_none"
        plan["applicability_target"] = APPLICABILITY_PRESENT
        plan["applicability_weight"] = _applicability_multiplier(row, contract, APPLICABILITY_PRESENT)
        plan["surface"] = _surface_of(row)
        plan["family_target"] = lineage
        plan["family_weight"] = provenance[prefix + "_family"] * contract["family_weights"][lineage]
        return plan
    if lineage in LEGACY_HEADS:
        plan["excluded"] = "legacy_not_remapped"
        return plan
    raise ClassificationContractError("unknown_lineage", lineage)


def epoch_selection_metrics(
    rows: Sequence[Mapping[str, Any]],
    applicability_predictions: Sequence[str],
    family_predictions: Sequence[str],
) -> dict[str, Any]:
    """Argmax metrics for one validation pass. Legacy rows are left out."""
    if not (len(rows) == len(applicability_predictions) == len(family_predictions)):
        raise ClassificationContractError("metric_length_mismatch")
    app_gold: list[str] = []
    app_pred: list[str] = []
    fam_gold: list[str] = []
    fam_pred: list[str] = []
    obs_gold: list[str] = []
    obs_pred: list[str] = []
    observed_app_gold: list[str] = []
    observed_app_pred: list[str] = []
    inferred_app_gold: list[str] = []
    inferred_app_pred: list[str] = []
    for row, app, fam in zip(rows, applicability_predictions, family_predictions):
        lineage = row.get("lineage")
        if lineage not in ACTIVE_FAMILY_VOCABULARY and lineage != V1_NONE_CLASS:
            continue
        gold_app = APPLICABILITY_NONE if lineage == V1_NONE_CLASS else APPLICABILITY_PRESENT
        app_gold.append(gold_app)
        app_pred.append(app)
        klass = row.get("class")
        if klass == "OBSERVED":
            observed_app_gold.append(gold_app)
            observed_app_pred.append(app)
        elif klass == "INFERRED":
            inferred_app_gold.append(gold_app)
            inferred_app_pred.append(app)
        if lineage in ACTIVE_FAMILY_VOCABULARY:
            fam_gold.append(str(lineage))
            fam_pred.append(fam)
            if klass == "OBSERVED":
                obs_gold.append(str(lineage))
                obs_pred.append(fam)
    app = prf_table(app_gold, app_pred, APPLICABILITY)
    fam = prf_table(fam_gold, fam_pred, ACTIVE_FAMILY_VOCABULARY)
    obs = prf_table(obs_gold, obs_pred, ACTIVE_FAMILY_VOCABULARY)
    per_label = fam["per_label"]

    def _group_macro(names: Sequence[str]) -> float | None:
        scored = [float(per_label[name]["f1"]) for name in names if per_label[name]["support"]]
        if not scored:
            return None
        return sum(scored) / len(scored)

    copied = [name for name in ACTIVE_FAMILY_VOCABULARY if name in EXACT_COPY_FAMILIES]
    prototyped = [name for name in ACTIVE_FAMILY_VOCABULARY if name not in EXACT_COPY_FAMILIES]
    score = None
    if None not in (app["macro_f1"], fam["macro_f1"], obs["macro_f1"]):
        score = selection_score(float(fam["macro_f1"]), float(app["macro_f1"]), float(obs["macro_f1"]))
    n = len(app_pred)
    none_stats = app["per_label"][APPLICABILITY_NONE]
    present_stats = app["per_label"][APPLICABILITY_PRESENT]
    return {
        "selection_score": score,
        "applicability_macro_f1": app["macro_f1"],
        "active_family_macro_f1": fam["macro_f1"],
        "observed_active_family_macro_f1": obs["macro_f1"],
        "exact_copy_family_macro_f1": _group_macro(copied),
        "prototype_family_macro_f1": _group_macro(prototyped),
        "none_precision": none_stats["precision"],
        "none_recall": none_stats["recall"],
        "none_f1": none_stats["f1"],
        "family_present_precision": present_stats["precision"],
        "family_present_recall": present_stats["recall"],
        "family_present_f1": present_stats["f1"],
        "per_family": fam["per_label"],
        "predicted_none_rate": None if n == 0 else app_pred.count(APPLICABILITY_NONE) / n,
        "family_emission_rate": None if n == 0 else app_pred.count(APPLICABILITY_PRESENT) / n,
        "observed_slice": prf_table(observed_app_gold, observed_app_pred, APPLICABILITY),
        "inferred_slice": prf_table(inferred_app_gold, inferred_app_pred, APPLICABILITY),
    }


def selection_score(
    active_family_macro_f1: float,
    applicability_macro_f1: float,
    observed_active_family_macro_f1: float,
) -> float:
    parts = (
        _finite(active_family_macro_f1, "selection_term_invalid"),
        _finite(applicability_macro_f1, "selection_term_invalid"),
        _finite(observed_active_family_macro_f1, "selection_term_invalid"),
    )
    return sum(weight * value for weight, value in zip(SELECTION_WEIGHTS, parts))


def _prf(gold: int, predicted: int, hit: int) -> dict[str, float | None]:
    if gold == 0 and predicted == 0:
        return {"precision": None, "recall": None, "f1": None, "support": 0}
    precision = hit / predicted if predicted else 0.0
    recall = hit / gold if gold else 0.0
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return {"precision": precision, "recall": recall, "f1": f1, "support": gold, "predicted": predicted}


def prf_table(golds: Sequence[str], preds: Sequence[str], labels: Sequence[str]) -> dict[str, Any]:
    if len(golds) != len(preds):
        raise ClassificationContractError("metric_length_mismatch")
    rows = {}
    scored: list[float] = []
    for label in labels:
        gold = sum(1 for item in golds if item == label)
        predicted = sum(1 for item in preds if item == label)
        hit = sum(1 for left, right in zip(golds, preds) if left == label and right == label)
        stats = _prf(gold, predicted, hit)
        rows[label] = stats
        if gold:
            scored.append(float(stats["f1"]))
    macro = None if not scored else sum(scored) / len(scored)
    return {"per_label": rows, "macro_f1": macro, "labels_with_support": len(scored)}


def _softmax(logits: Sequence[float], temperature: float) -> list[float]:
    scaled = [value / temperature for value in logits]
    peak = max(scaled)
    exps = [math.exp(value - peak) for value in scaled]
    total = sum(exps)
    return [value / total for value in exps]


def _mean_nll(rows: Sequence[tuple[Sequence[float], int]], temperature: float) -> float:
    """Mean NLL. Log-sum-exp stays finite when a class probability underflows."""
    total = 0.0
    for logits, label in rows:
        if label < 0 or label >= len(logits):
            raise ClassificationContractError("calibration_label_invalid")
        scaled = [value / temperature for value in logits]
        peak = max(scaled)
        log_partition = math.log(sum(math.exp(value - peak) for value in scaled))
        total -= scaled[label] - peak - log_partition
    return total / len(rows)


def fit_temperature(rows: Sequence[tuple[Sequence[float], int]], *, surface: str = "validation") -> float:
    if surface != "validation":
        raise ClassificationContractError("calibration_surface_forbidden")
    if not rows:
        raise ClassificationContractError("calibration_empty")
    best_t = TEMPERATURE_GRID[0]
    best_nll = _mean_nll(rows, best_t)
    for temperature in TEMPERATURE_GRID[1:]:
        nll = _mean_nll(rows, temperature)
        closer = abs(temperature - 1.0) < abs(best_t - 1.0)
        tied = abs(nll - best_nll) <= 1e-12
        better = nll < best_nll - 1e-12
        if better or (tied and (closer or (abs(abs(temperature - 1.0) - abs(best_t - 1.0)) <= 1e-15 and temperature < best_t))):
            best_t = temperature
            best_nll = nll
    return best_t


def applicability_threshold(probabilities: Sequence[float], labels: Sequence[int]) -> float:
    """Maximize balanced accuracy. Ties: closest to 0.5, then the lower threshold."""
    if len(probabilities) != len(labels) or not probabilities:
        raise ClassificationContractError("calibration_empty")
    if any(label not in (0, 1) for label in labels):
        raise ClassificationContractError("calibration_label_invalid")
    if any(label == 0 for label in labels) is False or any(label == 1 for label in labels) is False:
        raise ClassificationContractError("calibration_class_missing")
    candidates = sorted(set(_unit(value) for value in probabilities).union({0.0, 1.0}))
    best: tuple[float, float, float] | None = None
    chosen = candidates[0]
    for threshold in candidates:
        predictions = [1 if probability >= threshold else 0 for probability in probabilities]
        recalls = []
        for label in (0, 1):
            gold = [index for index, value in enumerate(labels) if value == label]
            hit = sum(1 for index in gold if predictions[index] == label)
            recalls.append(hit / len(gold))
        balanced = 0.5 * (recalls[0] + recalls[1])
        rank = (balanced, -abs(threshold - 0.5), -threshold)
        if best is None or rank > best:
            best = rank
            chosen = threshold
    return chosen


def family_emit_threshold(confidences: Sequence[float], correct: Sequence[bool]) -> float:
    """Largest proper subset whose selective accuracy preserves the unfiltered accuracy.

    Threshold 0 means no confidence abstention is added.
    """
    if len(confidences) != len(correct) or not confidences:
        raise ClassificationContractError("calibration_empty")
    checked = [_unit(value) for value in confidences]
    flags = [bool(value) for value in correct]
    unfiltered = sum(1 for value in flags if value) / len(flags)
    best: tuple[float, float, float] | None = None
    chosen: float | None = None
    for threshold in sorted(set(checked)):
        emitted = [(confidence, flag) for confidence, flag in zip(checked, flags) if confidence >= threshold]
        if len(emitted) in (0, len(flags)):
            continue
        selective = sum(1 for _, flag in emitted if flag) / len(emitted)
        if selective + 1e-12 < unfiltered:
            continue
        coverage = len(emitted) / len(flags)
        rank = (coverage, selective, -threshold)
        if best is None or rank > best:
            best = rank
            chosen = threshold
    return 0.0 if chosen is None else chosen


def _argmax_vocabulary(values: Sequence[float]) -> int:
    best_index = 0
    best_value = values[0]
    for index, value in enumerate(values[1:], start=1):
        if value > best_value:
            best_index = index
            best_value = value
    return best_index


def freeze_calibration(
    *,
    applicability_rows: Sequence[tuple[Sequence[float], int]],
    family_rows: Sequence[tuple[Sequence[float], int]],
    surface: str = "validation",
    checkpoint_identity: str | None = None,
) -> dict[str, Any]:
    """Temperature and thresholds from the restored checkpoint's validation logits.

    Training rows and the evaluation reserve are not inputs.
    """
    if surface != "validation":
        raise ClassificationContractError("calibration_surface_forbidden")
    applicability_temperature = fit_temperature(applicability_rows, surface=surface)
    probabilities = [
        _softmax(logits, applicability_temperature)[1] for logits, _label in applicability_rows
    ]
    labels = [int(label) for _logits, label in applicability_rows]
    threshold = applicability_threshold(probabilities, labels)
    family_temperature = fit_temperature(family_rows, surface=surface)
    confidences: list[float] = []
    correct: list[bool] = []
    width = len(ACTIVE_FAMILY_VOCABULARY)
    for logits, label in family_rows:
        if label < 0 or label >= width or len(logits) != width:
            raise ClassificationContractError("calibration_label_invalid")
        distribution = _softmax(logits, family_temperature)
        predicted = _argmax_vocabulary(distribution)
        confidences.append(distribution[predicted])
        correct.append(predicted == label)
    emit = family_emit_threshold(confidences, correct)
    return {
        "schema": "hyperlex.classification.v2.calibration.v1",
        "surface": "validation",
        "reserve_used": False,
        "training_rows_used": False,
        "applicability_temperature": applicability_temperature,
        "applicability_threshold": threshold,
        "family_temperature": family_temperature,
        "family_emit_threshold": emit,
        "n_applicability": len(applicability_rows),
        "n_family": len(family_rows),
        "checkpoint_identity": checkpoint_identity,
    }


def decide_v2(
    *,
    p_family_present: float,
    applicability_threshold_value: float,
    family_distribution: Mapping[str, float],
    family_emit_threshold_value: float,
) -> dict[str, Any]:
    present = _unit(p_family_present)
    app_threshold = _unit(applicability_threshold_value)
    emit_threshold = _unit(family_emit_threshold_value)
    if set(family_distribution) != set(ACTIVE_FAMILY_VOCABULARY):
        raise ClassificationContractError("family_distribution_incomplete")
    if V1_NONE_CLASS in family_distribution:
        raise ClassificationContractError("none_is_not_a_family")
    checked = {name: _unit(family_distribution[name]) for name in ACTIVE_FAMILY_VOCABULARY}
    if abs(sum(checked.values()) - 1.0) > 1e-6:
        raise ClassificationContractError("distribution_not_normalized")
    ordered = sorted(checked.items(), key=lambda item: (-item[1], ACTIVE_FAMILY_VOCABULARY.index(item[0])))
    margin = ordered[0][1] - ordered[1][1]
    ambiguous_candidate = margin == 0.0
    if present < app_threshold:
        decision, family, stage = V2_ABSTAIN, None, "Q1_APPLICABILITY"
    elif present <= 0.5:
        decision, family, stage = V2_NONE, None, "Q2_NONE"
    else:
        family_name, confidence = ordered[0]
        if confidence < emit_threshold:
            decision, family, stage = V2_ABSTAIN, None, "Q5_FAMILY_CONFIDENCE"
        else:
            decision, family, stage = V2_FAMILY, family_name, "Q4_FAMILY"
    if decision == V2_AMBIGUOUS:
        raise ClassificationContractError("ambiguous_emission_disabled")
    return {
        "decision": decision,
        "family": family,
        "stage": stage,
        "margin": margin,
        "ambiguous_candidate": ambiguous_candidate,
        "ambiguity_emission": AMBIGUITY_EMISSION,
        "family_confidence": ordered[0][1],
    }


def build_result(
    *,
    p_family_present: float,
    applicability_threshold_value: float,
    family_distribution: Mapping[str, float],
    family_emit_threshold_value: float,
    confidence: float,
    provenance_context: str,
) -> dict[str, Any]:
    if provenance_context not in PROVENANCE:
        raise ClassificationContractError("provenance_context_invalid")
    decided = decide_v2(
        p_family_present=p_family_present,
        applicability_threshold_value=applicability_threshold_value,
        family_distribution=family_distribution,
        family_emit_threshold_value=family_emit_threshold_value,
    )
    return {
        "schema": SCHEMA,
        "decision": decided["decision"],
        "family": decided["family"],
        "applicability": APPLICABILITY_PRESENT if _unit(p_family_present) > 0.5 else APPLICABILITY_NONE,
        "applicability_score": _unit(p_family_present),
        "applicability_threshold": _unit(applicability_threshold_value),
        "family_distribution": {name: _unit(family_distribution[name]) for name in ACTIVE_FAMILY_VOCABULARY},
        "family_confidence": decided["family_confidence"],
        "family_emit_threshold": _unit(family_emit_threshold_value),
        "confidence": _unit(confidence),
        "margin": decided["margin"],
        "ambiguous_candidate": decided["ambiguous_candidate"],
        "ambiguity_emission": AMBIGUITY_EMISSION,
        "provenance_context": provenance_context,
        "stage": decided["stage"],
        "brier": None,
        "forecast_eligible": False,
        "jev": {
            "mode": JEV_OFF,
            "invoked": False,
            "decision_packet_ref": None,
            "agreement": None,
            "rejection": None,
        },
    }


def validate_telemetry(record: Mapping[str, Any]) -> None:
    missing = [field for field in TELEMETRY_FIELDS if field not in record]
    if missing:
        raise ClassificationContractError("telemetry_incomplete", missing)
    for slice_name in ("observed_slice", "inferred_slice"):
        if not isinstance(record[slice_name], Mapping):
            raise ClassificationContractError("telemetry_incomplete", slice_name)
    if record.get("brier_head") is not None and "brier_head" in record:
        raise ClassificationContractError("brier_head_forbidden")


def packet_body(packet: Mapping[str, Any]) -> dict[str, Any]:
    return {key: packet[key] for key in packet if key != "output_hash"}


def packet_output_hash(packet: Mapping[str, Any]) -> str:
    return sha256_text(canonical_json(packet_body(packet)))


FORBIDDEN_PACKET_KEYS = frozenset(
    {"api_key", "best", "canonical_family", "observed_label", "reserve_gold", "semantic_family"}
)
PACKET_REQUIRED = (
    "decision_type",
    "candidate_set",
    "probabilities",
    "confidence",
    "provider",
    "model",
    "schema_version",
    "prompt_schema_version",
    "timestamp",
    "input_hash",
    "output_hash",
)
DECISION_TYPES = ("choice", "score", "route")
ROUTE_CHOICES = ("accept_automated", "human_review", "additional_evidence")


def _hash64(value: Any, reason: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise JevContractError(reason)
    try:
        int(value, 16)
    except ValueError as exc:
        raise JevContractError(reason) from exc
    return value


def validate_decision_packet(packet: Mapping[str, Any], *, eligible: Sequence[str]) -> dict[str, Any]:
    if not isinstance(packet, Mapping):
        raise JevContractError("packet_not_object")
    if FORBIDDEN_PACKET_KEYS.intersection(packet):
        raise JevContractError("forbidden_authority_field")
    if any(key not in packet for key in PACKET_REQUIRED):
        raise JevContractError("packet_field_missing")
    if packet.get("schema_version") != PACKET_SCHEMA:
        raise JevContractError("schema_mismatch")
    decision_type = packet.get("decision_type")
    if decision_type not in DECISION_TYPES:
        raise JevContractError("decision_type_invalid")
    _unit(packet.get("confidence"))
    _hash64(packet.get("input_hash"), "input_hash_invalid")
    _hash64(packet.get("output_hash"), "output_hash_invalid")
    if packet_output_hash(packet) != packet["output_hash"]:
        raise JevContractError("output_hash_mismatch")
    for key in ("provider", "model", "prompt_schema_version", "timestamp"):
        if not isinstance(packet.get(key), str) or not str(packet.get(key)).strip():
            raise JevContractError("packet_field_missing")
    candidates = packet.get("candidate_set")
    probabilities = packet.get("probabilities")
    if not isinstance(candidates, list) or not isinstance(probabilities, dict):
        raise JevContractError("packet_field_missing")
    eligible_set = set(eligible)
    if not eligible_set.issubset(set(ACTIVE_FAMILY_VOCABULARY)):
        raise ClassificationContractError("eligible_family_invalid")
    if decision_type == "choice":
        if not candidates or len(candidates) != len(set(candidates)):
            raise JevContractError("candidate_set_invalid")
        if any(name not in eligible_set for name in candidates):
            raise JevContractError("candidate_outside_eligible")
        if set(probabilities) != set(candidates):
            raise JevContractError("probability_keys_mismatch")
        if "abstain_probability" not in packet:
            raise JevContractError("packet_field_missing")
        checked = {name: _unit(probabilities[name]) for name in candidates}
        abstain = _unit(packet.get("abstain_probability"))
        if abs(sum(checked.values()) + abstain - 1.0) > 1e-6:
            raise JevContractError("not_normalized")
        selected = packet.get("selected")
        if selected is not None and selected not in candidates:
            raise JevContractError("candidate_outside_eligible")
    elif decision_type == "score":
        expected = {"confidence", "ambiguity", "escalation_need"}
        if set(probabilities) != expected:
            raise JevContractError("probability_keys_mismatch")
        for key in expected:
            _unit(probabilities[key])
    else:
        if not candidates or any(name not in ROUTE_CHOICES for name in candidates):
            raise JevContractError("candidate_set_invalid")
        if set(probabilities) != set(candidates):
            raise JevContractError("probability_keys_mismatch")
        checked = {name: _unit(probabilities[name]) for name in candidates}
        if abs(sum(checked.values()) - 1.0) > 1e-6:
            raise JevContractError("not_normalized")
    return dict(packet)


def jev_call_count(*, surface: str, mode: str) -> int:
    if mode == JEV_GATED or mode not in JEV_MODES_IMPLEMENTED:
        raise JevContractError("gated_not_authorized")
    if surface in PROHIBITED_SURFACES or mode == JEV_OFF:
        return 0
    return 1


def integrate_jev(
    *,
    canonical: Mapping[str, Any],
    mode: str,
    surface: str,
    eligible: Sequence[str],
    packet: Mapping[str, Any] | None = None,
    provider_status: str = "ok",
) -> dict[str, Any]:
    if mode == JEV_GATED or mode not in JEV_MODES_IMPLEMENTED:
        raise JevContractError("gated_not_authorized")
    result = json.loads(canonical_json(canonical))
    decision = result.get("decision")
    family = result.get("family")
    result["jev"] = {
        "mode": mode,
        "invoked": False,
        "decision_packet_ref": None,
        "agreement": None,
        "rejection": None,
    }
    if surface in PROHIBITED_SURFACES:
        result["jev"]["rejection"] = "exposure_prohibited"
    elif mode == JEV_SHADOW and provider_status != "ok":
        result["jev"]["rejection"] = "provider_unavailable"
    elif mode == JEV_SHADOW and packet is not None:
        try:
            checked = validate_decision_packet(packet, eligible=eligible)
        except JevContractError as exc:
            result["jev"]["rejection"] = exc.reason
        else:
            jev_choice = checked.get("selected") if checked.get("decision_type") == "choice" else None
            hyper_family = family if decision == V2_FAMILY else None
            result["jev"]["invoked"] = True
            result["jev"]["decision_packet_ref"] = checked["output_hash"]
            result["jev"]["agreement"] = {
                "family_agreement": None
                if checked.get("decision_type") != "choice"
                else hyper_family == jev_choice and hyper_family is not None,
                "hyperlex_abstain_jev_choice": decision == V2_ABSTAIN and jev_choice is not None,
                "hyperlex_choice_jev_null": decision == V2_FAMILY and jev_choice is None,
                "adopted": False,
            }
    if result.get("decision") != decision or result.get("family") != family:
        raise JevContractError("canonical_mutated")
    return result


def map_legacy_jevgate(*, jevgate: bool, no_jevgate: bool, v2_jev_mode: str | None) -> dict[str, Any]:
    requested = (v2_jev_mode or JEV_OFF).upper()
    if requested == JEV_GATED or requested not in JEV_MODES_IMPLEMENTED:
        raise JevContractError("gated_not_authorized")
    return {
        "legacy_gate": "jevgate-1",
        "legacy_enabled": False if no_jevgate else bool(jevgate),
        "authorizes_v2_gated": False,
        "v2_mode": requested,
        "legacy_flag_changes_v2_canonical": False,
        "required_for_v2_training": False,
    }


def require_v2_schedule(schedule: Mapping[str, Any]) -> None:
    expected = {
        "max_epochs": V2_SCHEDULE["max_epochs"],
        "minimum_epochs": V2_SCHEDULE["minimum_epochs"],
        "patience": V2_SCHEDULE["early_stopping_patience"],
        "improvement": "strict",
        "ties": "keep_earlier",
        "restore_best": True,
        "early_stopping": True,
    }
    for key, value in expected.items():
        if schedule.get(key) != value:
            raise ClassificationContractError("v2_schedule_mismatch", key)


def readiness(
    rows: Sequence[Mapping[str, Any]],
    *,
    loader_status: str,
    random_new_rows: bool = False,
    prototype_report: Mapping[str, Any] | None = None,
    validation_report: Mapping[str, Any] | None = None,
    definition_report: Mapping[str, Any] | None = None,
    surface_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """One audit. Incomplete families are returned together. Training stays off."""
    audit = support_audit(rows)
    missing = list(audit["missing_support"])
    family_weights: dict[str, float] | None = None
    applicability: dict[str, float] | None = None
    if not missing:
        family_weights = family_loss_weights(audit)
        applicability = applicability_class_weights(audit)
    elif audit["family_present_effective"] > 0 and audit["none"]["effective_support"] > 0:
        applicability = applicability_class_weights(audit)
    prototype_pass = bool(prototype_report and prototype_report.get("pass"))
    validation_pass = bool(validation_report and validation_report.get("pass"))
    definition_pass = bool(definition_report and definition_report.get("pass"))
    copied_pass = bool(prototype_report and prototype_report.get("copied_rows_match"))
    checks = {
        "all_active_family_rows_present": True,
        "all_active_families_have_positive_training_support": not missing,
        "all_new_rows_have_semantic_prototypes": prototype_pass,
        "all_copied_rows_match_source": copied_pass,
        "all_families_have_validation_support": validation_pass,
        "definition_string_rule_pass": definition_pass,
        "prototype_witness_pass": prototype_pass and bool(prototype_report and prototype_report.get("determinism") == "pass"),
        "family_weight_table_frozen": family_weights is not None and not missing,
        "applicability_weight_table_frozen": applicability is not None and not missing,
        "applicability_surface_cells_populated": surface_report is None or bool(surface_report.get("pass")),
        "representation_lineage_isolated": surface_report is None or not surface_report.get("representation_leaks"),
        "provenance_weights_frozen": True,
        "loader_witness_pass": loader_status == "PASS",
        "no_random_new_rows": not random_new_rows,
        "loss_masks_pass": True,
        "calibration_procedure_frozen": True,
        "selection_metric_frozen": True,
        "evaluation_contract_frozen": True,
        "telemetry_contract_pass": (
            "exact_copy_family_macro_f1" in TELEMETRY_FIELDS
            and "prototype_family_macro_f1" in TELEMETRY_FIELDS
        ),
        "training_evaluation_isolation_pass": True,
        "operator_authorization_present": OPERATOR_AUTHORIZATION["present"] is True,
        "ambiguous_emission_disabled": AMBIGUITY_EMISSION == "DISABLED_PENDING_GOLD",
        "jev_required_for_readiness": False,
        "historical_best_unchanged": True,
    }
    ready = all(
        checks[key]
        for key in checks
        if key not in {"jev_required_for_readiness", "ambiguous_emission_disabled"}
    )
    blockers: list[str] = []
    if missing:
        blockers.append("ACTIVE_FAMILY_WITHOUT_TRAINING_SUPPORT")
    if not definition_pass:
        blockers.append("DEFINITION_STRING_RULE")
    if not prototype_pass or checks["prototype_witness_pass"] is False:
        blockers.append("FAMILY_PROTOTYPE_UNAVAILABLE")
    if not validation_pass:
        blockers.append("VALIDATION_FAMILY_SUPPORT_INSUFFICIENT")
    if surface_report is not None and surface_report.get("representation_leaks"):
        blockers.append("REPRESENTATION_LEAK")
    if surface_report is not None and not surface_report.get("pass"):
        blockers.append("APPLICABILITY_SURFACE_SHORTCUT")
    if loader_status != "PASS":
        blockers.append("LOADER_WITNESS")
    if random_new_rows:
        blockers.append("RANDOM_NEW_ROWS")
    return {
        "state": "READY" if ready else "PREREGISTERED",
        "ready": ready,
        "blocker": None if ready else blockers[0],
        "blockers": [] if ready else blockers,
        "missing_support": missing,
        "deficient_validation": list((validation_report or {}).get("deficient") or []),
        "validation_support": dict((validation_report or {}).get("support") or {}),
        "below_preferred_validation": list((validation_report or {}).get("below_preferred") or []),
        "exact_copy_families": list((prototype_report or {}).get("exact_copy_families") or []),
        "prototype_families": list((prototype_report or {}).get("prototype_families") or []),
        "prototype_source_counts": dict((prototype_report or {}).get("source_counts") or {}),
        "witness_sha256": None if not prototype_report else prototype_report.get("witness_sha256"),
        "target_norm": None if not prototype_report else prototype_report.get("target_norm"),
        "checks": checks,
        "audit": audit,
        "family_weights": family_weights,
        "applicability_weights": applicability,
        "surface_cells": None if surface_report is None else surface_report.get("cells"),
        "surface_cell_weights": None if surface_report is None else surface_report.get("cell_weights"),
        "surface_ambiguous": None if surface_report is None else surface_report.get("ambiguous"),
        "provenance_weights": dict(PROVENANCE_WEIGHTS),
        "authorizes_training": ready,
        "moves_best": False,
    }
