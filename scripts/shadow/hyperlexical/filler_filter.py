"""Publishable-filler filter for the unbind vocab. No torch. D8.

Filler strings ship inside the weights config (``filler_vocab``), so every
filler must be a plain word. Rejects social handles, links, markup, and
dictionary/wiki scraps. Curly quotes are folded to ASCII before checking.

``HYPERLEX_FILLER_FILTER``: ``strict`` (default) drops unbind rows with any
non-publishable filler and fails closed if one reaches the vocab; ``off``
reproduces pre-filter recipes (morph75–78).
"""

from __future__ import annotations

import os
import re

FILLER_FILTER_ENV = "HYPERLEX_FILLER_FILTER"
MODES = ("strict", "off")
_FOLD = str.maketrans({"\u2019": "'", "\u2018": "'", "\u2010": "-", "\u2011": "-", "\u2013": "-"})
_WORD = re.compile(r"^[a-z0-9]+(?:['\-][a-z0-9]+)*$")
MAX_LEN = 24
CONTRACTIONS = frozenset({"'em", "'bout", "'cause", "'til", "'sup", "'round", "'nuff"})


def filter_mode(raw: str | None = None) -> str:
    value = (os.environ.get(FILLER_FILTER_ENV, "") if raw is None else raw).strip() or "strict"
    if value not in MODES:
        raise ValueError(f"{FILLER_FILTER_ENV} must be one of {MODES}")
    return value


def fold(token: str) -> str:
    return str(token).translate(_FOLD).strip().lower()


def reject_reason(token: str) -> str | None:
    """None if publishable, else a short reason code."""
    raw = str(token)
    t = fold(raw)
    if not t:
        return "empty"
    if "@" in raw:
        return "handle_or_email"
    if "://" in raw or raw.lower().startswith("www.") or re.search(r"\.(com|org|net|io|co)\b", raw.lower()):
        return "link"
    if any(c in raw for c in "[]()<>{}|!\"“”`*_#=\\"):
        return "markup_or_quote"
    if len(t) > MAX_LEN:
        return "too_long"
    if any(ord(c) > 127 for c in t):
        return "non_ascii"
    if t in CONTRACTIONS or (t.endswith("in'") and _WORD.match(t[:-1])):
        return None
    if not _WORD.match(t):
        return "not_word"
    return None


def is_publishable(token: str) -> bool:
    return reject_reason(token) is None


def filter_unbind_rows(rows: list[dict], mode: str | None = None) -> tuple[list[dict], dict]:
    mode = filter_mode(mode)
    if mode == "off":
        return list(rows), {"filler_filter": "off", "n_filler_rows_dropped": 0}
    kept, dropped, reasons = [], 0, {}
    for row in rows:
        bad = [reject_reason(f) for f in (row.get("fillers") or [])]
        bad = [b for b in bad if b]
        if bad:
            dropped += 1
            for b in bad:
                reasons[b] = reasons.get(b, 0) + 1
        else:
            kept.append(row)
    return kept, {"filler_filter": "strict", "n_filler_rows_dropped": dropped, "filler_reject_reasons": reasons}


def assert_publishable_vocab(filler_vocab: list[str], unk: str = "<unk>") -> None:
    bad = [f for f in filler_vocab if f != unk and not is_publishable(f)]
    if bad:
        raise ValueError(f"non-publishable fillers reached the vocab ({len(bad)}); first: {bad[0]!r}")
