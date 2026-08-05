# Hyperlex Brier & Calibration Design

**Status**: Design surface active  
**Version target**: 0.2.0  
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
| `murphy` | `{reliability, resolution, uncertainty, brier_score}` |
| `yates` | `{bias_squared, excess_variance, covariance_deficit, brier_score}` |
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

### Yates decomposition

```
bias²            = (mean(f) - mean(o))²
excess_variance  = Var(f)
covariance_deficit = Var(o) - 2*Cov(f, o)
BS               = bias² + excess_variance + covariance_deficit
```

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
       → append to local score log / optional series recompute
```

Receipts remain the primary artifact. Forecasts are **derived views** of receipts, not a parallel truth.

---

## Module Layout

```
src/hyperlex/
  calibration/
    __init__.py          # public API
    mapping.py           # signal → probability (versioned)
    forecast.py          # extract_forecasts, Forecast model
    settlement.py        # Settlement model, settle helpers
    scoring.py           # atomic, series BS, BSS, Murphy, Yates
    series.py            # cohort aggregation, NOT_COMPUTABLE guards
```

Public functions (minimal):

```python
extract_forecasts(result: dict, mapping_version: str = "v1") -> list[dict]
settle(forecast: dict, outcome_value: float, decision: str, **meta) -> dict
score_pair(forecast: dict, settlement: dict) -> dict
score_series(pairs: list[tuple[dict, dict]], reference: str = "climatology") -> dict
```

All pure where possible. Side effects only when writing optional local score logs (mirroring receipt style).

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

## Explicit Non-Goals (v1)

- Multi-class Brier beyond binary outcomes
- Online recalibration / Platt scaling of lineage confidence
- Automatic settlement without authority marker
- Treating hyperstition stage or virality as strongly calibrated probabilities without review

---

## Acceptance Criteria

1. No analysis result emits a numeric Brier without a linked settlement series.
2. `score_pair` and `score_series` are deterministic and match the formulas above.
3. Empty or invalid input yields `NOT_COMPUTABLE`, never a fabricated float.
4. Forecast extraction is pure given a result + mapping version.
5. Design and schemas are documented under `docs/` and `schemas/`.

---

## References

- Brier (1950); Murphy (1973) decomposition; Yates decomposition
- Abraxas-v2.0 `core/scoring/brier.py`, `core/intelligence/brier_variants.py` (compatible semantics)
- Hyperlex DESIGN principles 1, 2, 7, 9, 10, 11
