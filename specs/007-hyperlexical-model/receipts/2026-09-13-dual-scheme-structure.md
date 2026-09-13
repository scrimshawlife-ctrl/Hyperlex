# Receipt — dual-scheme structure ModernBERT (2026-09-13)

SHADOW / `name_gate=false`. No Hub. No BEST overwrite.

This receipt mirrors the dual-scheme entry appended to `training-recovery.md`.

### Dual-scheme (positional + type_slot) ModernBERT seed (2026-09-13)

- Operator **"merge and continue"** after type_slot seed: merged Spec-locked
  schemes on the **same** 33 multitoken spans — each structure example cloned as
  `__positional` (`pos_0`/`pos_1`) and `__typeslot` (`TOKEN`/`SLOT`). Family CE
  only on positional/base copies (avoid double-counting family loss).
- Prepare: `~/hlx-private/p1-structure-dual-prepare-20260913/` →
  `PACKAGE_VERIFIED` / `PREPARED_NOT_RUNNABLE`, blockers `[]`; structure
  train=50 / val=16; role vocab includes `SLOT`, `TOKEN`, `pos_0`, `pos_1`.
- ModernBERT train into **new**
  `~/hlx-private/p1-structure-dual-modernbert-20260913/out` (12 epochs, batch 8,
  struct upsample 4, GPU docker). Container exit 0.
- Val: `structure_exact=0.625` (n_structure=16), `family_exact≈0.737`
  (n_family=38). Matches positional-only ModernBERT seed; recovers from
  type_slot-only `0.5` while co-training both schemes.
- `best_overwrite=false`; `best_unchanged=true`; BEST morph19 path+mtime
  unchanged; `name_gate=false`.
- Private operator card:
  `~/hlx-private/p1-structure-dual-modernbert-20260913/OPERATOR_CARD.md`.
- OBSERVED `partial_slot_miss` remains policy hold. Envelope morphs exhausted.

Remaining ordered execution tasks:
1. Optional longer dual climb / holdout probe into a **new** out dir.
2. Decide SoT OBSERVED `partial_slot_miss` policy (default hold).
3. Hold further envelope-only morphs. Never overwrite BEST without explicit approval.

Provenance: operator "merge and continue" + dual prepare package +
ModernBERT `SMOKE_SUMMARY.json` on Spark 2026-09-13.
