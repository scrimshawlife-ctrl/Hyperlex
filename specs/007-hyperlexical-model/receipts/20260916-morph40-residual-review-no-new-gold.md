# morph40 residual review — no new gold (2026-09-16)

**Authority:** Spec 007. Labeler authorized. Schemes `positional` | `type_slot` only. `name_gate=false`.  
**BEST confirmed:** morph40 (`...-seed-morph40`), best unbind_exact **0.7368** ep9 on val **n=228**.

## Civilian residual (morph40 BEST / current val)

| theme | n |
|-------|--:|
| partial_slot_miss | **28** |
| positional_head_filler_miss | 23 |
| type_slot_token_miss | 23 |
| full_miss | 15 |
| morph_bleed | 4 |
| **n_residual** | **60** |

by_class: INFERRED 53 / OBSERVED 7 · by_scheme: positional 35 / type_slot 25

## P1 `partial_slot_miss` label pass

| decision | n |
|----------|--:|
| AUTHORIZE_OBSERVED_STRUCTURE_GOLD | **20** |
| ABSTAIN | **8** |
| promoted → force-train / hard_atoms | **0** |

Abstain: 4 prior abstain unchanged; 1 empty `SLOT::`; 1 wiki `▼`; 1 etymology affix; 1 dump scaffolding.

## Promote decision

**NO_NEW_GOLD_THIS_CLIMB.** Authorized structure held out of train. Gold train-ready **135** and hard_atoms **180** unchanged. Val **n=228** unchanged.

Rationale: remaining misses are near-miss morph on already-correct SoT gold; thin BEST margin vs fair morph36 (0.7368 vs 0.7325); defer second INFERRED-promote wave. Next lever = morph41 warm morph40.

## Artifacts

- Spark: `~/hlx-private/morph40-residual-review-20260916/`
- Workspace: `receipts/morph40-residual-review-20260916/`
