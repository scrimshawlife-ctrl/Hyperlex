"""Per-family classify errors. Does not train, does not move BEST, does not touch the ledger.

OBSERVED and INFERRED stay separate. ``none`` stays in the confusion table and
out of macro-F1, matching ``classify_macro_f1_nonnone``.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from .classify_metrics import macro_f1_nonnone, per_class_table
from .layout import FAMILIES

NONE = "none"
OBSERVED = "OBSERVED"
INFERRED = "INFERRED"


def confusion_matrix(gold: Sequence[str], pred: Sequence[str]) -> dict[str, dict[str, int]]:
    labels = list(dict.fromkeys([*FAMILIES, *gold, *pred]))
    table = {label: {other: 0 for other in labels} for label in labels}
    for left, right in zip(gold, pred, strict=True):
        table[left][right] += 1
    return {label: {other: count for other, count in row.items() if count} for label, row in table.items() if any(row.values())}


def _slice_report(rows: Sequence[Mapping[str, str]]) -> dict[str, Any] | None:
    if not rows:
        return None
    gold = [row["gold"] for row in rows]
    pred = [row["pred"] for row in rows]
    hits = sum(int(left == right) for left, right in zip(gold, pred))
    non_none = [row for row in rows if row["gold"] != NONE]
    none_predictions = sum(int(row["pred"] == NONE) for row in non_none)
    errors = Counter((row["gold"], row["pred"]) for row in rows if row["gold"] != row["pred"])
    return {
        "accuracy": hits / len(rows),
        "classify_macro_f1_nonnone": macro_f1_nonnone(gold, pred),
        "confusion": confusion_matrix(gold, pred),
        "error_clusters": [
            {"gold": left, "n": count, "pred": right}
            for (left, right), count in errors.most_common()
        ],
        "families": per_class_table(gold, pred, labels=FAMILIES),
        "n": len(rows),
        "none_prediction_rate_on_non_none": None if not non_none else none_predictions / len(non_none),
    }


def error_report(rows: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    """One surface. Each row carries ``gold``, ``pred``, and ``evidence``."""
    for row in rows:
        if row.get("evidence") not in {OBSERVED, INFERRED}:
            raise ValueError(f"evidence must be {OBSERVED} or {INFERRED}")
    return {
        "all": _slice_report(rows),
        "inferred": _slice_report([row for row in rows if row["evidence"] == INFERRED]),
        "observed": _slice_report([row for row in rows if row["evidence"] == OBSERVED]),
    }


def label_prior(rows: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    """Train or val label counts. ``lineage`` is the family. ``class`` is the evidence."""
    counts: dict[str, dict[str, int]] = {}
    for row in rows:
        family = str(row.get("lineage") or NONE)
        evidence = str(row.get("class") or "")
        bucket = counts.setdefault(family, {INFERRED: 0, OBSERVED: 0})
        if evidence in bucket:
            bucket[evidence] += 1
    return counts


def _predict(checkpoint: Path, texts: list[str]) -> list[str]:
    import torch
    from torch import nn

    from .loop import _require_local_model, freeze_encoder, warm_load_checkpoint
    from .select_006_reserve_eval import TRUNK, WARM, _checkpoint_vocabs

    role_vocab, filler_vocab = _checkpoint_vocabs(checkpoint)
    maps = {
        "families": list(FAMILIES),
        "family_of": {family: index for index, family in enumerate(FAMILIES)},
        "filler_of": {filler: index for index, filler in enumerate(filler_vocab)},
        "filler_vocab": filler_vocab,
        "role_of": {role: index for index, role in enumerate(role_vocab)},
        "role_vocab": role_vocab,
    }
    tok, encoder = _require_local_model(TRUNK)
    freeze_encoder(encoder)
    classify = nn.Linear(768, len(FAMILIES))
    role_head = nn.Linear(768, len(role_vocab))
    filler_head = nn.Linear(768, len(filler_vocab))
    warm_load_checkpoint(encoder, classify, role_head, filler_head, maps, WARM, expand_vocab=True)
    overlay = warm_load_checkpoint(
        encoder, classify, role_head, filler_head, maps, checkpoint, expand_vocab=False
    )
    if overlay.get("encoder_trainable_loaded") != overlay.get("encoder_trainable_present"):
        raise RuntimeError("checkpoint encoder tensors did not load")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    for module in (encoder, classify):
        module.to(device)
        module.eval()
    predictions: list[str] = []
    with torch.no_grad():
        for text in texts:
            encoded = tok([text], padding=True, truncation=True, max_length=64, return_tensors="pt")
            encoded = {key: value.to(device) for key, value in encoded.items()}
            pred_id = int(classify(encoder(**encoded).last_hidden_state[:, 0]).argmax(-1)[0])
            predictions.append(FAMILIES[pred_id])
    return predictions


def _val_rows(export: Path) -> list[dict[str, str]]:
    rows = []
    for line in export.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("split") != "val" or row.get("task") not in {"classify", "classify+unbind"}:
            continue
        evidence = row.get("class")
        if evidence not in {OBSERVED, INFERRED}:
            continue
        rows.append({"evidence": evidence, "gold": str(row.get("lineage") or NONE), "text": str(row["text"])})
    return rows


def audit_checkpoint(checkpoint: Path, export: Path) -> dict[str, Any]:
    from .select_006_reserve_eval import reserve_examples

    reserve = [row for row in reserve_examples() if row["task"] == "classify"]
    val = _val_rows(export)
    texts = [row["text"] for row in reserve] + [row["text"] for row in val]
    preds = _predict(checkpoint, texts)
    reserve_preds = preds[: len(reserve)]
    val_preds = preds[len(reserve) :]
    reserve_rows = [
        {"evidence": str(row["class"]), "gold": str(row["lineage"]), "pred": pred}
        for row, pred in zip(reserve, reserve_preds)
    ]
    val_rows = [
        {"evidence": row["evidence"], "gold": row["gold"], "pred": pred}
        for row, pred in zip(val, val_preds)
    ]
    return {
        "checkpoint": str(checkpoint),
        "reserve": error_report(reserve_rows),
        "val": error_report(val_rows),
    }


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 3:
        raise SystemExit("usage: checkpoint export dest")
    payload = audit_checkpoint(Path(args[0]), Path(args[1]))
    dest = Path(args[2])
    dest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
