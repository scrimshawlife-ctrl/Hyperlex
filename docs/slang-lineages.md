# Slang Lineages & Emergent Branches

**Status**: Active documentation surface  
**Version**: expanded 2026-08-05 (schema + matcher + confidence scoring + HTML + additional families + YTD backfill/backprop)  
**Purpose**: Provide canonical visual and structural documentation for historical families of slang words and the processes by which new branches emerge. This layer supports Hyperlex analysis outputs, Abraxas Slang Module family-tree sections, and Orchestra symbolic mapping.

!!! tip "Interactive overview"
    For a **dynamic radial map** of all families and terms (click hubs, search leaves),
    open the [Slang lineage map](map/index.md). Static Mermaid family trees remain below
    and under `examples/slang-families/`.

## Why Lineages Matter

Slang is not a flat inventory of terms. It forms phylogenetic structures:

- **Roots**: older forms, often from specialized communities (criminal cant, occupational jargon, AAVE, military, betting syndicates, early internet/gaming).
- **Trunk / Core family**: stable semantic and social payload that persists across mutations.
- **Branches**: new senses, intensifiers, ironic inversions, platform-specific compressions, or hyperstitious loops.
- **Emergent leaves**: recent neologisms or eggcorn events that may stabilize or die.

Hyperlex treats these structures as first-class signals. `detect_neologisms` flags candidate branch points. `trace_semantic_variation` maps drift drivers. `simulate_hyperstition_loop` identifies self-reinforcing pathways that can accelerate a branch into cultural infrastructure.

A well-documented lineage turns a single observed term into a structured signal: it tells the system *what family it belongs to*, *what payload it still carries*, *how far it has drifted*, and *whether it is currently actualizing*.

## Mutation Operators

These are the primary ways new branches form. Document them explicitly when reconstructing a family.

| Operator | Description | Example |
|----------|-------------|--------|
| **Extra-grammatical formation** | Novel compounds, blends, or zero-derivations that violate ordinary morphology | “low block”, “false nine” style candidates |
| **Sense extension / specialization** | Existing term gains a tighter domain meaning | “steam” from general force → coordinated sharp line pressure |
| **Irony inversion** | Positive or neutral term flipped for status or critique | “based” → layered ironic uses; “aura” positive → “negative aura” |
| **Platform compression** | Extreme shortening or orthographic mutation optimized for a medium | “rekt”, “HODL”, vowel-dropped forms |
| **Eggcorn / folk etymology** | Mishearing or reanalysis that stabilizes as a new form | classic eggcorn events treated as symbolic adaptation |
| **Cross-family borrowing** | Term migrates and re-specializes in a new community | gaming “rekt” → crypto; WallStreetBets “diamond hands” → crypto |
| **Hyperstition loop** | Narrative about the term begins to produce the behavior the term describes | “steam” chase behavior reinforcing the line-move narrative |

## Documentation Method

1. **Historical reconstruction** — earliest attested uses (Green’s Dictionary of Slang, OED, domain glossaries, forum archives, arXiv cultural-transmission papers).
2. **Semantic payload mapping** — core emotional, identity, and routing functions that survive mutations. Ask: what social work does this family still do?
3. **Branch points** — mark documented mutations with operator type and approximate era.
4. **Emergent monitoring** — live signals from X, Reddit, Urban Dictionary, domain glossaries, and Hyperlex ingest feed candidate new leaves.
5. **Visual encoding** — Mermaid diagrams stored under `examples/slang-families/`.
6. **Provenance tagging** — every claim about a root or branch should be OBSERVED / INFERRED / SPECULATIVE where possible.
7. **Registry + matcher** — add the family to `LINEAGE_REGISTRY` in `src/hyperlex/analysis/__init__.py` so `match_lineage()` can attach it at runtime.

### Documentation Template (copy for new families)

```markdown
## Family: [Name]

**Domain**: [betting | crypto | kinship | internet-compression | ai-native | political-status | ...]
**Core payload**: [one-sentence identity / emotional / routing function]
**Root (OBSERVED)**: [earliest form + source + era]
**Trunk**: [stable core terms]
**Key branches**:
- [term] — [operator] — [era] — [payload shift]
**Current emergent leaves**: [list with confidence]
**Hyperstition risk**: [low/medium/high + brief mechanism]
**Diagram**: examples/slang-families/[name].mmd
```

## Core Diagram Types

| Type | Mermaid construct | Use |
|------|-------------------|-----|
| Family tree / mindmap | `mindmap` or `flowchart TB` | Historical root → core → branches → leaves |
| Emergence process | `flowchart LR` | Signal intake → variation → hyperstition → archive |
| Drift timeline | `timeline` or sequenced flowchart | Chronological mutation events |
| Network of related terms | `graph` | Cross-family borrowing and convergence |

## Integration Points

- **Analysis module** (`zone_of_emergence`): `match_lineage()` runs inside `detect_memetic_patterns` and attaches a `lineage` object under `analysis` when a match is found.
- **Schema**: `schemas/lineage.v1.schema.json` defines the attachment shape (including optional `score_breakdown`).
- **Receipts**: provenance can later include `lineage_refs` pointing to documented families.
- **Abraxas Slang Emulation**: the mandatory `SLANG FAMILY TREE` section in SIGNAL REPORTs is the live counterpart of these static diagrams.
- **Orchestra**: diagrams carry the `orchestra-diagram.v1` header pattern already used in `examples/hyperlex-symbolic/`.

### Live Lineage Attachment (current)

```json
"analysis": {
  "neologisms": [...],
  "semantic_variation": {...},
  "lineage": {
    "family_id": "betting-sharp",
    "matched_terms": ["steam", "sharp"],
    "branch_operator": "sense_extension",
    "confidence": 0.72,
    "diagram_ref": "examples/slang-families/betting-sharp-family.mmd",
    "payload_note": "professional edge vs public money; line-physics signaling",
    "provenance": "INFERRED",
    "score_breakdown": {
      "n_hits": 2,
      "specificity": 0.41,
      "coverage": 0.22,
      "hit_bonus": 0.22,
      "density": 0.06,
      "raw": 0.72,
      "term_weights": {"steam": 0.37, "sharp": 0.37}
    }
  }
}
```

## Confidence Scoring

`compute_lineage_confidence(hits, family_terms, corpus)` produces a deterministic score in `[0, 0.98]`.

**Components**

| Component | What it measures | Role |
|-----------|------------------|------|
| **specificity** | Average term-weight of the hits | Longer and multi-word terms (e.g. “diamond hands”, “aura farming”) are more distinctive than short common ones (“ape”, “mid”, “bro”) |
| **coverage** | `len(hits) / len(family_terms)` | Fraction of the family’s known vocabulary that appeared |
| **hit_bonus** | Diminishing returns per additional distinct hit | 1st hit ≈ 0.12, 2nd ≈ 0.10, … floor ≈ 0.04; capped |
| **density** | Co-occurrence of ≥2 hits in a compact corpus | Multiple related terms close together is stronger evidence than scattered single hits |

**Term weight** (specificity prior):

```
weight = min(0.75, 0.22 + 0.14 * n_words + 0.025 * min(len(term), 24))
```

**Raw score**:

```
raw = 0.18 + specificity * 0.38 + coverage * 0.22 + hit_bonus + density
confidence = min(0.98, max(0.0, raw))
```

**Matching rules**
- Multi-word terms: substring match (already distinctive).
- Single-word terms: word-boundary match (`\bterm\b`) to avoid false positives (“steam” inside “steamed”, “ape” inside “escape”).

**Threshold**: `LINEAGE_CONFIDENCE_THRESHOLD = 0.42`. Matches below this are discarded so weak single short-term hits do not attach a lineage.

The full breakdown is returned under `score_breakdown` for auditability and future calibration.

## YTD backfill + lineage backpropagation

Hyperlex can **backfill** curated slang terms for prior months of the year and **backpropagate** lineage labels onto historical receipts **without rewriting integrity**.

| Piece | Location | Role |
|-------|----------|------|
| Monthly packs | `data/backfill/2026/YYYY-MM.json` | Curated term seeds (OBSERVED / INFERRED / SPECULATIVE) |
| Loader / merge | `hyperlex.analysis.backfill` | Inventory + in-memory registry overlay |
| Rematch report | `hyperlex.analysis.backprop` | Re-run `match_lineage` on goldens/archive/local receipts |
| CLI | `lineage-backfill`, `lineage-backprop` | Operator surface |

```bash
python3 scripts/hyperlex.py lineage-backfill --list --through 2026-08
python3 scripts/hyperlex.py lineage-backprop --from-golden --out out/backprop/report.json
```

**Integrity rules**

1. Historical receipt JSON and `provenance.integrity` are never rewritten by backprop.
2. Report schema: `hyperlex.lineage_backprop.v1` (change classes: `unchanged`, `gained`, `lost`, `reclassified`, `confidence_shift`).
3. Brier remains null until settlement — backfill does not invent scores.
4. Optional: re-run `archive-export` for a new sanitized Pages snapshot after reviewing the report.

`match_lineage(text, registry=...)` accepts an overlay so backprop can use merged packs without permanently mutating the process-global `LINEAGE_REGISTRY`. Base registry still includes the main 2026 leaves so live analyze benefits immediately.

See `data/backfill/2026/README.md` for pack schema and month notes.  
Visual timeline: `examples/slang-families/ytd-2026-timeline.mmd`.

## Example Families Documented

See `examples/slang-families/`:

- `betting-sharp-family.mmd` + `sharp-family-timeline.mmd` — sharp/steam/square cluster and chronological drift.
- `kinship-address.mmd` — bro/sis/twin/unc lineage and platform acceleration.
- `crypto-degen-family.mmd` — HODL → diamond hands → ape/rekt/degen cluster.
- `brainrot-aura-family.mmd` — content-degradation + status-signaling (mid/cooked/aura/brainrot).
- `ai-native-family.mmd` — hallucinate → slop → clanker / agentic.
- `political-status-family.mmd` — based / redpilled / cope tribal-judgment lineage.
- `emergence-process.mmd` — abstract Hyperlex process that generates new branches.

HTML renderers: `render-betting-sharp.html`, `render-ai-native.html`, `render-emergence.html`.

## Live Feed Process

1. Hyperlex (or Abraxas Slang Module) detects candidate terms via ingest + neologism pipeline.
2. `match_lineage()` scores against the static registry (seeded from the families above) using the confidence formula above.
3. Highest-confidence match that clears the threshold is attached under `analysis.lineage`.
4. If no match and confidence would be high for a novel cluster, a provisional leaf or family is proposed for human documentation.
5. Documentation is updated (diagram + markdown entry + registry entry) only after human review of provenance.
6. Future path: receipt histories → candidate diagram diffs → human approval gate.

## Future Work

- Full schema validation of `analysis.lineage` inside `validate_result`.
- Automated diagram generation / diffing from receipt histories.
- Expanded cross-domain libraries (regional, sports beyond betting, finance subtypes).
- Brier-calibrated forecasts of branch survivability (using the confidence score as a prior).
- Richer interactive Orchestra-style HTML (node tooltips, flow highlighting).
- Learned term weights from historical receipt outcomes instead of the current heuristic.

## References

- Green’s Dictionary of Slang (historical backbone)
- arXiv papers listed in `references/arxiv_papers.md` (semantic variation, cultural transmission, memetics, hyperstition)
- Hyperlex DESIGN principles (especially Real Over Synthetic, Provenance, ArXiv-Grounded, Lineage as First-Class Structure)
- Domain primary sources: BitcoinTalk archives, WallStreetBets, early gaming forums, Action Network glossary, Urban Dictionary attestations, Simon Willison / mainstream coverage of “slop” (2024)

## Registry families (matcher seed)

betting-sharp · crypto-degen · ai-native · brainrot-aura · kinship-address · political-status · **gaming-meta** · **workplace-corp**
