"""Phase 5 — transmission, multi-agent, risk, phylogeny, scenario."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cultural_transmission_deterministic():
    from hyperlex.simulation import simulate_cultural_transmission

    a = simulate_cultural_transmission("rizz", steps=8, virality_hybrid=0.7)
    b = simulate_cultural_transmission("rizz", steps=8, virality_hybrid=0.7)
    assert a["schema"] == "hyperlex.cultural_transmission.v1"
    assert a["brier"] is None
    assert a["provenance"] == "SPECULATIVE"
    assert a["summary"]["peak_mean_adoption"] == b["summary"]["peak_mean_adoption"]
    assert len(a["trajectory"]) == 9  # steps + initial
    assert a["summary"]["final_reach_fraction"] >= 0.0


def test_multi_agent_cascade():
    from hyperlex.simulation import run_multi_agent_memetics

    r = run_multi_agent_memetics("sigma rizz", n_agents=16, steps=12, memetic_score=0.8)
    assert r["schema"] == "hyperlex.multi_agent_memetics.v1"
    assert r["brier"] is None
    assert 0.0 <= r["summary"]["final_adoption_rate"] <= 1.0
    assert len(r["agents"]) == 16
    assert r["history"][0]["n_adopted"] >= 1


def test_hyperstition_risk_tiers():
    from hyperlex.simulation import forecast_hyperstition_risk

    low = forecast_hyperstition_risk(hyperstition_stage="EMERGENT", virality_hybrid=0.1)
    high = forecast_hyperstition_risk(
        hyperstition_stage="ACTUALIZING",
        virality_hybrid=0.9,
        virality_predicted=0.9,
        lineage_confidence=0.9,
        memetic_score=0.9,
        transmission_peak=0.8,
        transmission_reach=0.7,
        agent_cascade_success=True,
        agent_adoption_rate=0.85,
        domain="markets",
    )
    assert low["brier"] is None
    assert high["risk_score"] > low["risk_score"]
    assert high["tier"] in ("ELEVATED", "CRITICAL", "MODERATE")
    assert high["provenance"] == "SPECULATIVE"


def test_risk_from_analysis():
    from hyperlex import detect_memetic_patterns
    from hyperlex.simulation import risk_from_analysis, run_phase5_scenario

    result = detect_memetic_patterns(query="sharp steam revenge", ingest_source="mock")
    risk = risk_from_analysis(result, domain="markets")
    assert risk["brier"] is None
    assert risk["risk_score"] is not None
    # full scenario from analysis — single atomic seed (multi-word bags expand by default)
    sc = run_phase5_scenario(
        "sharp",
        analysis_result=result,
        domain="markets",
        expand_terms=False,
    )
    assert sc["schema"] == "hyperlex.phase5_scenario.v1"
    assert sc["brier"] is None
    assert sc["hyperstition_risk"]["brier"] is None
    assert sc["transmission"]["brier"] is None


def test_phylogeny_families():
    from hyperlex.simulation import build_family_phylogeny, list_phylogeny_families

    fams = list_phylogeny_families()
    assert "brainrot-aura" in fams
    tree = build_family_phylogeny("brainrot-aura")
    assert tree["ok"] is True
    assert tree["n_nodes"] >= 3
    assert tree["brier"] is None
    bad = build_family_phylogeny("not-a-real-family")
    assert bad["ok"] is False


def test_cli_simulate_scenario(tmp_path):
    out = tmp_path / "scenario.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "hyperlex.py"),
            "simulate",
            "--term",
            "rizz",
            "--mode",
            "scenario",
            "--domain",
            "ai",
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={**dict(__import__("os").environ), "PYTHONPATH": str(ROOT / "src"), "HYPERLEX_OFFLINE": "1"},
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(r.stdout)
    assert data["ok"] is True
    assert data["scenario"]["brier"] is None
    full = json.loads(out.read_text(encoding="utf-8"))
    assert full["schema"] == "hyperlex.phase5_scenario.v1"
    assert full["seed_term"] == "rizz"
    assert full["hyperstition_risk"]["tier"] in ("LOW", "MODERATE", "ELEVATED", "CRITICAL")


def test_cli_simulate_from_analyze():
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "hyperlex.py"),
            "simulate",
            "--term",
            "agentic slop skill issue",
            "--from-analyze",
            "--mode",
            "risk",
            "--domain",
            "ai",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={**dict(__import__("os").environ), "PYTHONPATH": str(ROOT / "src"), "HYPERLEX_OFFLINE": "1"},
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(r.stdout)
    assert data["scenario"]["brier"] is None
