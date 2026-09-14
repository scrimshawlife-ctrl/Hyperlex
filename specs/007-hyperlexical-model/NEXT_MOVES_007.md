# Spec 007 — accept7 gold in; famcls11 hard-neg rejected; weights stay famcls9

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins

| pin | path | note |
|-----|------|------|
| **weight joint (family-line)** | `~/hlx-private/p1-structure-unbind-famcls9-20260914/` | KEEP; structure-frozen head on accept5 |
| **data pin** | `~/hlx-private/p1-classify-accept7-20260914/prepare` | accept6 + **+211** adversarial contrastive surfaces |
| structure reference | `~/hlx-private/p1-structure-unbind-famsel-20260914/` | prior structure-line keep |
| freeze source | `~/hlx-private/p1-structure-unbind-famcls-20260914/` | under famcls9 freeze |

## This pass

1. Hyperlex docs for accept6 / famcls10 REJECT pushed to `main`.
2. Famcls9 dump on accept6-test: family **0.481**, 28 mistakes — `brainrot-aura → gaming-meta` still dominant.
3. **accept7:** +211 adversarial contrastive surfaces (brainrot↔gaming twins, crypto/betting/gaming disambiguators, workplace density, political vs brainrot, framed kinship).
4. Fair famcls9 on accept7-test: family **0.452**, structure/role/pointer **1.0**.
5. **famcls11** NEW hard-neg margin recipe (not inv-freq CE clone):

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls9 baseline | 1.0 | 1.0 | 1.0 | **0.452** |
| famcls11 | 1.0 | 1.0 | 1.0 | 0.435 |

**REJECT** famcls11 (family regress). Structure hold succeeded.

## Policy

1. OBSERVED `partial_slot_miss`: **hold**
2. No BEST overwrite
3. Keep **famcls9** weights; keep **accept7** data
4. Pause further **family-head-only** climbs (inv-freq CE **or** hard-neg) without a recipe that can move encoder representations
5. Agent may still classify; prefer harder contrastive gold or encoder-touching recipes under a new pre-registered gate

## Next unlock

- Encoder-last-N / joint recipe with structure hold pre-registered, **or**
- Harder reviewed contrastive pairs with human review — not more head-only thrash
