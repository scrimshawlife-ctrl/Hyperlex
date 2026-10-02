"""Machine-readable Hyperlex Instrument V1 capabilities."""

from __future__ import annotations

from typing import Any

from .constants import (
    CLASSIFIER_RELEASE,
    CONTRACT_VERSION,
    INSTRUMENT_VERSION,
    OPERATION_MODE,
    PRODUCT_ROLE,
)


def capabilities() -> dict[str, Any]:
    return {
        "schema": "hyperlex.instrument.capabilities.v1",
        "instrument_version": INSTRUMENT_VERSION,
        "contract_version": CONTRACT_VERSION,
        "product_role": PRODUCT_ROLE,
        "operation_mode": OPERATION_MODE,
        "classifier_release": CLASSIFIER_RELEASE,
        "authority": {
            "HYPERLEX_OUTPUT_EQ_SEMANTIC_TRUTH": False,
            "kind": "advisory",
            "roles": ["OBSERVATION", "EVIDENCE", "SHADOW_SIGNAL"],
            "forbidden_roles": [
                "CANONICAL_STATE",
                "GOLD",
                "FINAL_INTERPRETATION",
                "AUTHORIZATION",
            ],
        },
        "capabilities": {
            "evidence_signal": {
                "status": "supported",
                "notes": "NONE / abstention first-class",
            },
            "representation": {
                "status": "supported",
                "notes": (
                    "STATIC_HASH_EMBEDDING always; MODEL_EMBEDDING only when "
                    "optional encoder weights are present"
                ),
            },
            "domain_candidates": {
                "status": "advisory",
                "notes": "Never hard labels / never semantic truth",
            },
            "mediation_candidates": {
                "status": "advisory",
                "notes": "Never hard labels / never semantic truth",
            },
            "function_candidates": {
                "status": "experimental_or_advisory",
                "notes": "Text-only ceiling; contextual enrichment preferred",
            },
            "memetic_form": {
                "status": "research_only",
                "notes": "Not emitted by instrument runtime",
            },
            "neighborhood": {"status": "supported"},
            "margin": {"status": "supported"},
            "ambiguity": {"status": "supported"},
            "distribution_distance": {
                "status": "unavailable",
                "notes": "Requires sealed operating centroid store; null until available",
            },
            "representation_drift": {
                "status": "unavailable",
                "notes": "Requires longitudinal embedding store; null until available",
            },
            "final_classification": {
                "status": "unsupported",
                "notes": "V6 core classifier REJECTED; observe() is not classify()",
            },
        },
        "primary_operation": "observe",
        "forbidden_operations": ["classify", "authorize", "promote_to_gold"],
    }
