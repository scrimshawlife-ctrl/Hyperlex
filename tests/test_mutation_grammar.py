"""Spec 001 detector — civilian fixtures only."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_parse_rizz_register_compose():
    from hyperlex.mutation import parse_mutation_trace

    out = parse_mutation_trace("it's giving mid rizz")
    assert out["schema"] == "hyperlex.mutation_trace.v0.1"
    assert out["brier"] is None
    assert out["forecast_eligible"] is False
    assert "REGISTER_SHIFT" in out["operators"]
    assert "SUBSTITUTE" in out["operators"]
    assert "COMPOSE" in out["operators"]
    assert out["watch_score"] is not None
    assert 0.0 <= float(out["watch_score"]) <= 1.0
    assert out["surface_span"]


def test_parse_unalive_algospeak():
    from hyperlex.mutation import parse_mutation_trace

    out = parse_mutation_trace("unalive")
    assert "SUBSTITUTE" in out["operators"]
    assert out["algospeak_flag"] is True
    assert out["lexicon_hit"] is True
    assert out["brier"] is None


def test_parse_affix_maxxing():
    from hyperlex.mutation import parse_mutation_trace

    out = parse_mutation_trace("aura maxxing")
    assert "AFFIX" in out["operators"]
    assert out["affix_family"] == "maxxing"


def test_parse_eggcorn():
    from hyperlex.mutation import parse_mutation_trace

    out = parse_mutation_trace("for all intensive purposes")
    assert "EGGCORN" in out["operators"]
    assert out["class"] == "OBSERVED"


def test_empty_has_null_brier():
    from hyperlex.mutation import parse_mutation_trace

    out = parse_mutation_trace("   ")
    assert out["operators"] == []
    assert out["brier"] is None
    assert out["forecast_eligible"] is False


def test_restricted_redacts_surface():
    from hyperlex.mutation import parse_mutation_trace

    out = parse_mutation_trace("it's giving mid rizz", restricted_intent_suspected=True)
    assert out["restricted_intent_suspected"] is True
    assert out["surface_span"] is None
    assert out["canonical_gloss"] is None
    assert out["payload_ref"]
    assert len(out["payload_ref"]) == 64
    assert out["forecast_eligible"] is False


def test_watch_score_bounds():
    from hyperlex.mutation.watch import watch_score

    s = watch_score(
        decode_confidence=1.0,
        n_ops=4,
        register_shift="high",
        irony_flag=True,
        affix_productivity=True,
        lexicon_hit=False,
    )
    assert 0.0 <= s <= 1.0


def test_predict_not_used_on_restricted():
    """Wall: detector must not import-call predict_mutations."""
    import inspect
    from hyperlex.mutation import grammar as g

    src = inspect.getsource(g)
    assert "predict_mutations" not in src


def test_cli_module_offline():
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "HYPERLEX_OFFLINE": "1"}
    r = subprocess.run(
        [sys.executable, "-m", "hyperlex.mutation", "it's", "giving", "mid", "rizz"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(r.stdout)
    assert data.get("ok") is True
    assert data.get("brier") is None
    assert data.get("forecast_eligible") is False
    assert "REGISTER_SHIFT" in data.get("operators", [])
