# Spec 007 — status after dual-scheme longer climb

**Authority:** Spec 007 only. `name_gate` stays false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 pin — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Done this turn

- Operator **"merge and continue as recommended"** after dual merge: longer dual-scheme
  ModernBERT climb on the **same** prepare (positional + type_slot) into **new** out
  `~/hlx-private/p1-structure-dual-climb-20260913/out` (36 epochs, GPU).
- Final val: `structure_exact=0.625` (n_structure=16), `family_exact≈0.737`
  (n_family=38). Plateau matches the 12-epoch dual merge — no structure lift from
  the extra epochs (0.625 reached by epoch 2 and held).
- `best_overwrite=false`; `best_unchanged=true`; BEST morph19 path+mtime unchanged.
- OBSERVED `partial_slot_miss` still policy hold. Envelope morphs remain exhausted.

## Compare (structure seeds)

| seed | epochs | structure_exact | notes |
|------|--------|-----------------|-------|
| positional-only | — | 0.625 | first structure ModernBERT |
| type_slot-only | — | 0.500 | expected drop after role remap |
| dual merge | 12 | 0.625 | both schemes; val n_structure=16 |
| **dual climb** | **36** | **0.625** | plateau; no lift vs 12-epoch dual |

## Private paths (Spark)

- dual prepare `~/hlx-private/p1-structure-dual-prepare-20260913/`
- dual merge (12ep) `~/hlx-private/p1-structure-dual-modernbert-20260913/`
- dual climb (36ep) `~/hlx-private/p1-structure-dual-climb-20260913/`

## Next

1. Optional: holdout probe into another **new** out dir (or stop climbing this package).
2. OBSERVED `partial_slot_miss` policy decision (default hold).
3. Hold further envelope-only morphs. Never overwrite BEST without explicit approval.
