# Danny gold review package — morph19 `partial_slot_miss` (2026-09-15)

**Status:** waiting on Danny · **OBSERVED hold** · **no train until authorize**  
**BEST:** morph19 untouched · Climb KEEP famcls52 ≠ BEST · `name_gate=false`

## Package contents

| file | purpose |
|------|---------|
| `ASK_DANNY.md` | clear authorize-gold **or** alternate-ladder ask |
| `MANIFEST.json` | counts, constraints, source pins |
| `LABELING_TEMPLATE.md` | schemes `positional` \| `type_slot` only; blank gold rules |
| `PATTERN_RANK.md` | ranked miss patterns (`partial_slot_miss` first) |
| `candidates.jsonl` | **198** residual rows; blank `gold_*` for Danny (**canonical**) |
| `candidates_p1_observed.jsonl` | P1 ∩ OBSERVED only (**25**) — quick Danny start |
| `CANDIDATES_SHEET.md` | compact ranked table (all 198) |
| `CANDIDATES_POINTER.md` | where full JSONL lives (workspace / Spark / Hyperlex shards) |
| `CANDIDATES_SHARDS.md` | Hyperlex shard map; `cat part0..part13` → full `candidates.jsonl` |
| `candidates.part0.jsonl`…`part13.jsonl` | Hyperlex-safe shards (byte-identical concat to full JSONL) |
| `counts.json` | machine-readable tallies |
| `morph19_residual.summary.json` | Spark residual summary copy |
| `pattern_examples.json` | short example slices per cohort |

## Residual counts (morph19 BEST, civilian unbind val)

| metric | n |
|--------|--:|
| residual total | **198** |
| **partial_slot_miss** | **146** |
| type_slot_token_miss | 81 |
| positional_head_filler_miss | 36 |
| full_miss | 28 |
| morph_bleed | 11 |

P1 cohort exclusive count = **146** `partial_slot_miss` rows (gold fields blank).

## Source

- Spark: `~/hlx-private/climb_vs_best_civilian_20260915/morph19_residual.jsonl`
- Workspace civilian receipt: `../climb_vs_best_civilian.json`
- Escalate receipt: `../20260915-escalate-observed-partial-slot-miss.md`

## Policy

- Do **not** invent gold here.
- `eval_reference_fillers` ≠ authorized OBSERVED gold.
- No famcls53 / morph train; no BEST overwrite until Danny authorizes.
