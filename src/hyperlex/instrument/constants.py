"""Pinned identities for HYPERLEX_INSTRUMENT_V1.

Frozen references only. No training. No spent QUAL reuse.
"""

from __future__ import annotations

INSTRUMENT_VERSION = "HYPERLEX_INSTRUMENT_V1"
CONTRACT_VERSION = "hyperlex.instrument.v1"
PRODUCT_ROLE = "REPRESENTATION_AND_MEASUREMENT_LAYER"
OPERATION_MODE = "SHADOW_INSTRUMENT_ONLY"
CLASSIFIER_RELEASE = "REJECTED"
INSTRUMENT_READINESS = "READY_FOR_ABRAXAS_SHADOW_USE"

SETTLEMENT_REF = (
    "specs/007-hyperlexical-model/classification-v6-program-settlement-20261002.md"
)
SETTLEMENT_RECEIPT = (
    "4ae7cddffcf72330adad8eb3dfd453025aa02c8cb12c5e6f5499a4e6cad06ca2"
)
SETTLEMENT_COMMIT = "b74a1b1b"

ONTOLOGY_VERSION = "HYPERLEX_V6_FAMILY_ONTOLOGY_V1_FINAL"
ONTOLOGY_RECEIPT = (
    "04a765032f17c663959e151b3fd968d0f445e017bd310b536b9843d0b45b874b"
)

# Settled representation family (intended). Runtime may fall back to STATIC_HASH.
ENCODER_ID = "sentence-transformers/msmarco-distilbert-base-v4"
ENCODER_REVISION = "b2f66c95aba1481a880479165582020c2b9b64d7"
ENCODER_ROLE = "FROZEN_REFERENCE_FAMILY"
# Identity hash of the pin string (not Hub weight bytes — weights optional offline).
ENCODER_PIN_PREIMAGE = f"{ENCODER_ID}@{ENCODER_REVISION}"

# Rejected classifier package retained as scientific evidence only — never cold-loaded.
REJECTED_CORE_PACKAGE_SHA256 = (
    "035e1b7e21e97ed36f79750f1f643262540fba1546f488af2a0af04e8a7c1605"
)
REJECTED_CORE_QUAL_ID = "HYPERLEX_V6_CORE_QUALIFICATION_001"

AUTHORITY = {
    "kind": "advisory",
    "source": "hyperlex",
    "semantic_truth": False,
    "may_authorize": False,
    "may_mutate_governing_state": False,
    "role": "OBSERVATION",
}

# Ontology concept space for advisory candidates / neighborhood (pinned cues).
# Not a mandatory classifier emission checklist.
DOMAIN_CONCEPTS: dict[str, tuple[str, ...]] = {
    "domain.gaming": ("game", "gaming", "fps", "mmo", "npc", "loot", "nerf", "buff", "esport"),
    "domain.gambling": (
        "bet", "betting", "wager", "odds", "vig", "parlay", "bookmaker",
        "moneyline", "casino", "poker", "blackjack", "roulette", "handicap",
    ),
    "domain.crypto": (
        "crypto", "bitcoin", "ethereum", "blockchain", "defi", "nft", "airdrop",
        "mempool", "satoshi", "altcoin",
    ),
    "domain.sports": (
        "sport", "athlete", "league", "tournament", "championship", "coach",
        "mlb", "nba", "nfl",
    ),
    "domain.entertainment": (
        "music", "song", "album", "film", "movie", "television", "concert",
    ),
    "domain.fashion": (
        "fashion", "clothing", "garment", "outfit", "runway", "dress", "aesthetic",
    ),
    "domain.workplace": (
        "workplace", "career", "office", "employee", "manager", "corporate", "job",
    ),
    "domain.politics": (
        "politics", "political", "government", "election", "civic", "legislature",
        "policy",
    ),
    "domain.spiritual": (
        "occult", "astrology", "spiritual", "mystic", "ritual", "pagan",
        "esoteric", "zodiac",
    ),
    "domain.technology": (
        "software", "programming", "computer", "algorithm", "hardware", "code",
        "debugger",
    ),
    "domain.technology.ai_discourse": (
        "llm", "prompt", "agentic", "chatgpt", "inference", "clanker",
        "language model",
    ),
}

MEDIATION_CONCEPTS: dict[str, tuple[str, ...]] = {
    "mediation.internet_register": (
        "internet", "online", "reddit", "netspeak", "chat slang", "forum",
    ),
}

FUNCTION_CONCEPTS: dict[str, tuple[str, ...]] = {
    "function.evaluative_stance": (
        "derogatory", "pejorative", "insult", "slur", "praise", "compliment",
        "contempt", "scorn", "endearing", "disapproval", "approval",
    ),
    "function.relational_intimacy": (
        "romantic", "dating", "boyfriend", "girlfriend", "spouse", "marriage",
        "courtship", "intimate",
    ),
    "function.conflictive_force": (
        "military", "combat", "weapon", "violence", "aggression", "warfare", "kill",
    ),
}

# Research-only — never emitted as product candidates.
RESEARCH_ONLY_CONCEPTS = frozenset({"function.memetic_form"})

CANDIDATE_SCORE_FLOOR = 0.15
NEIGHBORHOOD_TOP_K = 8
STATIC_EMBED_DIMS = 32
