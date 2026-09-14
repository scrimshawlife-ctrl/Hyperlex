# Spec 007 — status after pointer-rebalance climb

**Authority:** Spec 007 only. `name_gate` stays false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 pin — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Done this turn

- Operator **merge and continue as recommended** after scheme role climb.
- Climb: pointer rebalance under scheme conditioning (role CE×1.5, pointer CE×1.5,
  24 ep, seed 21) with best-val selection by `structure_exact`.
  Out `~/hlx-private/p1-structure-unbind-ptrbal-20260914/out`.
- Holdout (selected ep0): `structure_exact=0.875`, `role_exact=1.0`,
  `filler_pointer_exact=0.875`, **`family_exact=0.0`**.
- Vs scheme last-epoch holdout: structure/pointer slightly higher, but family
  collapsed because structure-only early-stop picked epoch 0.
- **Verdict:** not a joint promotion. **Keep scheme out** as working checkpoint.
- `best_overwrite=false`; `best_unchanged=true`; BEST morph19 unchanged.
- OBSERVED `partial_slot_miss` still policy hold.

## Compare

| run | structure holdout | role | pointer | family |
|-----|-------------------|------|---------|--------|
| unbind pointer | 0.375 | 0.375 | 1.0 | ≈0.676 |
| scheme unbind (keep) | ≈0.833 | 1.0 | ≈0.833 | ≈0.676 |
| ptrbal best-val | **0.875** | 1.0 | 0.875 | **0.0** |

## Private paths (Spark)

- prepare (reused) `~/hlx-private/p1-structure-dual-expanded-prepare-20260914/`
- **working joint** `~/hlx-private/p1-structure-unbind-scheme-20260914/`
- ptrbal probe `~/hlx-private/p1-structure-unbind-ptrbal-20260914/`

## Next

1. Further climbs: family-aware selection / last-epoch under balanced weights — never structure-only early-stop.
2. OBSERVED `partial_slot_miss` policy decision (default hold).
3. Hold envelope-only morphs. Never overwrite BEST without explicit approval.
