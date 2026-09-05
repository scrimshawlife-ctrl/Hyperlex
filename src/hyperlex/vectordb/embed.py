"""Embedding backends for Hyperlex vector DB.

Default: deterministic feature-hash embedding (offline, no network).
Optional: OpenAI-compatible /v1/embeddings when configured.
"""

from __future__ import annotations

import hashlib
import math
import os
import struct
from dataclasses import dataclass
from typing import Iterable, List, Sequence


DEFAULT_DIM = 256
HASH_MODEL_ID = f"hyperlex.hash_ngram_v1.d{DEFAULT_DIM}"


@dataclass(frozen=True)
class EmbeddingModelInfo:
    model_id: str
    dim: int
    provider: str  # hash | openai_compatible
    provenance: str  # OBSERVED for remote; INFERRED for hash


def default_model_id() -> str:
    prov = str(os.environ.get("HYPERLEX_EMBED_PROVIDER", "hash")).strip().lower()
    if prov in {"openai", "openai_compatible", "oai"}:
        model = os.environ.get("HYPERLEX_EMBED_MODEL", "text-embedding-3-small")
        return f"openai_compatible:{model}"
    return HASH_MODEL_ID


def _tokenize(token: str) -> int:
    h = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(h, "little", signed=False)


def _l2_normalize(vec: List[float]) -> List[float]:
    s = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / s for x in vec]


def embed_hash(text: str, *, dim: int = DEFAULT_DIM) -> List[float]:
    """
    Offline bag-of-features embedding: word unigrams + char 3-grams hashed into dim.

    Deterministic, stable across processes, good enough for small slang/receipt corpora.
    """
    t = (text or "").lower().strip()
    if not t:
        return [0.0] * dim
    vec = [0.0] * dim
    # words
    for w in t.split():
        i = _tokenize(w) % dim
        vec[i] += 1.0
        # bigram-ish: prefix/suffix
        if len(w) >= 2:
            vec[_tokenize(w[:2] + "#") % dim] += 0.5
            vec[_tokenize("#" + w[-2:]) % dim] += 0.5
    # char 3-grams
    compact = "".join(ch if ch.isalnum() else " " for ch in t)
    compact = " ".join(compact.split())
    padded = f"^{compact}$"
    for i in range(len(padded) - 2):
        gram = padded[i : i + 3]
        j = _tokenize("c3:" + gram) % dim
        vec[j] += 0.35
    return _l2_normalize(vec)


def pack_embedding(vec: Sequence[float]) -> bytes:
    return struct.pack(f"<{len(vec)}f", *[float(x) for x in vec])


def unpack_embedding(blob: bytes, dim: int | None = None) -> List[float]:
    n = (dim if dim is not None else len(blob) // 4)
    return list(struct.unpack(f"<{n}f", blob[: n * 4]))


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return float(sum(x * y for x, y in zip(a, b)))


def embed_openai_compatible(texts: Sequence[str]) -> tuple[List[List[float]], EmbeddingModelInfo]:
    """Call OpenAI-compatible /v1/embeddings via stdlib urllib."""
    import json
    import urllib.error
    import urllib.request

    from hyperlex.guards import require_http_url

    base = os.environ.get("HYPERLEX_EMBED_BASE_URL") or os.environ.get("HYPERLEX_LLM_BASE_URL") or ""
    key = os.environ.get("HYPERLEX_EMBED_API_KEY") or os.environ.get("HYPERLEX_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
    model = os.environ.get("HYPERLEX_EMBED_MODEL", "text-embedding-3-small")
    if not base:
        raise RuntimeError("HYPERLEX_EMBED_BASE_URL or HYPERLEX_LLM_BASE_URL required for openai_compatible embeddings")
    base = require_http_url(base, name="HYPERLEX_EMBED_BASE_URL")
    if str(os.environ.get("HYPERLEX_OFFLINE", "")).strip() in {"1", "true", "yes", "on"}:
        raise RuntimeError("offline: remote embeddings disabled (HYPERLEX_OFFLINE=1)")

    url = base.rstrip("/") + "/embeddings"
    if not url.endswith("/v1/embeddings") and "/v1/" not in url:
        # allow base like https://api.openai.com/v1
        if base.rstrip("/").endswith("/v1"):
            url = base.rstrip("/") + "/embeddings"
        else:
            url = base.rstrip("/") + "/v1/embeddings"

    body = json.dumps({"model": model, "input": list(texts)}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {key}"} if key else {}),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"embed request failed: {exc}") from exc

    data = payload.get("data") or []
    data = sorted(data, key=lambda r: int(r.get("index", 0)))
    vecs = [_l2_normalize([float(x) for x in (row.get("embedding") or [])]) for row in data]
    if len(vecs) != len(texts):
        raise RuntimeError(f"embed count mismatch: got {len(vecs)} want {len(texts)}")
    dim = len(vecs[0]) if vecs else 0
    info = EmbeddingModelInfo(
        model_id=f"openai_compatible:{model}",
        dim=dim,
        provider="openai_compatible",
        provenance="OBSERVED",
    )
    return vecs, info


def embed_text(text: str) -> tuple[List[float], EmbeddingModelInfo]:
    """Embed one string with the configured provider (default hash)."""
    vecs, info = embed_batch([text])
    return vecs[0], info


def embed_batch(texts: Sequence[str]) -> tuple[List[List[float]], EmbeddingModelInfo]:
    prov = str(os.environ.get("HYPERLEX_EMBED_PROVIDER", "hash")).strip().lower()
    if prov in {"openai", "openai_compatible", "oai"}:
        return embed_openai_compatible(texts)
    # hash default
    vecs = [embed_hash(t) for t in texts]
    info = EmbeddingModelInfo(
        model_id=HASH_MODEL_ID,
        dim=DEFAULT_DIM,
        provider="hash",
        provenance="INFERRED",
    )
    return vecs, info
