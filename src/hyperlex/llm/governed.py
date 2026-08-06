"""Governed LLM augmentation (opt-in).

Activation requires **both**:
  - env HYPERLEX_LLM=1 (or true/yes/on)
  - a provider via set_provider(), **or** HYPERLEX_LLM_PROVIDER=
      echo              — deterministic dry-run (no network)
      openai_compatible — OpenAI-style /chat/completions (stdlib urllib)

No hard dependency on the `openai` package.

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
    if kind in {"openai", "openai_compatible", "openai-compatible", "http"}:
        return _openai_compatible_provider
    return None


def _openai_compatible_provider(prompt: str, context: Dict[str, Any]) -> str:
    """
    OpenAI-compatible chat completions via stdlib urllib.

    Env:
      HYPERLEX_LLM_API_KEY   (required)
      HYPERLEX_LLM_BASE_URL  (default https://api.openai.com/v1)
      HYPERLEX_LLM_MODEL     (default gpt-4o-mini)
      HYPERLEX_LLM_TIMEOUT   (seconds, default 30)

    Offline: HYPERLEX_OFFLINE=1 forces failure (no silent synthetic success).
    """
    offline = str(os.environ.get("HYPERLEX_OFFLINE", "")).strip().lower() in {
        "1", "true", "yes", "on",
    }
    if offline:
        raise GovernedLLMError("offline: refusing openai_compatible network call")

    api_key = (
        os.environ.get("HYPERLEX_LLM_API_KEY", "").strip()
        or os.environ.get("OPENAI_API_KEY", "").strip()
    )
    if not api_key:
        raise GovernedLLMError("HYPERLEX_LLM_API_KEY (or OPENAI_API_KEY) required")

    base = os.environ.get("HYPERLEX_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("HYPERLEX_LLM_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    try:
        timeout = float(os.environ.get("HYPERLEX_LLM_TIMEOUT", "30") or "30")
    except ValueError:
        timeout = 30.0

    text = str(context.get("text") or "")[:4000]
    existing = context.get("existing") or []
    system = (
        "You extract slang/neologism candidates from cultural text. "
        "Respond with ONLY valid JSON: "
        '{"candidates":[{"term":str,"formation":str,"confidence":float}]}. '
        "confidence in [0,0.85]. Do not invent Brier scores or settlements. "
        "Prefer terms present or strongly implied in the text."
    )
    user = json.dumps({
        "task": "neologism_candidates",
        "text": text,
        "existing_terms": [e.get("term") for e in existing if isinstance(e, dict)],
        "instruction": prompt,
    }, ensure_ascii=False)

    body = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
    }
    payload = json.dumps(body).encode("utf-8")
    url = f"{base}/chat/completions"

    # Prefer requests if present; else urllib
    try:
        import urllib.error
        import urllib.request

        req = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Hyperlex-GovernedLLM/0.2",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        data = json.loads(raw)
        content = (
            ((data.get("choices") or [{}])[0].get("message") or {}).get("content")
            or ""
        )
        if not content:
            raise GovernedLLMError("empty model content")
        return content
    except Exception as exc:
        if isinstance(exc, GovernedLLMError):
            raise
        raise GovernedLLMError(f"openai_compatible failed: {type(exc).__name__}: {exc}") from exc


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


_MUTATION_OPS = frozenset({
    "platform_compression",
    "derivational",
    "irony_inversion",
    "compound_phrase",
    "sense_extension",
    "cross_family_borrowing",
    "extra-grammatical",
})


def enrich_mutation_candidates(
    seed_term: str,
    *,
    family_id: Optional[str] = None,
    family_operator: Optional[str] = None,
    existing: Optional[List[Dict[str, Any]]] = None,
    require_enabled: bool = True,
) -> Dict[str, Any]:
    """Optional LLM next-form candidates. Fail-open; never invents Brier."""
    existing = list(existing or [])
    if require_enabled and not llm_enabled():
        return {
            "enabled": False,
            "applied": False,
            "candidates": [],
            "status": "skipped",
            "reason": "HYPERLEX_LLM not enabled",
        }
    provider = get_provider()
    if provider is None:
        return {
            "enabled": llm_enabled(),
            "applied": False,
            "candidates": [],
            "status": "not_configured",
            "reason": "no provider (set_provider or HYPERLEX_LLM_PROVIDER=echo)",
        }

    prompt = (
        "Propose next surface-form mutations for a slang seed. "
        "Return JSON {candidates:[{form, operator, confidence, rationale}]}. "
        "Operators must be one of: platform_compression, derivational, irony_inversion, "
        "compound_phrase, sense_extension, cross_family_borrowing, extra-grammatical. "
        "Do not invent Brier scores. Max 5 candidates. Speculative only."
    )
    context = {
        "seed_term": seed_term,
        "family_id": family_id,
        "family_operator": family_operator,
        "existing": existing[:8],
    }
    try:
        raw = provider(prompt, context)
    except Exception as exc:
        return {
            "enabled": True,
            "applied": False,
            "candidates": [],
            "status": "error",
            "reason": f"{type(exc).__name__}: {exc}",
        }

    parsed = _parse_mutation_candidates(raw)
    if not parsed:
        return {
            "enabled": True,
            "applied": False,
            "candidates": [],
            "status": "empty",
            "reason": "no parseable candidates",
        }
    return {
        "enabled": True,
        "applied": True,
        "candidates": parsed[:5],
        "status": "applied",
        "n_new": len(parsed[:5]),
    }


def _parse_mutation_candidates(raw: str) -> List[Dict[str, Any]]:
    raw = (raw or "").strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return []
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return []
    if isinstance(data, dict):
        cands = data.get("candidates") or []
    elif isinstance(data, list):
        cands = data
    else:
        return []
    out: List[Dict[str, Any]] = []
    for item in cands:
        if isinstance(item, str):
            out.append({
                "form": item,
                "operator": "extra-grammatical",
                "confidence": 0.35,
                "rationale": "governed LLM mutation candidate",
            })
            continue
        if not isinstance(item, dict):
            continue
        form = str(item.get("form") or item.get("term") or "").strip()
        if not form:
            continue
        op = str(item.get("operator") or item.get("formation") or "extra-grammatical")
        if op not in _MUTATION_OPS:
            op = "extra-grammatical"
        try:
            conf = float(item.get("confidence", 0.35))
        except (TypeError, ValueError):
            conf = 0.35
        conf = max(0.05, min(0.85, conf))
        out.append({
            "form": form,
            "operator": op,
            "confidence": conf,
            "rationale": str(item.get("rationale") or "governed LLM mutation candidate"),
        })
    return out
