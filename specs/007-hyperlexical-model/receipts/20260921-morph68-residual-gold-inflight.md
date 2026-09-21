# morph68 INFLIGHT — residual gold force/hard (2026-09-21)

`name_gate=false`. Exclusive mem 0.3. Qwen stopped+disabled.

## One knob

METHOD morph43 AUTHORIZE on morph67 residuals (n=2) → force/hard expand + harvest OBSERVED append.
Force **166** / hard **208**. Warm morph65. UPSAMPLE=8 + SECOND_SLOT=2 held.

## Fair (morph65 on morph68 surface)

| | |
|--|--|
| exact | **0.9695431472081218** (191/197) |
| path | `~/hlx/fair-eval-morph65-morph68.json` |

## Recipe (held except force/hard)

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
| PIN | best > fair 0.9695 on n=197 **and** E2 trunk-forward exact 1.0 |

## Not this card

upsample 11+ · SECOND_SLOT=4 · invent OBSERVED fillers · Hub · name_gate · replay morph67 SoT without new gold

Private: `~/hlx-private/p1-spark-morph68-40ep-residual-gold-20260921/`
