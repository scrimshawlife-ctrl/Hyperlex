# Hyperlex Quickstart

## Install as Hermes skill

```bash
git clone https://github.com/scrimshawlife-ctrl/Hyperlex-Hermes-Specs.git
cd Hyperlex-Hermes-Specs
bash install.sh --dry-run
bash install.sh
export HERMES_SKILL_DIR="${HOME}/.hermes/skills/hyperlex"
```

## First run

```bash
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" check
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" sources
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" analyze \
  --query "sharp steam square revenge" \
  --source mock \
  --forecasts \
  --validate
```

## Operator settle path

```bash
# Append forecasts to score log during analyze
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" analyze \
  --query "sharp steam" --source mock \
  --forecasts --append-log

# Settle one forecast (TRUE/FALSE)
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" settle \
  --forecast-id <id> --decision TRUE \
  --authority-note "operator review"

# Recompute Brier series + chain verify
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" score-series \
  --mean-shift --verify-chain
```

Score log: `~/.hyperlex/score_log.jsonl` (override with `HYPERLEX_SCORE_LOG` or `--log`).

## Design laws

1. **Real over synthetic** — mock is for tests only; mark it.
2. **Provenance sacred** — receipts carry integrity hashes.
3. **Brier requires settlement** — open analysis has `brier: null`.
4. **Fail closed** — empty series → `NOT_COMPUTABLE`.

## More

- Full contract: `SKILL.md`
- Calibration design: `docs/brier-calibration.md`
- Lineages: `docs/slang-lineages.md`
