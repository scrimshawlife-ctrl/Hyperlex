# Run history (static · GitHub Pages)

This directory is the **publish-safe static history of Hyperlex runs** hosted on
[GitHub Pages](https://scrimshawlife-ctrl.github.io/Hyperlex-Hermes-Specs/archive/).

| | |
|--|--|
| Primary store | Local `~/.hyperlex/` (receipts, ledger, score log) |
| Pages role | Sanitized snapshots for long-term browsing / git history |
| Latest | [latest analysis](./latest/index.md) (`golden-seed-0.3.1`) |
| Machine catalog | [`catalog.json`](./catalog.json) |
| Runs on record | **2** |

## All snapshots

| Snapshot | Kind | Receipts | Notes |
|----------|------|--------:|-------|
| [`phase5-rizz-ai-demo`](./runs/phase5-rizz-ai-demo/index.md) | `phase5_scenario` | — | — · risk `MODERATE` · term `sigma rizz locked in` |
| [`golden-seed-0.3.1`](./runs/golden-seed-0.3.1/index.md) | `analysis` | 9 | betting-sharp:5 |

## What is published

- Sanitized receipt summaries (preview text only)
- Lineage family + confidence, typology, virality metrics, hyperstition stage
- Optional Phase 5 scenario digests (risk tier, transmission peak — SPECULATIVE)
- Ledger index extracts (no secrets)

## What is **not** published

- Full raw network payloads / API keys
- Operator score log settlements (keep local unless you deliberately export)
- Anything that would invent Brier without settlement

## Append a run

```bash
# Analysis snapshot → runs/<id>/ + latest/ + catalog
python3 scripts/hyperlex.py archive-export --include-golden --history

# From operator home
python3 scripts/hyperlex.py archive-export --include-home-receipts --history \
  --snapshot-id "scan-$(date -u +%Y%m%dT%H%M%SZ)"

# Phase 5 scenario into history
python3 scripts/hyperlex.py simulate --term rizz --out /tmp/p5.json
python3 scripts/hyperlex.py archive-export --phase5 /tmp/p5.json --history

# Rebuild catalog only
python3 scripts/hyperlex.py archive-catalog
```

Commit + push `docs/archive/` to refresh Pages (`.github/workflows/docs.yml`).
