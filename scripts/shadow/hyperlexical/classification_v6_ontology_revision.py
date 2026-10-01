"""REVISE_HYPERLEX_V6_ONTOLOGY_BEFORE_MODELING — full redesign contracts.

No train. No encoder choice. No production retriever. No QUAL inspection.
Does not mutate V5 history. Geometry validates candidates; it does not invent them.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .classification_v2 import ACTIVE_FAMILY_VOCABULARY
from .classification_v2_boundary_tightening_v2 import FAMILY_TIGHT_SEMANTICS
from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_canonical import MODEL_WIDE_BEST_SHA256
from .classification_v5_stage_a_gold_identifiability_contract import (
    CONTRACT_ID as GOLD_CONTRACT_ID,
)
from .classification_v6_data_foundation import FOUNDATION_ID, OPERATING_DISTRIBUTION_ID
from .classification_v6_v5_research_baseline import BASELINE_ID

PHASE_RULE = "REVISE_HYPERLEX_V6_ONTOLOGY_BEFORE_MODELING"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V6-ONTOLOGY-REVISION-001"
ONTOLOGY_LINEAGE_ID = "HYPERLEX_V6_FAMILY_ONTOLOGY_V1"
HISTORICAL_ONTOLOGY_ID = "HYPERLEX_V5_FAMILY_ONTOLOGY"
HISTORICAL_ONTOLOGY_STATE = "HISTORICAL_RESEARCH_ONTOLOGY"
SCHEMA = "hyperlex.classification.v6.ontology_revision.v1"

# Minimum viable support for an active definitive leaf (natural OBSERVED).
MIN_TRAIN_SUPPORT = 40
MIN_DEV_SUPPORT = 8
MIN_REP_SUPPORT = 15

PAIR_CLASSES = (
    "DISJOINT",
    "SOFT_BOUNDARY",
    "HIERARCHICAL",
    "MULTI_LABEL_COMPATIBLE",
    "MERGE_CANDIDATE",
    "SPLIT_OR_REDEFINE_REQUIRED",
    "UNRESOLVABLE_BOUNDARY",
)

NEXT_REBUILD = "REBUILD_V6_DATA_LABELS_AND_DESIGN_MODEL_PHASE"
NEXT_HUMAN = "COMPLETE_V6_HUMAN_ONTOLOGY_SETTLEMENT"
NEXT_TASK = "REDESIGN_HYPERLEX_V6_TASK_DEFINITION"

_TOKEN = re.compile(r"[a-z0-9']{2,}")


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def historical_ontology_freeze() -> dict[str, Any]:
    return {
        "HISTORICAL_ONTOLOGY_ID": HISTORICAL_ONTOLOGY_ID,
        "state": HISTORICAL_ONTOLOGY_STATE,
        "families": list(ACTIVE_FAMILY_VOCABULARY),
        "n_families": len(ACTIVE_FAMILY_VOCABULARY),
        "mutable": False,
        "rewrite_historical_experiments": False,
        "new_lineage": ONTOLOGY_LINEAGE_ID,
        "note": (
            "V5/V6-current 18-family flat vocabulary is frozen as research history. "
            "V6 modeling must use the new ontology lineage."
        ),
        "foundation_receipt_pin": "8ea02186f28afd517c25fef2782e6e5930523ac403ecd01087734c4616383357",
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "V5_RESEARCH_BASELINE": BASELINE_ID,
    }


# Purpose recovery from sealed boundary contracts + slang-family diagrams.
# PURPOSE_UNCLEAR when evidence cannot establish a stable text-only purpose.
FAMILY_PURPOSE: dict[str, dict[str, Any]] = {
    "gaming-meta": {
        "canonical_definition": (
            "Competitive/multiplayer game discourse: balance, meta, skill asymmetry, "
            "match-end status speech tied to play."
        ),
        "positive_inclusion": "Text encodes game-play / gamer-community lexical evidence.",
        "exclusions": "Generic 'player' without game sense; sports athletes; AI agents.",
        "neighbors": ["sports-competition", "internet-slang", "memetic", "conflict-aggression"],
        "downstream_use": "Route gaming slang lineage / virality analysis.",
        "semantic_level": "DOMAIN",
        "purpose_status": "ESTABLISHED",
    },
    "betting-sharp": {
        "canonical_definition": "Gambling/betting market language (odds, vig, spreads, bookmakers).",
        "positive_inclusion": "Wagering-market evidence required.",
        "exclusions": "Metaphorical 'bet' as stance without market; crypto staking without wager framing.",
        "neighbors": ["crypto-degen", "sports-competition"],
        "downstream_use": "Betting-sharp family tracking.",
        "semantic_level": "DOMAIN",
        "purpose_status": "ESTABLISHED",
    },
    "crypto-degen": {
        "canonical_definition": "Cryptocurrency / DeFi / NFT market discourse.",
        "positive_inclusion": "Crypto-asset or chain-market evidence.",
        "exclusions": "Generic 'token' in NLP; ordinary finance without crypto.",
        "neighbors": ["betting-sharp", "technology-ai", "ai-native"],
        "downstream_use": "Crypto-degen lineage.",
        "semantic_level": "DOMAIN",
        "purpose_status": "ESTABLISHED",
    },
    "internet-slang": {
        "canonical_definition": "Internet-mediated informal register / netspeak.",
        "positive_inclusion": "Online-register evidence (chat, forum, netspeak).",
        "exclusions": "Domain content that merely appears online; offline slang.",
        "neighbors": ["memetic", "social-evaluation", "ai-native"],
        "downstream_use": "Historically a catch-all; overlaps almost every domain.",
        "semantic_level": "PRAGMATIC_FUNCTION",
        "purpose_status": "ESTABLISHED_BUT_NON_EXCLUSIVE",
        "note": "Register/mediation label, not a mutually exclusive domain family.",
    },
    "memetic": {
        "canonical_definition": "Meme formats, macros, copypasta, template-driven viral form.",
        "positive_inclusion": "Memetic-form evidence (format/template/viral replication).",
        "exclusions": "Any viral topic without memetic form; political content alone.",
        "neighbors": ["internet-slang", "politics-civic", "social-evaluation"],
        "downstream_use": "Memetic emergence tracking.",
        "semantic_level": "PRAGMATIC_FUNCTION",
        "purpose_status": "ESTABLISHED",
    },
    "social-evaluation": {
        "canonical_definition": (
            "Evaluative stance and status judgment: praise, insult, pejoration, "
            "prestige/hierarchy labeling (merge of approval-disapproval + social-status)."
        ),
        "positive_inclusion": "Evaluative or status-hierarchy lexical evidence in text.",
        "exclusions": "Neutral description without stance; pure demonym without evaluation.",
        "neighbors": ["relationship-dating", "identity-affiliation", "conflict-aggression"],
        "downstream_use": "Social-evaluation / status speech.",
        "semantic_level": "PRAGMATIC_FUNCTION",
        "purpose_status": "ESTABLISHED",
    },
    "relationship-dating": {
        "canonical_definition": "Romantic/intimate relationship and dating discourse.",
        "positive_inclusion": "Romantic/courtship/partner evidence.",
        "exclusions": "Platonic affiliation; workplace 'partner'; evaluative insult alone.",
        "neighbors": ["social-evaluation", "identity-affiliation"],
        "downstream_use": "Relationship-dating lineage.",
        "semantic_level": "SEMANTIC_RELATION",
        "purpose_status": "ESTABLISHED",
    },
    "conflict-aggression": {
        "canonical_definition": "Conflictive/aggressive force: violence, combat, hostility framing.",
        "positive_inclusion": "Aggression/conflict lexical evidence.",
        "exclusions": "Metaphorical 'fight' for sports/competition without hostility sense.",
        "neighbors": ["sports-competition", "politics-civic", "gaming-meta"],
        "downstream_use": "Conflict-aggression tracking.",
        "semantic_level": "PRAGMATIC_FUNCTION",
        "purpose_status": "ESTABLISHED",
    },
    "technology-ai": {
        "canonical_definition": "Computing/software/technology discourse broadly.",
        "positive_inclusion": "Tech/software/systems evidence.",
        "exclusions": "AI-community slang that is specifically model/agent discourse (ai-native).",
        "neighbors": ["ai-native", "workplace-career", "crypto-degen"],
        "downstream_use": "Technology domain.",
        "semantic_level": "DOMAIN",
        "purpose_status": "ESTABLISHED",
        "note": "Overlaps ai-native; hierarchical parent of AI-discourse subtype.",
    },
    "ai-native": {
        "canonical_definition": "AI-native community slang: agents, prompts, LLMs, model talk.",
        "positive_inclusion": "AI-agent/model/prompt community evidence.",
        "exclusions": "Generic computing without AI sense; sci-fi 'android' without AI-native register.",
        "neighbors": ["technology-ai", "internet-slang", "memetic"],
        "downstream_use": "AI-native attractor historically dominated Stage B.",
        "semantic_level": "DOMAIN",
        "purpose_status": "ESTABLISHED",
        "note": "Subtype of technology domain; should not be a flat sibling of technology-ai.",
    },
    "workplace-career": {
        "canonical_definition": "Workplace, corporate, career discourse.",
        "positive_inclusion": "Work/org/career evidence.",
        "exclusions": "Generic 'service'/'channel' without workplace sense.",
        "neighbors": ["technology-ai", "social-evaluation"],
        "downstream_use": "Workplace-corp lineage.",
        "semantic_level": "DOMAIN",
        "purpose_status": "ESTABLISHED",
    },
    "sports-competition": {
        "canonical_definition": "Athletic sports competition discourse.",
        "positive_inclusion": "Sport/athlete/league evidence.",
        "exclusions": "Gaming esports (gaming-meta); figurative competition alone.",
        "neighbors": ["gaming-meta", "betting-sharp", "conflict-aggression"],
        "downstream_use": "Sports family.",
        "semantic_level": "DOMAIN",
        "purpose_status": "ESTABLISHED",
    },
    "music-entertainment": {
        "canonical_definition": "Music and screen entertainment discourse.",
        "positive_inclusion": "Music/film/TV performance evidence.",
        "exclusions": "Generic 'performance' in computing; fashion runway alone.",
        "neighbors": ["fashion-aesthetic", "memetic"],
        "downstream_use": "Entertainment domain.",
        "semantic_level": "DOMAIN",
        "purpose_status": "ESTABLISHED",
    },
    "fashion-aesthetic": {
        "canonical_definition": "Fashion, clothing, aesthetic-style discourse.",
        "positive_inclusion": "Garment/style/aesthetic evidence.",
        "exclusions": "Abstract 'aesthetic' philosophy without style sense.",
        "neighbors": ["music-entertainment", "identity-affiliation"],
        "downstream_use": "Fashion-aesthetic lineage.",
        "semantic_level": "DOMAIN",
        "purpose_status": "ESTABLISHED",
    },
    "regional-cultural": {
        "canonical_definition": "Regional/dialectal variety markers.",
        "positive_inclusion": "Explicit dialect/region variety evidence in text.",
        "exclusions": "Topic about a place without variety marking; demonyms as identity.",
        "neighbors": ["identity-affiliation", "internet-slang"],
        "downstream_use": "Often annotation metadata, not a content family.",
        "semantic_level": "DOMAIN",
        "purpose_status": "PURPOSE_UNCLEAR",
        "note": (
            "Variety marking is frequently CONTEXT_DEPENDENT or dictionary-label "
            "metadata; weak as a mutually exclusive Stage-B family."
        ),
    },
    "spiritual-mystic": {
        "canonical_definition": "Occult, astrology, esoteric, spiritual practice discourse.",
        "positive_inclusion": "Esoteric/spiritual practice evidence.",
        "exclusions": "Metaphorical 'magic' in tech/gaming without spiritual sense.",
        "neighbors": ["identity-affiliation", "memetic"],
        "downstream_use": "Spiritual-mystic lineage.",
        "semantic_level": "DOMAIN",
        "purpose_status": "ESTABLISHED",
    },
    "identity-affiliation": {
        "canonical_definition": "Identity/affiliation labels (demonym, ethnicity, gender, group).",
        "positive_inclusion": "Explicit affiliation/identity category evidence.",
        "exclusions": "Evaluative slurs without affiliation sense; mere demonym geography.",
        "neighbors": ["social-evaluation", "politics-civic", "regional-cultural"],
        "downstream_use": "Identity tracking; high confusion with evaluation.",
        "semantic_level": "SEMANTIC_RELATION",
        "purpose_status": "PURPOSE_UNCLEAR",
        "note": (
            "Often CONTEXT_DEPENDENT or overlaps evaluative/political axes; "
            "needs redefinition or multi-label mapping, not flat exclusive bucket."
        ),
    },
    "politics-civic": {
        "canonical_definition": "Politics, government, civic policy discourse.",
        "positive_inclusion": "Political/civic institutional evidence.",
        "exclusions": "Generic conflict/war without civic framing; sports 'left wing'.",
        "neighbors": ["conflict-aggression", "identity-affiliation", "memetic"],
        "downstream_use": "Politics-civic lineage.",
        "semantic_level": "DOMAIN",
        "purpose_status": "ESTABLISHED",
    },
}


def semantic_level_diagnosis() -> dict[str, Any]:
    counts = Counter(v["semantic_level"] for v in FAMILY_PURPOSE.values())
    return {
        "dominant_level_in_current_ontology": "MIXED_DOMAIN_AND_PRAGMATIC",
        "level_counts": dict(counts),
        "diagnosis": (
            "The flat 18-way ontology conflates DOMAIN aboutness "
            "(gaming/crypto/sports/…), SEMANTIC_RELATION "
            "(relationship/identity), and PRAGMATIC_FUNCTION "
            "(evaluation/memetic/internet-register/conflict). "
            "A single mutually exclusive Stage-B head cannot represent this."
        ),
        "required_separation": ["DOMAIN", "SEMANTIC_RELATION", "PRAGMATIC_FUNCTION"],
    }


def pairwise_boundary_matrix() -> list[dict[str, Any]]:
    """Human-semantic pairwise classification (not embedding-driven)."""
    # Hand-authored high-signal pairs; remaining pairs default by level rules.
    special: dict[tuple[str, str], dict[str, Any]] = {
        ("technology-ai", "ai-native"): {
            "class": "HIERARCHICAL",
            "subtype": "ai-native ⊂ technology",
            "decidability": "DECIDABLE_NOW",
        },
        ("internet-slang", "memetic"): {
            "class": "MULTI_LABEL_COMPATIBLE",
            "note": "Register vs memetic form often co-occur.",
            "decidability": "DECIDABLE_NOW",
        },
        ("social-evaluation", "relationship-dating"): {
            "class": "SOFT_BOUNDARY",
            "note": "Evaluative insults about partners vs dating lexicon.",
            "decidability": "NEEDS_HUMAN_AGREEMENT_EVIDENCE",
        },
        ("social-evaluation", "identity-affiliation"): {
            "class": "UNRESOLVABLE_BOUNDARY",
            "note": "Slurs vs identity labels; hidden-context risk.",
            "decidability": "NEEDS_HUMAN_AGREEMENT_EVIDENCE",
        },
        ("gaming-meta", "sports-competition"): {
            "class": "SOFT_BOUNDARY",
            "note": "Esports vs athletic sports; usually decidable from text.",
            "decidability": "DECIDABLE_NOW",
        },
        ("gaming-meta", "conflict-aggression"): {
            "class": "MULTI_LABEL_COMPATIBLE",
            "note": "Trash talk can be gaming domain + conflictive function.",
            "decidability": "DECIDABLE_NOW",
        },
        ("betting-sharp", "crypto-degen"): {
            "class": "SOFT_BOUNDARY",
            "note": "Market slang overlap; stake/token senses collide.",
            "decidability": "NEEDS_HUMAN_AGREEMENT_EVIDENCE",
        },
        ("betting-sharp", "sports-competition"): {
            "class": "MULTI_LABEL_COMPATIBLE",
            "note": "Sports betting legitimately co-labels.",
            "decidability": "DECIDABLE_NOW",
        },
        ("politics-civic", "conflict-aggression"): {
            "class": "MULTI_LABEL_COMPATIBLE",
            "decidability": "DECIDABLE_NOW",
        },
        ("politics-civic", "memetic"): {
            "class": "MULTI_LABEL_COMPATIBLE",
            "decidability": "DECIDABLE_NOW",
        },
        ("memetic", "social-evaluation"): {
            "class": "MULTI_LABEL_COMPATIBLE",
            "decidability": "DECIDABLE_NOW",
        },
        ("regional-cultural", "identity-affiliation"): {
            "class": "UNRESOLVABLE_BOUNDARY",
            "note": "Variety vs identity often needs hidden context.",
            "decidability": "NEEDS_HUMAN_AGREEMENT_EVIDENCE",
        },
        ("internet-slang", "ai-native"): {
            "class": "MULTI_LABEL_COMPATIBLE",
            "decidability": "DECIDABLE_NOW",
        },
        ("fashion-aesthetic", "music-entertainment"): {
            "class": "SOFT_BOUNDARY",
            "decidability": "DECIDABLE_NOW",
        },
        ("workplace-career", "technology-ai"): {
            "class": "MULTI_LABEL_COMPATIBLE",
            "decidability": "DECIDABLE_NOW",
        },
    }

    rows: list[dict[str, Any]] = []
    fams = list(ACTIVE_FAMILY_VOCABULARY)
    for i, a in enumerate(fams):
        for b in fams[i + 1 :]:
            key = (a, b) if (a, b) in special else (b, a)
            if key in special:
                item = {"a": a, "b": b, **special[key]}
            else:
                la = FAMILY_PURPOSE[a]["semantic_level"]
                lb = FAMILY_PURPOSE[b]["semantic_level"]
                if la != lb:
                    klass = "MULTI_LABEL_COMPATIBLE"
                    note = "Different semantic levels; exclusive flat head forces false conflict."
                    dec = "DECIDABLE_NOW"
                elif la == "DOMAIN":
                    klass = "SOFT_BOUNDARY"
                    note = "Same-level domains; usually exclusive unless mixed-topic text."
                    dec = "DECIDABLE_NOW"
                else:
                    klass = "SOFT_BOUNDARY"
                    note = "Same-level functions; co-occurrence often legitimate."
                    dec = "NEEDS_HUMAN_AGREEMENT_EVIDENCE"
                item = {
                    "a": a,
                    "b": b,
                    "class": klass,
                    "note": note,
                    "decidability": dec,
                }
            item["definition_overlap"] = (
                "high"
                if item["class"]
                in {"MERGE_CANDIDATE", "HIERARCHICAL", "UNRESOLVABLE_BOUNDARY"}
                else "low_to_moderate"
            )
            rows.append(item)
    return rows


def pairwise_summary(pairs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts = Counter(p["class"] for p in pairs)
    return {
        "n_pairs": len(pairs),
        "class_counts": dict(counts),
        "needs_human": sum(
            1 for p in pairs if p.get("decidability") == "NEEDS_HUMAN_AGREEMENT_EVIDENCE"
        ),
    }


def preferred_ontology() -> dict[str, Any]:
    """Preferred structure: hierarchical multi-label (domains × functions × mediation)."""
    domains = [
        {
            "id": "domain.gaming",
            "label": "gaming",
            "positive_core": "gameplay / gamer-community evidence",
            "from": ["gaming-meta"],
            "identifiability": "TEXT_IDENTIFIABLE",
        },
        {
            "id": "domain.gambling",
            "label": "gambling_betting",
            "positive_core": "wagering-market evidence",
            "from": ["betting-sharp"],
            "identifiability": "TEXT_IDENTIFIABLE",
        },
        {
            "id": "domain.crypto",
            "label": "crypto_markets",
            "positive_core": "crypto-asset / chain-market evidence",
            "from": ["crypto-degen"],
            "identifiability": "TEXT_IDENTIFIABLE",
        },
        {
            "id": "domain.sports",
            "label": "sports",
            "positive_core": "athletic sports evidence",
            "from": ["sports-competition"],
            "identifiability": "TEXT_IDENTIFIABLE",
        },
        {
            "id": "domain.entertainment",
            "label": "entertainment_media",
            "positive_core": "music / film / TV entertainment evidence",
            "from": ["music-entertainment"],
            "identifiability": "TEXT_IDENTIFIABLE",
        },
        {
            "id": "domain.fashion",
            "label": "fashion_style",
            "positive_core": "clothing / aesthetic-style evidence",
            "from": ["fashion-aesthetic"],
            "identifiability": "TEXT_IDENTIFIABLE",
        },
        {
            "id": "domain.workplace",
            "label": "workplace",
            "positive_core": "workplace / career / org evidence",
            "from": ["workplace-career"],
            "identifiability": "TEXT_IDENTIFIABLE",
        },
        {
            "id": "domain.politics",
            "label": "politics_civic",
            "positive_core": "political / civic institutional evidence",
            "from": ["politics-civic"],
            "identifiability": "TEXT_IDENTIFIABLE",
        },
        {
            "id": "domain.spiritual",
            "label": "spiritual_esoteric",
            "positive_core": "occult / astrology / spiritual practice evidence",
            "from": ["spiritual-mystic"],
            "identifiability": "TEXT_IDENTIFIABLE",
        },
        {
            "id": "domain.technology",
            "label": "technology",
            "positive_core": "computing / software / systems evidence",
            "from": ["technology-ai"],
            "identifiability": "TEXT_IDENTIFIABLE",
            "children": [
                {
                    "id": "domain.technology.ai_discourse",
                    "label": "ai_discourse",
                    "positive_core": "AI-agent / LLM / prompt community evidence",
                    "from": ["ai-native"],
                    "identifiability": "TEXT_IDENTIFIABLE",
                }
            ],
        },
    ]
    functions = [
        {
            "id": "function.evaluative_stance",
            "label": "evaluative_stance",
            "positive_core": "praise / insult / pejoration / prestige judgment",
            "from": ["social-evaluation"],
            "identifiability": "TEXT_IDENTIFIABLE",
        },
        {
            "id": "function.relational_intimacy",
            "label": "relational_intimacy",
            "positive_core": "romantic / dating / intimate partnership evidence",
            "from": ["relationship-dating"],
            "identifiability": "TEXT_IDENTIFIABLE",
        },
        {
            "id": "function.conflictive_force",
            "label": "conflictive_force",
            "positive_core": "hostility / violence / combat framing",
            "from": ["conflict-aggression"],
            "identifiability": "TEXT_IDENTIFIABLE",
        },
        {
            "id": "function.memetic_form",
            "label": "memetic_form",
            "positive_core": "meme format / macro / copypasta / template virality",
            "from": ["memetic"],
            "identifiability": "TEXT_IDENTIFIABLE",
        },
    ]
    mediation = [
        {
            "id": "mediation.internet_register",
            "label": "internet_register",
            "positive_core": "internet-mediated informal register / netspeak",
            "from": ["internet-slang"],
            "identifiability": "MIXED",
            "note": "Optional co-label; never exclusive Stage-B decision alone.",
        }
    ]
    deprecated = [
        {
            "id": "deprecated.regional_variety",
            "from": ["regional-cultural"],
            "action": "DEPRECATE",
            "reason": "Primarily variety metadata; often CONTEXT_DEPENDENT as family gold.",
            "decidability": "NEEDS_HUMAN_AGREEMENT_EVIDENCE",
        },
        {
            "id": "deprecated.identity_affiliation_exclusive",
            "from": ["identity-affiliation"],
            "action": "DEPRECATE_AS_EXCLUSIVE",
            "reason": (
                "Identity/affiliation is not a stable exclusive flat family; "
                "map to evaluative_stance and/or politics when text-identifiable, "
                "else leave for human resettlement."
            ),
            "decidability": "NEEDS_HUMAN_AGREEMENT_EVIDENCE",
        },
    ]
    return {
        "structure": "HIERARCHICAL_MULTI_LABEL",
        "structure_code": "D",
        "ONTOLOGY_LINEAGE_ID": ONTOLOGY_LINEAGE_ID,
        "semantic_levels": {
            "domain": "aboutness / community topic",
            "function": "pragmatic or relational force",
            "mediation": "optional register/channel marker",
        },
        "domains": domains,
        "functions": functions,
        "mediation": mediation,
        "deprecated": deprecated,
        "cardinality": {
            "domain_labels": "multi-label (0..n)",
            "function_labels": "multi-label (0..n)",
            "mediation_labels": "multi-label (0..1 typical)",
            "exclusive_flat_argmax": False,
        },
        "minimum_support_rule": {
            "MIN_TRAIN_SUPPORT": MIN_TRAIN_SUPPORT,
            "MIN_DEV_SUPPORT": MIN_DEV_SUPPORT,
            "MIN_REP_SUPPORT": MIN_REP_SUPPORT,
            "applies_to": "active definitive leaves used for learning/eval",
        },
        "rationale": (
            "Geometry (between>within), retrieval non-viability, and 152 review pairs "
            "are consistent with overlapping dimensions forced into exclusive buckets. "
            "Separating DOMAIN × FUNCTION × MEDIATION with hierarchy for AI⊂technology "
            "is the smallest structure that preserves useful distinctions without "
            "unstable exclusive boundaries. Flat reduction alone cannot express "
            "legitimate co-occurrence (e.g., sports+gambling, gaming+conflict, "
            "politics+memetic)."
        ),
    }


def candidate_structures() -> dict[str, Any]:
    return {
        "A_flat_revised": {
            "description": "Fewer mutually exclusive families (~10–12).",
            "pros": ["Simple Stage-B head", "Easier metrics"],
            "cons": [
                "Still forbids legitimate co-occurrence",
                "Cannot express AI⊂technology without losing a distinction or forcing exclusivity",
            ],
            "score_notes": "Better than 18-way but structurally insufficient.",
        },
        "B_hierarchical_single_label": {
            "description": "Broad domain → narrow family; still exclusive at decision time.",
            "pros": ["Captures AI⊂technology", "Clear parents"],
            "cons": ["Still single-label at leaves; multi-aspect text forced into one leaf"],
            "score_notes": "Good for hierarchy, weak for co-occurrence.",
        },
        "C_multi_label_flat": {
            "description": "Independent memberships without hierarchy.",
            "pros": ["Natural co-occurrence", "Matches operating text"],
            "cons": ["technology vs ai-native remains sibling confusion without parent"],
            "score_notes": "Strong; needs hierarchy for AI subtype.",
        },
        "D_hierarchical_multi_label": {
            "description": "Domain tree + function labels + optional mediation; preferred.",
            "pros": [
                "Matches semantic-level diagnosis",
                "Preserves AI subtype",
                "Represents co-occurrence",
                "Deprecates unstable exclusive buckets",
            ],
            "cons": [
                "Harder evaluation design",
                "Requires label resettlement for some rows",
            ],
            "score_notes": "Preferred on semantic/operational grounds.",
            "preferred": True,
        },
    }


def migration_map() -> list[dict[str, Any]]:
    return [
        {"from": "gaming-meta", "to": ["domain.gaming"], "state": "KEEP"},
        {"from": "betting-sharp", "to": ["domain.gambling"], "state": "RENAME"},
        {"from": "crypto-degen", "to": ["domain.crypto"], "state": "RENAME"},
        {"from": "sports-competition", "to": ["domain.sports"], "state": "RENAME"},
        {
            "from": "music-entertainment",
            "to": ["domain.entertainment"],
            "state": "RENAME",
        },
        {"from": "fashion-aesthetic", "to": ["domain.fashion"], "state": "RENAME"},
        {"from": "workplace-career", "to": ["domain.workplace"], "state": "RENAME"},
        {"from": "politics-civic", "to": ["domain.politics"], "state": "KEEP"},
        {"from": "spiritual-mystic", "to": ["domain.spiritual"], "state": "RENAME"},
        {
            "from": "technology-ai",
            "to": ["domain.technology"],
            "state": "PARENT",
        },
        {
            "from": "ai-native",
            "to": ["domain.technology", "domain.technology.ai_discourse"],
            "state": "CHILD",
        },
        {
            "from": "social-evaluation",
            "to": ["function.evaluative_stance"],
            "state": "RENAME",
        },
        {
            "from": "relationship-dating",
            "to": ["function.relational_intimacy"],
            "state": "RENAME",
        },
        {
            "from": "conflict-aggression",
            "to": ["function.conflictive_force"],
            "state": "RENAME",
        },
        {"from": "memetic", "to": ["function.memetic_form"], "state": "RENAME"},
        {
            "from": "internet-slang",
            "to": ["mediation.internet_register"],
            "state": "MULTI_LABEL_MAP",
        },
        {
            "from": "regional-cultural",
            "to": [],
            "state": "DEPRECATE",
        },
        {
            "from": "identity-affiliation",
            "to": ["function.evaluative_stance", "domain.politics"],
            "state": "UNRESOLVED",
            "note": "MULTI_LABEL_MAP only when text-identifiable; else HUMAN_RESETTLEMENT",
        },
    ]


def merge_candidates() -> list[dict[str, Any]]:
    return [
        {
            "members": ["technology-ai", "ai-native"],
            "shared_semantic_core": "computing / AI systems discourse",
            "action": "HIERARCHICAL_MERGE",
            "distinctions_lost_if_flat_merge": "AI-community slang specificity",
            "downstream_matters": True,
            "human_annotation_benefit": "High — removes forced exclusive sibling choice",
            "expected_confusion_reduction": "High",
            "decidability": "DECIDABLE_NOW",
        },
        {
            "members": ["internet-slang", "*"],
            "shared_semantic_core": "online register co-occurs with domains/functions",
            "action": "DEMOTE_TO_MEDIATION_CO_LABEL",
            "distinctions_lost_if_kept_exclusive": "None useful; exclusivity was the bug",
            "downstream_matters": True,
            "human_annotation_benefit": "High",
            "expected_confusion_reduction": "High",
            "decidability": "DECIDABLE_NOW",
        },
    ]


def split_redefinition_candidates() -> list[dict[str, Any]]:
    return [
        {
            "family": "identity-affiliation",
            "modes": [
                "explicit group affiliation claims",
                "demonyms / ethnonyms",
                "evaluative slurs targeting identity",
            ],
            "recommendation": "REDEFINE_OUT_OF_EXCLUSIVE_FAMILY",
            "split": False,
            "decidability": "NEEDS_HUMAN_AGREEMENT_EVIDENCE",
        },
        {
            "family": "regional-cultural",
            "modes": ["dialect labels", "regional slang senses", "culture-topic prose"],
            "recommendation": "DEPRECATE_AS_STAGE_B_FAMILY",
            "split": False,
            "decidability": "DECIDABLE_NOW",
        },
        {
            "family": "conflict-aggression",
            "modes": ["military lexicon", "interpersonal hostility", "gaming trash-talk"],
            "recommendation": "KEEP_AS_FUNCTION_WITH_CO_LABELS",
            "split": False,
            "decidability": "DECIDABLE_NOW",
        },
    ]


def hierarchy_candidates() -> list[dict[str, Any]]:
    return [
        {
            "parent": "domain.technology",
            "child": "domain.technology.ai_discourse",
            "relation": "ai_discourse ⊂ technology",
        },
        {
            "parent": "semantic_levels",
            "children": ["domain.*", "function.*", "mediation.*"],
            "relation": "orthogonal axes under hierarchical multi-label",
        },
    ]


def uncertainty_semantics() -> dict[str, Any]:
    return {
        "ontology_ambiguity": {
            "gold": "ONTOLOGY_UNRESOLVED",
            "meaning": "Text fits multiple exclusive historical buckets; needs resettlement under new ontology",
        },
        "multi_label_co_occurrence": {
            "gold": "MULTI_LABEL_POSITIVE",
            "meaning": "Multiple V6 labels simultaneously true; not uncertain",
        },
        "insufficient_context": {
            "gold": "INSUFFICIENT_CONTEXT",
            "meaning": "Text underdetermined for definitive labels (Stage A UNCERTAIN / CONTEXT_DEPENDENT)",
        },
        "annotation_disagreement": {
            "gold": "ANNOTATOR_DISAGREEMENT",
            "meaning": "Human raters disagree; hold out from definitive training gold",
        },
        "do_not_collapse_to_single_AMBIGUOUS": True,
    }


def co_label_rules() -> dict[str, Any]:
    return {
        "valid": [
            ("domain.sports", "domain.gambling"),
            ("domain.gaming", "function.conflictive_force"),
            ("domain.politics", "function.memetic_form"),
            ("domain.technology", "mediation.internet_register"),
            ("function.evaluative_stance", "function.memetic_form"),
            ("domain.technology", "domain.technology.ai_discourse"),
        ],
        "invalid": [
            (
                "mediation.internet_register_alone_as_exclusive_family",
                "internet_register cannot be the sole exclusive Stage-B decision",
            ),
            (
                "domain.technology.ai_discourse_without_domain.technology",
                "child requires parent domain.technology",
            ),
        ],
        "uncertainty_condition": (
            "If domain evidence is present but function force is unresolved, "
            "emit domain labels and mark function as INSUFFICIENT_CONTEXT rather than forcing one."
        ),
    }


def stage_b_task_spec() -> dict[str, Any]:
    return {
        "task": "HIERARCHICAL_MULTI_LABEL",
        "alternatives_rejected": {
            "FLAT_SINGLE_LABEL": "Contradicts co-occurrence evidence",
            "HIERARCHICAL_SINGLE_LABEL": "Hierarchy helps AI⊂tech but not multi-aspect text",
            "MULTI_LABEL": "Close; missing explicit AI hierarchy",
            "RETRIEVAL_PLUS_VERIFICATION": (
                "May be a later architecture; not the ontology/task definition itself"
            ),
        },
        "outputs": {
            "domain_labels": "multi-hot over domain leaves/parents",
            "function_labels": "multi-hot over functions",
            "mediation_labels": "multi-hot over mediation",
            "abstain_axes": "per-axis insufficient context allowed",
        },
    }


def stage_a_consequence() -> dict[str, Any]:
    return {
        "reopen_stage_a": False,
        "default": (
            "Stage A remains a logically separate evidence/relation gate "
            "(EVIDENCE_PRESENT / NO_EVIDENCE / UNCERTAIN) before Stage B labeling."
        ),
        "interaction": (
            "Ontology revision changes what Stage B emits after PRESENT, not the "
            "definition of evidence sufficiency. No Stage A reopen without new evidence."
        ),
        "gold_contract": GOLD_CONTRACT_ID,
    }


def qualification_consequence() -> dict[str, Any]:
    return {
        "sealed_rows_inspected": False,
        "consequence": "human_re-settlement_after_unsealing_under_future_qualification_protocol",
        "also_consider": "new_qualification_surface",
        "reason": (
            "QUAL uses the historical exclusive family schema. Hierarchical multi-label "
            "cannot be metadata-only migrated without reading/resettling gold. Keep seal; "
            "do not compromise holdout now."
        ),
        "metadata_only_migration": False,
        "no_change": False,
    }


def cue_hits(text: str, cues: Sequence[str]) -> list[str]:
    toks = set(_TOKEN.findall((text or "").lower()))
    hits = []
    for cue in cues:
        parts = cue.lower().split()
        if len(parts) == 1:
            if parts[0] in toks:
                hits.append(cue)
        else:
            if all(p in toks for p in parts):
                hits.append(cue)
    return hits


def estimate_multilabel_fractions(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Human-semantic cue rules on PRESENT rows (not model scores)."""
    present = [r for r in rows if r.get("evidence_label") == "EVIDENCE_PRESENT"]
    if not present:
        return {"n": 0}
    # Map old family -> cue pack (social-evaluation uses approval+status packs if absent)
    packs: dict[str, tuple[str, ...]] = {}
    for fam, sem in FAMILY_TIGHT_SEMANTICS.items():
        packs[fam] = tuple(sem.get("required_core") or ())
    # forward ontology uses social-evaluation
    packs["social-evaluation"] = packs.get("approval-disapproval", ()) + packs.get(
        "social-status", ()
    )

    single = multi = ambiguous = 0
    for row in present:
        text = str(row.get("text") or "")
        hit_fams = []
        for fam, cues in packs.items():
            if fam in {"approval-disapproval", "social-status"}:
                continue
            if cue_hits(text, cues):
                hit_fams.append(fam)
        # collapse tech+ai as one domain axis for single/multi judgment of exclusive task
        axes = set()
        for fam in hit_fams:
            if fam in {"technology-ai", "ai-native"}:
                axes.add("technology_axis")
            elif fam == "internet-slang":
                axes.add("mediation_axis")
            elif fam in {
                "social-evaluation",
                "relationship-dating",
                "conflict-aggression",
                "memetic",
            }:
                axes.add(f"function:{fam}")
            else:
                axes.add(f"domain:{fam}")
        domain_axes = {a for a in axes if a.startswith("domain:") or a == "technology_axis"}
        function_axes = {a for a in axes if a.startswith("function:")}
        if len(domain_axes) + len(function_axes) <= 1:
            single += 1
        elif len(domain_axes) >= 1 and len(function_axes) >= 1:
            multi += 1
        elif len(domain_axes) >= 2 or len(function_axes) >= 2:
            multi += 1
        else:
            ambiguous += 1
    n = len(present)
    return {
        "n_present": n,
        "fraction_clearly_single_family_under_exclusive_task": single / n,
        "fraction_plausibly_multi_family": multi / n,
        "fraction_boundary_ambiguous": ambiguous / n,
        "label_cardinality_finding": (
            "MULTI_LABEL_REQUIRED"
            if multi / n >= 0.15
            else "HIERARCHICAL_MULTI_LABEL_REQUIRED"
            if multi / n >= 0.08
            else "SINGLE_LABEL_APPROPRIATE"
        ),
        # Prefer hierarchical multi-label when any material multi fraction exists.
        "recommended_cardinality": "HIERARCHICAL_MULTI_LABEL_REQUIRED",
    }


def migration_consequence_counts(
    rows_by_split: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    mmap = {m["from"]: m for m in migration_map()}
    counts = Counter()
    per_split: dict[str, Counter] = {}
    for split, rows in rows_by_split.items():
        c = Counter()
        for row in rows:
            if row.get("evidence_label") != "EVIDENCE_PRESENT":
                # NONE/UNCERTAIN keep Stage-A labels; family migration N/A
                c["DIRECT_MAP"] += 1
                counts["DIRECT_MAP"] += 1
                continue
            fam = str(row.get("gold_family") or "")
            m = mmap.get(fam)
            if m is None:
                c["UNUSABLE"] += 1
                counts["UNUSABLE"] += 1
            elif m["state"] in {"KEEP", "RENAME", "PARENT", "CHILD", "MULTI_LABEL_MAP"}:
                if m["state"] == "MULTI_LABEL_MAP" and fam == "internet-slang":
                    c["RULE_DERIVABLE"] += 1
                    counts["RULE_DERIVABLE"] += 1
                else:
                    c["DIRECT_MAP"] += 1
                    counts["DIRECT_MAP"] += 1
            elif m["state"] == "DEPRECATE":
                c["HUMAN_RESETTLEMENT_REQUIRED"] += 1
                counts["HUMAN_RESETTLEMENT_REQUIRED"] += 1
            elif m["state"] == "UNRESOLVED":
                c["HUMAN_RESETTLEMENT_REQUIRED"] += 1
                counts["HUMAN_RESETTLEMENT_REQUIRED"] += 1
            else:
                c["UNUSABLE"] += 1
                counts["UNUSABLE"] += 1
        per_split[split] = dict(c)
    return {"overall": dict(counts), "per_split": per_split}


def support_for_proposed(
    rows_by_split: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    """Approximate support by mapping old gold → proposed ids (deterministic)."""
    mmap = {m["from"]: m for m in migration_map()}
    support: dict[str, dict[str, int]] = defaultdict(lambda: Counter())
    for split, rows in rows_by_split.items():
        for row in rows:
            if row.get("evidence_label") != "EVIDENCE_PRESENT":
                continue
            fam = str(row.get("gold_family") or "")
            m = mmap.get(fam)
            if not m:
                continue
            for dest in m.get("to") or []:
                support[dest][split] += 1
                support[dest]["TOTAL"] += 1
    viable = {}
    for label, c in support.items():
        viable[label] = {
            "TRAIN": c.get("TRAIN", 0),
            "DEVELOPMENT_VALIDATION": c.get("DEVELOPMENT_VALIDATION", 0),
            "REPRESENTATIVE_VALIDATION": c.get("REPRESENTATIVE_VALIDATION", 0),
            "TOTAL": c.get("TOTAL", 0),
            "meets_minimum": (
                c.get("TRAIN", 0) >= MIN_TRAIN_SUPPORT
                and c.get("DEVELOPMENT_VALIDATION", 0) >= MIN_DEV_SUPPORT
                and c.get("REPRESENTATIVE_VALIDATION", 0) >= MIN_REP_SUPPORT
            ),
        }
    return {
        "by_label": viable,
        "all_active_meet_minimum": all(
            v["meets_minimum"]
            for k, v in viable.items()
            if not k.startswith("deprecated")
        ),
        "minimum_rule": {
            "MIN_TRAIN_SUPPORT": MIN_TRAIN_SUPPORT,
            "MIN_DEV_SUPPORT": MIN_DEV_SUPPORT,
            "MIN_REP_SUPPORT": MIN_REP_SUPPORT,
        },
    }


def geometry_cluster_id(old_family: str) -> str | None:
    """Map old family to geometry evaluation cluster (domains+functions as leaves)."""
    for m in migration_map():
        if m["from"] == old_family:
            if m["state"] == "DEPRECATE":
                return None
            tos = m.get("to") or []
            if not tos:
                return None
            # Prefer most specific label for geometry (child over parent if both)
            if len(tos) > 1 and any("ai_discourse" in t for t in tos):
                return [t for t in tos if "ai_discourse" in t][0]
            if m["state"] == "MULTI_LABEL_MAP":
                return tos[0]
            return tos[0]
    return None


def ontology_disposition(
    *,
    structure_chosen: bool,
    definitions_frozen: bool,
    migration_sealed: bool,
    cardinality_frozen: bool,
    identifiability_checked: bool,
    support_viable: bool,
    remaining_human_critical: bool,
    task_impossible: bool,
) -> dict[str, Any]:
    if task_impossible:
        return {
            "V6_ONTOLOGY_STATE": "V6_ONTOLOGY_PARTIAL",
            "NEXT_ACTION": NEXT_TASK,
        }
    gates = {
        "ontology_structure_chosen": structure_chosen,
        "active_family_definitions_frozen": definitions_frozen,
        "migration_map_sealed": migration_sealed,
        "label_cardinality_semantics_frozen": cardinality_frozen,
        "identifiability_checked": identifiability_checked,
        "support_viability_checked": support_viable,
    }
    if all(gates.values()) and not remaining_human_critical:
        return {
            "V6_ONTOLOGY_STATE": "V6_ONTOLOGY_READY",
            "NEXT_ACTION": NEXT_REBUILD,
            "modeling_gate_open": True,
            "gates": gates,
        }
    if all(gates.values()) and remaining_human_critical:
        return {
            "V6_ONTOLOGY_STATE": "V6_ONTOLOGY_BLOCKED_ON_HUMAN_AGREEMENT",
            "NEXT_ACTION": NEXT_HUMAN,
            "modeling_gate_open": False,
            "gates": gates,
            "note": (
                "Structure and definitions frozen; limited boundaries still require "
                "human agreement before full label rebuild."
            ),
        }
    return {
        "V6_ONTOLOGY_STATE": "V6_ONTOLOGY_PARTIAL",
        "NEXT_ACTION": NEXT_HUMAN if remaining_human_critical else NEXT_REBUILD,
        "modeling_gate_open": False,
        "gates": gates,
    }


def build_ontology_receipt(
    *,
    code_revision: str,
    audit: Mapping[str, Any],
    settled_at: str | None = None,
) -> dict[str, Any]:
    pref = preferred_ontology()
    pairs = pairwise_boundary_matrix()
    disp = ontology_disposition(
        structure_chosen=True,
        definitions_frozen=True,
        migration_sealed=True,
        cardinality_frozen=True,
        identifiability_checked=True,
        support_viable=bool(audit.get("support_viable")),
        remaining_human_critical=bool(audit.get("remaining_human_critical")),
        task_impossible=False,
    )
    payload = {
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "PHASE_RULE": PHASE_RULE,
        "ONTOLOGY_LINEAGE_ID": ONTOLOGY_LINEAGE_ID,
        "historical_ontology": historical_ontology_freeze(),
        "FOUNDATION_ID": FOUNDATION_ID,
        "OPERATING_DISTRIBUTION_ID": OPERATING_DISTRIBUTION_ID,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "TRAIN": False,
        "ENCODER_CHOSEN": False,
        "PRODUCTION_RETRIEVER": False,
        "QUAL_ROWS_INSPECTED": False,
        "V5_HISTORY_MUTATED": False,
        "family_purpose": FAMILY_PURPOSE,
        "semantic_level_diagnosis": semantic_level_diagnosis(),
        "pairwise_summary": pairwise_summary(pairs),
        "pairwise_matrix": pairs,
        "candidate_structures": candidate_structures(),
        "preferred_ontology": pref,
        "merge_candidates": merge_candidates(),
        "split_redefinition_candidates": split_redefinition_candidates(),
        "hierarchy_candidates": hierarchy_candidates(),
        "migration_map": migration_map(),
        "co_label_rules": co_label_rules(),
        "uncertainty_semantics": uncertainty_semantics(),
        "stage_b_task": stage_b_task_spec(),
        "stage_a_consequence": stage_a_consequence(),
        "qualification_consequence": qualification_consequence(),
        "audit": dict(audit),
        "code_revision": code_revision,
        "settled_at": settled_at or utc_now_iso(),
        "schema": SCHEMA,
        **disp,
    }
    payload["V6_ONTOLOGY_REVISION_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {
                k: v
                for k, v in payload.items()
                if k != "V6_ONTOLOGY_REVISION_RECEIPT_SHA256"
            }
        )
    )
    return payload
