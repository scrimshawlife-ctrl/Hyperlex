"""Predict next surface-form mutations for slang atoms.

Deterministic offline operators + optional pre-fetched LLM candidates.
Always SPECULATIVE; always brier null.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Sequence

SCHEMA = "hyperlex.mutation_prediction.v1"
NOTE = (
    "Next surface forms are speculative. Not calibrated probabilities / Brier."
)

OPERATORS = frozenset({
    "platform_compression",
    "derivational",
    "irony_inversion",
    "compound_phrase",
    "sense_extension",
    "cross_family_borrowing",
    "extra-grammatical",
})

_FAMILY_SUFFIXES: Dict[str, List[str]] = {
    "brainrot-aura": ["core", "maxxing", "posting", "points"],
    "political-status": ["pilled", "maxxing"],
    "gaming-meta": ["diff", "core"],
    "ai-native": ["slop", "core", "maxxing"],
    "crypto-degen": ["season", "core"],
    "workplace-corp": ["core"],
    "betting-sharp": ["core"],
    "kinship-address": [],
}

_GENERAL_SUFFIXES = ["ed", "ing", "er", "y"]
_VOWELS = set("aeiouAEIOU")


def _max_candidates(override: Optional[int] = None) -> int:
    if override is not None:
        n = int(override)
    else:
        raw = os.environ.get("HYPERLEX_MUTATION_MAX", "8").strip() or "8"
        try:
            n = int(raw)
        except ValueError:
            n = 8
    return max(1, min(20, n))


def _norm_form(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _norm_key(s: str) -> str:
    return _norm_form(s).lower()


def _vowel_drop(seed: str) -> Optional[str]:
    if len(seed) < 4 or " " in seed:
        return None
    chars = []
    for i, ch in enumerate(seed):
        if i > 0 and i < len(seed) - 1 and ch in _VOWELS:
            continue
        chars.append(ch)
    out = "".join(chars)
    if out.lower() == seed.lower() or len(out) < 2:
        return None
    return out


def _deterministic_candidates(
    seed: str,
    *,
    family_id: Optional[str],
    family_terms: Sequence[str],
    family_operator: Optional[str],
) -> List[Dict[str, Any]]:
    seed_disp = _norm_form(seed)
    seed_key = _norm_key(seed)
    attested = {_norm_key(t) for t in family_terms if t}
    out: List[Dict[str, Any]] = []

    def add(form: str, operator: str, confidence: float, rationale: str) -> None:
        f = _norm_form(form)
        if not f or _norm_key(f) == seed_key:
            return
        if operator not in OPERATORS:
            operator = "extra-grammatical"
        conf = float(confidence)
        already = _norm_key(f) in attested
        if already:
            conf *= 0.45
            rationale = f"{rationale} (already attested in family; down-ranked)"
        conf = max(0.05, min(0.95, conf))
        out.append({
            "form": f,
            "operator": operator,
            "confidence": round(conf, 4),
            "provenance": "SPECULATIVE",
            "source": "deterministic",
            "rationale": rationale,
            "already_attested": already,
        })

    vd = _vowel_drop(seed_disp)
    if vd:
        add(vd, "platform_compression", 0.38, "vowel-drop compression of seed")

    suffixes = list(_GENERAL_SUFFIXES)
    suffixes.extend(_FAMILY_SUFFIXES.get(family_id or "", []))
    base = seed_disp.rstrip("e") if seed_disp.endswith("e") and len(seed_disp) > 3 else seed_disp
    for suf in suffixes:
        if suf in {"ed", "ing", "er", "y"}:
            form = base + suf if not seed_disp.endswith(suf) else ""
        else:
            form = f"{seed_disp}{suf}" if not seed_disp.endswith(suf) else ""
        if form:
            add(form, "derivational", 0.40, f"derivational suffix -{suf}")

    if (
        family_id in {"brainrot-aura", "political-status", "gaming-meta"}
        or family_operator == "irony_inversion"
    ):
        add(f"negative {seed_disp}", "irony_inversion", 0.44, "polarity / status flip template")
        add(f"{seed_disp} points", "irony_inversion", 0.41, "quantified status template")
        add(f"mid {seed_disp}", "irony_inversion", 0.36, "mid-status compression template")

    co_terms = [t for t in family_terms if t and _norm_key(t) != seed_key][:6]
    for co in co_terms[:4]:
        add(f"{seed_disp} {co}", "compound_phrase", 0.37, f"compound with family co-term {co}")
        add(f"{co} {seed_disp}", "compound_phrase", 0.35, f"compound with family co-term {co}")

    return out


def _merge_llm(
    deterministic: List[Dict[str, Any]],
    llm_candidates: Optional[Sequence[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    merged = list(deterministic)
    if not llm_candidates:
        return merged
    for raw in llm_candidates:
        if not isinstance(raw, dict):
            continue
        form = _norm_form(str(raw.get("form") or raw.get("term") or ""))
        if not form:
            continue
        op = str(raw.get("operator") or raw.get("formation") or "extra-grammatical")
        if op not in OPERATORS:
            op = "extra-grammatical"
        try:
            conf = float(raw.get("confidence") or 0.35)
        except (TypeError, ValueError):
            conf = 0.35
        conf = max(0.05, min(0.9, conf))
        merged.append({
            "form": form,
            "operator": op,
            "confidence": round(conf, 4),
            "provenance": "SPECULATIVE",
            "source": "llm",
            "rationale": str(raw.get("rationale") or "governed LLM mutation candidate"),
        })
    return merged


def _rank_and_cap(
    candidates: List[Dict[str, Any]],
    *,
    seed_key: str,
    max_n: int,
) -> List[Dict[str, Any]]:
    best: Dict[str, Dict[str, Any]] = {}
    for c in candidates:
        key = _norm_key(str(c.get("form") or ""))
        if not key or key == seed_key:
            continue
        prev = best.get(key)
        if prev is None:
            best[key] = c
            continue
        pc, cc = float(prev.get("confidence") or 0), float(c.get("confidence") or 0)
        if cc > pc:
            best[key] = c
        elif cc == pc and prev.get("source") == "llm" and c.get("source") == "deterministic":
            best[key] = c

    ranked = list(best.values())
    ranked.sort(
        key=lambda c: (
            -float(c.get("confidence") or 0),
            0 if c.get("source") == "deterministic" else 1,
            str(c.get("form") or ""),
        )
    )
    cleaned = []
    for c in ranked[:max_n]:
        row = dict(c)
        row.pop("already_attested", None)
        cleaned.append(row)
    return cleaned


def predict_mutations(
    seed_term: str,
    *,
    family_id: Optional[str] = None,
    family_terms: Optional[Sequence[str]] = None,
    family_operator: Optional[str] = None,
    max_candidates: Optional[int] = None,
    llm_candidates: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Predict next surface forms for a slang atom.

    Returns hyperlex.mutation_prediction.v1 dict. Always brier=null.
    """
    seed = _norm_form(seed_term)
    max_n = _max_candidates(max_candidates)
    empty = {
        "schema": SCHEMA,
        "seed_term": seed,
        "family_id": family_id,
        "family_operator": family_operator,
        "candidates": [],
        "n_candidates": 0,
        "brier": None,
        "provenance": "SPECULATIVE",
        "note": NOTE,
    }
    if not seed:
        empty["error"] = "empty seed"
        return empty

    terms = list(family_terms or [])
    det = _deterministic_candidates(
        seed,
        family_id=family_id,
        family_terms=terms,
        family_operator=family_operator,
    )
    merged = _merge_llm(det, llm_candidates)
    ranked = _rank_and_cap(merged, seed_key=_norm_key(seed), max_n=max_n)
    return {
        "schema": SCHEMA,
        "seed_term": seed,
        "family_id": family_id,
        "family_operator": family_operator,
        "candidates": ranked,
        "n_candidates": len(ranked),
        "brier": None,
        "provenance": "SPECULATIVE",
        "note": NOTE,
    }
