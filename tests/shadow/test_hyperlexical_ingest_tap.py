import json
import pathlib
import sys
from argparse import Namespace

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.ingest_tap import (
    append_rows,
    harvest_store,
    row_from_atom,
    rows_from_analysis,
    rows_from_inbox,
    rows_from_pipeline_packet,
    tap_analysis,
)


def test_row_is_inferred_weak():
    row = row_from_atom("locked in", family="brainrot-aura", source="pipeline")
    assert row is not None
    assert row["class"] == "INFERRED"
    assert row["task"] == "classify"
    assert row["lineage"] == "brainrot-aura"
    assert row["provenance"] == "ingest:pipeline"
    assert row["license"] == "operator-local"
    assert "/home/" not in json.dumps(row)
    assert ".hyperlex" not in json.dumps(row)


def test_collision_hold():
    row = row_from_atom("skill issue", family="ai-native", source="scan")
    assert row["lineage"] == "none"
    assert row["class"] == "INFERRED"


def test_rows_from_analysis_packet():
    result = {
        "query": "rizz",
        "ingest": {"query": "rizz"},
        "analysis": {
            "primary_term": "rizz",
            "lineage": {"family_id": "brainrot-aura", "matched_terms": ["rizz"]},
            "neologisms": [{"term": "aura farm"}],
            "hyperstition": {"loop_stage": "EMERGENT"},
        },
    }
    rows = rows_from_analysis(result, query="rizz")
    texts = {r["text"] for r in rows}
    assert "rizz" in texts
    assert "aura farm" in texts
    assert all(r["class"] == "INFERRED" for r in rows)
    assert all(r["stage"] == "circulating" for r in rows)


def test_pipeline_packet_units():
    packet = {
        "schema": "hyperlex.pipeline_result.v1",
        "results": [
            {
                "query": "no cap",
                "result": {
                    "analysis": {
                        "primary_term": "no cap",
                        "lineage": {"family_id": "brainrot-aura", "matched_terms": []},
                    }
                },
            }
        ],
    }
    rows = rows_from_pipeline_packet(packet)
    assert rows
    assert rows[0]["text"] == "no cap"


def test_inbox_and_store(tmp_path):
    inbox = tmp_path / "inbox.jsonl"
    inbox.write_text(
        json.dumps({"payload": {"term": "let him cook", "lineage_family": "brainrot-aura"}}) + "\n",
        encoding="utf-8",
    )
    rows = rows_from_inbox(inbox)
    assert rows[0]["text"] == "let him cook"
    store = tmp_path / "ingest_candidates.jsonl"
    report = append_rows(rows, store)
    assert report["added"] == 1
    report2 = append_rows(rows, store)
    assert report2["added"] == 0
    harvested = harvest_store(store)
    assert harvested[0]["class"] == "INFERRED"
    assert harvested[0]["provenance"] == "ingest:store"


def test_tap_fail_open():
    out = tap_analysis({}, query="")
    assert out["ok"] is True
    assert out.get("skipped") is True
    assert out["brier"] is None


def test_attach_hyperlexical_tap_loads_shadow_module(monkeypatch, tmp_path):
    from hyperlex.pipeline import attach_hyperlexical_tap

    store = tmp_path / "ingest_candidates.jsonl"
    monkeypatch.setenv("HYPERLEX_HYPERLEXICAL_STORE", str(store))
    result = {
        "query": "rizz",
        "ingest": {"query": "rizz"},
        "analysis": {
            "primary_term": "rizz",
            "lineage": {"family_id": "brainrot-aura", "matched_terms": ["rizz"]},
        },
    }
    report = attach_hyperlexical_tap(result, query="rizz", source="pipeline")
    assert report["ok"] is True
    assert report["brier"] is None
    harvested = harvest_store(store)
    assert any(row["text"] == "rizz" for row in harvested)


def test_run_one_appends_hyperlexical_tap_step(monkeypatch, tmp_path):
    from hyperlex.pipeline import run_one

    monkeypatch.setenv("HYPERLEX_HYPERLEXICAL_STORE", str(tmp_path / "ingest_candidates.jsonl"))
    unit = run_one("rizz", route="offline", receipt=False, forecasts=False, phase5=False)
    assert unit["ok"] is True
    assert "hyperlexical_tap" in unit["steps"]
    assert unit["hyperlexical_tap"]["brier"] is None


def test_cli_analyze_and_scan_call_tap(monkeypatch):
    import hyperlex.cli as cli
    import hyperlex.pipeline as pipeline

    calls = []
    emitted = []

    def fake_attach(result, *, query="", source="pipeline"):
        calls.append((query, source, ((result.get("analysis") or {}).get("primary_term"))))
        return {"ok": True, "added": 1, "brier": None}

    monkeypatch.setattr(cli, "_emit", emitted.append)
    monkeypatch.setattr(pipeline, "attach_hyperlexical_tap", fake_attach)

    analyze_args = Namespace(
        query_pos=None,
        query="rizz",
        source="mock",
        route="offline",
        validate=False,
        command_label=None,
        receipt=False,
        receipt_dir=None,
        forecasts=False,
        relay=False,
        out="",
    )
    scan_args = Namespace(
        query=None,
        queries="rizz,locked in",
        source="mock",
        receipt=False,
        forecasts=False,
    )

    assert cli.cmd_analyze(analyze_args) == 0
    assert cli.cmd_scan(scan_args) == 0
    assert ("rizz", "analyze", "rizz") in calls
    assert ("rizz", "scan", "rizz") in calls
    assert ("locked in", "scan", "locked in") in calls
    assert emitted[0]["hyperlexical_tap"]["added"] == 1
    assert emitted[1]["results"][0]["hyperlexical_tap"]["added"] == 1


def test_cli_analyze_reuses_existing_tap(monkeypatch):
    import hyperlex as hyperlex_pkg
    import hyperlex.cli as cli
    import hyperlex.pipeline as pipeline

    emitted = []

    def fake_detect_memetic_patterns(**_kwargs):
        return {
            "analysis": {
                "primary_term": "rizz",
                "lineage": {"family_id": "brainrot-aura", "matched_terms": ["rizz"]},
            },
            "hyperlexical_tap": {"ok": True, "added": 0, "brier": None},
        }

    def fail_attach(*_args, **_kwargs):
        raise AssertionError("attach_hyperlexical_tap should not run when result already includes a tap report")

    monkeypatch.setattr(cli, "_emit", emitted.append)
    monkeypatch.setattr(hyperlex_pkg, "detect_memetic_patterns", fake_detect_memetic_patterns)
    monkeypatch.setattr(pipeline, "attach_hyperlexical_tap", fail_attach)

    analyze_args = Namespace(
        query_pos=None,
        query="rizz",
        source="mock",
        route="offline",
        validate=False,
        command_label=None,
        receipt=False,
        receipt_dir=None,
        forecasts=False,
        relay=False,
        out="",
    )

    assert cli.cmd_analyze(analyze_args) == 0
    assert emitted[0]["hyperlexical_tap"]["added"] == 0
