"""Atomic lexicon term splitting — multi-term seeds must not be blended.

Covers engine behavior + Pages demo fixtures under examples/demos/.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEMOS = ROOT / "examples" / "demos"
ENV = {
    **dict(os.environ),
    "PYTHONPATH": str(ROOT / "src"),
    "HYPERLEX_OFFLINE": "1",
    "HYPERLEX_VECTOR": "0",  # deterministic lineage without vector boost variance
}

# Demo matrix (must match docs/demos/atomic-terms.md + demo bundle)
DEMO_CASES = [
    ("sigma rizz locked in", ["sigma", "rizz", "locked in"]),
    ("agentic slop skill issue", ["agentic slop", "skill issue"]),
    ("sharp steam revenge", ["sharp", "steam", "revenge"]),
    ("locked in crash out", ["locked in", "crash out"]),
]


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


def test_split_agentic_slop_skill_issue():
    from hyperlex.analysis.terms import split_seed_terms

    s = split_seed_terms("agentic slop skill issue")
    assert s["terms"] == ["agentic slop", "skill issue"]
    assert s["multi_term"] is True
    # compound phrase not split into agentic + slop alone
    assert "agentic" not in s["terms"] or "agentic slop" in s["terms"]


def test_split_sharp_steam_revenge():
    from hyperlex.analysis.terms import split_seed_terms

    s = split_seed_terms("sharp steam revenge")
    assert s["terms"] == ["sharp", "steam", "revenge"]
    assert s["multi_term"] is True


def test_split_single_term():
    from hyperlex.analysis.terms import split_seed_terms

    s = split_seed_terms("rizz")
    assert s["terms"] == ["rizz"]
    assert s["multi_term"] is False


@pytest.mark.parametrize("text,expected", DEMO_CASES)
def test_demo_matrix_split(text, expected):
    from hyperlex.analysis.terms import split_seed_terms

    s = split_seed_terms(text)
    assert s["terms"] == expected
    assert s["multi_term"] is (len(expected) > 1)


def test_demo_fixtures_on_disk():
    """Pages demos ship fixtures under examples/demos/."""
    assert DEMOS.is_dir()
    for name in (
        "terms-split-sigma-rizz-locked-in.json",
        "terms-split-agentic-slop-skill-issue.json",
        "terms-split-locked-in-crash-out.json",
        "phase5-multi-sigma-rizz-locked-in.json",
        "atomic-terms-demo-bundle.json",
    ):
        path = DEMOS / name
        assert path.is_file(), f"missing demo fixture {name}"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("brier") is None or "brier" not in data or data.get("split", {}).get("brier") is None


def test_demo_bundle_matches_engine():
    from hyperlex.analysis.terms import split_seed_terms
    from hyperlex.simulation import run_phase5_scenario

    bundle = json.loads((DEMOS / "atomic-terms-demo-bundle.json").read_text(encoding="utf-8"))
    assert bundle["schema"] == "hyperlex.atomic_terms_demo.v1"
    assert len(bundle["cases"]) >= 4
    for case in bundle["cases"]:
        text = case["input"]
        live = split_seed_terms(text)["terms"]
        assert live == case["split_terms"], f"bundle stale for {text!r}"
        sc = run_phase5_scenario(text, domain=case.get("domain") or "ai", include_phylogeny=False)
        assert sc["brier"] is None
        if case["multi_term"]:
            assert sc["schema"] == "hyperlex.phase5_multi_term.v1"
            assert sc["terms"] == case["split_terms"]
            assert len(sc["scenarios"]) == len(case["split_terms"])
        assert case.get("brier") is None


def test_phase5_fixture_compact():
    data = json.loads((DEMOS / "phase5-multi-sigma-rizz-locked-in.json").read_text(encoding="utf-8"))
    assert data["schema"] == "hyperlex.phase5_multi_term.v1"
    assert data["terms"] == ["sigma", "rizz", "locked in"]
    assert data["multi_term"] is True
    assert data["brier"] is None
    assert len(data["summaries"]) == 3
    for row in data["summaries"]:
        assert row["brier"] is None
        assert row["seed_term"] in data["terms"]


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


@pytest.mark.parametrize("text,expected", DEMO_CASES)
def test_analyze_demo_matrix(text, expected):
    from hyperlex import detect_memetic_patterns

    r = detect_memetic_patterns(query=text, ingest_source="mock")
    a = r["analysis"]
    assert a["seed_terms"]["terms"] == expected
    if len(expected) > 1:
        assert a.get("multi_term") is True
        assert len(a.get("per_term") or []) == len(expected)
        lin = a.get("lineage") or {}
        if lin.get("multi_term_mode"):
            # primary is one of the split atoms (not the full bag string)
            assert lin.get("primary_term") in expected
            assert lin.get("primary_term") != text
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


@pytest.mark.parametrize("text,expected", DEMO_CASES)
def test_phase5_demo_matrix(text, expected):
    from hyperlex.simulation import run_phase5_scenario

    sc = run_phase5_scenario(text, domain="ai", include_phylogeny=False)
    assert sc["brier"] is None
    if len(expected) > 1:
        assert sc["schema"] == "hyperlex.phase5_multi_term.v1"
        assert sc["terms"] == expected
        assert len(sc["scenarios"]) == len(expected)
        for nested in sc["scenarios"]:
            assert nested["brier"] is None
            assert nested["seed_term"] in expected
    else:
        assert sc["schema"] == "hyperlex.phase5_scenario.v1"


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


def test_schedule_expands_seed_bag_to_atoms():
    from hyperlex.simulation.schedule import plan_scan_from_tier, plan_scan_from_risk

    plan = plan_scan_from_risk(
        {"tier": "MODERATE", "risk_score": 0.4, "seed_term": "sigma rizz locked in"},
        seed_term="sigma rizz locked in",
    )
    q = [str(x).lower() for x in (plan.get("queries") or [])]
    assert "sigma" in q or "rizz" in q or "locked in" in q
    # must not keep the full bag as a single query when expand works
    assert "sigma rizz locked in" not in q


def test_archive_sanitize_multi_term():
    from hyperlex.archive.export import sanitize_phase5_summary
    from hyperlex.simulation import run_phase5_scenario

    sc = run_phase5_scenario("sigma rizz locked in", domain="ai", include_phylogeny=False)
    summary = sanitize_phase5_summary(sc)
    assert summary["multi_term"] is True
    assert summary["terms"] == ["sigma", "rizz", "locked in"]
    assert summary["seed_term"] is None
    assert summary["brier"] is None
    assert summary["risk_tier"] is not None  # top aggregate tier


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


@pytest.mark.parametrize("text,expected", DEMO_CASES)
def test_cli_terms_split_demo_matrix(text, expected):
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "hyperlex.py"), "terms-split", text, "--no-lineage"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=ENV,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(r.stdout)
    assert data["split"]["terms"] == expected
