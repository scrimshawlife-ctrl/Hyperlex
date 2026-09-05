---
name: hyperlex-settle
description: Coach Hyperlex settlement. Human must supply forecast-id and decision. Never invent outcomes or Brier.
when_to_use: User wants to settle a forecast or close the calibration loop.
allowed-tools: Bash Read
---

# /hyperlex-settle

Settlement is an **explicit human step**. Do not invent TRUE/FALSE/VOID/CONFLICT. Do not invent Brier.

1. `$HLX pending` — show open ids.
2. Ask the operator for `--forecast-id` and `--decision`.
3. Only after they choose, run:

```bash
: "${HLX:=python3 ${HYPERLEX_SKILL_DIR:-${HERMES_SKILL_DIR:-$HOME/.claude/skills/hyperlex}}/scripts/hyperlex.py}"
$HLX settle --forecast-id <id> --decision TRUE
# FALSE | VOID | CONFLICT
$HLX score-series --mean-shift --verify-chain
```

## Expected

Settle appends the score log. `score-series` is the only place a numeric Brier is real. Empty series → `NOT_COMPUTABLE`.

## Fail-closed

If the operator has not chosen a decision, stop. Coach the flags. Do not auto-settle. Do not guess outcomes.
