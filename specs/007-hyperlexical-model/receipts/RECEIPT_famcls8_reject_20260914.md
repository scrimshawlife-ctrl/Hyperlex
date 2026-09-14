# RECEIPT — famcls8 frozen family-head reject (2026-09-14)

**Authority:** Spec 007. Agent classification ownership active.
**BEST:** untouched. `name_gate` false.

## Intent
Structure-preserving family climb after joint CE (famcls6/7) spent structure.

## Recipe
- Init: famcls keep
- Freeze: encoder + structure heads
- Train: family linear head only, inverse-frequency CE, 40 epochs
- Prepare: accept4 (`none` seeded + gaming salvage)

## Pre-registered gate
family > 0.545 (famcls accept4-test) AND structure/role/pointer = 1.0.

## Fair accept4-test

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls baseline | **1.0** | **1.0** | **1.0** | **0.545** |
| famcls8 (best ep4) | **1.0** | **1.0** | **1.0** | 0.473 |

## Verdict
**REJECT.** Structure hold OK; family regresses (−0.073).

## Pins after
- Data: accept4 prepare
- Weights: famcls joint
- Policy: stop CE/head variants without new reviewed gold

## Artifacts
`~/hlx-private/p1-structure-unbind-famcls8-20260914/{REJECTED.md,SMOKE_SUMMARY.json,out/,GATE.md}`
