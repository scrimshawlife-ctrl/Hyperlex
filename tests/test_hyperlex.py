import json
import subprocess
import sys
from pathlib import Path

import pytest

from hyperlex import emit_receipt, detect_memetic_patterns, schemas

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "hyperlex.py"


def _run_cli(*args: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = dict(**dict())
    env.update(__import__("os").environ.copy())
    env.update(env_extra or {})
    env["HYPERLEX_OFFLINE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=ROOT,
    )


def _load_json(payload: str):
    return json.loads(payload)


def test_cli_check_ok() -> None:
    result = _run_cli("check")
    assert result.returncode == 0
    body = _load_json(result.stdout)
    assert body["ok"] is True
    assert body["version"] == "0.2.6"
    checks = {entry["name"]: entry["ok"] for entry in body["checks"]}
    assert checks["version_file"]
    assert checks["schema_ingest"]


def test_sources_command() -> None:
    result = _run_cli("sources")
    assert result.returncode == 0
    body = _load_json(result.stdout)
    names = [entry["name"] for entry in body["sources"]]
    assert "mock" in names
    assert "real" in names
    assert "combined" in names
    assert "firecrawl" in names
    assert "crawl4ai" in names


def test_ingest_mock_structured() -> None:
    result = _run_cli("ingest", "sharp money revenge", "--source", "mock", "--structured")
    assert result.returncode == 0
    body = _load_json(result.stdout)
    assert body["ok"] is True
    payload = body["result"]
    assert payload["query"] == "sharp money revenge"
    assert payload["source"] == "mock"
    assert isinstance(payload["extracted_terms"], list)


def test_ingest_crawl4ai_fallback_is_safe() -> None:
    result = _run_cli("ingest", "sharp money revenge", "--source", "crawl4ai", "--structured")
    assert result.returncode == 0
    body = _load_json(result.stdout)
    payload = body["result"]
    assert payload["source"] == "crawl4ai"
    assert payload["raw_signal"]
    assert payload["metadata"]["source_type"] == "real"


def test_analyze_and_validate_schema() -> None:
    result = _run_cli(
        "analyze",
        "--query",
        "sharp money revenge",
        "--source",
        "mock",
        "--validate",
    )
    assert result.returncode == 0
    body = _load_json(result.stdout)
    payload = body["result"]
    assert body["ok"] is True
    assert payload["provenance"]["version"] == "0.2.6"
    assert "schema_validation" in payload
    assert payload["schema_validation"]["valid"]


def test_receipt_verify_cycle(tmp_path: Path) -> None:
    result = detect_memetic_patterns(query="sharp money revenge", ingest_source="mock", validate=True)
    receipt_path = emit_receipt(
        result,
        out_dir=tmp_path / "receipts",
        validate=True,
        append_ledger=True,
        ledger_path=tmp_path / "receipt_ledger.jsonl",
    )

    validate_cmd = _run_cli("validate", str(receipt_path))
    assert validate_cmd.returncode == 0
    validate_body = _load_json(validate_cmd.stdout)
    assert validate_body["ok"] is True
    assert validate_body["schema"] in {"receipt", "result"}

    verify_cmd = _run_cli("verify-receipt", str(receipt_path))
    assert verify_cmd.returncode == 0
    verify_body = _load_json(verify_cmd.stdout)
    assert verify_body["ok"] is True
    assert verify_body["expected"] == verify_body["actual"]

    # Guard against accidental mutation
    mutated = json.loads(receipt_path.read_text(encoding="utf-8"))
    mutated["observed"] = mutated["observed"] + " MUTATED"
    mutated_path = tmp_path / "mutated_receipt.json"
    mutated_path.write_text(json.dumps(mutated, indent=2), encoding="utf-8")
    verify_mutated = _run_cli("verify-receipt", str(mutated_path))
    assert verify_mutated.returncode == 2
    mutated_body = _load_json(verify_mutated.stdout)
    assert mutated_body["ok"] is False


def test_smoke() -> None:
    result = _run_cli("smoke")
    assert result.returncode == 0
    assert _load_json(result.stdout)["ok"] is True


def test_schemas_validate_helper_matches_cli() -> None:
    payload = detect_memetic_patterns("low block", ingest_source="mock", validate=False)
    ok, msg = schemas.validate_result(payload)
    assert ok
    assert msg == "valid"
