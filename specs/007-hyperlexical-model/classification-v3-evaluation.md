# Classification v3 — evaluation contract

Preregistered before any v3 training or acquisition results. State: `DRAFT` → `PREREGISTERED` with this document’s frozen gate.

## Surfaces

| Surface | Use |
|---|---|
| validation | calibrate/select evidence thresholds; report all metrics |
| spent v2 reserve | **forbidden** for v3 train/val/promotion |
| future v3 reserve | sealed only after validation passes primary gate |

## Required metrics (fresh validation)

```text
NO_EVIDENCE precision / recall / F1
EVIDENCE_PRESENT precision / recall / F1
UNCERTAIN rate
false_evidence_entry_rate_on_none
family emission precision
family emission coverage
end-to-end NONE precision / recall
end-to-end selective accuracy
```

### Definitions

- **false_evidence_entry_rate_on_none** = among gold `NO_EVIDENCE` (or gold NONE / none-subtype rows), fraction where Stage A returns `EVIDENCE_PRESENT` (retrieval would run).
- **family emission precision** = among end-to-end `FAMILY` decisions, fraction correct.
- **family emission coverage** = `FAMILY` emissions / gold evidence-present family rows.
- **end-to-end selective accuracy** = correct among emitted `FAMILY` ∪ correct `NONE` decisions / all rows that received a decisive `FAMILY` or `NONE` (exclude ABSTAIN/AMBIGUOUS from denominator, report rates separately).

## Primary gate (preregistered)

```text
false_evidence_entry_rate_on_none <= 0.05
```

Frozen at design time. **Not** fitted from spent v2 reserve statistics.  
If this gate fails, downstream family metrics **cannot** authorize a new reserve evaluation.

Secondary (only after primary gate passes): family emission precision ≥ 0.80 on validation (same product reliability floor as v2 selective intent, but now after evidence entry is controlled).

## Authorization ladder

```text
validation false_evidence_entry_rate_on_none <= 0.05
  AND validation family emission precision >= 0.80
  AND applicability/evidence invariance checks pass
=> may authorize sealing a NEW v3 reserve
=> one-shot reserve score under frozen thresholds
=> SETTLED_PASS | SETTLED_FAIL | SETTLED_INVALID
```

No reserve-derived threshold search. No per-family validation threshold tuning.

## Prohibited evaluation behaviors

```text
retune thresholds after seeing spent v2 reserve
use spent v2 reserve as promotion surface
force 18-way macro-F1 as primary success metric
ignore UNCERTAIN rate / force it into PRESENT
```
