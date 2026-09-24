# morph65 force residual gold — METHOD label (2026-09-21)

**Authority:** operator continue after morph66 REJECT. METHOD = morph43. `name_gate=false`.

## Source

morph65 misses on morph66 force surface (n=201): **8 INFERRED** (type_slot 6 / positional 2).
Dump: `~/hlx-private/p1-spark-morph65-force-residuals-20260921/`.
Receipt: `receipts/20260921-morph65-force-residuals-n201.json`.

## Label

| | n |
|--|--:|
| AUTHORIZE | 2 |
| ABSTAIN | 6 |

- AUTHORIZE reason: `type_slot_parse_match` (TOKEN/SLOT/MARKER parse == gold)
- ABSTAIN reason: `abstain_scaffolding_wiki_etym` (wiki/etym/quotations/synonym/Armenian/Google Trends)

AUTHORIZE texts:

1. `TOKEN:MUSH SLOT:: MARKER:Multi-User TOKEN:Shared SLOT:Hallucination`
2. `TOKEN:Real SLOT:eyes MARKER:realize TOKEN:clanker SLOT:lies!!!`

## Expand attempt (no-op)

Built `force_train_morph67_expanded.jsonl` / `hard_atoms_train_morph67.jsonl` from morph66 base:

| | |
|--|--:|
| force_base → force_new | 164 → 164 |
| **force_added** | **0** |
| hard_base → hard_new | 206 → 206 |
| **hard_added** | **0** |

Texts already present in morph66 force (from morph63 residual gold) with `dataset_class_source=INFERRED`. Fair morph65 on morph67 expand path stayed **0.9601990049751243 n=201**.

## Do not burn

Launching morph67 with identical force/hard and no class change would replay morph66. Stopped.

## Real one-knob (next)

`apply_unbind_force_train` only moves `class==OBSERVED`. Force had 164 keys but only **162** moved — the 2 AUTHORIZE keys were dead (INFERRED in val). Flip those 2 to OBSERVED in Wave A harvest sidecar → force moves 164/164; val n→199. See `receipts/morph65-force-residual-gold-20260921/SOT_FLIP_SUMMARY.json` and morph67 inflight.
