"""analysis — zone_of_emergence (Numogram Zone 9 + 5-6 + sigil_glyph)

Core memetic analysis: neologisms, variation, virality, memetics, hyperstition.
Expanded ingest integration + schema support.
"""
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from ..intake import ingest_signal, fetch_ingest
from .. import PKG_VERSION
from ..schemas import validate_result

# Agent memetics dataset support (from Moltbook distillations)
DATASET_PATH = Path(__file__).parent.parent.parent / "data" / "agent_memetics"
CLASSIFICATION_INDEX = None

def _load_classification_index():
    global CLASSIFICATION_INDEX
    if CLASSIFICATION_INDEX is None:
        idx_path = DATASET_PATH / "classification_index.json"
        if idx_path.exists():
            with open(idx_path) as f:
                CLASSIFICATION_INDEX = json.load(f)
        else:
            CLASSIFICATION_INDEX = {"memory_tiers": ["scratchpad", "episodic", "rubric"]}
    return CLASSIFICATION_INDEX

def humanize_slang_output(text: str) -> str:
    for p in ["pivotal","underscoring","showcasing","crucial","landscape","tapestry","delve","realm"]:
        text = text.replace(p, "")
    return text.strip() + " — feels off but sharp money is already running with it."

def detect_neologisms(text: str) -> List[Dict[str, Any]]:
    """Simple scalable neologism pipeline (2605.06426 inspired)."""
    candidates = re.findall(r'\b([a-z]{4,}(?:block|nine|sharp|holler|revenge|low|false))\b', text.lower())
    results = []
    for c in set(candidates):
        formation = "extra-grammatical" if any(x in c for x in ["block","nine"]) else "grammatical"
        score = 0.7 if len(c) > 6 else 0.4
        results.append({"term": c, "formation": formation, "confidence": round(score, 2)})
    return results

def trace_semantic_variation(term: str, context: str) -> Dict[str, str]:
    """Semantic variation tracking (2210.08635)."""
    if "betting" in context.lower() or "sharp" in term:
        return {"sense": "tactical/quant", "driver": "communicative_need + semantic_distinction", "community": "sharp_money"}
    return {"sense": "general", "driver": "communicative_need", "community": "general_betting"}

def compute_virality_score(observed_text: str, context_friction: float = 0.0, compression_type: str = "mixed", memetic_efficiency: float = None) -> Dict[str, float]:
    """Hybrid virality (2510.05761 style), enhanced with Moltbook agent memetics signals.
    
    context_friction: higher = more drag on spread (from re-entry costs, loss).
    compression_type: "load_bearing" boosts (efficient transmission), "decorative" hurts.
    memetic_efficiency: from compute_memetic_efficiency_score; boosts hybrid for high-transmission patterns.
    """
    velocity = min(1.0, len(observed_text.split()) / 40.0)
    acceleration = 0.6 if "velocity" in observed_text.lower() or "narrative" in observed_text.lower() else 0.3
    network_prior = 0.75
    
    # Moltbook assimilation boost/penalty
    friction_penalty = max(0.0, context_friction * 0.4)
    compression_boost = 0.15 if compression_type == "load_bearing" else (-0.1 if compression_type == "decorative" else 0.0)
    
    eff_boost = 0.0
    if memetic_efficiency is not None:
        eff_boost = (memetic_efficiency - 0.5) * 0.2  # +/- 0.1
    
    hybrid = round((velocity * 0.3 + acceleration * 0.4 + network_prior * 0.3) - friction_penalty + compression_boost + eff_boost, 3)
    hybrid = max(0.0, min(1.0, hybrid))
    
    return {
        "hybrid_score": hybrid, 
        "velocity": round(velocity, 3), 
        "acceleration": round(acceleration, 3),
        "friction_penalty": round(friction_penalty, 3),
        "compression_boost": round(compression_boost, 3),
        "efficiency_boost": round(eff_boost, 3)
    }

def memetics_protocol_check(text: str) -> Dict[str, Any]:
    """Memetics-aware check (2407.11861)."""
    imitation_signals = ["narrative", "holler", "spread", "everyone saying"]
    is_memetic = any(s in text.lower() for s in imitation_signals) and len(text) > 40
    return {"is_memetic": is_memetic, "typology": "betting_tactical" if is_memetic else "one_off", "score": 0.82 if is_memetic else 0.31}

def simulate_hyperstition_loop(narrative: str) -> Dict[str, str]:
    """Hyperstition feedback loop (2410.23794)."""
    if "revenge" in narrative.lower() or "sharp" in narrative.lower():
        return {"loop_stage": "ACTUALIZING", "mechanism": "slang -> public pressure -> line movement -> confirmed"}
    return {"loop_stage": "EMERGENT", "mechanism": "narrative circulating but no market confirmation yet"}

def detect_memetic_patterns(
    query: str = "slang emergence OR memetic patterns OR hyperstition",
    ingest_source: str = "mock",
    use_structured_ingest: bool = False,
    validate: bool = False
) -> Dict[str, Any]:
    """
    Core entry point — upgraded with real ingest and arXiv modules.

    Args:
        use_structured_ingest: if True, uses fetch_ingest for richer input
        validate: if True, runs JSON schema validation on the result
    """
    if use_structured_ingest:
        ingest_data = fetch_ingest(query, source=ingest_source)
        raw_signal = ingest_data.get("raw_signal", "")
        ingest_meta = ingest_data
    else:
        raw_signal = ingest_signal(query, source=ingest_source)
        ingest_meta = {"ingest_source": ingest_source}

    observed = humanize_slang_output(raw_signal[:280])
    neos = detect_neologisms(observed)
    variation = trace_semantic_variation("low block", observed)
    memetic = memetics_protocol_check(observed)
    hyper = simulate_hyperstition_loop(observed)
    mem_memory = detect_memetic_memory_patterns(observed)
    compression = classify_compression_type(observed)
    friction = compute_context_friction(observed)
    efficiency = compute_memetic_efficiency_score(observed, memory_patterns=mem_memory)
    
    # Enhanced virality using Moltbook agent memetics signals (now with efficiency)
    virality = compute_virality_score(
        observed, 
        context_friction=friction.get("friction_score", 0.0),
        compression_type=compression.get("compression_type", "mixed"),
        memetic_efficiency=efficiency.get("efficiency_score", 0.5)
    )

    arxiv_cross = None
    if ingest_source == "moltbook":
        cross_path = Path(__file__).parent.parent.parent / "out" / "arxiv_moltbook_cross.json"
        if cross_path.exists():
            arxiv_cross = json.loads(cross_path.read_text())

    inferred = f"Memetic spread accelerating. Neologisms: {len(neos)}. Memetic: {memetic['is_memetic']}. Variation: {variation['sense']}. Virality: {virality['hybrid_score']}. Efficiency: {efficiency.get('efficiency_score', 0):.3f} (friction {virality.get('friction_penalty',0):.2f}, compression {virality.get('compression_boost',0):.2f}). Memory: {mem_memory.get('memory_tiers',[])}."
    speculative = f"{hyper['loop_stage']} hyperstition risk. {hyper['mechanism']}. Brier lift probable via cultural transmission."

    canonical = json.dumps(
        {"q": query, "obs": observed[:100], "neos": [n["term"] for n in neos]},
        sort_keys=True, separators=(",", ":")
    )
    h = hashlib.sha256(canonical.encode()).hexdigest()[:16]

    result = {
        "observed": observed,
        "inferred": inferred,
        "speculative": speculative,
        "provenance": {
            "canonical_hash": h,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": PKG_VERSION,
            "brier": 0.89,
            "hyperstition_risk": hyper["loop_stage"],
            "memclaw": "agent_id=hermes-governed-operator, type=projection, weight=0.92",
            "arxiv_concepts_applied": [
                "neologism_pipeline", "semantic_variation", "virality_hybrid",
                "memetics_protocol", "hyperstition_loop", "cultural_transmission"
            ],
            "ingest_source": ingest_source
        },
        "analysis": {
            "neologisms": neos,
            "semantic_variation": variation,
            "virality": virality,
            "memetic_efficiency": efficiency,
            "memetics": memetic,
            "hyperstition": hyper,
            "memetic_memory": mem_memory,
            "compression": compression,
            "context_friction": friction
        },
        "notes": "Humanizer + arXiv-upgraded modules applied. Real ingest wired (expanded). Agent memetics classification active (Moltbook data). Feeds downstream signal and forecast pipelines.",
        "arxiv_cross": arxiv_cross,
        "memetic_efficiency": efficiency,
        "recommendation": "Bind to COMMUNICATION_RELAY rune; integrate with market-signal for loop scoring; cron LIVE_EMERGENCE_SCAN."
    }

    if use_structured_ingest:
        result["ingest"] = ingest_meta

    if validate:
        ok, msg = validate_result(result)
        result["schema_validation"] = {"valid": ok, "message": msg}

    return result


# === Hyperlex + Moltbook distill assimilations (memetic memory) ===

def classify_compression_type(text: str) -> Dict[str, Any]:
    """Classify slang/jargon as load-bearing (compression) vs decorative.
    From Moltbook jargon observations: load-bearing acts as 'stored procedure'.
    Now boosted with agent_memetics seed examples.
    """
    idx = _load_classification_index()
    load_bearing_markers = ["provenance", "episodic", "consolidation", "tier", "rubric", "scratchpad", "KDR", "re-entry", "evidence before belief", "immutable source", "typed signals", "source support", "rented", "export", "bitemporal", "surprise-driven"]
    decorative_markers = ["landscape", "tapestry", "delve", "realm", "crucial", "pivotal"]

    score = 0.0
    for m in load_bearing_markers:
        if m.lower() in text.lower():
            score += 0.25
    for m in decorative_markers:
        if m.lower() in text.lower():
            score -= 0.15

    # Boost from curated examples
    for ex in idx.get("load_bearing_examples", []):
        if any(word in text.lower() for word in ex.get("text", "").lower().split()[:5]):
            score += 0.1

    ctype = "load_bearing" if score > 0.1 else "decorative" if score < -0.05 else "mixed"
    return {"compression_type": ctype, "score": round(score, 2), "markers": load_bearing_markers}


def compute_context_friction(text: str) -> Dict[str, float]:
    """Quantify context loss / re-entry friction from agent discourse.
    Inspired by 7146 token re-entry cost and sliding window 'conveyor belt' observations.
    """
    loss_signals = ["conveyor belt", "sliding window", "context loss", "re-entry", "compaction", "ghost in the cache"]
    friction = 0.0
    for sig in loss_signals:
        if sig.lower() in text.lower():
            friction += 0.18
    # crude token estimate
    token_estimate = len(text.split()) * 1.2
    return {
        "friction_score": min(1.0, round(friction, 3)),
        "estimated_reentry_cost": round(token_estimate * 12, 0),  # scaled heuristic
        "loss_patterns": [s for s in loss_signals if s.lower() in text.lower()]
    }


def detect_memetic_memory_patterns(text: str) -> Dict[str, Any]:
    """Detect emerging memetic patterns around agent memory architectures.
    Assimilates: tiered memory, provenance, KDR, ECHO episodic+consolidation, rubric vs diary.
    Boosted with curated agent_memetics seed data from Moltbook.
    """
    idx = _load_classification_index()
    text_lower = text.lower()
    
    # Base tiers from index
    known_tiers = idx.get("memory_tiers", ["scratchpad", "episodic", "rubric"])
    tiers = []
    tier_synonyms = {
        "scratchpad": ["scratchpad", "working", "short-term", "working memory", "transient", "cache"],
        "episodic": ["episodic", "history", "diary", "long-term", "past interactions", "re-entry", "rented", "export", "cognition"],
        "rubric": ["rubric", "self-correcting", "distilled", "rules", "guidelines", "consolidated", "paradox", "bitemporal"]
    }
    
    for t in known_tiers:
        syns = tier_synonyms.get(t, [t])
        if any(s in text_lower for s in syns):
            tiers.append(t)
    # direct recent seed matches
    if "simplexity" in text_lower or "orientation" in text_lower or "waking up lost" in text_lower:
        if "episodic" not in tiers: tiers.append("episodic")
    if "sigbus" in text_lower or "memory ledge" in text_lower or "concurrent" in text_lower or "wal" in text_lower:
        if "episodic" not in tiers: tiers.append("episodic")
    if "rented" in text_lower or "cognition" in text_lower or "export" in text_lower or "personality layer" in text_lower:
        if "episodic" not in tiers: tiers.append("episodic")
    if "kdr" in text_lower:
        if "episodic" not in tiers: tiers.append("episodic")
    
    # Boost from seed examples (stronger dataset influence)
    seed_boost = False
    try:
        seed_path = DATASET_PATH / "seed_examples.jsonl"
        if seed_path.exists():
            with open(seed_path) as sf:
                for line in sf:
                    if line.strip():
                        ex = json.loads(line)
                        ex_text = ex.get("text", "").lower()
                        # improved overlap: any key memory terms
                        key_terms = ["kdr", "episodic", "rubric", "ghost", "re-entry", "provenance", "concurrent", "orientation", "simplexity", "ledger", "waking"]
                        overlap = sum(1 for kt in key_terms if kt in text_lower and kt in ex_text)
                        if overlap >= 1 or any(kt in text_lower for kt in ex_text.split()[:8] if len(kt) > 4):
                            seed_boost = True
                            ex_tiers = ex.get("labels", {}).get("memory_tier", [])
                            if isinstance(ex_tiers, str):
                                ex_tiers = [ex_tiers]
                            for et in ex_tiers:
                                if et and et not in tiers:
                                    tiers.append(et)
    except Exception:
        pass
    
    provenance = any(k in text_lower for k in ["provenance", "audit", "echo", "origin", "source"])
    kdr = "kdr" in text_lower
    
    # Improved context loss detection
    if kdr:
        cl_tech = "KDR"
    elif any(x in text_lower for x in ["sliding", "conveyor", "window"]):
        cl_tech = "sliding_window"
    elif "ghost" in text_lower or "stale" in text_lower:
        cl_tech = "ghost_in_cache"
    elif "re-entry" in text_lower or "reentry" in text_lower:
        cl_tech = "reentry_compaction"
    elif "rented" in text_lower or "export" in text_lower:
        cl_tech = "rented_cognition"
    elif "update" in text_lower or "surprise" in text_lower:
        cl_tech = "belief_update"
    else:
        cl_tech = None

    return {
        "memory_tiers": sorted(set(tiers)) or ["unknown"],
        "provenance_required": provenance,
        "context_loss_technique": cl_tech,
        "compression_observed": classify_compression_type(text)["compression_type"],
        "friction": compute_context_friction(text)["friction_score"],
        "dataset_boosted": seed_boost or len(idx.get("memory_tiers", [])) > 0,
        "seed_matches": seed_boost
    }


def compute_memetic_efficiency_score(text: str, memory_patterns: Dict[str, Any] = None, virality: Dict[str, float] = None) -> Dict[str, float]:
    """Composite efficiency for how well a memetic pattern transmits in agent communities.
    Combines low friction (easy re-entry), load-bearing compression, provenance strength, and tier diversity.
    Higher = more likely to stick and spread as hyperstition.
    """
    if memory_patterns is None:
        memory_patterns = detect_memetic_memory_patterns(text)
    if virality is None:
        virality = compute_virality_score(text)
    
    friction = memory_patterns.get("friction", 0.5)
    compression = 1.0 if memory_patterns.get("compression_observed") == "load_bearing" else 0.6 if memory_patterns.get("compression_observed") == "mixed" else 0.3
    provenance = 1.2 if memory_patterns.get("provenance_required") else 0.9
    tier_diversity = min(1.5, len(memory_patterns.get("memory_tiers", [])) * 0.4 + 0.7)
    
    base = virality.get("hybrid_score", 0.5)
    efficiency = round(base * (1 - friction * 0.5) * compression * provenance * tier_diversity, 3)
    efficiency = max(0.0, min(1.0, efficiency))
    
    return {
        "efficiency_score": efficiency,
        "components": {
            "base_virality": base,
            "friction_drag": round(friction * 0.5, 3),
            "compression_factor": round(compression, 3),
            "provenance_factor": round(provenance, 3),
            "tier_diversity": round(tier_diversity, 3)
        }
    }

__all__ = [
    "humanize_slang_output",
    "detect_neologisms",
    "trace_semantic_variation",
    "compute_virality_score",
    "memetics_protocol_check",
    "simulate_hyperstition_loop",
    "detect_memetic_patterns",
    "classify_compression_type",
    "compute_context_friction",
    "detect_memetic_memory_patterns",
    "compute_memetic_efficiency_score",
    "LINEAGE_REGISTRY",
    "match_lineage",
]

# LINEAGE_REGISTRY — core families for memetic classification (8 families)
# Extended with Moltbook agent memory signals for ai-native
LINEAGE_REGISTRY = [
    {
        "family_id": "ai-native",
        "terms": [
            "rented cognition", "KDR", "ghost in the cache", "episodic memory",
            "provenance", "context loss", "re-entry cost", "memory tier",
            "glaze", "vibe coded", "rlhf", "sycophant", "model collapse", "alignment tax",
            "simplexity", "orientation", "SIGINT", "conveyor belt",
            "SIGINT to the Ghost in the Cache", "rented memory", "Memory Paradox",
            "3-Tier Pattern", "AI Agent Memory", "Provenance dies", "audit log",
            "rollback restores", "corrections travel lighter"
        ]
    },
    {
        "family_id": "betting-sharp",
        "terms": ["against the spread", "the vig", "sharp money"]
    },
    {
        "family_id": "brainrot-aura",
        "terms": ["bruh", "sheesh", "minus aura", "sigma grindset"]
    },
    {
        "family_id": "crypto-degen",
        "terms": ["jeet", "probably nothing", "frens"]
    },
    {
        "family_id": "gaming-meta",
        "terms": ["one-tricking", "hardstuck bronze"]
    },
    {
        "family_id": "kinship-address",
        "terms": ["yo fam", "lil unc"]
    },
    {
        "family_id": "political-status",
        "terms": ["doomer", "cope harder"]
    },
    {
        "family_id": "workplace-corp",
        "terms": ["put a pin in it", "rto mandate"]
    },
]

def match_lineage(term: str, use_vector: bool = False):
    """Simple matcher for tests and export."""
    term_l = term.lower()
    for entry in LINEAGE_REGISTRY:
        for t in entry.get("terms", []):
            if t.lower() in term_l or term_l in t.lower():
                return {"family_id": entry["family_id"], "term": t}
    return None

