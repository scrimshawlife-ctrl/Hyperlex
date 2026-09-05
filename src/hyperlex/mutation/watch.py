"""Instrumentation scores. Not probabilities. Not Brier."""
from __future__ import annotations

_REGISTER_W = {"none": 0.0, "low": 0.33, "med": 0.66, "high": 1.0}


def clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def watch_score(
    *,
    decode_confidence: float,
    n_ops: int,
    register_shift: str,
    irony_flag: bool,
    affix_productivity: bool,
    lexicon_hit: bool,
) -> float:
    register_w = _REGISTER_W.get(register_shift or "none", 0.0)
    lexicon_only = 1.0 if (lexicon_hit and int(n_ops) <= 1) else 0.0
    raw = (
        0.35 * float(decode_confidence)
        + 0.15 * (min(int(n_ops), 4) / 4.0)
        + 0.20 * register_w
        + 0.10 * (1.0 if irony_flag else 0.0)
        + 0.15 * (1.0 if affix_productivity else 0.0)
        + 0.15 * (0.0 if lexicon_only else 1.0)
    )
    return round(clip01(raw), 4)
