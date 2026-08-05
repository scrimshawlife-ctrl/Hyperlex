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
        "terms": ["hallucinate", "slop", "clanker", "agentic", "glazing", "skill issue", "token", "context window"],
        "branch_operator": "platform_compression",
        "diagram_ref": "examples/slang-families/ai-native-family.mmd",
        "payload_note": "machine language as culture; quality judgment + hostility + agency framing",
    },
    {
        "family_id": "brainrot-aura",
        "terms": ["brainrot", "brain rot", "aura", "aura farming", "mid", "cooked", "let him cook"],
        "branch_operator": "irony_inversion",
        "diagram_ref": "examples/slang-families/brainrot-aura-family.mmd",
        "payload_note": "content-degradation + status radiation; self-aware consumption",
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


def match_lineage(
    text: str,
    terms: Optional[List[str]] = None,
    min_confidence: float = LINEAGE_CONFIDENCE_THRESHOLD,
) -> Optional[Dict[str, Any]]:
    corpus = (text or "").lower()
    if terms:
        corpus = corpus + " " + " ".join(t.lower() for t in terms)

    best: Optional[Dict[str, Any]] = None
    best_score = 0.0

    for entry in LINEAGE_REGISTRY:
        hits = _find_hits(corpus, entry["terms"])
        if not hits:
            continue

        score, breakdown = compute_lineage_confidence(hits, entry["terms"], corpus)
        if score < min_confidence:
            continue

        if score > best_score:
            best_score = score
            best = {
                "family_id": entry["family_id"],
                "matched_terms": hits,
                "branch_operator": entry.get("branch_operator", "unknown"),
                "confidence": round(score, 3),
                "diagram_ref": entry.get("diagram_ref"),
                "payload_note": entry.get("payload_note"),
                "provenance": "INFERRED",
                "score_breakdown": breakdown,
            }

    return best


def humanize_slang_output(text: str) -> str:
    for p in ["pivotal", "underscoring", "showcasing", "crucial", "landscape", "tapestry", "delve", "realm"]:
        text = text.replace(p, "")
    return text.strip() + " — feels off but sharp money is already running with it."


def detect_neologisms(text: str) -> List[Dict[str, Any]]:
    candidates = re.findall(r'\b([a-z]{4,}(?:block|nine|sharp|holler|revenge|low|false))\b', text.lower())
    results = []
    for c in set(candidates):
        formation = "extra-grammatical" if any(x in c for x in ["block", "nine"]) else "grammatical"
        score = 0.7 if len(c) > 6 else 0.4
        results.append({"term": c, "formation": formation, "confidence": round(score, 2)})
    return results


def trace_semantic_variation(term: str, context: str) -> Dict[str, str]:
    if "betting" in context.lower() or "sharp" in term:
        return {"sense": "tactical/quant", "driver": "communicative_need + semantic_distinction", "community": "sharp_money"}
    return {"sense": "general", "driver": "communicative_need", "community": "general_betting"}


def compute_virality_score(observed_text: str) -> Dict[str, float]:
    velocity = min(1.0, len(observed_text.split()) / 40.0)
    acceleration = 0.6 if "velocity" in observed_text.lower() or "narrative" in observed_text.lower() else 0.3
    network_prior = 0.75
    hybrid = round((velocity * 0.3 + acceleration * 0.4 + network_prior * 0.3), 3)
    return {"hybrid_score": hybrid, "velocity": round(velocity, 3), "acceleration": round(acceleration, 3)}


def memetics_protocol_check(text: str) -> Dict[str, Any]:
    imitation_signals = ["narrative", "holler", "spread", "everyone saying"]
    is_memetic = any(s in text.lower() for s in imitation_signals) and len(text) > 40
    return {"is_memetic": is_memetic, "typology": "betting_tactical" if is_memetic else "one_off", "score": 0.82 if is_memetic else 0.31}


def simulate_hyperstition_loop(narrative: str) -> Dict[str, str]:
    if "revenge" in narrative.lower() or "sharp" in narrative.lower():
        return {"loop_stage": "ACTUALIZING", "mechanism": "slang -> public pressure -> line movement -> confirmed"}
    return {"loop_stage": "EMERGENT", "mechanism": "narrative circulating but no market confirmation yet"}


def detect_memetic_patterns(
    query: str = "slang emergence OR memetic patterns OR hyperstition",
    ingest_source: str = "mock",
    use_structured_ingest: bool = False,
    validate: bool = False
) -> Dict[str, Any]:
    if use_structured_ingest:
        ingest_data = fetch_ingest(query, source=ingest_source)
        raw_signal = ingest_data.get("raw_signal", "")
        ingest_meta = ingest_data
        source_fp = ingest_data.get("source_fingerprint") or (
            (ingest_data.get("provenance") or {}).get("source_fingerprint")
        )
    else:
        # always fingerprint even non-structured path
        ingest_data = fetch_ingest(query, source=ingest_source, structured=True)
        raw_signal = ingest_data.get("raw_signal", "")
        ingest_meta = ingest_data
        source_fp = ingest_data.get("source_fingerprint")

    observed = humanize_slang_output(raw_signal[:280])
    neos = detect_neologisms(observed)
    variation = trace_semantic_variation("low block", observed)
    virality = compute_virality_score(observed)
    memetic = memetics_protocol_check(observed)
    hyper = simulate_hyperstition_loop(observed)

    neo_terms = [n["term"] for n in neos]
    lineage = match_lineage(observed, terms=neo_terms)

    inferred = (
        f"Memetic spread accelerating. Neologisms: {len(neos)}. "
        f"Memetic: {memetic['is_memetic']}. Variation: {variation['sense']}. "
        f"Virality: {virality['hybrid_score']}."
    )
    if lineage:
        inferred += f" Lineage: {lineage['family_id']} (conf={lineage['confidence']})."
    speculative = (
        f"{hyper['loop_stage']} hyperstition risk. {hyper['mechanism']}. "
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
    if lineage:
        analysis["lineage"] = lineage

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
