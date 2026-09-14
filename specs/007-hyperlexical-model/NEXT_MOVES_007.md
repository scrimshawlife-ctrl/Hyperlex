# Spec 007 — accept9 gold in; famcls14 rejected; weights stay famcls13

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins

| pin | path | note |
|-----|------|------|
| **weight joint (family-line)** | `~/hlx-private/p1-structure-unbind-famcls13-20260914/` | **KEEP**; last-N encoder on accept8 |
| **data pin** | `~/hlx-private/p1-classify-accept9-20260914/prepare` | accept8 + **+174** residual-miss contrastive |
| prior keep | `~/hlx-private/p1-structure-unbind-famcls12-20260914/` | ancestry |
| structure reference | `~/hlx-private/p1-structure-unbind-famsel-20260914/` | prior structure-line keep |

## This pass

1. Merged famcls13 KEEP; dumped accept8-test (27 mistakes; brainrot/ai/crypto shorts → gaming).
2. **accept9:** +174 residual-miss contrastive surfaces.
3. Fair famcls13 on accept9-test: family **0.615**, structure/role/pointer **1.0**.
4. **famcls14** last-N=2 init famcls13:

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls13 baseline | 1.0 | 1.0 | 1.0 | **0.615** |
| famcls14 | 1.0 | 1.0 | 1.0 | 0.615 |

**REJECT** famcls14 (tie; gate needs strict >). Structure hold succeeded.

## Policy

1. OBSERVED `partial_slot_miss`: **hold**
2. No BEST overwrite
3. Keep **famcls13** weights; keep **accept9** data
4. Pause identical last-N=2 inv-freq clones on near-duplicate residual gold
5. Next unlock: harder reviewed contrastive pairs **or** new pre-registered recipe (last-N=4 / LR schedule / joint)

## Next

- Do not thrash famcls15 with the same last-N=2 recipe
- Optional dump famcls13 on accept9-test for targeting
- Hold envelope morphs / BEST overwrite until ladder 0.55 has a real plan
