# Slang Family Diagrams

Mermaid source files documenting historical families of slang and emergent branches.

These diagrams are intended for:

- Human reading in GitHub (native Mermaid rendering)
- Orchestra / symbolic exporters that consume `.mmd` with the `orchestra-diagram.v1` header
- Reference material for Abraxas Slang Module `SLANG FAMILY TREE` sections
- Teaching the Hyperlex analysis pipeline how neologisms and hyperstition attach to existing families
- Live matching via `hyperlex.analysis.match_lineage()` (static registry seeded from these families)

## Files

| File | Content |
|------|---------|
| `betting-sharp-family.mmd` | Core betting/sharp-money family and modern tactical extensions |
| `kinship-address.mmd` | Fictive kinship address terms (bro → twin / unc lineage) |
| `crypto-degen-family.mmd` | HODL / diamond hands / ape / rekt / degen cluster |
| `brainrot-aura-family.mmd` | Content-degradation + status-signaling lineage (mid / cooked / aura / brainrot) |
| `ai-native-family.mmd` | Hallucinate → slop → clanker / agentic cluster |
| `political-status-family.mmd` | Based / redpilled / cope tribal-judgment lineage |
| `gaming-meta-family.mmd` | Nerf / buff / meta / sweaty multiplayer status |
| `workplace-corp-family.mmd` | Quiet quitting / RTO / bandwidth corporate labor speech |
| `sharp-family-timeline.mmd` | Chronological drift view of the betting-sharp family |
| `emergence-process.mmd` | Abstract process by which Hyperlex detects and archives new branches |

## HTML Renderers

| File | Renders |
|------|--------|
| `render-betting-sharp.html` | Betting / sharp mindmap |
| `render-ai-native.html` | AI-native mindmap |
| `render-emergence.html` | Emergence process flowchart |

Open locally or via GitHub Pages / raw.githubusercontent for interactive Mermaid views.

## Rendering

GitHub renders Mermaid automatically in `.md` and `.mmd` when viewed as text. HTML files use the mermaid.js CDN for standalone viewing.

## Adding New Families

1. Reconstruct the historical root with primary sources (see template in `docs/slang-lineages.md`).
2. Identify the stable semantic/identity payload.
3. Map documented branch points and current emergent candidates using the mutation operators table.
4. Encode as Mermaid with clear node labels (term + approximate era + payload note).
5. Add the family to `LINEAGE_REGISTRY` in `src/hyperlex/analysis/__init__.py` so the matcher can find it.
6. Link from `docs/slang-lineages.md` and update this README.
7. Prefer OBSERVED sources; mark INFERRED / SPECULATIVE explicitly when necessary.
