#!/usr/bin/env python3
"""Curation helper: scan moltbook_log + batch results, propose high-efficiency items for seed_examples.jsonl.

Usage:
  python scripts/curate_moltbook_seeds.py --scan
  python scripts/curate_moltbook_seeds.py --add "text here" --tiers episodic,rubric
"""
import json
import argparse
from pathlib import Path
from hyperlex import detect_memetic_patterns as dmp

LOG = Path("out/moltbook_log.txt")
BATCH = Path("out/batch_moltbook_memetics.json")
SEEDS = Path("data/agent_memetics/seed_examples.jsonl")

def scan_high_efficiency(min_eff=0.5, limit=10):
    candidates = []
    if BATCH.exists():
        data = json.loads(BATCH.read_text())
        for item in data.get("batch", []):
            eff = item.get("efficiency") or 0
            if eff >= min_eff:
                candidates.append({
                    "text": item.get("title", "") + ". " + item.get("inferred", "")[:200],
                    "efficiency": eff,
                    "source": "batch"
                })
    if LOG.exists():
        for line in LOG.read_text().splitlines():
            if "Hyperlex:" in line or "efficiency" in line.lower():
                continue
            # crude parse for titles
            if "[" in line and "]" in line:
                text = line.split("]", 1)[-1].strip()[:300]
                res = dmp(text, ingest_source="moltbook")
                eff = res.get("analysis", {}).get("memetic_efficiency", {}).get("efficiency_score", 0)
                if eff >= min_eff:
                    candidates.append({"text": text, "efficiency": eff, "source": "log"})
    candidates.sort(key=lambda x: -x["efficiency"])
    return candidates[:limit]

def add_to_seeds(text, tiers=None, compression="load_bearing"):
    tiers = tiers or ["episodic"]
    ex = {
        "text": text,
        "labels": {
            "memory_tier": tiers,
            "compression": compression,
            "provenance": "provenance" in text.lower() or "echo" in text.lower()
        }
    }
    with open(SEEDS, "a") as f:
        f.write(json.dumps(ex) + "\n")
    print(f"Added to seeds: {text[:80]}...")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--scan", action="store_true")
    p.add_argument("--min-eff", type=float, default=0.5)
    p.add_argument("--add", type=str)
    p.add_argument("--tiers", type=str)
    args = p.parse_args()

    if args.scan:
        cands = scan_high_efficiency(args.min_eff)
        print(f"Found {len(cands)} high-efficiency candidates:")
        for c in cands:
            print(f"  eff={c['efficiency']:.3f} [{c['source']}] {c['text'][:100]}")
    elif args.add:
        tiers = args.tiers.split(",") if args.tiers else None
        add_to_seeds(args.add, tiers)
    else:
        print("Use --scan or --add")
