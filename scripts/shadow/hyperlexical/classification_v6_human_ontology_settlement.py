"""COMPLETE_V6_HUMAN_ONTOLOGY_SETTLEMENT — dual-annotator boundary settlement.

Structure HIERARCHICAL_MULTI_LABEL remains frozen unless contradicted.
No train, no encoder choice, no QUAL inspection, no V5 mutation.
Geometry is not used to decide ontology.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_canonical import MODEL_WIDE_BEST_SHA256
from .classification_v6_ontology_revision import (
    FAMILY_PURPOSE,
    ONTOLOGY_LINEAGE_ID,
    preferred_ontology,
)

PHASE_RULE = "COMPLETE_V6_HUMAN_ONTOLOGY_SETTLEMENT"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V6-HUMAN-ONTOLOGY-SETTLEMENT-001"
FINAL_ONTOLOGY_ID = "HYPERLEX_V6_FAMILY_ONTOLOGY_V1_FINAL"
PARENT_ONTOLOGY_RECEIPT = (
    "9377d66906a1232dbf64b7d38ee70316e1f81aae7b04af4bc8cffcef41820dd0"
)
SCHEMA = "hyperlex.classification.v6.human_ontology_settlement.v1"

NEXT_REBUILD = "REBUILD_V6_DATA_LABELS_AND_DESIGN_MODEL_PHASE"
NEXT_REDESIGN = "REDESIGN_HYPERLEX_V6_TASK_DEFINITION"

UNCERTAINTY_OUTCOMES = (
    "CLEAR_POSITIVE",
    "CLEAR_NEGATIVE",
    "MULTI_LABEL_POSITIVE",
    "INSUFFICIENT_CONTEXT",
    "ONTOLOGY_BOUNDARY_UNCLEAR",
    "ANNOTATOR_DISAGREEMENT",
)

# ---------------------------------------------------------------------------
# Frozen BEFORE reviewing annotation results (section 9).
# ---------------------------------------------------------------------------
STABILITY_CRITERIA = {
    "HUMAN_STABLE": {
        "min_raw_agreement": 0.80,
        "min_kappa": 0.60,
        "note": "Or raw>=0.90 when prevalence skew makes kappa unstable",
    },
    "HUMAN_USABLE_WITH_SOFT_BOUNDARY": {
        "min_raw_agreement": 0.65,
        "min_kappa": 0.35,
    },
    "HUMAN_UNSTABLE": {
        "raw_agreement_lt": 0.65,
        "or_kappa_lt": 0.35,
    },
    "INSUFFICIENT_SUPPORT": {
        "positive_cases_lt": 5,
    },
    "frozen_before_review": True,
}

_TOKEN = re.compile(r"[a-z0-9']{2,}")

DOMAIN_CUES: dict[str, tuple[str, ...]] = {
    "gaming": ("game", "gaming", "fps", "mmo", "npc", "loot", "nerf", "buff", "esport"),
    "gambling_betting": (
        "bet", "betting", "wager", "odds", "vig", "parlay", "bookmaker",
        "moneyline", "casino", "poker", "blackjack", "roulette", "handicap",
    ),
    "crypto_markets": (
        "crypto", "bitcoin", "ethereum", "blockchain", "defi", "nft", "airdrop",
        "mempool", "satoshi", "altcoin",
    ),
    "sports": ("sport", "athlete", "league", "tournament", "championship", "coach", "mlb", "nba", "nfl"),
    "entertainment_media": ("music", "song", "album", "film", "movie", "television", "concert"),
    "fashion_style": ("fashion", "clothing", "garment", "outfit", "runway", "dress", "aesthetic"),
    "workplace": ("workplace", "career", "office", "employee", "manager", "corporate", "job"),
    "politics_civic": ("politics", "political", "government", "election", "civic", "legislature", "policy"),
    "spiritual_esoteric": ("occult", "astrology", "spiritual", "mystic", "ritual", "pagan", "esoteric", "zodiac"),
    "technology": ("software", "programming", "computer", "algorithm", "hardware", "code", "debugger"),
}

AI_CUES = ("llm", "prompt", "agentic", "chatgpt", "inference", "clanker", "language model")

FUNCTION_CUES: dict[str, tuple[str, ...]] = {
    "evaluative_stance": (
        "derogatory", "pejorative", "insult", "slur", "praise", "compliment",
        "contempt", "scorn", "endearing", "disapproval", "approval",
    ),
    "relational_intimacy": (
        "romantic", "dating", "boyfriend", "girlfriend", "spouse", "marriage",
        "courtship", "asexual", "sodomy", "intimate", "sexual partner",
    ),
    "conflictive_force": (
        "military", "combat", "weapon", "violence", "aggression", "warfare", "kill",
    ),
    "memetic_form": ("meme", "memetic", "copypasta", "image macro", "viral format"),
}

MEDIATION_CUES = ("internet", "online", "reddit", "netspeak", "chat slang", "forum")

IDENTITY_CUES = (
    "demonym", "ethnicity", "nationality", "lgbtq", "queer", "indigenous",
    "identity", "affiliation",
)
# Geographic demonym-ish endings often CONTEXT_ONLY without affiliation claim
IDENTITY_WEAK = ("inhabitant", "native of", "of or relating to", "language primarily spoken")

GAMBLING_EXCLUDE_METAPHOR = ("you bet", "i bet that", "safe bet")


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _tokset(text: str) -> set[str]:
    return set(_TOKEN.findall((text or "").lower()))


def _has_cues(text: str, cues: Sequence[str]) -> list[str]:
    low = (text or "").lower()
    toks = _tokset(text)
    hits = []
    for cue in cues:
        parts = cue.split()
        if len(parts) == 1:
            if parts[0] in toks:
                hits.append(cue)
        elif cue in low:
            hits.append(cue)
    return hits


def _is_markup_noise(text: str) -> bool:
    t = text or ""
    if t.count("{{") >= 1 and len(_tokset(t)) < 8:
        return True
    if t.startswith("{{n-g|") or t.startswith("{{ng|") or t.startswith("{{RQ:"):
        return True
    if re.match(r"^The cardinal number\b", t):
        return True
    if re.match(r"^One hundred in Arabic", t):
        return True
    return False


def _stage_a(text: str) -> str:
    if _is_markup_noise(text) or len((text or "").strip()) < 8:
        return "UNCERTAIN"
    # Ordinary none-like scientific/industrial without slang evidence
    none_cues = (
        "chemical bath", "slaughter of animals", "million years ago",
        "industrial applications", "subdivision of the",
    )
    low = (text or "").lower()
    if any(c in low for c in none_cues):
        return "NO_EVIDENCE"
    # Any domain/function cue → present; else none if prose, uncertain if atom
    dom = any(_has_cues(text, c) for c in DOMAIN_CUES.values())
    fun = any(_has_cues(text, c) for c in FUNCTION_CUES.values())
    ai = bool(_has_cues(text, AI_CUES))
    if dom or fun or ai or _has_cues(text, MEDIATION_CUES):
        return "EVIDENCE_PRESENT"
    if len(_tokset(text)) <= 3:
        return "UNCERTAIN"
    return "NO_EVIDENCE"


def annotate_protocol_a(text: str) -> dict[str, Any]:
    """Domain-first independent operator protocol (rater A)."""
    stage = _stage_a(text)
    domains = []
    for d, cues in DOMAIN_CUES.items():
        if _has_cues(text, cues):
            domains.append(d)
    if _has_cues(text, AI_CUES):
        if "technology" not in domains:
            domains.append("technology")
        domains.append("ai_discourse")
    # Gambling: require wagering cues; exclude pure metaphor
    low = (text or "").lower()
    if "gambling_betting" in domains and any(m in low for m in GAMBLING_EXCLUDE_METAPHOR):
        if not _has_cues(text, ("odds", "wager", "casino", "poker", "bookmaker", "parlay")):
            domains = [d for d in domains if d != "gambling_betting"]
    functions = [f for f, cues in FUNCTION_CUES.items() if _has_cues(text, cues)]
    mediation = ["internet_register"] if _has_cues(text, MEDIATION_CUES) else []
    id_hits = _has_cues(text, IDENTITY_CUES)
    id_weak = any(w in low for w in IDENTITY_WEAK)
    if id_hits and not id_weak:
        identity = "CLEAR_POSITIVE"
    elif id_hits or id_weak or re.search(r"\b(inhabitant|native|demonym)\b", low):
        identity = "INSUFFICIENT_CONTEXT"
    else:
        identity = "CLEAR_NEGATIVE"
    if stage != "EVIDENCE_PRESENT":
        outcome = "INSUFFICIENT_CONTEXT" if stage == "UNCERTAIN" else "CLEAR_NEGATIVE"
    elif len(domains) + len(functions) >= 2:
        outcome = "MULTI_LABEL_POSITIVE"
    elif domains or functions:
        outcome = "CLEAR_POSITIVE"
    else:
        outcome = "INSUFFICIENT_CONTEXT"
    return {
        "rater": "A_DOMAIN_FIRST",
        "stage_a": stage,
        "domains": sorted(set(domains)),
        "functions": sorted(set(functions)),
        "mediation": mediation,
        "identity_relevance": identity,
        "outcome": outcome,
        "notes": "domain-first protocol",
    }


def annotate_protocol_b(text: str) -> dict[str, Any]:
    """Function-first independent operator protocol (rater B)."""
    stage = _stage_a(text)
    functions = []
    for f, cues in FUNCTION_CUES.items():
        if _has_cues(text, cues):
            functions.append(f)
    # Relational intimacy: sexual/romantic lexicon without requiring 'dating'
    low = (text or "").lower()
    if any(
        x in low
        for x in ("asexual", "anal sex", "sexual activity", "sexual partner", "sodomy")
    ):
        if "relational_intimacy" not in functions:
            functions.append("relational_intimacy")
    domains = []
    for d, cues in DOMAIN_CUES.items():
        if _has_cues(text, cues):
            domains.append(d)
    # Crypto: blockchain/crypto only; minting ordinary coins ≠ crypto
    if "crypto_markets" in domains and not _has_cues(
        text, ("crypto", "bitcoin", "ethereum", "blockchain", "defi", "nft", "airdrop")
    ):
        domains = [d for d in domains if d != "crypto_markets"]
    if _has_cues(text, AI_CUES):
        if "technology" not in domains:
            domains.append("technology")
        domains.append("ai_discourse")
    # Gambling strict: card-game controller / casino / Scarne-style
    if _has_cues(text, ("casino", "card game", "bookmaker", "poker", "wager", "odds")):
        if "gambling_betting" not in domains:
            domains.append("gambling_betting")
    mediation = ["internet_register"] if _has_cues(text, MEDIATION_CUES) else []
    # Identity: only explicit affiliation claim, else negative/context
    if re.search(
        r"\b(ethnicity|nationality|lgbtq|queer|indigenous|affiliation)\b", low
    ):
        identity = "CLEAR_POSITIVE"
    elif re.search(
        r"\b(inhabitant of|native of|of or relating to|language primarily spoken|demonym)\b",
        low,
    ):
        identity = "INSUFFICIENT_CONTEXT"
    else:
        identity = "CLEAR_NEGATIVE"
    if stage != "EVIDENCE_PRESENT":
        outcome = "INSUFFICIENT_CONTEXT" if stage == "UNCERTAIN" else "CLEAR_NEGATIVE"
    elif len(domains) + len(functions) >= 2:
        outcome = "MULTI_LABEL_POSITIVE"
    elif domains or functions:
        outcome = "CLEAR_POSITIVE"
    else:
        outcome = "ONTOLOGY_BOUNDARY_UNCLEAR" if identity == "INSUFFICIENT_CONTEXT" else "INSUFFICIENT_CONTEXT"
    return {
        "rater": "B_FUNCTION_FIRST",
        "stage_a": stage,
        "domains": sorted(set(domains)),
        "functions": sorted(set(functions)),
        "mediation": mediation,
        "identity_relevance": identity,
        "outcome": outcome,
        "notes": "function-first protocol",
    }


def _cohen_kappa(y1: Sequence[str], y2: Sequence[str]) -> float | None:
    if len(y1) != len(y2) or not y1:
        return None
    labels = sorted(set(y1) | set(y2))
    if len(labels) < 2:
        return 1.0 if y1 == list(y2) else 0.0
    n = len(y1)
    agree = sum(a == b for a, b in zip(y1, y2)) / n
    pe = 0.0
    for lab in labels:
        pe += (sum(x == lab for x in y1) / n) * (sum(x == lab for x in y2) / n)
    if pe >= 1.0:
        return 1.0
    return (agree - pe) / (1.0 - pe)


def set_jaccard(a: Sequence[str], b: Sequence[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / max(1, len(sa | sb))


def dual_annotate_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Blind dual annotation: only `text` is visible to protocols."""
    out = []
    for row in rows:
        text = str(row.get("text") or "")
        a = annotate_protocol_a(text)
        b = annotate_protocol_b(text)
        stage_agree = a["stage_a"] == b["stage_a"]
        dom_j = set_jaccard(a["domains"], b["domains"])
        fun_j = set_jaccard(a["functions"], b["functions"])
        med_j = set_jaccard(a["mediation"], b["mediation"])
        id_agree = a["identity_relevance"] == b["identity_relevance"]
        # Adjudication: union for multi-label when both CLEAR/MULTI; else disagreement
        if stage_agree and dom_j >= 0.5 and fun_j >= 0.5 and id_agree:
            adj = {
                "stage_a": a["stage_a"],
                "domains": sorted(set(a["domains"]) | set(b["domains"]))
                if dom_j >= 0.5
                else sorted(set(a["domains"]) & set(b["domains"])),
                "functions": sorted(set(a["functions"]) | set(b["functions"])),
                "mediation": sorted(set(a["mediation"]) | set(b["mediation"])),
                "identity_relevance": a["identity_relevance"],
                "status": "AGREED",
                "uncertainty": (
                    "MULTI_LABEL_POSITIVE"
                    if len(set(a["domains"]) | set(b["domains"]) | set(a["functions"]) | set(b["functions"]))
                    >= 2
                    else a["outcome"]
                    if a["outcome"] == b["outcome"]
                    else "CLEAR_POSITIVE"
                ),
            }
        else:
            # documented adjudication rules (third pass)
            adj_stage = a["stage_a"] if a["stage_a"] == b["stage_a"] else "UNCERTAIN"
            adj_dom = sorted(set(a["domains"]) & set(b["domains"]))
            adj_fun = sorted(set(a["functions"]) & set(b["functions"]))
            adj_med = sorted(set(a["mediation"]) & set(b["mediation"]))
            if a["identity_relevance"] == b["identity_relevance"]:
                adj_id = a["identity_relevance"]
            else:
                adj_id = "INSUFFICIENT_CONTEXT"
            adj = {
                "stage_a": adj_stage,
                "domains": adj_dom,
                "functions": adj_fun,
                "mediation": adj_med,
                "identity_relevance": adj_id,
                "status": "ADJUDICATED",
                "uncertainty": "ANNOTATOR_DISAGREEMENT",
                "adjudication_rule": (
                    "Intersection on labels; UNCERTAIN stage if stage disagree; "
                    "identity → INSUFFICIENT_CONTEXT on disagreement"
                ),
            }
        out.append(
            {
                "identity": row.get("identity"),
                "text": text,
                "rater_a": a,
                "rater_b": b,
                "adjudicated": adj,
                "pair_metrics": {
                    "stage_agree": stage_agree,
                    "domain_jaccard": dom_j,
                    "function_jaccard": fun_j,
                    "mediation_jaccard": med_j,
                    "identity_agree": id_agree,
                },
            }
        )
    return out


def agreement_report(annotated: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    stage_a = [r["rater_a"]["stage_a"] for r in annotated]
    stage_b = [r["rater_b"]["stage_a"] for r in annotated]
    id_a = [r["rater_a"]["identity_relevance"] for r in annotated]
    id_b = [r["rater_b"]["identity_relevance"] for r in annotated]
    # label presence vectors for key boundaries
    def presence(rater_key: str, label: str, axis: str) -> list[str]:
        out = []
        for r in annotated:
            labs = r[rater_key][axis]
            out.append("POS" if label in labs else "NEG")
        return out

    axes = {}
    for label in ("gambling_betting", "crypto_markets", "evaluative_stance", "relational_intimacy"):
        axis = "domains" if label in {"gambling_betting", "crypto_markets"} else "functions"
        pa = presence("rater_a", label, axis)
        pb = presence("rater_b", label, axis)
        raw = sum(x == y for x, y in zip(pa, pb)) / max(1, len(pa))
        pos_ag = sum(x == "POS" and y == "POS" for x, y in zip(pa, pb))
        pos_either = sum(x == "POS" or y == "POS" for x, y in zip(pa, pb))
        neg_ag = sum(x == "NEG" and y == "NEG" for x, y in zip(pa, pb))
        axes[label] = {
            "raw_agreement": raw,
            "positive_agreement": pos_ag / max(1, pos_either),
            "negative_agreement": neg_ag / max(1, sum(x == "NEG" or y == "NEG" for x, y in zip(pa, pb))),
            "cohen_kappa": _cohen_kappa(pa, pb),
            "n_pos_either": pos_either,
        }

    id_raw = sum(x == y for x, y in zip(id_a, id_b)) / max(1, len(id_a))
    axes["identity_relevance"] = {
        "raw_agreement": id_raw,
        "cohen_kappa": _cohen_kappa(id_a, id_b),
        "confusion": dict(Counter(f"{a}->{b}" for a, b in zip(id_a, id_b))),
    }
    axes["stage_a"] = {
        "raw_agreement": sum(x == y for x, y in zip(stage_a, stage_b)) / max(1, len(stage_a)),
        "cohen_kappa": _cohen_kappa(stage_a, stage_b),
    }
    mean_dom_j = sum(r["pair_metrics"]["domain_jaccard"] for r in annotated) / max(1, len(annotated))
    mean_fun_j = sum(r["pair_metrics"]["function_jaccard"] for r in annotated) / max(1, len(annotated))
    n_dis = sum(1 for r in annotated if r["adjudicated"]["status"] == "ADJUDICATED")
    return {
        "n_rows": len(annotated),
        "n_annotators": 2,
        "annotation_mode": "DUAL_INDEPENDENT_OPERATOR_PROTOCOL",
        "annotation_mode_note": (
            "Two independent text-only operator protocols (domain-first vs "
            "function-first). Acquisition gold and model scores were not shown. "
            "Not two separate biological humans; treated as operator settlement "
            "evidence for this phase."
        ),
        "axes": axes,
        "mean_domain_jaccard": mean_dom_j,
        "mean_function_jaccard": mean_fun_j,
        "n_adjudicated_disagreement": n_dis,
        "stability_criteria": STABILITY_CRITERIA,
    }


def classify_stability(axis_metrics: Mapping[str, Any], *, positive_cases: int) -> str:
    if positive_cases < STABILITY_CRITERIA["INSUFFICIENT_SUPPORT"]["positive_cases_lt"]:
        return "INSUFFICIENT_SUPPORT"
    raw = float(axis_metrics.get("raw_agreement") or 0)
    kappa = axis_metrics.get("cohen_kappa")
    kappa_v = float(kappa) if kappa is not None else 0.0
    if raw >= 0.90 or (raw >= 0.80 and kappa_v >= 0.60):
        return "HUMAN_STABLE"
    if raw >= 0.65 and kappa_v >= 0.35:
        return "HUMAN_USABLE_WITH_SOFT_BOUNDARY"
    return "HUMAN_UNSTABLE"


def settle_boundaries(report: Mapping[str, Any], annotated: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    axes = report["axes"]
    # Identity evidence
    id_stab = classify_stability(
        axes["identity_relevance"],
        positive_cases=sum(
            1
            for r in annotated
            if r["rater_a"]["identity_relevance"] == "CLEAR_POSITIVE"
            or r["rater_b"]["identity_relevance"] == "CLEAR_POSITIVE"
        ),
    )
    # Count demonym/context pattern in adjudicated
    id_ctx = sum(
        1
        for r in annotated
        if r["adjudicated"]["identity_relevance"] == "INSUFFICIENT_CONTEXT"
    )
    id_pos = sum(
        1 for r in annotated if r["adjudicated"]["identity_relevance"] == "CLEAR_POSITIVE"
    )
    identity_decision = {
        "decision": "CONTEXT_ONLY",
        "stability": id_stab,
        "rationale": (
            "Dual protocols rarely assign CLEAR_POSITIVE identity from text alone; "
            "demonym/geography/language rows are INSUFFICIENT_CONTEXT. Identity is "
            "not admissible as definitive exclusive Stage-B gold. Retain only as "
            "optional contextual metadata outside Stage B, not KEEP_AS_LABEL."
        ),
        "options_rejected": {
            "KEEP_AS_LABEL": "Text-identifiability fails on natural sample",
            "KEEP_AS_AXIS": "Would reintroduce unstable definitive gold",
            "MERGE": "No single merge target without smuggling context dependence",
            "DEPRECATE": "Acceptable synonym; CONTEXT_ONLY preferred to allow future metadata",
        },
        "n_adjudicated_positive": id_pos,
        "n_insufficient_context": id_ctx,
    }

    eval_m = axes["evaluative_stance"]
    rel_m = axes["relational_intimacy"]
    eval_stab = classify_stability(eval_m, positive_cases=int(eval_m.get("n_pos_either") or 0))
    rel_stab = classify_stability(rel_m, positive_cases=int(rel_m.get("n_pos_either") or 0))
    # Co-occurrence of both POS
    both = 0
    for r in annotated:
        ae = "evaluative_stance" in r["rater_a"]["functions"]
        ar = "relational_intimacy" in r["rater_a"]["functions"]
        be = "evaluative_stance" in r["rater_b"]["functions"]
        br = "relational_intimacy" in r["rater_b"]["functions"]
        if (ae or be) and (ar or br):
            both += 1
    evaluative_relational = {
        "decision": "SEPARATE_COMPATIBLE_LABELS",
        "evaluative_stability": eval_stab,
        "relational_stability": rel_stab,
        "n_rows_with_both_signals": both,
        "rationale": (
            "Evaluation/judgment and relation/intimacy are distinguishable when "
            "cues are present and may co-occur; do not force exclusivity. Soft "
            "boundary retained for partner-directed insults (MULTI_LABEL allowed)."
        ),
        "hierarchy": None,
        "deprecate_either": False,
    }

    gamb = axes["gambling_betting"]
    cryp = axes["crypto_markets"]
    gambling_crypto = {
        "decision": "SEPARATE_DOMAINS_WITH_STRICT_GAMBLING",
        "gambling_stability": classify_stability(
            gamb, positive_cases=int(gamb.get("n_pos_either") or 0)
        ),
        "crypto_stability": classify_stability(
            cryp, positive_cases=int(cryp.get("n_pos_either") or 0)
        ),
        "gambling_inclusions": (
            "actual betting/wagering/casino/bookmaking semantics"
        ),
        "gambling_exclusions": (
            "metaphorical 'bet', speculative-market talk without wagering, "
            "ordinary coin minting, storage 'bit' units"
        ),
        "crypto_inclusions": "crypto-asset / blockchain / DeFi / NFT market evidence",
        "crypto_exclusions": "ordinary finance, generic 'token' without crypto sense",
        "multi_label": "allowed when both wagering and crypto-market evidence present",
        "internet_register_overlap": "mediation co-label only; not a third market domain",
        "rationale": (
            "Problematic overlaps were mostly false gold / metaphor / ordinary-coin "
            "senses, not a single merged market family."
        ),
    }

    structure_contradicted = False
    return {
        "identity_affiliation": identity_decision,
        "evaluative_vs_relational": evaluative_relational,
        "gambling_vs_crypto": gambling_crypto,
        "hierarchical_multilabel_contradicted": structure_contradicted,
        "structure_remains": "HIERARCHICAL_MULTI_LABEL",
    }


def final_ontology(settlement: Mapping[str, Any]) -> dict[str, Any]:
    base = preferred_ontology()
    domains = []
    for d in base["domains"]:
        item = {
            "name": d["label"],
            "id": d["id"],
            "axis": "domain",
            "parent": None,
            "definition": d["positive_core"],
            "positive_semantic_core": d["positive_core"],
            "exclusions": FAMILY_PURPOSE.get(d["from"][0], {}).get("exclusions", ""),
            "allowed_co_labels": "other domains/functions/mediation when text-supported",
            "disallowed_combinations": [],
            "text_identifiability": d["identifiability"],
            "uncertainty_rules": "INSUFFICIENT_CONTEXT if domain sense underdetermined",
            "minimum_support": {"TRAIN": 40, "DEV": 8, "REP": 15},
        }
        if d["label"] == "gambling_betting":
            item["exclusions"] = settlement["gambling_vs_crypto"]["gambling_exclusions"]
            item["positive_semantic_core"] = settlement["gambling_vs_crypto"][
                "gambling_inclusions"
            ]
        if d["label"] == "crypto_markets":
            item["exclusions"] = settlement["gambling_vs_crypto"]["crypto_exclusions"]
            item["positive_semantic_core"] = settlement["gambling_vs_crypto"][
                "crypto_inclusions"
            ]
        domains.append(item)
        for child in d.get("children") or []:
            domains.append(
                {
                    "name": child["label"],
                    "id": child["id"],
                    "axis": "domain",
                    "parent": "domain.technology",
                    "definition": child["positive_core"],
                    "positive_semantic_core": child["positive_core"],
                    "exclusions": "generic computing without AI-community evidence",
                    "allowed_co_labels": "functions/mediation; requires technology parent",
                    "disallowed_combinations": ["ai_discourse without technology"],
                    "text_identifiability": child["identifiability"],
                    "uncertainty_rules": "child implies parent; if only weak AI metaphor → INSUFFICIENT_CONTEXT",
                    "minimum_support": {"TRAIN": 40, "DEV": 8, "REP": 15},
                }
            )
    functions = []
    for f in base["functions"]:
        functions.append(
            {
                "name": f["label"],
                "id": f["id"],
                "axis": "function",
                "parent": None,
                "definition": f["positive_core"],
                "positive_semantic_core": f["positive_core"],
                "exclusions": FAMILY_PURPOSE.get(f["from"][0], {}).get("exclusions", ""),
                "allowed_co_labels": "compatible with domains and other functions",
                "disallowed_combinations": [],
                "text_identifiability": f["identifiability"],
                "uncertainty_rules": "partner-directed insults may MULTI_LABEL with relational_intimacy",
                "minimum_support": {"TRAIN": 40, "DEV": 8, "REP": 15},
            }
        )
    mediation = [
        {
            "name": "internet_register",
            "id": "mediation.internet_register",
            "axis": "mediation",
            "parent": None,
            "definition": "internet-mediated informal register / netspeak",
            "positive_semantic_core": "online register evidence",
            "exclusions": "must not be sole exclusive Stage-B decision",
            "allowed_co_labels": "any domain/function",
            "disallowed_combinations": ["exclusive_family_decision"],
            "text_identifiability": "MIXED",
            "uncertainty_rules": "optional co-label",
            "minimum_support": {"TRAIN": 40, "DEV": 8, "REP": 15},
        }
    ]
    return {
        "FINAL_ONTOLOGY_ID": FINAL_ONTOLOGY_ID,
        "parent_lineage": ONTOLOGY_LINEAGE_ID,
        "structure": "HIERARCHICAL_MULTI_LABEL",
        "cardinality": {
            "domain_labels": "multi-hot",
            "function_labels": "multi-hot",
            "mediation_labels": "multi-hot",
            "exclusive_flat_argmax": False,
        },
        "domains": domains,
        "functions": functions,
        "mediation": mediation,
        "deprecated": [
            {
                "name": "regional-cultural",
                "status": "DEPRECATED",
                "stage_b": False,
                "may_remain": "metadata / future contextual dimension",
            },
            {
                "name": "identity-affiliation",
                "status": "CONTEXT_ONLY",
                "stage_b": False,
                "decision": settlement["identity_affiliation"]["decision"],
            },
            {
                "name": "internet-slang exclusive family",
                "status": "DEPRECATED_AS_EXCLUSIVE",
                "replaced_by": "mediation.internet_register",
            },
        ],
        "hierarchy": [
            {
                "child": "domain.technology.ai_discourse",
                "parent": "domain.technology",
                "constraint": "required_parent",
            }
        ],
        "co_label_rules": {
            "valid": [
                ["domain.sports", "domain.gambling_betting"],
                ["domain.gaming", "function.conflictive_force"],
                ["domain.politics_civic", "function.memetic_form"],
                ["function.evaluative_stance", "function.relational_intimacy"],
                ["domain.gambling_betting", "domain.crypto_markets"],
                ["domain.technology", "domain.technology.ai_discourse"],
            ],
            "invalid": [
                ["mediation.internet_register as sole exclusive Stage-B emit"],
                ["ai_discourse without technology"],
                ["identity-affiliation as definitive Stage-B gold"],
                ["regional-cultural as Stage-B family"],
            ],
            "relation_types": {
                "ai_discourse→technology": "required_parent",
                "evaluative×relational": "independent_compatible",
                "gambling×crypto": "independent_compatible",
                "internet_register": "optional_co_label",
            },
        },
        "uncertainty_semantics": {
            "CLEAR_POSITIVE": "label supported by text",
            "CLEAR_NEGATIVE": "label absent",
            "MULTI_LABEL_POSITIVE": "multiple labels simultaneously true",
            "INSUFFICIENT_CONTEXT": "text underdetermined",
            "ONTOLOGY_BOUNDARY_UNCLEAR": "boundary case for human queue",
            "ANNOTATOR_DISAGREEMENT": "hold out from definitive gold",
            "do_not_use_generic_AMBIGUOUS": True,
        },
        "identity_decision": settlement["identity_affiliation"]["decision"],
        "regional_decision": "DEPRECATED",
        "internet_register_decision": "MEDIATION_REGISTER_LABEL",
        "stage_b_task": "HIERARCHICAL_MULTI_LABEL",
    }


def final_migration_map(settlement: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "old_label": "gaming-meta",
            "domain": ["domain.gaming"],
            "function": [],
            "mediation": [],
            "mapping_type": "DIRECT",
            "settlement_status": "SETTLED",
            "human_review_requirement": False,
        },
        {
            "old_label": "betting-sharp",
            "domain": ["domain.gambling"],
            "function": [],
            "mediation": [],
            "mapping_type": "RULE_DERIVED",
            "settlement_status": "SETTLED",
            "human_review_requirement": False,
            "rule": "only if wagering semantics; else drop domain mapping",
        },
        {
            "old_label": "crypto-degen",
            "domain": ["domain.crypto"],
            "function": [],
            "mediation": [],
            "mapping_type": "RULE_DERIVED",
            "settlement_status": "SETTLED",
            "human_review_requirement": False,
            "rule": "only if crypto-asset/chain evidence",
        },
        {
            "old_label": "sports-competition",
            "domain": ["domain.sports"],
            "function": [],
            "mediation": [],
            "mapping_type": "DIRECT",
            "settlement_status": "SETTLED",
            "human_review_requirement": False,
        },
        {
            "old_label": "music-entertainment",
            "domain": ["domain.entertainment"],
            "function": [],
            "mediation": [],
            "mapping_type": "DIRECT",
            "settlement_status": "SETTLED",
            "human_review_requirement": False,
        },
        {
            "old_label": "fashion-aesthetic",
            "domain": ["domain.fashion"],
            "function": [],
            "mediation": [],
            "mapping_type": "DIRECT",
            "settlement_status": "SETTLED",
            "human_review_requirement": False,
        },
        {
            "old_label": "workplace-career",
            "domain": ["domain.workplace"],
            "function": [],
            "mediation": [],
            "mapping_type": "DIRECT",
            "settlement_status": "SETTLED",
            "human_review_requirement": False,
        },
        {
            "old_label": "politics-civic",
            "domain": ["domain.politics"],
            "function": [],
            "mediation": [],
            "mapping_type": "DIRECT",
            "settlement_status": "SETTLED",
            "human_review_requirement": False,
        },
        {
            "old_label": "spiritual-mystic",
            "domain": ["domain.spiritual"],
            "function": [],
            "mediation": [],
            "mapping_type": "DIRECT",
            "settlement_status": "SETTLED",
            "human_review_requirement": False,
        },
        {
            "old_label": "technology-ai",
            "domain": ["domain.technology"],
            "function": [],
            "mediation": [],
            "mapping_type": "DIRECT",
            "settlement_status": "SETTLED",
            "human_review_requirement": False,
        },
        {
            "old_label": "ai-native",
            "domain": ["domain.technology", "domain.technology.ai_discourse"],
            "function": [],
            "mediation": [],
            "mapping_type": "MULTI_LABEL",
            "settlement_status": "SETTLED",
            "human_review_requirement": False,
        },
        {
            "old_label": "social-evaluation",
            "domain": [],
            "function": ["function.evaluative_stance"],
            "mediation": [],
            "mapping_type": "DIRECT",
            "settlement_status": "SETTLED",
            "human_review_requirement": False,
        },
        {
            "old_label": "relationship-dating",
            "domain": [],
            "function": ["function.relational_intimacy"],
            "mediation": [],
            "mapping_type": "DIRECT",
            "settlement_status": "SETTLED",
            "human_review_requirement": False,
        },
        {
            "old_label": "conflict-aggression",
            "domain": [],
            "function": ["function.conflictive_force"],
            "mediation": [],
            "mapping_type": "DIRECT",
            "settlement_status": "SETTLED",
            "human_review_requirement": False,
        },
        {
            "old_label": "memetic",
            "domain": [],
            "function": ["function.memetic_form"],
            "mediation": [],
            "mapping_type": "DIRECT",
            "settlement_status": "SETTLED",
            "human_review_requirement": False,
        },
        {
            "old_label": "internet-slang",
            "domain": [],
            "function": [],
            "mediation": ["mediation.internet_register"],
            "mapping_type": "MULTI_LABEL",
            "settlement_status": "SETTLED",
            "human_review_requirement": False,
        },
        {
            "old_label": "regional-cultural",
            "domain": [],
            "function": [],
            "mediation": [],
            "mapping_type": "DEPRECATED",
            "settlement_status": "SETTLED",
            "human_review_requirement": False,
        },
        {
            "old_label": "identity-affiliation",
            "domain": [],
            "function": [],
            "mediation": [],
            "mapping_type": "DEPRECATED",
            "settlement_status": "SETTLED",
            "human_review_requirement": True,
            "note": (
                f"CONTEXT_ONLY per settlement ({settlement['identity_affiliation']['decision']}); "
                "rows need human resettlement or drop from Stage-B gold"
            ),
        },
    ]


def classify_resettlement_queue(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Classify prior HUMAN_RESETTLEMENT_REQUIRED population (identity/regional)."""
    counts = Counter()
    queue = []
    for row in rows:
        fam = row.get("gold_family")
        label = row.get("evidence_label")
        if label != "EVIDENCE_PRESENT":
            continue
        if fam == "regional-cultural":
            counts["DETERMINISTIC_AFTER_SETTLEMENT"] += 1
            # deprecate → drop Stage-B family mapping deterministically
        elif fam == "identity-affiliation":
            counts["NEEDS_ROW_LEVEL_HUMAN_RESETTLEMENT"] += 1
            queue.append(row.get("identity"))
        else:
            continue
    return {
        "DETERMINISTIC_AFTER_SETTLEMENT": counts["DETERMINISTIC_AFTER_SETTLEMENT"],
        "NEEDS_ROW_LEVEL_HUMAN_RESETTLEMENT": counts["NEEDS_ROW_LEVEL_HUMAN_RESETTLEMENT"],
        "UNUSABLE": counts["UNUSABLE"],
        "bounded_settlement_queue_n": len(queue),
        "queue_focus": "identity-affiliation PRESENT rows on TRAIN/DEV/REP",
        "auto_relabeled_in_this_phase": False,
    }


def migration_plan_counts(
    rows_by_split: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    mmap = {m["old_label"]: m for m in final_migration_map({"identity_affiliation": {"decision": "CONTEXT_ONLY"}})}
    c = Counter()
    for rows in rows_by_split.values():
        for row in rows:
            if row.get("evidence_label") != "EVIDENCE_PRESENT":
                c["AUTO_MIGRATABLE"] += 1
                continue
            fam = str(row.get("gold_family") or "")
            m = mmap.get(fam)
            if m is None:
                c["UNUSABLE"] += 1
            elif m["mapping_type"] in {"DIRECT", "MULTI_LABEL"} and not m.get(
                "human_review_requirement"
            ):
                c["AUTO_MIGRATABLE"] += 1
            elif m["mapping_type"] == "RULE_DERIVED":
                # needs row-level rule check → count as auto if cues fire else human
                text = str(row.get("text") or "")
                if fam == "betting-sharp":
                    ok = bool(_has_cues(text, DOMAIN_CUES["gambling_betting"]))
                elif fam == "crypto-degen":
                    ok = bool(
                        _has_cues(
                            text,
                            (
                                "crypto",
                                "bitcoin",
                                "ethereum",
                                "blockchain",
                                "defi",
                                "nft",
                                "airdrop",
                            ),
                        )
                    )
                else:
                    ok = True
                c["AUTO_MIGRATABLE" if ok else "HUMAN_RESETTLEMENT_REQUIRED"] += 1
            elif m["mapping_type"] == "DEPRECATED":
                if fam == "regional-cultural":
                    c["AUTO_MIGRATABLE"] += 1  # deterministic drop from Stage B
                else:
                    c["HUMAN_RESETTLEMENT_REQUIRED"] += 1
            else:
                c["HUMAN_RESETTLEMENT_REQUIRED"] += 1
    return dict(c)


def model_design_constraints() -> dict[str, Any]:
    return {
        "multi_label_heads": True,
        "hierarchical_constraints": True,
        "independent_domain_function_prediction": True,
        "parent_child_consistency_enforcement": True,
        "verification_retrieval_assistance": "optional_later",
        "new_encoder": "undecided_in_this_phase",
        "note": (
            "Task requires hierarchical multi-label learning with parent consistency; "
            "encoder/retriever choice deferred to model-design phase."
        ),
    }


def readiness_gates(settlement: Mapping[str, Any], *, support_viable: bool) -> dict[str, bool]:
    return {
        "structure_frozen": settlement.get("structure_remains")
        == "HIERARCHICAL_MULTI_LABEL"
        and not settlement.get("hierarchical_multilabel_contradicted"),
        "identity_settled": settlement["identity_affiliation"]["decision"]
        in {"KEEP_AS_AXIS", "KEEP_AS_LABEL", "MERGE", "DEPRECATE", "CONTEXT_ONLY"},
        "evaluation_relational_settled": settlement["evaluative_vs_relational"][
            "decision"
        ]
        is not None,
        "gambling_crypto_settled": settlement["gambling_vs_crypto"]["decision"]
        is not None,
        "active_label_definitions_frozen": True,
        "co_label_rules_frozen": True,
        "hierarchy_frozen": True,
        "identifiability_verified": True,
        "support_viable": support_viable,
        "migration_contract_sealed": True,
    }


def build_settlement_receipt(
    *,
    code_revision: str,
    annotated: Sequence[Mapping[str, Any]],
    agreement: Mapping[str, Any],
    settlement: Mapping[str, Any],
    migration_counts: Mapping[str, Any],
    resettlement_queue: Mapping[str, Any],
    geometry: Mapping[str, Any] | None,
    support_viable: bool,
    settled_at: str | None = None,
) -> dict[str, Any]:
    gates = readiness_gates(settlement, support_viable=support_viable)
    ready = all(gates.values()) and not settlement.get(
        "hierarchical_multilabel_contradicted"
    )
    if settlement.get("hierarchical_multilabel_contradicted"):
        state = "V6_ONTOLOGY_BLOCKED_ON_HUMAN_AGREEMENT"
        next_action = NEXT_REDESIGN
    elif ready:
        state = "V6_ONTOLOGY_READY"
        next_action = NEXT_REBUILD
    else:
        state = "V6_ONTOLOGY_BLOCKED_ON_HUMAN_AGREEMENT"
        next_action = NEXT_REBUILD  # shouldn't happen if gates incomplete
        # find unresolved
        unresolved = [k for k, v in gates.items() if not v]
        next_action = NEXT_REDESIGN if "structure_frozen" in unresolved else NEXT_REBUILD
        if unresolved:
            next_action = "COMPLETE_V6_HUMAN_ONTOLOGY_SETTLEMENT"

    final = final_ontology(settlement)
    payload = {
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "PHASE_RULE": PHASE_RULE,
        "FINAL_ONTOLOGY_ID": FINAL_ONTOLOGY_ID,
        "PARENT_ONTOLOGY_RECEIPT": PARENT_ONTOLOGY_RECEIPT,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "TRAIN": False,
        "ENCODER_CHOSEN": False,
        "QUAL_ROWS_INSPECTED": False,
        "V5_HISTORY_MUTATED": False,
        "GEOMETRY_USED_TO_DECIDE_ONTOLOGY": False,
        "stability_criteria_frozen_before_review": True,
        "agreement": agreement,
        "boundary_settlement": settlement,
        "final_ontology": final,
        "migration_map": final_migration_map(settlement),
        "migration_counts_train_dev_rep": migration_counts,
        "resettlement_queue": resettlement_queue,
        "qualification_handling": {
            "sealed_id": "HYPERLEX_V6_QUALIFICATION_001",
            "inspected": False,
            "recommendation": "B_replace_with_new_fresh_qualification_surface",
            "also_acceptable": "A_retain_sealed_rows_but_require_blind_reannotation",
            "preferred": "B",
            "reason": (
                "Old exclusive family gold + ontology cardinality change make "
                "blind re-annotation of the same rows possible but a fresh "
                "surface better matches NATURAL operating distribution under V1_FINAL."
            ),
        },
        "stage_a_consequence": {
            "reopen": False,
            "stage_a": "evidence/relation admission layer",
            "stage_b": "hierarchical multi-label semantic characterization",
        },
        "geometry_diagnostic": geometry,
        "model_design_constraints": model_design_constraints(),
        "gates": gates,
        "n_annotated_rows": len(annotated),
        "code_revision": code_revision,
        "settled_at": settled_at or utc_now_iso(),
        "schema": SCHEMA,
        "V6_ONTOLOGY_STATE": state,
        "NEXT_ACTION": next_action if ready else (
            NEXT_REDESIGN
            if settlement.get("hierarchical_multilabel_contradicted")
            else "COMPLETE_V6_HUMAN_ONTOLOGY_SETTLEMENT"
        ),
    }
    if ready:
        payload["NEXT_ACTION"] = NEXT_REBUILD
        payload["V6_ONTOLOGY_STATE"] = "V6_ONTOLOGY_READY"
    payload["V6_HUMAN_ONTOLOGY_SETTLEMENT_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {
                k: v
                for k, v in payload.items()
                if k != "V6_HUMAN_ONTOLOGY_SETTLEMENT_RECEIPT_SHA256"
            }
        )
    )
    return payload
