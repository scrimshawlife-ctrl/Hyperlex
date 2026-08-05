# Slang Family Diagrams

Mermaid source files documenting historical families of slang and emergent branches.

These diagrams are intended for:

- Human reading in GitHub (native Mermaid rendering)
- Orchestra / symbolic exporters that consume `.mmd` with the `orchestra-diagram.v1` header
- Reference material for Abraxas Slang Module `SLANG FAMILY TREE` sections
- Teaching the Hyperlex analysis pipeline how neologisms and hyperstition attach to existing families

## Files

| File | Content |
|------|---------|
| `betting-sharp-family.mmd` | Core betting/sharp-money family and modern tactical extensions |
| `kinship-address.mmd` | Fictive kinship address terms (bro → twin / unc lineage) |
| `emergence-process.mmd` | Abstract process by which Hyperlex detects and archives new branches |

## Rendering

GitHub renders Mermaid automatically. For local HTML previews, copy the pattern used in `examples/hyperlex-symbolic/diagrams/`.

## Adding New Families

1. Reconstruct the historical root with primary sources.
2. Identify the stable semantic/identity payload.
3. Map documented branch points and current emergent candidates.
4. Encode as Mermaid with clear node labels (term + approximate era + payload note).
5. Link from `docs/slang-lineages.md`.
