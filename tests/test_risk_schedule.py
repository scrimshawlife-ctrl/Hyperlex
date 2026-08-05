"""Risk-tier → scan/cron schedule coupling (advisory)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = {
    **dict(__import__("os").environ),
    "PYTHONPATH": str(ROOT / "src"),
    "HYPERLEX_OFFLINE": "1",
}


def test_tier_policy_ordering():
    from hyperlex.simulation import TIER_POLICY, policy_for_tier

    assert set(TIER_POLICY) == {"LOW", "MODERATE", "ELEVATED", "CRITICAL"}
    assert policy_for_tier("LOW")["interval_hours"] > policy_for_tier("CRITICAL")["interval_hours"]
    assert policy_for_tier("CRITICAL")["max_queries"] >= policy_for_tier("LOW")["max_queries"]
    assert policy_for_tier("bogus")["interval_hours"] == TIER_POLICY["MODERATE"]["interval_hours"]


def test_plan_scan_from_tier_advisory():
    from hyperlex.simulation import plan_scan_from_tier

    plan = plan_scan_from_tier("ELEVATED")
    assert plan["schema"] == "hyperlex.risk_scan_plan.v1"
    assert plan["brier"] is None
    assert plan["provenance"] == "SPECULATIVE"
    assert plan["tier"] == "ELEVATED"
    assert plan["job"]["state"] == "proposed"
    assert plan["job"]["schedule"]["expr"] == "0 */2 * * *"
    assert plan["policy"]["vector_seed"] is True
    assert "hermes cron add" in plan["hermes_cron_hint"]
    assert "ADVISORY" in plan["job"]["notes"][0]


def test_plan_scan_from_term_and_write(tmp_path):
    from hyperlex.simulation import plan_scan_from_term, write_scan_plan

    plan = plan_scan_from_term("rizz locked in", domain="ai", use_phase5=True)
    assert plan["brier"] is None
    assert plan["tier"] in ("LOW", "MODERATE", "ELEVATED", "CRITICAL")
    assert "rizz locked in" in plan["queries"] or plan["queries"]

    written = write_scan_plan(plan, out_dir=tmp_path)
    assert written["ok"] is True
    assert Path(written["job_path"]).is_file()
    assert Path(written["queries_path"]).is_file()
    assert Path(written["plan_path"]).is_file()
    job = json.loads(Path(written["job_path"]).read_text(encoding="utf-8"))
    assert job["no_agent"] is True
    assert job["risk_tier"] == plan["tier"]


def test_aggregate_scan_risk():
    from hyperlex.simulation import aggregate_scan_risk

    rows = [
        {"query": "a", "lineage_family": "brainrot-aura"},
        {"query": "b", "lineage_family": "finance-slang"},
        {"query": "c", "lineage_family": None},
        {"query": "d", "lineage_family": "ai-native"},
    ]
    agg = aggregate_scan_risk(rows)
    assert agg["schema"] == "hyperlex.scan_risk_aggregate.v1"
    assert agg["brier"] is None
    assert agg["n_with_lineage"] == 3
    assert agg["recommended_tier"] in ("LOW", "MODERATE", "ELEVATED", "CRITICAL")
    assert "cron" in agg["next_plan"]


def test_cli_risk_schedule_tier(tmp_path):
    out_dir = tmp_path / "cron"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "hyperlex.py"),
            "risk-schedule",
            "--tier",
            "CRITICAL",
            "--schedule-out",
            str(out_dir),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=ENV,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(r.stdout)
    assert data["ok"] is True
    assert data["plan"]["tier"] == "CRITICAL"
    assert data["plan"]["brier"] is None
    assert data["written"]["ok"] is True
    job_files = list(out_dir.glob("*.job.json"))
    assert len(job_files) == 1


def test_cli_simulate_mode_schedule():
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "hyperlex.py"),
            "simulate",
            "--mode",
            "schedule",
            "--tier",
            "LOW",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=ENV,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(r.stdout)
    assert data["ok"] is True
    assert data["mode"] == "schedule"
    assert data["scenario"]["tier"] == "LOW"
    assert data["scenario"]["brier"] is None


def test_cli_scan_includes_advisory():
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "hyperlex.py"),
            "scan",
            "--queries",
            "rizz locked in,sharp steam revenge,agentic slop",
            "--source",
            "mock",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=ENV,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(r.stdout)
    assert data["ok"] is True
    adv = data.get("scan_risk_advisory") or {}
    assert adv.get("brier") is None
    assert "recommended_tier" in adv
    assert adv.get("schema") == "hyperlex.scan_risk_aggregate.v1"
