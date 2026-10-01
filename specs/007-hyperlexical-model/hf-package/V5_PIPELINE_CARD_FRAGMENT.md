## V5 Stage-A/B V1R2 pipeline (local; Hub unpublished)

**Packaging ID:** `HYPERLEX_V5_STAGE_A_B_V1R2_PACKAGE_V1`
**Pipeline:** `HYPERLEX_V5_STAGE_A_B_PIPELINE_V1` · Stage-A `HYPERLEX_V5_STAGE_A_CANONICAL_V1`
**States:** Stage-A `CANONICAL_FROZEN` · Stage-B `CANONICAL_FOR_V1R2_PIPELINE` · Pipeline `CANONICAL_FROZEN`

| Artifact | SHA256 / value |
| --- | --- |
| `STAGE_A_BEST` | `f2b00c5dfeb087288fc1686c901fbc8b52a8ba7a7b51cb83ff038656f93617fa` |
| `MODEL_WIDE_BEST` | `9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6` |
| Stage-B index | `4febe96ea179597eb7792b376ed9eedbc9295a2fd8b5fa0eec969719f015c1f4` (n=948) |
| Stage-B floors | score `0.83`, margin `0.01` |
| Stage-A thresholds | relation `0.6`, resolvability `0.75` |
| Surface | `HYPERLEX_V5_STAGE_A_IDENTIFIABILITY_FILTERED_SURFACE_V1R2` / `492ed36751c7fdc40fe10bcdfabb69fa8783f8680259c31b3a64ee6903326d73` |

**Flow:** text → Stage-A → (NONE stop | UNCERTAIN abstain | PRESENT → Stage-B → FAMILY|AMBIGUOUS|ABSTAIN).

**Load:** ModernBERT → MODEL_WIDE_BEST → STAGE_A_BEST (`relation_head` + `resolvability_head`) → Stage-B index `4febe96ea179597e…`.

**Limitations:** DOMAIN_IRRELEVANT=`NOT_ESTABLISHED`; SHORT_ATOM_POSITIVE=`LOW_SUPPORT`; CONTEXT_DEPENDENT_GOLD=`OUTSIDE_CURRENT_TEXT_ONLY_STAGE_A_CONTRACT`; Stage-B validation conditional on Stage-A admission.

**Hub:** `NOT_AUTHORIZED`. Weights/index stay on operator paths; not in git.
