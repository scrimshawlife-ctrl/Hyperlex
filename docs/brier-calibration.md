# Hyperlex Brier & Calibration Design

**Status**: Design surface active (v1.1 diagnostics)  
**Version target**: 0.2.2  
**Principle alignment**: Real Over Synthetic · Provenance Sacred · Evolution via Receipts · Determinism

## Intent

Replace the decorative `provenance.brier = 0.89` with a real forecast → settlement → score pipeline. Hyperlex emits **forecasts** (probabilities derived from analysis signals). Later **settlements** record outcomes. **Brier scores** are computed only from settled pairs. Unsettled forecasts never claim a Brier number.

This layer is self-contained inside Hyperlex. It is deliberately compatible with Abraxas Brier ledger patterns but has **no hard dependency** on Abraxas.

---

## Core Objects

### 1. Forecast

A probabilistic claim bound to a receipt.

| Field | Meaning |
|-------|--------|
| `forecast_id` | Stable id (hash of receipt canonical + signal_key) |
| `receipt_ref` | Path or integrity of the originating Hyperlex receipt |
| `signal_key` | Which analysis signal was mapped (e.g. `lineage.confidence`, `virality.hybrid_score`) |
| `probability` | \(f \in [0,1]\) |
| `target_event` | Human-readable description of what is being predicted |
| `target_schema` | Machine key for settlement matching (e.g. `lineage.family_confirmed`, `term.stabilized`) |
| `created_at` | ISO timestamp |
| `provenance` | OBSERVED / INFERRED / SPECULATIVE for the probability itself |

### 2. Settlement

The resolved outcome for a forecast.

| Field | Meaning |
|-------|--------|
| `settlement_id` | Stable id |
| `forecast_id` | Links to forecast |
| `outcome_value` | 0.0 or 1.0 (binary for v1) |
| `settlement_decision` | `TRUE` / `FALSE` / `VOID` / `CONFLICT` |
| `settled_at` | ISO timestamp |
| `authority` | Who/what settled (operator, automated rule, external oracle) |
| `evidence_ref` | Optional pointer to supporting material |

`VOID` and `CONFLICT` are **not scored**.

### 3. Brier Score Record

Atomic and series scores derived only from settled forecast–outcome pairs.

| Field | Meaning |
|-------|--------|
| `atomic_score` | \((f - o)^2\) for one pair |
| `series_brier` | Mean of atomic scores over a cohort |
| `brier_skill_score` | \(1 - BS / BS_{ref}\) vs climatology or persistence |
| `murphy` | standard REL − RES + UNC |
| `murphy_ferro` | Ferro–Fricker bias-corrected Murphy (prefer for small n) |
| `yates` | classical bias² + excess variance + covariance deficit |
| `yates_vieira` | non-negative rearrangement: variance mismatch + correlation deficit + bias² |
| `discrimination` | Δf = mean(f\|o=1) − mean(f\|o=0) |
| `n` | Number of scored pairs |
| `status` | `SCORED` or `NOT_COMPUTABLE` |

---

## Signal → Probability Mapping (v1)

Only signals that are already continuous and thresholded are eligible as \(f\).

| Signal | Mapping | Target event (v1) |
|--------|---------|-------------------|
| `analysis.lineage.confidence` | use confidence directly as \(f\) | Family membership confirmed on later human or automated review |
| `analysis.virality.hybrid_score` | use hybrid_score as \(f\) (weak) | Observed uptake / engagement above threshold in a defined window |
| Hyperstition stage | EMERGENT → 0.35, ACTUALIZING → 0.70 (explicit discrete map) | Loop later confirmed by market or cultural evidence |
| Neologism confidence | **not used as \(f\) in v1** (too crude) | — |

**Rule**: the mapping function must be pure and versioned (`mapping_version`). Changing the map starts a new forecast lineage; old forecasts keep their original \(f\).

---

## Calculation Methods (normative)

### Atomic

```
atomic = (probability - outcome_value) ** 2
```

### Series Brier

```
BS = mean(atomic_i) over scored pairs
```

### Brier Skill Score

```
BSS = 1 - (BS / BS_reference)
```

Reference options:
- **climatology**: always predict mean(outcome) of the series
- **persistence**: previous outcome (when ordered)

### Murphy decomposition (binary, binned)

```
BS = REL - RES + UNC

REL = Σ (n_k/N) * (f̄_k - ō_k)²     # reliability (calibration error)
RES = Σ (n_k/N) * (ō_k - ō)²         # resolution (discrimination)
UNC = ō * (1 - ō)                    # uncertainty (base-rate variance)
```

Default bins: 10 equal-width on [0, 1).

**Finite-sample bias:** standard REL is overestimated and UNC underestimated. Prefer Ferro–Fricker when n is small.

### Ferro–Fricker bias-corrected Murphy (v1.1)

```
UNC̃ = UNĈ + ȳ(1−ȳ)/(n−1)
RES̃ = REŜ + ȳ(1−ȳ)/(n−1) − (1/n) Σ [n_k/(n_k−1)] ȳ_k(1−ȳ_k)
REL̃ = REL̂ − (1/n) Σ [n_k/(n_k−1)] ȳ_k(1−ȳ_k)
```

Bins with `n_k < 2` skip the within-bin correction term. Components floored at 0. Exposed as `murphy_ferro` with `correction: "ferro_fricker"` and optional `uncorrected` snapshot.

### Yates decomposition (classical)

```
bias²            = (mean(f) - mean(o))²     # calibration-in-the-large (Yates bias)
excess_variance  = Var(f)
covariance_deficit = Var(o) - 2*Cov(f, o)
BS               = bias² + excess_variance + covariance_deficit
```

**Operational note:** `bias_squared` is the primary signal for level recalibration of forecast mappings (e.g. shift mean lineage.confidence toward empirical confirmation rate).

### Vieira non-negative Yates (v1.1)

```
BS = (σ_f − σ_o)² + 2(σ_f σ_o − Cov(f,o)) + (μ_f − μ_o)²
     ─────────────   ─────────────────────   ─────────────
     variance          correlation              bias²
     mismatch          deficit
```

All three terms ≥ 0. Optimality conditions: match outcome variance, perfect positive correlation, no mean bias. Also reports `rho` when defined.

### Discrimination slope Δf (v1.1)

```
Δf = mean(f | o=1) − mean(f | o=0)
```

Requires at least one positive and one negative outcome. Higher Δf = better separation. `NOT_COMPUTABLE` if either class is empty.

### Fail-closed

If no scored pairs exist, or lengths mismatch, every aggregate field is `NOT_COMPUTABLE`. Never invent a number.

---

## Lifecycle

```
analyze → result (+ optional lineage)
       → emit_receipt
       → extract_forecasts(result) → Forecast[]   # pure, deterministic

... time passes / human or automated review ...

settle(forecast_id, outcome) → Settlement
       → score_pair(forecast, settlement) → atomic Brier record
       → score_series(pairs) → BS, BSS, Murphy, Murphy-Ferro, Yates, Vieira, Δf
```

Receipts remain the primary artifact. Forecasts are **derived views** of receipts, not a parallel truth.

---

## Module Layout

```
src/hyperlex/
  calibration/
    __init__.py          # public API
    mapping.py           # signal → probability (versioned)
    forecast.py          # extract_forecasts
    settlement.py        # settle, is_scorable
    scoring.py           # atomic, series, Murphy, Ferro, Yates, Vieira, Δf
    score_log.py         # append-only hash-chained log + recompute_series
    export.py            # Abraxas BrierLedgerEntry-compatible export (no import)
    recalibrate.py       # advisory mean-shift (future forecasts only)
```

Public functions:

```python
extract_forecasts(result, mapping_version="v1") -> list[dict]
settle(forecast, outcome_value, settlement_decision, ...) -> dict
score_pair(forecast, settlement) -> dict
score_series(pairs, reference="climatology") -> dict
settle_and_log(forecast, outcome_value, settlement_decision, ..., path=...) -> dict
recompute_series(path=None, signal_key=None) -> dict
to_brier_ledger_entry(forecast, score, settlement=...) -> dict
mean_shift_from_series(series) -> dict   # ADVISORY only
murphy_decomposition_ferro(preds, targets) -> dict
yates_vieira(preds, targets) -> dict
discrimination_slope(preds, targets) -> dict
```

### Score log (operator path)

Default path: `~/.hyperlex/score_log.jsonl`  
Override: `HYPERLEX_SCORE_LOG` env, CLI `--log`, or `--repo-log` → `out/calibration/score_log.jsonl`

Each line is a JSON record with `schema`, `event` (`forecast`|`settlement`|`score`),
`prev_hash`, `record_hash`, `body`. Append-only; series scores are **recomputed** from
the log via `recompute_series` / `score-series` CLI — never stored as sole truth.

### CLI

```bash
# Analyze + extract forecasts + append to log
python3 scripts/hyperlex.py analyze --query "sharp steam" --source mock \
  --forecasts --append-log --log ~/.hyperlex/score_log.jsonl

# Or extract from a saved result
python3 scripts/hyperlex.py extract-forecasts --input out/result.json --append-log

# Operator settles a forecast (TRUE/FALSE/VOID/CONFLICT)
python3 scripts/hyperlex.py settle --forecast-id <id> --decision TRUE \
  --authority-note "human review confirmed family" --export-ledger

# Recompute series + optional mean-shift diagnostic + chain verify
python3 scripts/hyperlex.py score-series --mean-shift --verify-chain
python3 scripts/hyperlex.py verify-score-log
```

---

## Schema Contracts

- `schemas/forecast.v1.schema.json`
- `schemas/settlement.v1.schema.json`
- `schemas/brier_series.v1.schema.json`

`provenance.brier` on analysis results is **deprecated**. New results omit it or set `"brier": null` with note `"brier_requires_settlement"`. Series scores live in calibration artifacts, not inside every scan receipt.

---

## Integration Points

| System | Relationship |
|--------|----------------|
| Hyperlex receipts | Source of forecasts; integrity hash anchors `forecast_id` |
| Lineage matcher | Primary \(f\) source (`lineage.confidence`) |
| Abraxas Brier ledger | Optional export target; same atomic formula and Murphy/Yates semantics; no import required |
| Hermes / Orchestra | Forecasts and series scores are runnable signals for runes / cron |

---

## Hyperstition feedback (v0.2.2)

Settled `hyperstition.stage` series can advise an updated discrete stage→f map for **future** forecasts only (`hyperstition_feedback_from_series` / CLI `feedback`). Historical forecasts are never rewritten. See `docs/connectors.md`.

## Explicit Non-Goals (v1)

- Multi-class Brier beyond binary outcomes
- Online recalibration / Platt scaling of lineage confidence
- Automatic settlement without authority marker
- Treating hyperstition stage or virality as strongly calibrated probabilities without review
- Yates continuity correction (chi-square) — not applicable to Brier path

---

## Acceptance Criteria

1. No analysis result emits a numeric Brier without a linked settlement series.
2. `score_pair` and `score_series` are deterministic and match the formulas above.
3. Empty or invalid input yields `NOT_COMPUTABLE`, never a fabricated float.
4. Forecast extraction is pure given a result + mapping version.
5. Design and schemas are documented under `docs/` and `schemas/`.
6. v1.1 diagnostics (`murphy_ferro`, `yates_vieira`, `discrimination`) appear on every `score_series` output.

---

## References

- Brier (1950); Murphy (1973); Yates (1982) covariance decomposition
- Ferro & Fricker (2012) — bias-corrected Murphy decomposition
- Vieira (2026) arXiv:2603.05544 — non-negative Yates rearrangement
- Abraxas-v2.0 `core/scoring/brier.py` (compatible classical Murphy/Yates)
- Hyperlex DESIGN principles 1, 2, 7, 9, 10, 11, 12
