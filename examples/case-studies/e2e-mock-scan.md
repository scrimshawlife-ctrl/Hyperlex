# Case study: end-to-end mock scan (Hermes skill)

Offline-safe path using `source=mock`. No network, no Abraxas, no Brier invention.

## Goal

Run analyze → receipt → forecasts → diagrams → market signal → (optional) settle → series.

## Prerequisites

```bash
bash install.sh
export HERMES_SKILL_DIR="${HOME}/.hermes/skills/hyperlex"
H="$HERMES_SKILL_DIR/scripts/hyperlex.py"
python3 "$H" check
```

## Steps

### 1. Analyze with receipt + forecasts

```bash
python3 "$H" analyze \
  --query "nerf buff meta sweaty skill issue" \
  --source mock \
  --forecasts --receipt --append-log \
  --out out/case-study/analyze.json
```

Expect:
- `provenance.brier == null`
- `analysis.lineage.family_id` ≈ `gaming-meta` (INFERRED)
- `analysis.virality.prediction` present (SPECULATIVE)
- `n_forecasts >= 1`

### 2. Relay + market signal

```bash
python3 "$H" relay --input out/case-study/analyze.json --forecasts \
  --out out/case-study/envelopes.json
python3 "$H" signal --input out/case-study/analyze.json \
  --out out/case-study/signal.json
```

### 3. Diagrams from golden + this receipt

```bash
python3 "$H" diagram --from-golden --input out/case-study/analyze.json \
  --out-dir out/case-study/diagrams
```

### 4. Operator settlement (manual)

```bash
# pick a forecast_id from analyze.json / score log
python3 "$H" settle --forecast-id <id> --decision TRUE \
  --authority-note "case-study review"
python3 "$H" score-series --verify-chain
```

Only after step 4 may Brier numbers appear — and only on series artifacts.

## Runnable one-shot

```bash
python3 "$HERMES_SKILL_DIR/scripts/run_case_study.py" --out-dir out/case-study
```

Writes the same artifacts without requiring manual steps 1–3.
