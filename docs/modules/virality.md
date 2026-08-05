# Virality (descriptive + prediction v0)

## Descriptive hybrid (`compute_virality_score`)

| Feature | Role |
|---------|------|
| `velocity` | token-length proxy (capped) |
| `acceleration` | lexical spread/coordination cues |
| `hybrid_score` | weighted blend with network prior |
| `spread_cues` | count of spread-language hits |

All descriptive. Label: operational measurement on text → treat as **INFERRED**.

## Prediction v0 (`predict_virality` → `analysis.virality.prediction`)

Weak forward estimate of near-term hybrid virality from current features.

```json
{
  "predicted_hybrid": 0.72,
  "baseline_hybrid": 0.61,
  "delta_vs_baseline": 0.11,
  "horizon": "short",
  "confidence": 0.55,
  "method": "feature_blend_v0",
  "provenance": "SPECULATIVE",
  "note": "Not a settled forecast; not Brier-eligible without settlement design."
}
```

### Rules
- Lives under **analysis**, not calibration forecasts (no `virality.predicted` signal_key yet)
- Never sets `provenance.brier`
- Does not auto-settle

### Inputs
hybrid, velocity, acceleration, lineage confidence, hyperstition stage, memetic score, neologism count

## Community drivers (`trace_semantic_variation`)

Multi-label drivers (arXiv-inspired tags):

- `communicative_need`
- `semantic_distinction`
- `community_identity`
- `platform_compression`
- `status_competition`
- `risk_signaling`

Output includes `driver` (joined string, back-compat) and `drivers` (list).
