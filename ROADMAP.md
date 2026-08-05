# Hyperlex Roadmap

## Vision
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
- [ ] Reliable X/Twitter ingest (via xurl or API)
- [ ] Firecrawl / web scraping for broader signals
- [ ] Glossary expansion (multiple sources)
- [ ] Persistent cache + rate limiting
- [ ] Enhanced provenance (source fingerprints, timestamps)
- [ ] Receipt ledger (append-only, hash-chained)

### Phase 2 — Advanced Analysis & Calibration
- [ ] Integration with real historical calibration data
- [ ] Brier score tracking across runs
- [ ] Improved neologism pipeline (LLM + rules hybrid)
- [ ] Community driver modeling (from arXiv semantic variation papers)
- [ ] Virality prediction models
- [ ] Memetic typology expansion
- [x] Slang historical family documentation + emergent branch diagrams (Mermaid)
- [x] Schema support for lineage attachment on analysis results (`lineage.v1.schema.json`)
- [x] Simple deterministic lineage matcher (`match_lineage`) wired into `detect_memetic_patterns`
- [ ] Automated diagram generation from receipt histories

### Phase 3 — Hermes / Symbolic Integration
- [ ] Native integration points for Hermes Agent
- [ ] Rune / signal relay compatibility
- [ ] Hyperstition loop feedback into forecasting systems
- [ ] Market-signal and forecast pipeline connectors (generic)
- [ ] Cron / autonomous monitoring jobs

### Phase 4 — Production & Ecosystem
- [ ] PyPI publication
- [ ] Comprehensive test suite + golden receipts
- [ ] Documentation site / MkDocs
- [ ] Example notebooks and case studies
- [ ] Public API surface stabilization
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

## Recent Documentation & Code Additions (2026-08-05)
- `docs/slang-lineages.md` — full methodology, mutation operators, template, live-feed process
- `schemas/lineage.v1.schema.json` — attachment schema
- `src/hyperlex/analysis` — `match_lineage()` + automatic attachment under `analysis.lineage`
- `examples/slang-families/` — 8 diagrams + 3 HTML renderers covering:
  - betting-sharp (+ timeline)
  - kinship-address
  - crypto-degen
  - brainrot-aura
  - ai-native
  - political-status
  - emergence process
