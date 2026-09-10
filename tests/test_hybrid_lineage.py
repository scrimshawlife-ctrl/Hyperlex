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


def test_wave4_attested_registry_leaves() -> None:
    """On-disk vernacular/Hyperlex attested morphs land in the 8-family registry."""
    from hyperlex.analysis import LINEAGE_REGISTRY, match_lineage

    by_fam = {e["family_id"]: {t.lower() for t in e["terms"]} for e in LINEAGE_REGISTRY}
    samples = {
        "ai-native": ["glaze", "vibe coded", "rlhf"],
        "betting-sharp": ["against the spread", "the vig"],
        "brainrot-aura": ["bruh", "sheesh", "minus aura", "sigma grindset"],
        "crypto-degen": ["jeet", "probably nothing", "frens"],
        "gaming-meta": ["one-tricking", "hardstuck bronze"],
        "kinship-address": ["yo fam", "lil unc"],
        "political-status": ["doomer", "cope harder"],
        "workplace-corp": ["put a pin in it", "rto mandate"],
    }
    assert set(by_fam) == set(samples)
    for fam, terms in samples.items():
        for t in terms:
            assert t in by_fam[fam], (fam, t)
            hit = match_lineage(t, use_vector=False)
            assert hit is not None and hit["family_id"] == fam, (t, hit)
    # still exactly 8 families — no 9th
    assert len(LINEAGE_REGISTRY) == 8


def test_wave5_attested_registry_leaves() -> None:
    """Wave5 / attested-w2 on-disk morphs (vernacular/Hyperlex/kaikki/harvest) land in 8 families."""
    from hyperlex.analysis import LINEAGE_REGISTRY, match_lineage

    by_fam = {e["family_id"]: {t.lower() for t in e["terms"]} for e in LINEAGE_REGISTRY}
    samples = {
        "ai-native": ["sycophant", "model collapse", "alignment tax"],
        "betting-sharp": ["chalk eaters", "sucker bet", "point-shave"],
        "brainrot-aura": ["-1000 aura", "rizzless", "delulu is the solulu", "it's giving mid"],
        "crypto-degen": ["aped in", "shitcoin", "crypto winter"],
        "gaming-meta": ["git gud", "smurf account", "tryhards"],
        "kinship-address": ["bruv", "dawg"],
        "political-status": ["cope seethe"],
        "workplace-corp": ["circling back", "quiet hiring", "bare minimum monday"],
    }
    assert set(by_fam) == set(samples)
    for fam, terms in samples.items():
        for t in terms:
            assert t in by_fam[fam], (fam, t)
            hit = match_lineage(t, use_vector=False)
            assert hit is not None and hit["family_id"] == fam, (t, hit)
    assert len(LINEAGE_REGISTRY) == 8
    n_terms = sum(len(e["terms"]) for e in LINEAGE_REGISTRY)
    assert n_terms >= 379
