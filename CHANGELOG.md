# Changelog

## 0.1.0

- Added executable Hermes skill runtime for standalone use.
- Added `src/hyperlex` implementation package (copied from working engine implementation).
- Added command entrypoint `scripts/hyperlex.py` with `check`, `sources`, `ingest`, `analyze`, `validate`, and `verify-receipt`.
- Added schemas at repository root (`schemas/*.schema.json`) and manifest metadata.
- Added install script and initial command smoke/test surface.
- Updated SKILL/README/SPEC/docs references to reflect implemented runtime surface.

## Documentation (2026-08-05)

- Added `docs/slang-lineages.md` — methodology for documenting historical families of slang and emergent branches.
- Added `examples/slang-families/` with Mermaid diagrams:
  - betting-sharp family tree
  - kinship-address lineage (bro/sis/twin/unc)
  - Hyperlex emergence process flowchart
- Updated DESIGN.md (principle 11) and ROADMAP.md (Phase 2 items) to treat lineage structure as first-class.
