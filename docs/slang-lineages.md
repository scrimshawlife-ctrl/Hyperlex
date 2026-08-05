# Slang Lineages & Emergent Branches

**Status**: Active documentation surface  
**Purpose**: Provide canonical visual and structural documentation for historical families of slang words and the processes by which new branches emerge. This layer supports Hyperlex analysis outputs, Abraxas Slang Module family-tree sections, and Orchestra symbolic mapping.

## Why Lineages Matter

Slang is not a flat inventory of terms. It forms phylogenetic structures:

- **Roots**: older forms, often from specialized communities (criminal cant, occupational jargon, AAVE, military, betting syndicates).
- **Trunk / Core family**: stable semantic and social payload that persists across mutations.
- **Branches**: new senses, intensifiers, ironic inversions, platform-specific compressions, or hyperstitious loops.
- **Emergent leaves**: recent neologisms or eggcorn events that may stabilize or die.

Hyperlex treats these structures as first-class signals. `detect_neologisms` flags candidate branch points. `trace_semantic_variation` maps drift drivers. `simulate_hyperstition_loop` identifies self-reinforcing pathways that can accelerate a branch into cultural infrastructure.

## Documentation Method

1. **Historical reconstruction** — trace earliest attested uses (Green’s Dictionary of Slang, OED, domain glossaries, arXiv cultural-transmission papers).
2. **Semantic payload mapping** — record core emotional, identity, and routing functions that survive mutations.
3. **Branch points** — mark documented mutations (extra-grammatical formation, sense extension, irony inversion, platform compression).
4. **Emergent monitoring** — live signals from X, Reddit, Urban Dictionary, and domain sources feed candidate new branches.
5. **Visual encoding** — Mermaid diagrams (trees, mindmaps, flowcharts) stored under `examples/slang-families/` and rendered in GitHub Markdown or Orchestra HTML exporters.

## Core Diagram Types

| Type | Mermaid construct | Use |
|------|-------------------|-----|
| Family tree | `flowchart TB` or `mindmap` | Historical root → core family → branches |
| Emergence process | `flowchart LR` | Signal intake → variation → hyperstition → archive |
| Drift timeline | `timeline` or sequenced nodes | Chronological mutation events |
| Network of related terms | `graph` | Cross-family borrowing and convergence |

## Integration Points

- **Analysis module** (`zone_of_emergence`): lineage metadata can be attached to `analysis.neologisms` and `analysis.semantic_variation` in future schema extensions.
- **Receipts**: provenance may later include `lineage_refs` pointing to documented families.
- **Abraxas Slang Emulation**: the mandatory `SLANG FAMILY TREE` section in SIGNAL REPORTs is the live counterpart of these static diagrams.
- **Orchestra**: diagrams are compatible with the existing `orchestra-diagram.v1` comment headers used in `examples/hyperlex-symbolic/`.

## Example Families Documented

See `examples/slang-families/`:

- `betting-sharp-family.mmd` — the sharp/steam/square cluster and its modern extensions (including project-specific “holler” and “revenge” forms).
- `kinship-address.mmd` — the bro/sis/twin/unc lineage and its acceleration via social platforms.
- `emergence-process.mmd` — the abstract Hyperlex process that generates new branches.

## Future Work

- Schema field `lineage` under `analysis` (v0.2+).
- Automated diagram generation from receipt histories.
- Cross-domain family libraries (finance, AI-native, political, regional).
- Brier-calibrated forecasts of branch survivability.

## References

- Green’s Dictionary of Slang (historical backbone)
- arXiv papers listed in `references/arxiv_papers.md` (especially semantic variation and cultural transmission)
- Hyperlex DESIGN principles 1–3 (real signals, provenance, arXiv grounding)
