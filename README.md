# Hyperlex

<p align="center">
  <img src="assets/hyperlex-imagine-hero.jpg" alt="Hyperlex hero — memetic emergence atlas" width="100%" />
</p>

**Memetic emergence** skill + SHADOW encoder path for the Abraxas model stack.
Catch language while it’s still becoming culture — slang lineage, receipts, settled Brier only.

Hermes skill is what you **run today**. Spec 007 Hyperlexical encoder is **SHADOW / advisory**.

| | |
|---|---|
| **Owns** | memetic ingest · classify · receipts · virality / hyperstition signals · Spec 007 encoder specify |
| **Honesty** | `OBSERVED` / `INFERRED` / `SPECULATIVE` (+ provenance; settled Brier only where calibrated) |
| **Shape** | Hermes skill **live** (v0.4.0). Spec 007 T0→T1 **gated**. Not a chatbot mind. |
| **Anti** | Efficacy theater · inventing Brier · naming artifacts **Hyperlexical** before E2 · Hub without `ALLOW_HUB` |
| **Lane** | Skill ready · encoder SHADOW · `name_gate` **false** · Hub not published |
| **Version** | `0.4.0` — prefer [`STATUS.md`](STATUS.md) |

Docs site: [scrimshawlife-ctrl.github.io/Hyperlex](https://scrimshawlife-ctrl.github.io/Hyperlex/) · status mirror: [status](https://scrimshawlife-ctrl.github.io/Hyperlex/status/).

## Naming

Repo **Hyperlex** is the transitional monorepo shell. Do not use bare public **Hyperlex** as a product name — it collides with French legaltech CLM / DiliTrust.

| Name | Role |
|------|------|
| **Hyperlexical** | Spec 007 model / train / eval / E2 / `name_gate` product claim |
| **ne0l0gist** | Slang ingest tool: Crawl4AI harvest, `ingest_tap`, export/settle, civilian and live phrase harvest |
| **Hyperlex** (repo) | Transitional monorepo shell. GitHub repo name, `~/.hyperlex` paths, `HYPERLEX_*` env vars, and the `hyperlexical` Python package stay as-is |

`name_gate` stays **false**. This split does not name a trained artifact Hyperlexical-gated-true.

## What ships / what does not

| Ships now | Does **not** ship |
|-----------|-------------------|
| Hermes skill install + CLI (`install.sh`, `scripts/hyperlex.py`) | Artifact named **Hyperlexical** |
| Spec 007 SHADOW encoder code path | `name_gate` true / Hub publish |
| Local SoT classify volume (operator machine) | Full SoT in git |
| Pages static run history / Phase 5 research hooks | Paid Firecrawl by default (Crawl4AI is default) |

## Current state (OBSERVED 2026-09-10/11 PT)

Snapshot — full scoreboard in [`STATUS.md`](STATUS.md).

| Area | State |
|------|-------|
| Hermes skill | Ready **v0.4.0** |
| Spec 007 | SHADOW on main · T0 specified · T1 blocked on Spark E2 |
| `name_gate` | **false** (volume ≠ name) |
| Hub | Not published |
| Local SoT | `~/.hyperlex/hyperlexical/ingest_candidates.jsonl` — **4333** (**not in git**) |
| Export classify (include-live) | **2437** family-labeled (harvest gate) |
| Tracked seed export | `specs/007-…/exports/civilian.v0.1.jsonl` — seed/snapshot only |
| Scrape default | Crawl4AI **0.9.3** (paid Firecrawl needs Danny yes) |

## Pipeline

```
query + source → intake → analyze → receipt / score log
                              ↓
                    Spec 007 shadow infer (advisory)
                              ↓
              T0 card → T1 only after Spark E2 + name_gate
```

No hard Abraxas import. Compat shapes live under `hyperlex.compat.abraxas` when needed.
See [`ARCHITECTURE.md`](ARCHITECTURE.md) (spine note) and [`docs/shadow-hyperlexical.md`](docs/shadow-hyperlexical.md).

## Specs / model path

| Path | Role |
|------|------|
| Hermes `SKILL.md` | Operator surface |
| Spec 007 | [`specs/007-hyperlexical-model/`](specs/007-hyperlexical-model/) |
| Shadow encoder | `scripts/shadow/hyperlexical/` |
| Aaron Spark handoff | look under `specs/007-…` / STATUS links (train on Spark) |

## Quick links

| Doc | Path |
|-----|------|
| Status | [`STATUS.md`](STATUS.md) |
| Architecture | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| Shadow Hyperlexical | [`docs/shadow-hyperlexical.md`](docs/shadow-hyperlexical.md) |
| Commands | [`docs/commands.md`](docs/commands.md) |
| Brier calibration | [`docs/brier-calibration.md`](docs/brier-calibration.md) |
| Contributing | [`CONTRIBUTING.md`](CONTRIBUTING.md) |
| Changelog | [`CHANGELOG.md`](CHANGELOG.md) |

## Install (Hermes skill)

```bash
bash install.sh
# optional Claude host:
bash install.sh --claude
```

Editable package (dev):

```bash
pip install -e ".[dev]"
python3 scripts/hyperlex.py doctor
python3 scripts/release_preflight.py
python3 scripts/hyperlex.py simulate --term rizz --mode scenario
pytest -q
```

SHADOW infer (advisory):

```bash
PYTHONPATH=scripts/shadow python3 -m hyperlexical.infer --text rizz --offline
```

## Local data

| Layer | Where | In git? |
|-------|-------|---------|
| Operator SoT | `~/.hyperlex/…` | **No** |
| Receipts / score log | `~/.hyperlex/` | **No** |
| Tracked seed export | `specs/007-…/exports/` | Yes (seed only) |

Spark trains from **local SoT** / `export --include-live`, not from the tracked seed alone.

## Fail-closed gates

Do **not** without Danny/operator yes:

- Call an artifact **Hyperlexical** or flip `name_gate`
- Publish to Hub (`ALLOW_HUB`)
- Commit the 4333 SoT into git
- Invent Brier scores (settled calibration only)
- Paid Firecrawl cloud when Crawl4AI works

## Peers

**Hyperlex (form / lexical)** · Athanor (tradition structure) · Semion (sign relation) · Yggdrasil (route classifier) · VIRAL / VERNACULAR (collective seats)

## License

See repo `LICENSE` / package metadata. Corpus and scrape receipts carry their own provenance — do not treat PD-adjacent web text as automatically redistributable.
