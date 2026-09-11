#!/usr/bin/env python3
"""
Dedicated high-signal subset for hyperlexical model training (007).
Strict filter + FULL classification to meet T1 requirements:
- efficiency >= 0.75 OR (provenance + eff>0.65) OR explicit strong signals
- Always run detect_memetic_patterns for richest typology, roles, fillers, stage
- Roles = memory_tiers + provenance if required
- Fillers = context_loss_technique (or KDR/general)
- Typology includes memory_*, context_*, provenance, compression, hyperstition_signal
- Stage based on efficiency
- class = INFERRED but with full fields for T1 name-gate
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

def is_high_signal(item, eff_score=0.0):
    eff = float(item.get("efficiency", eff_score))
    if eff >= 0.75:
        return True
    if item.get("provenance_required") and eff > 0.65:
        return True
    text = (item.get("inferred", "") + " " + item.get("title", "")).lower()
    if any(p.lower() in text for p in STRONG_PHRASES):
        return True
    return False

def classify_row(text: str, fallback_item: dict = None) -> dict:
    """Full classification pass for T1 compliance."""
    try:
        res = detect_memetic_patterns(text, ingest_source="moltbook")
        mm = res.get("analysis", {}).get("memetic_memory", {})
        eff = res.get("memetic_efficiency") or res.get("analysis", {}).get("memetic_efficiency", {})
        eff_score = float(eff.get("efficiency_score", 0.0))
        comp = res.get("analysis", {}).get("compression", {})
        comp_type = comp.get("compression_type", "load_bearing")
    except Exception:
        eff_score = float(fallback_item.get("efficiency", 0.7)) if fallback_item else 0.7
        comp_type = "load_bearing"
        mm = {"memory_tiers": fallback_item.get("tiers", ["episodic"]) if fallback_item else ["episodic"],
              "provenance_required": fallback_item.get("provenance_required", False) if fallback_item else False,
              "context_loss_technique": None}

    stage = "hyperstition_ish" if eff_score >= 0.75 else "contested" if eff_score >= 0.55 else "circulating"

    typology = []
    if comp_type == "load_bearing":
        typology.append("compression")
    for t in mm.get("memory_tiers", []):
        if t and t != "unknown":
            typology.append(f"memory_{t}")
    if mm.get("context_loss_technique"):
        typology.append(f"context_{mm['context_loss_technique']}")
    if mm.get("provenance_required"):
        typology.append("provenance")
    if eff_score > 0.7:
        typology.append("hyperstition_signal")

    roles = list(mm.get("memory_tiers", []))
    if mm.get("provenance_required"):
        roles.append("provenance")
    if not roles:
        roles = ["episodic"]

    fillers = [mm.get("context_loss_technique")] if mm.get("context_loss_technique") else ["KDR" if any(p in text.lower() for p in ["kdr", "rented", "ghost"]) else "general"]

    return {
        "typology": sorted(set(typology)) or ["memory", "provenance"],
        "stage": stage,
        "roles": roles,
        "fillers": fillers,
        "eff_score": round(eff_score, 3),
        "comp_type": comp_type,
        "mm": mm
    }

def main():
    print("Building T1-compliant high-signal subset (full classification)...")
    
    batch = json.loads(BATCH.read_text()).get("batch", [])
    high_rows = []
    
    for item in batch:
        text = f"{item.get('title','')}. {item.get('inferred','')}"[:320].strip()
        if len(text) < 50:
            continue
        eff = float(item.get("efficiency", 0))
        if not is_high_signal(item, eff):
            continue
        
        cl = classify_row(text, item)
        
        row = {
            "text": text,
            "split": "train",
            "lineage": "ai-native",
            "typology": cl["typology"],
            "stage": cl["stage"],
            "roles": cl["roles"],
            "fillers": cl["fillers"],
            "role_scheme": "type_slot",
            "provenance": {
                "source": "moltbook",
                "post_id": item.get("post_id"),
                "efficiency": cl["eff_score"],
                "compression": cl["comp_type"],
                "class": "INFERRED"
            },
            "class": "INFERRED",
            "license": "MIT (distilled)"
        }
        high_rows.append(row)
    
    # Add from high seeds
    for s in [json.loads(l) for l in open(SEEDS) if l.strip()]:
        text = s["text"][:320]
        labels = s.get("labels", {})
        eff = float(labels.get("efficiency", 0))
        if eff < 0.65 and not labels.get("provenance"):
            continue
        if any(text[:70] in r["text"] for r in high_rows):
            continue
        
        cl = classify_row(text, {"efficiency": eff, "tiers": labels.get("memory_tier", []), "provenance_required": labels.get("provenance", False)})
        
        row = {
            "text": text,
            "split": "train",
            "lineage": "ai-native",
            "typology": cl["typology"],
            "stage": cl["stage"],
            "roles": cl["roles"],
            "fillers": cl["fillers"],
            "role_scheme": "type_slot",
            "provenance": {
                "source": "moltbook-curated-seed",
                "efficiency": cl["eff_score"],
                "class": "INFERRED"
            },
            "class": "INFERRED",
            "license": "MIT (distilled)"
        }
        high_rows.append(row)
    
    # Dedup + sort by eff
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
    
    print(f"Wrote {len(unique)} T1-classified high-signal rows to {OUT}")
    print("Stage breakdown:", {s: sum(1 for r in unique if r["stage"]==s) for s in set(r["stage"] for r in unique)})
    print("Avg roles per row:", sum(len(r["roles"]) for r in unique)/len(unique))
    print("Rows with provenance in roles:", sum(1 for r in unique if "provenance" in r["roles"]))
    print("Top eff:", [r["provenance"]["efficiency"] for r in unique[:5]])

if __name__ == "__main__":
    main()