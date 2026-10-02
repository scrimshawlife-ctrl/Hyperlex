"""Machine-readable HYPERLEX_INSTRUMENT_V1 manifest + cold-load identity."""

from __future__ import annotations

import hashlib
import json
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

from hyperlex import PKG_VERSION

from .capabilities import capabilities
from .constants import (
    CLASSIFIER_RELEASE,
    CONTRACT_VERSION,
    ENCODER_ID,
    ENCODER_REVISION,
    ENCODER_ROLE,
    INSTRUMENT_READINESS,
    INSTRUMENT_VERSION,
    ONTOLOGY_RECEIPT,
    ONTOLOGY_VERSION,
    OPERATION_MODE,
    PRODUCT_ROLE,
    REJECTED_CORE_PACKAGE_SHA256,
    REJECTED_CORE_QUAL_ID,
    SETTLEMENT_COMMIT,
    SETTLEMENT_RECEIPT,
    SETTLEMENT_REF,
)
from .representation import encoder_pin_hash

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / "schemas" / "hyperlex.instrument.v1.schema.json"
)
_REPO_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3] / "schemas" / "hyperlex.instrument.v1.schema.json"
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


@lru_cache(maxsize=1)
def schema_bytes() -> bytes:
    path = _SCHEMA_PATH if _SCHEMA_PATH.is_file() else _REPO_SCHEMA_PATH
    return path.read_bytes()


@lru_cache(maxsize=1)
def schema_sha256() -> str:
    return _sha256_bytes(schema_bytes())


def load_schema() -> dict[str, Any]:
    return json.loads(schema_bytes().decode("utf-8"))


def runtime_commit() -> str:
    """Best-effort git commit; falls back to settlement commit pin."""
    try:
        root = Path(__file__).resolve().parents[3]
        out = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        return out or SETTLEMENT_COMMIT
    except Exception:
        return SETTLEMENT_COMMIT


def build_manifest() -> dict[str, Any]:
    body = {
        "schema": "hyperlex.instrument.manifest.v1",
        "instrument_version": INSTRUMENT_VERSION,
        "contract_version": CONTRACT_VERSION,
        "product_role": PRODUCT_ROLE,
        "operation_mode": OPERATION_MODE,
        "classifier_release": CLASSIFIER_RELEASE,
        "readiness": INSTRUMENT_READINESS,
        "encoder": {
            "id": ENCODER_ID,
            "revision": ENCODER_REVISION,
            "pin_sha256": encoder_pin_hash(),
            "role": ENCODER_ROLE,
            "default_embed_mode": "STATIC_HASH_EMBEDDING",
        },
        "ontology": {
            "version": ONTOLOGY_VERSION,
            "receipt": ONTOLOGY_RECEIPT,
        },
        "evidence_gate": {
            "artifact": "instrument_cue_evidence_v1",
            "note": (
                "Deterministic cue-support abstention; rejected V6 core classifier "
                "package is not loaded"
            ),
            "rejected_classifier_package_sha256": REJECTED_CORE_PACKAGE_SHA256,
            "rejected_qual_id": REJECTED_CORE_QUAL_ID,
        },
        "runtime": {
            "package_version": PKG_VERSION,
            "commit": runtime_commit(),
        },
        "schema_sha256": schema_sha256(),
        "settlement": {
            "ref": SETTLEMENT_REF,
            "receipt": SETTLEMENT_RECEIPT,
            "commit": SETTLEMENT_COMMIT,
        },
        "capabilities": capabilities()["capabilities"],
        "authority_boundary": {
            "HYPERLEX_OUTPUT_EQ_SEMANTIC_TRUTH": False,
            "may_authorize": False,
            "may_mutate_governing_state": False,
        },
    }
    # Manifest hash excludes its own digest field.
    digest = _sha256_text(json.dumps(body, sort_keys=True, separators=(",", ":")))
    body["manifest_sha256"] = digest
    return body


@lru_cache(maxsize=1)
def cold_load_manifest() -> dict[str, Any]:
    """Cold-load identity check: schema present, manifest self-consistent."""
    m = build_manifest()
    assert m["schema_sha256"] == schema_sha256()
    assert m["contract_version"] == CONTRACT_VERSION
    assert m["authority_boundary"]["HYPERLEX_OUTPUT_EQ_SEMANTIC_TRUTH"] is False
    return m
