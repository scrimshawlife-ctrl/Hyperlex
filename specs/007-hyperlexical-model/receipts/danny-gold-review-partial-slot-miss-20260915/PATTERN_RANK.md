# Ranked miss patterns — morph19 civilian residuals

Source: `~/hlx-private/climb_vs_best_civilian_20260915/morph19_residual.jsonl`  
n_residual=**198** / val n=363. Themes co-occur; cohort priority is exclusive.

## Priority order

| priority | cohort | n | note |
|---------:|--------|--:|------|
| **1** | `partial_slot_miss` | **146** | Ladder wall — review first |
| **2** | `type_slot_token_miss` (no partial) | 16 | type_slot scheme misses without partial |
| **3** | `positional_head_filler_miss` (no partial/type) | 36 | positional head/filler misses |
| — | (full_miss / morph_bleed as co-themes) | — | counted in theme totals below |

## Theme totals (non-exclusive; row may carry multiple)

| theme | count |
|-------|------:|
| **partial_slot_miss** | **146** |
| type_slot_token_miss | 81 |
| positional_head_filler_miss | 36 |
| full_miss | 28 |
| morph_bleed | 11 |

## `partial_slot_miss` breakdown (P1)

| slice | n |
|-------|--:|
| scheme `type_slot` | 75 |
| scheme `positional` | 71 |
| dataset_class `INFERRED` | 121 |
| dataset_class `OBSERVED` | 25 |

## Review guidance

1. Start with **P1** (`candidates.jsonl` ranks 1…146).
2. Within P1, OBSERVED rows are listed before INFERRED; `type_slot` before `positional`.
3. Then P2 type_slot-only leftovers, then P3 positional head misses.
4. Fill blank gold only under **`positional` | `type_slot`**. Leave blank if not authorizing.

## Example surfaces (illustrative; gold blank in package)

See `pattern_examples.json` and top of `candidates.jsonl`. Pred shown; **no invented gold**.
