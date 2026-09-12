# Hyperlex documentation

**Naming:** repo **Hyperlex** is the transitional monorepo shell. Public products: **Hyperlexical** (Spec 007 model) and **ne0l0gist** (slang ingest). See the [README Naming](https://github.com/scrimshawlife-ctrl/Hyperlex/blob/main/README.md#naming) section.

Published with **MkDocs** (`mkdocs.yml` at the repo root).

```bash
pip install -e ".[docs]"
python3 scripts/sync_mkdocs_pages.py
mkdocs serve
```

CI copies `ARCHITECTURE.md`, `DESIGN.md`, `SPEC.md`, `STATUS.md`, `ROADMAP.md`, and `CONTRIBUTING.md` into `docs/`, then runs `mkdocs build --strict`.

Hyperlex **ships as a Hermes skill** (Python package repo). Spec 007 is the model path (T0 → T1 after E2), still SHADOW. Relevant Abraxas wire shapes live in `hyperlex.compat.abraxas` (no Abraxas import).

## Information architecture

| Section | Purpose |
|---------|---------|
| [Start](start/index.md) | First success, glossary, contribute |
| [Concepts](architecture.md) | Architecture, lineages, Phase 5, modules |
| [Operator](commands.md) | Daily commands, Hermes, Claude |
| [Specs](specs/index.md) | Spec kit + SHADOW 007 + status/roadmap |
| [Archive](archive/index.md) | Run history and historical pages |

## Root files (do not delete)

These stay in git as history. Prefer the site for navigation.

| Root file | Docs copy / pointer |
|-----------|---------------------|
| `README.md` | GitHub front door (not this file) |
| `STATUS.md` | [status.md](status.md) (CI copy) |
| `ROADMAP.md` | [ROADMAP.md](ROADMAP.md) (CI copy) |
| `CONTRIBUTING.md` | [contributing.md](contributing.md) (CI copy) |
| `QUICKSTART.md` | [start/quickstart.md](start/quickstart.md) |
| `ARCHITECTURE.md` | [architecture.md](architecture.md) |
| `DESIGN.md` | [design.md](design.md) |
| `SPEC.md` | [spec.md](spec.md) (v0.3 spine) |
| `SKILL.md` | Hermes contract (not on Pages) |

## Examples

- `examples/slang-families/` — Mermaid family trees
- `examples/calibration/settled_series.v1.json` — golden Brier pairs
- `examples/receipts/golden/` — golden receipt corpus
- `examples/cron/` — Hermes cron templates

## References (repo, not Pages)

- [arXiv papers](https://github.com/scrimshawlife-ctrl/Hyperlex/blob/main/references/arxiv_papers.md)
- [Hermes runtime contract](https://github.com/scrimshawlife-ctrl/Hyperlex/blob/main/references/hermes-runtime-contract.md)
- [Claude Code runtime contract](claude-runtime-contract.md)
