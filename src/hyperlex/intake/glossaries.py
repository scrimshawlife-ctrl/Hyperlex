"""Multi-source glossary adapters for slang expansion.

Each adapter returns a plain-text signal string. Failures degrade gracefully.
"""

from __future__ import annotations

import os
import re
from typing import Callable, Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    requests = None

# (source_key, human_name, url_template_or_url, kind)
GLOSSARY_REGISTRY: List[Dict[str, str]] = [
    {
        "id": "action_network",
        "name": "Action Network Betting Glossary",
        "url": "https://www.actionnetwork.com/education/sports-betting-terms-glossary",
        "domain": "betting",
    },
    {
        "id": "wikipedia_slang",
        "name": "Wikipedia Internet slang",
        "url": "https://en.wikipedia.org/wiki/List_of_Internet_slang",
        "domain": "internet",
    },
    {
        "id": "urban_query",
        "name": "Urban Dictionary (query)",
        "url": "https://api.urbandictionary.com/v0/define",
        "domain": "user",
    },
]


def _offline() -> bool:
    flag = str(os.environ.get("HYPERLEX_OFFLINE", "")).strip().lower()
    return flag in {"1", "true", "yes", "on"}


def list_glossaries() -> List[Dict[str, str]]:
    return list(GLOSSARY_REGISTRY)


def fetch_action_network(query: str) -> Tuple[str, str]:
    """Returns (signal, source_locator)."""
    locator = GLOSSARY_REGISTRY[0]["url"]
    if _offline() or requests is None:
        return (
            f"[OFFLINE_GLOSSARY:action_network] sharp money, steam, juice, clv for '{query}'",
            locator,
        )
    r = requests.get(
        locator,
        headers={"User-Agent": "Hyperlex/1.7 (glossary; real-ingest)"},
        timeout=8,
    )
    r.raise_for_status()
    html = r.text
    matches = re.findall(
        r"([A-Z][a-zA-Z\s]{2,30}?)\s*[—–-]\s*([A-Za-z][^<]{15,70})",
        html,
    )
    terms: List[str] = []
    for term, _def in matches:
        t = term.strip()
        if len(t) > 3 and t not in terms:
            terms.append(t)
        if len(terms) >= 12:
            break
    if not terms:
        terms = ["Action", "Chalk", "Dog", "Vig", "Juice", "Sharp", "Steam", "Revenge"]
    signal = (
        f"Action Network glossary for '{query}': {', '.join(terms[:8])}. "
        f"Active: chalk, sharp money, vig, steam."
    )
    return signal, locator


def fetch_wikipedia_slang(query: str) -> Tuple[str, str]:
    locator = "https://en.wikipedia.org/api/rest_v1/page/summary/List_of_Internet_slang"
    if _offline() or requests is None:
        return (
            f"[OFFLINE_GLOSSARY:wikipedia_slang] internet slang context for '{query}'",
            locator,
        )
    r = requests.get(
        locator,
        headers={"User-Agent": "Hyperlex/1.7 (glossary-wiki)"},
        timeout=8,
    )
    if r.status_code != 200:
        return f"[WIKI_SLANG_MISS] status={r.status_code} for '{query}'", locator
    data = r.json()
    extract = (data.get("extract") or "")[:400]
    return f"Wikipedia Internet slang (context for '{query}'): {extract}", locator


def fetch_urban_as_glossary(query: str) -> Tuple[str, str]:
    locator = f"https://api.urbandictionary.com/v0/define?term={query}"
    if _offline() or requests is None:
        return f"[OFFLINE_GLOSSARY:urban] '{query}'", locator
    r = requests.get(
        "https://api.urbandictionary.com/v0/define",
        params={"term": query},
        timeout=6,
    )
    if r.status_code != 200:
        return f"[URBAN_GLOSSARY_MISS] '{query}'", locator
    defs = (r.json() or {}).get("list") or []
    if not defs:
        return f"[URBAN_GLOSSARY_EMPTY] '{query}'", locator
    top = defs[0]
    word = top.get("word", query)
    definition = (top.get("definition") or "")[:200].replace("\n", " ")
    return f"Urban glossary '{word}': {definition}", locator


_FETCHERS: Dict[str, Callable[[str], Tuple[str, str]]] = {
    "action_network": fetch_action_network,
    "wikipedia_slang": fetch_wikipedia_slang,
    "urban_query": fetch_urban_as_glossary,
}


def fetch_glossary(
    query: str,
    *,
    glossary_id: str = "action_network",
) -> Tuple[str, str, str]:
    """
    Fetch one glossary.

    Returns (signal, source_locator, glossary_id).
    """
    fetcher = _FETCHERS.get(glossary_id)
    if fetcher is None:
        return f"[UNKNOWN_GLOSSARY] {glossary_id}", f"hyperlex://glossary/{glossary_id}", glossary_id
    try:
        signal, locator = fetcher(query)
        return signal, locator, glossary_id
    except Exception as exc:
        return (
            f"[GLOSSARY_FALLBACK:{glossary_id}] {query} ({type(exc).__name__})",
            f"hyperlex://glossary/{glossary_id}",
            glossary_id,
        )


def fetch_glossary_expanded(query: str) -> Tuple[str, List[Dict[str, str]]]:
    """
    Combine multiple glossaries into one signal.

    Returns (combined_signal, component_meta).
    """
    parts: List[str] = []
    meta: List[Dict[str, str]] = []
    for g in GLOSSARY_REGISTRY:
        signal, locator, gid = fetch_glossary(query, glossary_id=g["id"])
        parts.append(signal[:280])
        meta.append({"glossary_id": gid, "locator": locator, "domain": g.get("domain", "")})
    combined = " || ".join(parts) if parts else f"[GLOSSARY_EMPTY] {query}"
    return combined, meta
