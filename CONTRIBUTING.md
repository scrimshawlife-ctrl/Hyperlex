# Contribute to Hyperlex

Hyperlex **ships as a Hermes skill** plus this Python package. Spec 007 is the model path (T0 → T1 after E2), still SHADOW. You can change specs, the engine, docs, or operator receipts. Keep claims evidence-bound.

Read [STATUS.md](STATUS.md) before you write a feature sentence. If STATUS says a gate is false, do not flip it in prose.

## Before you start

- Python 3.10, 3.11, or 3.12
- No API keys for the offline path
- Docs style: [Google developer documentation style](https://developers.google.com/style) — second person, active voice, sentence-case headings, descriptive link text

## Run tests

From the repo root:

```bash
python3 -m pip install -U pip pytest jsonschema
export HYPERLEX_OFFLINE=1
export HYPERLEX_NO_RATE_LIMIT=1
export PYTHONPATH=src

python3 scripts/hyperlex.py check
python3 scripts/hyperlex.py doctor
python3 scripts/hyperlex.py smoke
python3 -m pytest -q
```

That matches [`.github/workflows/hermes-evals.yml`](.github/workflows/hermes-evals.yml). Shadow 007 tests live under `tests/shadow/` and run in the same pytest invocation.

Skill-only smoke from a checkout (no install):

```bash
python3 scripts/hyperlex.py demo
```

Expect `ok: true` and `brier: null`.

## Serve and build docs

```bash
python3 -m pip install -e ".[docs]"
python3 scripts/sync_mkdocs_pages.py
mkdocs serve
```

CI copies root snapshots into `docs/` then builds strict:

```bash
cp ARCHITECTURE.md docs/architecture.md
cp DESIGN.md docs/design.md
cp SPEC.md docs/spec.md
cp STATUS.md docs/status.md
cp ROADMAP.md docs/ROADMAP.md
cp CONTRIBUTING.md docs/contributing.md
python3 scripts/sync_mkdocs_pages.py
mkdocs build --strict
```

Published site: https://scrimshawlife-ctrl.github.io/Hyperlex/

## Pull request expectations

1. Open an issue first for behavior or spec changes that are not obvious fixes.
2. Keep PRs small. Prefer tests or receipts when behavior changes.
3. Update [STATUS.md](STATUS.md) and [ROADMAP.md](ROADMAP.md) only when a gate actually moved.
4. Link the relevant spec (`specs/00N-…`) or roadmap row.
5. Docs and PR text follow Google developer style. Keep the Hyperlex voice where it already lives; do not invent swagger or features.

### Do not

- Invent a numeric Brier on open analysis. Empty series → `NOT_COMPUTABLE`.
- Auto-settle forecasts. Settlement is a human step (`TRUE` / `FALSE` / `VOID` / `CONFLICT`).
- Add a **ninth** lineage family.
- Claim Hub publish, `name_gate: true`, or the name **Hyperlexical** (E2 on Spark has not passed).
- Rewrite historical receipt hashes.
- Treat Phase 5 or Spec 007 packets as measurement.

## Where truth lives

| File | Role |
|------|------|
| [SKILL.md](https://github.com/scrimshawlife-ctrl/Hyperlex/blob/main/SKILL.md) | Hermes / Claude behavior contract |
| [STATUS.md](STATUS.md) | Operator snapshot (copied to the docs site) |
| [ROADMAP.md](ROADMAP.md) | Phase and 007 checklist (copied to the docs site) |
| [Docs site](https://scrimshawlife-ctrl.github.io/Hyperlex/) | Operator-facing MkDocs |
| [specs/](https://github.com/scrimshawlife-ctrl/Hyperlex/tree/main/specs) | Spec kit (000–007). 006 stays reserved. |
| [ARCHITECTURE.md](ARCHITECTURE.md), [DESIGN.md](DESIGN.md), [SPEC.md](SPEC.md) | Historical spines. Prefer the docs site for navigation. |

## Style for requirements

Use MUST / SHOULD / MAY in specs. Label claims OBSERVED / INFERRED / SPECULATIVE. Cite arXiv or attested sources when you add methodology.
