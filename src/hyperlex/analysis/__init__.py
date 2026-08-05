"""analysis — zone_of_emergence (Numogram Zone 9 + 5-6 + sigil_glyph)

Core memetic analysis: neologisms, variation, virality, memetics, hyperstition.
Expanded ingest integration + schema support + lineage matching with confidence scoring.

Brier scores are NOT emitted here. Use hyperlex.calibration after settlement.
"""
import re
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from ..intake import ingest_signal, fetch_ingest
from .. import PKG_VERSION
from ..schemas import validate_result
from ..provenance import analysis_canonical_hash

# ---------------------------------------------------------------------------
# Lineage registry (static seed; expand via docs/examples/slang-families)
# ---------------------------------------------------------------------------

LINEAGE_REGISTRY: List[Dict[str, Any]] = [
    {
        "family_id": "betting-sharp",
        "terms": ["sharp", "steam", "square", "wiseguy", "hammer", "holler", "revenge", "low block", "false nine"],
        "branch_operator": "sense_extension",
        "diagram_ref": "examples/slang-families/betting-sharp-family.mmd",
        "payload_note": "professional edge vs public money; line-physics signaling",
    },
    {
        "family_id": "crypto-degen",
        "terms": ["hodl", "diamond hands", "paper hands", "rekt", "ape", "degen", "moon", "bagholder", "fud", "fomo", "ngmi", "wagmi", "rug"],
        "branch_operator": "cross_family_borrowing",
        "diagram_ref": "examples/slang-families/crypto-degen-family.mmd",
        "payload_note": "conviction under volatility; risk identity as honorific",
    },
    {
        "family_id": "ai-native",
        "terms": [
            "hallucinate", "slop", "clanker", "agentic", "glazing", "skill issue",
            "token", "context window", "vibe coding",
        ],
        "branch_operator": "platform_compression",
        "diagram_ref": "examples/slang-families/ai-native-family.mmd",
        "payload_note": "machine language as culture; quality judgment + hostility + agency framing",
    },
    {
        "family_id": "brainrot-aura",
        "terms": [
            # core (pre-2026 trunk)
            "brainrot", "brain rot", "aura", "aura farming", "mid", "cooked", "let him cook",
            # 2026 YTD leaves (see data/backfill/2026/)
            "rizz", "skibidi", "gyatt", "sigma", "delulu", "no cap", "locked in", "crash out",
            "mewing", "looksmaxxing", "mog", "mogging", "ate", "left no crumbs", "it's giving",
            "npc", "main character", "main character energy", "fanum tax", "ohio",
            "bussin", "slay", "six seven", "67", "edging", "gooning",
            "vibe check", "negative aura", "aura points", "yap", "yapping", "chat is this real",
        ],
        "branch_operator": "irony_inversion",
        "diagram_ref": "examples/slang-families/brainrot-aura-family.mmd",
        "payload_note": "content-degradation + status radiation; self-aware consumption; 2026 Gen Alpha carryover",
    },
    {
        "family_id": "kinship-address",
        "terms": ["bro", "sis", "twin", "unc", "cuz", "family"],
        "branch_operator": "sense_extension",
        "diagram_ref": "examples/slang-families/kinship-address.mmd",
        "payload_note": "fictive kinship; community responsibility + platform acceleration",
    },
    {
        "family_id": "political-status",
        "terms": ["based", "redpilled", "blackpilled", "cope", "seethe", "dilate"],
        "branch_operator": "irony_inversion",
        "diagram_ref": "examples/slang-families/political-status-family.mmd",
        "payload_note": "tribal signaling + emotional routing; high mutation rate",
    },
    {
        "family_id": "gaming-meta",
        "terms": [
            "nerf", "buff", "meta", "sweaty", "noob", "gg", "ez", "ratio",
            "touch grass", "skill issue", "diff", "int", "feed", "smurf", "sus",
        ],
        "branch_operator": "platform_compression",
        "diagram_ref": "examples/slang-families/gaming-meta-family.mmd",
        "payload_note": "competitive balance + status in multiplayer; meta as living rule-set",
    },
    {
        "family_id": "workplace-corp",
        "terms": [
            "quiet quitting", "quiet firing", "rto", "return to office", "layoffs",
            "pip", "synergy", "circle back", "bandwidth", "low-hanging fruit",
            "act your wage",
        ],
        "branch_operator": "sense_extension",
        "diagram_ref": "examples/slang-families/workplace-corp-family.mmd",
        "payload_note": "labor identity under corporate speech; resistance + managerial cant",
    },
]

LINEAGE_CONFIDENCE_THRESHOLD = 0.42


def _term_weight(term: str) -> float:
    t = term.strip().lower()
    n_words = max(1, len(t.split()))
    weight = 0.22 + 0.14 * n_words + 0.025 * min(len(t), 24)
    return min(0.75, weight)


def _find_hits(corpus: str, family_terms: List[str]) -> List[str]:
    hits: List[str] = []
    for term in family_terms:
        t = term.lower()
        if " " in t:
            if t in corpus:
                hits.append(term)
        else:
            if re.search(rf"\b{re.escape(t)}\b", corpus):
                hits.append(term)
    return hits


def compute_lineage_confidence(
    hits: List[str],
    family_terms: List[str],
    corpus: str,
) -> Tuple[float, Dict[str, Any]]:
    if not hits:
        return 0.0, {"n_hits": 0}

    weights = [_term_weight(t) for t in hits]
    specificity = sum(weights) / len(weights)
    coverage = len(hits) / max(len(family_terms), 1)

    hit_bonus = 0.0
    for i in range(len(hits)):
        hit_bonus += max(0.04, 0.12 - 0.02 * i)
    hit_bonus = min(0.38, hit_bonus)

    density = 0.0
    if len(hits) >= 2:
        length_factor = max(0.0, 1.0 - (len(corpus) / 600.0))
        density = min(0.18, 0.06 * (len(hits) - 1) * (0.5 + 0.5 * length_factor))

    raw = 0.18 + specificity * 0.38 + coverage * 0.22 + hit_bonus + density
    confidence = min(0.98, max(0.0, raw))

    breakdown = {
        "n_hits": len(hits),
        "specificity": round(specificity, 3),
        "coverage": round(coverage, 3),
        "hit_bonus": round(hit_bonus, 3),
        "density": round(density, 3),
        "raw": round(raw, 3),
        "term_weights": {t: round(_term_weight(t), 3) for t in hits},
    }
    return confidence, breakdown


def _vector_family_boosts(
    query_text: str,
    *,
    top_k: int = 8,
    min_score: float = 0.12,
) -> Tuple[Dict[str, float], List[Dict[str, Any]]]:
    """
    Aggregate cosine neighbor mass by family_id from local vector DB.

    Fail-open: empty boosts if DB missing or disabled.
    """
    import os
    from pathlib import Path as _Path

    vflag = str(os.environ.get("HYPERLEX_VECTOR", "auto")).strip().lower()
    if vflag in {"0", "false", "off", "no"}:
        return {}, []
    try:
        from ..vectordb import default_vector_db_path, vector_search

        vpath = default_vector_db_path()
        want = vflag in {"1", "true", "yes", "on"} or (
            vflag in {"", "auto"} and _Path(vpath).is_file() and _Path(vpath).stat().st_size > 0
        )
        if not want:
            return {}, []
        vs = vector_search(query_text, kind="term", top_k=top_k, min_score=min_score)
        if not vs.get("ok"):
            return {}, []
        hits = list(vs.get("hits") or [])
        boosts: Dict[str, float] = {}
        for h in hits:
            fam = h.get("family_id")
            if not fam:
                continue
            # weight by cosine score, diminishing by rank
            sc = float(h.get("score") or 0.0)
            boosts[str(fam)] = boosts.get(str(fam), 0.0) + sc
        # normalize boost mass into [0, VECTOR_BOOST_CAP]
        if boosts:
            mx = max(boosts.values()) or 1.0
            for k in list(boosts.keys()):
                # scale so strongest family gets up to VECTOR_BOOST_CAP
                boosts[k] = VECTOR_BOOST_CAP * (boosts[k] / mx)
        return boosts, hits
    except Exception:
        return {}, []


# Max confidence points added from vector evidence (hybrid re-rank)
VECTOR_BOOST_CAP = 0.12
# Candidates within this gap of lexical best may be flipped by vector
VECTOR_FLIP_MARGIN = 0.08


def match_lineage(
    text: str,
    terms: Optional[List[str]] = None,
    min_confidence: float = LINEAGE_CONFIDENCE_THRESHOLD,
    registry: Optional[List[Dict[str, Any]]] = None,
    *,
    use_vector: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    """Match text to a lineage family.

    ``registry`` optionally overrides ``LINEAGE_REGISTRY`` (e.g. backfill merge).
    When a local vector DB is available (or HYPERLEX_VECTOR=1), applies a hybrid
    re-rank: lexical confidence + small family boost from term neighbors.

    Historical receipts are never mutated by this function. Not Brier.
    """
    import os

    corpus = (text or "").lower()
    if terms:
        corpus = corpus + " " + " ".join(t.lower() for t in terms)

    entries = registry if registry is not None else LINEAGE_REGISTRY
    candidates: List[Dict[str, Any]] = []

    for entry in entries:
        family_terms = list(entry.get("terms") or [])
        hits = _find_hits(corpus, family_terms)
        if not hits:
            continue

        score, breakdown = compute_lineage_confidence(hits, family_terms, corpus)
        # keep near-misses for hybrid (slightly below threshold)
        if score < min_confidence - 0.06:
            continue

        candidates.append({
            "family_id": entry["family_id"],
            "matched_terms": hits,
            "branch_operator": entry.get("branch_operator", "unknown"),
            "lexical_confidence": round(score, 3),
            "diagram_ref": entry.get("diagram_ref"),
            "payload_note": entry.get("payload_note"),
            "score_breakdown": breakdown,
            "entry": entry,
        })

    if not candidates:
        return None

    vflag = str(os.environ.get("HYPERLEX_VECTOR", "auto")).strip().lower()
    if use_vector is None:
        use_vector = vflag not in {"0", "false", "off", "no"}

    vector_boosts: Dict[str, float] = {}
    vector_hits: List[Dict[str, Any]] = []
    hybrid_applied = False
    if use_vector:
        q = corpus.strip()
        vector_boosts, vector_hits = _vector_family_boosts(q)
        hybrid_applied = bool(vector_boosts)

    for c in candidates:
        boost = float(vector_boosts.get(c["family_id"], 0.0)) if hybrid_applied else 0.0
        hybrid = min(0.98, float(c["lexical_confidence"]) + boost)
        c["vector_boost"] = round(boost, 4)
        c["hybrid_confidence"] = round(hybrid, 3)
        # eligibility: hybrid must clear threshold (lexical near-miss can be rescued)
        c["eligible"] = hybrid >= min_confidence

    eligible = [c for c in candidates if c["eligible"]]
    if not eligible:
        return None

    # rank by hybrid, then lexical
    eligible.sort(
        key=lambda c: (c["hybrid_confidence"], c["lexical_confidence"]),
        reverse=True,
    )
    best_c = eligible[0]
    lexical_best = max(candidates, key=lambda c: c["lexical_confidence"])
    flipped = (
        hybrid_applied
        and best_c["family_id"] != lexical_best["family_id"]
        and (best_c["hybrid_confidence"] - lexical_best["lexical_confidence"]) >= -VECTOR_FLIP_MARGIN
    )

    result = {
        "family_id": best_c["family_id"],
        "matched_terms": best_c["matched_terms"],
        "branch_operator": best_c["branch_operator"],
        "confidence": best_c["hybrid_confidence"],
        "diagram_ref": best_c["diagram_ref"],
        "payload_note": best_c["payload_note"],
        "provenance": "INFERRED",
        "score_breakdown": {
            **best_c["score_breakdown"],
            "lexical_confidence": best_c["lexical_confidence"],
            "vector_boost": best_c["vector_boost"],
            "hybrid_confidence": best_c["hybrid_confidence"],
            "hybrid_applied": hybrid_applied,
            "vector_flipped": bool(flipped),
        },
    }
    if hybrid_applied:
        result["hybrid"] = {
            "schema": "hyperlex.lineage_hybrid.v1",
            "lexical_family": lexical_best["family_id"],
            "lexical_confidence": lexical_best["lexical_confidence"],
            "vector_boosts": {k: round(v, 4) for k, v in sorted(vector_boosts.items(), key=lambda kv: -kv[1])[:6]},
            "vector_top_hits": [
                {"text": h.get("text"), "family_id": h.get("family_id"), "score": h.get("score")}
                for h in vector_hits[:5]
            ],
            "selected_family": best_c["family_id"],
            "flipped": bool(flipped),
            "brier": None,
            "note": "Hybrid = lexical confidence + capped vector family boost; not Brier.",
        }
    return result


def humanize_slang_output(text: str) -> str:
    """Strip AI-ism tokens without injecting domain slang (preserves lineage purity)."""
    for p in ["pivotal", "underscoring", "showcasing", "crucial", "landscape", "tapestry", "delve", "realm"]:
        text = text.replace(p, "")
    cleaned = " ".join(text.split()).strip()
    return cleaned


def detect_neologisms(text: str) -> List[Dict[str, Any]]:
    """Rule-based neologism candidates (no LLM). Multi-word + formation tags."""
    corpus = (text or "").lower()
    results: List[Dict[str, Any]] = []
    seen = set()

    # multi-word tactical / identity phrases
    multi = re.findall(
        r"\b((?:sharp money|diamond hands|paper hands|false nine|low block|"
        r"aura farming|skill issue|context window|organic velocity|line movement|"
        r"locked in|crash out|left no crumbs|main character energy|fanum tax|"
        r"six seven|vibe check|vibe coding|aura points|negative aura|chat is this real|"
        r"it's giving|no cap|looksmaxxing|touch grass|quiet quitting|act your wage))\b",
        corpus,
    )
    for phrase in multi:
        if phrase in seen:
            continue
        seen.add(phrase)
        results.append({
            "term": phrase,
            "formation": "compound_phrase",
            "confidence": 0.78,
            "provenance": "INFERRED",
        })

    # known single-token 2026 / slang stems (word-boundary)
    for tok in (
        "rizz", "skibidi", "gyatt", "sigma", "delulu", "mewing", "mog", "mogging",
        "bussin", "gooning", "yap", "yapping", "npc", "slay", "ohio", "edging",
    ):
        if re.search(rf"\b{re.escape(tok)}\b", corpus) and tok not in seen:
            seen.add(tok)
            results.append({
                "term": tok,
                "formation": "platform_compression",
                "confidence": 0.72,
                "provenance": "INFERRED",
            })

    # single-token morphological / slang stems
    candidates = re.findall(
        r"\b([a-z]{3,}(?:block|nine|sharp|holler|revenge|degen|slop|aura|pilled|rot))\b",
        corpus,
    )
    for c in candidates:
        if c in seen:
            continue
        seen.add(c)
        if any(x in c for x in ("block", "nine")):
            formation = "extra-grammatical"
        elif c.endswith("pilled") or c.endswith("rot"):
            formation = "derivational"
        else:
            formation = "grammatical"
        score = 0.7 if len(c) > 6 else 0.45
        results.append({
            "term": c,
            "formation": formation,
            "confidence": round(score, 2),
            "provenance": "INFERRED",
        })
    return results


# Community drivers (arXiv semantic-variation inspired labels)
COMMUNITY_DRIVERS = (
    "communicative_need",
    "semantic_distinction",
    "community_identity",
    "platform_compression",
    "status_competition",
    "risk_signaling",
)


def trace_semantic_variation(
    term: str,
    context: str,
    *,
    lineage_family: Optional[str] = None,
    typology: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Sense + driver tags for semantic variation.

    Drivers are multi-label INFERRED cues, not exclusive.
    """
    ctx = (context or "").lower()
    term_l = (term or "").lower()
    drivers: List[str] = []

    if any(k in ctx for k in ("sharp", "steam", "betting", "line", "clv")) or "sharp" in term_l:
        sense = "tactical/quant"
        community = "sharp_money"
        drivers.extend(["communicative_need", "semantic_distinction"])
    elif any(k in ctx for k in ("degen", "hodl", "rekt", "moon")):
        sense = "risk/conviction"
        community = "crypto_degen"
        drivers.extend(["community_identity", "risk_signaling"])
    elif any(k in ctx for k in ("agentic", "slop", "hallucin", "clanker", "token")):
        sense = "machine-culture"
        community = "ai_native"
        drivers.extend(["platform_compression", "semantic_distinction"])
    elif any(k in ctx for k in ("aura", "mid", "based", "brainrot")):
        sense = "status/irony"
        community = "status_publics"
        drivers.extend(["status_competition", "community_identity"])
    elif any(k in ctx for k in ("bro", "sis", "twin", "unc", "family")):
        sense = "kinship-address"
        community = "fictive_kin"
        drivers.extend(["community_identity", "communicative_need"])
    else:
        sense = "general"
        community = "general"
        drivers.append("communicative_need")

    # Lineage / typology soft tags
    if lineage_family:
        drivers.append("community_identity")
    if typology in ("platform_agency",):
        drivers.append("platform_compression")
    if typology in ("risk_identity",):
        drivers.append("risk_signaling")
    if typology in ("status_radiation", "irony_inversion"):
        drivers.append("status_competition")

    # dedupe preserve order
    seen_d = []
    for d in drivers:
        if d in COMMUNITY_DRIVERS and d not in seen_d:
            seen_d.append(d)

    return {
        "sense": sense,
        "driver": " + ".join(seen_d) if seen_d else "communicative_need",
        "drivers": seen_d,
        "community": community,
        "lineage_family": lineage_family,
        "provenance": "INFERRED",
    }


def compute_virality_score(observed_text: str) -> Dict[str, Any]:
    """Descriptive hybrid virality features (not a future prediction)."""
    velocity = min(1.0, len(observed_text.split()) / 40.0)
    acceleration = 0.6 if "velocity" in observed_text.lower() or "narrative" in observed_text.lower() else 0.3
    # keyword boosts for coordination / spread language
    spread_cues = sum(
        1 for k in ("spread", "steam", "coordinated", "organic", "everyone", "viral")
        if k in observed_text.lower()
    )
    acceleration = min(1.0, acceleration + 0.08 * spread_cues)
    network_prior = 0.75
    hybrid = round((velocity * 0.3 + acceleration * 0.4 + network_prior * 0.3), 3)
    return {
        "hybrid_score": hybrid,
        "velocity": round(velocity, 3),
        "acceleration": round(acceleration, 3),
        "spread_cues": spread_cues,
    }


def predict_virality(
    *,
    hybrid_score: float,
    velocity: float,
    acceleration: float,
    lineage_confidence: Optional[float] = None,
    hyperstition_stage: Optional[str] = None,
    memetic_score: Optional[float] = None,
    n_neologisms: int = 0,
    horizon: str = "short",
) -> Dict[str, Any]:
    """
    Weak predictive estimate of near-term virality from current features.

    Pure function. Does NOT emit Brier and is not a settled forecast.
    Label: SPECULATIVE (forward-looking) with method transparency.
    """
    h = max(0.0, min(1.0, float(hybrid_score)))
    v = max(0.0, min(1.0, float(velocity)))
    a = max(0.0, min(1.0, float(acceleration)))
    lc = float(lineage_confidence) if isinstance(lineage_confidence, (int, float)) else 0.0
    ms = float(memetic_score) if isinstance(memetic_score, (int, float)) else 0.0
    stage = str(hyperstition_stage or "").upper()
    stage_boost = 0.12 if stage == "ACTUALIZING" else (0.04 if stage == "EMERGENT" else 0.0)
    neo_boost = min(0.1, 0.03 * max(0, int(n_neologisms)))

    # Weighted blend: descriptive hybrid dominates; lineage/memetic/stage nudge
    predicted = (
        h * 0.50
        + v * 0.12
        + a * 0.18
        + min(1.0, lc) * 0.10
        + min(1.0, ms) * 0.05
        + stage_boost
        + neo_boost
    )
    predicted = round(max(0.0, min(0.98, predicted)), 3)

    # Confidence in the *prediction itself* (not outcome Brier)
    conf = 0.35 + 0.15 * (1 if lc >= 0.42 else 0) + 0.1 * (1 if stage == "ACTUALIZING" else 0)
    conf = round(min(0.75, conf + 0.05 * min(3, n_neologisms)), 3)

    delta = round(predicted - h, 3)
    return {
        "predicted_hybrid": predicted,
        "baseline_hybrid": h,
        "delta_vs_baseline": delta,
        "horizon": horizon,
        "confidence": conf,
        "method": "feature_blend_v0",
        "features_used": {
            "hybrid_score": h,
            "velocity": v,
            "acceleration": a,
            "lineage_confidence": lc or None,
            "memetic_score": ms or None,
            "hyperstition_stage": stage or None,
            "n_neologisms": n_neologisms,
        },
        "provenance": "SPECULATIVE",
        "note": "Not a settled forecast; do not treat as Brier-eligible without settlement design.",
    }


# Deterministic memetic typology rules (additive; primary = highest score).
# Labels are INFERRED from lexical cues — not OBSERVED ground truth.
TYPOLOGY_RULES: List[Dict[str, Any]] = [
    {
        "id": "tactical_edge",
        "cues": ["sharp", "steam", "square", "wiseguy", "hammer", "clv", "juice", "vig", "line move", "revenge"],
        "weight": 1.0,
        "note": "professional edge / line-physics signaling",
    },
    {
        "id": "risk_identity",
        "cues": ["degen", "hodl", "rekt", "diamond hands", "paper hands", "ape", "moon", "rug", "ngmi", "wagmi"],
        "weight": 1.0,
        "note": "risk/conviction identity under volatility",
    },
    {
        "id": "platform_agency",
        "cues": [
            "agentic", "slop", "hallucin", "clanker", "context window", "skill issue",
            "token", "glazing", "nerf", "buff", "meta", "sweaty", "smurf", "diff",
        ],
        "weight": 1.0,
        "note": "machine language as culture / quality + agency framing / game-meta",
    },
    {
        "id": "labor_identity",
        "cues": [
            "quiet quitting", "quiet firing", "rto", "return to office", "layoffs",
            "bandwidth", "circle back", "act your wage", "synergy", "pip",
        ],
        "weight": 0.95,
        "note": "workplace / corporate speech + labor resistance",
    },
    {
        "id": "status_radiation",
        "cues": ["aura", "aura farming", "based", "mid", "cooked", "let him cook", "glazing"],
        "weight": 0.95,
        "note": "status radiation / quality judgment",
    },
    {
        "id": "irony_inversion",
        "cues": ["brainrot", "brain rot", "cope", "seethe", "dilate", "redpill", "blackpill"],
        "weight": 0.95,
        "note": "irony inversion + emotional routing",
    },
    {
        "id": "kinship_address",
        "cues": [" bro ", " sis ", "twin", " unc ", " cuz ", "family"],
        "weight": 0.9,
        "note": "fictive kinship address",
    },
    {
        "id": "imitation_spread",
        "cues": ["narrative", "holler", "spread", "everyone saying", "organic velocity", "coordinated"],
        "weight": 0.75,
        "note": "generic imitation / spread cues",
    },
]

# Lineage family → preferred typology (soft prior when cues tied)
LINEAGE_TYPOLOGY = {
    "betting-sharp": "tactical_edge",
    "crypto-degen": "risk_identity",
    "ai-native": "platform_agency",
    "brainrot-aura": "status_radiation",
    "kinship-address": "kinship_address",
    "political-status": "irony_inversion",
    "gaming-meta": "platform_agency",
    "workplace-corp": "status_radiation",
}


def memetics_protocol_check(
    text: str,
    *,
    lineage_family: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Rule-based memetic typology with transparent cue hits.

    Returns primary typology, per-type scores, and rules_hit for audit.
    """
    corpus = f" {(text or '').lower()} "
    scores: Dict[str, float] = {}
    hits: Dict[str, List[str]] = {}

    for rule in TYPOLOGY_RULES:
        matched = [c.strip() for c in rule["cues"] if c.lower() in corpus]
        if not matched:
            continue
        # score = weight * diminishing hits
        raw = float(rule["weight"]) * min(1.0, 0.35 + 0.2 * len(matched))
        scores[rule["id"]] = round(raw, 3)
        hits[rule["id"]] = matched

    # Soft prior from lineage family when present
    if lineage_family and lineage_family in LINEAGE_TYPOLOGY:
        pref = LINEAGE_TYPOLOGY[lineage_family]
        scores[pref] = round(scores.get(pref, 0.0) + 0.15, 3)
        hits.setdefault(pref, []).append(f"lineage:{lineage_family}")

    if not scores:
        return {
            "is_memetic": False,
            "typology": "one_off",
            "typology_scores": {},
            "rules_hit": {},
            "score": 0.31,
            "provenance": "INFERRED",
        }

    primary = max(scores.items(), key=lambda kv: kv[1])[0]
    top = scores[primary]
    is_memetic = top >= 0.45 or len(scores) >= 2
    # Map legacy alias for back-compat consumers
    legacy = "betting_tactical" if primary == "tactical_edge" and is_memetic else primary

    return {
        "is_memetic": is_memetic,
        "typology": legacy if primary == "tactical_edge" else primary,
        "typology_primary": primary,
        "typology_scores": dict(sorted(scores.items(), key=lambda kv: -kv[1])),
        "rules_hit": hits,
        "score": round(min(0.95, 0.4 + top * 0.5), 2) if is_memetic else 0.31,
        "provenance": "INFERRED",
    }


def simulate_hyperstition_loop(narrative: str) -> Dict[str, str]:
    if "revenge" in narrative.lower() or "sharp" in narrative.lower():
        return {"loop_stage": "ACTUALIZING", "mechanism": "slang -> public pressure -> line movement -> confirmed"}
    return {"loop_stage": "EMERGENT", "mechanism": "narrative circulating but no market confirmation yet"}


def detect_memetic_patterns(
    query: str = "slang emergence OR memetic patterns OR hyperstition",
    ingest_source: str = "mock",
    use_structured_ingest: bool = False,
    validate: bool = False,
    *,
    ingest_route: Optional[str] = None,
) -> Dict[str, Any]:
    # Structured fingerprint path is always used (use_structured_ingest kept for API compat).
    ingest_data = fetch_ingest(
        query,
        source=ingest_source,
        structured=True,
        route=ingest_route,
    )
    raw_signal = ingest_data.get("raw_signal", "")
    ingest_meta = ingest_data
    source_fp = ingest_data.get("source_fingerprint") or (
        (ingest_data.get("provenance") or {}).get("source_fingerprint")
    )
    _ = use_structured_ingest  # API compat; always structured now

    observed = humanize_slang_output(raw_signal[:280])
    neos = detect_neologisms(observed)
    llm_meta: Optional[Dict[str, Any]] = None
    # Optional governed LLM enrichment (HYPERLEX_LLM=1 + provider)
    try:
        from ..llm import llm_enabled, enrich_neologisms

        if llm_enabled():
            llm_meta = enrich_neologisms(observed, neos)
            if llm_meta.get("applied"):
                neos = list(llm_meta.get("merged") or neos)
    except Exception:
        llm_meta = {"status": "error", "applied": False}

    virality = compute_virality_score(observed)
    hyper = simulate_hyperstition_loop(observed)

    neo_terms = [n["term"] for n in neos]
    lineage = match_lineage(observed, terms=neo_terms)
    memetic = memetics_protocol_check(
        observed,
        lineage_family=(lineage or {}).get("family_id"),
    )
    variation = trace_semantic_variation(
        neo_terms[0] if neo_terms else "term",
        observed,
        lineage_family=(lineage or {}).get("family_id"),
        typology=memetic.get("typology_primary") or memetic.get("typology"),
    )

    # Weak forward estimate — analysis field only (not calibration forecast)
    virality = dict(virality)
    virality["prediction"] = predict_virality(
        hybrid_score=float(virality.get("hybrid_score") or 0.0),
        velocity=float(virality.get("velocity") or 0.0),
        acceleration=float(virality.get("acceleration") or 0.0),
        lineage_confidence=(lineage or {}).get("confidence"),
        hyperstition_stage=hyper.get("loop_stage"),
        memetic_score=memetic.get("score"),
        n_neologisms=len(neos),
        horizon="short",
    )

    inferred = (
        f"Memetic spread accelerating. Neologisms: {len(neos)}. "
        f"Memetic: {memetic['is_memetic']}. Variation: {variation['sense']}. "
        f"Virality: {virality['hybrid_score']}."
    )
    if lineage:
        inferred += f" Lineage: {lineage['family_id']} (conf={lineage['confidence']})."
    pred = virality.get("prediction") or {}
    speculative = (
        f"{hyper['loop_stage']} hyperstition risk. {hyper['mechanism']}. "
        f"Virality prediction (SPECULATIVE): {pred.get('predicted_hybrid')} "
        f"Δ={pred.get('delta_vs_baseline')}. "
        f"Brier requires settlement via hyperlex.calibration — not claimed on open forecasts."
    )

    fp_id = (source_fp or {}).get("fingerprint_id")
    h = analysis_canonical_hash(
        query=query,
        observed=observed,
        neo_terms=neo_terms,
        source_fingerprint_id=fp_id,
    )

    analysis: Dict[str, Any] = {
        "neologisms": neos,
        "semantic_variation": variation,
        "virality": virality,
        "memetics": memetic,
        "hyperstition": hyper,
    }
    if llm_meta is not None:
        analysis["llm_enrichment"] = {
            "status": llm_meta.get("status"),
            "applied": bool(llm_meta.get("applied")),
            "n_new": llm_meta.get("n_new", 0),
            "reason": llm_meta.get("reason"),
            "provenance": "SPECULATIVE" if llm_meta.get("applied") else "NOT_COMPUTABLE",
        }
    if lineage:
        analysis["lineage"] = lineage

    # Optional local vector-DB neighbors (fail-open; never invents Brier)
    try:
        import os
        from pathlib import Path as _Path

        from ..vectordb import default_vector_db_path, vector_search

        vflag = str(os.environ.get("HYPERLEX_VECTOR", "auto")).strip().lower()
        vpath = default_vector_db_path()
        want = vflag in {"1", "true", "yes", "on"} or (
            vflag in {"", "auto"} and vpath.is_file() and vpath.stat().st_size > 0
        )
        if want and vflag not in {"0", "false", "off", "no"}:
            qtext = " ".join(
                x for x in [query, observed, " ".join(neo_terms[:8])] if x
            ).strip()
            if qtext:
                vs = vector_search(qtext, kind="term", top_k=5, min_score=0.12)
                if vs.get("ok") and vs.get("hits"):
                    analysis["vector_neighbors"] = {
                        "schema": "hyperlex.vector_neighbors.v1",
                        "model": vs.get("model"),
                        "embed_provenance": vs.get("embed_provenance"),
                        "hits": vs.get("hits")[:5],
                        "n_hits": vs.get("n_hits"),
                        "db_path": vs.get("db_path"),
                        "provenance": "INFERRED",
                        "brier": None,
                        "note": "Cosine neighbors from local vector DB; not calibrated probabilities.",
                    }
    except Exception:
        pass

    result = {
        "observed": observed,
        "inferred": inferred,
        "speculative": speculative,
        "provenance": {
            "canonical_hash": h,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": PKG_VERSION,
            "brier": None,
            "brier_note": "brier_requires_settlement",
            "hyperstition_risk": hyper["loop_stage"],
            "memclaw": "agent_id=hermes-governed-operator, type=projection, weight=0.92",
            "arxiv_concepts_applied": [
                "neologism_pipeline", "semantic_variation", "virality_hybrid",
                "memetics_protocol", "hyperstition_loop", "cultural_transmission"
            ],
            "ingest_source": ingest_source,
            "source_fingerprint": source_fp,
            "content_hash": (source_fp or {}).get("content_hash"),
            "source_locator": (source_fp or {}).get("source_locator"),
            "adapter_version": (source_fp or {}).get("adapter_version"),
        },
        "analysis": analysis,
        "notes": "Humanizer + lineage confidence scoring applied. Brier is not emitted until forecasts are settled (see hyperlex.calibration / docs/brier-calibration.md).",
        "recommendation": (
            "Bind RUNE.HLX.COMMUNICATION_RELAY via hyperlex.relay; "
            "extract_forecasts for calibration; cron LIVE_EMERGENCE_SCAN."
        ),
    }

    # always attach structured ingest meta for fingerprint audit trail
    result["ingest"] = {
        "query": ingest_meta.get("query", query),
        "source": ingest_meta.get("source", ingest_source),
        "extracted_terms": ingest_meta.get("extracted_terms"),
        "metadata": ingest_meta.get("metadata"),
        "source_fingerprint": source_fp,
    }

    if validate:
        ok, msg = validate_result(result)
        result["schema_validation"] = {"valid": ok, "message": msg}

    return result
