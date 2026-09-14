# Spec 007 — status after dual-scheme structure holdout probe

**Authority:** Spec 007 only. `name_gate` stays false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 pin — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Done this turn

- Operator **"continue"** after dual climb plateau: structure **holdout probe**.
  Carved 6 train structure bases (12 dual rows) into `split=test`; retrained Dual
  ModernBERT (12 epochs) into **new** out
  `~/hlx-private/p1-structure-dual-holdout-20260914/out`.
- Val: `structure_exact=0.625` (n=16), `family_exact≈0.737` (n=38) — same plateau.
- **Holdout test:** `structure_exact=0.0` (n=12), `family_exact≈0.742` (n=31).
  Val structure score does **not** generalize to held-out bases.
- `best_overwrite=false`; `best_unchanged=true`; BEST morph19 path+mtime unchanged.
- OBSERVED `partial_slot_miss` still policy hold. Envelope morphs remain exhausted.

## Compare

| run | structure val | structure holdout | notes |
|-----|---------------|-------------------|-------|
| dual merge 12ep | 0.625 | — | first dual |
| dual climb 36ep | 0.625 | — | plateau |
| **dual holdout** | **0.625** | **0.0** | val ≠ generalization |

## Private paths (Spark)

- holdout prepare `~/hlx-private/p1-structure-dual-holdout-prepare-20260914/`
- holdout out `~/hlx-private/p1-structure-dual-holdout-20260914/`
- prior dual climb / merge packages unchanged under `~/hlx-private/p1-structure-dual-*-20260913/`

## Next

1. Expand structure gold or change structure recipe — **not** another epoch climb on these 33 bases.
2. OBSERVED `partial_slot_miss` policy decision (default hold).
3. Hold further envelope-only morphs. Never overwrite BEST without explicit approval.
