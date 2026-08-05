"""Phase 5.1/5.2 — transmission calibration, scenario library, research export."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "examples" / "calibration" / "settled_series.v1.json"


def test_calibrate_transmission_from_golden():
    from hyperlex.simulation import calibrate_transmission_params

    out = calibrate_transmission_params(golden_path=GOLDEN)
    assert out["ok"] is True
    assert out["brier"] is None
    assert out["provenance"] == "SPECULATIVE"
    assert out["best_params"] is not None
    assert "beta" in out["best_params"]
    assert "gamma" in out["best_params"]
    assert out["n_pairs"] >= 1


def test_scenario_library_compare():
    from hyperlex.simulation import compare_scenarios, list_scenario_presets, run_named_scenario

    presets = list_scenario_presets()
    assert len(presets) >= 4
    one = run_named_scenario("viral_cascade", "rizz")
    assert one["ok"] is True
    assert one["brier"] is None
    assert one["summary"] is not None
    cmp = compare_scenarios("rizz", scenario_ids=["baseline", "skeptic_wall", "viral_cascade"])
    assert cmp["ok"] is True
    assert cmp["n_scenarios"] == 3
    assert len(cmp["ranking"]) == 3


def test_research_export(tmp_path: Path):
    from hyperlex.simulation import compare_scenarios, export_research_packet

    cmp = compare_scenarios("agentic slop", scenario_ids=["baseline", "slow_burn"])
    exp = export_research_packet(cmp, out_dir=tmp_path, title="compare-demo", snapshot_id="t1")
    assert exp["ok"] is True
    assert Path(exp["json_path"]).is_file()
    assert Path(exp["md_path"]).is_file()
    assert exp["brier"] is None
