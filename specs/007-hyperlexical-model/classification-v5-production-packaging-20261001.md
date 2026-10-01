# HYPERLEX_V5_PRODUCTION_PACKAGING_V1

## V5 classification pipeline (local; Hub unpublished)

**Packaging ID:** `HYPERLEX_V5_PRODUCTION_PACKAGING_V1`
**Pipeline:** `HYPERLEX_V5_STAGE_A_B_PIPELINE_V1` · Stage-A `HYPERLEX_V5_STAGE_A_CANONICAL_V1`

| Artifact | SHA256 / value |
| --- | --- |
| `STAGE_A_BEST` | `f2b00c5dfeb087288fc1686c901fbc8b52a8ba7a7b51cb83ff038656f93617fa` |
| `MODEL_WIDE_BEST` | `9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6` |
| Stage-B index | `3fd6c87a5825f3f2a25a81f1a769a77aa69e03ddca5b370f9247672d93aaee21` |
| Stage-B floors | score `0.64`, margin `0.07` |
| Stage-A thresholds | relation `0.6`, resolvability `0.75` |

**Load sequence:** ModernBERT trunk → MODEL_WIDE_BEST → STAGE_A_BEST (layers 20/21 + `relation_head` + `resolvability_head`).

**Decision:** `if P(RESOLVABLE) < 0.75 -> UNCERTAIN; else if P(EVIDENCE_RELATION_PRESENT) >= 0.60 -> EVIDENCE_PRESENT; else NO_EVIDENCE`

**Stage B:** only on `EVIDENCE_PRESENT`. Index not rebuilt under this packaging.

**Limitations:** DOMAIN_IRRELEVANT=`NOT_ESTABLISHED`; SHORT_ATOM_POSITIVE=`LOW_SUPPORT`; CONTEXT_DEPENDENT_GOLD=`OUTSIDE_CURRENT_TEXT_ONLY_STAGE_A_CONTRACT`.

**Hub:** `NOT_AUTHORIZED`. Weights stay on operator Spark paths; not in git.

**PACKAGING_READY** = `false` (pipeline eval failed primary gate on V1R9)

**PACKAGING_RECEIPT_SHA256** = `86e6c490c3d7fa95…` (see receipt JSON)

**PRIMARY_DIAGNOSIS** = `STAGE_A_V1R2_CANONICAL_ON_STAGE_B_V1R9_SURFACE`

**NEXT_ACTION** = `ALIGN_V5_STAGE_B_TO_V1R2_OR_SCOPED_CROSS_SURFACE_EVAL`
