# Classification v5 — Stage-A two-stage decision graph (design freeze)

```text
RULE = HYPERLEX_V5_STAGE_A_TWO_STAGE_DECISION_GRAPH_V1
DESIGN_STATE = FROZEN
TRAIN = false
TRAIN_AUTHORIZED = false
DATASET = V1R9_UNCHANGED (8d4be830…)
BEST = UNCHANGED (9fba0f66…)
RESERVE = unused
PARENT = HLX-CLASSIFICATION-V5-STAGE-A-004
PARENT_PRIMARY_DECISION = STAGE_A_ARCHITECTURE_REDESIGN_REQUIRED
PARENT_FLAT_SELECTED = 82840630…
EXPERIMENT = HLX-CLASSIFICATION-V5-STAGE-A-005-TWO-STAGE
FLAT_HEAD = DEPRECATED_FOR_V5_STAGE_A_CANONICAL_DECISION
```

Spec-only architectural factorization. No train. No V1R9/label/reserve/BEST
mutation. Flat-head Stage-A-001..004 artifacts retained as historical evidence
(not rewritten).

## 1. Canonical graph

```text
input
  -> shared encoder
  -> Gate 1: NO_EVIDENCE vs POSSIBLE_EVIDENCE
      |
      +-- NO_EVIDENCE -> NONE
      |
      +-- POSSIBLE_EVIDENCE
             -> Gate 2: CONFIRMED_PRESENT vs UNCERTAIN
                    |
                    +-- CONFIRMED_PRESENT -> EVIDENCE_PRESENT
                    |
                    +-- UNCERTAIN -> ABSTAIN (canonical UNCERTAIN)
```

Canonical semantic outputs remain:

```text
NO_EVIDENCE
EVIDENCE_PRESENT
UNCERTAIN
```

## 2. Gold mapping (frozen contract unchanged)

### Gate 1 (all Stage-A rows)

| Gold | Target |
|---|---|
| `NO_EVIDENCE` | `0` |
| `EVIDENCE_PRESENT` | `1` (POSSIBLE_EVIDENCE) |
| `UNCERTAIN` | `1` (POSSIBLE_EVIDENCE) |

### Gate 2 (PRESENT / UNCERTAIN gold only)

| Gold | Target |
|---|---|
| `EVIDENCE_PRESENT` | `1` (CONFIRMED_PRESENT) |
| `UNCERTAIN` | `0` |
| `NO_EVIDENCE` | **excluded** from Gate-2 loss |

## 3. Architecture

- One shared ModernBERT encoder
- `gate1_head`: linear `hidden_size → 2`
- `gate2_head`: linear `hidden_size → 2`
- Pooling: `last_hidden_state[:,0]`
- Trainable: last **2** encoder layers + both heads
- Forbidden: MLPs, attention blocks, prototypes, retrieval, family heads
- Do not mutate BEST

## 4. Forward contract

```text
gate1_logits
gate2_logits
gate1_probabilities
gate2_probabilities
```

Gate 2 may be computed for all rows; loss and canonical decision are masked
unless Gate 1 permits entry.

## 5. Loss

```text
L_total = L_gate1 + lambda_gate2 * L_gate2
lambda_gate2 = 1.0
```

Both gates: binary weighted cross-entropy. Provenance multipliers
`OBSERVED=1.0`, `INFERRED=0.5`. Class weights computed independently per gate
on the **train** split via inverse-sqrt effective counts, mean-normalize to 1.0,
clip `[0.50, 2.00]`. No focal loss.

## 6. Inference policy

```text
if P(POSSIBLE_EVIDENCE) < gate1_threshold:
    NO_EVIDENCE
else if P(CONFIRMED_PRESENT) >= gate2_present_threshold:
    EVIDENCE_PRESENT
else:
    UNCERTAIN
```

Do not use one scalar for all three semantic states.

## 7. Threshold grids (validation only)

```text
gate1_threshold ∈ {0.50, 0.55, …, 0.95}   # 10
gate2_present_threshold ∈ {0.50, …, 0.95} # 10
→ 100 combinations; no continuous tuning
```

Selection among pairs that pass all three end-to-end gates:

1. maximize Stage-A macro-F1  
2. maximize PRESENT recall  
3. maximize UNCERTAIN recall  
4. minimize false evidence entry  
5. higher Gate-1 threshold  
6. higher Gate-2 threshold  

If none pass → `SETTLED_FAIL` (do not relax gates).

## 8. Acceptance (end-to-end; unchanged)

```text
false_evidence_entry_rate_on_none <= 0.05
EVIDENCE_PRESENT recall >= 0.70
NO_EVIDENCE recall >= 0.90
```

Component diagnostics (Gate-1 / Gate-2 recalls, false possible-entry, Gate-2
macro-F1) do **not** replace these gates.

## 9. Checkpoint selection (independent of threshold search)

```text
selection_score = 0.50 * Gate1_macro_F1 + 0.50 * Gate2_macro_F1
```

Gate-2 macro-F1 over PRESENT/UNCERTAIN gold only. Tie-break: lower Gate-1
false-entry → higher Gate-2 PRESENT recall → earlier epoch. Restore best.

## 10. Required diagnostics

- Gate-1 / Gate-2 / end-to-end confusion matrices  
- PRESENT FN: blocked at Gate 1 vs rejected at Gate 2  
- NONE FP: leaked through Gate 1 vs both gates  
- UNCERTAIN: blocked / correctly routed / promoted to PRESENT  
- Stratify: OBSERVED/INFERRED, ATOM/PROSE, source, domain, ambiguity_reason  

No-data: Gate-2 with zero eligible → `NO_DATA`; missing prob/logit →
`NOT_COMPUTABLE`; missing gold → `LABEL_MAPPING_INVALID`. No silent zeros.

## 11. Implementation artifacts

| Artifact | Path |
|---|---|
| Spec module | `scripts/shadow/hyperlexical/classification_v5_stage_a_two_stage.py` |
| Train runner (fail-closed) | `scripts/spark/run_classification_v5_stage_a_two_stage_train.py` |
| Config schema | `schemas/classification-v5/stage_a_two_stage_config.v1.schema.json` |
| Auth schema | `schemas/classification-v5/stage_a_two_stage_authorization.v1.schema.json` |
| Train receipt schema | `schemas/classification-v5/stage_a_two_stage_train_receipt.v1.schema.json` |
| Forward schema | `schemas/classification-v5/stage_a_two_stage_forward.v1.schema.json` |
| Tests | `tests/shadow/test_classification_v5_stage_a_two_stage.py` |

## Next action

```text
NEXT_ACTION = AUTHORIZE_V5_STAGE_A_TWO_STAGE_TRAIN_V1
```

Stop. Do not train, authorize, remediate V1R9, retune thresholds, consume
reserve, promote, or move BEST in this execution.

Receipt: `classification-v5-stage-a-two-stage-decision-graph-v1-receipt-20260930.json`
(`631427cc…`).
