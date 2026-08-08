"""Hermes workflow wizard — week-one guided path."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_wizard_step_order_and_schema():
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
    # skeleton may still return not-fully-wired steps; ids must match
    out = run_wizard(mode="auto", query="rizz")
    assert out["schema"] == WIZARD_SCHEMA
    assert [s["id"] for s in out["steps"]] == list(WIZARD_STEP_IDS)
    assert "brier" in out
    assert out["brier"] is None or out["ok"] is False
    assert isinstance(out.get("next"), list)
