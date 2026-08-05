# Hyperlex Roadmap

## Vision
Hyperlex is a **standalone app**. Relevant Abraxas wire capabilities ship as Hyperlex modules (`hyperlex.compat.abraxas`); hosts import *from* Hyperlex.

Hyperlex evolves into the canonical engine for detecting, scoring, and acting on emerging memetic signals in real time — grounded in real data, arXiv research, and strict provenance.

## Phases

### Phase 0 — Foundation (Complete)
- Standalone Python package (`hyperlex`)
- Core modules: neologism, semantic variation, virality, memetics, hyperstition
- Real ingest (Action Network glossary + Reddit)
- Strict JSON + receipt system
- External signal integration stub
- arXiv distillation applied

### Phase 1 — Robust Ingest & Provenance (Current Focus)
- [x] X/Twitter ingest (API bearer / xurl / structured stub)
- [x] Firecrawl / crawl4ai web scrape adapters (graceful fallback)
- [x] Glossary expansion (`glossary_expanded` multi-source pack)
- [x] Persistent cache + rate limiting (`~/.hyperlex/cache/`, rate_limit.json)
- [x] Enhanced provenance fingerprints (`source_fingerprint`, content_hash, locator)
- [x] Receipt ledger (append-only, hash-chained) — `~/.hyperlex/receipt_ledger.jsonl`

### Phase 2 — Advanced Analysis & Calibration
- [x] Golden settled series fixture + tests (`examples/calibration/settled_series.v1.json`)
- [x] Brier score calculation layer (atomic, series, BSS, Murphy, Yates)
- [x] Forecast extraction + settlement models (`hyperlex.calibration`)
- [x] Remove decorative `provenance.brier` from open analysis results
- [ ] Improved neologism pipeline (LLM + rules hybrid)
- [ ] Community driver modeling (from arXiv semantic variation papers)
- [ ] Virality prediction models
- [ ] Memetic typology expansion
- [x] Slang historical family documentation + emergent branch diagrams (Mermaid)
- [x] Schema support for lineage attachment on analysis results (`lineage.v1.schema.json`)
- [x] Deterministic lineage matcher with confidence scoring
- [ ] Automated diagram generation from receipt histories
- [x] Operator settlement workflow + score log persistence (`settle_and_log`, `~/.hyperlex/score_log.jsonl`)
- [x] CLI: `analyze --forecasts`, `extract-forecasts`, `settle`, `score-series`, `verify-score-log`
- [x] Golden tests for lineage confidence, score_pair, score_series (empty → NOT_COMPUTABLE), score log
- [x] Optional Abraxas-compatible `BrierLedgerEntry.v1` export (no Abraxas import)
- [x] Advisory mean-shift recalibration diagnostic (`mean_shift_from_series`)

### Phase 3 — Hermes / Symbolic Integration
- [x] Hermes skill packaging (`SKILL.md`, `install.sh` → `~/.hermes/skills/hyperlex`)
- [x] Native skill install path + post-install check/smoke
- [x] Rune / signal relay (`hyperlex.relay`, RUNE.HLX.*)
- [x] Hyperstition loop feedback into forecasting systems (`connectors.hyperstition_feedback`)
- [x] Market-signal and forecast pipeline connectors (`connectors.market_signal`)
- [x] Cron / autonomous monitoring (`scan` + `examples/cron/live-emergence-scan.job.json`)

### Phase 4 — Production & Ecosystem
- [x] Local/Hermes packaging (`pip install -e .` / skill install) — **no public PyPI publish planned**
- [x] Golden receipt corpus (`examples/receipts/golden/`) + API v1 freeze
- [ ] Broader test corpus / CI expansion
- [ ] Documentation site / MkDocs
- [ ] Example notebooks and case studies
- [x] Public API v1 freeze (`docs/api-v1.md`, `hyperlex.API_V1`)
- [ ] Optional LLM augmentation layer (governed)
- [ ] Cross-domain expansion (beyond betting slang)

### Long-term (Phase 5+)
- Cultural transmission simulation
- Multi-agent memetic modeling
- Hyperstition risk forecasting for real-world systems
- Open research contributions back to memetics community
- Full phylogenetic libraries across domains (finance, AI-native, political, regional)

## Milestones
- v1.5: Current package + receipt system (done)
- v2.0: Strong real-time ingest + Phase 2 analysis
- v2.5: Full Hermes integration
- v3.0: Public release + ecosystem

See SPEC.md and DESIGN.md for detailed requirements per phase.

## Recent Additions (2026-08-05)
- Lineage system (docs, diagrams, matcher, confidence scoring)
- **Brier / calibration design** (`docs/brier-calibration.md`)
- `src/hyperlex/calibration/` — extract_forecasts, settle, score_pair, score_series, Murphy/Yates/BSS
- Schemas: `forecast.v1`, `settlement.v1`, `brier_series.v1`
- DESIGN principle 12: Brier requires settlement
