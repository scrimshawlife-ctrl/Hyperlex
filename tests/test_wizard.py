"""Hermes workflow wizard — week-one guided path."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_wizard_step_order_and_schema(tmp_path):
    from hyperlex.wizard import WIZARD_SCHEMA, WIZARD_STEP_IDS, run_wizard

    assert WIZARD_SCHEMA == "hyperlex.wizard.v1"
    assert list(WIZARD_STEP_IDS) == [
        "env_intro",
        "doctor",
        "demo",
        "first_pipeline",
        "calibration_coach",
        "score_series_hint",
        "handoff",
    ]
    out = run_wizard(
        mode="auto",
        query="rizz",
        skill_root=ROOT,
        out_dir=tmp_path / "wiz",
    )
    assert out["schema"] == WIZARD_SCHEMA
    assert [s["id"] for s in out["steps"]] == list(WIZARD_STEP_IDS)
    assert "brier" in out
    assert out["brier"] is None or out["ok"] is False
    assert isinstance(out.get("next"), list)


def test_wizard_auto_offline_null_brier(tmp_path, monkeypatch):
    monkeypatch.setenv("HYPERLEX_OFFLINE", "1")
    monkeypatch.setenv("HYPERLEX_VECTOR", "0")
    from hyperlex.wizard import run_wizard

    out = run_wizard(
        mode="auto",
        query="rizz",
        skill_root=ROOT,
        out_dir=tmp_path / "wiz",
        strict=False,
    )
    assert out["ok"] is True, out
    assert out["schema"] == "hyperlex.wizard.v1"
    assert out["brier"] is None
    assert out["route"] == "offline"
    ids = [s["id"] for s in out["steps"]]
    assert ids == [
        "env_intro",
        "doctor",
        "demo",
        "first_pipeline",
        "calibration_coach",
        "score_series_hint",
        "handoff",
    ]
    by_id = {s["id"]: s for s in out["steps"]}
    assert by_id["demo"]["ok"] is True
    assert by_id["first_pipeline"]["ok"] is True
    assert by_id["calibration_coach"]["ok"] is True
    # open analysis artifacts must not claim brier
    for sid in ("demo", "first_pipeline"):
        art = by_id[sid].get("artifacts") or {}
        assert art.get("brier") in (None, )
    assert any("settle" in c for c in out["next"])


def test_wizard_no_settle_side_effect(tmp_path, monkeypatch):
    monkeypatch.setenv("HYPERLEX_OFFLINE", "1")
    monkeypatch.setenv("HYPERLEX_VECTOR", "0")
    from hyperlex.calibration.score_log import index_settlements, read_log
    from hyperlex.wizard import run_wizard

    log = tmp_path / "wiz" / "wizard_score_log.jsonl"
    out_dir = tmp_path / "wiz"
    # first run creates log
    run_wizard(mode="auto", query="rizz", skill_root=ROOT, out_dir=out_dir)
    before = len(index_settlements(read_log(log)))
    run_wizard(mode="auto", query="rizz", skill_root=ROOT, out_dir=out_dir)
    after = len(index_settlements(read_log(log)))
    assert after == before


def test_wizard_skip_doctor(tmp_path, monkeypatch):
    monkeypatch.setenv("HYPERLEX_OFFLINE", "1")
    monkeypatch.setenv("HYPERLEX_VECTOR", "0")
    from hyperlex.wizard import run_wizard

    out = run_wizard(
        mode="auto",
        query="rizz",
        skill_root=ROOT,
        out_dir=tmp_path / "wiz2",
        skip_doctor=True,
    )
    doc = next(s for s in out["steps"] if s["id"] == "doctor")
    assert doc["skipped"] is True
    assert out["ok"] is True
