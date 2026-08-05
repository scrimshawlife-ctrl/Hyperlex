"""Cross-domain lineages + case study script."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from hyperlex import detect_memetic_patterns, match_lineage
from hyperlex.analysis import LINEAGE_REGISTRY, memetics_protocol_check

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_case_study.py"


def test_registry_has_gaming_and_workplace() -> None:
    ids = {e["family_id"] for e in LINEAGE_REGISTRY}
    assert "gaming-meta" in ids
    assert "workplace-corp" in ids


def test_match_gaming_meta() -> None:
    m = match_lineage("nerf buff meta sweaty smurf skill issue gg")
    assert m is not None
    assert m["family_id"] == "gaming-meta"
    assert m["confidence"] >= 0.42


def test_match_workplace_corp() -> None:
    m = match_lineage("quiet quitting rto bandwidth circle back act your wage layoffs")
    assert m is not None
    assert m["family_id"] == "workplace-corp"


def test_analyze_gaming_mock() -> None:
    r = detect_memetic_patterns("nerf buff meta sweaty gaming", ingest_source="mock")
    assert r["provenance"]["brier"] is None
    lin = r["analysis"].get("lineage") or {}
    assert lin.get("family_id") == "gaming-meta"
    mem = r["analysis"]["memetics"]
    assert mem.get("typology_primary") in {"platform_agency", "tactical_edge", "status_radiation"}


def test_analyze_workplace_mock() -> None:
    r = detect_memetic_patterns("quiet quitting rto workplace corp", ingest_source="mock")
    lin = r["analysis"].get("lineage") or {}
    assert lin.get("family_id") == "workplace-corp"
    mem = r["analysis"]["memetics"]
    assert mem.get("typology_primary") == "labor_identity" or "labor_identity" in (mem.get("typology_scores") or {})


def test_labor_identity_typology() -> None:
    m = memetics_protocol_check("quiet quitting act your wage bandwidth rto")
    assert m["typology_primary"] == "labor_identity"


def test_case_study_script(tmp_path: Path) -> None:
    env = __import__("os").environ.copy()
    env["HYPERLEX_OFFLINE"] = "1"
    env["PYTHONPATH"] = str(ROOT / "src")
    out = tmp_path / "cs"
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--out-dir", str(out)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["ok"] is True
    assert summary["brier"] is None
    assert summary["n_forecasts"] >= 1
    assert (out / "analyze.json").exists()
    assert (out / "diagrams").exists()
