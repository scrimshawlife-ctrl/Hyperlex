# RECEIPT — accept19 famcls28/29 REJECT; famcls30 mid-LR climb (2026-09-14)

**Authority:** Spec 007. SHADOW / `name_gate=false`. BEST untouched.

## Pins after this receipt
- **Weights:** `~/hlx-private/p1-structure-unbind-famcls25-20260914/` (still last KEEP)
- **Data:** `~/hlx-private/p1-classify-accept19-20260914/prepare`
- **BEST:** morph19

## Gates

### famcls28 — REJECT
- Recipe: init famcls25, N=8, encoder LR **1e-5**, accept19, 40 ep
- Baseline family: 0.9367816091954023
- Holdout: family **0.9598**, structure/pointer **0.9583**, role 1.0
- Fail: structure/pointer slip despite family lift

### famcls29 — REJECT
- Recipe: init famcls25, N=8, encoder LR **5e-6**, accept19, 40 ep (best epoch 30)
- Holdout: family **0.9195**, structure/role/pointer **1.0**
- Fail: family below baseline; structure held

### famcls30 — IN FLIGHT
- Recipe: init famcls25, N=8, encoder LR **7.5e-6** (mid bracket), accept19, full 40 ep
- Same pre-registered gate: family > 0.9367816091954023 AND structure/role/pointer == 1.0
- Path: `~/hlx-private/p1-structure-unbind-famcls30-20260914/`

## Protocol note
Do not deepen N after famcls27 failure. Prefer LR bracket between the structure-slipping and under-training rates before refreshing gold again.
