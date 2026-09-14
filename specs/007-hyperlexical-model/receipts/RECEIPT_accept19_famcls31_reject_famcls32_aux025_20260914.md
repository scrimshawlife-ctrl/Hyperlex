# RECEIPT — accept19 famcls31 REJECT; famcls32 aux=0.25 climb (2026-09-14)

**Authority:** Spec 007. SHADOW / `name_gate=false`. BEST untouched.

## Pins after this receipt
- **Weights:** `~/hlx-private/p1-structure-unbind-famcls25-20260914/`
- **Data:** `~/hlx-private/p1-classify-accept19-20260914/prepare`
- **BEST:** morph19

## famcls31 — REJECT
- N=8, LR 1e-5, STRUCT_UPSAMPLE=4, AUX=**1.0**
- Holdout: family **0.9023**, structure/role/pointer **1.0**
- Structure aux works; family suppressed vs baseline 0.9368 and vs famcls28 0.9598

## famcls32 — IN FLIGHT
- Same recipe with AUX=**0.25**
- Path: `~/hlx-private/p1-structure-unbind-famcls32-20260914/`
