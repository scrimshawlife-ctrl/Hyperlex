# Hyperlex design (Orchestra-aligned)

!!! warning "Historical"
    This page is an **Orchestra-era design note**. It is not the current
    operator contract. Prefer [Design principles](design.md), [Architecture](architecture.md),
    and [Status](status.md). Version target "2.0" below was never a shipping
    Hyperlex release.

**Status**: Historical design surface  
**Hosts**: Hermes, OpenClaw

## Intent
Hyperlex provides **governed memetic signal detection** that can be orchestrated using traditional symbolic maps. It surfaces real emerging slang and hyperstition loops as first-class, provenance-rich signals for Abraxas symbolic intelligence.

## Core Contracts (inspired by Orchestra)
1. **Real-data only** — No synthetic signals in production paths. Provenance always records source.
2. **Dual nature** — Mechanical analysis (scores, JSON) + symbolic correspondence (Numogram loci, Chaos currents).
3. **Fail closed on weak signals** — Low confidence or unknown sources are explicitly marked.
4. **Provenance-first** — Every output carries canonical hash + arXiv lineage.
5. **Composable** — Analysis blocks and ingest are independent so they can be wired by Orchestra or Hermes runes.
6. **Agent posture** — Smallest working layer. Do not invent signals. Receipts are the canonical artifact.

## Key Modules & Symbolic Correspondences (proposed)
- Ingest → Intake / "Choronzon" gate (chaos entry)
- Neologism → Generation locus (Numogram 9)
- Virality → Acceleration current (Numogram 5-6)
- Hyperstition → Self-fulfilling loop (Chaos Magic, Enochian transmission)
- Receipt → Record / Archive (Tree of Life Malkuth)

See `references/` for mappings.

## Integration with Abraxas-Orchestra
Hyperlex is intended to be used as:
- A **signal-forager** component (see `examples/memetic-forager-skeleton`)
- An analysis module that Orchestra can diagram and optimize
- A source of memetic data for larger symbolic architectures

## Executable Surface (current)
- Package API + CLI
- `emit_receipt`
- Real ingest
- External signal mock

Future: full `analyze → map → optimize` pipeline when used inside Orchestra.

## Related Documents
- [Roadmap](ROADMAP.md)
- [Technical spec](spec.md)
- [Architecture](architecture.md)
- [Agent posture](https://github.com/scrimshawlife-ctrl/Hyperlex/blob/main/references/agent-posture.md)