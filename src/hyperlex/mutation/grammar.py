"""Offline v0.1 parser: AFFIX, SUBSTITUTE, REGISTER_SHIFT, EGGCORN, COMPOSE."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .operators import (
    EGGCORN_PHRASES,
    FRAME_MARKERS,
    LAYER_FOR_OP,
    PRODUCTIVE_AFFIXES,
    REGISTER_MARKERS,
    SUBSTITUTE_TERMS,
)
from .packet import MutationTracePacket, packet_id_for, payload_ref_for, redact_packet
from .watch import watch_score


def _norm(text: str) -> str:
    return " ".join((text or "").lower().split())


def parse_mutation_trace(
    text: str,
    *,
    source: str = "cli",
    restricted_intent_suspected: bool = False,
) -> Dict[str, Any]:
    raw = text or ""
    norm = _norm(raw)
    ops: List[str] = []
    affix_hit: Optional[str] = None
    recovered: Optional[str] = None
    lexicon_hit = False
    algospeak = False
    irony = False
    dissociation = False
    register = "none"
    decode = 0.35
    claim = "INFERRED"

    if not norm:
        pkt = MutationTracePacket(
            packet_id=packet_id_for(""),
            source=source,
            surface_span=raw or None,
            operators=[],
            layers_touched=[],
            class_="OBSERVED",
            decode_confidence=0.0,
            watch_score=0.0,
            provenance=["empty-input"],
        )
        return redact_packet(pkt.to_dict())

    for phrase in EGGCORN_PHRASES:
        if phrase in norm:
            ops.append("EGGCORN")
            recovered = phrase
            decode = max(decode, 0.7)
            claim = "OBSERVED"
            break

    for marker in REGISTER_MARKERS:
        if marker in norm:
            ops.append("REGISTER_SHIFT")
            register = "med" if marker.startswith("it's") or marker.startswith("its") else "low"
            if marker in {"it's giving", "its giving"}:
                register = "high"
                irony = True
            decode = max(decode, 0.62)
            break

    for marker in FRAME_MARKERS:
        if marker in norm:
            dissociation = True
            irony = True
            # Flag only in v0.1 — FRAME_WRAP parser deferred; still record feature.
            break

    tokens = re.findall(r"[a-z0-9']+", norm)
    for tok in tokens:
        if tok in SUBSTITUTE_TERMS:
            ops.append("SUBSTITUTE")
            lexicon_hit = True
            recovered = recovered or tok
            if tok in {"unalive"}:
                algospeak = True
            decode = max(decode, 0.72)
            claim = "OBSERVED" if claim != "INFERRED" or True else claim
            claim = "OBSERVED"
            break

    for suf in PRODUCTIVE_AFFIXES:
        if re.search(rf"\b[a-z0-9']{{2,}}{re.escape(suf)}\b", norm) or re.search(
            rf"\b[a-z0-9']+\s+{re.escape(suf)}\b", norm
        ):
            ops.append("AFFIX")
            affix_hit = suf
            decode = max(decode, 0.68)
            claim = "OBSERVED"
            break
        # bare suffix mention as productivity signal ("-maxxing")
        if suf in tokens or f"-{suf}" in norm:
            ops.append("AFFIX")
            affix_hit = suf
            decode = max(decode, 0.6)
            claim = "OBSERVED"
            break

    # unique preserve order
    seen = set()
    uniq: List[str] = []
    for op in ops:
        if op not in seen:
            seen.add(op)
            uniq.append(op)
    ops = uniq
    if len(ops) >= 2:
        ops.append("COMPOSE")

    layers: List[str] = []
    for op in ops:
        layer = LAYER_FOR_OP.get(op)
        if layer and layer not in layers:
            layers.append(layer)

    ws = watch_score(
        decode_confidence=decode,
        n_ops=len([o for o in ops if o != "COMPOSE"]) + (1 if "COMPOSE" in ops else 0),
        register_shift=register,
        irony_flag=irony,
        affix_productivity=bool(affix_hit),
        lexicon_hit=lexicon_hit,
    )

    pkt = MutationTracePacket(
        packet_id=packet_id_for(norm),
        source=source,
        surface_span=raw,
        recovered_lemma=recovered,
        operators=ops,
        layers_touched=layers,
        register_shift=register,
        irony_flag=irony,
        dissociation_flag=dissociation,
        algospeak_flag=algospeak,
        affix_family=affix_hit,
        decode_confidence=round(decode, 4),
        lexicon_hit=lexicon_hit,
        watch_score=ws,
        class_=claim if ops else "OBSERVED",
        restricted_intent_suspected=bool(restricted_intent_suspected),
        payload_ref=payload_ref_for(norm) if restricted_intent_suspected else None,
        provenance=["hyperlex.mutation.grammar.v0.1"],
    )
    return redact_packet(pkt.to_dict())
