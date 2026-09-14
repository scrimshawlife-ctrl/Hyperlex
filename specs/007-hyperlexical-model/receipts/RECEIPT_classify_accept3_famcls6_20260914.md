# RECEIPT — agent classify accept3 + famcls6 reject (2026-09-14)

**Authority:** Spec 007. Operator unlocked agent classification ownership (“you can handle all classification jobs”).
**BEST:** untouched (morph19). `name_gate` false. No Hub.

## Classification (agent-owned)

Source queues:
- `p1-classify-expand-20260914/review_queue_inferred.jsonl` (293)
- remaining `review_queue_inferred_pass.jsonl`

| decision | n | notes |
|----------|---|-------|
| accept | 115 | kinship/gaming lexicon + 7 inferred_pass |
| reject | 174 | joke-`none`, wiki/declension/prose, weak pass |
| skip | 23 | already in train |

Promoted prepare: `~/hlx-private/p1-classify-accept3-20260914/prepare` (599 rows).
`none` class still empty of good controls.

## Fair eval (accept3-test)

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls (baseline) | **1.0** | **1.0** | **1.0** | 0.612 |
| famcls6 | 0.875 | 1.0 | 0.875 | **0.633** |

## famcls6 verdict

**REJECT.** Family cleared (+0.020) but structure/pointer hold failed.
Selection: `last_epoch_fallback` (val never met family floor 0.68).
BEST unchanged.

## Pins after this job

- **Data:** accept3 prepare
- **Weights:** famcls joint (unchanged keep)
- **Policy:** hold OBSERVED `partial_slot_miss`; no CE thrash without new gold

## Artifacts (Spark private)

- `~/hlx-private/p1-classify-accept3-20260914/`
- `~/hlx-private/p1-structure-unbind-famcls6-20260914/{REJECTED.md,SMOKE_SUMMARY.json,out/}`
