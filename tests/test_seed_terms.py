"""Atomic lexicon term splitting — multi-term seeds must not be blended."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = {
    **dict(os.environ),
    "PYTHONPATH": str(ROOT / "src"),
    "HYPERLEX_OFFLINE": "1",
    "HYPERLEX_VECTOR": "0",  # deterministic lineage without vector boost variance
}


def test_split_sigma_rizz_locked_in():
    from hyperlex.analysis.terms import split_seed_terms

    s = split_seed_terms("sigma rizz locked in")
    assert s["terms"] == ["sigma", "rizz", "locked in"]
    assert s["multi_term"] is True
    assert "locked" not in s["terms"]  # phrase kept whole


def test_split_locked_in_crash_out():
    from hyperlex.analysis.terms import split_seed_terms

    s = split_seed_terms("locked in crash out")
    assert "locked in" in s["terms"]
    assert "crash out" in s["terms"]
    assert s["multi_term"] is True


def test_split_single_term():
    from hyperlex.analysis.terms import split_seed_terms

    s = split_seed_terms("rizz")
    assert s["terms"] == ["rizz"]
    assert s["multi_term"] is False


def test_analyze_multi_term_separate():
    from hyperlex import detect_memetic_patterns

    r = detect_memetic_patterns(query="sigma rizz locked in", ingest_source="mock")
    a = r["analysis"]
    assert a.get("multi_term") is True
    assert a["seed_terms"]["terms"] == ["sigma", "rizz", "locked in"]
    assert len(a["per_term"]) == 3
    # primary lineage is single-term match, not density-stacked bag of three
    lin = a.get("lineage") or {}
    assert lin.get("multi_term_mode") is True
    assert lin.get("matched_terms") == [lin.get("primary_term")]
    assert r["provenance"]["brier"] is None


def test_phase5_expands_multi_term():
    from hyperlex.simulation import run_phase5_scenario

    sc = run_phase5_scenario("sigma rizz locked in", domain="ai", include_phylogeny=False)
    assert sc["schema"] == "hyperlex.phase5_multi_term.v1"
    assert sc["terms"] == ["sigma", "rizz", "locked in"]
    assert sc["brier"] is None
    assert sc["multi_term"] is True
    assert len(sc["scenarios"]) == 3
    for nested in sc["scenarios"]:
        assert nested["brier"] is None
        assert nested["seed_term"] in ("sigma", "rizz", "locked in")


def test_phase5_no_expand_keeps_blend():
    from hyperlex.simulation import run_phase5_scenario

    sc = run_phase5_scenario(
        "sigma rizz locked in",
        domain="ai",
        include_phylogeny=False,
        expand_terms=False,
    )
    assert sc["schema"] == "hyperlex.phase5_scenario.v1"
    assert sc["seed_term"] == "sigma rizz locked in"
    assert sc.get("multi_term") is False


def test_cli_terms_split_and_simulate():
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "hyperlex.py"), "terms-split", "sigma rizz locked in"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=ENV,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(r.stdout)
    assert data["split"]["terms"] == ["sigma", "rizz", "locked in"]

    r2 = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "hyperlex.py"),
            "simulate",
            "--term",
            "sigma rizz locked in",
            "--mode",
            "scenario",
            "--domain",
            "ai",
            "--no-phylogeny",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=ENV,
    )
    assert r2.returncode == 0, r2.stderr + r2.stdout
    sim = json.loads(r2.stdout)
    assert sim["multi_term"] is True
    assert sim["terms"] == ["sigma", "rizz", "locked in"]
