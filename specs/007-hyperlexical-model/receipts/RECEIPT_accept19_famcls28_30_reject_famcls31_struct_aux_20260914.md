# RECEIPT — accept19 famcls28–30 REJECT; famcls31 struct-aux climb (2026-09-14)

**Authority:** Spec 007. SHADOW / `name_gate=false`. BEST untouched.

## Pins after this receipt
- **Weights:** `~/hlx-private/p1-structure-unbind-famcls25-20260914/` (still last KEEP)
- **Data:** `~/hlx-private/p1-classify-accept19-20260914/prepare`
- **BEST:** morph19

## Gates

### famcls28 — REJECT
- N=8, encoder LR **1e-5**: family **0.9598**, structure/pointer **0.958**

### famcls29 — REJECT
- N=8, encoder LR **5e-6**: family **0.9195**, structure/role/pointer **1.0**

### famcls30 — REJECT
- N=8, encoder LR **7.5e-6**: family **0.9195**, structure/pointer **0.958**
- Mid-LR got the worst of both sides; val structure guard inert (~0.8125)

### famcls31 — IN FLIGHT
- N=8, encoder LR **1e-5**, frozen-head **structure aux** (role+pointer CE, STRUCT_UPSAMPLE=4)
- Same gate: family > 0.9367816091954023 AND structure/role/pointer == 1.0
- Path: `~/hlx-private/p1-structure-unbind-famcls31-20260914/`

## Protocol note
Stop thrashing LR alone. Re-anchor encoder with structure aux through frozen heads while using the family-lifting LR.
