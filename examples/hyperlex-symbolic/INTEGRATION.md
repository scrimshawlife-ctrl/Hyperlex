# Hyperlex + Abraxas-Orchestra Integration

## Current State (2026-08-05)
- Symbolic architecture applied to actual source code.
- Dual-named structure live in `src/hyperlex/`:
  - `intake/` — gate_of_intake (real wired ingest)
  - `analysis/` — zone_of_emergence (core memetic modules + arXiv concepts)
  - `synthesis/` — current_of_transmission (external signal feed)
  - `receipt/` — archive_of_becoming (emit_receipt + provenance)
- Top-level __init__ re-exports the public API.
- engine.py is now a thin backward-compat shim.
- All tests and CLI pass.

## Symbolic Correspondence (curated)
See numogram-chaos-correspondence.json and SKELETON.md.

Framework: numogram (primary) + chaos-magic (overlay)

## How to Use with Orchestra
1. `python3 ~/.hermes/skills/orchestra/scripts/orchestra.py analyze --path . -f numogram -o chaos-magic`
2. The curated mapping lives in `symbolic/`.
3. Diagrams in `symbolic/diagrams/`.

## Next Integration Opportunities
- Add Hyperlex as a native signal-forager in Orchestra frameworks.
- Use Orchestra `project` or `structure` to generate more of the package.
- Wire real Orchestra runes to the synthesis output.
- Make Hyperlex emit receipts in Orchestra-compatible format.

## Package Structure Now Mirrors Symbolic
src/hyperlex/          ← mechanical
├── intake/            ← gate_of_intake
├── analysis/          ← zone_of_emergence
├── synthesis/         ← current_of_transmission
├── receipt/           ← archive_of_becoming
└── ...

See SKELETON.md for full dual names and loci.
