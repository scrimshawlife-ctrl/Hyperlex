# Changelog

## 0.1.3 — Cache, golden series, LIVE_EMERGENCE_SCAN (2026-08-05)

- Persistent ingest cache (`~/.hyperlex/cache/`) + per-source rate limiting.
- Golden settled series fixture: `examples/calibration/settled_series.v1.json`.
- CLI `scan` (LIVE_EMERGENCE_SCAN) for multi-query cron/autonomous monitoring.
- Hermes cron template: `examples/cron/live-emergence-scan.job.json` + `docs/cron-live-emergence.md`.

## 0.1.2 — Receipt ledger (2026-08-05)

- Append-only hash-chained receipt ledger (`~/.hyperlex/receipt_ledger.jsonl`).
- `emit_receipt(..., append_ledger=True)` indexes each receipt (integrity, lineage, path).
- CLI: `emit-receipt`, `list-receipts`, `verify-receipt-ledger`; `analyze --receipt`.
- Hermes skill packaging already on `main` (v0.1.1); this continues the archive path.

## 0.1.1 — Hermes skill packaging (2026-08-05)

- Full Hermes skill contract in `SKILL.md` (frontmatter, triggers, procedure, authority).
- Atomic-style `install.sh`: `--dry-run`, `--target`, `--rollback`, `--openclaw`, post-install check/smoke.
- `hyperlex.manifest.yaml` expanded for Hermes/OpenClaw hosts and command surface.
- `skills.sh.json`, `QUICKSTART.md`, `references/hermes-runtime-contract.md`.
- Install target: `~/.hermes/skills/hyperlex`.


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

## Calibration v1.1 diagnostics (2026-08-05)

- **Vieira non-negative Yates** (`yates_vieira`): variance mismatch + correlation deficit + bias²; reports ρ when defined.
- **Ferro–Fricker Murphy** (`murphy_ferro`): bias-corrected REL/RES/UNC for small-n series; keeps uncorrected snapshot.
- **Discrimination slope** (`discrimination.delta_f`): mean(f|o=1) − mean(f|o=0).
- Classical Yates enriched with mean_forecast, mean_outcome, cov_fo, var_f, var_o.
- Schema `brier_series.v1` extended; design doc updated.

## Operator settlement path + score log (2026-08-05)

- `calibration/score_log.py` — append-only, hash-chained JSONL (`forecast` / `settlement` / `score` events).
  Default `~/.hyperlex/score_log.jsonl`; override via `HYPERLEX_SCORE_LOG`, `--log`, or `--repo-log`.
- `settle_and_log` + `recompute_series` / `verify_chain`.
- CLI: `analyze --forecasts [--append-log]`, `extract-forecasts`, `settle`, `score-series`, `verify-score-log`.
- `export.to_brier_ledger_entry` — Abraxas `BrierLedgerEntry.v1`-compatible shape (no Abraxas import).
- `recalibrate.mean_shift_from_series` — advisory only when Yates bias² elevated; does not rewrite history.
- Golden tests: lineage confidence formula, score_pair, score_series empty→NOT_COMPUTABLE, log roundtrip, CLI settle path.
- Result schema: `provenance.brier` may be `null`; analysis may include `lineage`.
- CLI import hardening: package `src/` always shadows `scripts/hyperlex.py` on `sys.path`.
