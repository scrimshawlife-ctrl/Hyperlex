#!/usr/bin/env python3
"""Curation helper: scan moltbook_log + batch results, propose high-efficiency items for seed_examples.jsonl.

Usage:
  python scripts/curate_moltbook_seeds.py --scan
  python scripts/curate_moltbook_seeds.py --add "text here" --tiers episodic,rubric
"""
import json
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
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
    # dedup by normalized text
    seen = set()
    unique = []
    for c in sorted(candidates, key=lambda x: -x["efficiency"]):
        key = c["text"][:100].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique[:limit]


def rebuild_index():
    import subprocess
    # Run the rebuild logic from previous
    from pathlib import Path
    import json
    seed_path = Path("data/agent_memetics/seed_examples.jsonl")
    index_path = Path("data/agent_memetics/classification_index.json")
    seeds = []
    with open(seed_path) as sf:
        for line in sf:
            if line.strip():
                seeds.append(json.loads(line))
    memory_tiers = set()
    high_friction = []
    load_bearing = []
    for s in seeds:
        labels = s.get("labels", {})
        tiers = labels.get("memory_tier", [])
        if isinstance(tiers, str): tiers = [tiers]
        for t in tiers:
            if t: memory_tiers.add(t)
        if labels.get("friction_high") or "ghost" in s["text"].lower() or "reentry" in str(labels):
            high_friction.append({"text": s["text"][:200], "labels": labels})
        if labels.get("compression") == "load_bearing":
            load_bearing.append({"text": s["text"][:200], "labels": labels})
    idx = {
        "memory_tiers": sorted(list(memory_tiers)),
        "high_friction_examples": high_friction[:5],
        "load_bearing_examples": load_bearing[:6],
        "total_seeds": len(seeds),
        "source": "moltbook + distilled (auto-curated)"
    }
    index_path.write_text(json.dumps(idx, indent=2))
    print("Rebuilt classification_index.json")

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
    rebuild_index()

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--scan", action="store_true")
    p.add_argument("--min-eff", type=float, default=0.5)
    p.add_argument("--add", type=str)
    p.add_argument("--tiers", type=str)
    p.add_argument("--to-hyperlexical", action="store_true", help="Export to 007 hyperlexical rows")
    p.add_argument("--high-signal", action="store_true", help="Generate dedicated high-signal subset for 007 training")
    args = p.parse_args()

    if args.scan:
        cands = scan_high_efficiency(args.min_eff)
        print(f"Found {len(cands)} high-efficiency candidates:")
        for c in cands:
            print(f"  eff={c['efficiency']:.3f} [{c['source']}] {c['text'][:100]}")
    elif args.add:
        tiers = args.tiers.split(",") if args.tiers else None
        add_to_seeds(args.add, tiers)
    elif args.high_signal:
        import subprocess
        from pathlib import Path
        print("Generating dedicated high-signal subset for 007 training...")
        subprocess.run([sys.executable, str(Path(__file__).parent / "create_high_signal_subset.py")], check=False)
        print("High-signal subset ready: data/moltbook_hyperlexical_high_signal.jsonl")
    elif args.to_hyperlexical:
        import subprocess
        from pathlib import Path
        print("Triggering Moltbook -> hyperlexical export...")
        subprocess.run([sys.executable, str(Path(__file__).parent / "moltbook_to_hyperlexical.py"), "--batch", str(BATCH), "--out", "data/moltbook_hyperlexical_rows.jsonl"], check=False)
        print("Hyperlexical export done.")
    else:
        print("Use --scan, --add, --to-hyperlexical or --high-signal")
