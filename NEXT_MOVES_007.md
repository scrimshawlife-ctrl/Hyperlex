# Spec 007 — next after morph66 REJECT: label morph65 force residuals (n=201)

`name_gate=false`. BEST=**morph65**. Upsample ladder frozen. Do not run SECOND_SLOT=4. Do not replay morph66 force/hard.

## Gate result

morph66 residual-gold **REJECT**: best **0.9502** (191/201) < fair morph65 **0.9602** (193/201). E2 PASS. BEST stays morph65.

## 0.95 bar

On post-force fair surface n=201, morph65 already clears ~0.95 (**0.9602**). Gap to 1.0 = **8 exacts**.

## Prepared dump (Spark)

`~/hlx-private/p1-spark-morph65-force-residuals-20260921/` — morph65 misses on force surface: **8 INFERRED** (type_slot 6 / positional 2). Receipt: `receipts/20260921-morph65-force-residuals-n201.json`.

## One card

METHOD morph43 AUTHORIZE / ABSTAIN only on those 8. Expect many wiki/scaffold ABSTAINs. If AUTHORIZE ≥1: expand force/hard, re-fair morph65, one gold-knob morph67 warm morph65 (UPSAMPLE=8, SECOND_SLOT=2 held).

| not this card | |
|--|--|
| upsample 11+ | frozen |
| SECOND_SLOT=4 | blocked |
| replay morph66 force/hard | rejected |
| invent OBSERVED | forbidden |
| Hub / name_gate | false |

Qwen stays stopped unless the operator re-enables `qwen38-27b.service`.
