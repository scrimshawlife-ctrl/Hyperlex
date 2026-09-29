"""Score one SELECT-005 checkpoint on the frozen reserve.

This module does not train, does not append the ledger, and does not move BEST.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping

from .align import atom_token_index, pool_indices
from .classify_metrics import macro_f1_nonnone
from .holdout_guard import normalized_text_sha256
from .layout import FAMILIES, HIDDEN, MAX_LEN
from .loop import (
    _offsets,
    _require_local_model,
    freeze_encoder,
    warm_load_checkpoint,
)
from .unbind_metrics import mapped_filler, mapped_pred, summarize_unbind_pairs

EXPERIMENT_ID = "HLX-EXP-2026-09-27-SELECT-005"
MANIFEST = Path(
    "/home/morpheus/hlx-private/exp-20260927-select-005/source-fetch-001/RESERVE_MANIFEST.json"
)
FETCH_ROUTING = Path(
    "/home/morpheus/hlx-private/exp-20260927-select-005/source-fetch-001/ROUTING_RECORDS.jsonl"
)
HARVEST_ROUTING = Path(
    "/home/morpheus/hlx-private/exp-20260927-select-005/harvest-002/ROUTING_RECORDS.jsonl"
)
FETCH_RAW = Path(
    "/home/morpheus/hlx-private/exp-20260927-select-005/source-fetch-001/RAW_CANDIDATES.jsonl"
)
HARVEST_RAW = Path(
    "/home/morpheus/hlx-private/exp-20260927-select-005/harvest-002/RAW_HARVEST.jsonl"
)
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
EXPECTED_COUNTS = {
    "classify": 51,
    "classify_non_none": 11,
    "classify_observed": 11,
    "unbind_clean": 27,
}


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def reserve_examples() -> list[dict[str, Any]]:
    """Join the frozen manifest to text and routing. Refuse a partial join."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("experiment_id") != EXPERIMENT_ID:
        raise SystemExit("EVALUATION_FAILURE: manifest experiment")
    routing: dict[str, dict[str, Any]] = {}
    for path in (HARVEST_ROUTING, FETCH_ROUTING):
        for record in _rows(path):
            digest = str(record.get("normalized_identity") or "")
            if digest:
                routing[digest] = record
    text_by_hash: dict[str, str] = {}
    fillers_by_hash: dict[str, list[str]] = {}
    for record in _rows(HARVEST_RAW):
        text = record.get("text")
        if isinstance(text, str):
            text_by_hash[normalized_text_sha256(text)] = text
    for record in _rows(FETCH_RAW):
        text = record.get("normalized_text")
        if not isinstance(text, str):
            continue
        digest = normalized_text_sha256(text)
        text_by_hash[digest] = text
        tokens = record.get("source_lemma_tokens")
        if isinstance(tokens, list):
            fillers_by_hash[digest] = [str(token) for token in tokens]
    examples = []
    for row in manifest["rows"]:
        digest = str(row["text_hash"])
        route = routing.get(digest)
        text = text_by_hash.get(digest)
        if route is None or text is None:
            raise SystemExit("EVALUATION_FAILURE: reserve row is not joined")
        if str(route.get("row_id")) != str(row["row_id"]):
            raise SystemExit("EVALUATION_FAILURE: row id mismatch")
        if sorted(route.get("slices") or []) != sorted(row.get("slices") or []):
            raise SystemExit("EVALUATION_FAILURE: slice mismatch")
        examples.append(
            {
                "class": route.get("class"),
                "fillers": fillers_by_hash.get(digest, []),
                "lineage": route.get("lineage"),
                "slices": list(row.get("slices") or []),
                "task": route.get("task"),
                "text": text,
                "unbind_clean": bool(route.get("unbind_clean")),
            }
        )
    if len(examples) != 78:
        raise SystemExit("EVALUATION_FAILURE: reserve count")
    return examples


def _checkpoint_vocabs(arm_dir: Path) -> tuple[list[str], list[str]]:
    """Read the restored checkpoint config. The final layout.json has no vocabs."""
    path = arm_dir / "config.json"
    if not path.is_file():
        raise SystemExit("EVALUATION_FAILURE: checkpoint config is absent")
    config = json.loads(path.read_text(encoding="utf-8"))
    role = config.get("role_vocab")
    filler = config.get("filler_vocab")
    if not isinstance(role, list) or not isinstance(filler, list) or not role or not filler:
        raise SystemExit("EVALUATION_FAILURE: checkpoint vocabs are absent")
    return [str(item) for item in role], [str(item) for item in filler]


def _load(arm_dir: Path):
    import torch
    from torch import nn

    role_vocab, filler_vocab = _checkpoint_vocabs(arm_dir)
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
    classify = nn.Linear(HIDDEN, len(FAMILIES))
    role_head = nn.Linear(HIDDEN, len(role_vocab))
    filler_head = nn.Linear(HIDDEN, len(filler_vocab))
    warm_load_checkpoint(encoder, classify, role_head, filler_head, maps, arm_dir)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    for module in (encoder, classify, role_head, filler_head):
        module.to(device)
        module.eval()
    return tok, encoder, classify, filler_head, maps, device


def score_arm(arm_dir: Path) -> dict[str, Any]:
    """Reserve metrics for one restored checkpoint. Does not write weights."""
    import torch

    examples = reserve_examples()
    tok, encoder, classify, filler_head, maps, device = _load(arm_dir)

    def encode(text: str):
        encoded = tok(
            [text],
            padding=True,
            truncation=True,
            max_length=MAX_LEN,
            return_tensors="pt",
        )
        return {key: value.to(device) for key, value in encoded.items()}

    classify_golds: list[str] = []
    classify_preds: list[str] = []
    observed_hit = observed_n = 0
    pairs: list[tuple[list[str], list[str]]] = []
    unbind_n = 0
    with torch.no_grad():
        for example in examples:
            if example["task"] == "classify":
                hidden = encoder(**encode(example["text"])).last_hidden_state[:, 0]
                pred_id = int(classify(hidden).argmax(-1)[0])
                gold = maps["family_of"].get(example["lineage"], maps["family_of"]["none"])
                gold_name = FAMILIES[gold]
                pred_name = FAMILIES[pred_id] if 0 <= pred_id < len(FAMILIES) else "none"
                classify_golds.append(gold_name)
                classify_preds.append(pred_name)
                if example["class"] == "OBSERVED":
                    observed_n += 1
                    observed_hit += int(pred_id == gold)
            elif example["unbind_clean"]:
                fillers = list(example["fillers"])
                if not fillers:
                    raise SystemExit("EVALUATION_FAILURE: unbind row has no fillers")
                states = encoder(**encode(example["text"])).last_hidden_state[0]
                offsets = _offsets(tok, example["text"])
                gold_strs = []
                pred_strs = []
                for fill in fillers:
                    indices = pool_indices(states.size(0), atom_token_index(example["text"], fill, offsets))
                    pred_id = int(filler_head(states[indices].mean(0)).argmax())
                    gold_strs.append(mapped_filler(maps, fill))
                    pred_strs.append(mapped_pred(maps, pred_id))
                pairs.append((gold_strs, pred_strs))
                unbind_n += 1
            else:
                raise SystemExit("EVALUATION_FAILURE: row is neither classify nor unbind_clean")
    if len(classify_golds) != EXPECTED_COUNTS["classify"] or observed_n != EXPECTED_COUNTS["classify_observed"]:
        raise SystemExit("EVALUATION_FAILURE: classify slice count")
    if unbind_n != EXPECTED_COUNTS["unbind_clean"]:
        raise SystemExit("EVALUATION_FAILURE: unbind slice count")
    non_none = sum(1 for gold in classify_golds if gold != "none")
    if non_none != EXPECTED_COUNTS["classify_non_none"]:
        raise SystemExit("EVALUATION_FAILURE: non-none slice count")
    macro = macro_f1_nonnone(classify_golds, classify_preds)
    if macro is None:
        raise SystemExit("METRIC_NONCOMPUTABLE: classify_macro_f1_nonnone")
    summary = summarize_unbind_pairs(pairs)
    return {
        "classification_accuracy": sum(int(a == b) for a, b in zip(classify_preds, classify_golds))
        / len(classify_golds),
        "classify_macro_f1_nonnone": float(macro),
        "n_classify": len(classify_golds),
        "n_classify_non_none": non_none,
        "n_classify_observed": observed_n,
        "n_unbind_clean": unbind_n,
        "observed_label_accuracy": observed_hit / observed_n,
        "unbind_clean_exact": float(summary["unbind_exact"]),
    }


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        raise SystemExit("EVALUATION_FAILURE: usage arm_dir dest")
    payload = score_arm(Path(args[0]))
    dest = Path(args[1])
    dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
