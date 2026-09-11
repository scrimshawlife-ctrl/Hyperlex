# Hyperlex Roadmap

## Vision
Hyperlex **ships today as a Hermes skill** (this Python package). Relevant Abraxas wire capabilities live under `hyperlex.compat.abraxas`; hosts import *from* Hyperlex.

The same project is on a **model path** (Spec 007): T0 encoder baseline, then T1 after eval gate E2. T1 is the first artifact that may be called Hyperlexical. Until E2 passes on Spark, `name_gate` is false and there is no Hub card.

The skill remains the operator surface while the encoder stays SHADOW.

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
- [x] **5.x** Chroma local + Cloud backend; `vector-export` / `import` / `sync` promote path
- [x] **5.x** Fail-open vector auto-index on ingest/pipeline/receipt (local sqlite/chroma)
- [ ] **5.x+** Optional post-ingest Cloud promote (`HYPERLEX_VECTOR_PROMOTE`) — off by default
- [ ] **5.3** ANN backend option if corpus grows past linear scan (**deferred** until corpus pain)

### Spec 007 — Hyperlexical encoder (SHADOW · 2026-09-10)
- [x] Specify C1–C52 + A5 milestones / engineering (#33)
- [x] U1 stub infer + packet walls
- [x] U2 civilian harvest exporter
- [x] U3 eval harness vs Spec 004
- [x] Keepable layout + span aligner + HF skeleton
- [x] Live-split coerce to lexical train/val/test (#38)
- [x] 8-family leaf unlock; classify volume ready (harvest receipt 2026-09-10)
- [x] Spark bring-up runbooks on main (#28)
- [ ] E2 pass (Spark-blocked; stub expected fail; seed smoke is not a pass)
- [ ] Hub upload (operator — not started)
- [ ] T13 promote into `src/hyperlex/`

`name_gate` stays **false** until E2 passes on Spark. Classify volume ≠ a Hyperlexical name. No ninth family.

## Milestones
- v0.2.x: Phases 0–4 complete (Hermes skill production track)
- v0.3.0: Phase 5.0 research simulation track
- v0.3.6: calibrate + scenario library + research export
- v0.3.7: risk-tier → scan/cron schedule coupling
- v0.3.8: operator loop + ingest route simplification
- v0.3.9: atomic multi-term seeds + Pages demos
- **v0.4.0: automatic backend pipeline (ingest → results)** (current)
- v0.3.x: Phylogeny libraries + vector hybrid lineage + research export polish
- v1.0: Stable skill contract + long-horizon archive + optional research contribs
- 007: `hyperlex-structure-149m` name only after E2

See [SPEC.md](spec.md) and [DESIGN.md](design.md) for the historical spine. Current operator snapshot: [STATUS.md](status.md).

## Recent
- 2026-09-10 PT evening: Spec 007 SoT 4333 / `--include-live` classify 2437; Danny ~2500 bar met; `name_gate` false; E2 Spark-blocked. Hermes 913 / gap-to-2500 superseded. Spark bring-up (#28), A5 milestones (#33), lexical-split coerce (#38), 8-family unlock (#37).
- 2026-09-09: Spec 007 SHADOW encoder harness on main (not a Hub card)
- v0.4.0: automatic backend pipeline (ingest → results)
- v0.3.9: Atomic multi-term seeds; Pages demos; scan packs atomic
- v0.3.8: Operator loop docs; `--route` ingest; `run` / `commands` / `pending`
- v0.3.7: Risk-tier → scan/cron schedule (advisory; post-scan advisory on scan)
- v0.3.5: Hybrid lineage re-rank + domain phylogeny packs
- v0.3.3: Local SQLite vector DB; seed from registry/backfill/receipts
- v0.3.0: Phase 5.0 simulation stack (transmission, agents, risk, phylogeny)
- v0.2.12: YTD backfill + lineage backprop
