"""Governed LLM augmentation (opt-in stub).

Activation requires **both**:
  - env HYPERLEX_LLM=1 (or true/yes/on)
  - a callable provider registered via set_provider(), **or**
    HYPERLEX_LLM_PROVIDER=echo (deterministic dry-run)

No network client ships by default. Operators inject their own provider.

Authority:
  - Outputs are always labeled SPECULATIVE / INFERRED as declared
  - Never sets Brier scores
  - Never auto-settles forecasts
  - Never mutates receipts or score logs
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Callable, Dict, List, Optional

ProviderFn = Callable[[str, Dict[str, Any]], str]

_PROVIDER: Optional[ProviderFn] = None


class GovernedLLMError(RuntimeError):
    """Raised when LLM is requested but not properly configured."""


def llm_enabled() -> bool:
    flag = str(os.environ.get("HYPERLEX_LLM", "")).strip().lower()
    return flag in {"1", "true", "yes", "on"}


def set_provider(fn: Optional[ProviderFn]) -> None:
    """Register or clear the operator-supplied provider."""
    global _PROVIDER
    _PROVIDER = fn


def get_provider() -> Optional[ProviderFn]:
    if _PROVIDER is not None:
        return _PROVIDER
    kind = str(os.environ.get("HYPERLEX_LLM_PROVIDER", "")).strip().lower()
    if kind == "echo":
        return _echo_provider
    return None


def _echo_provider(prompt: str, context: Dict[str, Any]) -> str:
    """Deterministic dry-run provider for tests — extracts quoted tokens only."""
    text = str(context.get("text") or "")
    # Suggest multi-word titles as speculative candidates (no invention beyond text)
    words = re.findall(r"\b[a-z][a-z0-9_-]{3,}\b", text.lower())
    # unique preserve order, skip stop-ish
    stop = {"that", "this", "with", "from", "have", "were", "been", "they", "them", "mock", "channel"}
    seen = []
    for w in words:
        if w in stop or w in seen:
            continue
        seen.append(w)
        if len(seen) >= 5:
            break
    payload = {
        "candidates": [
            {"term": w, "formation": "llm_echo", "confidence": 0.4, "provenance": "SPECULATIVE"}
            for w in seen
        ],
        "provider": "echo",
        "note": "deterministic stub; not a live model",
    }
    return json.dumps(payload)


def enrich_neologisms(
    text: str,
    existing: Optional[List[Dict[str, Any]]] = None,
    *,
    require_enabled: bool = True,
) -> Dict[str, Any]:
    """
    Optionally enrich neologism list via governed provider.

    Returns:
      {
        "enabled": bool,
        "applied": bool,
        "candidates": [...],
        "merged": [...],  # existing + new terms (dedup by term)
        "status": "skipped"|"applied"|"error"|"not_configured",
        ...
      }
    """
    existing = list(existing or [])
    if require_enabled and not llm_enabled():
        return {
            "enabled": False,
            "applied": False,
            "candidates": [],
            "merged": existing,
            "status": "skipped",
            "reason": "HYPERLEX_LLM not enabled",
        }

    provider = get_provider()
    if provider is None:
        return {
            "enabled": llm_enabled(),
            "applied": False,
            "candidates": [],
            "merged": existing,
            "status": "not_configured",
            "reason": "no provider (set_provider or HYPERLEX_LLM_PROVIDER=echo)",
        }

    prompt = (
        "Extract slang/neologism candidates from the text. "
        "Return JSON {candidates:[{term, formation, confidence}]}. "
        "Do not invent Brier scores or settlements."
    )
    context = {"text": text, "existing": existing}
    try:
        raw = provider(prompt, context)
    except Exception as exc:
        return {
            "enabled": True,
            "applied": False,
            "candidates": [],
            "merged": existing,
            "status": "error",
            "reason": f"{type(exc).__name__}: {exc}",
        }

    candidates = _parse_candidates(raw)
    # force safe labels
    for c in candidates:
        c["provenance"] = c.get("provenance") or "SPECULATIVE"
        c["source"] = "governed_llm"
        try:
            c["confidence"] = float(c.get("confidence", 0.4))
        except (TypeError, ValueError):
            c["confidence"] = 0.4
        c["confidence"] = max(0.0, min(0.85, c["confidence"]))  # cap — never claim certainty

    seen = {str(x.get("term", "")).lower() for x in existing}
    merged = list(existing)
    for c in candidates:
        t = str(c.get("term", "")).lower().strip()
        if not t or t in seen:
            continue
        seen.add(t)
        merged.append(c)

    return {
        "enabled": True,
        "applied": True,
        "candidates": candidates,
        "merged": merged,
        "status": "applied",
        "n_new": len(merged) - len(existing),
    }


def _parse_candidates(raw: str) -> List[Dict[str, Any]]:
    raw = (raw or "").strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # try fenced block
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return []
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return []
    if isinstance(data, dict):
        cands = data.get("candidates") or data.get("terms") or []
    elif isinstance(data, list):
        cands = data
    else:
        return []
    out: List[Dict[str, Any]] = []
    for item in cands:
        if isinstance(item, str):
            out.append({"term": item, "formation": "llm", "confidence": 0.4})
        elif isinstance(item, dict) and item.get("term"):
            out.append(dict(item))
    return out
