"""intake — gate_of_intake (Numogram Zone 0-1 + chaos_shift)

Expanded real wired ingest for memetic signals.

Sources:
- mock
- real/glossary/web: Action Network betting glossary
- reddit: old.reddit
- urban: Urban Dictionary (public API)
- wikipedia: Wikipedia REST summary
- x_search: placeholder adapter
- firecrawl: Crawl4AI-powered web crawl
- crawl4ai: explicit Crawl4AI-backed adapter
- combined: tries multiple sources

Returns either str (backward compat) or structured dict.
"""
import asyncio
import inspect
import re
import os
import urllib.parse
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    requests = None

try:
    from crawl4ai import AsyncWebCrawler
except Exception:  # pragma: no cover - optional dependency
    AsyncWebCrawler = None

from .cache import (
    cache_key as _cache_key,
    get_cached as _get_cached_raw,
    set_cached as _set_cached_raw,
    wait_for_rate_limit,
    is_cached,
    cache_stats,
)
from .glossaries import fetch_glossary, fetch_glossary_expanded, list_glossaries
from .x_search import fetch_x_search
from .sources import (
    SOURCE_ALIASES,
    SOURCE_CATALOG,
    ROUTE_PRESETS,
    list_sources,
    offline_mode as _offline_mode,
    pick_source,
    resolve_source,
)
from ..provenance import source_fingerprint, merge_ingest_provenance


def _get_cached(key: str, source: str = "") -> Optional[str]:
    return _get_cached_raw(key, source=source or key.split(":", 1)[0])


def _set_cached(key: str, val: str, source: str = "") -> None:
    _set_cached_raw(key, val, source=source or key.split(":", 1)[0])


def _before_network(source: str) -> None:
    """Rate-limit live network adapters (no-op when disabled via env)."""
    wait_for_rate_limit(source)

def _fetch_real_betting_glossary(query: str) -> str:
    """Live fetch of current betting slang from public glossary."""
    if _offline_mode():
        return f"[OFFLINE_REAL_FALLBACK] Real glossary unavailable for '{query}'."
    if requests is None:
        return f"Real fetch unavailable (no requests): sharp money + revenge narrative for {query}."

    key = _cache_key(query, "glossary")
    cached = _get_cached(key)
    if cached:
        return cached

    try:
        _before_network("glossary")
        url = "https://www.actionnetwork.com/education/sports-betting-terms-glossary"
        r = requests.get(
            url,
            headers={"User-Agent": "Hyperlex/1.6 (real-ingest; deterministic)"},
            timeout=8
        )
        r.raise_for_status()
        html = r.text

        matches = re.findall(
            r'([A-Z][a-zA-Z\s]{2,30}?)\s*[—–-]\s*([A-Za-z][^<]{15,70})',
            html
        )
        terms = []
        for term, _def in matches:
            t = term.strip()
            if len(t) > 3 and t not in terms:
                terms.append(t)
            if len(terms) >= 10:
                break

        if not terms:
            terms = ["Action", "Chalk", "Dog", "Vig", "Juice", "Sharp", "Banker", "Revenge", "Fade", "Steam"]

        signal = (
            f"Real betting slang from glossary for '{query}': "
            f"{', '.join(terms[:7])}. Active community terms: chalk eaters, sharp money, vig, action."
        )
        _set_cached(key, signal)
        return signal
    except Exception as e:
        fallback = f"Real fetch fallback for {query} (error: {type(e).__name__}): sharp money signal + low block revenge narrative with organic velocity."
        _set_cached(key, fallback)
        return fallback

def _fetch_reddit_slang(query: str) -> str:
    """Attempt real Reddit search for betting slang signals."""
    if _offline_mode() or requests is None:
        return f"[REDDIT_FALLBACK] {query} slang chatter."

    key = _cache_key(query, "reddit")
    cached = _get_cached(key)
    if cached:
        return cached

    try:
        _before_network("reddit")
        url = "https://old.reddit.com/search.json"
        params = {"q": f"{query} betting slang OR sharp OR revenge OR memetic", "sort": "new", "limit": "8"}
        headers = {"User-Agent": "Hyperlex/1.6 (real-ingest)"}
        r = requests.get(url, params=params, headers=headers, timeout=7)
        if r.status_code == 200 and "json" in r.headers.get("content-type", ""):
            data = r.json()
            posts = data.get("data", {}).get("children", [])
            titles = []
            for p in posts[:4]:
                d = p.get("data", {})
                sub = d.get("subreddit", "")
                title = d.get("title", "")
                titles.append(f"[{sub}] {title[:90]}")
            if titles:
                signal = "Reddit slang signals: " + " | ".join(titles)
                _set_cached(key, signal)
                return signal
        fallback = f"[REDDIT_NO_JSON] Recent chatter on {query} slang."
        _set_cached(key, fallback)
        return fallback
    except Exception:
        fallback = f"[REDDIT_FALLBACK] Organic velocity on {query} revenge/sharp narratives."
        _set_cached(key, fallback)
        return fallback

def _fetch_urban_dict(query: str) -> str:
    """Urban Dictionary public API for slang definitions."""
    if _offline_mode() or requests is None:
        return f"[URBAN_FALLBACK] {query} - user slang definitions unavailable."

    key = _cache_key(query, "urban")
    cached = _get_cached(key)
    if cached:
        return cached

    try:
        _before_network("urban")
        url = "https://api.urbandictionary.com/v0/define"
        r = requests.get(url, params={"term": query}, timeout=6)
        if r.status_code == 200:
            data = r.json()
            defs = data.get("list", [])
            if defs:
                top = defs[0]
                word = top.get("word", query)
                definition = top.get("definition", "")[:200].replace("\r", " ").replace("\n", " ")
                example = top.get("example", "")[:120].replace("\r", " ").replace("\n", " ")
                signal = f"Urban Dictionary '{word}': {definition} Example: {example}"
                _set_cached(key, signal)
                return signal
        return f"[URBAN_NO_DEF] No strong user definitions for '{query}' yet."
    except Exception:
        return f"[URBAN_FALLBACK] Community slang around {query}."

def _fetch_wikipedia(query: str) -> str:
    """Wikipedia REST API for term context (good for neologism background)."""
    if _offline_mode() or requests is None:
        return f"[WIKI_FALLBACK] {query} context unavailable."

    key = _cache_key(query, "wikipedia")
    cached = _get_cached(key)
    if cached:
        return cached

    try:
        _before_network("wikipedia")
        # Use REST summary endpoint
        safe_term = query.replace(" ", "_")
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{safe_term}"
        r = requests.get(url, headers={"User-Agent": "Hyperlex/1.6 (wikipedia-ingest)"}, timeout=6)
        if r.status_code == 200:
            data = r.json()
            title = data.get("title", query)
            extract = data.get("extract", "")[:280]
            signal = f"Wikipedia '{title}': {extract}"
            _set_cached(key, signal)
            return signal
        return f"[WIKI_NO_PAGE] No Wikipedia page for '{query}'."
    except Exception:
        return f"[WIKI_FALLBACK] Cultural/technical context for {query}."

def _coerce_crawl_payload(payload: Any) -> str:
    """Best-effort extraction from Crawl4AI response objects."""
    if payload is None:
        return ""

    if isinstance(payload, str):
        return payload

    if isinstance(payload, (bytes, bytearray)):
        try:
            return payload.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    if isinstance(payload, dict):
        for key in [
            "markdown",
            "text",
            "content",
            "raw_markdown",
            "raw_content",
            "cleaned_html",
            "html",
        ]:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value

    for key in ["markdown", "text", "content", "raw_markdown", "raw_content", "cleaned_html", "html"]:
        value = getattr(payload, key, None)
        if isinstance(value, str) and value.strip():
            return value

    if hasattr(payload, "__dict__") and isinstance(payload.__dict__, dict):
        for key in ["markdown", "text", "content", "raw_markdown", "raw_content", "cleaned_html", "html"]:
            value = payload.__dict__.get(key)
            if isinstance(value, str) and value.strip():
                return value

    # Deep fallback for nested objects
    for attr in ("llm_extraction", "data", "result", "payload"):
        value = getattr(payload, attr, None)
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, dict):
            for key in ["markdown", "text", "content", "raw_markdown", "raw_content", "cleaned_html"]:
                value2 = value.get(key)
                if isinstance(value2, str) and value2.strip():
                    return value2

    return ""


def _shorten_signal(text: str, max_len: int = 950) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len].rstrip()


def _run_crawl4ai(url: str):
    if AsyncWebCrawler is None:
        raise RuntimeError("crawl4ai dependency is not installed")

    async def _runner() -> Any:
        async with AsyncWebCrawler() as crawler:
            for method_name in ["arun", "run", "crawl"]:
                method = getattr(crawler, method_name, None)
                if not callable(method):
                    continue
                result = method(url=url)
                if inspect.isawaitable(result):
                    result = await result
                return result
            raise RuntimeError("No supported crawl method on AsyncWebCrawler")

    return asyncio.run(asyncio.wait_for(_runner(), timeout=12.0))


def _fetch_crawl4ai_query(query: str) -> str:
    """Best-effort crawl using crawl4ai over an external search page."""
    if _offline_mode():
        return f"[CRAWL4AI_OFFLINE] Crawl-based signals disabled for '{query}'."

    if AsyncWebCrawler is None:
        return (
            "[CRAWL4AI_MISSING] crawl4ai dependency not installed. "
            "Install with `pip install .[runtime]` to enable this source."
        )

    encoded = urllib.parse.quote_plus(f"{query} slang")
    # DuckDuckGo HTML endpoint is lightweight and often works without JS.
    url = f"https://duckduckgo.com/html/?q={encoded}"
    key = _cache_key(url, "crawl4ai")
    cached = _get_cached(key)
    if cached:
        return cached

    try:
        _before_network("crawl4ai")
        raw = _run_crawl4ai(url)
        body = _coerce_crawl_payload(raw)
        if not body.strip():
            return f"[CRAWL4AI_NO_RESULT] Empty crawl output for '{query}'."

        signal = (
            f"Crawl4AI web-scan for '{query}': "
            f"{_shorten_signal(body)}"
        )
        _set_cached(key, signal)
        return signal
    except Exception as exc:
        return (
            f"[CRAWL4AI_FALLBACK] crawl4ai failed for '{query}' "
            f"(error: {type(exc).__name__})."
        )


def _fetch_x(query: str) -> str:
    key = _cache_key(query, "x_search")
    cached = _get_cached(key, "x_search")
    if cached:
        return cached
    _before_network("x_search")
    signal, meta = fetch_x_search(query)
    # stash locator in cache only as text; structured meta via fetch_ingest
    _set_cached(key, signal, "x_search")
    # attach last meta for structured path via module global
    global _LAST_X_META
    _LAST_X_META = meta
    return signal


_LAST_X_META: Dict[str, Any] = {}
_LAST_GLOSSARY_META: Dict[str, Any] = {}


def _fetch_glossary_primary(query: str) -> str:
    key = _cache_key(query, "glossary")
    cached = _get_cached(key, "glossary")
    if cached:
        return cached
    _before_network("glossary")
    signal, locator, gid = fetch_glossary(query, glossary_id="action_network")
    global _LAST_GLOSSARY_META
    _LAST_GLOSSARY_META = {"glossary_id": gid, "source_locator": locator, "mode": "single"}
    _set_cached(key, signal, "glossary")
    return signal


def _fetch_glossary_expanded(query: str) -> str:
    key = _cache_key(query, "glossary_expanded")
    cached = _get_cached(key, "glossary_expanded")
    if cached:
        return cached
    _before_network("glossary")
    signal, components = fetch_glossary_expanded(query)
    global _LAST_GLOSSARY_META
    _LAST_GLOSSARY_META = {
        "mode": "expanded",
        "components": components,
        "source_locator": "hyperlex://glossary/expanded",
    }
    _set_cached(key, signal, "glossary_expanded")
    return signal


def _fetch_firecrawl_via_crawl4ai(query: str) -> str:
    # Reusing Crawl4AI for web crawl based signal extraction.
    return _fetch_crawl4ai_query(query)

def ingest_signal(query: str, source: str = "mock", *, route: Optional[str] = None) -> str:
    """
    Real-signal ingestion.

    Prefer `route=` (offline|live|default|glossary|social) over raw adapter names.
    Aliases (real→glossary, x→x_search, firecrawl→crawl4ai, live→combined) resolve
    via `resolve_source`. HYPERLEX_OFFLINE=1 forces mock for network sources.
    """
    source, _resolved = pick_source(source, route=route)

    if source == "mock":
        # Deterministic but query-aware so lineage/forecast fixtures stay distinct.
        q = (query or "").strip()
        ql = q.lower()
        # Neutral base — no imitation/spread cues unless family seed matches
        base = f'Mock channel note on "{q}". Quiet discourse sample.'
        if any(k in ql for k in ("sharp", "steam", "revenge", "betting", "square", "wiseguy")):
            base = (
                f'Mock memetic channel on "{q}": organic velocity, coordinated push. '
                "sharp steam square revenge wiseguy hammer low block."
            )
        elif any(k in ql for k in ("hodl", "degen", "rekt", "moon", "crypto")):
            base = (
                f'Mock memetic channel on "{q}": organic velocity. '
                "hodl diamond hands rekt degen moon bagholder."
            )
        elif any(k in ql for k in ("brainrot", "aura", "mid", "cooked")):
            base = (
                f'Mock memetic channel on "{q}". '
                "brainrot aura farming mid cooked let him cook."
            )
        elif any(k in ql for k in ("agentic", "slop", "hallucin", "clanker", "token")):
            base = (
                f'Mock memetic channel on "{q}". '
                "agentic slop skill issue hallucinate clanker context window."
            )
        elif any(k in ql for k in ("based", "cope", "seethe", "redpill", "blackpill", "political")):
            base = (
                f'Mock memetic channel on "{q}". '
                "based redpilled cope seethe dilate blackpilled."
            )
        elif any(k in ql for k in ("bro", "sis", "twin", "unc", "cuz", "kinship")):
            base = (
                f'Mock memetic channel on "{q}". '
                "bro sis twin unc cuz family."
            )
        elif any(k in ql for k in ("nerf", "buff", "meta", "sweaty", "noob", "gg", "gaming", "smurf")):
            base = (
                f'Mock memetic channel on "{q}". '
                "nerf buff meta sweaty noob gg ez ratio touch grass skill issue diff smurf."
            )
        elif any(k in ql for k in ("quiet quitting", "rto", "layoff", "bandwidth", "workplace", "corp", "act your wage")):
            base = (
                f'Mock memetic channel on "{q}". '
                "quiet quitting quiet firing rto return to office layoffs pip synergy "
                "circle back bandwidth low-hanging fruit act your wage."
            )
        return base
    elif source in ("real", "glossary", "web"):
        return _fetch_glossary_primary(query)
    elif source in ("glossary_expanded", "glossaries"):
        return _fetch_glossary_expanded(query)
    elif source == "reddit":
        return _fetch_reddit_slang(query)
    elif source == "urban":
        return _fetch_urban_dict(query)
    elif source == "wikipedia":
        return _fetch_wikipedia(query)
    elif source in ("x_search", "x", "twitter"):
        return _fetch_x(query)
    elif source == "firecrawl":
        return _fetch_firecrawl_via_crawl4ai(query)
    elif source == "crawl4ai":
        return _fetch_crawl4ai_query(query)
    elif source == "combined":
        parts = []
        for s in ["glossary", "urban", "reddit", "wikipedia", "x_search", "crawl4ai"]:
            try:
                parts.append(ingest_signal(query, source=s)[:220])
            except Exception:
                continue
        return " | ".join(parts) if parts else f"[COMBINED_EMPTY] No signals for {query}"
    else:
        return f"No signal available for source={source}"


_SOURCE_LOCATORS = {
    "mock": "hyperlex://mock",
    "glossary": "https://www.actionnetwork.com/education/sports-betting-terms-glossary",
    "real": "https://www.actionnetwork.com/education/sports-betting-terms-glossary",
    "web": "https://www.actionnetwork.com/education/sports-betting-terms-glossary",
    "glossary_expanded": "hyperlex://glossary/expanded",
    "glossaries": "hyperlex://glossary/expanded",
    "reddit": "https://old.reddit.com/search",
    "urban": "https://api.urbandictionary.com/v0/define",
    "wikipedia": "https://en.wikipedia.org/api/rest_v1/page/summary/",
    "x_search": "hyperlex://x_search",
    "x": "hyperlex://x_search",
    "twitter": "hyperlex://x_search",
    "firecrawl": "hyperlex://crawl4ai",
    "crawl4ai": "hyperlex://crawl4ai",
    "combined": "hyperlex://combined",
}


def fetch_ingest(
    query: str,
    source: str = "mock",
    structured: bool = True,
    max_terms: int = 8,
    *,
    route: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Structured ingest entry point with source fingerprints.

    Always routes through `resolve_source` / `pick_source` so CLI aliases and
    `--route offline|live` behave consistently.
    """
    source, resolved = pick_source(source, route=route)
    key = _cache_key(query, source)
    was_cached = is_cached(key)
    # Call adapters with canonical id; skip re-resolve by using internal path
    # (ingest_signal re-resolves, which is fine when source is already canonical)
    raw = ingest_signal(query, source=source)
    fetched_at = datetime.now(timezone.utc).isoformat()

    locator = _SOURCE_LOCATORS.get(source, f"hyperlex://{source}")
    adapter_meta: Dict[str, Any] = {}
    if source == "x_search" and _LAST_X_META:
        adapter_meta = dict(_LAST_X_META)
        locator = adapter_meta.get("source_locator") or locator
    if source in ("glossary", "glossary_expanded") and _LAST_GLOSSARY_META:
        adapter_meta = dict(_LAST_GLOSSARY_META)
        locator = adapter_meta.get("source_locator") or locator

    fp = source_fingerprint(
        source=source,
        query=query,
        raw_signal=raw,
        source_locator=locator,
        fetched_at=fetched_at,
    )

    # Heuristic term extraction
    terms = re.findall(
        r"\b([a-z]{4,}(?:block|nine|sharp|holler|revenge|low|false|vig|action|chalk|steam|degen|aura|slop))\b",
        raw.lower(),
    )
    terms = list(dict.fromkeys(terms))[:max_terms]

    network_sources = {
        name for name, meta in SOURCE_CATALOG.items() if meta.get("network")
    }
    live = bool(adapter_meta.get("live")) if adapter_meta else (source in network_sources)

    try:
        from .. import PKG_VERSION as _pkg_v
    except Exception:
        _pkg_v = "0.0.0"
    provenance = merge_ingest_provenance(
        {
            "version": _pkg_v,
            "ingest_source": source,
            "fetched_at": fetched_at,
            "route": resolved.get("route"),
            "requested_source": resolved.get("requested"),
        },
        fp,
    )

    return {
        "query": query,
        "source": source,
        "raw_signal": raw,
        "extracted_terms": terms,
        "route": resolved,
        "metadata": {
            "source_type": "real" if source in network_sources else "synthetic_stub",
            "live": live if source == "x_search" else (source in network_sources),
            "cached": was_cached,
            "fetched_at": fetched_at,
            "source_locator": locator,
            "adapter": adapter_meta,
            "cache": cache_stats(),
            "route": resolved.get("route"),
            "requested_source": resolved.get("requested"),
            "offline_forced": resolved.get("offline_forced"),
        },
        "provenance": provenance,
        "source_fingerprint": fp,
    }
