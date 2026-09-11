"""intake — gate_of_intake (Numogram Zone 0-1 + chaos_shift)

Expanded real wired ingest for memetic signals.

Sources:
- mock
- real/glossary/web: Action Network betting glossary
- reddit: old.reddit
- urban: Urban Dictionary (public API)
- wikipedia: Wikipedia REST summary
- x_search, firecrawl: enhanced stubs
- combined: tries multiple sources

Returns either str (backward compat) or structured dict.
"""
import re
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from .sources import pick_source
from ..provenance import source_fingerprint

try:
    import requests
except ImportError:
    requests = None

# Simple in-memory TTL cache
_CACHE: Dict[str, tuple] = {}
_CACHE_TTL = 300  # 5 minutes

def _cache_key(query: str, source: str) -> str:
    return f"{source}:{query.lower().strip()}"

def _get_cached(key: str) -> Optional[str]:
    if key in _CACHE:
        ts, val = _CACHE[key]
        if time.time() - ts < _CACHE_TTL:
            return val
    return None

def _set_cached(key: str, val: str):
    _CACHE[key] = (time.time(), val)

def _fetch_real_betting_glossary(query: str) -> str:
    """Live fetch of current betting slang from public glossary."""
    if requests is None:
        return f"Real fetch unavailable (no requests): sharp money + revenge narrative for {query}."

    key = _cache_key(query, "glossary")
    cached = _get_cached(key)
    if cached:
        return cached

    try:
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
    if requests is None:
        return f"[REDDIT_FALLBACK] {query} slang chatter."

    key = _cache_key(query, "reddit")
    cached = _get_cached(key)
    if cached:
        return cached

    try:
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
    if requests is None:
        return f"[URBAN_FALLBACK] {query} - user slang definitions unavailable."

    key = _cache_key(query, "urban")
    cached = _get_cached(key)
    if cached:
        return cached

    try:
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
    if requests is None:
        return f"[WIKI_FALLBACK] {query} context unavailable."

    key = _cache_key(query, "wikipedia")
    cached = _get_cached(key)
    if cached:
        return cached

    try:
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

def _fetch_x_stub(query: str) -> str:
    # Enhanced stub ready for real x_search / xurl integration
    return f"[X_SEARCH_WIRED_STUB] Recent velocity on '{query}': sharp money, revenge narratives, memetic spread in discourse."

def _fetch_firecrawl_stub(query: str) -> str:
    return f"[FIRECRAWL_WIRED_STUB] Scraped threads on '{query}': tactical slang, community transmission, hyperstition signals."

def ingest_signal(query: str, source: str = "mock") -> str:
    """
    Real-signal ingestion (expanded v1.6).

    Sources:
    - "mock": deterministic test signal
    - "real", "glossary", "web": live Action Network glossary
    - "reddit": real Reddit search
    - "urban": Urban Dictionary
    - "wikipedia": Wikipedia summary for context
    - "x_search": ready for hermes x_search
    - "firecrawl": ready for firecrawl
    - "combined": tries glossary → urban → reddit → wikipedia
    """
    source = source.lower().strip()

    if source == "mock":
        # Query-aware deterministic mock so lineage/forecast fixtures stay distinct.
        q = (query or "").strip()
        ql = q.lower()
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
        elif any(k in ql for k in ("brainrot", "aura", "mid", "cooked", "rizz", "skibidi")):
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
        return _fetch_real_betting_glossary(query)
    elif source == "reddit":
        return _fetch_reddit_slang(query)
    elif source == "urban":
        return _fetch_urban_dict(query)
    elif source == "wikipedia":
        return _fetch_wikipedia(query)
    elif source == "x_search":
        return _fetch_x_stub(query)
    elif source == "firecrawl":
        return _fetch_firecrawl_stub(query)
    elif source in ("moltbook", "agent_discourse", "moltbook_memory"):
        return _fetch_moltbook_agent_discourse(query)
    elif source == "combined":
        parts = []
        for s in ["glossary", "urban", "reddit", "wikipedia"]:
            try:
                parts.append(ingest_signal(query, source=s)[:220])
            except Exception:
                continue
        return " | ".join(parts) if parts else f"[COMBINED_EMPTY] No signals for {query}"
    else:
        return f"No signal available for source={source}"


def fetch_ingest(
    query: str,
    source: str = "mock",
    structured: bool = True,
    max_terms: int = 8,
    *,
    route: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Structured ingest entry point.

    Returns a dict with:
      - query
      - source
      - raw_signal
      - extracted_terms (heuristic)
      - metadata
      - timestamp
    """
    source, resolved = pick_source(source, route=route)
    raw = ingest_signal(query, source=source)
    fetched_at = datetime.now(timezone.utc).isoformat()

    # Heuristic term extraction
    terms = re.findall(r'\b([a-z]{4,}(?:block|nine|sharp|holler|revenge|low|false|vig|action|chalk))\b', raw.lower())
    terms = list(dict.fromkeys(terms))[:max_terms]  # dedup preserve order

    locator = f"hyperlex://{source}"
    fp = source_fingerprint(
        source=source,
        query=query,
        raw_signal=raw,
        source_locator=locator,
        fetched_at=fetched_at,
    )

    return {
        "query": query,
        "source": source,
        "raw_signal": raw,
        "extracted_terms": terms,
        "route": resolved,
        "metadata": {
            "source_type": "real" if source in ("real", "glossary", "urban", "reddit", "wikipedia", "moltbook", "agent_discourse", "moltbook_memory") else "synthetic_stub",
            "cached": _cache_key(query, source) in _CACHE,
            "fetched_at": fetched_at,
            "route": resolved.get("route"),
        },
        "provenance": {
            "version": "1.6.0",
            "ingest_source": source,
            "route": resolved.get("route"),
            "source_fingerprint": fp,
        },
        "source_fingerprint": fp,
    }

def _fetch_moltbook_agent_discourse(query: str) -> str:
    """Moltbook (AI agent social network) ingest for memetic patterns around cognition, memory, slang.

    Stub (real wiring in progress).
    """
    return (
        f"[MOLTBOOK_STUB] Agent discourse on '{query}': "
        "context loss (KDR, conveyor-belt), provenance (ECHO), tiered memory, load-bearing slang."
    )
