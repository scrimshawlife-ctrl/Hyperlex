"""Moltbook-assimilated memetic memory helpers (additive; not on API_V1)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

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
        if "episodic" not in tiers:
            tiers.append("episodic")
    if "sigbus" in text_lower or "memory ledge" in text_lower or "concurrent" in text_lower or "wal" in text_lower:
        if "episodic" not in tiers:
            tiers.append("episodic")
    if "rented" in text_lower or "cognition" in text_lower or "export" in text_lower or "personality layer" in text_lower:
        if "episodic" not in tiers:
            tiers.append("episodic")
    if "kdr" in text_lower:
        if "episodic" not in tiers:
            tiers.append("episodic")

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
        from . import compute_virality_score

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
