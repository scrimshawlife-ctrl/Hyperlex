# RECEIPT — agent classify accept4 + famcls7 reject (2026-09-14)

**Authority:** Spec 007. Operator unlocked agent classification ownership.
**BEST:** untouched (morph19). `name_gate` false. No Hub.

## Classification accept4 (agent-owned)

Parent: accept3 prepare.

| decision | n | notes |
|----------|---|-------|
| accept gaming salvage | 21 | clean lexicon over-rejected in accept3 |
| accept none controls | 110 | agent-seeded everyday English (non-slang) |
| **promoted total** | **131** | |

Promoted prepare: `~/hlx-private/p1-classify-accept4-20260914/prepare`.
Joke inferred-`none` euphemisms remain rejected.

## Fair eval (accept4-test)

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls (baseline) | **1.0** | **1.0** | **1.0** | 0.545 |
| famcls7 | 0.917 | 1.0 | 0.917 | **0.618** |

## famcls7 verdict

**REJECT.** Family cleared (+0.073) but structure/pointer hold failed.
Selection: `last_epoch_fallback` (val never met family floor 0.68).
BEST unchanged.

## Pins after this job

- **Data:** accept4 prepare (now has real `none` coverage)
- **Weights:** famcls joint (unchanged keep)
- **Policy:** hard pause on joint CE thrash that spends structure

## Artifacts (Spark private)

- `~/hlx-private/p1-classify-accept4-20260914/`
- `~/hlx-private/p1-structure-unbind-famcls7-20260914/{REJECTED.md,SMOKE_SUMMARY.json,out/}`
