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
