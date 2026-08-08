# Quickstart — offline first success

**Goal:** one command, no API keys, no Hermes host, real receipt, `brier: null`.

## From this repo

```bash
cd Hyperlex
python3 scripts/hyperlex.py demo
```

Equivalent explicit path:

```bash
export HYPERLEX_OFFLINE=1
python3 scripts/hyperlex.py pipeline "rizz" --route offline
# or: run "rizz" --route offline
```

### What success looks like

| Check | Expect |
|-------|--------|
| Exit code | `0` |
| `ok` | `true` |
| `brier` | `null` |
| Receipt | Path under `~/.hyperlex/receipts/` or demo out dir |
| Lineage | Often a `family_id` for known slang atoms |

### Verify the environment

```bash
python3 scripts/hyperlex.py doctor
python3 scripts/hyperlex.py smoke
python3 scripts/hyperlex.py check
```

## After Hermes skill install

```bash
bash install.sh
export HERMES_SKILL_DIR="${HOME}/.hermes/skills/hyperlex"
export HLX="python3 $HERMES_SKILL_DIR/scripts/hyperlex.py"
$HLX demo
$HLX wizard --auto
```

## Committed sample output

See [`examples/quickstart/`](https://github.com/scrimshawlife-ctrl/Hyperlex/tree/main/examples/quickstart)
for a checked-in receipt summary and notes from the offline demo path.

## Next

1. [See it work](see-it-work.md) — golden example + archive  
2. [Operator loop](../operator-loop.md) — settle for real Brier  
3. [Commands](../commands.md) — full map  
4. [Glossary](glossary.md) — jargon  
