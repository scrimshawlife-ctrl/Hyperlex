"""Translate HyperlexObservation → Abraxas-native advisory evidence.

Translation and provenance preservation only.
Does not embed semantic business logic.
Does not promote Hyperlex evidence to canonical / gold / authorization.
"""

from __future__ import annotations

from typing import Any, Mapping

# Ubiquitous Abraxas lane language
ABRAXAS_ROLES = ("OBSERVATION", "EVIDENCE", "SHADOW_SIGNAL")
FORBIDDEN_PROMOTIONS = (
    "CANONICAL_STATE",
    "GOLD",
    "FINAL_INTERPRETATION",
    "AUTHORIZATION",
)


class AuthorityBoundaryError(ValueError):
    """Raised when a caller attempts to treat Hyperlex as semantic truth."""


def to_abraxas_evidence(
    observation: Mapping[str, Any],
    *,
    role: str = "SHADOW_SIGNAL",
) -> dict[str, Any]:
    """Convert a HyperlexObservation into an Abraxas advisory evidence object."""
    if role not in ABRAXAS_ROLES:
        raise AuthorityBoundaryError(
            f"role must be one of {ABRAXAS_ROLES}, not {role!r}"
        )
    if role in FORBIDDEN_PROMOTIONS:
        raise AuthorityBoundaryError("forbidden promotion role")

    auth = observation.get("authority") or {}
    if auth.get("semantic_truth") is True:
        raise AuthorityBoundaryError(
            "refusing observation that claims semantic_truth=true"
        )
    if auth.get("kind") != "advisory":
        raise AuthorityBoundaryError("observation authority.kind must be advisory")

    prov = observation.get("provenance") or {}
    evidence = observation.get("evidence") or {}
    diagnostics = observation.get("diagnostics") or {}

    candidates = []
    for c in observation.get("candidates") or []:
        if c.get("advisory") is not True:
            raise AuthorityBoundaryError(
                "non-advisory candidate cannot cross Abraxas boundary"
            )
        candidates.append(
            {
                "concept_id": c["concept_id"],
                "score": c["score"],
                "axis": c["axis"],
                "advisory": True,
                "status": c.get("status", "advisory"),
            }
        )

    return {
        "schema": "abraxas.evidence.hyperlex_instrument.v1",
        "kind": role,
        "source": "hyperlex",
        "authority": "advisory",
        "semantic_truth": False,
        "may_authorize": False,
        "may_mutate_governing_state": False,
        "may_override_provenance": False,
        "observation_id": observation.get("observation_id"),
        "input_hash": observation.get("input_hash"),
        "evidence": {
            "present": bool(evidence.get("present")),
            "score": evidence.get("score"),
            "abstain": bool(evidence.get("abstain")),
            "reason": evidence.get("reason"),
        },
        "candidates": candidates,
        "neighborhood": list(observation.get("neighborhood") or []),
        "ambiguity": diagnostics.get("ambiguity"),
        "margin": diagnostics.get("margin"),
        "diagnostics": {
            "distribution_distance": diagnostics.get("distribution_distance"),
            "representation_drift": diagnostics.get("representation_drift"),
            "unavailable": list(diagnostics.get("unavailable") or []),
        },
        "representation": {
            "encoder_id": (observation.get("representation") or {}).get("encoder_id"),
            "encoder_hash": (observation.get("representation") or {}).get(
                "encoder_hash"
            ),
            "embed_mode": (observation.get("representation") or {}).get("embed_mode"),
            "embedding_ref": (observation.get("representation") or {}).get(
                "embedding_ref"
            ),
        },
        "instrument_version": prov.get("instrument_version"),
        "ontology_version": prov.get("ontology_version"),
        "contract_version": prov.get("contract_version"),
        "manifest_sha256": prov.get("manifest_sha256"),
        "schema_sha256": prov.get("schema_sha256"),
        "settlement_ref": prov.get("settlement_ref"),
        "settlement_receipt": prov.get("settlement_receipt"),
        "artifact_hashes": dict(prov.get("artifact_hashes") or {}),
        "influence_policy": "NONE",
        "valid_for_forecast": False,
        "lane": "shadow",
        "notes": [
            "HYPERLEX_OUTPUT != SEMANTIC_TRUTH",
            "Downstream Abraxas reasoning may consume but must verify.",
            "Promotion into canonical state requires Abraxas rules, not this adapter.",
        ],
    }


def assert_not_authoritative(evidence: Mapping[str, Any]) -> None:
    """Negative guard used by tests and Abraxas intake."""
    if evidence.get("semantic_truth") is True:
        raise AuthorityBoundaryError("semantic_truth must remain false")
    if evidence.get("authority") != "advisory":
        raise AuthorityBoundaryError("authority must remain advisory")
    if evidence.get("may_authorize") is True:
        raise AuthorityBoundaryError("may_authorize must remain false")
    if evidence.get("may_mutate_governing_state") is True:
        raise AuthorityBoundaryError("may_mutate_governing_state must remain false")
    if evidence.get("kind") in FORBIDDEN_PROMOTIONS:
        raise AuthorityBoundaryError("evidence kind must not be a promotion role")
    if evidence.get("valid_for_forecast") is True:
        raise AuthorityBoundaryError("valid_for_forecast must remain false")
    for c in evidence.get("candidates") or []:
        if c.get("advisory") is not True:
            raise AuthorityBoundaryError("candidates must remain advisory")


def promote_to_canonical_state(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Intentionally unsupported — Hyperlex cannot mint Abraxas canonical state."""
    raise AuthorityBoundaryError(
        "Hyperlex evidence cannot become CANONICAL_STATE through the adapter"
    )
