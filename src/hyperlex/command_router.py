"""Load the static Hermes command router table."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def router_path() -> Path:
    return Path(__file__).resolve().parents[2] / "docs" / "command-router.v1.json"


def load_router() -> Dict[str, Any]:
    path = router_path()
    if not path.is_file():
        return {
            "daily": [],
            "research": [],
            "invoke": {
                "pipeline": "scripts/hyperlex.py",
                "mutation": "scripts/hlx-mutation",
            },
            "note": "router file missing",
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {"daily": [], "research": [], "note": "router root must be object"}
    data.pop("schema", None)
    return data
