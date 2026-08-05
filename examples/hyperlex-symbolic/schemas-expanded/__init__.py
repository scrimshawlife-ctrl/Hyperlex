"""Schemas for Hyperlex (v1.6)

Symbolic: intake (gate), analysis (emergence), receipt (archive)
"""
import json
from pathlib import Path
from typing import Dict, Any, Tuple

SCHEMAS_DIR = Path(__file__).parent

def _load_schema(name: str) -> Dict[str, Any]:
    path = SCHEMAS_DIR / name
    with open(path, "r") as f:
        return json.load(f)

INGEST_SCHEMA = _load_schema("ingest.v1.schema.json")
RESULT_SCHEMA = _load_schema("result.v1.schema.json")
RECEIPT_SCHEMA = _load_schema("receipt.v1.schema.json")

def _get_validator():
    try:
        import jsonschema
        return jsonschema.validate
    except ImportError:
        return None

validate = _get_validator()

def validate_ingest(data: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate structured ingest output."""
    if validate is None:
        return True, "jsonschema not installed (skipped)"
    try:
        validate(instance=data, schema=INGEST_SCHEMA)
        return True, "valid"
    except Exception as e:
        return False, str(e)

def validate_result(data: Dict[str, Any]) -> Tuple[bool, str]:
    if validate is None:
        return True, "jsonschema not installed (skipped)"
    try:
        validate(instance=data, schema=RESULT_SCHEMA)
        return True, "valid"
    except Exception as e:
        return False, str(e)

def validate_receipt(data: Dict[str, Any]) -> Tuple[bool, str]:
    if validate is None:
        return True, "jsonschema not installed (skipped)"
    try:
        validate(instance=data, schema=RECEIPT_SCHEMA)
        return True, "valid"
    except Exception as e:
        return False, str(e)

def get_ingest_schema() -> Dict[str, Any]:
    return INGEST_SCHEMA

def get_result_schema() -> Dict[str, Any]:
    return RESULT_SCHEMA

__all__ = [
    "validate_ingest", "validate_result", "validate_receipt",
    "get_ingest_schema", "get_result_schema", "INGEST_SCHEMA", "RESULT_SCHEMA", "RECEIPT_SCHEMA"
]
