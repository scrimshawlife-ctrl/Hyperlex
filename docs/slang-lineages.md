# Slang Lineages & Emergent Branches

**Status**: Active documentation surface  
**Version**: expanded 2026-08-05  
**Purpose**: Provide canonical visual and structural documentation for historical families of slang words and the processes by which new branches emerge. This layer supports Hyperlex analysis outputs, Abraxas Slang Module family-tree sections, and Orchestra symbolic mapping.

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

### Documentation Template (copy for new families)

```markdown
## Family: [Name]

**Domain**: [betting | crypto | kinship | internet-compression | ...]
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

- **Analysis module** (`zone_of_emergence`): lineage metadata can be attached to `analysis.neologisms` and `analysis.semantic_variation`.
- **Receipts**: provenance may include `lineage_refs` pointing to documented families.
- **Abraxas Slang Emulation**: the mandatory `SLANG FAMILY TREE` section in SIGNAL REPORTs is the live counterpart of these static diagrams.
- **Orchestra**: diagrams carry the `orchestra-diagram.v1` header pattern already used in `examples/hyperlex-symbolic/`.

### Example Receipt Attachment (future schema sketch)

```json
"analysis": {
  "neologisms": [...],
  "semantic_variation": {...},
  "lineage": {
    "family_id": "betting-sharp",
    "matched_terms": ["steam", "sharp money revenge"],
    "branch_operator": "sense_extension + hyperstition",
    "confidence": 0.81,
    "diagram_ref": "examples/slang-families/betting-sharp-family.mmd"
  }
}
```

## Example Families Documented

See `examples/slang-families/`:

- `betting-sharp-family.mmd` — sharp/steam/square cluster and modern tactical extensions.
- `kinship-address.mmd` — bro/sis/twin/unc lineage and platform acceleration.
- `crypto-degen-family.mmd` — HODL → diamond hands → ape/rekt/degen cluster.
- `brainrot-aura-family.mmd` — content-degradation + status-signaling lineage (mid/cooked/aura/brainrot).
- `sharp-family-timeline.mmd` — chronological drift view of the betting-sharp family.
- `emergence-process.mmd` — abstract Hyperlex process that generates new branches.

## Live Feed Process

1. Hyperlex (or Abraxas Slang Module) detects candidate terms via ingest + neologism pipeline.
2. Analyst or automated rule matches against existing family IDs.
3. If no match and confidence is high, a new provisional leaf or family is proposed.
4. Documentation is updated (diagram + markdown entry) only after human review of provenance.
5. Future automated path: receipt histories → candidate diagram diffs → human approval gate.

## Future Work

- Schema field `lineage` under `analysis` (v0.2+).
- Automated diagram generation / diffing from receipt histories.
- Cross-domain family libraries (finance, AI-native, political, regional, sports beyond betting).
- Brier-calibrated forecasts of branch survivability.
- HTML interactive renderers matching the Orchestra diagram style.

## References

- Green’s Dictionary of Slang (historical backbone)
- arXiv papers listed in `references/arxiv_papers.md` (semantic variation, cultural transmission, memetics, hyperstition)
- Hyperlex DESIGN principles (especially Real Over Synthetic, Provenance, ArXiv-Grounded, Lineage as First-Class Structure)
- Domain primary sources: BitcoinTalk archives, WallStreetBets, early gaming forums, Action Network glossary, Urban Dictionary attestations
