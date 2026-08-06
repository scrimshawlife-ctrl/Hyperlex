"""Local SQLite vector DB tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_hash_embed_deterministic():
    from hyperlex.vectordb.embed import cosine, embed_hash

    a = embed_hash("locked in")
    b = embed_hash("locked in")
    c = embed_hash("quiet quitting bandwidth")
    assert a == b
    assert abs(sum(x * x for x in a) - 1.0) < 1e-5
    assert cosine(a, b) > 0.99
    assert cosine(a, c) < cosine(a, b)


def test_seed_and_search(tmp_path: Path):
    from hyperlex.vectordb import VectorStore, seed_from_backfill, seed_from_registry, vector_search

    db = tmp_path / "v.db"
    with VectorStore(db) as store:
        r1 = seed_from_registry(store)
        r2 = seed_from_backfill(
            store,
            year=2026,
            through="2026-08",
            backfill_root=ROOT / "data" / "backfill",
        )
        assert r1["n_upserted"] >= 20
        assert r2["n_upserted"] >= 20
        assert store.count("term") >= 20

    out = vector_search("rizz sigma aura", path=db, kind="term", top_k=5, min_score=0.05)
    assert out["ok"] is True
    assert out["brier"] is None
    assert out["n_hits"] >= 1
    # top hit should look brainrot-ish or related slang
    families = {h.get("family_id") for h in out["hits"]}
    assert families  # non-empty


def test_analyze_attaches_vector_neighbors(tmp_path: Path, monkeypatch):
    from hyperlex import detect_memetic_patterns
    from hyperlex.vectordb import VectorStore, seed_from_registry

    db = tmp_path / "neighbors.db"
    with VectorStore(db) as store:
        seed_from_registry(store)
    monkeypatch.setenv("HYPERLEX_VECTOR_DB", str(db))
    monkeypatch.setenv("HYPERLEX_VECTOR", "1")
    monkeypatch.setenv("HYPERLEX_OFFLINE", "1")
    r = detect_memetic_patterns(query="rizz locked in sigma", ingest_source="mock")
    assert r["provenance"]["brier"] is None
    vn = (r.get("analysis") or {}).get("vector_neighbors")
    assert isinstance(vn, dict)
    assert vn.get("brier") is None
    assert vn.get("hits")


def test_cli_vector_seed_search(tmp_path: Path):
    db = tmp_path / "cli.db"
    env = {**dict(__import__("os").environ), "PYTHONPATH": str(ROOT / "src"), "HYPERLEX_OFFLINE": "1"}
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "hyperlex.py"),
            "vector-seed",
            "--db",
            str(db),
            "--no-receipts",
            "--root",
            str(ROOT / "data" / "backfill"),
            "--through",
            "2026-03",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(r.stdout)
    assert data["ok"] is True
    assert data["stats"]["n_total"] >= 10

    r2 = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "hyperlex.py"),
            "vector-search",
            "locked in rizz",
            "--db",
            str(db),
            "--kind",
            "term",
            "--top-k",
            "3",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r2.returncode == 0, r2.stderr + r2.stdout
    hits = json.loads(r2.stdout)
    assert hits["n_hits"] >= 1


def test_chroma_path_kwarg_does_not_typeerror(tmp_path: Path):
    """seed_all always passes path=; chroma factory must accept it."""
    pytest = __import__("pytest")
    chromadb = pytest.importorskip("chromadb")

    from hyperlex.vectordb.chroma import ChromaVectorStore, get_vector_store
    from hyperlex.vectordb.seed import seed_from_registry
    from hyperlex.vectordb.embed import embed_text

    chroma_dir = tmp_path / "chroma-local"
    store = get_vector_store(backend="chroma", path=chroma_dir)
    assert isinstance(store, ChromaVectorStore)
    r = seed_from_registry(store)
    assert r["n_upserted"] >= 20
    assert store.count() >= 20
    vec, _info = embed_text("rizz sigma")
    hits = store.search(vec, kind="term", top_k=5, min_score=0.05)
    assert hits
    stats = store.stats()
    assert stats["backend"] == "chroma"
    assert stats["n_total"] >= 20
    assert "chroma" in str(stats.get("path", ""))
    # reopen from same path
    store2 = ChromaVectorStore(path=chroma_dir)
    assert store2.count() >= 20


def test_chroma_ephemeral_client():
    pytest = __import__("pytest")
    chromadb = pytest.importorskip("chromadb")

    from hyperlex.vectordb.chroma import ChromaVectorStore
    from hyperlex.vectordb.embed import embed_text

    client = chromadb.EphemeralClient()
    store = ChromaVectorStore(client=client, collection_name="hyperlex-test")
    vec, info = embed_text("locked in")
    store.upsert(
        id="term:locked",
        kind="term",
        text="locked in",
        embedding=vec,
        model=info.model_id,
        family_id="brainrot-aura",
        meta={"source": "test", "nullable": None},
    )
    hits = store.search(vec, kind="term", top_k=1, min_score=0.5)
    assert len(hits) == 1
    assert hits[0]["text"] == "locked in"
    assert hits[0]["score"] >= 0.99


def test_cli_chroma_local_seed_search(tmp_path: Path):
    """CLI --db alone must drive local chroma (no HYPERLEX_CHROMA_PATH required)."""
    pytest = __import__("pytest")
    pytest.importorskip("chromadb")

    chroma_dir = tmp_path / "cli-chroma"
    # Strip chroma env so --db is the only path signal
    env = {
        k: v
        for k, v in dict(__import__("os").environ).items()
        if not k.startswith("HYPERLEX_CHROMA") and k != "HYPERLEX_VECTOR_BACKEND"
    }
    env.update({"PYTHONPATH": str(ROOT / "src"), "HYPERLEX_OFFLINE": "1"})
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "hyperlex.py"),
            "vector-seed",
            "--backend",
            "chroma",
            "--db",
            str(chroma_dir),
            "--no-receipts",
            "--root",
            str(ROOT / "data" / "backfill"),
            "--through",
            "2026-03",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(r.stdout)
    assert data["ok"] is True
    assert data.get("backend") == "chroma"
    assert data["stats"]["n_total"] >= 10

    r2 = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "hyperlex.py"),
            "vector-search",
            "locked in rizz",
            "--backend",
            "chroma",
            "--db",
            str(chroma_dir),
            "--kind",
            "term",
            "--top-k",
            "3",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r2.returncode == 0, r2.stderr + r2.stdout
    hits = json.loads(r2.stdout)
    assert hits["n_hits"] >= 1
    assert hits.get("backend") == "chroma"
    assert str(chroma_dir) in str(hits.get("db_path") or "")
