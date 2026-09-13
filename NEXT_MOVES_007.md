# Spec 007 — status after dual-scheme structure merge

**Authority:** Spec 007 only. `name_gate` stays false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 pin — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Done this turn

- Operator **"merge and continue"**: dual-scheme gold on the **same spans** —
  Spec-locked `positional` (`pos_0`/`pos_1`) **and** `type_slot` (`TOKEN`/`SLOT`).
  Prepare clones each structure row as `__positional` + `__typeslot` (66 structure
  rows; family loss only on positional/base copies to avoid double family CE).
- Prepare: `~/hlx-private/p1-structure-dual-prepare-20260913/` →
  `PREPARED_NOT_RUNNABLE`, blockers `[]`.
- ModernBERT structure(+family) train into **new** out
  `~/hlx-private/p1-structure-dual-modernbert-20260913/out` (12 epochs, GPU).
- Final val: `structure_exact=0.625` (n_structure=16), `family_exact≈0.737`
  (n_family=38). Matches positional-only seed (`0.625`); recovers from
  type_slot-only (`0.5`) while learning both schemes.
- `best_overwrite=false`; `best_unchanged=true`; BEST morph19 path+mtime unchanged.
- OBSERVED `partial_slot_miss` still policy hold. Envelope morphs remain exhausted.

## Compare (structure seeds)

| seed | structure_exact | notes |
|------|-----------------|-------|
| positional-only | 0.625 | first structure ModernBERT |
| type_slot-only | 0.500 | expected drop after role remap |
| **dual merge** | **0.625** | both schemes; val n_structure=16 |

## Private paths (Spark)

- dual prepare `~/hlx-private/p1-structure-dual-prepare-20260913/`
- dual modernbert `~/hlx-private/p1-structure-dual-modernbert-20260913/`
  (operator card + `out/SMOKE_SUMMARY.json`)
- prior typeslot / positional packages unchanged under `~/hlx-private/p1-structure-*-20260913/`

## Next

1. Optional: longer dual climb or holdout probe into another **new** out dir.
2. OBSERVED `partial_slot_miss` policy decision (default hold).
3. Hold further envelope-only morphs. Never overwrite BEST without explicit approval.
