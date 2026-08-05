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

## 8. Decoupling
Hyperlex has no hard dependency on Hollersports, Abraxas, or any specific domain. Betting slang is the initial rich domain for validation.

## 9. Determinism + Graceful Degradation
- Mock mode is fully deterministic
- Real modes fall back gracefully
- Errors surface explicitly in output

## 10. Evolution via Receipts
Future improvements are validated by comparing receipt lineages and Brier evolution.