# Hyperlex — Claude Code project notes

This file is for when you open the Hyperlex repo as a Claude Code **project**.
Plugin `CLAUDE.md` is not loaded as plugin context. The behavior contract is
repo-root [`SKILL.md`](./SKILL.md). Host paths: [`docs/claude-skill.md`](./docs/claude-skill.md)
and [`references/claude-runtime-contract.md`](./references/claude-runtime-contract.md).

## Identity

Hyperlex is a memetic emergence engine (slang, lineage, virality, hyperstition,
receipts, settled forecasts). Hermes is the primary skill host. Claude Code is
an additional host. Dual-runtime — not a rewrite.

You are an operator assistant. You run the CLI. You do not invent scores.

## Environment

```bash
export HYPERLEX_SKILL_DIR="${HYPERLEX_SKILL_DIR:-$PWD}"
export HERMES_SKILL_DIR="${HERMES_SKILL_DIR:-$HYPERLEX_SKILL_DIR}"
export HLX="${HLX:-python3 $HYPERLEX_SKILL_DIR/scripts/hyperlex.py}"
# wrapper:
# bash scripts/claude_hlx.sh <command>
```

`HERMES_SKILL_DIR` is the Hermes name for the same skill root. Claude may reuse
it. Prefer `HYPERLEX_SKILL_DIR` in Claude sessions.

## First commands

```bash
$HLX check
$HLX doctor
$HLX demo
$HLX wizard --auto
```

Expect `ok: true` and **`brier: null`** on open analysis. No API keys for this path.

## Settlement rule

Settlement is a **human** step. Never auto-settle. Never invent a numeric Brier.

```text
pending → ask the operator for TRUE|FALSE|VOID|CONFLICT
       → settle --forecast-id <id> --decision …
       → score-series --mean-shift --verify-chain
```

Empty series → `NOT_COMPUTABLE`.

## Receipts and logs

```text
~/.hyperlex/receipts/
~/.hyperlex/receipt_ledger.jsonl
~/.hyperlex/score_log.jsonl
```

Demo artifacts also land under `examples/quickstart/out/` unless `--out-dir` is set.

## Slash helpers

Project skills under `.claude/skills/` (and plugin `commands/` when this repo is
a Claude plugin): `/hyperlex`, `/hyperlex-demo`, `/hyperlex-wizard`,
`/hyperlex-scan`, `/hyperlex-analyze`, `/hyperlex-pending`, `/hyperlex-settle`.
