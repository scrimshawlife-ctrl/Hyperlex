# morph45 — recipe HEAD_SLOT=3 BLOCKED (was IN FLIGHT 2026-09-16)

**CLOSED 2026-09-17:** invalid Spark `loop.py` (ignored INIT_FROM/SAVE_BEST/FORCE_TRAIN). Train stopped. BEST=morph40. See `BLOCKED_INVALID_LAUNCH.md`.

# (original card below)

**Authority:** Spec 007. `name_gate=false`. Labeler authorized. No invent beyond labeled set.  
**BEST held:** **morph40** (`unbind_exact≈0.7368` ep9, fair val n=228). morph36 preserved.

## Lever (one card)

| field | value |
|-------|-------|
| Family | `recipe_head_slot_weight` |
| **Delta** | `HYPERLEX_UNBIND_HEAD_SLOT_WEIGHT=3` (morph40/morph19 envelope = **2**) |
| Init | warm `HYPERLEX_INIT_FROM=morph40` + `SAVE_BEST_UNBIND=1` |
| Gold | morph40 surface only — force-train **135**, hard_atoms **180** (`hard_atoms_train_morph40.jsonl`) |
| Val | n=**228** (unchanged vs morph40 BEST) |
| Epochs / batch / LR | 40 / 8 / 2e-5 |
| mem_fraction | **0.3 exclusive** (Qwen stopped for climb) |
| Hold | slot_ce, OBSERVED=2, HARD=4, INFERRED=1.0, CAP=0, POS=1 TYPE=1, LAST=4, margin=0.5, loss=1.0 |

**Not** a warm+force residual-gold clone (escalate forbids morph45-style residual warm+force). Recipe delta only; no new gold; no abstain reopen; famcls52 still saturated — skipped.

## Why this lever

Post-morph40/41/42 residuals still dominated by `positional_head_filler_miss` / `partial_slot_miss`. morph19 itself cleared a ladder rung with HEAD_SLOT **1→2**. Escalate asks for head-slot / curriculum / LR / last-N — HEAD_SLOT=3 is the justified next recipe step on the fair morph40 surface.

## Fair gate

Promote morph45→BEST iff best `unbind_exact` **> 0.7368421052631579** on same val n=228. Else **REJECT_VS_BEST**; BEST stays morph40; morph36 untouched.

## Artifacts (Spark)

- Out: `~/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph45`
- Private: `~/hlx-private/p1-spark-morph45-40ep-head-slot3-20260916/`
