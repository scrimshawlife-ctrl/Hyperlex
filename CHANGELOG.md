# Changelog

## 0.1.0

- Added executable Hermes skill runtime for standalone use.
- Added `src/hyperlex` implementation package (copied from working engine implementation).
- Added command entrypoint `scripts/hyperlex.py` with `check`, `sources`, `ingest`, `analyze`, `validate`, and `verify-receipt`.
- Added schemas at repository root (`schemas/*.schema.json`) and manifest metadata.
- Added install script and initial command smoke/test surface.
- Updated SKILL/README/SPEC/docs references to reflect implemented runtime surface.

## Documentation & Lineage (2026-08-05)

- Added and expanded `docs/slang-lineages.md` (methodology, mutation operators, template, live-feed process).
- Added `schemas/lineage.v1.schema.json` for analysis lineage attachments.
- Implemented `match_lineage()` in `src/hyperlex/analysis` and wired it into `detect_memetic_patterns` so results carry `analysis.lineage` when a family matches.
- Added `examples/slang-families/` with Mermaid diagrams and HTML renderers:
  - betting-sharp family + timeline
  - kinship-address
  - crypto-degen (HODL → diamond hands → ape/rekt/degen)
  - brainrot-aura (mid/cooked/aura/brainrot)
  - ai-native (hallucinate → slop → clanker/agentic)
  - political-status (based/redpilled/cope)
  - emergence process
- Updated DESIGN.md (principle 11), ROADMAP.md, schemas/README, and examples README.
