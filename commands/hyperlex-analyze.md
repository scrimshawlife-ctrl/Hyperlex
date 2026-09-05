---
description: Analyze pasted text or a JSON ingest file with the Hyperlex CLI. Prefer offline route.
allowed-tools: Bash Read
---

# /hyperlex-analyze

Analyze text or a file. Prefer `pipeline` / `run` when the user wants a receipt + forecasts. Use `analyze` for analysis-only.

```bash
: "${HLX:=python3 ${HYPERLEX_SKILL_DIR:-${HERMES_SKILL_DIR:-$HOME/.claude/skills/hyperlex}}/scripts/hyperlex.py}"
$HLX analyze "$ARGUMENTS" --route offline
$HLX pipeline "$ARGUMENTS" --route offline
$HLX analyze --input "$ARGUMENTS" --route offline
```

## Expected

JSON result. `provenance.brier` is `null`. Lineage / virality / mutation_trace only when the CLI attaches them.

## Fail-closed

Do not invent labels or Brier. If the file is missing, say so. Do not settle.
