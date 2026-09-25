"""jevgate-1 unit tests. Synthetic strings only. The Jev client is mocked."""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

import pytest

from hyperlex.analysis.jevgate import (
    FROZEN_PROMPT_SHA256,
    MODEL_ID,
    TAU,
    JevCallError,
    JevHttpClient,
    assert_prompt_sha,
    classify_term,
    eight_families,
    prompt_sha256,
)

ROOT = Path(__file__).resolve().parents[1]
TERM = "zzsynthetic-jevgate-term"


class FakeJev:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def evaluate(self, state):
        self.calls.append(dict(state))
        if not self.responses:
            raise JevCallError("provider_error", "no scripted response")
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _miss(_term, **_kwargs):
    return None


def _probs(none_p, peaks):
    order = eight_families()
    probs = {name: 0.0 for name in order}
    probs.update(peaks)
    probs["none"] = none_p
    return probs


def _pass(none_p, peaks, *, model=MODEL_ID, choice="workplace-corp"):
    return {
        "model_id": model,
        "answers": {
            "in_scope": {"type": "boolean", "probability": 0.11},
            "any_slang": {"type": "boolean", "probability": 0.22},
            "family": {
                "type": "choice",
                "choice": choice,
                "probabilities": _probs(none_p, peaks),
            },
        },
    }


def _three(none_p, peaks, **kwargs):
    return [_pass(none_p, peaks, **kwargs) for _ in range(3)]


def test_prompt_sha_assert(monkeypatch):
    assert prompt_sha256() == FROZEN_PROMPT_SHA256
    assert_prompt_sha()
    monkeypatch.setitem(
        __import__("hyperlex.analysis.jevgate", fromlist=["QUESTIONS"]).QUESTIONS,
        "in_scope",
        {"type": "boolean", "instructions": "drift"},
    )
    # setitem may not replace the object identity used by prompt_sha256 if QUESTIONS
    # is the same dict. Mutating in_scope changes JSON.stringify.
    with pytest.raises(AssertionError):
        assert_prompt_sha()
    client = FakeJev([])
    out = classify_term(TERM, jevgate=True, client=client, match_fn=_miss)
    assert out["family"] == "none"
    assert out["jev_error"]["flag"] is True
    assert out["jev_error"]["reason"] == "prompt_sha_mismatch"
    assert client.calls == []


def test_rule_first_precedence():
    seen = {}

    def match(term, use_vector=True):
        seen["term"] = term
        seen["use_vector"] = use_vector
        return {
            "family_id": "gaming-meta",
            "matched_terms": ["zz"],
            "confidence": 0.77,
            "provenance": "INFERRED",
        }

    client = FakeJev([AssertionError("jev must not run")])
    out = classify_term(TERM, jevgate=True, client=client, match_fn=match)
    assert seen == {"term": TERM, "use_vector": False}
    assert out["family"] == "gaming-meta"
    assert out["source"] == "match_lineage"
    assert out["jev_best_guess"] is None
    assert out["jev_p_none"] is None
    assert out["jev_error"] is None
    assert client.calls == []
    assert out["brier"] is None


def test_flag_off_keeps_cascade():
    client = FakeJev([AssertionError("jev must not run")])
    out = classify_term(TERM, jevgate=False, client=client, match_fn=_miss)
    assert out["family"] == "none"
    assert out["source"] == "cascade"
    assert out["jevgate_enabled"] is False
    assert client.calls == []


@pytest.mark.parametrize(
    "none_p, expect_family",
    [
        (0.30332999999999993, "ai-native"),  # just below 0.30333
        (0.30333, "none"),  # at tau, strict
        (0.30333000000000004, "none"),  # just above
    ],
)
def test_tau_boundary(none_p, expect_family):
    assert (0.30332999999999993 < TAU) and not (TAU < TAU) and not (0.30333000000000004 < TAU)
    client = FakeJev(_three(none_p, {"ai-native": 0.62}, choice="workplace-corp"))
    out = classify_term(TERM, jevgate=True, client=client, match_fn=_miss)
    assert len(client.calls) == 3
    assert all(call == {"text": TERM} for call in client.calls)
    assert out["family"] == expect_family
    assert out["source"] == "jevgate"
    assert out["jev_p_none"] == none_p
    assert out["jev_p_none"] < TAU or expect_family == "none"
    # choice is workplace-corp on every pass and must not decide
    assert out["jev_log"]["choice"] == ["workplace-corp", "workplace-corp", "workplace-corp"]
    assert out["jev_best_guess"] == "ai-native"
    assert out["jev_family_means"]["ai-native"] == 0.62
    assert set(out["jev_family_means"]) == set(eight_families())
    assert "none" not in out["jev_family_means"]
    assert out["jev_error"] is None


def test_tie_break_follows_layout_order():
    order = eight_families()
    shadow = str(ROOT / "scripts" / "shadow")
    if shadow not in sys.path:
        sys.path.insert(0, shadow)
    from hyperlexical.layout import FAMILIES

    assert order == tuple(name for name in FAMILIES if name != "none")
    later = order[5]
    earlier = order[2]
    assert order.index(earlier) < order.index(later)
    client = FakeJev(_three(0.1, {earlier: 0.4, later: 0.4}))
    out = classify_term(TERM, jevgate=True, client=client, match_fn=_miss)
    assert out["family"] == earlier
    assert out["jev_best_guess"] == earlier
    assert out["jev_family_means"][earlier] == out["jev_family_means"][later]


def test_best_guess_when_output_is_none():
    client = FakeJev(_three(0.9, {"crypto-degen": 0.05, "kinship-address": 0.01}))
    out = classify_term(TERM, jevgate=True, client=client, match_fn=_miss)
    assert out["family"] == "none"
    assert out["jev_best_guess"] == "crypto-degen"
    assert out["jev_p_none"] == 0.9
    assert out["jev_error"] is None


def test_best_guess_null_when_all_family_means_are_zero():
    client = FakeJev(_three(1.0, {}))
    out = classify_term(TERM, jevgate=True, client=client, match_fn=_miss)
    assert out["jev_p_none"] == 1.0
    assert out["jev_p_none"] >= TAU
    assert all(value == 0.0 for value in out["jev_family_means"].values())
    assert out["family"] == "none"
    assert out["jev_best_guess"] is None


def test_best_guess_null_when_all_family_means_are_equal():
    order = eight_families()
    client = FakeJev(_three(0.52, {name: 0.06 for name in order}))
    out = classify_term(TERM, jevgate=True, client=client, match_fn=_miss)
    assert out["jev_p_none"] == 0.52
    assert out["jev_p_none"] >= TAU
    assert len(set(out["jev_family_means"].values())) == 1
    assert out["jev_family_means"][order[0]] == 0.06
    assert out["family"] == "none"
    assert out["jev_best_guess"] is None


def test_retry_then_fail_closed(monkeypatch):
    secret = "synthetic-jev-key-not-real"
    monkeypatch.setenv("JEV_API_KEY", secret)
    client = FakeJev(
        [
            JevCallError("provider_error", f"boom {secret} Bearer {secret}"),
            JevCallError("timeout", f"still {secret}"),
        ]
    )
    out = classify_term(TERM, jevgate=True, client=client, match_fn=_miss)
    assert len(client.calls) == 2
    assert out["family"] == "none"
    assert out["source"] == "jevgate"
    assert out["jev_error"]["flag"] is True
    assert out["jev_error"]["reason"] == "timeout"
    blob = json.dumps(out)
    assert secret not in blob
    assert "Bearer [R]" in blob or "[R]" in blob


def test_retry_then_success_uses_the_pass():
    order = eight_families()
    winner = order[0]
    client = FakeJev(
        [
            JevCallError("provider_error", "transient"),
            *_three(0.05, {winner: 0.7}),
        ]
    )
    out = classify_term(TERM, jevgate=True, client=client, match_fn=_miss)
    assert len(client.calls) == 4
    assert out["family"] == winner
    assert out["jev_error"] is None


def test_model_id_mismatch(monkeypatch):
    monkeypatch.delenv("JEV_API_KEY", raising=False)
    client = FakeJev(
        [
            _pass(0.01, {"ai-native": 0.9}, model="jev-other"),
            _pass(0.01, {"ai-native": 0.9}, model="jev-1.13.0-alias"),
        ]
    )
    out = classify_term(TERM, jevgate=True, client=client, match_fn=_miss)
    assert len(client.calls) == 2
    assert out["family"] == "none"
    assert out["jev_error"]["flag"] is True
    assert out["jev_error"]["reason"] == "model_mismatch"
    assert out["jev_best_guess"] is None


def test_http_client_wire_format(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", "synthetic-jev-key-not-real")
    monkeypatch.delenv("HYPERLEX_OFFLINE", raising=False)
    monkeypatch.delenv("JEV_BASE_URL", raising=False)
    captured = {}
    order = eight_families()
    probs = {name: 0.0 for name in order}
    probs["ai-native"] = 0.7
    probs["none"] = 0.2

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def read(self):
            body = {
                "model": MODEL_ID,
                "answers": {
                    "in_scope": {"type": "noul", "noul": 0.15},
                    "any_slang": {"type": "noul", "noul": 0.25},
                    "family": {
                        "type": "choice",
                        "choice": "none",
                        "probabilities": probs,
                    },
                },
            }
            return json.dumps(body).encode("utf-8")

    def fake_urlopen(req, timeout=0):
        captured["url"] = req.full_url
        captured["timeout"] = timeout
        captured["body"] = json.loads(req.data.decode("utf-8"))
        captured["auth"] = req.get_header("Authorization")
        return _Resp()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    out = JevHttpClient().evaluate({"text": TERM})
    assert captured["url"] == "https://api.typesafe.ai/v1/systemone"
    assert captured["timeout"] == 55.0
    assert captured["body"]["model"] == MODEL_ID
    assert captured["body"]["state"] == {"text": TERM}
    assert captured["body"]["questions"]["in_scope"]["type"] == "noul"
    assert captured["body"]["questions"]["any_slang"]["type"] == "noul"
    assert captured["body"]["questions"]["family"]["type"] == "choice"
    assert captured["auth"] == "Bearer synthetic-jev-key-not-real"
    assert out["model_id"] == MODEL_ID
    assert out["answers"]["in_scope"]["type"] == "boolean"
    assert out["answers"]["in_scope"]["probability"] == 0.15
    assert "synthetic-jev-key-not-real" not in json.dumps(
        {k: v for k, v in captured.items() if k != "auth"}
    )


def test_missing_key_does_not_call_network(monkeypatch):
    monkeypatch.delenv("JEV_API_KEY", raising=False)
    monkeypatch.delenv("TYPESAFE_AI_API_KEY", raising=False)
    monkeypatch.delenv("JEV_KEY_FILE", raising=False)
    monkeypatch.setenv("HYPERLEX_OFFLINE", "0")

    def boom(*_a, **_k):
        raise AssertionError("network")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    out = classify_term(TERM, jevgate=True, match_fn=_miss)
    assert out["family"] == "none"
    assert out["jev_error"]["flag"] is True
    assert out["jev_error"]["reason"] == "missing_key"


def test_cli_classify_default_is_cascade(capsys, monkeypatch):
    monkeypatch.delenv("HYPERLEX_JEVGATE", raising=False)
    from hyperlex.cli import main

    rc = main(["classify", TERM])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is True
    assert data["command"] == "classify"
    assert data["family"] == "none"
    assert data["source"] == "cascade"
    assert data["jevgate_enabled"] is False
    assert data["brier"] is None


def test_skill_cli_classify_default_is_cascade(monkeypatch):
    monkeypatch.delenv("HYPERLEX_JEVGATE", raising=False)
    env = os.environ.copy()
    env.pop("HYPERLEX_JEVGATE", None)
    env["HYPERLEX_OFFLINE"] = "1"
    env["PYTHONPATH"] = str(ROOT / "src")
    import subprocess

    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "hyperlex.py"), "classify", TERM],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["family"] == "none"
    assert data["source"] == "cascade"
    assert data["brier"] is None
