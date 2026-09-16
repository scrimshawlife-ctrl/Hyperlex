# Receipt — labeler authorized for OBSERVED structure gold (2026-09-16)

**Authority:** Operator granted labeler authority **2026-09-16** for Spec 007 Hyperlex civilian `partial_slot_miss` residuals.  
**Schemes:** `positional` | `type_slot` only.  
**BEST:** morph36 (`unbind_exact≈0.5455`). Climb famcls52 separate. `name_gate=false`.

## Decision

Option (1) from `ASK_DANNY.md` — **authorize OBSERVED structure gold** for ranked residual spans under Spec-locked schemes. No freestyle schemes. No invented spans. Conservative abstain on wiki/meta noise.

## Artifacts

| path | note |
|------|------|
| `receipts/danny-gold-review-partial-slot-miss-20260915/METHOD.md` | decision rules |
| `…/labeled_observed_partial_slot_miss.jsonl` | P1 labels (146 rows) |
| `…/LABEL_COUNTS.json` | authorize / abstain tallies + QA |
| `receipts/20260916-labeler-authorized-observed-gold.md` | this receipt |

## Label tallies (P1 `partial_slot_miss`)

| metric | n |
|--------|--:|
| candidates | **146** |
| authorized structure gold | **136** |
| abstain | **10** |
| authorized ∩ OBSERVED (train-ready) | **25** |
| authorized ∩ INFERRED (documentary; no class promote) | **111** |

QA second-pass: all 25 OBSERVED authorized rows re-parsed clean (0 mismatches).

## Train integrate (authorized)

- Force-train OBSERVED authorized exacts via `HYPERLEX_UNBIND_FORCE_TRAIN_PATH` (val→train; fair-eval morph36 on new val).
- Append hard_atoms for authorized OBSERVED surfaces (match existing train OBSERVED only).
- Do **not** auto-promote INFERRED → OBSERVED.
- morph39: init morph36 BEST, `SAVE_BEST_UNBIND=1`, 40ep; promote only if best unbind_exact **> 0.5455**.
