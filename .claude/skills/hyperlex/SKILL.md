---
name: hyperlex
description: >
  Main Hyperlex contract in Claude Code. Use for slang, memetics, lineage,
  virality, hyperstition, receipts, forecasts, and settlement coaching.
  Prefer the CLI. Not for jailbreak / wrap composition.
when_to_use: >
  User asks for Hyperlex, slang analysis, memetic emergence, lineage,
  Brier settlement, or cultural-signal receipts.
allowed-tools: Bash Read Grep
---

# Hyperlex (project skill)

Read the repo-root [SKILL.md](../../../SKILL.md) for the full Hermes + Claude
contract. This file is a thin pointer so Claude Code can invoke `/hyperlex`
when this checkout is the project. Do not duplicate engine logic here.

## Invoke

```bash
export HYPERLEX_SKILL_DIR="${HYPERLEX_SKILL_DIR:-$PWD}"
export HERMES_SKILL_DIR="${HERMES_SKILL_DIR:-$HYPERLEX_SKILL_DIR}"
export HLX="${HLX:-python3 $HYPERLEX_SKILL_DIR/scripts/hyperlex.py}"
$HLX check
$HLX doctor
$HLX demo
$HLX wizard --auto
$HLX pipeline "<term>" --route offline
```

Installed personal skill:

```bash
export HLX="python3 $HOME/.claude/skills/hyperlex/scripts/hyperlex.py"
# or: bash "$HOME/.claude/skills/hyperlex/scripts/claude_hlx.sh"
```

## Fail-closed

- Never invent a numeric Brier. Open analysis keeps `brier: null`.
- Never auto-settle. Ask for TRUE|FALSE|VOID|CONFLICT, then run `settle`.
- Prefer Bash CLI over guessing labels. Repeat OBSERVED / INFERRED / SPECULATIVE.
