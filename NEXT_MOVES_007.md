# Spec 007 — status after expanded structure gold + dual holdout

**Authority:** Spec 007 only. `name_gate` stays false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 pin — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Done this turn

- Operator **"continue as recommended"** after holdout miss: **expanded structure gold**
  (+40 multitoken bases → **62** total), dual-scheme prepare (positional + type_slot),
  12-base holdout, ModernBERT 12-ep train into **new**
  `~/hlx-private/p1-structure-dual-expanded-20260914/out`.
- Val: `structure_exact=0.125` (n=16), `family_exact≈0.686` (n=35).
- Holdout: `structure_exact=0.0` (n=24), `family_exact≈0.676` (n=37).
  Expansion alone did **not** create holdout structure signal.
- `best_overwrite=false`; `best_unchanged=true`; BEST morph19 path+mtime unchanged.
- OBSERVED `partial_slot_miss` still policy hold. Envelope morphs remain exhausted.

## Compare

| run | bases | structure val | structure holdout |
|-----|-------|---------------|-------------------|
| dual merge 12ep | 33 | 0.625 | — |
| dual holdout 12ep | 33 | 0.625 | 0.0 |
| **dual expanded** | **62** | **0.125** | **0.0** |

## Private paths (Spark)

- annotated expanded `~/hlx-private/p1-structure-annotated-expanded-20260914/`
- intake expanded `~/hlx-private/p1-structure-intake-expanded-20260914/`
- prepare `~/hlx-private/p1-structure-dual-expanded-prepare-20260914/`
- out `~/hlx-private/p1-structure-dual-expanded-20260914/`

## Next

1. **Change structure recipe** (not more whitespace-`pos_i` gold / not more epochs on this recipe).
2. OBSERVED `partial_slot_miss` policy decision (default hold).
3. Hold further envelope-only morphs. Never overwrite BEST without explicit approval.
