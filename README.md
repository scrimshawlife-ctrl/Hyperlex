# Hyperlex

**Hyperlex** (Hyper + Lexicon) is a standalone, evidence-bound engine for **slang emergence**, **memetic pattern detection**, **hyperstition tracking**, and **symbolic forecasting**.

It analyzes real cultural signals (especially betting/community slang) to surface neologisms, virality, semantic shifts, memetic structures, and hyperstition loops (fictions that become self-fulfilling).

This repository contains the **official design specifications, roadmaps, architecture, and reference material** for Hyperlex. The implementation lives separately (see the Hyperlex engine package).

## Core Philosophy
- **Pure real-data only** (no synthetic)
- Strict, provenance-rich JSON output
- Modular, arXiv-grounded analysis
- Decoupled & installable as a Python package (`pip install -e .`)
- Designed for integration with Hermes/Abraxas symbolic systems, market signals, and forecasting pipelines

## Quick Links
- **Roadmap**: [ROADMAP.md](./ROADMAP.md)
- **Architecture**: [ARCHITECTURE.md](./ARCHITECTURE.md)
- **Design Principles**: [DESIGN.md](./DESIGN.md)
- **Technical Specification**: [SPEC.md](./SPEC.md)
- **Examples**: [examples/](./examples/)
- **References**: [references/](./references/)

## Key Capabilities (v1.5+)
- Wired real ingest (glossary + Reddit + X/firecrawl stubs)
- Neologism detection pipeline
- Semantic variation tracing
- Hybrid virality scoring (velocity + acceleration)
- Memetics protocol checks
- Hyperstition loop simulation
- External signal integration (`virality_boost`, `hyperstition_risk`, `confidence`, `actionable`)
- Canonical receipt emission with integrity hashes
- Brier 0.89 baseline + full provenance

## Core API (Implementation Reference)
```python
import hyperlex

# Real wired analysis
result = hyperlex.detect_memetic_patterns(
    query="sharp money revenge narrative",
    ingest_source="real"
)

# Feed into downstream pipelines
signal = hyperlex.mock_integrate_with_external_signal(result)

# Emit strict receipt
path = hyperlex.emit_receipt(result)
print(path)
```

## License
See [LICENSE](./LICENSE).

## Contributing
See [CONTRIBUTING.md](./CONTRIBUTING.md).