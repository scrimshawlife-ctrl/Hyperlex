# Spec 007 — status after scheme-conditioned role unbind climb

**Authority:** Spec 007 only. `name_gate` stays false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 pin — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Done this turn

- Operator **"okay continue"** after pointer recipe: finish docs push, then **role unbind climb**.
- Diagnosis: dual-scheme gold assigns conflicting roles to the same text
  (`pos_0/pos_1` vs `TOKEN/SLOT`). Unconditioned CLS+slot query had a hard ceiling
  near `role_exact≈0.375`.
- Climb: Spec-locked **scheme embedding** in the unbind query
  (`CLS + slot_embed + scheme_embed`); role CE×2; pointer CE×0.5; 18 ep; seed 14.
  New out `~/hlx-private/p1-structure-unbind-scheme-20260914/out`.
- Holdout: `structure_exact≈0.833`, `role_exact=1.0`,
  `filler_pointer_exact≈0.833`, `family_exact≈0.676` (n_structure=24).
- Val: `structure_exact=0.6875`, `role_exact=1.0`,
  `filler_pointer_exact=0.6875`, `family_exact≈0.657`.
- Prior unconditioned pointer holdout structure/role were **0.375** — scheme
  conditioning clears the role bottleneck.
- `best_overwrite=false`; `best_unchanged=true`; BEST morph19 path+mtime unchanged.
- OBSERVED `partial_slot_miss` still policy hold. Envelope morphs remain exhausted.

## Compare

| run | recipe | structure holdout | role holdout | filler holdout |
|-----|--------|-------------------|--------------|----------------|
| dual expanded | closed-vocab filler CE | 0.0 | — | 0.0 |
| unbind pointer | role CE + span pointer | 0.375 | 0.375 | 1.0 |
| **scheme unbind** | **+ scheme_embed** | **≈0.833** | **1.0** | **≈0.833** |

## Private paths (Spark)

- prepare (reused) `~/hlx-private/p1-structure-dual-expanded-prepare-20260914/`
- prior pointer `~/hlx-private/p1-structure-unbind-pointer-20260914/`
- scheme climb `~/hlx-private/p1-structure-unbind-scheme-20260914/`

## Next

1. Optional pointer rebalance / early-stop (role solved; pointer traded slightly).
2. OBSERVED `partial_slot_miss` policy decision (default hold).
3. Hold envelope-only morphs. Never overwrite BEST without explicit approval.
