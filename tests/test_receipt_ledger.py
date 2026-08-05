"""Tests for append-only receipt ledger."""

from __future__ import annotations

import json
from pathlib import Path

from hyperlex import (
    detect_memetic_patterns,
    emit_receipt,
    verify_receipt,
    list_receipts,
    verify_ledger_chain,
    default_ledger_path,
)


def test_emit_receipt_appends_ledger(tmp_path: Path) -> None:
    result = detect_memetic_patterns(
        query="sharp steam revenge",
        ingest_source="mock",
        validate=False,
    )
    receipts_dir = tmp_path / "receipts"
    ledger = tmp_path / "receipt_ledger.jsonl"

    path = emit_receipt(
        result,
        out_dir=receipts_dir,
        validate=False,
        append_ledger=True,
        ledger_path=ledger,
    )
    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    ok, msg = verify_receipt(payload)
    assert ok, msg
    assert payload["receipt"]["integrity"]
    assert payload["provenance"].get("brier") is None

    chain = verify_ledger_chain(ledger)
    assert chain["ok"] is True
    assert chain["n"] == 1

    entries = list_receipts(ledger, limit=10)
    assert len(entries) == 1
    assert entries[0]["integrity"] == payload["receipt"]["integrity"]
    assert str(path) == entries[0]["receipt_path"]


def test_ledger_chain_two_entries(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    out = tmp_path / "r"
    for q in ("sharp steam", "hodl diamond hands rekt"):
        result = detect_memetic_patterns(query=q, ingest_source="mock", validate=False)
        emit_receipt(result, out_dir=out, append_ledger=True, ledger_path=ledger)

    chain = verify_ledger_chain(ledger)
    assert chain["ok"] is True
    assert chain["n"] == 2
    assert chain["tip_hash"]


def test_emit_without_ledger(tmp_path: Path) -> None:
    result = detect_memetic_patterns(query="aura farming mid", ingest_source="mock")
    ledger = tmp_path / "should_not_exist.jsonl"
    path = emit_receipt(
        result,
        out_dir=tmp_path / "r",
        append_ledger=False,
        ledger_path=ledger,
    )
    assert path.exists()
    assert not ledger.exists()
    ok, _ = verify_receipt(json.loads(path.read_text(encoding="utf-8")))
    assert ok


def test_default_ledger_path_under_home() -> None:
    p = default_ledger_path()
    assert p.name == "receipt_ledger.jsonl"
    assert ".hyperlex" in str(p)
