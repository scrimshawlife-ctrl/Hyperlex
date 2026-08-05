"""YTD backfill packs + non-mutating lineage backpropagation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BACKFILL = ROOT / "data" / "backfill"


def test_backfill_packs_exist_jan_through_aug():
    year_dir = BACKFILL / "2026"
    assert year_dir.is_dir()
    labels = sorted(p.stem for p in year_dir.glob("2026-*.json"))
    assert labels == [f"2026-{m:02d}" for m in range(1, 9)]


def test_inventory_and_apply():
    from hyperlex.analysis.backfill import apply_backfill, inventory_backfill

    inv = inventory_backfill(2026, root=BACKFILL, through="2026-08")
    assert inv["n_packs"] == 8
    assert inv["n_term_entries"] >= 40
    assert "brainrot-aura" in inv["by_family"]
    assert inv["by_provenance"]  # OBSERVED and/or INFERRED

    report = apply_backfill(2026, through="2026-08", root=BACKFILL)
    assert report["mutates_receipts"] is False
    assert report["merged_term_count"] >= report["base_term_count"]
    # base registry already includes 2026 leaves; packs may add little or nothing
    assert "merged_registry" in report
    fams = {e["family_id"] for e in report["merged_registry"]}
    assert "brainrot-aura" in fams
    brain = next(e for e in report["merged_registry"] if e["family_id"] == "brainrot-aura")
    terms_l = {t.lower() for t in brain["terms"]}
    assert "rizz" in terms_l
    assert "locked in" in terms_l
    assert "six seven" in terms_l


def test_match_lineage_2026_terms():
    from hyperlex.analysis import match_lineage

    hit = match_lineage("that sigma rizz is locked in no cap")
    assert hit is not None
    assert hit["family_id"] == "brainrot-aura"
    assert hit["confidence"] >= 0.42
    matched = {t.lower() for t in hit["matched_terms"]}
    assert "rizz" in matched or "sigma" in matched or "locked in" in matched


def test_match_lineage_registry_override():
    from hyperlex.analysis import match_lineage

    tiny = [
        {
            "family_id": "test-only",
            "terms": ["zzuniquebackfilltoken"],
            "branch_operator": "test",
            "diagram_ref": None,
            "payload_note": "unit test",
        }
    ]
    hit = match_lineage("hello zzuniquebackfilltoken world", registry=tiny)
    assert hit is not None
    assert hit["family_id"] == "test-only"
    # base registry should not know this token
    assert match_lineage("hello zzuniquebackfilltoken world") is None


def test_backprop_from_golden_integrity_preserving():
    from hyperlex.analysis.backprop import backpropagate_lineage

    report = backpropagate_lineage(
        year=2026,
        through="2026-08",
        backfill_root=BACKFILL,
        from_golden=True,
        repo_root=ROOT,
        use_backfill=True,
    )
    assert report["schema"] == "hyperlex.lineage_backprop.v1"
    assert report["mutates_receipts"] is False
    assert report["integrity_preserving"] is True
    assert report["brier_invented"] is False
    assert report["n_receipts"] >= 8
    # goldens should mostly stay on their families
    for row in report["rows"]:
        assert row["receipt_mutated"] is False
        if row["prior_family"] and row["change"] == "reclassified":
            # allow but rare; document in report
            assert row["new_family"] is not None


def test_backprop_gains_on_synthetic_open_text(tmp_path):
    from hyperlex.analysis.backprop import rematch_receipt
    from hyperlex.analysis.backfill import apply_backfill

    # receipt with no lineage but 2026 slang text
    receipt = {
        "query": "sigma rizz locked in",
        "observed": "bro that sigma rizz is locked in no cap",
        "analysis": {},
        "provenance": {"integrity": "syntheticdeadbeef"},
    }
    merged = apply_backfill(2026, root=BACKFILL)["merged_registry"]
    row = rematch_receipt(receipt, registry=merged)
    assert row["change"] == "gained"
    assert row["new_family"] == "brainrot-aura"
    assert row["receipt_mutated"] is False


def test_cli_lineage_backfill_list():
    import subprocess
    import sys

    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "hyperlex.py"), "lineage-backfill", "--list", "--through", "2026-03"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={**dict(__import__("os").environ), "PYTHONPATH": str(ROOT / "src"), "HYPERLEX_OFFLINE": "1"},
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["ok"] is True
    assert data["n_packs"] == 3


def test_cli_lineage_backprop_golden(tmp_path):
    import subprocess
    import sys

    out = tmp_path / "backprop.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "hyperlex.py"),
            "lineage-backprop",
            "--from-golden",
            "--through",
            "2026-08",
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
    assert data["integrity_preserving"] is True
    assert out.is_file()
    full = json.loads(out.read_text(encoding="utf-8"))
    assert "rows" in full
