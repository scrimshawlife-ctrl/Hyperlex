# Hyperlex Roadmap

## Vision
Hyperlex is a **Hermes skill** backed by this Python package repo. Relevant Abraxas wire capabilities ship as Hyperlex modules (`hyperlex.compat.abraxas`); hosts import *from* Hyperlex.

Hyperlex evolves into the canonical engine for detecting, scoring, and acting on emerging memetic signals in real time — grounded in real data, arXiv research, and strict provenance.

## Phases

### Phase 0 — Foundation (Complete)
- Standalone Python package (`hyperlex`)
- Core modules: neologism, semantic variation, virality, memetics, hyperstition
- Real ingest (Action Network glossary + Reddit)
- Strict JSON + receipt system
- External signal integration stub
- arXiv distillation applied

### Phase 1 — Robust Ingest & Provenance (Complete)
- [x] X/Twitter ingest (API bearer / xurl / structured stub)
- [x] Firecrawl / crawl4ai web scrape adapters (graceful fallback)
- [x] Glossary expansion (`glossary_expanded` multi-source pack)
- [x] Persistent cache + rate limiting (`~/.hyperlex/cache/`, rate_limit.json)
- [x] Enhanced provenance fingerprints (`source_fingerprint`, content_hash, locator)
- [x] Receipt ledger (append-only, hash-chained) — `~/.hyperlex/receipt_ledger.jsonl`

### Phase 2 — Advanced Analysis & Calibration (Complete)
- [x] Golden settled series fixture + tests
- [x] Brier score calculation layer (atomic, series, BSS, Murphy, Yates)
- [x] Forecast extraction + settlement models (`hyperlex.calibration`)
- [x] Remove decorative `provenance.brier` from open analysis results
- [x] Neologism rules + community drivers + virality prediction v0
- [x] Memetic typology expansion; slang lineage docs + matcher + confidence
- [x] Automated diagrams from receipt histories
- [x] Operator settlement + score log; Abraxas-compatible ledger export
- [x] Advisory mean-shift recalibration
- [x] YTD slang backfill packs + lineage backpropagation (non-mutating)

### Phase 3 — Hermes / Symbolic Integration (Complete)
- [x] Hermes skill packaging (`SKILL.md`, `install.sh`)
- [x] Rune / signal relay (`RUNE.HLX.*`)
- [x] Hyperstition feedback + market-signal connectors
- [x] Cron / autonomous monitoring (`scan`)

### Phase 4 — Production & Ecosystem (Complete)
- [x] Local/Hermes packaging — **no public PyPI publish planned**
- [x] Golden receipt corpus + API v1 freeze
- [x] CI + MkDocs / GitHub Pages
- [x] Case studies; governed LLM (opt-in); cross-domain lineages
- [x] Long-term analysis archive (`archive-export` → docs/archive)

### Phase 5 — Research simulation (Current focus · v0.3.0+)
- [x] **5.0** Cultural transmission simulation (`hyperlex.simulation.transmission`)
- [x] **5.0** Multi-agent memetic modeling (`hyperlex.simulation.agents`)
- [x] **5.0** Hyperstition risk forecasting for real-world systems (`hyperlex.simulation.risk`)
- [x] **5.0** Phylogeny scaffold from registry + backfill timeline
- [x] **5.0** Composed scenario runner + CLI `simulate`
- [x] **5.0** Docs: `docs/phase5.md`, `docs/modules/simulation.md`
- [x] **5.0** Local SQLite vector DB (`hyperlex.vectordb`, `vector-seed` / `vector-search`)
- [x] **5.0** Analyze attaches `vector_neighbors` when DB present; receipts auto-index (fail-open)
- [x] **5.1** Domain-specific phylogeny packs (`data/phylogeny/`: finance, ai-native, political, regional)
- [x] **5.1** Transmission parameter calibration against settled series (still no invented Brier)
- [x] **5.1** Vector hybrid re-rank for lineage matcher (`match_lineage` + local vector DB)
- [x] **5.2** Multi-agent scenario library + comparative runs (`compare_scenarios`)
- [x] **5.2** Open research export templates (`export_research_packet`)
- [x] **5.3** Risk tiers → scan schedules / operator alerts (advisory Hermes cron envelopes)
- [x] **5.3** Operator loop docs + simplified ingest routes / command map (`run`, `commands`, `pending`)
- [x] **5.3** Atomic multi-term seeds (`split_seed_terms`, Phase 5 multi-term, Pages demos)
- [ ] **5.3** ANN backend option if corpus grows past linear scan (**deferred** until corpus pain)

## Milestones
- v0.2.x: Phases 0–4 complete (Hermes skill production track)
- v0.3.0: Phase 5.0 research simulation track
- v0.3.6: calibrate + scenario library + research export
- v0.3.7: risk-tier → scan/cron schedule coupling
- v0.3.8: operator loop + ingest route simplification
- **v0.3.9: atomic multi-term seeds + Pages demos** (current)
- v0.3.x: Phylogeny libraries + vector hybrid lineage + research export polish
- v1.0: Stable skill contract + long-horizon archive + optional research contribs

See SPEC.md and DESIGN.md for detailed requirements per phase.

## Recent (2026-08-05)
- v0.2.12: YTD backfill + lineage backprop
- v0.3.0: Phase 5.0 simulation stack (transmission, agents, risk, phylogeny)
- v0.3.3: Local SQLite vector DB; seed from registry/backfill/receipts
- v0.3.5: Hybrid lineage re-rank + domain phylogeny packs
- v0.3.7: Risk-tier → scan/cron schedule (advisory; post-scan advisory on scan)
- v0.3.8: Operator loop docs; `--route` ingest; `run` / `commands` / `pending`
- v0.3.9: Atomic multi-term seeds; Pages demos; scan packs atomic
