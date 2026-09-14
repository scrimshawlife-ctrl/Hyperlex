# REJECTED — famcls2 floor/sampler tweak (2026-09-14)

**Authority:** Spec 007. `name_gate=false`. **BEST untouched**.

## Run

`~/hlx-private/p1-structure-unbind-famcls2-20260914/`

Init: famcls keep. Prepare: classify-expand. Tweak: class-balance family upsample + `family_floor=0.60`.

## Holdout

| metric | famcls MERGED | famcls2 | Δ |
|--------|---------------|---------|---|
| structure_exact | **1.0** | 0.958 | **-0.042** |
| role_exact | **1.0** | 1.0 | 0 |
| filler_pointer_exact | **1.0** | 0.958 | **-0.042** |
| family_exact | 0.690 | **0.786** | +0.095 |

Selection: `last_epoch_fallback` — val family never cleared floor 0.60 (max **0.55**).

## Verdict

**REJECT.** Family gain does not pay for structure/pointer regression. Keep gate requires structure/role/pointer hold.

Working joint remains **famcls**.

## Next

1. Explicit review of INFERRED / golden-term queues (esp. `none`) before more family climbs
2. No further CE/sampler thrash on current gold
3. OBSERVED `partial_slot_miss` hold; no BEST overwrite
