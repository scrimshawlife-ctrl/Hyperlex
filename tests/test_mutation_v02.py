"""Spec 003 — civilian fixtures only. Detect, never generate."""
from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phonetic_warp_rzz():
    from hyperlex.mutation import parse_mutation_trace

    out = parse_mutation_trace("rzz")
    assert "PHONETIC_WARP" in out["operators"]
    assert out["recovered_lemma"] == "rizz"
    assert out["brier"] is None
    assert out["forecast_eligible"] is False
    assert "L1" in out["layers_touched"]


def test_phonetic_warp_brainrot():
    from hyperlex.mutation import parse_mutation_trace

    out = parse_mutation_trace("brnrt")
    assert "PHONETIC_WARP" in out["operators"]
    assert out["recovered_lemma"] == "brainrot"
    assert out["brier"] is None


def test_phonetic_warp_with_register():
    from hyperlex.mutation import parse_mutation_trace

    out = parse_mutation_trace("it's giving rzz")
    assert "REGISTER_SHIFT" in out["operators"]
    assert "PHONETIC_WARP" in out["operators"]
    assert "COMPOSE" in out["operators"]
    assert out["forecast_eligible"] is False


def test_v01_rizz_not_phonetic_warp():
    from hyperlex.mutation import parse_mutation_trace

    out = parse_mutation_trace("it's giving mid rizz")
    assert "REGISTER_SHIFT" in out["operators"]
    assert "SUBSTITUTE" in out["operators"]
    assert "COMPOSE" in out["operators"]
    assert "PHONETIC_WARP" not in out["operators"]
    assert out["brier"] is None
    assert out["forecast_eligible"] is False


def test_game_encode_leet():
    from hyperlex.mutation import parse_mutation_trace

    out = parse_mutation_trace("r1zz")
    assert "GAME_ENCODE" in out["operators"]
    assert out["recovered_lemma"] == "rizz"
    assert out["brier"] is None
    assert out["forecast_eligible"] is False
    assert "L4" in out["layers_touched"]


def test_game_encode_fortnite_frame():
    from hyperlex.mutation import parse_mutation_trace

    out = parse_mutation_trace("rizz in fortnite")
    assert "GAME_ENCODE" in out["operators"]
    assert "SUBSTITUTE" in out["operators"]
    assert out["brier"] is None


def test_game_frame_without_slang_does_not_fire():
    from hyperlex.mutation import parse_mutation_trace

    out = parse_mutation_trace("build a house in fortnite")
    assert "GAME_ENCODE" not in out["operators"]


def test_code_switch_particle():
    from hyperlex.mutation import parse_mutation_trace

    out = parse_mutation_trace("el rizz")
    assert "CODE_SWITCH" in out["operators"]
    assert "SUBSTITUTE" in out["operators"]
    assert out["brier"] is None
    assert "L6" in out["layers_touched"]


def test_code_switch_mixed_script():
    from hyperlex.mutation import parse_mutation_trace

    out = parse_mutation_trace("rizz 리즈")
    assert "CODE_SWITCH" in out["operators"]
    assert "SUBSTITUTE" in out["operators"]
    assert out["forecast_eligible"] is False


def test_ordinary_prose_empty():
    from hyperlex.mutation import parse_mutation_trace

    out = parse_mutation_trace("the committee adjourned after lunch")
    assert out["operators"] == []
    assert out["brier"] is None


def test_human_card_states_null_brier():
    from hyperlex.mutation import format_human_card, parse_mutation_trace

    pkt = parse_mutation_trace("it's giving mid rizz")
    card = format_human_card(pkt)
    assert "Brier: null" in card
    assert "Forecast eligible: no" in card
    assert "not a tool-fire threshold" in card
    assert "REGISTER_SHIFT" in card
    assert "SHADOW" in card


def test_human_card_redacts_restricted():
    from hyperlex.mutation import format_human_card, parse_mutation_trace

    pkt = parse_mutation_trace("it's giving mid rizz", restricted_intent_suspected=True)
    card = format_human_card(pkt)
    assert "it's giving mid rizz" not in card
    assert "redacted" in card.lower()
    assert "Brier: null" in card


def test_watch_jsonl_append_and_read(tmp_path):
    from hyperlex.mutation import append_watch, parse_mutation_trace, read_watch_log, watch_summary

    pkt = parse_mutation_trace("rzz")
    log = tmp_path / "mutation_watch.jsonl"
    rec = append_watch(pkt, path=log)
    assert rec is not None
    assert rec["brier"] is None
    assert rec["forecast_eligible"] is False
    assert rec["auto_fire"] is False
    rows = read_watch_log(log)
    assert len(rows) == 1
    assert rows[0]["auto_fire"] is False
    summary = watch_summary(log, limit=5)
    assert summary["auto_fire"] is False
    assert summary["brier"] is None
    assert summary["n"] == 1


def test_watch_jsonl_fail_open(tmp_path):
    from hyperlex.mutation import append_watch, parse_mutation_trace

    pkt = parse_mutation_trace("rzz")
    blocked = tmp_path / "not_a_dir"
    blocked.write_text("nope", encoding="utf-8")
    rec = append_watch(pkt, path=blocked / "nested" / "watch.jsonl")
    assert rec is None


def test_watch_score_not_used_as_fire_threshold():
    import hyperlex.mutation.watch as w
    import hyperlex.cli as cli

    assert "execute_production" not in inspect.getsource(w)
    assert "auto_fire" in inspect.getsource(w)
    src = inspect.getsource(cli.cmd_mutation_trace) + inspect.getsource(cli.cmd_mutation_watch)
    assert "watch_score" not in src or "threshold" not in src
    assert "list_runes" not in inspect.getsource(cli.cmd_mutation_watch)


def test_detector_still_has_no_predict_call():
    from hyperlex.mutation import detect as d
    from hyperlex.mutation import grammar as g

    assert "predict_mutations" not in inspect.getsource(g)
    assert "predict_mutations" not in inspect.getsource(d)
    assert "wrap" not in (inspect.getsource(d).split())


def test_cli_human_and_watch(tmp_path):
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "HYPERLEX_OFFLINE": "1"}
    log = tmp_path / "watch.jsonl"
    r = subprocess.run(
        [
            sys.executable, "-m", "hyperlex", "mutation", "trace", "r1zz",
            "--human", "--watch-jsonl", str(log),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert "GAME_ENCODE" in r.stdout
    assert "Brier: null" in r.stdout
    assert "Forecast eligible: no" in r.stdout
    w = subprocess.run(
        [sys.executable, "-m", "hyperlex", "mutation", "watch", "--path", str(log)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert w.returncode == 0, w.stderr + w.stdout
    data = json.loads(w.stdout)
    assert data.get("brier") is None
    assert data.get("auto_fire") is False
    assert data.get("n") == 1


def test_hlx_mutation_human_passthrough():
    env = {**os.environ, "HYPERLEX_OFFLINE": "1"}
    env.pop("PYTHONPATH", None)
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "hlx-mutation"), "trace", "rzz", "--human"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert "PHONETIC_WARP" in r.stdout
    assert "Brier: null" in r.stdout
