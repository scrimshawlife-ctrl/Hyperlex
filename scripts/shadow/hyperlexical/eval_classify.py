"""Classify harness. Predictions plus an eval split, against three baselines.

Does not train Hyperlexical weights and does not read a held-out manifest.
Slices are reporting-only: they are not a checkpoint rule.

Baselines, all scored on the eval rows and refit only on the train split
passed in (never on eval text or eval labels):
  (a) bag-of-terms logistic regression, two fits of the same guarded split
      - ``bow_lr_nonnone``: non-none train rows only, output space the 8 families
      - ``bow_lr_with_none``: every train row, including ``none``
      ``--bow-nonnone`` defaults to auto: on when eval gold has no ``none``.
      On, ``bow_lr_nonnone`` is the gated baseline and ``bow_lr_with_none``
      is reference. Off, those roles swap. Both still get an exact McNemar.
  (b) registry rule ``match_lineage`` (lexical, vector re-rank off)
  (c) Spec 004 linear probe, refit on this split when the rows carry span
      encodings; otherwise NOT_COMPUTABLE

sklearn is not a project dependency. The logistic regression is pure Python
(zero init, full-batch softmax cross-entropy) so the public test job can run
it without numpy.
"""

from __future__ import annotations

import argparse
import importlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from .classify_metrics import (
    NONE_LABEL,
    accuracy,
    macro_f1_nonnone,
    mcnemar_paired,
    none_rates,
    per_class_table,
)
from .layout import FAMILIES

NONNONE_FAMILIES = tuple(name for name in FAMILIES if name != NONE_LABEL)

SLICES_WARNING = "slices are reporting-only"
_PRED_FIELDS = ("pred", "lineage_pred", "prediction")
_GOLD_FIELDS = ("lineage", "label")
_LOGREG_STEPS = 400
_LOGREG_LR = 1.0
_LOGREG_L2 = 1e-2
_SPEC004_REASON = (
    "Spec 004 linear probe cannot be refit on this split: "
    "recoverable_structure.fit.fit_scheme needs span item_ids and encoder "
    "encodings, which these rows do not carry"
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise SystemExit(f"REFUSE: not a file: {path}")
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"REFUSE: {path} line {index} is not JSON") from exc
        if not isinstance(obj, dict):
            raise SystemExit(f"REFUSE: {path} line {index} must be an object")
        rows.append(obj)
    return rows


def _join_key(row: Mapping[str, Any]) -> tuple[str, str]:
    for field in ("id", "row_id"):
        token = row.get(field)
        if isinstance(token, str) and token.strip():
            return ("id", token.strip())
    text = row.get("text")
    if isinstance(text, str) and text.strip():
        return ("text", text)
    raise SystemExit("REFUSE: row needs id, row_id, or text")


def _field(row: Mapping[str, Any], names: Sequence[str], what: str) -> str:
    for name in names:
        token = row.get(name)
        if isinstance(token, str) and token.strip():
            return token.strip()
    raise SystemExit(f"REFUSE: {what} needs one of {', '.join(names)}")


def _tags(row: Mapping[str, Any]) -> set[str]:
    raw = row.get("tags")
    if raw is None:
        return set()
    if isinstance(raw, str):
        token = raw.strip()
        return {token} if token else set()
    if not isinstance(raw, list):
        return set()
    return {str(item).strip() for item in raw if str(item).strip()}


def _terms(text: str) -> list[str]:
    return [tok.casefold() for tok in str(text or "").split() if tok]


def resolve_bow_nonnone(gold: Sequence[str], raw: str | None = None) -> tuple[bool, str]:
    """Whether ``bow_lr_nonnone`` is the gated baseline.

    ``auto`` (the default) is on exactly when eval gold contains no ``none``.
    The decision reads eval labels only to choose which already-fit baseline
    is gated. It does not choose features, classes, or steps.
    """
    mode = "auto" if raw is None else str(raw).strip().lower()
    if mode in {"", "auto"}:
        has_none = any(label == NONE_LABEL for label in gold)
        if has_none:
            return False, "eval gold includes none"
        return True, "eval gold has no none"
    if mode in {"1", "on", "true"}:
        return True, "forced on"
    if mode in {"0", "off", "false"}:
        return False, "forced off"
    raise SystemExit(
        "REFUSE: --bow-nonnone must be auto, on, or off, "
        f"got {raw!r}"
    )


def fit_bag_of_terms_logreg(
    train_texts: Sequence[str],
    train_labels: Sequence[str],
    eval_texts: Sequence[str],
    *,
    classes: Sequence[str] | None = None,
    steps: int = _LOGREG_STEPS,
    lr: float = _LOGREG_LR,
    l2: float = _LOGREG_L2,
) -> tuple[list[str] | None, dict[str, Any]]:
    """Binary bag-of-terms logistic regression.

    Vocab and rows come from the train arguments only. ``eval_texts`` is scored
    after the fit. A fixed ``classes`` list (the 8 families) drops train rows
    whose label is outside that list and does not add labels from eval.
    Steps, learning rate, and L2 are constants.
    """
    if len(train_texts) != len(train_labels):
        raise ValueError("train texts and labels differ in length")
    n_train = len(train_labels)
    if classes is None:
        paired = list(zip(train_texts, train_labels, strict=True))
        class_list = sorted({label for _text, label in paired})
        empty_reason = "train split is empty"
    else:
        allowed = set(classes)
        paired = [(text, label) for text, label in zip(train_texts, train_labels, strict=True) if label in allowed]
        class_list = list(classes)
        empty_reason = "no train rows in the requested class list"
    base_meta = {
        "n_train_rows": n_train,
        "n_train_rows_used": len(paired),
        "classes": class_list,
        "eval_used_for_fit": False,
        "steps": steps,
    }
    if not paired or not class_list:
        return None, {"status": "NOT_COMPUTABLE", "reason": empty_reason, **base_meta}
    used_texts = [text for text, _label in paired]
    used_labels = [label for _text, label in paired]
    vocab = sorted({tok for text in used_texts for tok in _terms(text)})
    index = {tok: i for i, tok in enumerate(vocab)}
    width = len(vocab) + 1
    n_class = len(class_list)
    class_of = {label: i for i, label in enumerate(class_list)}
    weights = [[0.0] * width for _ in range(n_class)]

    def featurize(texts: Sequence[str]) -> list[list[float]]:
        rows = []
        for text in texts:
            vec = [0.0] * width
            for tok in _terms(text):
                slot = index.get(tok)
                if slot is not None:
                    vec[slot] = 1.0
            vec[-1] = 1.0
            rows.append(vec)
        return rows

    features = featurize(used_texts)
    targets = [class_of[label] for label in used_labels]
    n = float(len(features))
    for _step in range(steps):
        grad = [[0.0] * width for _ in range(n_class)]
        for vec, target in zip(features, targets):
            logits = [sum(w * x for w, x in zip(weights[c], vec)) for c in range(n_class)]
            pivot = max(logits)
            exps = [math.exp(item - pivot) for item in logits]
            total = sum(exps) or 1.0
            for c in range(n_class):
                err = exps[c] / total - (1.0 if c == target else 0.0)
                if err == 0.0:
                    continue
                for j, value in enumerate(vec):
                    if value:
                        grad[c][j] += err * value
        for c in range(n_class):
            for j in range(width):
                penalty = 0.0 if j == width - 1 else l2 * weights[c][j]
                weights[c][j] -= lr * (grad[c][j] / n + penalty)
    preds: list[str] = []
    for vec in featurize(eval_texts):
        logits = [sum(w * x for w, x in zip(weights[c], vec)) for c in range(n_class)]
        preds.append(class_list[max(range(n_class), key=lambda c: (logits[c], -c))])
    return preds, {
        "status": "OK",
        "n_features": len(vocab),
        **base_meta,
    }


def _registry_preds(texts: Sequence[str]) -> tuple[list[str] | None, dict[str, Any]]:
    """Lexical registry rule. Imported lazily so this package stays import-free."""
    try:
        match_lineage = importlib.import_module("hyperlex.analysis").match_lineage
    except Exception as exc:
        return None, {
            "status": "NOT_COMPUTABLE",
            "reason": f"registry matcher could not be imported: {type(exc).__name__}: {exc}",
        }
    preds: list[str] = []
    for text in texts:
        try:
            hit = match_lineage(text, use_vector=False)
        except Exception as exc:
            return None, {
                "status": "NOT_COMPUTABLE",
                "reason": f"match_lineage failed: {type(exc).__name__}: {exc}",
            }
        if not hit:
            preds.append(NONE_LABEL)
            continue
        family = hit.get("family_id")
        preds.append(str(family) if family else NONE_LABEL)
    return preds, {"status": "OK", "rule": "match_lineage", "use_vector": False}


def _span_ready(rows: Sequence[Mapping[str, Any]]) -> bool:
    width: int | None = None
    if not rows:
        return False
    for row in rows:
        items = row.get("item_ids")
        encoding = row.get("encoding")
        if not isinstance(items, list) or not items or not all(isinstance(item, str) for item in items):
            return False
        if (
            not isinstance(encoding, list)
            or not encoding
            or not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in encoding)
        ):
            return False
        if width is None:
            width = len(encoding)
        elif len(encoding) != width:
            return False
    return True


def _import_probe():
    try:
        from recoverable_structure.fit import fit_scheme, swap_accuracy
    except ImportError:
        shadow = Path(__file__).resolve().parents[1]
        if str(shadow) not in sys.path:
            sys.path.insert(0, str(shadow))
        from recoverable_structure.fit import fit_scheme, swap_accuracy
    return fit_scheme, swap_accuracy


def _spec004_preds(
    train_rows: Sequence[Mapping[str, Any]],
    eval_rows: Sequence[Mapping[str, Any]],
) -> tuple[list[str] | None, dict[str, Any]]:
    if not _span_ready(train_rows) or not _span_ready(eval_rows):
        return None, {"status": "NOT_COMPUTABLE", "reason": _SPEC004_REASON}
    try:
        fit_scheme, swap_accuracy = _import_probe()
        spans = []
        encodings = []
        for row in list(train_rows) + list(eval_rows):
            spans.append(
                {
                    "item_ids": list(row["item_ids"]),
                    "type_tags": list(row.get("type_tags") or []),
                    "label": _field(row, _GOLD_FIELDS, "span row"),
                }
            )
            encodings.append([float(value) for value in row["encoding"]])
        snap = {
            "spans": spans,
            "encodings": encodings,
            "max_len": max(len(span["item_ids"]) for span in spans),
            "encoder_id": "eval_classify_refit",
        }
        n_train = len(train_rows)
        train_idx = list(range(n_train))
        test_idx = list(range(n_train, n_train + len(eval_rows)))
        fitted = fit_scheme("positional", snap, train_idx, test_idx)
        _acc, predict = swap_accuracy(fitted, snap, train_idx, test_idx)
        preds = [str(item) for item in predict(fitted["pred_test"])]
    except Exception as exc:
        return None, {
            "status": "NOT_COMPUTABLE",
            "reason": f"Spec 004 linear probe could not be refit: {type(exc).__name__}: {exc}",
        }
    if len(preds) != len(eval_rows):
        return None, {
            "status": "NOT_COMPUTABLE",
            "reason": "Spec 004 probe returned a different number of predictions than eval rows",
        }
    return preds, {"status": "OK", "scheme": "positional", "refit": "fit_scheme+swap_accuracy"}


def _baseline_block(
    gold: Sequence[str],
    model: Sequence[str],
    preds: list[str] | None,
    meta: Mapping[str, Any],
) -> dict[str, Any]:
    if preds is None:
        return {
            "status": str(meta.get("status") or "NOT_COMPUTABLE"),
            "reason": str(meta.get("reason") or ""),
            "mcnemar": None,
        }
    return {
        "status": "OK",
        **{key: value for key, value in meta.items() if key != "status"},
        "accuracy": accuracy(gold, preds),
        "macro_f1_nonnone": macro_f1_nonnone(gold, preds),
        "mcnemar": mcnemar_paired(gold, model, preds),
    }


def _score_block(gold: Sequence[str], pred: Sequence[str]) -> dict[str, Any]:
    rates = none_rates(gold, pred)
    return {
        "n": len(gold),
        "accuracy": accuracy(gold, pred),
        "macro_f1_nonnone": macro_f1_nonnone(gold, pred),
        "none_fpr": rates["none_fpr"],
        "none_fnr": rates["none_fnr"],
        "per_class": per_class_table(gold, pred),
    }


def _resolve_preds_path(preds: str, checkpoint: str) -> Path:
    if preds:
        return Path(preds)
    if checkpoint:
        path = Path(checkpoint)
        if path.is_file():
            return path
        candidate = path / "classify-preds.jsonl"
        if candidate.is_file():
            return candidate
        raise SystemExit(
            "NOT_COMPUTABLE: checkpoint has no classify-preds.jsonl; pass --preds"
        )
    raise SystemExit("REFUSE: pass --preds or --checkpoint")


def _bow_pair(
    train_texts: Sequence[str],
    train_labels: Sequence[str],
    eval_texts: Sequence[str],
    gold: Sequence[str],
    model: Sequence[str],
    *,
    nonnone_gated: bool,
) -> dict[str, dict[str, Any]]:
    """Both BoW fits on one train split. Eval text is scored, never fit."""
    with_preds, with_meta = fit_bag_of_terms_logreg(train_texts, train_labels, eval_texts)
    non_preds, non_meta = fit_bag_of_terms_logreg(
        train_texts,
        train_labels,
        eval_texts,
        classes=NONNONE_FAMILIES,
    )
    with_block = _baseline_block(gold, model, with_preds, with_meta)
    non_block = _baseline_block(gold, model, non_preds, non_meta)
    with_block["role"] = "reference" if nonnone_gated else "gated"
    non_block["role"] = "gated" if nonnone_gated else "reference"
    return {"bow_lr_with_none": with_block, "bow_lr_nonnone": non_block}


def run_eval_classify(
    *,
    preds_path: str | Path,
    eval_path: str | Path,
    train_path: str | Path,
    slices: Sequence[str] = (),
    bow_nonnone: str | None = None,
) -> dict[str, Any]:
    """Score model predictions. Train rows fit the bag-of-terms baseline only."""
    pred_rows = _read_jsonl(Path(preds_path))
    eval_rows = _read_jsonl(Path(eval_path))
    train_rows = _read_jsonl(Path(train_path))
    if not eval_rows:
        raise SystemExit("REFUSE: eval split is empty")
    pred_of: dict[tuple[str, str], str] = {}
    for row in pred_rows:
        key = _join_key(row)
        if key in pred_of:
            raise SystemExit(f"REFUSE: duplicate prediction key {key[1]!r}")
        pred_of[key] = _field(row, _PRED_FIELDS, "prediction row")
    gold: list[str] = []
    model: list[str] = []
    texts: list[str] = []
    for row in eval_rows:
        key = _join_key(row)
        if key not in pred_of:
            raise SystemExit(f"REFUSE: missing prediction for {key[1]!r}")
        gold.append(_field(row, _GOLD_FIELDS, "eval row"))
        model.append(pred_of[key])
        texts.append(str(row.get("text") or ""))
    train_texts = [str(row.get("text") or "") for row in train_rows]
    train_labels = [_field(row, _GOLD_FIELDS, "train row") for row in train_rows]
    nonnone_gated, nonnone_reason = resolve_bow_nonnone(gold, bow_nonnone)
    bow = _bow_pair(
        train_texts,
        train_labels,
        texts,
        gold,
        model,
        nonnone_gated=nonnone_gated,
    )
    rule_preds, rule_meta = _registry_preds(texts)
    probe_preds, probe_meta = _spec004_preds(train_rows, eval_rows)
    report: dict[str, Any] = {
        "schema": "hyperlex.classify_harness.v0.1",
        **_score_block(gold, model),
        "macro_f1_nonnone_definition": (
            "unweighted mean of per-class F1 over gold labels other than none with n>0"
        ),
        "none_fpr_definition": "predicted none among gold that is not none",
        "none_fnr_definition": "predicted not-none among gold none",
        "bow_nonnone": nonnone_gated,
        "bow_nonnone_reason": nonnone_reason,
        "gated_baseline": "bow_lr_nonnone" if nonnone_gated else "bow_lr_with_none",
        "baselines": {
            **bow,
            "match_lineage": _baseline_block(gold, model, rule_preds, rule_meta),
            "spec004_linear_probe": _baseline_block(gold, model, probe_preds, probe_meta),
        },
        "brier": None,
    }
    slice_names = [item.strip() for item in slices if item and item.strip()]
    if slice_names:
        print(SLICES_WARNING, flush=True)
        packed = []
        for row, g, p in zip(eval_rows, gold, model):
            packed.append((g, p, _tags(row)))
        report["slices_warning"] = SLICES_WARNING
        report["slices"] = {}
        for name in slice_names:
            kept = [(g, p) for g, p, tags in packed if name in tags]
            if not kept:
                report["slices"][name] = {
                    "n": 0,
                    "status": "NOT_COMPUTABLE",
                    "reason": f"no eval rows tagged {name}",
                    "reporting_only": True,
                }
                continue
            block = _score_block([g for g, _p in kept], [p for _g, p in kept])
            block["reporting_only"] = True
            report["slices"][name] = block
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hyperlexical-eval-classify")
    parser.add_argument("--preds", default="", help="jsonl of model predictions")
    parser.add_argument(
        "--checkpoint",
        default="",
        help="checkpoint dir containing classify-preds.jsonl, or a preds jsonl path",
    )
    parser.add_argument("--eval", required=True, help="eval split jsonl (gold lineage)")
    parser.add_argument("--train", required=True, help="train split jsonl for the bag-of-terms baseline")
    parser.add_argument(
        "--slices",
        default="",
        help="comma-separated tags to report. Reporting-only; not a selection rule.",
    )
    parser.add_argument(
        "--bow-nonnone",
        nargs="?",
        const="on",
        default="auto",
        metavar="auto|on|off",
        help=(
            "Gated BoW baseline. auto (default) is on when eval gold has no none: "
            "refit on non-none train rows over the 8 families. "
            "bow_lr_with_none stays in the report as reference. "
            "Pass off to gate on the with-none fit instead."
        ),
    )
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)
    preds_path = _resolve_preds_path(args.preds, args.checkpoint)
    report = run_eval_classify(
        preds_path=preds_path,
        eval_path=args.eval,
        train_path=args.train,
        slices=[part for part in str(args.slices).split(",")],
        bow_nonnone=args.bow_nonnone,
    )
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
