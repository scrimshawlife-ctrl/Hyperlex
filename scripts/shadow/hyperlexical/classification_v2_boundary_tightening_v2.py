"""Boundary tightening V2 — unresolved-row cleanup only.

Reclassifies REVIEW / AMBIGUOUS / DROP / RELABEL_CANDIDATE rows from the sealed
boundary-redefinition artifact and applies pairwise discriminators on the three
structural SPLIT_CANDIDATE pairs. Does not train, score the reserve, move BEST,
mutate ontology, or relax the frozen 30% overlap gate.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from .classification_v2 import (
    ACTIVE_FAMILY_VOCABULARY,
    ClassificationContractError,
    canonical_json,
    sha256_text,
)
from .classification_v2_boundary_redefinition import (
    HIGH_OVERLAP_COSINE,
    MATERIAL_OVERLAP_REDUCTION,
    PRESERVED_NOISE,
    PRESERVED_NOISE_COUNTS,
    REDEF_RULE,
    _tokens,
)
from .classification_v2_separability_audit import (
    BEST_SHA,
    BOUNDARY_SHA,
    COLLAPSE_CLUSTER,
    REPAIR_PRIMARY_SHA,
    SEPARATION_SHA,
    SPARSE_FOCUS,
)

TIGHTEN_SCHEMA = "hyperlex.classification.v2.active_family_boundary_tightening.v2"
TIGHTEN_RULE = "HYPERLEX_ACTIVE_FAMILY_BOUNDARY_TIGHTENING_V2"
BOUNDARY_REDEFINITION_SHA = "4757d46aa7f0c95732378d5f710cbd1a28d048f60bee2fc35dfb6d5c0fe8cad1"
OVERLAY_SHA = "8a934806885fb939f8b4ca26f10ab5bc6600c495d3be77d5a2366dc6c62146e0"
PHASE_EXECUTION_SHA = "6d11eab035d64a5ef8d1008ade9b565064920e6de2cc86673202cbc60753be3b"

UNRESOLVED_STATUSES = frozenset({"REVIEW", "AMBIGUOUS", "DROP", "RELABEL_CANDIDATE"})
FINAL_STATUSES = ("KEEP", "DROP", "RELABEL_CANDIDATE", "AMBIGUOUS")
STRUCTURAL_SPLIT_PAIRS: tuple[tuple[str, str], ...] = (
    ("approval-disapproval", "social-status"),
    ("approval-disapproval", "relationship-dating"),
    ("relationship-dating", "social-status"),
)
STRUCTURAL_FAMILIES = frozenset(
    {
        "approval-disapproval",
        "social-status",
        "relationship-dating",
    }
)

# Mutually exclusive semantic contracts. Phrase cues match as substrings;
# token cues match as whole tokens after tokenization.
FAMILY_TIGHT_SEMANTICS: dict[str, dict[str, tuple[str, ...]]] = {
    "approval-disapproval": {
        "required_core": (
            "derogatory", "endearing", "insult", "pejorative", "praise", "slur",
            "compliment", "disapproval", "approval", "condemn", "condemnation",
            "contemptible", "pejorative", "approving", "disapproving", "abusive",
            "contempt", "scorn", "laudatory",
        ),
        "allowed_secondary_semantics": ("effeminate", "homosexual", "person", "term"),
        # Phrase exclusions only — bare peer-core tokens are handled by pairwise
        # discriminators (AMBIGUOUS), not unilateral DROP.
        "explicit_exclusions": (
            "social status", "social standing", "prestige rank",
            "romantic relationship", "dating partner",
        ),
        "collision_triggers": ("social", "status", "relationship", "romantic"),
    },
    "social-status": {
        "required_core": (
            "status", "prestige", "hierarchy", "rank", "standing", "honorific",
            "elite", "class", "aristocrat", "nobility", "caste", "stratum",
        ),
        "allowed_secondary_semantics": ("social", "society", "title", "respect"),
        "explicit_exclusions": (
            "derogatory insult", "pejorative slur", "romantic relationship",
            "dating partner",
        ),
        "collision_triggers": ("derogatory", "insult", "romantic", "dating", "relationship"),
    },
    "relationship-dating": {
        "required_core": (
            "romantic", "dating", "courtship", "boyfriend", "girlfriend",
            "spouse", "marriage", "partner", "romance", "affection",
            "relationship",
        ),
        "allowed_secondary_semantics": ("love", "intimate", "couple", "attraction"),
        "explicit_exclusions": (
            "social status", "prestige hierarchy", "pejorative insult",
            "honorific rank",
        ),
        "collision_triggers": ("status", "prestige", "hierarchy", "derogatory", "insult"),
    },
    "internet-slang": {
        "required_core": ("internet", "slang", "online", "chat", "reddit", "forum", "netspeak", "meme"),
        "allowed_secondary_semantics": ("web", "digital", "informal"),
        "explicit_exclusions": ("military rank", "point spread", "blockchain wallet"),
        "collision_triggers": ("agent", "prompt", "status", "rank"),
    },
    "memetic": {
        "required_core": ("meme", "memes", "memetic", "copypasta", "macro", "image macro"),
        "allowed_secondary_semantics": ("viral", "format", "template"),
        "explicit_exclusions": ("geopolitical", "military"),
        "collision_triggers": ("political", "status"),
    },
    "betting-sharp": {
        "required_core": (
            "bet", "betting", "odds", "vig", "vigorish", "spread", "moneyline",
            "parlay", "bookmaker", "handicap", "wager",
        ),
        "allowed_secondary_semantics": ("gambling", "stake", "payout"),
        "explicit_exclusions": ("social status", "romantic"),
        "collision_triggers": ("status", "romantic"),
    },
    "ai-native": {
        "required_core": ("agent", "agentic", "llm", "prompt", "clanker", "inference", "model"),
        "allowed_secondary_semantics": ("ai", "assistant", "token"),
        "explicit_exclusions": ("internet slang label",),
        "collision_triggers": ("slang", "reddit"),
    },
    "gaming-meta": {
        "required_core": ("game", "games", "gaming", "player", "players", "fps", "mmo", "loot", "npc", "meta"),
        "allowed_secondary_semantics": ("match", "build", "nerf", "buff"),
        "explicit_exclusions": (),
        "collision_triggers": (),
    },
    "crypto-degen": {
        "required_core": ("crypto", "bitcoin", "ethereum", "token", "defi", "nft", "blockchain", "wallet", "airdrop"),
        "allowed_secondary_semantics": ("mempool", "chain"),
        "explicit_exclusions": (),
        "collision_triggers": (),
    },
    "conflict-aggression": {
        "required_core": ("military", "army", "war", "combat", "weapon", "aggression", "fight", "violence"),
        "allowed_secondary_semantics": ("naval", "troops", "battle"),
        "explicit_exclusions": (),
        "collision_triggers": (),
    },
    "technology-ai": {
        "required_core": ("software", "programming", "computer", "code", "algorithm", "hardware", "security"),
        "allowed_secondary_semantics": ("debugger", "staging", "technology"),
        "explicit_exclusions": (),
        "collision_triggers": (),
    },
    "workplace-career": {
        "required_core": ("business", "workplace", "career", "office", "employee", "manager", "corporate", "profession", "job"),
        "allowed_secondary_semantics": ("utility", "channel", "service"),
        "explicit_exclusions": (),
        "collision_triggers": (),
    },
    "sports-competition": {
        "required_core": ("sport", "sports", "athlete", "championship", "tournament", "league", "coach"),
        "allowed_secondary_semantics": ("team", "score", "puck", "ball"),
        "explicit_exclusions": (),
        "collision_triggers": (),
    },
    "music-entertainment": {
        "required_core": ("music", "song", "melody", "film", "television", "movie", "concert", "album", "solfège", "solfege"),
        "allowed_secondary_semantics": ("instrument", "performance", "note"),
        "explicit_exclusions": (),
        "collision_triggers": (),
    },
    "fashion-aesthetic": {
        "required_core": ("fashion", "clothing", "aesthetic", "garment", "outfit", "dress", "runway"),
        "allowed_secondary_semantics": ("style", "wear", "tone"),
        "explicit_exclusions": (),
        "collision_triggers": (),
    },
    "regional-cultural": {
        "required_core": ("dialect", "regional", "vernacular", "accent", "locale", "cultural"),
        "allowed_secondary_semantics": ("region", "english"),
        "explicit_exclusions": (),
        "collision_triggers": (),
    },
    "spiritual-mystic": {
        "required_core": ("occult", "mystic", "mysticism", "astrology", "spiritual", "ritual", "pagan", "wicca", "esoteric", "alchemy", "magic"),
        "allowed_secondary_semantics": ("spell", "awareness"),
        "explicit_exclusions": (),
        "collision_triggers": (),
    },
    "identity-affiliation": {
        "required_core": ("demonym", "identity", "ethnicity", "lgbtq", "gender", "affiliation", "nationality", "queer", "indigenous"),
        "allowed_secondary_semantics": ("peoples", "member"),
        "explicit_exclusions": (),
        "collision_triggers": (),
    },
    "politics-civic": {
        "required_core": ("politics", "political", "government", "civic", "policy", "election", "geopolitics", "legislature", "reactionary"),
        "allowed_secondary_semantics": ("left-wing", "candidate", "manifesto"),
        "explicit_exclusions": (),
        "collision_triggers": (),
    },
}

# Pairwise discriminators: cues that assign exclusively to one side.
PAIRWISE_DISCRIMINATORS: dict[str, dict[str, Any]] = {
    "approval-disapproval||social-status": {
        "family_a": "approval-disapproval",
        "family_b": "social-status",
        "a_exclusive": (
            "derogatory", "endearing", "insult", "pejorative", "praise", "slur",
            "compliment", "disapproval", "approval", "condemnation", "contemptible",
        ),
        "b_exclusive": (
            "prestige", "hierarchy", "rank", "standing", "honorific", "elite", "caste",
        ),
        "insufficient_alone": ("social", "person", "people", "term", "someone"),
        "ambiguous_when_both": True,
    },
    "approval-disapproval||relationship-dating": {
        "family_a": "approval-disapproval",
        "family_b": "relationship-dating",
        "a_exclusive": (
            "derogatory", "endearing", "insult", "pejorative", "praise", "slur",
            "disapproval", "approval", "condemnation",
        ),
        "b_exclusive": (
            "romantic", "dating", "courtship", "boyfriend", "girlfriend", "spouse", "marriage",
        ),
        "insufficient_alone": ("relationship", "person", "partner"),
        "ambiguous_when_both": True,
    },
    "relationship-dating||social-status": {
        "family_a": "relationship-dating",
        "family_b": "social-status",
        "a_exclusive": (
            "romantic", "dating", "courtship", "boyfriend", "girlfriend", "spouse", "marriage", "affection",
        ),
        "b_exclusive": (
            "prestige", "hierarchy", "rank", "standing", "honorific", "elite", "status",
        ),
        "insufficient_alone": ("relationship", "social", "partner"),
        "ambiguous_when_both": True,
    },
}


def tightening_contract() -> dict[str, Any]:
    return {
        "best_sha256": BEST_SHA,
        "boundary_redefinition_rule": REDEF_RULE,
        "boundary_redefinition_sha256": BOUNDARY_REDEFINITION_SHA,
        "boundary_sha256": BOUNDARY_SHA,
        "encoder_updated": False,
        "high_overlap_cosine": HIGH_OVERLAP_COSINE,
        "historical_boundaries_mutated": False,
        "jev": "OFF",
        "material_overlap_reduction": MATERIAL_OVERLAP_REDUCTION,
        "moves_best": False,
        "mutates_ontology": False,
        "overlay_sha256": OVERLAY_SHA,
        "phase_execution_sha256": PHASE_EXECUTION_SHA,
        "repair_primary_sha256": REPAIR_PRIMARY_SHA,
        "reserve_scored": False,
        "rule": TIGHTEN_RULE,
        "schema": TIGHTEN_SCHEMA,
        "separation_sha256": SEPARATION_SHA,
        "split_candidates_diagnostic_only": True,
        "structural_split_pairs": [
            {"family_a": a, "family_b": b} for a, b in STRUCTURAL_SPLIT_PAIRS
        ],
        "train": False,
        "unresolved_scope": sorted(UNRESOLVED_STATUSES),
    }


def family_semantic_contract(family: str) -> dict[str, Any]:
    raw = FAMILY_TIGHT_SEMANTICS.get(family) or {
        "required_core": (),
        "allowed_secondary_semantics": (),
        "explicit_exclusions": (),
        "collision_triggers": (),
    }
    return {
        "allowed_secondary_semantics": list(raw["allowed_secondary_semantics"]),
        "collision_triggers": list(raw["collision_triggers"]),
        "explicit_exclusions": list(raw["explicit_exclusions"]),
        "family": family,
        "required_core": list(raw["required_core"]),
    }


def pairwise_discriminator(family_a: str, family_b: str) -> dict[str, Any] | None:
    key = "||".join(sorted((family_a, family_b)))
    item = PAIRWISE_DISCRIMINATORS.get(key)
    if item is None:
        return None
    return dict(item)


def _match_cues(text: str, cues: Sequence[str]) -> list[str]:
    lowered = str(text or "").lower()
    tokens = _tokens(lowered)
    hits: list[str] = []
    for cue in cues:
        cue_l = str(cue).lower()
        if " " in cue_l:
            if cue_l in lowered and cue_l not in hits:
                hits.append(cue_l)
        elif cue_l in tokens and cue_l not in hits:
            hits.append(cue_l)
    return hits


def score_family(text: str, family: str) -> dict[str, Any]:
    contract = family_semantic_contract(family)
    core = _match_cues(text, contract["required_core"])
    secondary = _match_cues(text, contract["allowed_secondary_semantics"])
    exclusions = _match_cues(text, contract["explicit_exclusions"])
    triggers = _match_cues(text, contract["collision_triggers"])
    return {
        "core_hits": core,
        "exclusion_hits": exclusions,
        "family": family,
        "score": len(core) * 2 + len(secondary),
        "secondary_hits": secondary,
        "trigger_hits": triggers,
    }


def _noise_preset(identity: str) -> tuple[str, str, str | None] | None:
    for prefix, payload in PRESERVED_NOISE.items():
        if identity.startswith(prefix):
            return payload
    return None


def _pair_key(a: str, b: str) -> str:
    return "||".join(sorted((a, b)))


def classify_unresolved_row(
    *,
    identity: str,
    current_family: str,
    text: str | None,
    prior_decision: str,
) -> dict[str, Any]:
    """Emit exactly one KEEP/DROP/RELABEL_CANDIDATE/AMBIGUOUS for an unresolved row."""
    preset = _noise_preset(identity)
    if preset is not None:
        decision, gold, relabel = preset
        return {
            "collision_pair": None,
            "current_family": gold,
            "decision": decision,
            "matched_exclusion": None,
            "matched_required_core": [],
            "prior_decision": prior_decision,
            "proposed_family": relabel,
            "reason_code": "preserved_phase_a_noise_audit",
            "source_identity": identity,
            "text": text,
        }

    body = str(text or "").strip()
    if not body:
        return {
            "collision_pair": None,
            "current_family": current_family,
            "decision": "DROP",
            "matched_exclusion": None,
            "matched_required_core": [],
            "prior_decision": prior_decision,
            "proposed_family": None,
            "reason_code": "empty_or_missing_definition",
            "source_identity": identity,
            "text": text,
        }

    scores = [score_family(body, family) for family in ACTIVE_FAMILY_VOCABULARY]
    scores.sort(key=lambda row: (-row["score"], row["family"]))
    own = next(row for row in scores if row["family"] == current_family)
    best = scores[0]
    second = scores[1] if len(scores) > 1 else None

    if own["exclusion_hits"]:
        return {
            "collision_pair": None,
            "current_family": current_family,
            "decision": "DROP",
            "matched_exclusion": own["exclusion_hits"][0],
            "matched_required_core": own["core_hits"],
            "prior_decision": prior_decision,
            "proposed_family": None,
            "reason_code": "explicit_exclusion_violated",
            "source_identity": identity,
            "text": text,
        }

    # Structural pairwise discriminator when gold is in the three-way cluster.
    for a, b in STRUCTURAL_SPLIT_PAIRS:
        if current_family not in (a, b):
            continue
        disc = pairwise_discriminator(a, b)
        if disc is None:
            continue
        a_hits = _match_cues(body, disc["a_exclusive"])
        b_hits = _match_cues(body, disc["b_exclusive"])
        insufficient = _match_cues(body, disc["insufficient_alone"])
        if a_hits and b_hits and disc.get("ambiguous_when_both"):
            return {
                "collision_pair": _pair_key(a, b),
                "current_family": current_family,
                "decision": "AMBIGUOUS",
                "matched_exclusion": None,
                "matched_required_core": own["core_hits"],
                "prior_decision": prior_decision,
                "proposed_family": None,
                "reason_code": "structural_dual_core",
                "source_identity": identity,
                "text": text,
            }
        if insufficient and not a_hits and not b_hits and not own["core_hits"]:
            return {
                "collision_pair": _pair_key(a, b),
                "current_family": current_family,
                "decision": "DROP",
                "matched_exclusion": None,
                "matched_required_core": [],
                "prior_decision": prior_decision,
                "proposed_family": None,
                "reason_code": "shared_context_only",
                "source_identity": identity,
                "text": text,
            }
        # Exclusive peer win → relabel candidate (do not auto-apply).
        if current_family == a and b_hits and not a_hits and not own["core_hits"]:
            return {
                "collision_pair": _pair_key(a, b),
                "current_family": current_family,
                "decision": "RELABEL_CANDIDATE",
                "matched_exclusion": None,
                "matched_required_core": b_hits,
                "prior_decision": prior_decision,
                "proposed_family": b,
                "reason_code": "pairwise_discriminator_peer",
                "source_identity": identity,
                "text": text,
            }
        if current_family == b and a_hits and not b_hits and not own["core_hits"]:
            return {
                "collision_pair": _pair_key(a, b),
                "current_family": current_family,
                "decision": "RELABEL_CANDIDATE",
                "matched_exclusion": None,
                "matched_required_core": a_hits,
                "prior_decision": prior_decision,
                "proposed_family": a,
                "reason_code": "pairwise_discriminator_peer",
                "source_identity": identity,
                "text": text,
            }

    if not own["core_hits"] and best["family"] != current_family and best["score"] >= 2 and len(best["core_hits"]) >= 1:
        return {
            "collision_pair": _pair_key(current_family, best["family"]),
            "current_family": current_family,
            "decision": "RELABEL_CANDIDATE",
            "matched_exclusion": None,
            "matched_required_core": best["core_hits"],
            "prior_decision": prior_decision,
            "proposed_family": best["family"],
            "reason_code": "competitor_required_core",
            "source_identity": identity,
            "text": text,
        }

    if own["core_hits"] and second and len(second["core_hits"]) >= 1 and second["score"] >= own["score"]:
        return {
            "collision_pair": _pair_key(current_family, second["family"]),
            "current_family": current_family,
            "decision": "AMBIGUOUS",
            "matched_exclusion": None,
            "matched_required_core": own["core_hits"],
            "prior_decision": prior_decision,
            "proposed_family": None,
            "reason_code": "multi_family_required_core",
            "source_identity": identity,
            "text": text,
        }

    if own["core_hits"]:
        return {
            "collision_pair": None,
            "current_family": current_family,
            "decision": "KEEP",
            "matched_exclusion": None,
            "matched_required_core": own["core_hits"],
            "prior_decision": prior_decision,
            "proposed_family": None,
            "reason_code": "required_core_established",
            "source_identity": identity,
            "text": text,
        }

    if own["score"] == 0 and best["score"] == 0:
        return {
            "collision_pair": None,
            "current_family": current_family,
            "decision": "DROP",
            "matched_exclusion": None,
            "matched_required_core": [],
            "prior_decision": prior_decision,
            "proposed_family": None,
            "reason_code": "no_family_required_core",
            "source_identity": identity,
            "text": text,
        }

    if own["score"] == 0 and (own["trigger_hits"] or len(body.split()) <= 6):
        return {
            "collision_pair": None,
            "current_family": current_family,
            "decision": "DROP",
            "matched_exclusion": None,
            "matched_required_core": [],
            "prior_decision": prior_decision,
            "proposed_family": None,
            "reason_code": "too_generic_or_associative",
            "source_identity": identity,
            "text": text,
        }

    return {
        "collision_pair": None,
        "current_family": current_family,
        "decision": "DROP",
        "matched_exclusion": None,
        "matched_required_core": [],
        "prior_decision": prior_decision,
        "proposed_family": None,
        "reason_code": "unresolved_without_required_core",
        "source_identity": identity,
        "text": text,
    }


def classify_structural_keep_for_comparison(
    *,
    identity: str,
    current_family: str,
    text: str | None,
) -> dict[str, Any] | None:
    """Only for KEEP rows inside structural split families — comparison pass."""
    if current_family not in STRUCTURAL_FAMILIES:
        return None
    body = str(text or "").strip()
    if not body:
        return None
    own = score_family(body, current_family)
    for a, b in STRUCTURAL_SPLIT_PAIRS:
        if current_family not in (a, b):
            continue
        disc = pairwise_discriminator(a, b)
        if disc is None:
            continue
        a_hits = _match_cues(body, disc["a_exclusive"])
        b_hits = _match_cues(body, disc["b_exclusive"])
        if a_hits and b_hits:
            return {
                "collision_pair": _pair_key(a, b),
                "current_family": current_family,
                "decision": "AMBIGUOUS",
                "matched_exclusion": None,
                "matched_required_core": own["core_hits"],
                "prior_decision": "KEEP",
                "proposed_family": None,
                "reason_code": "structural_keep_dual_core_comparison",
                "source_identity": identity,
                "text": text,
            }
        peer = b if current_family == a else a
        peer_hits = b_hits if current_family == a else a_hits
        own_hits = a_hits if current_family == a else b_hits
        if peer_hits and not own_hits and not own["core_hits"]:
            return {
                "collision_pair": _pair_key(a, b),
                "current_family": current_family,
                "decision": "AMBIGUOUS",
                "matched_exclusion": None,
                "matched_required_core": [],
                "prior_decision": "KEEP",
                "proposed_family": peer,
                "reason_code": "structural_keep_peer_core_comparison",
                "source_identity": identity,
                "text": text,
            }
    return None


def build_final_keep_identities(
    *,
    prior_rows: Sequence[Mapping[str, Any]],
    unresolved_results: Sequence[Mapping[str, Any]],
    structural_keep_overrides: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Prior KEEP minus structural overrides plus newly KEEP unresolved rows."""
    override = {row["source_identity"]: row for row in structural_keep_overrides}
    keep_by_family: dict[str, list[str]] = {family: [] for family in ACTIVE_FAMILY_VOCABULARY}
    for row in prior_rows:
        if row.get("decision") != "KEEP":
            continue
        identity = str(row["identity"])
        if identity in override and override[identity]["decision"] != "KEEP":
            continue
        family = str(row["family"])
        keep_by_family[family].append(identity)
    for row in unresolved_results:
        if row["decision"] != "KEEP":
            continue
        # Never reintroduce preserved DROP noise.
        preset = _noise_preset(str(row["source_identity"]))
        if preset and preset[0] == "DROP":
            continue
        family = str(row["current_family"])
        identity = str(row["source_identity"])
        if identity not in keep_by_family[family]:
            keep_by_family[family].append(identity)
    support = {family: len(ids) for family, ids in keep_by_family.items()}
    sparse_ok = all(support.get(family, 0) >= 12 for family in SPARSE_FOCUS)
    zeros = [family for family in ACTIVE_FAMILY_VOCABULARY if support.get(family, 0) < 1]
    return {
        "keep_identities": keep_by_family,
        "sparse_support_preserved": sparse_ok,
        "support": support,
        "support_floor_failure": (not sparse_ok) or bool(zeros),
        "zero_support_families": zeros,
    }


def assess_structural_splits(
    *,
    pre_pairs: Sequence[Mapping[str, Any]],
    post_pairs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    pre_set = {(p["family_a"], p["family_b"]) for p in pre_pairs} | {
        (p["family_b"], p["family_a"]) for p in pre_pairs
    }
    post_set = {(p["family_a"], p["family_b"]) for p in post_pairs} | {
        (p["family_b"], p["family_a"]) for p in post_pairs
    }
    out = []
    for a, b in STRUCTURAL_SPLIT_PAIRS:
        was = (a, b) in pre_set
        still = (a, b) in post_set
        if was and not still:
            status = "RESOLVED_BY_BOUNDARY"
            future = False
        elif still:
            status = "OVERLAP_REMAINS_STRUCTURAL"
            future = True
        else:
            status = "INSUFFICIENT_EVIDENCE"
            future = False
        out.append(
            {
                "family_a": a,
                "family_b": b,
                "future_ontology_refactor_candidate": future,
                "split_performed": False,
                "status": status,
            }
        )
    return out


def training_gate_v2(
    *,
    pre_count: int,
    post_count: int,
    support: Mapping[str, int],
    collapse_pre: int,
    collapse_post: int,
    support_floor_failure: bool,
) -> dict[str, Any]:
    if pre_count == 0:
        reduction = 1.0 if post_count == 0 else 0.0
    else:
        reduction = (pre_count - post_count) / pre_count
    zeros = [family for family in ACTIVE_FAMILY_VOCABULARY if support.get(family, 0) < 1]
    sparse_ok = all(support.get(family, 0) >= 12 for family in SPARSE_FOCUS)
    collapse_weakened = collapse_post < collapse_pre
    open_gate = (
        not support_floor_failure
        and not zeros
        and sparse_ok
        and reduction >= MATERIAL_OVERLAP_REDUCTION
        and collapse_weakened
    )
    residual = []
    if reduction < MATERIAL_OVERLAP_REDUCTION:
        residual.append(
            {
                "blocker": "OVERLAP_REDUCTION_BELOW_THRESHOLD",
                "observed": reduction,
                "required": MATERIAL_OVERLAP_REDUCTION,
            }
        )
    if support_floor_failure or not sparse_ok:
        residual.append(
            {
                "blocker": "TRAINING_SUPPORT_FLOOR_FAILURE",
                "sparse": {family: support.get(family, 0) for family in SPARSE_FOCUS},
                "zeros": zeros,
            }
        )
    if zeros:
        residual.append({"blocker": "ZERO_SUPPORT_FAMILY", "families": zeros})
    if not collapse_weakened:
        residual.append(
            {
                "blocker": "COLLAPSE_COMPONENT_NOT_WEAKENED",
                "pre": collapse_pre,
                "post": collapse_post,
            }
        )
    return {
        "allow_best_move": False,
        "allow_encoder_training": open_gate,
        "allow_reserve_scoring": False,
        "collapse_component_post": collapse_post,
        "collapse_component_pre": collapse_pre,
        "collapse_weakened": collapse_weakened,
        "material_overlap_reduction_required": MATERIAL_OVERLAP_REDUCTION,
        "next_action": "TRAIN_CLASSIFICATION_V2" if open_gate else "RESOLVE_RESIDUAL_BLOCKERS",
        "overlap_reduction": reduction,
        "post_high_overlap_pairs": post_count,
        "pre_high_overlap_pairs": pre_count,
        "residual_blockers": residual,
        "sparse_support_preserved": sparse_ok,
        "training_gate": "OPEN" if open_gate else "CLOSED",
        "zero_support_families": zeros,
    }


def delta_counts(
    prior_counts: Mapping[str, int],
    new_unresolved_counts: Mapping[str, int],
    *,
    structural_override_counts: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Summarize changes vs sealed boundary-redefinition unresolved set."""
    structural_override_counts = structural_override_counts or {}
    return {
        "prior_unresolved_counts": {
            status: int(prior_counts.get(status, 0)) for status in sorted(UNRESOLVED_STATUSES)
        },
        "reclassified_unresolved_counts": {
            status: int(new_unresolved_counts.get(status, 0)) for status in FINAL_STATUSES
        },
        "structural_keep_overrides": {
            status: int(structural_override_counts.get(status, 0)) for status in FINAL_STATUSES
        },
        "prior_keep": int(prior_counts.get("KEEP", 0)),
    }


def next_engineering_action(artifact: Mapping[str, Any]) -> str:
    gate = artifact.get("training_gate") or {}
    if gate.get("training_gate") == "OPEN":
        return "TRAIN_CLASSIFICATION_V2"
    blockers = gate.get("residual_blockers") or []
    if any(row.get("blocker") == "TRAINING_SUPPORT_FLOOR_FAILURE" for row in blockers):
        return (
            "TRAINING_SUPPORT_FLOOR_FAILURE — restore sparse/family floors before any training; "
            "do not train, score the reserve, or move BEST."
        )
    structural = [
        row
        for row in (artifact.get("split_candidate_assessments") or [])
        if row.get("status") == "OVERLAP_REMAINS_STRUCTURAL"
    ]
    if structural and any(row.get("blocker") == "OVERLAP_REDUCTION_BELOW_THRESHOLD" for row in blockers):
        return (
            "ONTOLOGY_REFACTOR_REVIEW — residual three-way cluster still structural after "
            "tightening; schedule operator MERGE/SPLIT review. Do not train."
        )
    return (
        "BOUNDARY_TIGHTENING_RESIDUAL — clear residual blockers in the sealed artifact, "
        "then reseal. Do not train, score the reserve, or move BEST."
    )


def assemble_tightening(payload: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "family_semantics",
        "pairwise_discriminators",
        "unresolved_reclassifications",
        "structural_keep_overrides",
        "row_status_counts",
        "delta",
        "support",
        "overlap_pre",
        "overlap_post",
        "split_candidate_assessments",
        "training_gate",
    )
    for key in required:
        if key not in payload:
            raise ClassificationContractError("BOUNDARY_TIGHTENING_UNAVAILABLE", key)
    if len(payload["family_semantics"]) != 19:
        raise ClassificationContractError("BOUNDARY_TIGHTENING_UNAVAILABLE", "semantics_count")
    contract = tightening_contract()
    artifact = {
        "best_sha256": BEST_SHA,
        "boundary_redefinition_sha256": BOUNDARY_REDEFINITION_SHA,
        "boundary_sha256": BOUNDARY_SHA,
        "boundary_tightening_state": "SEALED",
        "collapse_component_post": payload["overlap_post"].get("largest_collapse_component"),
        "collapse_component_pre": payload["overlap_pre"].get("largest_collapse_component"),
        "contract": contract,
        "delta": payload["delta"],
        "encoder_updated": False,
        "family_semantics": payload["family_semantics"],
        "historical_boundaries_mutated": False,
        "jev": "OFF",
        "material_overlap_reduction": MATERIAL_OVERLAP_REDUCTION,
        "moves_best": False,
        "mutates_ontology": False,
        "overlap_absolute_reduction": int(payload["overlap_pre"]["high_overlap_pair_count"])
        - int(payload["overlap_post"]["high_overlap_pair_count"]),
        "overlap_post": {
            "collapse_high_overlap_pairs": payload["overlap_post"]["collapse_high_overlap_pairs"],
            "high_overlap_pair_count": payload["overlap_post"]["high_overlap_pair_count"],
            "largest_collapse_component": payload["overlap_post"]["largest_collapse_component"],
            "threshold": payload["overlap_post"]["threshold"],
        },
        "overlap_pre": {
            "collapse_high_overlap_pairs": payload["overlap_pre"]["collapse_high_overlap_pairs"],
            "high_overlap_pair_count": payload["overlap_pre"]["high_overlap_pair_count"],
            "largest_collapse_component": payload["overlap_pre"]["largest_collapse_component"],
            "threshold": payload["overlap_pre"]["threshold"],
        },
        "overlap_reduction": payload["training_gate"].get("overlap_reduction"),
        "overlay_sha256": OVERLAY_SHA,
        "pairwise_discriminators": payload["pairwise_discriminators"],
        "preserved_noise_audit": PRESERVED_NOISE_COUNTS,
        "repair_primary_sha256": REPAIR_PRIMARY_SHA,
        "reserve_scored": False,
        "row_status_counts": payload["row_status_counts"],
        "schema": TIGHTEN_SCHEMA,
        "separation_sha256": SEPARATION_SHA,
        "sparse_support": {family: payload["support"].get(family, 0) for family in SPARSE_FOCUS},
        "split_candidate_assessments": payload["split_candidate_assessments"],
        "structural_keep_overrides": payload["structural_keep_overrides"],
        "support": {family: payload["support"].get(family, 0) for family in ACTIVE_FAMILY_VOCABULARY},
        "train": False,
        "training_gate": payload["training_gate"],
        "unresolved_reclassifications": payload["unresolved_reclassifications"],
    }
    artifact["next_engineering_action"] = next_engineering_action(artifact)
    artifact["artifact_sha256"] = sha256_text(
        canonical_json({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    )
    return artifact
