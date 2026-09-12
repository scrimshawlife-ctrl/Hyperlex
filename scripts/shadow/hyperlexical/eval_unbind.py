"""U3 eval harness. Stub vs Spec 004 probe. No torch. No Hub."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

HEAD_NAMES = ("heads.json", "model.safetensors", "heads.pt")
DEFAULT_TRAIN_OUT = Path.home() / ".hyperlex" / "models" / "hyperlex-encoder-modernbert-base-seed"


def _shadow() -> Path:
    return Path(__file__).resolve().parents[1]


def stub_swap(spans: list[dict]) -> float:
    """Chance-like filler guess from text hash. Not Hyperlexical."""
    hit = 0
    for sp in spans:
        items = list(sp["item_ids"])
        guess = []
        for i, it in enumerate(items):
            digest = hashlib.sha256(f"stub-unbind:{i}:{it}".encode()).digest()
            guess.append(items[digest[0] % len(items)])
        if guess == items:
            hit += 1
    return hit / max(1, len(spans))


def model_swap(spans: list[dict], seed: bytes) -> float:
    """Permutation guess seeded by loaded head bytes. Not a trunk forward."""
    hit = 0
    for sp in spans:
        items = list(sp["item_ids"])
        guess = []
        for i, it in enumerate(items):
            digest = hashlib.sha256(seed + f":unbind:{i}:{it}".encode()).digest()
            guess.append(items[digest[0] % len(items)])
        if guess == items:
            hit += 1
    return hit / max(1, len(spans))


def resolve_model_dir(explicit: str | Path | None = None) -> Path | None:
    if explicit not in (None, ""):
        return Path(explicit)
    env = os.environ.get("HYPERLEX_TRAIN_OUT", "").strip()
    if env:
        return Path(env)
    if DEFAULT_TRAIN_OUT.is_dir():
        return DEFAULT_TRAIN_OUT
    return None


def find_weight_file(model_dir: Path) -> Path | None:
    for name in HEAD_NAMES:
        path = model_dir / name
        if path.is_file() and path.stat().st_size > 0:
            return path
    return None


def load_heads_meta(weight_path: Path) -> dict:
    """Torch-free load. JSON fixture or sibling layout/config + file digest."""
    model_dir = weight_path.parent
    meta = {
        "weight_file": weight_path.name,
        "model_id": "hyperlex-encoder-modernbert-base-seed",
        "digest": hashlib.sha256(weight_path.read_bytes()).hexdigest(),
    }
    if weight_path.suffix == ".json":
        blob = json.loads(weight_path.read_text(encoding="utf-8"))
        if not isinstance(blob, dict):
            raise ValueError("heads.json must be an object")
        if blob.get("model_id"):
            meta["model_id"] = str(blob["model_id"])
        if blob.get("weight_digest"):
            meta["digest"] = str(blob["weight_digest"])
        return meta
    for name in ("config.json", "layout.json", "train-receipt.json"):
        side = model_dir / name
        if not side.is_file():
            continue
        try:
            side_blob = json.loads(side.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(side_blob, dict) and side_blob.get("model_id"):
            meta["model_id"] = str(side_blob["model_id"])
            break
    return meta


def _probe_report() -> tuple[dict, list[dict], float, float, float, float]:
    sys.path.insert(0, str(_shadow()))
    from recoverable_structure.fit import run_probe
    from recoverable_structure.fixtures import snapshot

    snap = snapshot("tpr", n=48, length=4, dim=12, seed=7)
    probe = run_probe(snap, schemes=("positional", "type_slot"))
    rec = probe["receipt"]
    pos = next(b for b in rec["schemes"] if b["scheme"] == "positional")
    typ = next(b for b in rec["schemes"] if b["scheme"] == "type_slot")
    test_spans = [snap["spans"][i] for i in probe["test_idx"]]
    stub_acc = stub_swap(test_spans)
    probe_acc = min(float(pos["swap_accuracy"]), float(typ["swap_accuracy"]))
    return rec, test_spans, stub_acc, probe_acc, float(pos["swap_accuracy"]), float(typ["swap_accuracy"])


def run_eval(model_dir: str | Path | None = None) -> dict:
    rec, test_spans, stub_acc, probe_acc, pos_acc, typ_acc = _probe_report()
    directory = resolve_model_dir(model_dir)
    weight = find_weight_file(directory) if directory is not None else None
    base = {
        "schema": "hyperlex.hyperlexical.eval_unbind.v0.1",
        "probe_schema": rec.get("schema"),
        "probe_positional_swap": pos_acc,
        "probe_type_slot_swap": typ_acc,
        "probe_swap_min": probe_acc,
        "stub_swap": stub_acc,
        "n_test": len(test_spans),
        "trunk": "answerdotai/ModernBERT-base",
        "trunk_loaded": False,
        "brier": None,
        "forecast_eligible": False,
    }
    if weight is None:
        base.update(
            {
                "e2_pass": stub_acc > probe_acc,
                "model_id": "stub",
                "heads_loaded": False,
                "weight_file": None,
                "model_swap": None,
                "note": "E2 requires a trained T1 to beat the 004 probe. Stub is expected to fail.",
            }
        )
        return base
    meta = load_heads_meta(weight)
    model_acc = model_swap(test_spans, meta["digest"].encode("utf-8"))
    base.update(
        {
            "e2_pass": model_acc > probe_acc,
            "model_id": meta["model_id"],
            "heads_loaded": True,
            "weight_file": meta["weight_file"],
            "model_swap": model_acc,
            "note": (
                f"Loaded heads from {weight}. E2 still requires beating the 004 probe."
            ),
        }
    )
    return base


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="hyperlexical-eval-unbind")
    p.add_argument("--out", default="")
    p.add_argument(
        "--model-dir",
        default="",
        help="train out dir with heads.json / heads.pt / model.safetensors",
    )
    args = p.parse_args(argv)
    report = run_eval(model_dir=args.model_dir or None)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0 if report["e2_pass"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
