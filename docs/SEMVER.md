# Semantic Versioning for Hyperlex

We follow SemVer 2.0 with these additions:

- **MAJOR (1.0+)**: Breaking changes to `API_V1` or core JSON schemas without deprecation.
- **MINOR (0.x)**: New modules, CLI commands, extended API symbols (backward compatible).  
  Example: **0.3.0** = Phase 5.0 simulation track (additive).
- **PATCH**: Bug fixes, docs, data packs, golden corpus expansion.

Rules:

- `hyperlex.API_V1` is frozen for the 0.2–0.3 series (no remove/rename).
- `API_EXTENDED` may grow freely within a minor line.
- Phase 5 research packets always keep `brier: null`.
- All releases update `VERSION`, `CHANGELOG.md`, `SKILL.md`, `hyperlex.manifest.yaml` in lockstep.

| Line | Meaning |
|------|---------|
| 0.2.x | Phases 0–4 production Hermes skill |
| 0.3.x | Phase 5 research simulation (+ prior surface) |
| 1.0.0 | Stable skill contract + long-horizon archive (future) |