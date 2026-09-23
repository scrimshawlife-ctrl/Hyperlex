# Hyperlex status

**Naming:** repo **Hyperlex** is the transitional monorepo shell. Public products: **Hyperlexical** (Spec 007 model / train / eval / E2 / `name_gate` claim) and **ne0l0gist** (slang ingest). `name_gate` remains false.

**Version:** 0.4.0  
**Observed:** 2026-09-12  
**Posture:** Hermes skill = current operator surface. Spec 007 = model path (SHADOW). Spark BEST = `seed-morph65` (**PROMOTE**). morph73 **IN FLIGHT** (`INIT_EXPAND_VOCAB=1` warm morph65; UPSAMPLE=10 held). morph72 REJECT (UPSAMPLE=10 non-warm best 0.9532 < fair 0.9649 n=171). `name_gate` still false.

## Spec 007 — honest gates

SHADOW / advisory. Spark BEST = **`seed-morph65`**. morph68–72 REJECT. morph73 expand-warm train live. `name_gate=false`.

## Recommended next

1. Spark BEST = **morph65** (held). **morph73 IN FLIGHT** — `INIT_EXPAND_VOCAB=1` warm morph65 on morph72 force/hard; fair **0.9649122807017544** n=171; container `hlx-train-morph73-1790148566`. See `NEXT_MOVES_007.md` / `receipts/20260923-morph73-expand-warm-inflight.md`.
2. Burn-in offline runs + settle path.
3. Do not Hub-upload. Do not flip `name_gate`.
