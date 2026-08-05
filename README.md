# Hyperlex

**Hyperlex** — Memetic Emergence Engine

<p align="center">
  <strong>Standalone, real-data, provenance-first engine for slang, hyperstition, and symbolic signal analysis</strong>
</p>

Version **1.6.0** · Skill name: `hyperlex` · Python ≥ 3.10 · License: MIT

---

## What this is (plain English)

**Hyperlex** detects emerging slang and memetic patterns in real cultural signals. It tracks virality and hyperstition loops (fictions that become self-realizing) and outputs strict, auditable JSON receipts.

It is designed to work as a **signal forager** inside Abraxas-Orchestra and Hermes symbolic systems.

It does three things:
1. **Ingest** real signals (glossaries, Reddit, X stubs)
2. **Analyze** using arXiv-grounded modules + symbolic correspondences
3. **Emit** canonical receipts with integrity and provenance

It is **not** a general LLM wrapper. It is evidence-bound and can be orchestrated with traditional symbolic maps (Numogram, Chaos Magic, Enochian transmission).

## How to use (current implementation)

See the package at `~/hyperlex` or the Hyperlex engine repo.

```bash
python -m hyperlex
```

Produces full analysis + receipt.

## Design Surface

This repository is the **authoritative specs and design surface**, modeled directly on the structure and rigor of [Abraxas-Orchestra-Hermes](https://github.com/scrimshawlife-ctrl/Abraxas-Orchestra-Hermes).

- [SKILL.md](./SKILL.md) — Hermes/OpenClaw skill contract
- [ROADMAP.md](./ROADMAP.md) — Phased plan
- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [DESIGN.md](./DESIGN.md) — Principles + symbolic mapping
- [SPEC.md](./SPEC.md) — Exact interfaces and schemas
- `docs/` — Release notes, security, semver, etc.
- `references/` — Chaos magic, Numogram, agent posture, arXiv
- `examples/` — Memetic forager skeleton (Orchestra style)
- `schemas/` — JSON schemas (ingest.v1, result.v1, receipt.v1) — see `schemas/README.md`

## Integration with Abraxas-Orchestra

Hyperlex is intended to be used as a first-class "signal-forager" component.

Future: Use Orchestra to give Hyperlex modules dual mechanical + symbolic names and diagrams.

See `references/` and `examples/memetic-forager-skeleton/`.



## Schemas & Expanded Ingest (v1.6)

Schemas are exported to the repository root:

- `schemas/ingest.v1.schema.json`
- `schemas/result.v1.schema.json`
- `schemas/receipt.v1.schema.json`

See `schemas/README.md` for usage and the expanded ingest sources (urban, wikipedia, combined + structured API).

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) and the Orchestra model of spec-first development.

## License

MIT (see LICENSE).