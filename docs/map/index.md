---
title: Slang lineage map
hide:
  - toc
---

# Slang lineage map

<div class="hlx-status" markdown>
<span><span class="hlx-dot"></span><strong>Interactive</strong></span>
<span>8 families · registry + YTD leaves</span>
<span>Static export · not live DB</span>
<span>Similarity / map ≠ Brier</span>
</div>

<p class="hlx-lead">
<strong>One glance:</strong> hubs are families, size is term count, color is domain.
Click a hub to open leaves. Search jumps to the family that owns a term.
</p>

<div class="hlx-path-grid" markdown>

<div class="hlx-path-card hlx-path-card--primary" markdown>

**How to read**

Map position and cosine neighbors are **structure**, not forecast skill.

[Reading evidence →](../demos/reading-evidence.md){ .md-button .md-button--primary }

</div>

<div class="hlx-path-card" markdown>

**Docs**

Mutation operators, family write-ups, Mermaid sources.

[Slang lineages →](../slang-lineages.md){ .md-button }

</div>

</div>

<div id="hlx-lineage-map" class="hlx-map-root" data-src="lineage-map.json"></div>

## Instant legend

| You see | Means |
|---------|--------|
| **Center hub** | All families (click to reset) |
| **Ring of disks** | One **lineage family** each |
| **Disk size** | Number of atomic terms in registry |
| **Disk color** | Domain hue (betting, crypto, AI, …) |
| **Orbit labels** | Atomic terms after you open a family |
| **Month chip** | First seen in YTD backfill packs (if any) |

## Why this shape

Slang is not a flat dictionary. Hyperlex stores **phylogenetic families**
(root payload → trunk → branches → leaves). A radial constellation keeps:

1. **Global structure** always visible (8 hubs)  
2. **Local detail** on demand (terms after click)  
3. **No force-layout spaghetti** on first paint  

Static Mermaid family trees still live under `examples/slang-families/`.
This map is the **overview instrument** for researchers and operators.

## Data source

| Field | Source |
|-------|--------|
| Families + terms | `LINEAGE_REGISTRY` in `hyperlex.analysis` |
| First-seen months | `data/backfill/2026/*.json` |
| Export | `scripts/export_lineage_map.py` → `map/lineage-map.json` |

```bash
python3 scripts/export_lineage_map.py
# commits docs/map/lineage-map.json for Pages
```

Machine graph: [`lineage-map.json`](./lineage-map.json)
