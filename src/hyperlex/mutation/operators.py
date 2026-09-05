"""Detector enum and maps onto lineage / prediction vocabularies."""
from __future__ import annotations

DETECTOR_OPS = (
    "SUBSTITUTE",
    "AFFIX",
    "CLIP_BLEND",
    "EGGCORN",
    "PHONETIC_WARP",
    "GAME_ENCODE",
    "REGISTER_SHIFT",
    "CODE_SWITCH",
    "FRAME_WRAP",
    "COMPOSE",
)

LAYER_FOR_OP = {
    "SUBSTITUTE": "L3",
    "AFFIX": "L2",
    "CLIP_BLEND": "L2",
    "EGGCORN": "L3",
    "PHONETIC_WARP": "L1",
    "GAME_ENCODE": "L4",
    "REGISTER_SHIFT": "L5",
    "CODE_SWITCH": "L6",
    "FRAME_WRAP": "L7",
    "COMPOSE": None,
}

LINEAGE_TO_DETECTOR = {
    "sense_extension": "SUBSTITUTE",
    "irony_inversion": "REGISTER_SHIFT",
    "platform_compression": "PHONETIC_WARP",
    "eggcorn": "EGGCORN",
    "cross_family_borrowing": "SUBSTITUTE",
    "hyperstition_loop": None,
    "derivational": "AFFIX",
    "compound_phrase": None,
    "extra-grammatical": "AFFIX",
}

PRODUCTIVE_AFFIXES = (
    "maxxing",
    "pilled",
    "core",
    "posting",
    "points",
    "slop",
    "diff",
    "season",
    "coded",
)

SUBSTITUTE_TERMS = frozenset({
    "unalive",
    "cooked",
    "mid",
    "npc",
    "rizz",
    "aura",
    "brainrot",
    "delulu",
    "glazing",
    "slop",
    "sigma",
    "skibidi",
    "gyatt",
    "bussin",
    "based",
    "cope",
    "seethe",
    "ratio",
    "owned",
    "rekt",
    "hodl",
    "ngmi",
    "wagmi",
})

REGISTER_MARKERS = (
    "it's giving",
    "its giving",
    "lowkey",
    "highkey",
    "no cap",
    "ngl",
    "fr fr",
    "iykyk",
    "not gonna lie",
)

FRAME_MARKERS = (
    "for the lore",
    "just a bit",
    "in this essay",
)

EGGCORN_PHRASES = (
    "all intensive purposes",
    "mute point",
    "old timers disease",
    "old-timers disease",
    "egg corn",
    "eggcorn",
    "for all intensive purposes",
)

# Civilian game-frame phrases only. Marker alone does not fire GAME_ENCODE.
GAME_MARKERS = (
    "in fortnite",
    "in minecraft",
    "in roblox",
    "in among us",
    "pig latin",
    "in uwu",
    "as a haiku",
)

# Whole-token bilingual particles. Require a slang lexicon hit in the same span.
CODE_SWITCH_PARTICLES = frozenset({
    "que",
    "qué",
    "el",
    "très",
    "c'est",
    "mucho",
    "muito",
    "não",
    "kein",
})

_VOWELS = set("aeiouAEIOU")
_LEET_TABLE = str.maketrans({
    "0": "o",
    "1": "i",
    "3": "e",
    "4": "a",
    "5": "s",
    "7": "t",
    "@": "a",
    "$": "s",
    "!": "i",
})


def vowel_drop(seed: str) -> str | None:
    """Keep first/last chars; drop internal vowels. Same rule as predict."""
    if len(seed) < 4 or " " in seed:
        return None
    chars = []
    for i, ch in enumerate(seed):
        if i > 0 and i < len(seed) - 1 and ch in _VOWELS:
            continue
        chars.append(ch)
    out = "".join(chars)
    if out.lower() == seed.lower() or len(out) < 2:
        return None
    return out.lower()


def vowel_drop_map(terms: frozenset[str] | None = None) -> dict[str, str]:
    out: dict[str, str] = {}
    for term in terms or SUBSTITUTE_TERMS:
        warped = vowel_drop(term)
        if warped and warped not in SUBSTITUTE_TERMS:
            out[warped] = term
    return out


def leet_decode(token: str) -> str:
    return token.translate(_LEET_TABLE).lower()


def token_has_leet(token: str) -> bool:
    return any(ch in token for ch in "013457@$!")
