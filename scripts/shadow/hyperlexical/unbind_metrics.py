"""Token/slot F1 beside unbind_exact. No torch. Does not invent gold.

Civilian unbind_exact is all-or-nothing on the full filler list. These
secondary scores use the same gold/pred alignment the train val loop
already uses (one predicted filler per gold slot, positional / type_slot
order). name_gate stays false.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping, Sequence

from .layout import UNK


def _tokens(fillers: Sequence[str] | None) -> list[str]:
    return [str(item) for item in (fillers or [])]


def mapped_filler(maps: Mapping[str, Any], fill: str) -> str:
    """Gold surface through filler_vocab. Missing → UNK, same as exact."""
    vocab = maps["filler_vocab"]
    idx = maps["filler_of"].get(fill, maps["filler_of"][UNK])
    return vocab[idx]


def mapped_pred(maps: Mapping[str, Any], pred_id: int) -> str:
    """Predicted id through filler_vocab. Out of range → UNK."""
    vocab = maps["filler_vocab"]
    idx = int(pred_id)
    if 0 <= idx < len(vocab):
        return vocab[idx]
    return vocab[maps["filler_of"][UNK]]


def token_multiset_counts(
    gold: Sequence[str], pred: Sequence[str]
) -> tuple[int, int, int]:
    """Bag-of-filler overlap. Returns (tp, pred_n, gold_n)."""
    g, p = _tokens(gold), _tokens(pred)
    return sum((Counter(g) & Counter(p)).values()), len(p), len(g)


def slot_counts(gold: Sequence[str], pred: Sequence[str]) -> tuple[int, int, int]:
    """Order-sensitive slot match. Index is the role when roles exist.

    Treats (position, filler) as the slot. Same-length alignment as exact:
    zip for TP, leftover pred slots as FP, leftover gold slots as FN.
    """
    g, p = _tokens(gold), _tokens(pred)
    n = min(len(g), len(p))
    tp = sum(1 for i in range(n) if g[i] == p[i])
    return tp, len(p), len(g)


def _prf(tp: int, pred_n: int, gold_n: int) -> tuple[float, float, float]:
    precision = tp / pred_n if pred_n else 0.0
    recall = tp / gold_n if gold_n else 0.0
    if precision + recall == 0:
        return precision, recall, 0.0
    return precision, recall, 2 * precision * recall / (precision + recall)


def summarize_unbind_pairs(
    pairs: Iterable[tuple[Sequence[str], Sequence[str]]],
) -> dict[str, float | int]:
    """Row-level unbind_exact plus micro token/slot F1.

    Skips rows with an empty gold list (same as train val). Empty series
    returns zeros, matching unbind_exact = 0 / max(1, n).
    """
    exact_hit = exact_n = 0
    tok_tp = tok_p = tok_g = 0
    slot_tp = slot_p = slot_g = 0
    for gold, pred in pairs:
        g, p = _tokens(gold), _tokens(pred)
        if not g:
            continue
        exact_hit += int(g == p)
        exact_n += 1
        tp, pn, gn = token_multiset_counts(g, p)
        tok_tp += tp
        tok_p += pn
        tok_g += gn
        stp, spn, sgn = slot_counts(g, p)
        slot_tp += stp
        slot_p += spn
        slot_g += sgn
    tok_p_, tok_r, tok_f1 = _prf(tok_tp, tok_p, tok_g)
    _, _, slot_f1 = _prf(slot_tp, slot_p, slot_g)
    return {
        "unbind_exact": exact_hit / max(1, exact_n),
        "n_unbind_eval": exact_n,
        "unbind_token_f1": tok_f1,
        "unbind_token_precision": tok_p_,
        "unbind_token_recall": tok_r,
        "unbind_slot_f1": slot_f1,
    }


def null_unbind_secondary() -> dict[str, None]:
    """004 probe stub/digest: no civilian filler lists, so F1 is not computable."""
    return {
        "unbind_token_f1": None,
        "unbind_token_precision": None,
        "unbind_token_recall": None,
        "unbind_slot_f1": None,
    }
