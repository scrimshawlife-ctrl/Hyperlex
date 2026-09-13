# Spec 007 — status after type_slot structure upgrade

**Authority:** Spec 007 only. `name_gate` stays false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 pin — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Done this turn

- Operator **"go ahead and continue"** on role upgrade: remapped existing spans
  `pos_i` → Spec-locked **`type_slot`** tags (`TOKEN`/`SLOT` by index). Span
  boundaries unchanged. Free-form gloss roles rejected (schemes locked:
  `positional` | `type_slot` only).
- Intake **33/33**; prepare verified; ModernBERT structure(+family) train into
  **new** out `~/hlx-private/p1-structure-typeslot-modernbert-20260913/out`.
- Final val: `family_exact≈0.763`, `structure_exact=0.5` (n_structure=8).
  Below prior positional seed (`0.625`) — expected under non-redundant tags.
- `best_overwrite=false`; BEST morph19 path+mtime unchanged.
- OBSERVED `partial_slot_miss` still policy hold. Envelope morphs remain exhausted.

## Private paths (Spark)

- typeslot worksheet `~/hlx-private/p1-structure-typeslot-20260913/`
- intake `~/hlx-private/p1-structure-typeslot-intake-20260913/`
- prepare `~/hlx-private/p1-structure-typeslot-prepare-20260913/`
- modernbert out `~/hlx-private/p1-structure-typeslot-modernbert-20260913/`

## Next

1. Optional: longer type_slot ModernBERT climb / holdout probe into another **new** out dir.
2. Optional: dual-scheme gold (positional + type_slot) if unbind curriculum needs both.
3. OBSERVED `partial_slot_miss` policy decision (default hold).
Hold further envelope-only morphs. Never overwrite BEST without explicit approval.
