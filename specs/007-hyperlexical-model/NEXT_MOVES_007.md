# Spec 007 — status after structure recipe change (unbind pointer)

**Authority:** Spec 007 only. `name_gate` stays false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 pin — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Done this turn

- Operator **"continue"** after expanded-gold holdout miss: **changed structure recipe**
  (not more whitespace-`pos_i` gold).
- Diagnosis: closed-vocab filler CE cannot hit OOV holdout fillers (~65% OOV).
- New recipe on same expanded dual prepare: CLS+slot **unbind** with **role CE** +
  **filler span-pointer** (no closed-vocab filler CE). Schemes still `positional` |
  `type_slot` only. New out
  `~/hlx-private/p1-structure-unbind-pointer-20260914/out`.
- Holdout: `structure_exact=0.375`, `role_exact=0.375`,
  `filler_pointer_exact=1.0`, `family_exact≈0.676` (n_structure=24).
- Val: `structure_exact=0.3125`, `role_exact=0.3125`,
  `filler_pointer_exact=0.875`, `family_exact≈0.629`.
- Prior expanded closed-vocab holdout structure was **0.0** — pointer recipe
  restores holdout signal; **role unbind is now the bottleneck**.
- `best_overwrite=false`; `best_unchanged=true`; BEST morph19 path+mtime unchanged.
- OBSERVED `partial_slot_miss` still policy hold. Envelope morphs remain exhausted.

## Compare

| run | recipe | structure holdout | filler holdout | role holdout |
|-----|--------|-------------------|----------------|--------------|
| dual expanded | closed-vocab filler CE | 0.0 | 0.0 | — |
| **unbind pointer** | **role CE + span pointer** | **0.375** | **1.0** | **0.375** |

## Private paths (Spark)

- prepare (reused) `~/hlx-private/p1-structure-dual-expanded-prepare-20260914/`
- out `~/hlx-private/p1-structure-unbind-pointer-20260914/`

## Next

1. Improve **role unbind** under the pointer recipe (bottleneck).
2. OBSERVED `partial_slot_miss` policy decision (default hold).
3. Hold envelope-only morphs. Never overwrite BEST without explicit approval.
