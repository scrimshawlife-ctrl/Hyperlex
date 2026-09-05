"""v0.2 detect-only heuristics. Never generate wraps or encodings."""
from __future__ import annotations

import unicodedata
from typing import Iterable, Optional, Sequence

from .operators import (
    CODE_SWITCH_PARTICLES,
    GAME_MARKERS,
    SUBSTITUTE_TERMS,
    leet_decode,
    token_has_leet,
    vowel_drop_map,
)

_SCRIPT_PREFIXES = (
    "LATIN",
    "CYRILLIC",
    "HANGUL",
    "HIRAGANA",
    "KATAKANA",
    "CJK",
    "ARABIC",
    "HEBREW",
    "GREEK",
    "DEVANAGARI",
    "THAI",
)

_WARP_MAP = vowel_drop_map()


def _script_of(ch: str) -> Optional[str]:
    if not ch.isalpha():
        return None
    name = unicodedata.name(ch, "")
    for prefix in _SCRIPT_PREFIXES:
        if name.startswith(prefix):
            return prefix
    return "OTHER" if name else None


def detect_phonetic_warp(tokens: Sequence[str]) -> Optional[str]:
    """Return recovered slang atom if a token is its vowel-dropped form."""
    for tok in tokens:
        recovered = _WARP_MAP.get(tok)
        if recovered and tok != recovered:
            return recovered
    return None


def detect_game_encode(
    tokens: Sequence[str],
    norm: str,
    *,
    slang_context: bool,
) -> Optional[str]:
    """Leet-of-known-slang, or civilian game-frame plus slang context."""
    for tok in tokens:
        if not token_has_leet(tok):
            continue
        decoded = leet_decode(tok)
        if decoded in SUBSTITUTE_TERMS and decoded != tok:
            return decoded
    if slang_context:
        for marker in GAME_MARKERS:
            if marker in norm:
                return marker
    return None


def detect_code_switch(
    raw: str,
    tokens: Sequence[str],
    *,
    lexicon_hit: bool,
) -> bool:
    """Mixed Unicode scripts, or closed particle next to a slang lexicon hit."""
    scripts = {s for s in (_script_of(ch) for ch in raw) if s}
    if len(scripts) >= 2:
        return True
    if lexicon_hit and any(tok in CODE_SWITCH_PARTICLES for tok in tokens):
        return True
    return False


def slang_context(tokens: Iterable[str], ops: Sequence[str]) -> bool:
    if any(tok in SUBSTITUTE_TERMS for tok in tokens):
        return True
    return bool(ops)
