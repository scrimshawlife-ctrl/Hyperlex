# Operator review pack — classify expand queues (2026-09-14)

After famcls **MERGED** and famcls2 **REJECT**, family progress needs **reviewed labels**, not more CE/sampler.

## Queues (do not auto-train)

Path: `~/hlx-private/p1-classify-expand-20260914/`

| file | n | policy |
|------|---|--------|
| `review_queue_inferred_pass.jsonl` | ~19 | curated INFERRED shortlist — accept/reject each |
| `review_queue_inferred.jsonl` | ~293 | full INFERRED (noisy; gaming/kinship/none heavy) |
| `review_queue_golden_terms.jsonl` | ~12 | golden-receipt matched terms — accept/reject each |

## Pass shortlist sample lineages

brainrot-aura, kinship-address, gaming-meta, plus some ai-native / betting-sharp fillers. `none` still has **no** OBSERVED short surfaces.

## Accept procedure

1. Mark accepted rows (text + lineage) in a new `accepted_family_labels.jsonl`
2. Re-run expand builder to append only accepted rows into prepare
3. Resume from **famcls** init (not famcls2)
4. Gate unchanged: structure/role/pointer hold at 1.0; family > new-test majority

## Do not

- Train INFERRED wholesale
- Invent OBSERVED structure gold
- Overwrite BEST
- Merge famcls2
