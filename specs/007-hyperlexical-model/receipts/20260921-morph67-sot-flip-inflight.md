# morph67 INFLIGHT — SoT class flip (2026-09-21)

**Superseded by** `receipts/20260921-morph67-40ep-reject-vs-best.md`.

Container `hlx-train-morph67-1790010500`. `name_gate=false`. Exclusive mem 0.3. Qwen stopped+disabled.

## One knob

SoT **INFERRED→OBSERVED** for 2 METHOD AUTHORIZE morph65 force residuals, appended to Spark
`~/.hyperlex/hyperlexical/harvest_unbind_observed_mw.jsonl` (backup
`bak-pre-morph67-sot-flip-20260921T170637Z`). No invented fillers. Force/hard paths **unchanged**
(`force_train_morph66_expanded.jsonl` 164 / `hard_atoms_train_morph66.jsonl` 206).

## Why

Label card AUTHORIZE≥1 but `force_added=0`. Keys already in force as INFERRED — force skip.
After flip: force moves **164/164**, val after force **199**.

## Fair (morph65 on post-flip surface)

| | |
|--|--|
| exact | **0.9698492462311558** (193/199) |
| prior fair n=201 | 0.9601990049751243 (193/201) |
| path | `~/hlx/fair-eval-morph65-morph67-sot.json` |

Same 193 correct; the 2 flipped misses left val.

## Recipe (held except SoT)

| knob | value |
|--|--|
| warm | morph65 |
| UPSAMPLE | 8 (held) |
| SECOND_SLOT | 2 (held) |
| LAST | 8 |
| HEAD_SLOT | 2 |
| HARD_UPSAMPLE | 4 |
| LR | 2e-5 |
| epochs | 40 |
| SAVE_BEST | on |
| PIN | best > fair 0.9698 on n=199 **and** E2 trunk-forward exact 1.0 |

## Not this card

upsample 11+ · SECOND_SLOT=4 · invent OBSERVED fillers · Hub · name_gate · identical expand without SoT flip

Private: `~/hlx-private/p1-spark-morph67-40ep-sot-flip-20260921/`
