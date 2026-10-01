# Classification v5 — Promote ident-filtered factorized Stage-A

```text
RULE = PROMOTE_STAGE_A_IDENT_FILTERED_FACTORIZED_CANDIDATE
EXPERIMENT = HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-001
STAGE_A_PROMOTION = PROMOTION_INVALID
STAGE_A_BEST = cd2829c1… UNCHANGED
PREVIOUS_STAGE_A_BEST = cd2829c1…
MODEL_WIDE_BEST = 9fba0f66… UNCHANGED
MODEL_WIDE_BEST_MUTATED = false
RESERVE_CONSUMED = false
SELECTED_CHECKPOINT = 8b2de447… (encoder-only)
receipt = 1123d70dec32b827…
NEXT_ACTION = REPAIR_IDENT_FILTERED_FACTORIZED_CHECKPOINT_SERIALIZATION
```

Promotion preflight against the sealed SETTLED_PASS train receipt **passed**.
Cold-load of `8b2de447…` through the canonical factorized path **failed closed**
because the selected safetensors contains encoder overlays only.

## Root cause

`flatten_weight_tensors` historically whitelisted head names and omitted
`relation_head` / `resolvability_head`. The authorized train scored and sealed
metrics from in-memory heads, then persisted an encoder-only checkpoint whose
SHA is `8b2de447…`.

Required heads for promotion cold-load:

```text
relation_head -> 2 logits
resolvability_head -> 2 logits
```

are absent. Overlay verification:

```text
architecture_identity = false
has_factorized_heads = false
no_legacy_possible_evidence_heads = true
no_flat_evidence_head_canonical = true
parent_best_matches = true
```

## Pointer state (unchanged)

| Pointer | Value |
|---|---|
| STAGE_A_BEST | `cd2829c1…` (two-stage) |
| MODEL_WIDE_BEST | `9fba0f66…` |
| V1R2 | unchanged |
| spent reserve | SPENT / unused |

No STAGE_A_BEST mutation was applied. No restore required.

## Serialization fix shipped (not sufficient alone)

`save_pretrained._HEAD_NAMES` now includes `relation_head` and
`resolvability_head` for future saves. Rematerializing a complete checkpoint
still requires a packaging repair of the sealed train artifacts.

## Exact next action

```text
REPAIR_IDENT_FILTERED_FACTORIZED_CHECKPOINT_SERIALIZATION
```

Do **not** claim Stage-A promotion applied. Do **not** move MODEL_WIDE_BEST.
