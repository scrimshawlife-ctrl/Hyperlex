"""Hybrid lexical + vector lineage re-rank tests."""

from __future__ import annotations

from pathlib import Path

from hyperlex.analysis import match_lineage
from hyperlex.vectordb import VectorStore, seed_from_registry


def test_hybrid_adds_breakdown_when_vector_db_present(tmp_path: Path, monkeypatch):
    db = tmp_path / "hy.db"
    with VectorStore(db) as store:
        seed_from_registry(store)
    monkeypatch.setenv("HYPERLEX_VECTOR_DB", str(db))
    monkeypatch.setenv("HYPERLEX_VECTOR", "1")
    monkeypatch.setenv("HYPERLEX_OFFLINE", "1")

    hit = match_lineage("sharp steam revenge")
    assert hit is not None
    assert hit["family_id"] == "betting-sharp"
    assert hit["provenance"] == "INFERRED"
    sb = hit.get("score_breakdown") or {}
    assert "lexical_confidence" in sb
    assert "hybrid_confidence" in sb
    assert sb.get("hybrid_applied") is True
    assert "hybrid" in hit
    assert hit["hybrid"]["brier"] is None


def test_hybrid_can_be_disabled(tmp_path: Path, monkeypatch):
    db = tmp_path / "hy2.db"
    with VectorStore(db) as store:
        seed_from_registry(store)
    monkeypatch.setenv("HYPERLEX_VECTOR_DB", str(db))
    monkeypatch.setenv("HYPERLEX_VECTOR", "0")

    hit = match_lineage("sharp steam revenge", use_vector=False)
    assert hit is not None
    assert hit["family_id"] == "betting-sharp"
    assert "hybrid" not in hit


def test_domain_phylogeny_packs():
    from hyperlex.simulation import build_domain_phylogeny, list_domain_packs

    packs = list_domain_packs()
    ids = {p["domain_id"] for p in packs}
    assert "finance" in ids
    assert "ai-native" in ids
    tree = build_domain_phylogeny("finance")
    assert tree["ok"] is True
    assert tree["brier"] is None
    assert "betting-sharp" in tree["families"]
