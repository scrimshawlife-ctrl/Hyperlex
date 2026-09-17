# Spec 007 — morph45 RELAUNCH IN FLIGHT; BEST=morph40 held

**Authority:** Spec 007 only. `name_gate` false. No Hub. **Labeler authorized.** No invent beyond labeled set.  
**BEST held:** **morph40** — fair n=228 `unbind_exact≈0.7368` (ep9). morph36 preserved.

## Status

Warm-only morph41/42 REJECT. Residual-gold morph43/44 REJECT; high-conf gold **exhausted** (escalate).  
**morph45 attempt 1:** intent LEGAL (`HEAD_SLOT=3` on morph40 gold) but Spark `loop.py` was a 471-line regression → **BLOCKED**; train stopped; code restored.  
**morph45 attempt 2 (relaunch):** same intent card on **restored** Spark `loop.py` (711 lines; INIT_FROM + SAVE_BEST + FORCE_TRAIN confirmed in-container). Container `hlx-train-morph45-1789620853`. Single gate: this relaunch agent (`bc-cc8b0f28…`). Escalate peer `bc-9ecde051…` RUNNING with empty transcript — not owning train/gate.

## Fair surface (documented)

| field | value |
|-------|------:|
| Force-train | `force_train_morph40_expanded.jsonl` (**135**) |
| Hard atoms | `hard_atoms_train_morph40.jsonl` (**180**) |
| Val after force-train | **n=228** (unchanged vs morph40; morph41 receipt `n_unbind_val_after_force_train=228`) |
| Fair baseline | morph40 BEST **0.7368421052631579** |
| Recompute fair? | **No** — val surface matches morph40 force set |

Promote iff best `unbind_exact` **> 0.7368** on n=228; else REJECT; BEST stays morph40.

## Next

Poll morph45 to 40ep. Gate best > 0.7368 on n=228 → promote; else REJECT. Preserve morph40/morph36.

## Policy

`name_gate=false`. Fair-eval when val changes (unchanged here — morph40 surface). No invent beyond labeled set.
