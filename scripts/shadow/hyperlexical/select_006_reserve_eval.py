"""Score one restored SELECT-006 checkpoint on the frozen reserve.

This module does not train, does not append the ledger, and does not move BEST.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .holdout_guard import normalized_text_sha256
from .layout import FAMILIES

EXPERIMENT_ID = "HLX-EXP-2026-09-29-SELECT-006"
ROOT = Path("/home/morpheus/hlx-private/exp-20260929-select-006/reserve-acquisition-002")
MANIFEST = ROOT / "RESERVE_MANIFEST.json"
ROUTING = ROOT / "ROUTING_RECORDS.jsonl"
RAW = ROOT / "RAW_CANDIDATES.jsonl"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
WARM = Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph65")
EXPECTED_COUNTS = {
    "classify": 32,
    "classify_non_none": 32,
    "classify_observed": 32,
    "head_mapped_non_none": 32,
    "unbind_clean": 5,
}
SCORING_FAILURE = "RESERVE_SCORING_FAILURE"
NONCOMPUTABLE = "METRIC_NONCOMPUTABLE"


def _fail(code: str, detail: str) -> None:
    raise SystemExit(f"{code}: {detail}")


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def reserve_examples() -> list[dict[str, Any]]:
    """Join the frozen manifest to text and routing. Refuse a partial join."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("experiment_id") != EXPERIMENT_ID:
        _fail(SCORING_FAILURE, "manifest experiment")
    routing = {str(record["normalized_identity"]): record for record in _rows(ROUTING)}
    text_by_hash: dict[str, str] = {}
    fillers_by_hash: dict[str, list[str]] = {}
    for record in _rows(RAW):
        text = record.get("normalized_text")
        if not isinstance(text, str):
            _fail(SCORING_FAILURE, "raw candidate text")
        digest = normalized_text_sha256(text)
        if digest != record.get("normalized_hash"):
            _fail(SCORING_FAILURE, "raw normalized hash")
        text_by_hash[digest] = text
        tokens = record.get("source_lemma_tokens")
        if isinstance(tokens, list):
            fillers_by_hash[digest] = [str(token) for token in tokens]
    examples = []
    for row in manifest["rows"]:
        digest = str(row["normalized_text_sha256"])
        route = routing.get(digest)
        text = text_by_hash.get(digest)
        if route is None or text is None:
            _fail(SCORING_FAILURE, "reserve row is not joined")
        if str(route.get("row_id")) != str(row["row_id"]):
            _fail(SCORING_FAILURE, "row id mismatch")
        if sorted(route.get("slices") or []) != sorted(row.get("slices") or []):
            _fail(SCORING_FAILURE, "slice mismatch")
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
    if len(examples) != 37:
        _fail(SCORING_FAILURE, "reserve count")
    counts = {name: 0 for name in EXPECTED_COUNTS if name != "head_mapped_non_none"}
    for example in examples:
        for name in example["slices"]:
            if name in counts:
                counts[name] += 1
    counts["head_mapped_non_none"] = sum(
        1
        for example in examples
        if example["task"] == "classify" and example["lineage"] not in (None, "", "none")
    )
    if counts != EXPECTED_COUNTS:
        _fail(SCORING_FAILURE, "slice counts")
    return examples


def score_arm(arm_dir: Path) -> dict[str, Any]:
    """Reserve metrics for one restored checkpoint. Does not write weights."""
    import torch

    from .align import atom_token_index, pool_indices
    from .classify_metrics import macro_f1_nonnone
    from .layout import HIDDEN, MAX_LEN
    from .loop import (
        _offsets,
        _require_local_model,
        freeze_encoder,
        warm_load_checkpoint,
    )
    from .unbind_metrics import mapped_filler, mapped_pred, summarize_unbind_pairs

    examples = reserve_examples()
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
    from torch import nn

    classify = nn.Linear(HIDDEN, len(FAMILIES))
    role_head = nn.Linear(HIDDEN, len(role_vocab))
    filler_head = nn.Linear(HIDDEN, len(filler_vocab))
    warm_load_checkpoint(encoder, classify, role_head, filler_head, maps, WARM, expand_vocab=True)
    overlay = warm_load_checkpoint(
        encoder, classify, role_head, filler_head, maps, arm_dir, expand_vocab=False
    )
    loaded = overlay.get("encoder_trainable_loaded")
    present = overlay.get("encoder_trainable_present")
    if not loaded or loaded != present:
        _fail(SCORING_FAILURE, "checkpoint encoder tensors did not load")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    for module in (encoder, classify, role_head, filler_head):
        module.to(device)
        module.eval()

    def encode(text: str):
        encoded = tok([text], padding=True, truncation=True, max_length=MAX_LEN, return_tensors="pt")
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
                gold = maps["family_of"].get(example["lineage"])
                if gold is None:
                    _fail(SCORING_FAILURE, "classify lineage is not on the head")
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
                    _fail(SCORING_FAILURE, "unbind row has no fillers")
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
                _fail(SCORING_FAILURE, "row is neither classify nor unbind_clean")
    if len(classify_golds) != 32 or observed_n != 32 or unbind_n != 5:
        _fail(SCORING_FAILURE, "scored slice count")
    non_none = sum(1 for gold in classify_golds if gold != "none")
    if non_none != 32:
        _fail(SCORING_FAILURE, "head_mapped_non_none")
    macro = macro_f1_nonnone(classify_golds, classify_preds)
    if macro is None or observed_n == 0:
        _fail(NONCOMPUTABLE, "required metric")
    summary = summarize_unbind_pairs(pairs)
    if summary.get("unbind_exact") is None:
        _fail(NONCOMPUTABLE, "unbind_clean_exact")
    return {
        "classification_accuracy": sum(int(a == b) for a, b in zip(classify_preds, classify_golds))
        / len(classify_golds),
        "classify_macro_f1_nonnone": float(macro),
        "n_classify": len(classify_golds),
        "n_classify_non_none": 32,
        "n_classify_observed": observed_n,
        "n_head_mapped_non_none": non_none,
        "n_unbind_clean": unbind_n,
        "observed_label_accuracy": observed_hit / observed_n,
        "unbind_clean_exact": float(summary["unbind_exact"]),
    }


def _checkpoint_vocabs(arm_dir: Path) -> tuple[list[str], list[str]]:
    path = arm_dir / "config.json"
    if not path.is_file():
        _fail(SCORING_FAILURE, "checkpoint config is absent")
    config = json.loads(path.read_text(encoding="utf-8"))
    role = config.get("role_vocab")
    filler = config.get("filler_vocab")
    if not isinstance(role, list) or not isinstance(filler, list) or not role or not filler:
        _fail(SCORING_FAILURE, "checkpoint vocabs are absent")
    return [str(item) for item in role], [str(item) for item in filler]


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        _fail(SCORING_FAILURE, "usage arm_dir dest")
    payload = score_arm(Path(args[0]))
    dest = Path(args[1])
    dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
