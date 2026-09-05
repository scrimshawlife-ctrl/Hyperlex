"""Civilian advisory cards from mutation-trace packets. Not forecasts."""
from __future__ import annotations

from typing import Any, Dict, List

_OP_BLURB = {
    "SUBSTITUTE": "known slang / algospeak swap",
    "AFFIX": "productive suffix",
    "EGGCORN": "folk reanalysis",
    "PHONETIC_WARP": "vowel-drop / compressed slang atom",
    "GAME_ENCODE": "language-game or leet framing (detect only)",
    "REGISTER_SHIFT": "informal-register marker",
    "CODE_SWITCH": "mixed script or bilingual particle + slang",
    "FRAME_WRAP": "dissociation / lore frame (flag only)",
    "COMPOSE": "two or more operators stacked",
    "CLIP_BLEND": "clip / blend (not parsed in v0.2)",
}


def format_human_card(packet: Dict[str, Any]) -> str:
    ops: List[str] = list(packet.get("operators") or [])
    layers = list(packet.get("layers_touched") or [])
    restricted = bool(packet.get("restricted_intent_suspected"))
    if restricted:
        surface = "(redacted — restricted flag; payload_ref only)"
    else:
        surface = packet.get("surface_span") or "(empty)"
    recovered = packet.get("recovered_lemma") or "—"
    watch = packet.get("watch_score")
    watch_s = "—" if watch is None else f"{watch}"
    blurbs = [_OP_BLURB.get(op, op) for op in ops] if ops else ["no operators"]
    lines = [
        "MUTATION TRACE (SHADOW advisory — not a forecast)",
        f"Surface: {surface}",
        f"Operators: {' · '.join(ops) if ops else '(none)'}",
        f"Layers: {' · '.join(layers) if layers else '(none)'}",
        f"What fired: {'; '.join(blurbs)}",
        f"Recovered lemma: {recovered}",
        f"Watch score: {watch_s} — instrumentation, not P(harm), not a tool-fire threshold",
        "Brier: null",
        "Forecast eligible: no",
        f"Restricted: {'yes' if restricted else 'no'}",
        "Lane: SHADOW / advisory. Hosts must not execute this card.",
    ]
    return "\n".join(lines) + "\n"
