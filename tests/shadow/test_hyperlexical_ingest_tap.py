import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
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
    assert row["license"] == "operator-local-crawl; labels INFERRED"
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


def test_reject_junk_atom():
    assert row_from_atom("ab", source="inbox") is None
    assert row_from_atom("12345", source="inbox") is None
    assert row_from_atom("Unsupported title", source="inbox") is None
