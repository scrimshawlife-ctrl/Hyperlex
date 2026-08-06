"""Mutation prediction — next surface forms (SPECULATIVE, brier null)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_predict_mutations_returns_schema_and_null_brier():
    from hyperlex.analysis.mutation import predict_mutations

    out = predict_mutations(
        "rizz",
        family_id="brainrot-aura",
        family_terms=["rizz", "aura", "sigma", "brainrot"],
        family_operator="irony_inversion",
    )
    assert out["schema"] == "hyperlex.mutation_prediction.v1"
    assert out["seed_term"] == "rizz"
    assert out["family_id"] == "brainrot-aura"
    assert out["brier"] is None
    assert out["provenance"] == "SPECULATIVE"
    assert out["n_candidates"] >= 1
    assert len(out["candidates"]) == out["n_candidates"]
    for c in out["candidates"]:
        assert c["form"]
        assert c["form"].lower() != "rizz"
        assert c["operator"]
        assert c["provenance"] == "SPECULATIVE"
        assert c["source"] in {"deterministic", "llm"}
        assert 0.0 < float(c["confidence"]) <= 1.0
        assert c.get("rationale")


def test_predict_mutations_empty_seed():
    from hyperlex.analysis.mutation import predict_mutations

    out = predict_mutations("  ")
    assert out["n_candidates"] == 0
    assert out["brier"] is None
    assert out.get("candidates") == []


def test_predict_mutations_respects_max_candidates(monkeypatch):
    from hyperlex.analysis.mutation import predict_mutations

    monkeypatch.setenv("HYPERLEX_MUTATION_MAX", "3")
    out = predict_mutations(
        "sigma",
        family_id="brainrot-aura",
        family_terms=["sigma", "rizz", "aura", "mid", "cooked"],
    )
    assert out["n_candidates"] <= 3
    assert len(out["candidates"]) <= 3


def test_predict_mutations_dedupes_casefold():
    from hyperlex.analysis.mutation import predict_mutations

    out = predict_mutations(
        "Aura",
        family_id="brainrot-aura",
        family_terms=["aura", "rizz"],
        llm_candidates=[
            {
                "form": "AURAED",
                "operator": "derivational",
                "confidence": 0.9,
                "source": "llm",
                "rationale": "dup test",
            }
        ],
    )
    forms = [c["form"].lower() for c in out["candidates"]]
    assert len(forms) == len(set(forms))


def test_predict_mutations_merges_llm_candidates_without_dup():
    from hyperlex.analysis.mutation import predict_mutations

    out = predict_mutations(
        "rizz",
        family_id="brainrot-aura",
        family_terms=["rizz", "aura"],
        llm_candidates=[
            {
                "form": "rizzler",
                "operator": "derivational",
                "confidence": 0.55,
                "rationale": "agentive -er form",
            }
        ],
    )
    forms = {c["form"].lower() for c in out["candidates"]}
    assert "rizzler" in forms
    assert out["brier"] is None
    sources = {c["source"] for c in out["candidates"] if c["form"].lower() == "rizzler"}
    assert "llm" in sources


def test_enrich_mutation_candidates_skipped_when_llm_off(monkeypatch):
    monkeypatch.delenv("HYPERLEX_LLM", raising=False)
    from hyperlex.llm.governed import enrich_mutation_candidates

    meta = enrich_mutation_candidates("rizz", family_id="brainrot-aura", existing=[])
    assert meta["applied"] is False
    assert meta.get("candidates") == []


def test_analyze_includes_mutation_prediction_offline(monkeypatch):
    monkeypatch.setenv("HYPERLEX_OFFLINE", "1")
    monkeypatch.setenv("HYPERLEX_VECTOR", "0")
    monkeypatch.delenv("HYPERLEX_LLM", raising=False)
    from hyperlex import detect_memetic_patterns

    r = detect_memetic_patterns(
        "rizz",
        ingest_source="mock",
        use_structured_ingest=False,
        validate=False,
    )
    assert r["provenance"]["brier"] is None
    mp = (r.get("analysis") or {}).get("mutation_prediction")
    assert isinstance(mp, dict)
    assert mp["schema"] == "hyperlex.mutation_prediction.v1"
    assert mp["brier"] is None
    assert mp["provenance"] == "SPECULATIVE"
    assert mp["seed_term"]
    assert mp["n_candidates"] >= 1


def test_cli_mutation_predict_offline():
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "HYPERLEX_OFFLINE": "1"}
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "hyperlex.py"), "mutation-predict", "rizz"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(r.stdout)
    assert data.get("ok") is True
    assert data.get("brier") is None
    assert data.get("schema") == "hyperlex.mutation_prediction.v1"
    assert data.get("n_candidates", 0) >= 1
