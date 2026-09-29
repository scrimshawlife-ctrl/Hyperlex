"""SELECT reserve routing. Settlement stays untouched.

A routing record is a derivative. It copies the sealed decision, registry
class, and semantic family, then applies ``identity_ledger.slices_of``.
It does not settle, score, or read reserve deficits.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from .eval_settlement import ABSTAIN, ACTIVE_FAMILIES, ATTESTS, DECISIONS, SETTLED_DECISIONS
from .identity_ledger import slices_of

SCHEMA = "hyperlex.eval_routing.v1"
ROUTING_VERSION = "v1"
PROCEDURE_ID = "select_eval_routing_v1"
CLEARED_RIGHTS = "CC-BY-SA"
UNBIND_CLEAN_DERIVATION = "soft_ceiling.clean_surface"
TASKS = ("classify", "unbind")
REGISTRY_CLASSES = ATTESTS
LINEAGES = (ABSTAIN, *ACTIVE_FAMILIES)
ROUTING_STORE = (
    "private evaluation evidence store "
    "eval-reserve-20260926/routing/events.jsonl"
)
_BANNED = frozenset(
    {
        "admission_floors",
        "candidate_score",
        "current_reserve_deficits",
        "desired_select_slice",
        "desired_slice",
        "model_error",
        "model_score",
        "planning_targets",
        "prediction",
        "residual",
        "reserve_counts",
        "routed_counts",
        "semantic_evidence",
        "threshold_v2",
    }
)
_SLICE_CODES = {
    "classify": "SLICE_CLASSIFY",
    "classify_non_none": "SLICE_CLASSIFY_NON_NONE",
    "classify_observed": "SLICE_CLASSIFY_OBSERVED",
    "unbind_clean": "SLICE_UNBIND_CLEAN",
}
RULE_TABLE = {
    "class_meaning": "registry attest class OBSERVED or INFERRED, not the semantic family",
    "cleared_rights": CLEARED_RIGHTS,
    "classify": "task classify; decision ACCEPT, RECLASSIFY, or NONE",
    "classify_non_none": "classify and lineage not empty and not none",
    "classify_observed": "classify and registry class OBSERVED",
    "lineage_meaning": "semantic family, including none",
    "overlap": "one record may enter every classify slice it satisfies; unbind_clean requires task unbind",
    "procedure_id": PROCEDURE_ID,
    "routable_decisions": sorted(SETTLED_DECISIONS),
    "unbind_clean": "task unbind and frozen soft_ceiling.clean_surface is true",
    "unroutable_decisions": ["UNRESOLVED"],
}


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def settlement_hash(record: Mapping[str, Any]) -> str:
    return sha256_text(canonical_json(record))


def procedure_hash() -> str:
    return sha256_text(canonical_json({"procedure_id": PROCEDURE_ID, "rules": RULE_TABLE}))


def _refuse_banned(value: Mapping[str, Any]) -> None:
    found = sorted(_BANNED.intersection(value))
    if found:
        raise SystemExit(
            "REFUSE: routing must not read quota state or model output: " + ",".join(found)
        )


def _slices_for(task: str, registry_class: str, lineage: str, unbind_clean: bool) -> list[str]:
    label: dict[str, Any] = {
        "class": registry_class,
        "lineage": lineage,
        "task": task,
    }
    if task == "unbind":
        label["unbind_clean"] = unbind_clean
    return sorted(slices_of({"labels": [label]}))


def _base(
    settlement: Mapping[str, Any],
    metadata: Mapping[str, Any],
    *,
    status: str,
    reasons: Sequence[str],
    slices: Sequence[str],
    task: str | None,
    registry_class: str | None,
    lineage: str | None,
    unbind_clean: bool | None,
) -> dict[str, Any]:
    text_hash = str(settlement.get("text_hash") or "")
    row_id = str(settlement.get("row_id") or "")
    return {
        "class": registry_class,
        "created_from_frozen_artifact": True,
        "derivation_procedure_hash": procedure_hash(),
        "derivation_procedure_id": PROCEDURE_ID,
        "lineage": lineage,
        "normalized_identity": text_hash,
        "provenance_state": str(metadata.get("provenance_state") or "INCOMPLETE"),
        "rights_state": str(settlement.get("rights") or ""),
        "routing_reason_codes": sorted(set(reasons)),
        "routing_status": status,
        "routing_version": ROUTING_VERSION,
        "row_id": row_id,
        "schema": SCHEMA,
        "settlement_decision": str(settlement.get("decision") or ""),
        "settlement_registry_class": registry_class,
        "slices": list(slices),
        "source_identity": str(metadata.get("source_identity") or ""),
        "source_settlement_hash": settlement_hash(settlement),
        "source_settlement_id": row_id,
        "task": task,
        "unbind_clean": unbind_clean,
    }


def derive_routing(
    settlement: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """One settlement plus frozen metadata. No RNG and no quota read."""
    _refuse_banned(settlement)
    _refuse_banned(metadata)
    decision = settlement.get("decision")
    if decision not in DECISIONS:
        raise SystemExit(f"REFUSE: settlement decision is not canonical: {decision}")
    text_hash = str(settlement.get("text_hash") or "")
    row_id = str(settlement.get("row_id") or "")
    if len(text_hash) != 64 or any(ch not in "0123456789abcdef" for ch in text_hash):
        raise SystemExit("REFUSE: normalized identity is not sha256")
    attest = settlement.get("attest")
    family = settlement.get("semantic_family")
    reasons: list[str] = []
    meta_row = str(metadata.get("row_id") or "")
    if not row_id or meta_row != row_id or str(metadata.get("normalized_identity") or "") != text_hash:
        reasons.append("IDENTITY_CONFLICT")
    provenance_state = str(metadata.get("provenance_state") or "")
    if (
        provenance_state != "COMPLETE"
        or not str(metadata.get("source_identity") or "").strip()
        or not str(settlement.get("provenance") or "").strip()
    ):
        reasons.append("PROVENANCE_INCOMPLETE")
    if str(settlement.get("rights") or "") != CLEARED_RIGHTS:
        reasons.append("RIGHTS_NOT_CLEARED")
    if decision == "UNRESOLVED":
        reasons.append("SETTLEMENT_UNRESOLVED")
    elif decision not in SETTLED_DECISIONS:
        reasons.append("SETTLEMENT_DECISION_NOT_ADMISSIBLE")
    if "class" in metadata and metadata.get("class") != attest:
        reasons.append("CLASS_PROMOTION_REFUSED")
    if "lineage" in metadata and metadata.get("lineage") != family:
        reasons.append("LINEAGE_CONFLICT")
    task = metadata.get("task")
    if task not in TASKS:
        reasons.append("TASK_ABSENT")
        task_out = None
    else:
        task_out = str(task)
    registry_out = attest if attest in REGISTRY_CLASSES else None
    lineage_out = family if isinstance(family, str) and family in LINEAGES else None
    if decision in SETTLED_DECISIONS and registry_out is None:
        reasons.append("REGISTRY_CLASS_ABSENT")
    if decision in SETTLED_DECISIONS and lineage_out is None:
        reasons.append("LINEAGE_ABSENT")
    unbind_flag = metadata.get("unbind_clean") is True
    derivation = metadata.get("unbind_clean_derivation")
    if task_out == "classify" and unbind_flag:
        reasons.append("UNBIND_CLEAN_TASK_MISMATCH")
    if task_out == "unbind" and unbind_flag and derivation != UNBIND_CLEAN_DERIVATION:
        reasons.append("UNBIND_CLEAN_DERIVATION_ABSENT")
    clean_out = False
    if task_out == "unbind" and unbind_flag and derivation == UNBIND_CLEAN_DERIVATION:
        clean_out = True
    if reasons:
        return _base(
            settlement,
            metadata,
            status="INELIGIBLE",
            reasons=reasons,
            slices=[],
            task=task_out,
            registry_class=registry_out,
            lineage=lineage_out,
            unbind_clean=None,
        )
    assert task_out is not None and registry_out is not None and lineage_out is not None
    slices = _slices_for(task_out, registry_out, lineage_out, clean_out)
    if not slices:
        return _base(
            settlement,
            metadata,
            status="INELIGIBLE",
            reasons=["NO_SELECT_SLICE"],
            slices=[],
            task=task_out,
            registry_class=registry_out,
            lineage=lineage_out,
            unbind_clean=clean_out,
        )
    return _base(
        settlement,
        metadata,
        status="ELIGIBLE",
        reasons=[_SLICE_CODES[name] for name in slices],
        slices=slices,
        task=task_out,
        registry_class=registry_out,
        lineage=lineage_out,
        unbind_clean=clean_out,
    )


def derive_batch(
    pairs: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    """First row_id wins. A later copy is a duplicate, not a second route."""
    seen: set[str] = set()
    records = []
    for settlement, metadata in pairs:
        row_id = str(settlement.get("row_id") or "")
        if row_id and row_id in seen:
            records.append(
                _base(
                    settlement,
                    metadata,
                    status="INELIGIBLE",
                    reasons=["DUPLICATE_IDENTITY"],
                    slices=[],
                    task=None,
                    registry_class=settlement.get("attest") if settlement.get("attest") in REGISTRY_CLASSES else None,
                    lineage=settlement.get("semantic_family")
                    if settlement.get("semantic_family") in LINEAGES
                    else None,
                    unbind_clean=None,
                )
            )
            continue
        if row_id:
            seen.add(row_id)
        records.append(derive_routing(settlement, metadata))
    return records


def authorize_for_census(event: Mapping[str, Any], routing: Mapping[str, Any]) -> str:
    """Census may use a routing record only when it still matches the settlement."""
    if routing.get("schema") != SCHEMA or routing.get("routing_status") != "ELIGIBLE":
        return "ROUTING_INELIGIBLE"
    if str(routing.get("row_id") or "") != str(event.get("row_id") or ""):
        return "ROUTING_IDENTITY_MISMATCH"
    if str(routing.get("normalized_identity") or "") != str(event.get("text_hash") or ""):
        return "ROUTING_IDENTITY_MISMATCH"
    if routing.get("source_settlement_hash") != settlement_hash(event):
        return "ROUTING_HASH_MISMATCH"
    if routing.get("rights_state") != CLEARED_RIGHTS:
        return "ROUTING_INELIGIBLE"
    if routing.get("created_from_frozen_artifact") is not True:
        return "ROUTING_REJECTED"
    task = routing.get("task")
    registry_class = routing.get("class")
    lineage = routing.get("lineage")
    if task not in TASKS or registry_class not in REGISTRY_CLASSES or lineage not in LINEAGES:
        return "ROUTING_SLICE_MISMATCH"
    expected = _slices_for(str(task), str(registry_class), str(lineage), routing.get("unbind_clean") is True)
    if list(routing.get("slices") or []) != expected or not expected:
        return "ROUTING_SLICE_MISMATCH"
    return "ELIGIBLE"


def reference_pairs() -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Synthetic corpus. Not a harvest and not the 339 settlements."""
    specs = [
        ("accept-observed", "11", "ACCEPT", "ai-native", "OBSERVED", "CC-BY-SA", "COMPLETE", "classify", False, None),
        ("accept-inferred", "22", "ACCEPT", "technology-ai", "INFERRED", "CC-BY-SA", "COMPLETE", "classify", False, None),
        ("accept-non-none", "33", "ACCEPT", "politics-civic", "INFERRED", "CC-BY-SA", "COMPLETE", "classify", False, None),
        ("accept-unbind", "44", "ACCEPT", "none", "INFERRED", "CC-BY-SA", "COMPLETE", "unbind", True, UNBIND_CLEAN_DERIVATION),
        ("none-classify", "55", "NONE", "none", "INFERRED", "CC-BY-SA", "COMPLETE", "classify", False, None),
        ("unresolved", "66", "UNRESOLVED", None, None, "CC-BY-SA", "COMPLETE", "classify", False, None),
        ("reclassify", "77", "RECLASSIFY", "workplace-career", "INFERRED", "CC-BY-SA", "COMPLETE", "classify", False, None),
        ("rights-blocked", "88", "ACCEPT", "ai-native", "OBSERVED", "RIGHTS_UNRESOLVED", "COMPLETE", "classify", False, None),
        ("provenance-blocked", "99", "ACCEPT", "ai-native", "INFERRED", "CC-BY-SA", "INCOMPLETE", "classify", False, None),
        ("identity-conflict", "ab", "ACCEPT", "ai-native", "INFERRED", "CC-BY-SA", "COMPLETE", "classify", False, None),
    ]
    pairs = []
    for name, nibble, decision, family, attest, rights, provenance_state, task, clean, derivation in specs:
        digest = nibble * 32
        settlement: dict[str, Any] = {
            "attest": attest,
            "decision": decision,
            "provenance": "routing-fixture",
            "rights": rights,
            "row_id": f"route-fixture-{name}",
            "schema": "hyperlex.eval_settlement.v1",
            "semantic_family": family,
            "text_hash": digest,
        }
        metadata: dict[str, Any] = {
            "normalized_identity": digest,
            "provenance_state": provenance_state,
            "row_id": settlement["row_id"],
            "source_identity": f"fixture:{name}",
            "task": task,
            "unbind_clean": clean,
        }
        if name == "provenance-blocked":
            metadata["source_identity"] = ""
        if name == "identity-conflict":
            metadata["normalized_identity"] = "cd" * 32
        if derivation is not None:
            metadata["unbind_clean_derivation"] = derivation
        pairs.append((settlement, metadata))
    inferred = {
        "attest": "INFERRED",
        "decision": "ACCEPT",
        "provenance": "routing-fixture",
        "rights": "CC-BY-SA",
        "row_id": "route-fixture-promotion-refused",
        "schema": "hyperlex.eval_settlement.v1",
        "semantic_family": "ai-native",
        "text_hash": "ef" * 32,
    }
    pairs.append(
        (
            inferred,
            {
                "class": "OBSERVED",
                "normalized_identity": inferred["text_hash"],
                "provenance_state": "COMPLETE",
                "row_id": inferred["row_id"],
                "source_identity": "fixture:promotion-refused",
                "task": "classify",
                "unbind_clean": False,
            },
        )
    )
    classify_as_unbind = {
        "attest": "INFERRED",
        "decision": "ACCEPT",
        "provenance": "routing-fixture",
        "rights": "CC-BY-SA",
        "row_id": "route-fixture-classify-not-unbind",
        "schema": "hyperlex.eval_settlement.v1",
        "semantic_family": "ai-native",
        "text_hash": "ba" * 32,
    }
    pairs.append(
        (
            classify_as_unbind,
            {
                "normalized_identity": classify_as_unbind["text_hash"],
                "provenance_state": "COMPLETE",
                "row_id": classify_as_unbind["row_id"],
                "source_identity": "fixture:classify-not-unbind",
                "task": "classify",
                "unbind_clean": True,
                "unbind_clean_derivation": UNBIND_CLEAN_DERIVATION,
            },
        )
    )
    return pairs


def semantic_errors(record: Mapping[str, Any], settlement: Mapping[str, Any]) -> list[str]:
    """Schema plus the slice, rights, and settlement-hash checks."""
    from .select_contract_schema import routing_schema_errors

    errors = [f"schema: {item}" for item in routing_schema_errors(record)]
    if record.get("source_settlement_hash") != settlement_hash(settlement):
        errors.append("source settlement hash mismatch")
    if record.get("row_id") != settlement.get("row_id"):
        errors.append("row_id mismatch")
    if record.get("normalized_identity") != settlement.get("text_hash"):
        errors.append("normalized identity mismatch")
    if record.get("settlement_decision") != settlement.get("decision"):
        errors.append("decision mismatch")
    status = record.get("routing_status")
    if status == "ELIGIBLE":
        if record.get("rights_state") != CLEARED_RIGHTS:
            errors.append("eligible record is not rights-cleared")
        if record.get("provenance_state") != "COMPLETE":
            errors.append("eligible record is provenance-incomplete")
        if record.get("settlement_decision") not in SETTLED_DECISIONS:
            errors.append("eligible record is not a settled decision")
        if record.get("class") != record.get("settlement_registry_class"):
            errors.append("class drifted from the registry class")
        if record.get("class") != settlement.get("attest"):
            errors.append("class was promoted away from attest")
        if record.get("lineage") != settlement.get("semantic_family"):
            errors.append("lineage drifted from semantic_family")
        expected = _slices_for(
            str(record.get("task")),
            str(record.get("class")),
            str(record.get("lineage")),
            record.get("unbind_clean") is True,
        )
        if list(record.get("slices") or []) != expected:
            errors.append("slices do not match slices_of")
        if "classify_observed" in expected and record.get("class") != "OBSERVED":
            errors.append("classify_observed without OBSERVED")
        if "unbind_clean" in expected and record.get("unbind_clean") is not True:
            errors.append("unbind_clean slice without the frozen flag")
        if record.get("class") == "INFERRED" and "classify_observed" in expected:
            errors.append("INFERRED entered classify_observed")
    elif status == "INELIGIBLE":
        if record.get("slices"):
            errors.append("ineligible record carries slices")
        if not record.get("routing_reason_codes"):
            errors.append("ineligible record has no reason")
    else:
        errors.append("routing_status is not canonical")
    return errors


def contract_validation(
    pairs: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Run the reference corpus twice. Schema and semantic failures stay distinct."""
    corpus = list(pairs) if pairs is not None else reference_pairs()
    first = [derive_routing(settlement, metadata) for settlement, metadata in corpus]
    second = [derive_routing(settlement, metadata) for settlement, metadata in corpus]
    if [canonical_json(row) for row in first] != [canonical_json(row) for row in second]:
        return {
            "determinism": "NOT_IDENTICAL",
            "errors": ["reconstructions differed"],
            "state": "ROUTING_NONDETERMINISTIC",
        }
    errors: list[str] = []
    schema_hit = False
    for record, (settlement, _metadata) in zip(first, corpus):
        found = semantic_errors(record, settlement)
        schema_hit = schema_hit or any(item.startswith("schema:") for item in found)
        errors.extend(f"{record['row_id']}: {item}" for item in found)
    if errors and schema_hit:
        state = "ROUTING_SCHEMA_FAILURE"
    elif errors:
        state = "ROUTING_SEMANTIC_VALIDATION_FAILURE"
    else:
        state = "ROUTING_VALIDATION_COMPLETE"
    return {
        "determinism": "IDENTICAL",
        "errors": errors,
        "procedure_id": PROCEDURE_ID,
        "procedure_sha256": procedure_hash(),
        "schema": SCHEMA,
        "state": state,
    }
