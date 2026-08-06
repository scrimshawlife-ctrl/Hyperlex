# Changelog

## Unreleased

- **SIGNAL REPORT parity (Companion adaptation):** `result.v1` extended with optional `provenance.seed`, `analysis.compression_metrics`, `analysis.symbolic_role`, `analysis.propagation_vector`, `analysis.slang_family_tree`, `analysis.signal_report` (schema + package-local copy). Docs: `docs/superpowers/specs/2026-08-06-signal-report-adaptation.md`. Analysis population still pending; all new fields optional and fail-open. Brier remains null on open analysis.
- **Ingest ↔ vector:** fail-open auto-index on `pipeline` / `run` / receipt emit (`hyperlex.vectordb.autoindex`); respects `HYPERLEX_VECTOR` + `HYPERLEX_VECTOR_BACKEND` (local only; Cloud promote stays explicit)
- Vector/Chroma: `get_vector_store(backend="chroma", path=...)` no longer TypeErrors (`seed_all` always passed `path`)
- Chroma local PersistentClient via `--db` / `HYPERLEX_CHROMA_PATH` (cloud credentials still supported)
- Installer removes leftover destination `.git` so Hermes skill installs are not nested half-repos
- Tests: ephemeral + local persistent Chroma seed/search smoke
- **Promote path:** `vector-export` / `vector-import` / `vector-sync` copy embeddings as-is (local chroma → Cloud without re-embed)
- `force_cloud=True` ignores `HYPERLEX_CHROMA_PATH` so promote does not write back to local by mistake
- CLI auto-loads `~/.hermes/.env` (and `~/.hyperlex/.env`); accepts official `CHROMA_API_KEY` / `CHROMA_TENANT` / `CHROMA_DATABASE` aliases
- Cloud client only requires API key; tenant/database optional when Chroma can infer them

## 0.4.0 — Automatic backend pipeline (2026-08-05)

- `run_pipeline` / CLI `pipeline`: ingest → analyze → receipt → forecasts → score log → Phase 5 risk
- `ingest` and `run` default to the full auto path (`ingest --raw-only` for signal-only)
- Multi-term bags auto-expand to one full result unit per lexicon atom
- Never auto-settles; `brier` always null until operator `settle`
- Package API: `run_pipeline`, `run_one`

## 0.3.9 — Atomic multi-term seeds (2026-08-05)

- `split_seed_terms`: longest-match lexicon split (`sigma rizz locked in` → sigma | rizz | locked in)
- Analyze attaches `seed_terms` + `per_term` lineage; primary lineage is best single atom (no density stack)
- Phase 5 auto-expands multi-term seeds → `hyperlex.phase5_multi_term.v1` (use `--no-expand` to blend)
- CLI: `terms-split`; docs/backfill README clarify atomic pack entries
- Scan/cron defaults use atomic queries; risk-schedule expands seed bags into atoms
- Phase 5 archive snapshots re-exported multi-term; examples/docs scrubbed of blended seeds

## 0.3.8 — Operator loop docs + simplified ingest routing (2026-08-05)

- Canonical ingest catalog: `hyperlex.intake.sources` (`resolve_source`, `pick_source`, `ROUTE_PRESETS`)
- Prefer `--route offline|live|glossary|social` over raw adapter names (aliases: real→glossary, x→x_search, …)
- CLI: `run` one-shot path, `commands` map, `pending` open forecasts; positional query on `analyze`/`run`
- Structured ingest always on the analyze path; `sources` shows routes + resolve preview
- Docs: `docs/operator-loop.md`, `docs/commands.md`; ingest module rewrite
- Recommendation: burn-in with offline cron + settle before ANN or more Phase 5 surface

## 0.3.7 — Risk-tier → scan/cron schedule coupling (2026-08-05)

- `hyperlex.simulation.schedule`: `TIER_POLICY`, `plan_scan_from_risk/term/tier`, `write_scan_plan`, `aggregate_scan_risk`
- CLI: `risk-schedule` + `simulate --mode schedule` (advisory Hermes job envelopes; no auto-register)
- `scan` summaries include `scan_risk_advisory` (lineage coverage → next cadence)
- Examples: `examples/cron/risk-tier-elevated.job.json`, `examples/cron/README.md`
- Docs: cron-live-emergence, phase5, modules/simulation

## 0.3.6 — Transmission calibration, scenario library, research export (2026-08-05)

- `calibrate_transmission_params` grid-search β/γ against settled pairs (SPECULATIVE)
- Multi-agent scenario library + `compare_scenarios` presets
- `export_research_packet` paper-ready JSON/Markdown
- CLI: `simulate --mode calibrate|compare|export`

## 0.3.5 — Hybrid lineage re-rank + domain phylogeny packs (2026-08-05)

- `match_lineage` hybrid: lexical confidence + capped vector family boost
- Domain packs under `data/phylogeny/` (finance, ai-native, political, regional)
- `build_domain_phylogeny` / `list_domain_packs`; CLI `simulate --mode phylogeny --domain …`

## 0.3.4 — Vector neighbors on analyze + receipt auto-index (2026-08-05)

- `detect_memetic_patterns` attaches `analysis.vector_neighbors` when local DB present (`HYPERLEX_VECTOR=auto|1`)
- `emit_receipt` fail-open indexes into `~/.hyperlex/vector.db`
- ROADMAP: vector DB marked complete; hybrid lineage re-rank listed under 5.1

## 0.3.3 — Local SQLite vector DB (2026-08-05)

- `hyperlex.vectordb`: SQLite store at `~/.hyperlex/vector.db`
- Default offline hash embeddings (`hyperlex.hash_ngram_v1.d256`); optional openai_compatible
- Seed from LINEAGE_REGISTRY + `data/backfill/2026` + receipts
- CLI: `vector-seed`, `vector-search`, `vector-stats`
- Docs: `docs/modules/vectordb.md`

## 0.3.2 — Hallmark redesign: Pages workbench identity (2026-08-05)

- Custom docs identity: IBM Plex + phosphor-teal tokens (`docs/stylesheets/extra.css`)
- Workbench home: status strip, desk cards (history / install / simulate / status)
- STATUS published on site (`docs/status.md`); Run history elevated in nav
- Archive family stats from receipt summaries (not ledger-only)
- Catalog uses Material card grid for each run snapshot

## 0.3.1 — Pages as static history of runs (2026-08-05)

- `export_run_history` writes dated snapshots under `docs/archive/runs/<id>/`
- Auto-refresh `docs/archive/latest/` + `catalog.json` + history `index.md`
- CLI: `archive-export --history`, `--phase5`, `archive-catalog`
- Phase 5 scenarios can be appended as publish-safe digests (not full agent dumps)
- Docs/MkDocs: Run history catalog nav; Pages role clarified (static, not live store)

## 0.3.0 — Phase 5.0 research simulation track (2026-08-05)

- **Phase 5.0** package `hyperlex.simulation`:
  - cultural transmission cascade (`simulate_cultural_transmission`)
  - multi-agent memetic roles (`run_multi_agent_memetics`)
  - hyperstition risk forecast (`forecast_hyperstition_risk`, `risk_from_analysis`)
  - phylogeny scaffold (`build_family_phylogeny`)
  - composed scenario (`run_phase5_scenario`)
- CLI: `simulate` (`--mode scenario|transmission|agents|risk|phylogeny`, `--from-analyze`)
- Docs: `docs/phase5.md`, `docs/modules/simulation.md`; ROADMAP/STATUS/SPEC/README refresh
- All Phase 5 outputs **SPECULATIVE**; `brier` always null; no receipt mutation
- API: symbols on `API_EXTENDED` (frozen `API_V1` unchanged)

## 0.2.12 — YTD 2026 slang backfill + lineage backpropagation (2026-08-05)

- Curated monthly packs: `data/backfill/2026/` (Jan–Aug) with OBSERVED/INFERRED terms.
- `hyperlex.analysis.backfill` — load, inventory, merge packs into registry overlay.
- `hyperlex.analysis.backprop` — non-mutating rematch of historical receipts; reclassification report only.
- CLI: `lineage-backfill`, `lineage-backprop` (scripts + package entry).
- `LINEAGE_REGISTRY` expanded with 2026 brainrot/AI leaves (`rizz`, `locked in`, `crash out`, `vibe coding`, …).
- `match_lineage(..., registry=)` accepts overlay for backprop without global mutation.
- Integrity rule: never rewrite historical receipt hashes; Brier still null until settlement.
- Docs: `data/backfill/2026/README.md`; slang-lineages backfill section.

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
