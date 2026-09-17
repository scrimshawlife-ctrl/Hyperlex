# morph45 — HEAD_SLOT=3 REJECT_VS_BEST (2026-09-17)

**Authority:** Spec 007. `name_gate=false`.  
**Decision:** **REJECT_VS_BEST** — do not promote. **BEST stays morph40**.

## Scores

| metric | value |
|--------|------:|
| morph45 best `unbind_exact` | **0.7236842105263158** (ep2) |
| morph45 final `unbind_exact` | 0.7105263157894737 (ep39) |
| morph40 fair baseline (n=228) | **0.7368421052631579** |
| Val n after force-train | **228** |
| E2 trunk-forward | **PASS** (`unbind_exact=1.0`) |
| Promote? | **NO** |

## Recipe (legal relaunch)

After attempt1 **BLOCKED** (bad Spark `loop.py`), relaunch used restored loop (712 lines): warm `INIT_FROM=morph40`, `SAVE_BEST_UNBIND=1`, force 135 / hard 180 morph40 paths, `HEAD_SLOT=3`, 40ep, mem 0.3. Confirmed in `config-train.json` (`warm_start=true`, `n_unbind_val_after_force_train=228`).

## Fair surface

**Same morph40 surface — no fair recompute.** See `morph45-40ep-head-slot3-relaunch-20260917/FAIR_SURFACE.md`.

## Artifacts

- Container: `hlx-train-morph45-1789620853` (exit 0)
- Out: `~/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph45`
- Private: `~/hlx-private/p1-spark-morph45-40ep-head-slot3-relaunch-20260917/`
- Package: `receipts/morph45-40ep-head-slot3-relaunch-20260917/`
