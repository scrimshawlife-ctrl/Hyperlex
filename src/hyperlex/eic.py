"""HYPERLEX-Q1 controlled-transform export boundary.

This module records transform provenance. It does not determine whether a
declared semantic invariant survived in a model representation.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

_ALLOWED_EPISTEMIC = {"OBSERVED", "NOT_COMPUTABLE"}


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def validate_q1_result(payload: dict[str, Any], schema_path: str | Path | None = None) -> None:
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError as exc:
        raise RuntimeError("jsonschema is required for HYPERLEX-Q1 validation") from exc

    path = Path(schema_path) if schema_path else Path(__file__).resolve().parents[2] / "schemas" / "hyperlex-q1-transform-result.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(payload),
        key=lambda error: list(error.path),
    )
    if errors:
        raise ValueError("HYPERLEX-Q1 contract violation: " + "; ".join(e.message for e in errors))

    if payload["epistemic_status"] not in _ALLOWED_EPISTEMIC:
        raise ValueError("Hyperlex Q1 cannot promote transform output beyond OBSERVED/NOT_COMPUTABLE")
    transform = payload["transform"]
    if transform["deterministic"] and transform.get("seed") is None and transform["parameters"].get("requires_seed"):
        raise ValueError("declared deterministic seeded transform is missing seed")
    if payload["status"] == "PRODUCED" and payload.get("runtime_binding") is None and transform["parameters"].get("requires_runtime_binding"):
        raise ValueError("required runtime/model binding is missing")


def build_q1_result(
    *,
    result_id: str,
    source: str,
    output: str | None,
    transform_id: str,
    revision: str,
    parameters: dict[str, Any] | None = None,
    deterministic: bool = True,
    seed: int | str | None = None,
    declared_semantic_intent: str | None = None,
    declared_invariants: list[str] | None = None,
    expected_changed_attributes: list[str] | None = None,
    runtime_binding: dict[str, Any] | None = None,
    contamination: list[str] | None = None,
    fallback: dict[str, Any] | None = None,
    not_computable_reason: str | None = None,
) -> dict[str, Any]:
    parameters = deepcopy(parameters or {})
    not_computable = not_computable_reason is not None
    payload = {
        "schema_version": "0.1.0",
        "result_id": result_id,
        "status": "NOT_COMPUTABLE" if not_computable else "PRODUCED",
        "source_hash": sha256_text(source),
        "output_hash": None if not_computable or output is None else sha256_text(output),
        "transform": {
            "transform_id": transform_id,
            "revision": revision,
            "parameters": parameters,
            "deterministic": deterministic,
            "seed": seed,
        },
        "declared_semantic_intent": declared_semantic_intent,
        "declared_invariants": list(declared_invariants or []),
        "expected_changed_attributes": list(expected_changed_attributes or []),
        "runtime_binding": deepcopy(runtime_binding),
        "contamination": list(contamination or []),
        "fallback": deepcopy(fallback),
        "provenance": "NOT_COMPUTABLE" if not_computable else "OBSERVED",
        "epistemic_status": "NOT_COMPUTABLE" if not_computable else "OBSERVED",
        "limitations": [not_computable_reason] if not_computable else [],
    }
    validate_q1_result(payload)
    return payload
