# Hyperlex Roadmap

**Canonical copy:** root [`ROADMAP.md`](../ROADMAP.md). This file is kept in
sync for docs-site consumers.

Hyperlex is a **Hermes skill** backed by this Python package repo. Relevant Abraxas
wire capabilities ship as Hyperlex modules under `hyperlex.compat.abraxas` (no Abraxas import).

## Phase 0 — Foundation (Complete)
- Standalone Python package (`hyperlex`)
- Core modules: neologism, semantic variation, virality, memetics, hyperstition
- Real ingest (Action Network glossary + Reddit)
- Strict JSON + receipt system
- arXiv distillation applied

## Phase 1 — Robust Ingest & Provenance (Complete for v0.2)
- [x] X/Twitter ingest (API bearer / xurl / structured stub)
- [x] Firecrawl / crawl4ai adapters
- [x] Glossary expansion (`glossary_expanded`)
- [x] Persistent cache + rate limiting
- [x] Enhanced provenance fingerprints
- [x] Receipt ledger (append-only, hash-chained)

## Phase 2 — Advanced Analysis & Calibration
- [x] Golden settled series + Brier layer (atomic, series, Murphy, Yates, v1.1)
- [x] Forecast extraction + settlement models
- [x] Lineage system (docs, diagrams, matcher, confidence)
- [x] Operator settlement + score log
- [x] Abraxas-compatible modules (`compat.abraxas`: ledger, score packet, review, runes)
- [x] Neologism rules expanded (compounds + formation); LLM hybrid still optional later
- [ ] Community driver modeling
- [x] Virality prediction v0 (`analysis.virality.prediction`, SPECULATIVE)
- [x] Memetic typology expansion (rule table + lineage prior)
- [x] Automated diagram generation from receipt histories (`hyperlex.diagrams`, CLI `diagram`)

## Phase 3 — Hermes / Host Integration
- [x] Hermes skill packaging + install
- [x] Rune / signal relay (`RUNE.HLX.*`)
- [x] Cron / LIVE_EMERGENCE_SCAN
- [x] Hyperstition loop feedback into forecasting systems
- [x] Market-signal / forecast pipeline connectors (generic)

## Phase 4 — Production & Ecosystem
- [x] Local/Hermes packaging — **no public PyPI publish planned**
- [x] Public API v1 freeze (`docs/api-v1.md`, `hyperlex.API_V1`)
- [x] Golden receipt corpus (`examples/receipts/golden/`)
- [ ] Expanded golden corpus + CI coverage
- [x] Documentation site / MkDocs (`mkdocs.yml`, `pip install -e ".[docs]"`)
- [x] Example case studies (`examples/case-studies/`, `scripts/run_case_study.py`)
- [ ] Optional governed LLM layer
- [ ] Cross-domain expansion

## Long-term
- Cultural transmission simulation
- Multi-agent memetic modeling
- Hyperstition risk forecasting
- Full phylogenetic libraries across domains

See root `ROADMAP.md` for the checklist used in active planning.
