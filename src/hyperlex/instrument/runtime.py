"""HYPERLEX_INSTRUMENT_V1 observe() runtime.

Primary operation is observe — never classify.
"""

from __future__ import annotations

import hashlib
from typing import Any, Optional, Sequence

from hyperlex import PKG_VERSION

from .candidates import build_candidates, build_neighborhood
from .capabilities import capabilities
from .constants import (
    AUTHORITY,
    CONTRACT_VERSION,
    INSTRUMENT_VERSION,
    ONTOLOGY_RECEIPT,
    ONTOLOGY_VERSION,
    SETTLEMENT_RECEIPT,
    SETTLEMENT_REF,
)
from .diagnostics import build_diagnostics
from .evidence import build_evidence
from .manifest import cold_load_manifest, schema_sha256
from .representation import build_representation
from .validate import validate_observation

REQUEST_KEYS = (
    "evidence",
    "representation",
    "candidates",
    "neighborhood",
    "diagnostics",
)


def input_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def observe(
    text: str,
    *,
    requested: Optional[Sequence[str]] = None,
    include_function_candidates: bool = True,
    validate: bool = True,
) -> dict[str, Any]:
    """Canonical instrument operation: text → HyperlexObservation."""
    req = list(requested) if requested else list(REQUEST_KEYS)
    for r in req:
        if r not in REQUEST_KEYS:
            raise ValueError(f"unsupported requested facet: {r}")

    manifest = cold_load_manifest()
    ih = input_hash(text)
    observation_id = hashlib.sha256(
        f"{INSTRUMENT_VERSION}|{ih}|{manifest['manifest_sha256']}".encode("utf-8")
    ).hexdigest()[:24]

    evidence = build_evidence(text) if "evidence" in req else {
        "present": False,
        "score": 0.0,
        "abstain": True,
        "reason": "not_requested",
    }
    representation = (
        build_representation(text)
        if "representation" in req
        else {
            "encoder_id": manifest["encoder"]["id"],
            "encoder_hash": manifest["encoder"]["pin_sha256"],
            "encoder_revision": manifest["encoder"]["revision"],
            "embed_mode": "UNAVAILABLE",
            "embedding": None,
            "embedding_ref": None,
            "dims": None,
        }
    )

    candidates: list[dict[str, Any]] = []
    if "candidates" in req or "neighborhood" in req or "diagnostics" in req:
        # Abstention: do not force semantic candidates without evidence support.
        if evidence.get("abstain") or not evidence.get("present"):
            candidates = []
        else:
            candidates = build_candidates(
                text, include_function=include_function_candidates
            )

    neighborhood = (
        build_neighborhood(candidates) if "neighborhood" in req else []
    )
    diagnostics = (
        build_diagnostics(candidates) if "diagnostics" in req else {
            "margin": None,
            "ambiguity": None,
            "distribution_distance": None,
            "representation_drift": None,
            "unavailable": [
                "margin",
                "ambiguity",
                "distribution_distance",
                "representation_drift",
            ],
        }
    )

    # Strip non-schema helper keys from representation before emit.
    rep_out = {
        k: representation[k]
        for k in (
            "encoder_id",
            "encoder_hash",
            "encoder_revision",
            "embed_mode",
            "embedding",
            "embedding_ref",
            "dims",
        )
        if k in representation
    }

    observation: dict[str, Any] = {
        "schema": CONTRACT_VERSION,
        "version": INSTRUMENT_VERSION,
        "observation_id": observation_id,
        "input_hash": ih,
        "authority": dict(AUTHORITY),
        "evidence": evidence,
        "representation": rep_out,
        "candidates": candidates if "candidates" in req else [],
        "neighborhood": neighborhood,
        "diagnostics": diagnostics,
        "provenance": {
            "instrument_version": INSTRUMENT_VERSION,
            "contract_version": CONTRACT_VERSION,
            "ontology_version": ONTOLOGY_VERSION,
            "ontology_sha256": ONTOLOGY_RECEIPT,
            "runtime_commit": manifest["runtime"]["commit"],
            "package_version": PKG_VERSION,
            "schema_sha256": schema_sha256(),
            "manifest_sha256": manifest["manifest_sha256"],
            "settlement_ref": SETTLEMENT_REF,
            "settlement_receipt": SETTLEMENT_RECEIPT,
            "artifact_hashes": {
                "encoder_pin_sha256": manifest["encoder"]["pin_sha256"],
                "schema_sha256": schema_sha256(),
                "manifest_sha256": manifest["manifest_sha256"],
            },
        },
        "capabilities_ref": "hyperlex.instrument.capabilities.v1",
        "requested": req,
        "final_classification": None,
    }

    if validate:
        result = validate_observation(observation)
        if not result["ok"]:
            raise ValueError(f"observation failed schema validation: {result['errors']}")
    return observation


def health() -> dict[str, Any]:
    m = cold_load_manifest()
    return {
        "ok": True,
        "instrument_version": INSTRUMENT_VERSION,
        "contract_version": CONTRACT_VERSION,
        "operation_mode": m["operation_mode"],
        "readiness": m["readiness"],
        "manifest_sha256": m["manifest_sha256"],
        "schema_sha256": m["schema_sha256"],
        "HYPERLEX_OUTPUT_EQ_SEMANTIC_TRUTH": False,
    }


def get_manifest() -> dict[str, Any]:
    return cold_load_manifest()


def get_capabilities() -> dict[str, Any]:
    return capabilities()
