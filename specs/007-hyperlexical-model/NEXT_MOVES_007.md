# Spec 007 — famcls8 frozen-head rejected; stop CE variants without new gold

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins

| pin | path | note |
|-----|------|------|
| **weight joint** | `~/hlx-private/p1-structure-unbind-famcls-20260914/` | structure/role/pointer **1.0** |
| **data pin** | `~/hlx-private/p1-classify-accept4-20260914/prepare` | +none controls + gaming salvage |
| structure reference | `~/hlx-private/p1-structure-unbind-famsel-20260914/` | prior structure-line keep |

Accept4-test famcls baseline family **≈0.545** (structure 1.0).

## Rejected weight resumes (recent)

| run | recipe | family vs baseline | structure |
|-----|--------|--------------------|-----------|
| famcls6 | joint CE (accept3) | 0.633 > 0.612 | 0.875 FAIL |
| famcls7 | joint CE (accept4) | 0.618 > 0.545 | 0.917 FAIL |
| **famcls8** | **frozen trunk + family head (accept4)** | **0.473 < 0.545** | **1.0 HOLD** |

Frozen-head preserves structure but **does not** beat famcls family on accept4-test.

## Policy

1. OBSERVED `partial_slot_miss`: **hold**
2. No BEST overwrite
3. **Stop** further famclsN CE / head / sampler variants on current gold
4. Agent may still classify new queues when they appear
5. Do not invent OBSERVED structure gold

## What would unlock the next weight resume

One of:
- New reviewed minority / hard-family gold beyond accept4
- New reviewed structure gold (not invented)
- A **pre-registered** recipe that is not another inv-freq family-head or joint CE clone

Until then: **weight work paused**. Classification ownership remains active for new queues.
