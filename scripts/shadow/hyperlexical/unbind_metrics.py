"""Token/slot F1 beside unbind_exact. No torch. Does not invent gold.

Civilian unbind_exact is all-or-nothing on the full filler list. These
secondary scores use the same gold/pred alignment the train val loop
already uses (one predicted filler per gold slot, positional / type_slot
order). name_gate stays false.

Strict keys sit beside the legacy ones. Legacy gold may already be
``mapped_filler`` (OOV → ``<unk>``), so predicting ``<unk>`` on that slot
is a legacy hit. Strict gold is the raw lowercased filler, and a ``<unk>``
prediction is always a miss. Ladder selection still reads ``unbind_exact``.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping, Sequence

from .layout import UNK


def _tokens(fillers: Sequence[str] | None) -> list[str]:
    return [str(item) for item in (fillers or [])]


# Not a filler. Keeps an unk prediction from matching gold or another unk.
_UNK_MISS = "\x00"


def strict_pair(gold: Sequence[str], pred: Sequence[str]) -> tuple[list[str], list[str]]:
    """Lowercased raw gold. A ``<unk>`` prediction never matches."""
    g = [str(item).lower() for item in gold]
    p: list[str] = []
    for item in pred:
        tok = str(item).lower()
        p.append(_UNK_MISS if tok == UNK else tok)
    return g, p


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


def _score_pairs(
    pairs: Iterable[tuple[Sequence[str], Sequence[str]]],
    *,
    strict: bool,
) -> dict[str, float | int]:
    """Row-level exact plus micro token/slot F1.

    Skips rows with an empty gold list (same as train val). Empty series
    returns zeros, matching unbind_exact = 0 / max(1, n).
    """
    exact_hit = exact_n = 0
    tok_tp = tok_p = tok_g = 0
    slot_tp = slot_p = slot_g = 0
    for gold, pred in pairs:
        if strict:
            g, p = strict_pair(gold, pred)
        else:
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


def summarize_unbind_pairs(
    pairs: Iterable[tuple[Sequence[str], Sequence[str]]],
    *,
    strict_pairs: Iterable[tuple[Sequence[str], Sequence[str]]] | None = None,
) -> dict[str, float | int]:
    """Legacy unbind metrics plus strict keys.

    ``strict_pairs`` is the raw-filler series (one row per legacy row).
    When omitted, strict rules apply to ``pairs`` themselves. Legacy keys
    are scored on ``pairs`` unchanged.
    """
    rows = list(pairs)
    legacy = _score_pairs(rows, strict=False)
    strict_src = rows if strict_pairs is None else strict_pairs
    strict = _score_pairs(strict_src, strict=True)
    legacy.update(
        {
            "unbind_exact_strict": strict["unbind_exact"],
            "unbind_token_f1_strict": strict["unbind_token_f1"],
            "unbind_token_precision_strict": strict["unbind_token_precision"],
            "unbind_token_recall_strict": strict["unbind_token_recall"],
            "unbind_slot_f1_strict": strict["unbind_slot_f1"],
        }
    )
    return legacy


def null_unbind_secondary() -> dict[str, None]:
    """004 probe stub/digest: no civilian filler lists, so F1 is not computable."""
    return {
        "unbind_token_f1": None,
        "unbind_token_precision": None,
        "unbind_token_recall": None,
        "unbind_slot_f1": None,
        "unbind_exact_strict": None,
        "unbind_token_f1_strict": None,
        "unbind_token_precision_strict": None,
        "unbind_token_recall_strict": None,
        "unbind_slot_f1_strict": None,
    }
