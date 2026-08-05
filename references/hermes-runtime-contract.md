# Hyperlex — Hermes runtime contract

## Identity

| Field | Value |
|-------|--------|
| Skill name | `hyperlex` |
| Default install | `~/.hermes/skills/hyperlex` |
| Entry contract | `SKILL.md` |
| CLI | `scripts/hyperlex.py` |
| Package | `src/hyperlex/` |

Hermes discovers skills by scanning `$HERMES_HOME/skills/**/SKILL.md`.
This skill is a **directory skill** (not a single markdown file).

## Paths

```text
$HERMES_SKILL_DIR/
  SKILL.md                 # agent contract (frontmatter + procedure)
  hyperlex.manifest.yaml   # machine metadata
  VERSION
  install.sh
  scripts/hyperlex.py      # CLI entrypoint
  src/hyperlex/            # importable package
  schemas/                 # public JSON schemas
  docs/                    # design docs
  examples/                # slang-family diagrams, samples
  references/              # runtime + domain references
```

Operator / runtime data (outside skill tree):

```text
~/.hyperlex/score_log.jsonl     # default score log
$HERMES_SKILL_DIR/out/          # smoke + optional local artifacts
```

## Execution rules

1. Prefer CLI with absolute skill path:
   `python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" …`
2. The CLI inserts `src/` at front of `sys.path` so `import hyperlex` resolves to the package, not the script.
3. Baseline work uses `source=mock` (deterministic, offline).
4. Network sources are optional and must degrade without crashing.
5. Write receipts and score-log events; do not invent Brier numbers.

## Authority classes

| Class | Use |
|-------|-----|
| OBSERVED | Directly from ingest signal / receipt integrity |
| INFERRED | Lineage confidence, mapped forecast probabilities |
| SPECULATIVE | Hyperstition stage maps without later confirmation |
| NOT_COMPUTABLE | Missing settlement, empty series, invalid pairs |
| operator settlement | Explicit `settle` with authority.kind |

## Dependencies

| Profile | Required |
|---------|----------|
| stdlib | Python ≥ 3.10 only |
| validation | optional `jsonschema` |
| network | optional `requests` |
| crawl | optional `crawl4ai` |

Absence of optional deps must not block `check` / `smoke` / mock analyze.

## Reload

After `install.sh`, restart Hermes or reload skills so the agent sees the new/updated `SKILL.md`.
