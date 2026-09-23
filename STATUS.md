# Hyperlex status

**Naming:** repo **Hyperlex** is the transitional monorepo shell. Public products: **Hyperlexical** (Spec 007 model / train / eval / E2 / `name_gate` claim) and **ne0l0gist** (slang ingest). `name_gate` remains false.

**Version:** 0.4.0  
**Observed:** 2026-09-12  
**Posture:** Hermes skill = current operator surface. Spec 007 = model path (SHADOW). Spark BEST = `seed-morph65` (**PROMOTE** — 0.8584070796460177 ep6 > fair morph63 0.8539823008849557 n=226; E2 PASS). morph71 **REJECT_VS_BEST** (non-warm best 0.9591 < fair 0.9649 n=171). `name_gate` still false.
**Install:** `bash install.sh` → `~/.hermes/skills/hyperlex`  
**Claude (optional):** `bash install.sh --claude` → `~/.claude/skills/hyperlex`  
**Track:** Phases 0–4 complete · Phase 5.0–5.3 · Pages static run history · Spec 007 SHADOW encoder on main

This file is the operator snapshot. The docs site copies it to [status](https://scrimshawlife-ctrl.github.io/Hyperlex/status/). Do not treat it as a Hub card or a Brier score.

## Spec 007 — honest gates

SHADOW / advisory. Spark BEST = **`seed-morph65`**. morph68–71 REJECT. Residual AUTHORIZE=0 — hold. `name_gate=false`.

## Recommended next

1. Spark BEST = **morph65** (held). **morph71 REJECT_VS_BEST** — best **0.9590643274853801** < fair **0.9649122807017544** n=171. E2 PASS. Non-warm role-vocab expand **force_added=23** did not beat fair. Residual AUTHORIZE=0 — **hold**. See `NEXT_MOVES_007.md` / `receipts/20260922-morph71-40ep-reject-vs-best.md`.
2. Burn-in offline runs + settle path (this is how Brier becomes real).
3. Do not Hub-upload. Do not flip `name_gate`.
