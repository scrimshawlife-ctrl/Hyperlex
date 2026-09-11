#!/usr/bin/env python3
"""
Moltbook -> Hyperlexical dataset row exporter.

Uses our Moltbook classifiers (memory patterns, efficiency, compression, friction)
to produce rows compatible with specs/007-hyperlexical-model/schemas/dataset_row.v0.1.schema.json

Usage:
  python scripts/moltbook_to_hyperlexical.py --batch out/batch_moltbook_memetics.json --out data/moltbook_hyperlexical_rows.jsonl

This feeds agent memory discourse directly into the hyperlexical model's training data.
"""

import json
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from hyperlex import detect_memetic_patterns

def moltbook_post_to_row(post: dict, split: str = "train") -> dict:
    text = f"{post.get('title', '')}. {post.get('body', '')}"[:250]
    if not text.strip():
        return None

    res = detect_memetic_patterns(text, ingest_source="moltbook")
    mm = res["analysis"].get("memetic_memory", {})
    eff = res.get("memetic_efficiency") or res["analysis"].get("memetic_efficiency", {})
    comp = res["analysis"].get("compression", {})
    vir = res["analysis"].get("virality", {})

    # Map to hyperlexical fields
    typology = []
    if comp.get("compression_type") == "load_bearing":
        typology.append("compression")
    if mm.get("memory_tiers"):
        typology.extend([f"memory_{t}" for t in mm["memory_tiers"] if t != "unknown"])
    if mm.get("context_loss_technique"):
        typology.append(f"context_{mm['context_loss_technique']}")

    # Stage heuristic from efficiency
    eff_score = eff.get("efficiency_score", 0) if isinstance(eff, dict) else 0
    if eff_score > 0.75:
        stage = "hyperstition_ish"
    elif eff_score > 0.55:
        stage = "contested"
    else:
        stage = "circulating"

    lineage = "ai-native"  # Moltbook agent discourse

    row = {
        "text": text,
        "split": split,
        "lineage": lineage,
        "typology": sorted(set(typology)) or ["agent_slang"],
        "stage": stage,
        "roles": mm.get("memory_tiers", []) + (["provenance"] if mm.get("provenance_required") else []),
        "fillers": [mm.get("context_loss_technique") or "general"] if mm.get("context_loss_technique") else ["general"],
        "role_scheme": "type_slot",
        "provenance": {
            "source": "moltbook",
            "post_id": post.get("post_id"),
            "efficiency": eff_score,
            "compression": comp.get("compression_type"),
            "class": "INFERRED"  # weak labels from our classifiers
        },
        "class": "INFERRED",
        "license": "MIT (distilled)"
    }
    return row

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", default="out/batch_moltbook_memetics.json")
    parser.add_argument("--out", default="data/moltbook_hyperlexical_rows.jsonl")
    parser.add_argument("--split", default="train")
    args = parser.parse_args()

    batch_path = Path(args.batch)
    if not batch_path.exists():
        print(f"No batch at {batch_path}")
        return

    data = json.loads(batch_path.read_text())
    rows = []
    for item in data.get("batch", []):
        # reconstruct a post-like dict
        post = {
            "title": item.get("title", ""),
            "body": item.get("inferred", ""),
            "post_id": item.get("post_id")
        }
        row = moltbook_post_to_row(post, split=args.split)
        if row:
            rows.append(row)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    print(f"Exported {len(rows)} hyperlexical rows to {out_path}")
    print("These can be fed into U2 / 007-hyperlexical-model training (ai-native lineage + memory typology).")

if __name__ == "__main__":
    main()