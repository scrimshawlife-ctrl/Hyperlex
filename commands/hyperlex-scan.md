---
description: LIVE_EMERGENCE_SCAN helper. Pass a query (or comma-separated queries). Offline-first.
allowed-tools: Bash Read
---

# /hyperlex-scan

Multi-query LIVE_EMERGENCE_SCAN. Prefer `--route offline` unless the user allows network.

```bash
: "${HLX:=python3 ${HYPERLEX_SKILL_DIR:-${HERMES_SKILL_DIR:-$HOME/.claude/skills/hyperlex}}/scripts/hyperlex.py}"
$HLX scan --query "$ARGUMENTS" --route offline --receipt --forecasts --append-log
$HLX scan --queries "rizz,locked in" --route offline --receipt --forecasts --append-log
$HLX scan --config "${HYPERLEX_SKILL_DIR:-.}/examples/cron/scan-queries.json" --route offline --receipt --forecasts
```

## Expected

JSON scan summary. Per-query receipts when `--receipt` is set. Forecasts have `brier: null` until settle.

## Fail-closed

Do not register cron. `risk-schedule` is advisory only. Do not invent Brier. Do not auto-settle.
