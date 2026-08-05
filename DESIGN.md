# Hyperlex Design Principles

## 1. Real Over Synthetic
All analysis must be traceable to real signals. Synthetic data is only for internal unit tests and explicitly marked.

## 2. Provenance is Sacred
Every output carries:
- canonical_hash
- timestamp
- version
- ingest_source
- arxiv_concepts_applied
- integrity receipt hash

## 3. ArXiv-Grounded
Core algorithms distilled from:
- Neologism pipeline (2605.06426)
- Semantic variation drivers (2210.08635)
- Virality/diffusion (2510.05761)
- Memetics protocol (2407.11861)
- Hyperstition loops (2410.23794)
- Cultural transmission (2203.00715)

## 4. Strict Interfaces
Public API is minimal and stable:
- ingest_signal(query, source)
- detect_memetic_patterns(...)
- mock_integrate_with_external_signal(result)
- emit_receipt(result)
- extract_forecasts / settle / score_series (calibration)
- Helper scorers

## 5. Modularity for Integration
Analysis blocks are independent so they can be:
- Used standalone
- Wired into larger Hermes runes
- Fed into forecasting or market-signal systems
- Composed in different orders

## 6. Humanizer Layer
Light post-processing to remove AI-isms while preserving sharp signal.

## 7. Receipt-Centric Workflow
The `emit_receipt` pattern ensures every serious run produces an auditable artifact. Receipts are the primary output for serious use.

## 8. Hermes Skill + Modular Host Compat
Hyperlex is a **Hermes skill** implemented in this Python package repository.
It has no hard dependency on Hollersports, Abraxas, Orchestra, or any domain host.
Betting slang is the initial validation domain.

**Relevant Abraxas capabilities** (Brier ledger/score packets, claim labels,
operator review, HLX rune envelopes) are implemented as Hyperlex modules under
`hyperlex.compat.abraxas`. Hosts may `import hyperlex.compat.abraxas`; Hyperlex
never imports Abraxas. See `docs/hermes-skill.md`.

## 9. Determinism + Graceful Degradation
- Mock mode is fully deterministic
- Real modes fall back gracefully
- Errors surface explicitly in output

## 10. Evolution via Receipts
Future improvements are validated by comparing receipt lineages and Brier evolution over settled forecast series.

## 11. Lineage as First-Class Structure
Slang is documented and analyzed as historical families with emergent branches rather than flat term lists. Visual diagrams live under `examples/slang-families/` and are described in `docs/slang-lineages.md`. Lineage confidence is the primary continuous signal eligible as a forecast probability.

## 12. Brier Requires Settlement
A Brier score is never emitted from an open analysis run. Analysis may emit forecast probabilities (via `extract_forecasts`). Only after a settlement records an outcome may `score_pair` / `score_series` compute atomic BS, series BS, BSS, Murphy, and Yates decompositions. Missing outcomes yield `NOT_COMPUTABLE`, never a fabricated float. See `docs/brier-calibration.md`.

## 13. Phase 5 Simulation Is Speculative Research
Cultural transmission, multi-agent memetics, hyperstition risk, and phylogeny scaffolds are **research tooling**. They:
- always label `provenance: SPECULATIVE` (or INFERRED for structural phylogeny)
- never emit numeric Brier (`brier: null`)
- never rewrite historical receipt integrity
- never auto-settle forecasts

Risk tiers inform operator diligence (scan frequency, archive, settlement criteria) — not automated market action. See `docs/phase5.md`.
