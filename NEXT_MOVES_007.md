# Spec 007 — status after ModernBERT structure seed (post morph34)

**Authority:** Spec 007 only. `name_gate` stays false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 pin — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Done this turn

- Operator **"continue as recommended"**: occurrence-aware ModernBERT structure(+family)
  train from verified prepare into **new** out dir
  `~/hlx-private/p1-structure-modernbert-20260913/out`.
- Realign uses ModernBERT offset_mapping with whitespace-only BPE overhang allowance
  (`align_occurrences_modernbert`); no first-occurrence fallback.
- Final val: `family_exact≈0.763`, `structure_exact=0.625` (n_structure=8).
  Pipeline seed only — not civilian ladder / not BEST pin.
- `best_overwrite=false`; BEST morph19 path+mtime unchanged.
- SoT OBSERVED `partial_slot_miss` pack still policy hold.
- Envelope-only morphs remain exhausted.

## Private paths (Spark)

- prepare `~/hlx-private/p1-structure-prepare-20260913/`
- modernbert train `~/hlx-private/p1-structure-modernbert-20260913/`
- prior reviewed toy smoke `~/hlx-private/p1-structure-train-20260913/`

## Next

1. Danny: accept or upgrade positional `pos_i` gold → semantic roles (optional).
2. Optional longer ModernBERT structure climb / holdout probe into another **new** out dir.
3. OBSERVED `partial_slot_miss` policy decision (default hold).
Hold further envelope-only morphs. Never overwrite BEST without explicit approval.
