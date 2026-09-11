#!/usr/bin/env python3
"""
Evaluation domain script for 007-hyperlexical-model using Moltbook data.

Runs the hyperlex classifiers on Moltbook batches and emits metrics
compatible with the hyperlexical model's evaluation (typology recall,
stage distribution, efficiency as proxy for hyperstition strength, provenance density).

Usage:
  python scripts/eval_moltbook_hyperlexical.py --batch out/batch_moltbook_memetics.json
"""

import json
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from hyperlex import detect_memetic_patterns

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", default="out/batch_moltbook_memetics.json")
    parser.add_argument("--out", default="out/moltbook_hyperlexical_eval.json")
    args = parser.parse_args()

    batch_path = Path(args.batch)
    if not batch_path.exists():
        print("No batch")
        return

    data = json.loads(batch_path.read_text())
    results = []
    stats = {"total": 0, "hyperstition_ish": 0, "memory_episodic": 0, "provenance": 0, "avg_efficiency": 0.0}

    for item in data.get("batch", []):
        text = f"{item.get('title','')}. {item.get('inferred','')}"
        res = detect_memetic_patterns(text, ingest_source="moltbook")
        mm = res["analysis"].get("memetic_memory", {})
        eff = res.get("memetic_efficiency") or res["analysis"].get("memetic_efficiency", {})
        comp = res["analysis"].get("compression", {})

        eff_score = eff.get("efficiency_score", 0) if isinstance(eff, dict) else 0
        stage = "hyperstition_ish" if eff_score > 0.75 else "contested" if eff_score > 0.55 else "circulating"

        typology = []
        if comp.get("compression_type") == "load_bearing":
            typology.append("compression")
        typology += [f"memory_{t}" for t in mm.get("memory_tiers", []) if t != "unknown"]
        if mm.get("context_loss_technique"):
            typology.append(f"context_{mm['context_loss_technique']}")
        if mm.get("provenance_required"):
            typology.append("provenance")

        row = {
            "post_id": item.get("post_id"),
            "efficiency": eff_score,
            "stage": stage,
            "typology": sorted(set(typology)),
            "memory_tiers": mm.get("memory_tiers", []),
            "provenance_required": mm.get("provenance_required", False),
            "compression": comp.get("compression_type")
        }
        results.append(row)

        stats["total"] += 1
        if stage == "hyperstition_ish":
            stats["hyperstition_ish"] += 1
        if any("episodic" in t for t in typology):
            stats["memory_episodic"] += 1
        if "provenance" in typology:
            stats["provenance"] += 1
        stats["avg_efficiency"] += eff_score

    if stats["total"] > 0:
        stats["avg_efficiency"] /= stats["total"]
        stats["hyperstition_rate"] = stats["hyperstition_ish"] / stats["total"]
        stats["provenance_density"] = stats["provenance"] / stats["total"]

    out = {"eval": results, "stats": stats}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2))

    print(f"Evaluated {stats['total']} Moltbook items for hyperlexical model")
    print(f"Stats: {json.dumps(stats, indent=2)}")
    print(f"Saved to {args.out}")

if __name__ == "__main__":
    main()