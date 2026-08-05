"""Lexicon-aware seed term splitting.

Backfill packs and LINEAGE_REGISTRY store **atomic** terms (including multi-word
phrases like ``locked in``). Free-text seeds such as ``sigma rizz locked in``
must be expanded into separate considerations — never simulated or lineage-
scored as a single blended phrase when they are independent lexicon items.

Strategy: greedy left-to-right longest match against the known lexicon, then
word-level residual tokens.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Set

# Multi-word / high-value phrases not only in registry leaves but used as atoms
DEFAULT_EXTRA_PHRASES: Sequence[str] = (
    "locked in",
    "crash out",
    "touch grass",
    "skill issue",
    "agentic slop",
    "quiet quitting",
    "act your wage",
    "diamond hands",
    "sharp money",
    "false nine",
    "low block",
    "vibe coding",
    "context window",
    "return to office",
    "let him cook",
    "no cap",
    "main character",
)


def collect_lexicon(
    *,
    registry: Optional[Sequence[Dict[str, Any]]] = None,
    extra: Optional[Sequence[str]] = None,
    include_backfill: bool = True,
    year: int = 2026,
    through: Optional[str] = "2026-08",
) -> List[str]:
    """Unique lexicon strings, longest first (for greedy match)."""
    seen: Set[str] = set()
    terms: List[str] = []

    def _add(t: str) -> None:
        s = (t or "").strip().lower()
        if not s or s in seen:
            return
        seen.add(s)
        terms.append(s)

    for phrase in extra or DEFAULT_EXTRA_PHRASES:
        _add(phrase)

    if registry is not None:
        reg = list(registry)
    else:
        # Lazy import avoids circular import with analysis package init
        from . import LINEAGE_REGISTRY as _LINEAGE_REGISTRY

        reg = list(_LINEAGE_REGISTRY)
    for entry in reg:
        for t in entry.get("terms") or []:
            _add(str(t))

    if include_backfill:
        try:
            from .backfill import inventory_backfill

            inv = inventory_backfill(year, through=through)
            for row in inv.get("terms") or []:
                _add(str(row.get("term") or ""))
        except Exception:
            pass

    # longest first so "locked in" wins over "locked"
    terms.sort(key=lambda s: (-len(s), s))
    return terms


def split_seed_terms(
    text: str,
    *,
    lexicon: Optional[Sequence[str]] = None,
    include_backfill: bool = True,
    keep_unknown_words: bool = False,
    min_unknown_len: int = 3,
) -> Dict[str, Any]:
    """
    Split free text into independent lexicon terms.

    Examples
    --------
    ``"sigma rizz locked in"`` → ``["sigma", "rizz", "locked in"]``
    ``"locked in crash out"`` → ``["locked in", "crash out"]``
    ``"rizz"`` → ``["rizz"]``

    Unknown residual words are omitted by default (unless ``keep_unknown_words``)
    so prose noise does not become fake slang atoms.
    """
    original = (text or "").strip()
    if not original:
        return {
            "schema": "hyperlex.seed_terms.v1",
            "original": "",
            "terms": [],
            "matched": [],
            "residual": [],
            "multi_term": False,
            "method": "lexicon_longest_match",
        }

    lex = list(lexicon) if lexicon is not None else collect_lexicon(include_backfill=include_backfill)
    # normalize spaces
    corpus = re.sub(r"\s+", " ", original.lower()).strip()
    matched: List[str] = []
    residual: List[str] = []
    i = 0
    n = len(corpus)

    while i < n:
        if corpus[i] == " ":
            i += 1
            continue
        hit: Optional[str] = None
        for phrase in lex:
            end = i + len(phrase)
            if end > n:
                continue
            if corpus[i:end] != phrase:
                continue
            # boundary: start of string or after space; end of string or before space
            left_ok = i == 0 or corpus[i - 1] == " "
            right_ok = end == n or corpus[end] == " "
            if left_ok and right_ok:
                hit = phrase
                break
        if hit:
            matched.append(hit)
            i += len(hit)
            continue
        # consume one residual token
        m = re.match(r"[^\s]+", corpus[i:])
        if not m:
            break
        tok = m.group(0)
        residual.append(tok)
        i += len(tok)

    terms = list(matched)
    if keep_unknown_words:
        for tok in residual:
            clean = re.sub(r"[^a-z0-9'-]", "", tok)
            if len(clean) >= min_unknown_len and clean not in terms:
                terms.append(clean)

    # de-dupe preserve order
    seen: Set[str] = set()
    uniq: List[str] = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            uniq.append(t)

    return {
        "schema": "hyperlex.seed_terms.v1",
        "original": original,
        "terms": uniq,
        "matched": matched,
        "residual": residual,
        "multi_term": len(uniq) > 1,
        "n_terms": len(uniq),
        "method": "lexicon_longest_match",
        "note": (
            "Atomic lexicon terms only. Multi-word phrases (e.g. locked in) stay "
            "together; independent items are not blended into one seed."
        ),
    }


def per_term_lineage(
    terms: Sequence[str],
    *,
    match_fn=None,
    min_confidence: float = 0.42,
) -> List[Dict[str, Any]]:
    """Run lineage match on each term independently (no density stacking)."""
    if match_fn is None:
        from . import match_lineage as match_fn  # type: ignore

    rows: List[Dict[str, Any]] = []
    for term in terms:
        t = str(term).strip()
        if not t:
            continue
        lin = match_fn(t, terms=[t], min_confidence=min_confidence)
        # also try without threshold floor for visibility
        lin_soft = match_fn(t, terms=[t], min_confidence=0.0) if lin is None else lin
        rows.append({
            "term": t,
            "lineage": lin,
            "lineage_soft": lin_soft if lin is None else None,
            "family_id": (lin or {}).get("family_id"),
            "confidence": (lin or {}).get("confidence"),
            "considered_separately": True,
        })
    return rows


def primary_term_from_split(split: Dict[str, Any], per_term: Sequence[Dict[str, Any]]) -> Optional[str]:
    """Pick primary term: highest lineage confidence, else first term."""
    best_term = None
    best_c = -1.0
    for row in per_term:
        c = row.get("confidence")
        if c is not None and float(c) > best_c:
            best_c = float(c)
            best_term = row.get("term")
    if best_term:
        return str(best_term)
    terms = split.get("terms") or []
    return str(terms[0]) if terms else None
