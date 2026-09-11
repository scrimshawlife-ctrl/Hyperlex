#!/usr/bin/env python3
"""
Dedicated high-signal subset for hyperlexical model training (007).
Strict filter: efficiency >= 0.75 OR (provenance + eff>0.65) OR explicit strong signals from Moltbook.
Matches dataset_row.v0.1 schema. Small, high-quality set for oversampling or focused training.
"""

import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from hyperlex import detect_memetic_patterns

BATCH = Path("out/batch_moltbook_memetics.json")
SEEDS = Path("data/agent_memetics/seed_examples.jsonl")
OUT = Path("data/moltbook_hyperlexical_high_signal.jsonl")

STRONG_PHRASES = ["rented cognition", "ghost in the cache", "SIGINT", "Memory Paradox", "3-Tier Pattern", "Provenance dies", "KDR", "audit log"]

def is_high_signal(item):
    eff = float(item.get("efficiency", 0))
    if eff >= 0.75:
        return True
    if item.get("provenance_required") and eff > 0.65:
        return True
    text = (item.get("inferred", "") + " " + item.get("title", "")).lower()
    if any(p.lower() in text for p in STRONG_PHRASES):
        return True
    return False

def main():
    print("Building *dedicated high-signal* subset for 007 hyperlexical training...")
    
    batch = json.loads(BATCH.read_text()).get("batch", [])
    high_rows = []
    
    for item in batch:
        if not is_high_signal(item):
            continue
        text = f"{item.get('title','')}. {item.get('inferred','')}"[:320].strip()
        if len(text) < 50:
            continue
        
        try:
            res = detect_memetic_patterns(text, ingest_source="moltbook")
            mm = res.get("analysis", {}).get("memetic_memory", {})
            eff = res.get("memetic_efficiency") or res.get("analysis", {}).get("memetic_efficiency", {})
            eff_score = float(eff.get("efficiency_score", item.get("efficiency", 0.75)))
            comp = res.get("analysis", {}).get("compression", {})
            comp_type = comp.get("compression_type", "load_bearing")
        except Exception:
            eff_score = float(item.get("efficiency", 0.75))
            comp_type = "load_bearing"
            mm = {"memory_tiers": item.get("tiers", ["episodic"]), "provenance_required": item.get("provenance_required", False)}
        
        stage = "hyperstition_ish" if eff_score >= 0.75 else "contested"
        typology = ["memory"]
        if mm.get("provenance_required"):
            typology.append("provenance")
        if comp_type == "load_bearing":
            typology.append("compression")
        if any(p in text.lower() for p in ["kdr", "rented", "ghost", "context loss"]):
            typology.append("context_friction")
        
        row = {
            "text": text,
            "split": "train",
            "lineage": "ai-native",
            "typology": sorted(set(typology)),
            "stage": stage,
            "roles": mm.get("memory_tiers", ["episodic"]),
            "fillers": [mm.get("context_loss_technique") or "KDR"],
            "role_scheme": "type_slot",
            "provenance": {
                "source": "moltbook",
                "post_id": item.get("post_id"),
                "efficiency": round(eff_score, 3),
                "compression": comp_type,
                "class": "INFERRED"
            },
            "class": "INFERRED",
            "license": "MIT (distilled)"
        }
        high_rows.append(row)
    
    # Pull additional from curated high seeds
    for s in [json.loads(l) for l in open(SEEDS) if l.strip()]:
        text = s["text"][:320]
        labels = s.get("labels", {})
        eff = float(labels.get("efficiency", 0))
        if eff < 0.7 and not labels.get("provenance"):
            continue
        if any(text[:70] in r["text"] for r in high_rows):
            continue
        typology = ["memory", "provenance"] if labels.get("provenance") else ["memory"]
        if labels.get("compression") == "load_bearing":
            typology.append("compression")
        row = {
            "text": text,
            "split": "train",
            "lineage": "ai-native",
            "typology": sorted(set(typology)),
            "stage": "hyperstition_ish" if eff >= 0.75 else "contested",
            "roles": labels.get("memory_tier", ["episodic"]),
            "fillers": ["KDR"] if any(p in text.lower() for p in STRONG_PHRASES) else ["general"],
            "role_scheme": "type_slot",
            "provenance": {
                "source": "moltbook-curated-seed",
                "efficiency": round(eff, 3),
                "class": "INFERRED"
            },
            "class": "INFERRED",
            "license": "MIT (distilled)"
        }
        high_rows.append(row)
    
    # Dedup + sort by efficiency desc
    seen = set()
    unique = []
    for r in sorted(high_rows, key=lambda x: -x["provenance"].get("efficiency", 0)):
        key = r["text"][:70]
        if key not in seen:
            seen.add(key)
            unique.append(r)
    
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as f:
        for r in unique:
            f.write(json.dumps(r) + "\n")
    
    print(f"Wrote {len(unique)} dedicated high-signal rows to {OUT}")
    print("Stage breakdown:", {s: sum(1 for r in unique if r["stage"]==s) for s in set(r["stage"] for r in unique)})
    print("Example typologies:", [r["typology"] for r in unique[:3]])
    print("Top efficiencies:", sorted([r["provenance"]["efficiency"] for r in unique], reverse=True)[:5])

if __name__ == "__main__":
    main()