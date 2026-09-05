# Hyperlex in Claude Code

Hermes is the primary skill host. Claude Code is an additional host. Same CLI,
same settlement rule, same receipts. This is dual-runtime packaging — not a
rewrite.

## Two install shapes

| Shape | Path | What Claude loads |
|-------|------|-------------------|
| **Personal skill** | `~/.claude/skills/hyperlex/` | Directory `SKILL.md` + bundled `scripts/` / `src/` for offline CLI |
| **Local plugin** | `~/.claude/plugins/hyperlex/` | `.claude-plugin/plugin.json`, root `SKILL.md`, slash `commands/` |

The repo itself is already a single-skill plugin: root `SKILL.md` plus
`.claude-plugin/plugin.json`. You can point Claude Code at this checkout
instead of copying it.

Thin `hyperlex init --target claude` writes only `SKILL.md` and expects
`hyperlex` on PATH. Prefer `install.sh --claude` when you want the offline CLI
tree without a pip install.

## Personal skill (recommended for operators)

```bash
bash install.sh --claude --dry-run
bash install.sh --claude
export HYPERLEX_SKILL_DIR="${HOME}/.claude/skills/hyperlex"
export HERMES_SKILL_DIR="${HERMES_SKILL_DIR:-$HYPERLEX_SKILL_DIR}"
export HLX="python3 $HYPERLEX_SKILL_DIR/scripts/hyperlex.py"
$HLX check && $HLX doctor && $HLX demo
```

`--claude` is **additive**. Hermes still installs to `~/.hermes/skills/hyperlex`
unless you pass `--target`. Sibling slash helpers land next to the personal
skill:

```text
~/.claude/skills/hyperlex/          # main contract + CLI
~/.claude/skills/hyperlex-demo/
~/.claude/skills/hyperlex-wizard/
~/.claude/skills/hyperlex-scan/
~/.claude/skills/hyperlex-analyze/
~/.claude/skills/hyperlex-pending/
~/.claude/skills/hyperlex-settle/
```

Reload Claude Code so it sees the new skills.

## Local plugin dir

```bash
bash install.sh --claude-plugin --dry-run
bash install.sh --claude-plugin
# tree: ~/.claude/plugins/hyperlex
# enable via Claude plugin UI, or: claude plugin add ~/.claude/plugins/hyperlex
```

Plugin slash commands live in repo `commands/` (`/hyperlex-demo`, …). The main
`/hyperlex` skill is the root `SKILL.md` (single-skill layout — no duplicate
engine under `skills/hyperlex/`).

You can also add this git checkout as a plugin path. `CLAUDE.md` at the repo
root is **project** context only; Claude does not load it as plugin context.

## First success (no Anthropic API)

```bash
$HLX demo
$HLX wizard --auto
```

Expect `ok: true` and `brier: null`. No paid keys. Settlement stays a human
step: `pending` → operator decision → `settle` → `score-series`.

## Differences from Hermes

| | Hermes | Claude Code |
|--|--------|-------------|
| Default skill path | `~/.hermes/skills/hyperlex` | `~/.claude/skills/hyperlex` |
| Env name | `HERMES_SKILL_DIR` | `HYPERLEX_SKILL_DIR` (may reuse Hermes) |
| Wrapper | `python3 $HERMES_SKILL_DIR/scripts/hyperlex.py` | `scripts/claude_hlx.sh` |
| Discovery | Hermes scans `SKILL.md` | Personal skills + optional plugin |
| Slash helpers | Hermes procedure in `SKILL.md` | `.claude/skills/` and `commands/` |
| Contract | Same `SKILL.md` | Same `SKILL.md` + Claude section |

Fail-closed rules do not change: no invented Brier, no auto-settle, no
phenomenology claims.

## See also

- [Claude runtime contract](claude-runtime-contract.md)
- [Hermes skill model](hermes-skill.md)
- [Operator loop](operator-loop.md)
