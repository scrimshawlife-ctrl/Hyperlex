<p align="center">
  <img src="assets/hyperlex-hero.jpg" alt="Hyperlex — Memetic Emergence Engine" width="720">
</p>

# Hyperlex

**Hyperlex** is a standalone Hermes skill for memetic emergence analysis.

Version **0.1.0** · Skill name: `hyperlex` · Python ≥ 3.10 · License: MIT

## What this skill does

Hyperlex ingests live or structured cultural signals, analyzes memetic signals
(neologisms, virality, memetics, hyperstition), and emits canonical receipts
with integrity metadata.

## Quick start

```bash
python3 scripts/hyperlex.py check
python3 scripts/hyperlex.py sources
python3 scripts/hyperlex.py ingest "sharp money revenge" --source mock
python3 scripts/hyperlex.py analyze --query "sharp money revenge" --source mock
python3 scripts/hyperlex.py analyze --input out/ingest.json
python3 scripts/hyperlex.py validate out/receipt.json
python3 scripts/hyperlex.py verify-receipt out/receipt.json
```

## Install

```bash
bash install.sh
```

Install supports `--dry-run` and copies the skill to
`${HERMES_SKILL_DIR:-$HOME/.hermes/skills/hyperlex}`.

## Design surface

- [SKILL.md](./SKILL.md) — Hermes/OpenClaw contract
- [SPEC.md](./SPEC.md) — API and runtime contract
- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [ROADMAP.md](./ROADMAP.md)
- [DESIGN.md](./DESIGN.md)
- [docs/slang-lineages.md](./docs/slang-lineages.md) — historical families of slang + emergent branches
- [examples/slang-families/](./examples/slang-families/) — Mermaid family trees and process diagrams
- [schemas/](./schemas/) — canonical schemas (`ingest`, `result`, `receipt`)

## Schemas & ingest

Schema files at repository root:

- `schemas/ingest.v1.schema.json`
- `schemas/result.v1.schema.json`
- `schemas/receipt.v1.schema.json`

Core sources include `mock`, `real`, `reddit`, `urban`, `wikipedia`, `combined`,
`crawl4ai`, and stubs for `x_search`.

## License

MIT (see LICENSE).
