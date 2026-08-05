# Changelog

## 0.2.11 — GitHub Pages enabled + long-term analysis archive (2026-08-05)

- GitHub Pages enabled (Actions build) → https://scrimshawlife-ctrl.github.io/Hyperlex-Hermes-Specs/
- `archive-export` writes sanitized ingest/analysis snapshots under `docs/archive/`
  for long-term review on the docs site (local ~/.hyperlex remains primary store).
- Docs: `docs/archive/README.md`; MkDocs nav includes analysis archive.

## 0.2.10 — OpenAI-compatible LLM provider, ledger-stats, STATUS (2026-08-05)

- Governed LLM: `HYPERLEX_LLM_PROVIDER=openai_compatible` (stdlib urllib; fail-closed offline).
- CLI `ledger-stats` aggregates family/stage/source counts from receipt ledger.
- `STATUS.md` skill readiness snapshot.

## 0.2.9 — Skill doctor, Pages URL, release preflight (2026-08-05)

- CLI `doctor`: deep Hermes-skill health (files, API_V1, mock analyze, brier null, goldens, compat).
- Expanded `scripts/release_preflight.py` (doctor, diagram, case study, tests).
- MkDocs `site_url` set for GitHub Pages project site.

## 0.2.8 — Docs site deploy, strict MkDocs, CI case study (2026-08-05)

- GitHub Pages workflow (`.github/workflows/docs.yml`) builds/deploys MkDocs.
- `scripts/sync_mkdocs_pages.py` rewrites root-doc links for strict builds.
- Skill CI runs case study script; docs ROADMAP mirrored to site.
- MkDocs `--strict` clean (README excluded from site).

## 0.2.7 — MkDocs site, governed LLM stub, ledger-diff (2026-08-05)

- MkDocs documentation site (`mkdocs.yml`, optional extra `[docs]`).
- Governed LLM neologism enrichment (`hyperlex.llm`); requires `HYPERLEX_LLM=1` + provider.
- CLI `ledger-diff` compares two receipt snapshots.
- Docs: `docs/modules/llm.md`, `docs/index.md`.

## 0.2.6 — Case study + cross-domain lineages (2026-08-05)

- Case study: `examples/case-studies/e2e-mock-scan.md` + `scripts/run_case_study.py`.
- New lineage families: `gaming-meta`, `workplace-corp` (registry, Mermaid, mock seeds, goldens).
- Typology: `labor_identity`; gaming cues on `platform_agency`.

## 0.2.5 — Virality prediction v0, community drivers, richer neologisms (2026-08-05)

- `predict_virality` → `analysis.virality.prediction` (SPECULATIVE; not Brier/calibration).
- Semantic variation multi-label community drivers.
- Neologism detector: compound phrases + formation tags.
- Docs: `docs/modules/virality.md`.

## 0.2.4 — Hermes skill posture, CI, typology, goldens (2026-08-05)

- Docs: Hyperlex is a **Hermes skill (Python package repo)** — not a separate product app.
  `docs/hermes-skill.md` replaces standalone-app framing.
- CI: `PYTHONPATH=src`, offline env, diagram --from-golden step.
- Memetic typology expansion: multi-type rule table + lineage soft prior + transparent rules_hit.
- Golden receipts: kinship-address, political-status (+ typology field in MANIFEST).

## 0.2.3 — Receipt history diagrams (2026-08-05)

- `hyperlex.diagrams` — Mermaid lineage distribution, receipt timeline, family graph, per-receipt flow.
- CLI `diagram --from-golden|--from-ledger|--input` writes `.mmd` + optional HTML.
- Docs: `docs/diagrams.md`.

## 0.2.2 — Docs refresh, market connectors, hyperstition feedback (2026-08-05)

- Full docs pass: ARCHITECTURE, README, QUICKSTART, RELEASE_NOTES, connectors.md.
- `hyperlex.connectors.market_signal` — market_signal.v1 + forecast_pipeline.v1 packets.
- `hyperlex.connectors.hyperstition_feedback` — advisory stage→f map from settled series.
- CLI: `signal`, `feedback`; `extract_forecasts(..., hyperstition_stage_map=...)`.
- Roadmap: hyperstition feedback + market connectors marked done.

## 0.2.1 — Standalone app, API freeze, golden receipts, Abraxas modules (2026-08-05)

- Docs synced: `docs/ROADMAP.md`, `docs/api-v1.md`, `docs/hermes-skill.md`, SPEC/DESIGN.
- Public API v1 freeze via `hyperlex.API_V1`.
- Golden receipt corpus: `examples/receipts/golden/` + MANIFEST.
- Relevant Abraxas capabilities as Hyperlex modules: `hyperlex.compat.abraxas`
  (claims, BrierScorePacket, BrierLedgerEntry, operator review, HLX runes).
- Hyperlex never imports Abraxas; hosts may import from Hyperlex.

## 0.2.0 — Relay, provenance, glossary/X, local package (2026-08-05)

- Rune/signal relay: `hyperlex.relay` + CLI `relay` + `schemas/rune_envelope.v1.schema.json`
- Enhanced provenance fingerprints on ingest + analysis (`source_fingerprint`, content_hash, locator)
- Glossary expansion (`glossary_expanded`) multi-source pack; X ingest via bearer token / xurl / stub
- Package CLI (`python -m hyperlex` / console script); optional local build via `scripts/publish_pypi.sh` (no public PyPI publish)
- Version 0.2.0

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
