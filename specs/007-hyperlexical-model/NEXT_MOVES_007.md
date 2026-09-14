# Spec 007 — status after family-climb probe

**Authority:** Spec 007 only. `name_gate` stays false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 pin — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Done this turn

- Operator **continue** after famsel keep: family climb under structure floor
  (family CE×3, structure_floor=0.75, 24 ep, seed 35).
  Out `~/hlx-private/p1-structure-unbind-famclimb-20260914/out`.
- Holdout: structure≈0.833, role=1.0, pointer≈0.833, family≈0.676.
- Vs famsel keep (structure/role/pointer=1.0, family≈0.676): family flat;
  structure/pointer **regressed**.
- **Verdict: reject.** Working joint remains famsel.
- `best_overwrite=false`; `best_unchanged=true`; BEST morph19 unchanged.
- OBSERVED `partial_slot_miss` still policy hold.

## Compare

| run | structure holdout | role | pointer | family |
|-----|-------------------|------|---------|--------|
| **famsel (keep)** | **1.0** | **1.0** | **1.0** | **≈0.676** |
| famclimb (reject) | ≈0.833 | 1.0 | ≈0.833 | ≈0.676 |

## Private paths (Spark)

- **working joint** `~/hlx-private/p1-structure-unbind-famsel-20260914/`
- famclimb reject `~/hlx-private/p1-structure-unbind-famclimb-20260914/`
- prepare (reused) `~/hlx-private/p1-structure-dual-expanded-prepare-20260914/`

## Next

1. OBSERVED `partial_slot_miss` policy decision (default **hold**).
2. Hold envelope-only morphs. Never overwrite BEST without explicit approval.
3. Do not re-litigate family CE upweight without a new recipe or gold change — holdout family plateaus while structure pays.
