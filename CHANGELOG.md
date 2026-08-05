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
- Implemented `match_lineage()` with confidence scoring; wired into `detect_memetic_patterns`.
- Added `examples/slang-families/` with Mermaid diagrams and HTML renderers.

## Brier / Calibration (2026-08-05)

- Design: `docs/brier-calibration.md` (forecast → settlement → atomic/series Brier, Murphy, Yates, BSS).
- Module: `src/hyperlex/calibration/` (`extract_forecasts`, `settle`, `score_pair`, `score_series`).
- Schemas: `forecast.v1`, `settlement.v1`, `brier_series.v1`.
- Removed hardcoded `provenance.brier = 0.89`; open results set `brier: null` with `brier_requires_settlement`.
- DESIGN principle 12: Brier requires settlement; fail-closed `NOT_COMPUTABLE` when outcomes missing.
