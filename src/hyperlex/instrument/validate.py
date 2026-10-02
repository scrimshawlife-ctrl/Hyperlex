"""Schema validation for hyperlex.instrument.v1."""

from __future__ import annotations

from typing import Any

from .manifest import load_schema


def validate_observation(observation: dict[str, Any]) -> dict[str, Any]:
    """Validate observation against JSON Schema. Returns {ok, errors}."""
    try:
        import jsonschema
    except ImportError:  # pragma: no cover
        return _lightweight_validate(observation)

    schema = load_schema()
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(observation), key=lambda e: list(e.path))
    if not errors:
        return {"ok": True, "errors": []}
    return {
        "ok": False,
        "errors": [
            {"path": "/".join(str(p) for p in e.path), "message": e.message}
            for e in errors
        ],
    }


def _lightweight_validate(observation: dict[str, Any]) -> dict[str, Any]:
    """Stdlib fallback used when jsonschema is unavailable."""
    errors: list[dict[str, str]] = []
    if observation.get("schema") != "hyperlex.instrument.v1":
        errors.append({"path": "schema", "message": "must be hyperlex.instrument.v1"})
    auth = observation.get("authority") or {}
    if auth.get("semantic_truth") is not False:
        errors.append(
            {"path": "authority/semantic_truth", "message": "must be false"}
        )
    if auth.get("kind") != "advisory":
        errors.append({"path": "authority/kind", "message": "must be advisory"})
    for c in observation.get("candidates") or []:
        if c.get("advisory") is not True:
            errors.append(
                {"path": "candidates", "message": "every candidate must be advisory"}
            )
    for forbidden in (
        "domain_labels",
        "mediation_labels",
        "function_labels",
        "gold",
        "canonical_state",
        "authorized_action",
    ):
        if forbidden in observation:
            errors.append(
                {"path": forbidden, "message": f"forbidden field {forbidden}"}
            )
    return {"ok": not errors, "errors": errors}
