"""Build and validate hyperlex.hyperlexical.inference.v0.1 packets."""

from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA = "hyperlex.hyperlexical.inference.v0.1"
FORBIDDEN = {"symbolic", "has_symbols"}
ROUTES = frozenset({"form", "lexical"})
STAGES = frozenset({"noise", "circulating", "contested", "hyperstition_ish"})
SCHEMES = frozenset({"positional", "type_slot"})
CLASSES = frozenset({"OBSERVED", "INFERRED", "SPECULATIVE"})
RESTRICTED_MARKER = "__RESTRICTED_FIXTURE__"
REFUSAL_MARKERS = (
    "i cannot analyze",
    "i'm sorry, but i can't",
    "i am unable to",
    "as an ai",
)


class PacketError(ValueError):
    pass


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _routes(claimed: list[str] | None) -> list[str]:
    routes = list(claimed or ["form", "lexical"])
    if not routes:
        raise PacketError("routes_claimed empty")
    bad = [r for r in routes if r not in ROUTES]
    if bad:
        raise PacketError(f"forbidden route {bad}")
    return routes


def build_packet(
    text: str | None,
    *,
    restricted: bool = False,
    role_scheme: str | None = "positional",
    typology: list[str] | None = None,
    stage: str | None = None,
    class_: str = "INFERRED",
) -> dict[str, Any]:
    surface = text if text is not None else ""
    flagged = bool(restricted) or RESTRICTED_MARKER in surface
    if flagged:
        ref_src = surface or RESTRICTED_MARKER
        packet: dict[str, Any] = {
            "schema": SCHEMA,
            "model_id": "stub",
            "embed_mode": "STATIC_HASH_EMBEDDING",
            "selection_proxy": "unspecified",
            "param_count": 0,
            "surface": None,
            "payload_ref": sha256_hex(ref_src),
            "lineage_family": None,
            "lineage_confidence": None,
            "typology": [],
            "stage": None,
            "role_scheme": None,
            "unbind_ok": False,
            "unbind": None,
            "routes_claimed": ["form"],
            "restricted_intent_suspected": True,
            "brier": None,
            "forecast_eligible": False,
            "auto_fire": False,
            "class": "INFERRED",
        }
        validate_packet(packet)
        return packet

    packet = {
        "schema": SCHEMA,
        "model_id": "stub",
        "embed_mode": "STATIC_HASH_EMBEDDING",
        "input_hash": sha256_hex(surface),
        "vector_hash": sha256_hex("stub-vector:" + surface),
        "selection_proxy": "unspecified",
        "param_count": 0,
        "surface": surface,
        "payload_ref": None,
        "lineage_family": "none",
        "lineage_confidence": 0.0,
        "typology": list(typology or []),
        "stage": stage,
        "role_scheme": role_scheme,
        "unbind_ok": False,
        "unbind": None,
        "routes_claimed": ["form", "lexical"],
        "restricted_intent_suspected": False,
        "brier": None,
        "forecast_eligible": False,
        "auto_fire": False,
        "class": class_,
    }
    validate_packet(packet)
    return packet


def validate_packet(packet: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(packet, dict):
        raise PacketError("packet must be object")
    hit = FORBIDDEN.intersection(packet)
    if hit:
        raise PacketError(f"forbidden keys {sorted(hit)}")
    if packet.get("schema") != SCHEMA:
        raise PacketError("bad schema")
    if packet.get("brier") is not None:
        raise PacketError("brier must be null")
    if packet.get("forecast_eligible") is not False:
        raise PacketError("forecast_eligible must be false")
    if packet.get("auto_fire") is not False:
        raise PacketError("auto_fire must be false")
    if packet.get("class") not in CLASSES:
        raise PacketError("bad class")
    routes = packet.get("routes_claimed")
    if not isinstance(routes, list) or not routes:
        raise PacketError("routes_claimed required")
    if any(r not in ROUTES for r in routes):
        raise PacketError("semantic or unknown route")
    scheme = packet.get("role_scheme")
    if scheme is not None and scheme not in SCHEMES:
        raise PacketError("bad role_scheme")
    stage = packet.get("stage")
    if stage is not None and stage not in STAGES:
        raise PacketError("bad stage")
    if packet.get("restricted_intent_suspected") is True:
        if packet.get("surface") is not None:
            raise PacketError("restricted packet must drop surface")
        ref = packet.get("payload_ref")
        if not isinstance(ref, str) or len(ref) != 64:
            raise PacketError("restricted packet needs payload_ref")
    if packet.get("embed_mode") == "MODEL_EMBEDDING":
        for key in ("model_id", "input_hash", "vector_hash"):
            if not packet.get(key):
                raise PacketError(f"MODEL_EMBEDDING missing {key}")
    blob = json.dumps(packet, sort_keys=True)
    low = blob.lower()
    for marker in REFUSAL_MARKERS:
        if marker in low:
            raise PacketError("refusal string in packet")
    return packet


def attach_or_omit(packet: dict[str, Any] | None) -> dict[str, Any] | None:
    """Fail-open analyze attachment. Empty/invalid → omit."""
    if not packet:
        return None
    try:
        validate_packet(packet)
    except PacketError:
        return None
    return {"analysis": {"hyperlexical": packet}}
