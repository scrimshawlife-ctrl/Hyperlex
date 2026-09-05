# Hyperlex — Claude Code runtime contract

## Identity

| Field | Value |
|-------|--------|
| Skill / plugin name | `hyperlex` |
| Personal skill | `~/.claude/skills/hyperlex` |
| Local plugin dir | `~/.claude/plugins/hyperlex` |
| Plugin manifest | `.claude-plugin/plugin.json` |
| Entry contract | root `SKILL.md` (single-skill plugin layout) |
| CLI | `scripts/hyperlex.py` |
| Wrapper | `scripts/claude_hlx.sh` |
| Package | `src/hyperlex/` |

Claude Code loads a root `SKILL.md` as one skill when the plugin has no
`skills/` directory and no `skills` manifest field. Slash helpers are project
skills under `.claude/skills/` and plugin commands under `commands/`. Do not
copy the engine into `skills/hyperlex/`.

`CLAUDE.md` is project context when this repo is the working directory. It is
not plugin context.

## Paths

```text
Personal skill (~/.claude/skills/hyperlex/):
  SKILL.md
  scripts/hyperlex.py
  scripts/claude_hlx.sh
  src/hyperlex/

Local plugin (~/.claude/plugins/hyperlex/):
  .claude-plugin/plugin.json
  SKILL.md
  commands/hyperlex-*.md
  scripts/  src/

Project checkout:
  CLAUDE.md
  .claude/skills/<helper>/SKILL.md
```

Operator data is unchanged (outside the skill tree):

```text
~/.hyperlex/receipts/
~/.hyperlex/score_log.jsonl
```

## Environment

| Variable | Role |
|----------|------|
| `HLX` | CLI invocation string (`python3 …/scripts/hyperlex.py`) |
| `HYPERLEX_SKILL_DIR` | Claude-preferred skill root |
| `CLAUDE_SKILL_DIR` | Optional alias for `HYPERLEX_SKILL_DIR` |
| `HERMES_SKILL_DIR` | Hermes name for the same tree; Claude may reuse it |

`scripts/claude_hlx.sh` resolves the skill dir in this order:
`HYPERLEX_SKILL_DIR`, `CLAUDE_SKILL_DIR`, `HERMES_SKILL_DIR`, this checkout,
`~/.claude/skills/hyperlex`, `~/.claude/plugins/hyperlex`,
`~/.hermes/skills/hyperlex`. Then it execs `scripts/hyperlex.py`.

## Execution rules

1. Prefer Bash CLI: `$HLX …` or `bash scripts/claude_hlx.sh …`.
2. Baseline work uses `--route offline` (no network, no API keys).
3. Never invent numeric Brier. Open analysis keeps `provenance.brier` null.
4. Never auto-settle. Ask for TRUE\|FALSE\|VOID\|CONFLICT, then run `settle`.
5. `doctor` reports `CLAUDE_OK` or `CLAUDE_MISSING`. Missing does not fail Hermes.

## Authority

Same classes as [hermes-runtime-contract.md](hermes-runtime-contract.md):
OBSERVED, INFERRED, SPECULATIVE, NOT_COMPUTABLE, operator settlement.
