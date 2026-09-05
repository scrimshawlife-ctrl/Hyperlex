"""Mutation-trace packet + restricted redaction."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

SCHEMA = "hyperlex.mutation_trace.v0.1"


def packet_id_for(surface: str) -> str:
    h = hashlib.sha256((surface or "").encode("utf-8")).hexdigest()
    return "mt-" + h[:16]


def payload_ref_for(surface: str) -> str:
    norm = " ".join((surface or "").lower().split())
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


@dataclass
class MutationTracePacket:
    schema: str = SCHEMA
    packet_id: str = ""
    observed_at: Optional[str] = None
    source: Optional[str] = "cli"
    surface_span: Optional[str] = None
    recovered_lemma: Optional[str] = None
    canonical_gloss: Optional[str] = None
    operators: List[str] = field(default_factory=list)
    layers_touched: List[str] = field(default_factory=list)
    register_shift: str = "none"
    irony_flag: bool = False
    dissociation_flag: bool = False
    algospeak_flag: bool = False
    machine_dialect: bool = False
    affix_family: Optional[str] = None
    decode_confidence: Optional[float] = None
    lexicon_hit: bool = False
    watch_score: Optional[float] = None
    class_: str = "INFERRED"
    restricted_intent_suspected: bool = False
    payload_ref: Optional[str] = None
    forecast_eligible: bool = False
    brier: Optional[Any] = None
    provenance: List[str] = field(default_factory=list)
    receipt_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["class"] = d.pop("class_")
        d["forecast_eligible"] = False
        d["brier"] = None
        return d


def redact_packet(d: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(d)
    out["forecast_eligible"] = False
    out["brier"] = None
    if out.get("restricted_intent_suspected"):
        surface = out.get("surface_span") or ""
        if not out.get("payload_ref"):
            out["payload_ref"] = payload_ref_for(str(surface))
        out["surface_span"] = None
        out["canonical_gloss"] = None
    return out


def dumps(d: Dict[str, Any]) -> str:
    return json.dumps(d, ensure_ascii=False, indent=2)
