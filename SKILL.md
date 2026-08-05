---
name: hyperlex
description: "Standalone memetic emergence engine for slang detection, hyperstition tracking, virality scoring, and symbolic signal analysis. Wired real ingest + arXiv-grounded modules (neologism, semantic variation, memetics protocol, hyperstition loops). Produces strict provenance-rich JSON receipts. Use when designing or running memetic pattern detection, cultural signal foragers, hyperstition risk analysis, or integrating emerging slang/virality into Hermes/Abraxas forecasting and market-signal pipelines. Decoupled, pip-installable."
version: 1.5.0
license: MIT
metadata:
  openclaw:
    requires:
      bins: [python3]
    os: [darwin, linux]
    emoji: "🌀"
---

# Hyperlex

**Hermes + OpenClaw** memetic signal engine.

Hosts: **Hermes**, **OpenClaw**, standalone Python package.

## Philosophy
Hyperlex is the **memetic forager** — a governed, real-data-only engine that surfaces emerging slang, memetic patterns, and hyperstition loops from live cultural signals. It is designed to feed Abraxas-Orchestra, Hermes runes, and downstream symbolic forecasting systems.

It draws on traditional correspondence systems (Chaos Magic for hyperstition, Numogram for emergence vectors, Peircean signs for signal typology) while remaining strictly evidence-bound.

## Core Commands (Implementation)

```bash
# From installed skill or repo root
python -m hyperlex                    # full demo + receipt emission
python scripts/hyperlex.py analyze    # (future) repo or signal analysis
python scripts/hyperlex.py forager    # real ingest run
```

## Public API (Package)
```python
import hyperlex

result = hyperlex.detect_memetic_patterns(ingest_source="real")
signal = hyperlex.mock_integrate_with_external_signal(result)
receipt_path = hyperlex.emit_receipt(result)
```

## Key Outputs
- Strict JSON with `observed | inferred | speculative`
- `provenance` block (canonical_hash, arxiv_concepts, brier, ingest_source)
- `analysis` blocks: neologisms, semantic_variation, virality (hybrid), memetics, hyperstition
- Receipt with integrity hash

## Integration with Abraxas-Orchestra
Hyperlex modules can be symbolically structured using Orchestra frameworks (e.g., Numogram loci for emergence stages, Enochian for signal transmission).

See `docs/INTEGRATION_WITH_ORCHESTRA.md` (to be added) and references/.

## Install (as Hermes skill)
```bash
# After cloning or via skill manager
bash install.sh
```

See README.md and docs/ for full design surface.
