"""Evaluation-settlement apply path for the eighteen-family taxonomy.

``source_hint``, ``semantic_family``, and ``attest`` are separate fields.
A confirm settlement may store the same family string in both ``source_hint``
and ``semantic_family``. This module never copies one field into another,
and it never derives ``attest`` from ``decision``.

The production classify head is not read or written here. ``ACCEPT`` records
the operator-selected attest. It does not promote existing evidence to
``OBSERVED``. This command does not admit rows to ``EVAL_RESERVE``.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from .holdout_guard import normalized_text_sha256

SCHEMA = "hyperlex.eval_settlement.v1"
RECEIPT_SCHEMA = "hyperlex.eval_settlement_receipt.v1"
VENDOR_CALLS = 0

ACTIVE_FAMILIES: tuple[str, ...] = (
    "gaming-meta",
    "betting-sharp",
    "crypto-degen",
    "internet-slang",
    "memetic",
    "social-status",
    "relationship-dating",
    "approval-disapproval",
    "conflict-aggression",
    "technology-ai",
    "workplace-career",
    "sports-competition",
    "music-entertainment",
    "fashion-aesthetic",
    "regional-cultural",
    "spiritual-mystic",
    "identity-affiliation",
    "politics-civic",
)
CANDIDATE_FAMILIES: tuple[str, ...] = (
    "finance-retail",
    "market-structure",
    "sexual-romantic",
    "substance-party",
    "crime-illicit",
    "health-fitness",
)
ABSTAIN = "none"
DECISIONS = ("ACCEPT", "RECLASSIFY", "NONE", "UNRESOLVED")
DECISION_ALIASES = {
    "ACCEPT": "ACCEPT",
    "ACCEPT FAMILY": "ACCEPT",
    "RECLASSIFY": "RECLASSIFY",
    "CHOOSE DIFFERENT FAMILY": "RECLASSIFY",
    "NONE": "NONE",
    "UNRESOLVED": "UNRESOLVED",
}
ATTESTS = ("OBSERVED", "INFERRED")
REGISTERS = ("slang", "domain-specific", "high-register", "general")
FUNCTIONS = ("address", "evaluation", "intensification", "reference", "affiliation")
SURFACES = {
    "A": "CONFIRM",
    "B": "PROPOSED FAMILY",
    "C": "DISAMBIGUATE",
    "D": "RIGHTS BLOCKED",
    "HELD_OUTSIDE_LANES": "hint-only",
}
SHEET_COLUMNS = (
    "lane",
    "row_key",
    "text",
    "source_hint",
    "source_hint_provenance",
    "current_label",
    "label_source",
    "rights",
    "proposed_family_evidence",
    "disambiguation_options",
    "semantic_family",
    "attest",
    "register",
    "function",
    "decision",
)
SETTLED_DECISIONS = frozenset({"ACCEPT", "RECLASSIFY", "NONE"})
_CLEARED_SOURCES = {
    "wiktionary_category": "CC-BY-SA",
    "wikipedia_prose": "CC-BY-SA",
}
_BLOCKED_SOURCES = {
    "reddit_title": "RIGHTS_UNRESOLVED",
    "kym_slang_list": "RIGHTS_UNRESOLVED",
}
_SCORE_KEYS = frozenset(
    {"candidate_score", "model_error", "model_score", "prediction"}
)
_FORBIDDEN_KEYS = frozenset({"text", "normalized_text", "raw_text"}) | _SCORE_KEYS
_HINT_PROVENANCE = "stream.family_hint_not_a_label"


def refuse(message: str) -> None:
    raise SystemExit(f"REFUSE: {message}")


def family_flags(name: str, *, activated: set[str] | None = None) -> dict[str, bool]:
    """Three independent flags. Evaluation settlement does not enable a family."""
    activated = set(activated or ())
    if name in ACTIVE_FAMILIES:
        return {
            "taxonomy.active": True,
            "evaluation.enabled": False,
            "production.enabled": False,
        }
    if name in CANDIDATE_FAMILIES:
        return {
            "taxonomy.active": name in activated,
            "evaluation.enabled": False,
            "production.enabled": False,
        }
    refuse(f"family is not in the evaluation taxonomy: {name}")
    raise AssertionError("refuse")


def _activated(activated: set[str] | None) -> set[str]:
    extra = set(activated or ())
    unknown = sorted(extra - set(CANDIDATE_FAMILIES))
    if unknown:
        refuse(f"activation refused for {unknown[0]}")
    return extra


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _optional_text(value: Any) -> str | None:
    if _blank(value):
        return None
    if not isinstance(value, str):
        refuse("settlement field is not text")
    return value.strip()


def _decision(value: Any) -> str:
    token = _optional_text(value)
    if token is None:
        refuse("decision is empty")
    mapped = DECISION_ALIASES.get(token.upper())
    if mapped is None:
        if token.upper() == "REJECT":
            refuse("reject is a production attest token, not an evaluation decision")
        refuse(f"invalid decision: {token}")
    return mapped


def _attest(value: Any) -> str | None:
    token = _optional_text(value)
    if token is None:
        return None
    mapped = token.upper()
    if mapped not in ATTESTS:
        refuse(f"invalid attest: {token}")
    return mapped


def _family_token(value: Any) -> str | None:
    token = _optional_text(value)
    if token is None:
        return None
    return token.casefold()


def _closed_vocab(value: Any, allowed: tuple[str, ...], label: str) -> str | None:
    token = _optional_text(value)
    if token is None:
        return None
    mapped = token.casefold()
    if mapped not in allowed:
        refuse(f"invalid {label}: {token}")
    return mapped


def _resolve_family(token: str | None, *, activated: set[str], allow_null: bool) -> str | None:
    if token is None:
        if allow_null:
            return None
        refuse("explicit semantic_family is required")
    if token == ABSTAIN:
        return ABSTAIN
    if token in CANDIDATE_FAMILIES and token not in activated:
        refuse(f"candidate family is inactive: {token}")
    if token in ACTIVE_FAMILIES or token in activated:
        return token
    refuse(f"family is not in the evaluation taxonomy: {token}")
    raise AssertionError("refuse")


def rights_of(stream_row: Mapping[str, Any]) -> str:
    source_type = str(stream_row.get("source_type") or "")
    if source_type in _CLEARED_SOURCES:
        return _CLEARED_SOURCES[source_type]
    if source_type in _BLOCKED_SOURCES:
        return _BLOCKED_SOURCES[source_type]
    refuse(f"unknown rights source_type: {source_type or 'missing'}")
    raise AssertionError("refuse")


def evidence_hint(stream_row: Mapping[str, Any]) -> str | None:
    hint = stream_row.get("family_hint_not_a_label")
    if _blank(hint):
        return None
    return str(hint)


def sheet_hint_token(hint: str | None) -> str:
    return "NO_HINT" if hint is None else hint


def sheet_label_token(label: Any) -> str:
    if label is None:
        return "UNLABELLED"
    return str(label)


def settlement_allows_reserve(record: Mapping[str, Any]) -> bool:
    """Rights and decision gates. This predicate does not admit a row."""
    if record.get("decision") not in SETTLED_DECISIONS:
        return False
    if record.get("rights") == "RIGHTS_UNRESOLVED":
        return False
    family = record.get("semantic_family")
    attest = record.get("attest")
    if family is None or attest not in ATTESTS:
        return False
    if attest == "OBSERVED" and record.get("decision") is None:
        return False
    return True


def _forbid_payload(value: Mapping[str, Any], where: str) -> None:
    for key in value:
        if key in _FORBIDDEN_KEYS:
            refuse(f"{where} must not carry {key}")


def _refuse_scores(value: Mapping[str, Any], where: str) -> None:
    for key in value:
        if key in _SCORE_KEYS:
            refuse(f"{where} must not carry {key}")


def _canonical_hash(stream_row: Mapping[str, Any]) -> str:
    digest = normalized_text_sha256(str(stream_row.get("text") or ""))
    stored = stream_row.get("normtext_sha256")
    if isinstance(stored, str) and stored and stored != digest:
        refuse("stream normtext_sha256 drifted from canonical row identity")
    return digest


def _coerce_choice(
    decision: str,
    family: str | None,
    attest: str | None,
    proposed: str | None,
    hint: str | None,
) -> tuple[str | None, str | None]:
    if decision == "UNRESOLVED":
        if family is not None or attest is not None:
            refuse("UNRESOLVED requires null semantic_family and null attest")
        return None, None
    if decision == "NONE":
        if family not in (None, ABSTAIN):
            refuse("NONE requires semantic_family none")
        if attest is None:
            refuse("NONE requires an explicit attest")
        return ABSTAIN, attest
    if decision == "ACCEPT":
        if family is None:
            refuse("ACCEPT requires an explicit semantic_family")
        if attest is None:
            refuse("ACCEPT requires an explicit attest")
        if proposed is not None and family != proposed:
            refuse("ACCEPT does not match the proposed family")
        return family, attest
    if decision == "RECLASSIFY":
        if family is None:
            refuse("RECLASSIFY requires an explicit family")
        if attest is None:
            refuse("RECLASSIFY requires an explicit attest")
        evidence = proposed if proposed is not None else hint
        if evidence is not None and family == evidence:
            refuse("RECLASSIFY family must differ from the proposed evidence family")
        return family, attest
    refuse(f"invalid decision: {decision}")
    raise AssertionError("refuse")


def validate_settlement(
    incoming: Mapping[str, Any],
    stream_row: Mapping[str, Any],
    *,
    activated: set[str] | None = None,
    prior_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Fail closed. Does not read ``label_source`` as ``attest``."""
    _forbid_payload(incoming, "settlement")
    extra = _activated(activated)
    row_id = _optional_text(incoming.get("row_id")) or _optional_text(stream_row.get("row_key"))
    if not row_id or row_id != stream_row.get("row_key"):
        refuse("row_id is not in the held-out stream")
    if row_id in set(prior_ids or ()):
        refuse(f"duplicate settlement for {row_id}")
    digest = _canonical_hash(stream_row)
    claimed = _optional_text(incoming.get("text_hash"))
    if claimed is None or claimed != digest:
        refuse(f"text_hash does not match canonical row identity for {row_id}")
    hint = evidence_hint(stream_row)
    supplied_hint = incoming.get("source_hint")
    if _blank(supplied_hint):
        supplied_hint = None
    elif isinstance(supplied_hint, str) and supplied_hint.strip() == "NO_HINT":
        supplied_hint = None
    elif isinstance(supplied_hint, str):
        supplied_hint = supplied_hint.strip()
    else:
        refuse("source_hint is not text")
    if supplied_hint != hint:
        refuse(f"source_hint does not match held-out evidence for {row_id}")
    rights = rights_of(stream_row)
    sheet_rights = _optional_text(incoming.get("rights"))
    if sheet_rights is not None and sheet_rights != rights:
        refuse(f"rights state does not match held-out evidence for {row_id}")
    decision = _decision(incoming.get("decision"))
    proposed = _family_token(incoming.get("proposed_family"))
    register = _closed_vocab(incoming.get("register"), REGISTERS, "register")
    function = _closed_vocab(incoming.get("function"), FUNCTIONS, "function")
    attest = _attest(incoming.get("attest"))
    family = _family_token(incoming.get("semantic_family"))
    if decision == "UNRESOLVED" and (register is not None or function is not None):
        refuse("UNRESOLVED cannot carry register or function")
    family, attest = _coerce_choice(decision, family, attest, proposed, hint)
    family = _resolve_family(family, activated=extra, allow_null=decision == "UNRESOLVED")
    operator = _optional_text(incoming.get("operator"))
    settled_at = _optional_text(incoming.get("settled_at"))
    provenance = _optional_text(incoming.get("provenance"))
    if not operator:
        refuse("operator is required")
    if not settled_at:
        refuse("settled_at is required")
    if not provenance:
        refuse("provenance is required")
    lane = _optional_text(incoming.get("lane"))
    if lane is not None and lane not in SURFACES:
        refuse(f"unknown settlement surface: {lane}")
    record = {
        "schema": SCHEMA,
        "row_id": row_id,
        "text_hash": digest,
        "decision": decision,
        "semantic_family": family,
        "attest": attest,
        "register": register,
        "function": function,
        "source_hint": hint,
        "operator": operator,
        "settled_at": settled_at,
        "provenance": provenance,
        "rights": rights,
        "lane": lane,
    }
    _forbid_payload(record, "settlement record")
    return record


def _stream_index(rows: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    index: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        _refuse_scores(row, "held-out row")
        key = row.get("row_key")
        if not isinstance(key, str) or not key:
            refuse("held-out row is missing row_key")
        if key in index:
            refuse(f"duplicate held-out row_id {key}")
        index[key] = row
    return index


def load_stream(path: str | Path) -> dict[str, Mapping[str, Any]]:
    rows = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    refuse("held-out stream row is not an object")
                rows.append(payload)
    return _stream_index(rows)


def _check_sheet_integrity(
    parts: Sequence[str],
    header: Sequence[str],
    stream_row: Mapping[str, Any],
) -> str:
    cell = dict(zip(header, parts))
    row_id = cell["row_key"].strip()
    if row_id != stream_row.get("row_key"):
        refuse("row_id is not in the held-out stream")
    digest = normalized_text_sha256(cell["text"])
    if digest != _canonical_hash(stream_row):
        refuse(f"text_hash does not match canonical row identity for {row_id}")
    hint = evidence_hint(stream_row)
    if cell["source_hint"] != sheet_hint_token(hint):
        refuse(f"source_hint does not match held-out evidence for {row_id}")
    if cell["source_hint_provenance"] != _HINT_PROVENANCE:
        refuse(f"source_hint provenance does not match for {row_id}")
    if cell["current_label"] != sheet_label_token(stream_row.get("label")):
        refuse(f"current_label does not match held-out evidence for {row_id}")
    if cell["label_source"] != str(stream_row.get("label_source") or ""):
        refuse(f"label_source does not match held-out evidence for {row_id}")
    if cell["rights"].strip() != rights_of(stream_row):
        refuse(f"rights state does not match held-out evidence for {row_id}")
    lane = cell["lane"].strip()
    if lane not in SURFACES:
        refuse(f"unknown settlement surface: {lane}")
    return digest


def _operator_cells(cell: Mapping[str, str]) -> dict[str, str]:
    return {
        "semantic_family": cell["semantic_family"],
        "attest": cell["attest"],
        "register": cell["register"],
        "function": cell["function"],
        "decision": cell["decision"],
    }


def parse_sheet(
    path: str | Path,
    stream: Mapping[str, Mapping[str, Any]],
    *,
    operator: str,
    provenance: str,
    settled_at: str,
    activated: set[str] | None = None,
    prior_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Validate a private lane sheet. Does not write the sheet or fill decisions."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    if not lines:
        refuse("settlement sheet is empty")
    header = tuple(lines[0].split("\t"))
    if header != SHEET_COLUMNS:
        refuse("sheet header does not match the operator lane contract")
    records = []
    unset = 0
    lane_rows: dict[str, int] = {}
    seen: set[str] = set()
    errors: list[str] = []
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != len(header):
            errors.append("REFUSE: sheet row is not rectangular")
            continue
        row_id = parts[1].strip()
        stream_row = stream.get(row_id)
        if stream_row is None:
            errors.append(f"REFUSE: row_id is not in the held-out stream: {row_id}")
            continue
        if row_id in seen or row_id in set(prior_ids or ()):
            errors.append(f"REFUSE: duplicate settlement for {row_id}")
            continue
        seen.add(row_id)
        try:
            digest = _check_sheet_integrity(parts, header, stream_row)
            cell = dict(zip(header, parts))
            lane = cell["lane"].strip()
            lane_rows[lane] = lane_rows.get(lane, 0) + 1
            chosen = _operator_cells(cell)
            if all(_blank(value) for value in chosen.values()):
                unset += 1
                continue
            if _blank(chosen["decision"]):
                refuse(f"decision is empty for {row_id}; refusing to infer one")
            record = validate_settlement(
                {
                    "row_id": row_id,
                    "text_hash": digest,
                    "decision": chosen["decision"],
                    "semantic_family": chosen["semantic_family"],
                    "attest": chosen["attest"],
                    "register": chosen["register"],
                    "function": chosen["function"],
                    "source_hint": evidence_hint(stream_row),
                    "proposed_family": cell["proposed_family_evidence"],
                    "operator": operator,
                    "settled_at": settled_at,
                    "provenance": provenance,
                    "rights": cell["rights"],
                    "lane": lane,
                },
                stream_row,
                activated=activated,
                prior_ids=prior_ids,
            )
            records.append(record)
        except SystemExit as exc:
            errors.append(str(exc))
    if errors:
        refuse("; ".join(message.removeprefix("REFUSE: ") for message in errors))
    return {"records": records, "unset_row_count": unset, "lane_rows": lane_rows, "row_ids": seen}


def load_record_file(
    path: str | Path,
    stream: Mapping[str, Mapping[str, Any]],
    *,
    operator: str,
    provenance: str,
    settled_at: str,
    activated: set[str] | None = None,
    prior_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    records = []
    seen = set(prior_ids or ())
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                refuse("settlement record is not an object")
            row_id = payload.get("row_id")
            if not isinstance(row_id, str) or row_id not in stream:
                refuse(f"row_id is not in the held-out stream: {row_id}")
            if row_id in seen:
                refuse(f"duplicate settlement for {row_id}")
            payload = dict(payload)
            payload.setdefault("operator", operator)
            payload.setdefault("provenance", provenance)
            payload.setdefault("settled_at", settled_at)
            records.append(
                validate_settlement(
                    payload,
                    stream[row_id],
                    activated=activated,
                    prior_ids=prior_ids,
                )
            )
            seen.add(row_id)
    return records


def _decision_counts(records: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = {name: 0 for name in DECISIONS}
    for record in records:
        counts[str(record["decision"])] += 1
    return counts


def _family_counts(records: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = {name: 0 for name in (*ACTIVE_FAMILIES, ABSTAIN)}
    for record in records:
        if record["decision"] not in SETTLED_DECISIONS:
            continue
        family = record.get("semantic_family")
        if family in counts:
            counts[str(family)] += 1
    return counts


def build_receipt(
    records: Sequence[Mapping[str, Any]],
    *,
    batch_id: str,
    operator: str,
    provenance: str,
    unset_row_count: int,
    lane_rows: Mapping[str, int],
    stream_run_id: str = "",
    settled_at: str = "",
    input_sheets: Sequence[Mapping[str, str]] | None = None,
) -> dict[str, Any]:
    if not str(batch_id or "").strip():
        refuse("batch_id is required")
    if not str(operator or "").strip() or not str(provenance or "").strip():
        refuse("operator and provenance are required")
    settled = [record for record in records if record["decision"] in SETTLED_DECISIONS]
    unresolved = [record for record in records if record["decision"] == "UNRESOLVED"]
    body = {
        "schema": RECEIPT_SCHEMA,
        "batch_id": batch_id,
        "operator": operator,
        "provenance": provenance,
        "settled_row_count": len(settled),
        "unresolved_row_count": len(unresolved),
        "unset_row_count": unset_row_count,
        "decision_counts": _decision_counts(records),
        "family_counts": _family_counts(records),
        "observed_count": sum(1 for record in settled if record.get("attest") == "OBSERVED"),
        "inferred_count": sum(1 for record in settled if record.get("attest") == "INFERRED"),
        "rights_blocked_settled_count": sum(
            1 for record in settled if record.get("rights") == "RIGHTS_UNRESOLVED"
        ),
        "reserve_eligible_count": sum(1 for record in records if settlement_allows_reserve(record)),
        "reserve_added": 0,
        "ledger_mutated": False,
        "vendor_calls": VENDOR_CALLS,
        "evaluation_enabled": False,
        "lane_rows": dict(lane_rows),
    }
    run_id = str(stream_run_id or "").strip()
    if run_id:
        body["stream_run_id"] = run_id
    stamp = str(settled_at or "").strip()
    if stamp:
        body["settled_at"] = stamp
    if input_sheets:
        sheets = []
        for item in input_sheets:
            identity = str(item.get("identity") or "").strip()
            digest = str(item.get("sha256") or "").strip()
            if not identity or len(digest) != 64:
                refuse("input sheet identity is incomplete")
            sheets.append({"identity": identity, "sha256": digest})
        body["input_sheets"] = sheets
    _walk_forbid(body)
    return seal_receipt(body)


def seal_receipt(body: Mapping[str, Any]) -> dict[str, Any]:
    payload = {key: value for key, value in body.items() if key != "receipt_sha256"}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sealed = dict(payload)
    sealed["receipt_sha256"] = hashlib.sha256(raw).hexdigest()
    return sealed


def receipt_sha_matches(receipt: Mapping[str, Any]) -> bool:
    sealed = seal_receipt(receipt)
    return sealed["receipt_sha256"] == receipt.get("receipt_sha256")


def _walk_forbid(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _FORBIDDEN_KEYS:
                refuse(f"receipt must not carry {key}")
            _walk_forbid(item)
    elif isinstance(value, list):
        for item in value:
            _walk_forbid(item)


def load_logged_ids(path: str | Path) -> set[str]:
    log = Path(path)
    if not log.exists():
        return set()
    found = set()
    for line in log.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            refuse("settlement log row is not an object")
        _forbid_payload(payload, "settlement log")
        row_id = payload.get("row_id")
        if not isinstance(row_id, str) or not row_id:
            refuse("settlement log row is missing row_id")
        if row_id in found:
            refuse(f"settlement log already contains a duplicate for {row_id}")
        found.add(row_id)
    return found


def _write_exclusive(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)


def commit_settlement(
    records: Sequence[Mapping[str, Any]],
    receipt: Mapping[str, Any],
    *,
    log_path: str | Path,
    receipt_path: str | Path,
) -> dict[str, Any]:
    """Append settlement rows, then write a new receipt. Never rewrites either."""
    receipt_file = Path(receipt_path)
    if receipt_file.exists():
        refuse(f"receipt already exists: {receipt_file}")
    log = Path(log_path)
    prior = load_logged_ids(log)
    fresh_ids = []
    for record in records:
        _forbid_payload(record, "settlement record")
        row_id = str(record["row_id"])
        if row_id in prior or row_id in fresh_ids:
            refuse(f"duplicate settlement for {row_id}")
        fresh_ids.append(row_id)
    if not log.exists():
        _write_exclusive(log, "")
    if records:
        with log.open("a", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
    sealed = dict(receipt)
    _walk_forbid(sealed)
    _write_exclusive(receipt_file, json.dumps(sealed, indent=2, sort_keys=True) + "\n")
    os.chmod(log, 0o600)
    return sealed


def settle(
    stream_rows: Sequence[Mapping[str, Any]],
    decisions: Sequence[Mapping[str, Any]],
    *,
    batch_id: str,
    operator: str,
    provenance: str,
    settled_at: str,
    activated: set[str] | None = None,
    prior_ids: set[str] | None = None,
    unset_row_count: int = 0,
    lane_rows: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Validate explicit decisions. Blank callers pass no decisions and settle nothing."""
    stream = _stream_index(stream_rows)
    prior = set(prior_ids or ())
    records = []
    seen: set[str] = set()
    for incoming in decisions:
        row_id = incoming.get("row_id")
        stream_row = stream.get(row_id) if isinstance(row_id, str) else None
        if stream_row is None:
            refuse(f"row_id is not in the held-out stream: {row_id}")
        if row_id in seen:
            refuse(f"duplicate settlement for {row_id}")
        seen.add(str(row_id))
        payload = dict(incoming)
        payload.setdefault("operator", operator)
        payload.setdefault("provenance", provenance)
        payload.setdefault("settled_at", settled_at)
        records.append(
            validate_settlement(payload, stream_row, activated=activated, prior_ids=prior)
        )
    receipt = build_receipt(
        records,
        batch_id=batch_id,
        operator=operator,
        provenance=provenance,
        unset_row_count=unset_row_count,
        lane_rows=dict(lane_rows or {}),
    )
    return {"records": records, "receipt": receipt}


def run_settlement_apply(args: Any) -> int:
    """CLI entry. Reads operator cells. Does not choose them or touch the ledger."""
    import sys

    stream = load_stream(args.stream_rows)
    activated = set(args.activated_family or [])
    sheets = list(args.sheet or [])
    records_path = str(args.records or "").strip()
    if not sheets and not records_path:
        refuse("no operator surface supplied")
    prior = load_logged_ids(args.settlement_log)
    records: list[dict[str, Any]] = []
    unset = 0
    lane_rows: dict[str, int] = {}
    decided: set[str] = set()
    surfaced: set[str] = set()
    for sheet in sheets:
        parsed = parse_sheet(
            sheet,
            stream,
            operator=args.operator,
            provenance=args.provenance,
            settled_at=args.settled_at,
            activated=activated,
            prior_ids=prior | decided,
        )
        for row_id in parsed["row_ids"]:
            if row_id in surfaced:
                refuse(f"duplicate settlement for {row_id}")
            surfaced.add(row_id)
        for record in parsed["records"]:
            decided.add(record["row_id"])
            records.append(record)
        unset += int(parsed["unset_row_count"])
        for lane, count in parsed["lane_rows"].items():
            lane_rows[lane] = lane_rows.get(lane, 0) + count
    if records_path:
        loaded = load_record_file(
            records_path,
            stream,
            operator=args.operator,
            provenance=args.provenance,
            settled_at=args.settled_at,
            activated=activated,
            prior_ids=prior | decided,
        )
        for record in loaded:
            if record["row_id"] in decided or record["row_id"] in surfaced:
                refuse(f"duplicate settlement for {record['row_id']}")
            decided.add(record["row_id"])
            records.append(record)
    sheet_identities = []
    for sheet in sheets:
        raw = Path(sheet).read_bytes()
        sheet_identities.append(
            {"identity": Path(sheet).name, "sha256": hashlib.sha256(raw).hexdigest()}
        )
    receipt = build_receipt(
        records,
        batch_id=args.batch_id,
        operator=args.operator,
        provenance=args.provenance,
        unset_row_count=unset,
        lane_rows=lane_rows,
        stream_run_id=str(getattr(args, "stream_run_id", "") or ""),
        settled_at=str(args.settled_at or ""),
        input_sheets=sheet_identities,
    )
    sealed = commit_settlement(
        records,
        receipt,
        log_path=args.settlement_log,
        receipt_path=args.receipt,
    )
    sys.stdout.write(json.dumps(sealed, indent=2, sort_keys=True) + "\n")
    return 0
