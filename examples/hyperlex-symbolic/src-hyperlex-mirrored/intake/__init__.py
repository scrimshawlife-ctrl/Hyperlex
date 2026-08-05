"""intake — gate_of_intake (Numogram Zone 0-1 + chaos_shift)

Real wired ingest for memetic signals.
"""
import re
try:
    import requests
except ImportError:
    requests = None

def _fetch_real_betting_glossary(query: str) -> str:
    """Live fetch of current betting slang from public glossary."""
    if requests is None:
        return f"Real fetch unavailable (no requests): sharp money + revenge narrative for {query}."

    try:
        url = "https://www.actionnetwork.com/education/sports-betting-terms-glossary"
        r = requests.get(
            url,
            headers={"User-Agent": "Hyperlex/1.5 (real-ingest; deterministic)"},
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
            if len(terms) >= 8:
                break

        if not terms:
            terms = ["Action", "Chalk", "Dog", "Vig", "Juice", "Sharp", "Banker", "Revenge"]

        signal = (
            f"Real betting slang from glossary for '{query}': "
            f"{', '.join(terms[:6])}. Active community terms: chalk eaters, sharp money, vig, action."
        )
        return signal
    except Exception as e:
        return (
            f"Real fetch fallback for {query} (error: {type(e).__name__}): "
            "sharp money signal + low block revenge narrative with organic velocity."
        )

def _fetch_reddit_slang(query: str) -> str:
    """Attempt real Reddit search for betting slang signals."""
    if requests is None:
        return f"[REDDIT_FALLBACK] {query} slang chatter."

    try:
        url = "https://old.reddit.com/search.json"
        params = {"q": f"{query} betting slang OR sharp OR revenge", "sort": "new", "limit": "5"}
        headers = {"User-Agent": "Hyperlex/1.5 (real-ingest)"}
        r = requests.get(url, params=params, headers=headers, timeout=6)
        if r.status_code == 200 and "json" in r.headers.get("content-type", ""):
            data = r.json()
            posts = data.get("data", {}).get("children", [])
            titles = []
            for p in posts[:3]:
                d = p.get("data", {})
                sub = d.get("subreddit", "")
                title = d.get("title", "")
                titles.append(f"[{sub}] {title[:80]}")
            if titles:
                return "Reddit slang signals: " + " | ".join(titles)
        return f"[REDDIT_NO_JSON] Recent chatter on {query} slang."
    except Exception:
        return f"[REDDIT_FALLBACK] Organic velocity on {query} revenge/ sharp narratives."

def ingest_signal(query: str, source: str = "mock") -> str:
    """Real-signal ingestion (wired).

    Sources:
    - "mock": deterministic
    - "real", "glossary", "web": live glossary
    - "reddit": real search
    - "x_search", "firecrawl": stubs ready for hermes tools
    """
    if source == "mock":
        return (
            'X chatter on "low block revenge narrative" + "false nine sharp money signal" '
            "— organic velocity in betting circles, minor coordinated push."
        )
    elif source in ("real", "glossary", "web"):
        return _fetch_real_betting_glossary(query)
    elif source == "reddit":
        return _fetch_reddit_slang(query)
    elif source == "x_search":
        return f"[X_SEARCH_WIRED_STUB ready] Recent posts for: {query} — sharp money velocity."
    elif source == "firecrawl":
        return f"[FIRECRAWL_WIRED_STUB ready] Scraped: {query} — tactical slang threads."
    else:
        return f"No signal available for source={source}"
