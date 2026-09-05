---
name: hyperlex-demo
description: Run the Hyperlex offline demo and summarize receipt labels. No API keys. Never invent Brier.
when_to_use: User asks for a Hyperlex demo, first success path, or a sample receipt.
allowed-tools: Bash Read
---

# /hyperlex-demo

Run the offline demo. Summarize labels from the CLI output. Do not invent scores.

```bash
: "${HLX:=python3 ${HYPERLEX_SKILL_DIR:-${HERMES_SKILL_DIR:-$HOME/.claude/skills/hyperlex}}/scripts/hyperlex.py}"
$HLX demo
# repo checkout: python3 scripts/hyperlex.py demo
# wrapper: bash scripts/claude_hlx.sh demo
```

## Expected

- Exit `0`, `ok: true`
- `brier` and `provenance_brier` are `null`
- Receipt path under the demo out dir or `~/.hyperlex/receipts/`
- Known atoms often match a lineage family (`rizz` → `brainrot-aura`)
- Repeat OBSERVED / INFERRED / SPECULATIVE — do not upgrade them

## Fail-closed

If the CLI fails, report the error. Do not fabricate a receipt or Brier. Do not settle.
