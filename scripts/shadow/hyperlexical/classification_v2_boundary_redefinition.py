"""Deterministic active-family boundary redefinition contracts.

Converts Phase-B cue packs and Phase-C overlap findings into machine-usable
family contracts and pairwise distinction rules. Does not train, score the
reserve, move BEST, or mutate historical boundary artifacts.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Mapping, Sequence

from .classification_v2 import (
    ACTIVE_FAMILY_VOCABULARY,
    ClassificationContractError,
    canonical_json,
    sha256_text,
)
from .classification_v2_boundaries import COLLISION_COSINE
from .classification_v2_phase_execution import (
    PHASE_RULE as PHASE_EXECUTION_RULE,
)
from .classification_v2_separability_audit import (
    BEST_SHA,
    BOUNDARY_SHA,
    COLLAPSE_CLUSTER,
    REPAIR_PRIMARY_SHA,
    SEPARATION_SHA,
    SPARSE_FOCUS,
    lexical_pair_report,
    token_document_counts,
)
from .classification_v2_prototype import _unit
from .holdout_guard import normalized_text_sha256

REDEF_SCHEMA = "hyperlex.classification.v2.active_family_boundary_redefinition.v1"
REDEF_RULE = "HYPERLEX_ACTIVE_FAMILY_BOUNDARY_REDEFINITION_V1"
PHASE_EXECUTION_SHA = "6d11eab035d64a5ef8d1008ade9b565064920e6de2cc86673202cbc60753be3b"
PHASE_D_AUDIT_SHA = "d56d03420e7f7072b1798a55e7ecd8877263b1dfd4ad938d36115cba18a21d0a"
OVERLAY_SHA = "8a934806885fb939f8b4ca26f10ab5bc6600c495d3be77d5a2366dc6c62146e0"

# Defined before applying rules. Do not tune after seeing results.
HIGH_OVERLAP_COSINE = COLLISION_COSINE  # 0.80
MATERIAL_OVERLAP_REDUCTION = 0.30
ROW_STATUSES = ("KEEP", "REVIEW", "DROP", "RELABEL_CANDIDATE", "AMBIGUOUS")

# Preserved Phase-A noise audit (exact prefix identities).
PRESERVED_NOISE = {
    "17d1d192814cdda7": ("KEEP", "relationship-dating", None),
    "4df2dd1d7f069ccc": ("KEEP", "relationship-dating", None),
    "5dcd520e0f42301b": ("KEEP", "spiritual-mystic", None),
    "2e19997bbcf52f02": ("RELABEL_CANDIDATE", "workplace-career", "technology-ai"),
    "8bd78f57167eeb19": ("DROP", "regional-cultural", None),
    "90544f171008d3cf": ("DROP", "music-entertainment", None),
    "bc29c71410e85594": ("DROP", "relationship-dating", None),
}
PRESERVED_NOISE_COUNTS = {"KEEP": 3, "RELABEL_CANDIDATE": 1, "DROP": 3}

# Family semantic cores: operator-stable cues that must appear for KEEP when
# the row would otherwise collide with a nearest competitor.
FAMILY_SEMANTIC_CORES: dict[str, tuple[str, ...]] = {
    "gaming-meta": ("game", "games", "gaming", "player", "players", "meta", "fps", "mmo", "loot", "npc"),
    "betting-sharp": ("bet", "betting", "odds", "vig", "vigorish", "spread", "moneyline", "steam", "sharp", "bookmaker", "parlay", "handicap"),
    "crypto-degen": ("crypto", "bitcoin", "ethereum", "token", "defi", "nft", "blockchain", "wallet", "airdrop", "mempool"),
    "internet-slang": ("internet", "slang", "online", "chat", "meme", "reddit", "forum", "netspeak"),
    "memetic": ("meme", "memes", "memetic", "copypasta", "macro", "viral", "image"),
    "social-status": ("status", "prestige", "hierarchy", "rank", "elite", "honorific", "class", "standing"),
    "relationship-dating": ("relationship", "dating", "romantic", "courtship", "partner", "boyfriend", "girlfriend", "spouse", "marriage"),
    "approval-disapproval": ("derogatory", "endearing", "insult", "pejorative", "praise", "slur", "compliment", "disapproval", "approval"),
    "conflict-aggression": ("military", "army", "war", "combat", "weapon", "attack", "aggression", "fight", "violence"),
    "technology-ai": ("software", "programming", "computer", "code", "algorithm", "hardware", "security", "program", "technology"),
    "workplace-career": ("business", "workplace", "career", "office", "employee", "manager", "corporate", "profession", "job"),
    "sports-competition": ("sport", "sports", "athlete", "team", "championship", "tournament", "league", "coach", "score"),
    "music-entertainment": ("music", "song", "melody", "film", "television", "movie", "concert", "album", "performance"),
    "fashion-aesthetic": ("fashion", "clothing", "aesthetic", "style", "garment", "wear", "outfit", "dress"),
    "regional-cultural": ("dialect", "regional", "vernacular", "accent", "locale", "region", "cultural"),
    "spiritual-mystic": ("occult", "mystic", "mysticism", "astrology", "spiritual", "ritual", "pagan", "wicca", "esoteric"),
    "identity-affiliation": ("demonym", "identity", "ethnicity", "lgbtq", "gender", "affiliation", "nationality", "queer"),
    "politics-civic": ("politics", "political", "government", "civic", "policy", "election", "geopolitics", "legislature"),
    "ai-native": ("agent", "agentic", "llm", "model", "prompt", "clanker", "ai", "assistant", "inference"),
}

_TOKEN = re.compile(r"[a-z0-9]{3,}")
_STOP = frozenset(
    {
        "the", "and", "for", "with", "that", "this", "from", "into", "used", "using",
        "especially", "often", "usually", "someone", "something", "person", "people",
        "without", "about", "other", "when", "which", "their", "them", "they", "have",
        "been", "being", "also", "more", "most", "such", "than", "then", "very",
        "you", "your", "has", "are", "was", "were", "not", "any", "all", "one", "two",
    }
)


def redefinition_contract() -> dict[str, Any]:
    return {
        "best_sha256": BEST_SHA,
        "boundary_sha256": BOUNDARY_SHA,
        "encoder_updated": False,
        "high_overlap_cosine": HIGH_OVERLAP_COSINE,
        "historical_boundaries_mutated": False,
        "jev": "OFF",
        "material_overlap_reduction": MATERIAL_OVERLAP_REDUCTION,
        "moves_best": False,
        "mutates_ontology": False,
        "overlay_sha256": OVERLAY_SHA,
        "phase_d_audit_sha256": PHASE_D_AUDIT_SHA,
        "phase_execution_sha256": PHASE_EXECUTION_SHA,
        "repair_primary_sha256": REPAIR_PRIMARY_SHA,
        "reserve_scored": False,
        "rule": REDEF_RULE,
        "schema": REDEF_SCHEMA,
        "separation_sha256": SEPARATION_SHA,
        "split_candidates_diagnostic_only": True,
        "train": False,
    }


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in _TOKEN.findall(str(text).lower())
        if token not in _STOP and len(token) >= 3
    }


def _noise_preset(identity: str) -> tuple[str, str, str | None] | None:
    for prefix, payload in PRESERVED_NOISE.items():
        if identity.startswith(prefix):
            return payload
    return None


def build_family_contract(
    family: str,
    *,
    pack: Mapping[str, Any] | None,
    evidence: Mapping[str, Any] | None,
    texts: Sequence[str],
) -> dict[str, Any]:
    pack = pack or {}
    evidence = evidence or {}
    positive = list(pack.get("positive_cues") or evidence.get("positive_semantic_cues") or [])
    counts = token_document_counts(texts)
    enriched = sorted(counts, key=lambda token: (-counts[token], token))[:12]
    positive = list(dict.fromkeys([*positive, *enriched]))[:12]
    core = list(FAMILY_SEMANTIC_CORES.get(family, ()))
    # Prefer cores that also appear in training text or positive cues.
    present = _tokens(" ".join(texts)) | {str(token).lower() for token in positive}
    required = [cue for cue in core if cue in present] or list(core[:4])
    nearest_raw = list(pack.get("nearest_competitors") or evidence.get("nearest_competing_families") or [])
    nearest: list[str] = []
    for item in nearest_raw:
        if isinstance(item, Mapping):
            name = str(item.get("family") or "")
        else:
            name = str(item)
        if name and name not in nearest:
            nearest.append(name)
    nearest = nearest[:3]
    exclusions = list(pack.get("exclusion_cues") or evidence.get("exclusion_cues") or [])[:8]
    shared = pack.get("shared_overlapping_cues") or evidence.get("shared_overlapping_cues") or {}
    counterexamples = []
    for row in evidence.get("boundary_violating_rows") or []:
        counterexamples.append(
            {
                "identity": row.get("identity"),
                "nearest_family": row.get("best_family"),
                "text": row.get("text"),
            }
        )
    ambiguous_with = []
    for row in evidence.get("ambiguous_training_rows") or []:
        second = row.get("second_family")
        if second and second not in ambiguous_with:
            ambiguous_with.append(second)
    for competitor in nearest:
        if competitor not in ambiguous_with:
            ambiguous_with.append(competitor)
    return {
        "ambiguous_with": ambiguous_with[:5],
        "counterexample_patterns": counterexamples[:6],
        "exclusion_cues": exclusions,
        "family": family,
        "nearest_competitors": nearest,
        "positive_cues": positive,
        "required_semantic_core": required[:8],
        "shared_overlapping_cues": {
            key: list(value)[:6] for key, value in sorted(shared.items())
        },
    }


def build_pairwise_rule(
    family_a: str,
    family_b: str,
    *,
    contract_a: Mapping[str, Any],
    contract_b: Mapping[str, Any],
    texts_a: Sequence[str],
    texts_b: Sequence[str],
) -> dict[str, Any]:
    lexical = lexical_pair_report(texts_a, texts_b)
    shared = list(lexical.get("shared_high_frequency_tokens") or [])[:8]
    a_dist = list(
        dict.fromkeys(
            list(contract_a.get("required_semantic_core") or [])
            + list(lexical.get("tokens_enriched_in_a") or [])
        )
    )[:8]
    b_dist = list(
        dict.fromkeys(
            list(contract_b.get("required_semantic_core") or [])
            + list(lexical.get("tokens_enriched_in_b") or [])
        )
    )[:8]
    return {
        "a_distinguishing_semantics": a_dist,
        "ambiguous_conditions": (
            "row matches both required cores, or matches shared semantics without either "
            "family's distinguishing cues"
        ),
        "b_distinguishing_semantics": b_dist,
        "family_a": family_a,
        "family_b": family_b,
        "shared_semantics": shared,
        "shared_token_ratio": lexical.get("shared_token_ratio"),
    }


def _core_hits(tokens: set[str], cues: Sequence[str]) -> list[str]:
    hits = []
    for cue in cues:
        cue_l = str(cue).lower()
        if " " in cue_l:
            # multiword exclusion strings handled separately
            continue
        if cue_l in tokens:
            hits.append(cue_l)
    return hits


def _exclusion_triggered(text: str, exclusion_cues: Sequence[str], family_tokens: set[str]) -> str | None:
    lowered = text.lower()
    for cue in exclusion_cues:
        # formats like "note (music-entertainment) without social"
        match = re.match(r"([a-z0-9\- ]+)\s*\(([^)]+)\)\s*without\s+([a-z0-9\-]+)", str(cue).lower())
        if not match:
            continue
        trigger, _competitor, required = match.group(1).strip(), match.group(2).strip(), match.group(3).strip()
        if trigger in lowered and required not in family_tokens:
            return cue
    return None


def classify_training_row(
    *,
    family: str,
    text: str,
    identity: str,
    contracts: Mapping[str, Mapping[str, Any]],
    pairwise_rules: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    preset = _noise_preset(identity)
    if preset is not None:
        decision, gold, relabel = preset
        return {
            "decision": decision,
            "family": gold,
            "identity": identity,
            "reasons": ["preserved_phase_a_noise_audit"],
            "relabel_to": relabel,
            "text": text,
        }
    tokens = _tokens(text)
    contract = contracts[family]
    core_hits = _core_hits(tokens, contract.get("required_semantic_core") or [])
    positive_hits = _core_hits(tokens, contract.get("positive_cues") or [])
    exclusion = _exclusion_triggered(text, contract.get("exclusion_cues") or [], tokens)
    competitor_scores: list[tuple[str, int, list[str]]] = []
    for competitor in ACTIVE_FAMILY_VOCABULARY:
        if competitor == family:
            continue
        other = contracts[competitor]
        hits = _core_hits(tokens, other.get("required_semantic_core") or [])
        if hits:
            competitor_scores.append((competitor, len(hits), hits))
    competitor_scores.sort(key=lambda item: (-item[1], item[0]))
    reasons: list[str] = []
    if exclusion:
        reasons.append(f"exclusion_triggered:{exclusion}")
        return {
            "decision": "DROP",
            "family": family,
            "identity": identity,
            "reasons": reasons,
            "relabel_to": None,
            "text": text,
        }
    best_competitor = competitor_scores[0] if competitor_scores else None
    own_score = len(core_hits) * 2 + len(positive_hits)
    if best_competitor and best_competitor[1] >= 2 and len(core_hits) == 0:
        reasons.append(f"competitor_core:{best_competitor[0]}:{','.join(best_competitor[2])}")
        reasons.append("missing_gold_core")
        return {
            "decision": "RELABEL_CANDIDATE",
            "family": family,
            "identity": identity,
            "reasons": reasons,
            "relabel_to": best_competitor[0],
            "text": text,
        }
    if best_competitor and len(core_hits) >= 1 and best_competitor[1] >= 1:
        key = "||".join(sorted((family, best_competitor[0])))
        rule = pairwise_rules.get(key)
        shared = set((rule or {}).get("shared_semantics") or [])
        if shared & tokens and not (set((rule or {}).get("a_distinguishing_semantics") or []) & tokens) and not (
            set((rule or {}).get("b_distinguishing_semantics") or []) & tokens
        ):
            reasons.append("shared_semantics_without_distinguisher")
            return {
                "decision": "AMBIGUOUS",
                "family": family,
                "identity": identity,
                "reasons": reasons,
                "relabel_to": None,
                "text": text,
            }
        reasons.append("dual_core_hits")
        return {
            "decision": "AMBIGUOUS",
            "family": family,
            "identity": identity,
            "reasons": reasons,
            "relabel_to": None,
            "text": text,
        }
    if core_hits or (positive_hits and own_score >= 2):
        reasons.append("gold_core_or_positive_support")
        return {
            "decision": "KEEP",
            "family": family,
            "identity": identity,
            "reasons": reasons + [f"core:{','.join(core_hits)}" if core_hits else "positive_only"],
            "relabel_to": None,
            "text": text,
        }
    reasons.append("weak_boundary_evidence")
    # Phase-A sparse remediation must remain usable: do not demote weak-but-
    # non-colliding sparse positives below the sealed >=12 floor via REVIEW.
    if family in SPARSE_FOCUS:
        reasons.append("sparse_floor_keep_weak_evidence")
        return {
            "decision": "KEEP",
            "family": family,
            "identity": identity,
            "reasons": reasons,
            "relabel_to": None,
            "text": text,
        }
    return {
        "decision": "REVIEW",
        "family": family,
        "identity": identity,
        "reasons": reasons,
        "relabel_to": None,
        "text": text,
    }


def enforce_sparse_support_floor(
    classifications: Sequence[Mapping[str, Any]],
    *,
    floor: int = 12,
) -> list[dict[str, Any]]:
    """Promote weak flags back to KEEP so Phase-A sparse floors stay intact.

    Promotion order is REVIEW then AMBIGUOUS, lowest identity first. DROP and
    RELABEL_CANDIDATE are never promoted (noise audit stays sealed).
    """
    rows = [dict(row) for row in classifications]
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_family[str(row["family"])].append(row)
    for family in SPARSE_FOCUS:
        family_rows = by_family.get(family) or []
        keep_n = sum(1 for row in family_rows if row["decision"] == "KEEP")
        if keep_n >= floor:
            continue
        needed = floor - keep_n
        for status in ("REVIEW", "AMBIGUOUS"):
            if needed <= 0:
                break
            candidates = sorted(
                (row for row in family_rows if row["decision"] == status),
                key=lambda row: str(row["identity"]),
            )
            for row in candidates[:needed]:
                row["decision"] = "KEEP"
                reasons = list(row.get("reasons") or [])
                reasons.append(f"sparse_floor_promote_from_{status.lower()}")
                row["reasons"] = reasons
                needed -= 1
    return rows


def filter_keep_rows(
    family_rows: Mapping[str, Sequence[Mapping[str, Any]]],
    classifications: Sequence[Mapping[str, Any]],
) -> dict[str, list[Mapping[str, Any]]]:
    by_id = {row["identity"]: row for row in classifications}
    kept: dict[str, list[Mapping[str, Any]]] = {family: [] for family in ACTIVE_FAMILY_VOCABULARY}
    for family, rows in family_rows.items():
        for row in rows:
            identity = str(row["identity"])
            decision = by_id.get(identity, {}).get("decision")
            if decision == "KEEP":
                kept[family].append(row)
            elif decision == "RELABEL_CANDIDATE":
                # do not auto-relabel; exclude from gold-family keep set
                continue
            elif decision in {"DROP", "AMBIGUOUS", "REVIEW"}:
                continue
    return kept


def count_high_overlap_family_pairs(
    family_vectors: Mapping[str, Sequence[Sequence[float]]],
    *,
    threshold: float = HIGH_OVERLAP_COSINE,
) -> dict[str, Any]:
    """Count unordered family pairs whose max cross-member cosine is >= threshold."""
    families = [family for family in ACTIVE_FAMILY_VOCABULARY if family_vectors.get(family)]
    high_pairs = []
    for index, left in enumerate(families):
        left_u = [_unit(vector) for vector in family_vectors[left]]
        for right in families[index + 1 :]:
            right_u = [_unit(vector) for vector in family_vectors[right]]
            peak = max(
                (sum(a * b for a, b in zip(x, y)) for x in left_u for y in right_u),
                default=-1.0,
            )
            if peak >= threshold:
                high_pairs.append(
                    {
                        "cosine": float(peak),
                        "family_a": left,
                        "family_b": right,
                        "in_collapse_cluster": left in COLLAPSE_CLUSTER and right in COLLAPSE_CLUSTER,
                    }
                )
    collapse_pairs = [pair for pair in high_pairs if pair["in_collapse_cluster"]]
    # connected components inside collapse cluster using high pairs
    parent = {family: family for family in COLLAPSE_CLUSTER}

    def find(node: str) -> str:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(left: str, right: str) -> None:
        root_l, root_r = find(left), find(right)
        if root_l != root_r:
            parent[root_r] = root_l

    for pair in collapse_pairs:
        union(pair["family_a"], pair["family_b"])
    components: dict[str, list[str]] = defaultdict(list)
    for family in COLLAPSE_CLUSTER:
        if family_vectors.get(family):
            components[find(family)].append(family)
    largest = max((len(members) for members in components.values()), default=0)
    return {
        "collapse_high_overlap_pairs": len(collapse_pairs),
        "high_overlap_pairs": high_pairs,
        "high_overlap_pair_count": len(high_pairs),
        "largest_collapse_component": largest,
        "threshold": threshold,
    }


def training_gate_result(
    *,
    pre: Mapping[str, Any],
    post: Mapping[str, Any],
    support_post: Mapping[str, int],
) -> dict[str, Any]:
    pre_count = int(pre["high_overlap_pair_count"])
    post_count = int(post["high_overlap_pair_count"])
    if pre_count == 0:
        reduction = 1.0 if post_count == 0 else 0.0
    else:
        reduction = (pre_count - post_count) / pre_count
    zero_support = [family for family in ACTIVE_FAMILY_VOCABULARY if support_post.get(family, 0) < 1]
    sparse_ok = all(support_post.get(family, 0) >= 12 for family in SPARSE_FOCUS)
    collapse_pre = int(pre["largest_collapse_component"])
    collapse_post = int(post["largest_collapse_component"])
    collapse_weakened = collapse_post < collapse_pre or int(post["collapse_high_overlap_pairs"]) < int(
        pre["collapse_high_overlap_pairs"]
    )
    open_gate = (
        not zero_support
        and len(support_post) == len(ACTIVE_FAMILY_VOCABULARY)
        and all(support_post.get(family, 0) >= 1 for family in ACTIVE_FAMILY_VOCABULARY)
        and reduction >= MATERIAL_OVERLAP_REDUCTION
        and collapse_weakened
        and sparse_ok
    )
    return {
        "allow_best_move": False,
        "allow_encoder_training": open_gate,
        "allow_reserve_scoring": False,
        "collapse_component_pre": collapse_pre,
        "collapse_component_post": collapse_post,
        "collapse_weakened": collapse_weakened,
        "material_overlap_reduction_required": MATERIAL_OVERLAP_REDUCTION,
        "overlap_reduction": reduction,
        "pre_high_overlap_pairs": pre_count,
        "post_high_overlap_pairs": post_count,
        "sparse_support_preserved": sparse_ok,
        "training_gate": "OPEN" if open_gate else "CLOSED",
        "zero_support_families": zero_support,
    }


def assess_split_candidates(
    split_pairs: Sequence[Mapping[str, Any]],
    *,
    pre_pairs: Sequence[Mapping[str, Any]],
    post_pairs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    pre_set = {(row["family_a"], row["family_b"]) for row in pre_pairs} | {
        (row["family_b"], row["family_a"]) for row in pre_pairs
    }
    post_set = {(row["family_a"], row["family_b"]) for row in post_pairs} | {
        (row["family_b"], row["family_a"]) for row in post_pairs
    }
    out = []
    for pair in split_pairs:
        a = pair["family_a"]
        b = pair["family_b"]
        was_high = (a, b) in pre_set
        still_high = (a, b) in post_set
        if was_high and not still_high:
            status = "RESOLVED_BY_BOUNDARY_FILTER"
            future_split = False
            structural = False
        elif still_high:
            status = "OVERLAP_REMAINS_STRUCTURAL"
            future_split = True
            structural = True
        else:
            status = "NOT_HIGH_OVERLAP_PRE_OR_POST"
            future_split = False
            structural = False
        out.append(
            {
                "family_a": a,
                "family_b": b,
                "future_ontology_split_still_justified": future_split,
                "overlap_remains_structural": structural,
                "status": status,
                "split_performed": False,
            }
        )
    return out


def preserved_noise_classifications() -> list[dict[str, Any]]:
    """Emit the sealed Phase-A noise audit rows even when absent from the overlay."""
    rows = []
    for prefix, (decision, gold, relabel) in sorted(PRESERVED_NOISE.items()):
        rows.append(
            {
                "decision": decision,
                "family": gold,
                "identity": prefix,
                "reasons": ["preserved_phase_a_noise_audit"],
                "relabel_to": relabel,
                "text": None,
            }
        )
    return rows


def next_engineering_action(artifact: Mapping[str, Any]) -> str:
    gate = artifact.get("training_gate") or {}
    if gate.get("training_gate") == "OPEN":
        return (
            "BOUNDARY_REDEFINITION_CLEARED — run one clean classification-v2 training pass "
            "under the filtered KEEP set; do not score the reserve or move BEST until that "
            "run is sealed."
        )
    return (
        "BOUNDARY_OVERLAP_STILL_BLOCKS_TRAINING — inspect AMBIGUOUS/REVIEW/DROP row "
        "identities and unresolved SPLIT_CANDIDATE pairs; tighten mutually exclusive "
        "definitions before any v2 training run. Do not train, score the reserve, or move BEST."
    )


def assemble_boundary_redefinition(payload: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "family_contracts",
        "pairwise_rules",
        "row_classifications",
        "row_status_counts",
        "support_post",
        "overlap_pre",
        "overlap_post",
        "pair_overlap_table",
        "split_candidate_assessments",
        "training_gate",
    )
    for key in required:
        if key not in payload:
            raise ClassificationContractError("BOUNDARY_REDEFINITION_UNAVAILABLE", key)
    if set(payload["family_contracts"]) != set(ACTIVE_FAMILY_VOCABULARY):
        raise ClassificationContractError("BOUNDARY_REDEFINITION_UNAVAILABLE", "contracts")
    if len(payload["family_contracts"]) != 19:
        raise ClassificationContractError("BOUNDARY_REDEFINITION_UNAVAILABLE", "contract_count")
    contract = redefinition_contract()
    artifact = {
        "best_sha256": BEST_SHA,
        "boundary_redefinition_state": "SEALED",
        "boundary_sha256": BOUNDARY_SHA,
        "contract": contract,
        "encoder_updated": False,
        "family_contracts": {
            family: payload["family_contracts"][family] for family in ACTIVE_FAMILY_VOCABULARY
        },
        "historical_boundaries_mutated": False,
        "jev": "OFF",
        "material_overlap_reduction": MATERIAL_OVERLAP_REDUCTION,
        "moves_best": False,
        "mutates_ontology": False,
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
        "overlay_sha256": OVERLAY_SHA,
        "pair_overlap_table": payload["pair_overlap_table"],
        "pairwise_rules": payload["pairwise_rules"],
        "phase_d_audit_sha256": PHASE_D_AUDIT_SHA,
        "phase_execution_sha256": PHASE_EXECUTION_SHA,
        "phase_execution_rule": PHASE_EXECUTION_RULE,
        "preserved_noise_audit": PRESERVED_NOISE_COUNTS,
        "repair_primary_sha256": REPAIR_PRIMARY_SHA,
        "reserve_scored": False,
        "row_classifications": payload["row_classifications"],
        "row_status_counts": payload["row_status_counts"],
        "schema": REDEF_SCHEMA,
        "separation_sha256": SEPARATION_SHA,
        "sparse_support_post": {
            family: payload["support_post"].get(family, 0) for family in SPARSE_FOCUS
        },
        "split_candidate_assessments": payload["split_candidate_assessments"],
        "support_post": {
            family: payload["support_post"].get(family, 0) for family in ACTIVE_FAMILY_VOCABULARY
        },
        "train": False,
        "training_gate": payload["training_gate"],
    }
    artifact["overlap_reduction"] = payload["training_gate"].get("overlap_reduction")
    artifact["artifact_sha256"] = sha256_text(
        canonical_json({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    )
    return artifact
