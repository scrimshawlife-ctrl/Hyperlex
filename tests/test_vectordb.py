"""Local SQLite vector DB tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_hash_embed_deterministic():
    from hyperlex.vectordb.embed import cosine, embed_hash

    a = embed_hash("sigma rizz locked in")
    b = embed_hash("sigma rizz locked in")
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
