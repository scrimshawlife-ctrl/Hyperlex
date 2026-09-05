---
name: hyperlex-pending
description: List open Hyperlex forecasts from the score log. Start of the calibration loop.
when_to_use: User asks what forecasts are open, pending, or ready to settle.
allowed-tools: Bash Read
---

# /hyperlex-pending

List unsettled forecasts. This is the start of the calibration loop — not settlement.

```bash
: "${HLX:=python3 ${HYPERLEX_SKILL_DIR:-${HERMES_SKILL_DIR:-$HOME/.claude/skills/hyperlex}}/scripts/hyperlex.py}"
$HLX pending
$HLX pending --limit 20
```

## Expected

JSON list of open forecast ids (default log: `~/.hyperlex/score_log.jsonl`). Empty list is valid.

## Fail-closed

Do not invent forecast ids. Do not compute Brier here. Next step is human: `/hyperlex-settle` after they choose TRUE|FALSE|VOID|CONFLICT.
