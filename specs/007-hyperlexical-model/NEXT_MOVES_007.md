# Spec 007 — status after family-aware selection climb

**Authority:** Spec 007 only. `name_gate` stays false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 pin — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Done this turn

- Operator **continue** after ptrbal reject: family-aware selection under balanced
  scheme unbind (role/pointer CE×1.5, family_floor=0.5, 24 ep, seed 28).
  Out `~/hlx-private/p1-structure-unbind-famsel-20260914/out`.
- Holdout: `structure_exact=1.0`, `role_exact=1.0`, `filler_pointer_exact=1.0`,
  `family_exact≈0.676` (n_structure=24). Selected ep1.
- Clears scheme joint (structure≈0.833) without the ptrbal family collapse.
- `best_overwrite=false`; `best_unchanged=true`; BEST morph19 unchanged.
- OBSERVED `partial_slot_miss` still policy hold.

## Compare

| run | structure holdout | role | pointer | family |
|-----|-------------------|------|---------|--------|
| scheme unbind | ≈0.833 | 1.0 | ≈0.833 | ≈0.676 |
| ptrbal best-val | 0.875 | 1.0 | 0.875 | **0.0** |
| **famsel (keep)** | **1.0** | **1.0** | **1.0** | **≈0.676** |

## Private paths (Spark)

- prepare (reused) `~/hlx-private/p1-structure-dual-expanded-prepare-20260914/`
- **working joint** `~/hlx-private/p1-structure-unbind-famsel-20260914/`
- prior scheme `~/hlx-private/p1-structure-unbind-scheme-20260914/`
- ptrbal reject `~/hlx-private/p1-structure-unbind-ptrbal-20260914/`

## Next

1. OBSERVED `partial_slot_miss` policy decision (default hold).
2. Hold envelope-only morphs. Never overwrite BEST without explicit approval.
3. Optional: probe whether family can climb without regressing structure=1.0 holdout.
