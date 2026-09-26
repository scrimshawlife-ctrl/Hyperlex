"""Unbind target settlement. Separate from classify settlement.

Decisions are about the unbind target only. They do not set
``semantic_family``, ``attest``, or ``evaluation.enabled``.

A correction is an appended event. Earlier events stay in the log.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "hyperlex.eval_unbind_settlement.v1"
RECEIPT_SCHEMA = "hyperlex.eval_unbind_settlement_receipt.v1"
DECISIONS = ("ACCEPT", "CORRECT_TARGET", "REJECT", "UNRESOLVED")
ADMIT_DECISIONS = frozenset({"ACCEPT", "CORRECT_TARGET"})
VENDOR_CALLS = 0


def refuse(message: str) -> None:
    raise SystemExit(f"REFUSE: {message}")


def _hex64(value: Any, field: str) -> str:
    text = str(value or "")
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        refuse(f"{field} must be 64 lowercase hex characters")
    return text


def _forbid_text(value: Mapping[str, Any]) -> None:
    for key in value:
        if key in {"text", "normalized_text", "raw_text", "fillers", "surface"}:
            refuse(f"unbind settlement must not carry {key}")


def event_from_decision(
    *,
    normalized_text_sha256: str,
    decision: str,
    target_sha256: str,
    target_provenance: str,
    operator: str,
    settled_at: str,
    decision_basis: str,
    previous_target_sha256: str = "",
) -> dict[str, Any]:
    """Build one append-only settlement event. No surface text."""
    if decision not in DECISIONS:
        refuse(f"unbind decision must be one of {DECISIONS}")
    if not str(operator or "").strip() or not str(settled_at or "").strip():
        refuse("operator and settled_at are required")
    if not str(target_provenance or "").strip():
        refuse("target provenance is required")
    if not str(decision_basis or "").strip():
        refuse("decision basis is required")
    digest = _hex64(normalized_text_sha256, "normalized_text_sha256")
    target = _hex64(target_sha256, "target_sha256")
    previous = str(previous_target_sha256 or "")
    if decision == "CORRECT_TARGET":
        previous = _hex64(previous, "previous_target_sha256")
        if previous == target:
            refuse("CORRECT_TARGET requires a different target")
    elif previous:
        refuse("previous_target_sha256 is only valid on CORRECT_TARGET")
    body: dict[str, Any] = {
        "schema": SCHEMA,
        "normalized_text_sha256": digest,
        "decision": decision,
        "target_sha256": target,
        "target_provenance": str(target_provenance),
        "operator": str(operator),
        "settled_at": str(settled_at),
        "decision_basis": str(decision_basis),
        "vendor_calls": VENDOR_CALLS,
    }
    if decision == "CORRECT_TARGET":
        body["previous_target_sha256"] = previous
    _forbid_text(body)
    return body


def append_events(path: str | Path, events: Sequence[Mapping[str, Any]]) -> int:
    """Append events. Refuse if the existing prefix changes."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    prior = dest.read_bytes() if dest.exists() else b""
    encoded: list[bytes] = []
    for event in events:
        if not isinstance(event, Mapping):
            refuse("settlement event must be an object")
        _forbid_text(event)
        if event.get("schema") != SCHEMA:
            refuse("settlement event schema mismatch")
        encoded.append((json.dumps(dict(event), sort_keys=True) + "\n").encode("utf-8"))
    with dest.open("ab") as handle:
        for line in encoded:
            handle.write(line)
    current = dest.read_bytes()
    if not current.startswith(prior):
        refuse("unbind settlement log was not append-only")
    return len(encoded)


def load_events(path: str | Path) -> list[dict[str, Any]]:
    dest = Path(path)
    if not dest.is_file():
        return []
    events: list[dict[str, Any]] = []
    for index, line in enumerate(dest.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            refuse(f"settlement log line {index} is not JSON")
        if not isinstance(obj, dict) or obj.get("schema") != SCHEMA:
            refuse(f"settlement log line {index} has the wrong schema")
        _forbid_text(obj)
        events.append(obj)
    return events


def latest_by_hash(events: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Last event for each surface hash wins. Earlier lines stay in the file."""
    latest: dict[str, dict[str, Any]] = {}
    for event in events:
        digest = str(event.get("normalized_text_sha256") or "")
        if digest:
            latest[digest] = dict(event)
    return latest
