"""U3 eval harness. Stub vs Spec 004 probe. No torch. No Hub."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


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


def run_eval() -> dict:
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
    e2 = stub_acc > probe_acc
    report = {
        "schema": "hyperlex.hyperlexical.eval_unbind.v0.1",
        "probe_schema": rec.get("schema"),
        "probe_positional_swap": pos["swap_accuracy"],
        "probe_type_slot_swap": typ["swap_accuracy"],
        "probe_swap_min": probe_acc,
        "stub_swap": stub_acc,
        "n_test": len(test_spans),
        "e2_pass": e2,
        "model_id": "stub",
        "trunk": "answerdotai/ModernBERT-base",
        "trunk_loaded": False,
        "brier": None,
        "forecast_eligible": False,
        "note": "E2 requires a trained T1 to beat the 004 probe. Stub is expected to fail.",
    }
    return report


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="hyperlexical-eval-unbind")
    p.add_argument("--out", default="")
    args = p.parse_args(argv)
    report = run_eval()
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0 if report["e2_pass"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
