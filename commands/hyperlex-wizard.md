---
description: Week-one Hyperlex onboarding via wizard --auto. Offline. Never auto-settles.
allowed-tools: Bash Read
---

# /hyperlex-wizard

Week-one guided path. Prefer `--auto` in Claude (non-interactive).

```bash
: "${HLX:=python3 ${HYPERLEX_SKILL_DIR:-${HERMES_SKILL_DIR:-$HOME/.claude/skills/hyperlex}}/scripts/hyperlex.py}"
$HLX wizard --auto
$HLX wizard --auto --query "<term>"
```

## Expected

Steps: `env_intro` → `doctor` → `demo` → `first_pipeline` → `calibration_coach` → `score_series_hint` → `handoff`.

Summarize those steps. Open analysis stays `brier: null`. Show any open forecasts from the wizard / `$HLX pending`.

## Fail-closed

Do not auto-settle. Ask the operator for TRUE|FALSE|VOID, then coach `$HLX settle`. Do not invent Brier.
