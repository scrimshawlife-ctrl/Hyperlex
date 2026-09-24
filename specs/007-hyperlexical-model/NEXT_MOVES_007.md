# Spec 007 — next: morph78 is BEST and named Hyperlexical

`name_gate` **true** for `seed-morph78` (Danny `flip name_gate`, 2026-09-24, amendment A6). BEST=**morph78**. Upsample freeze = **11+**. Do not run SECOND_SLOT=4.

## Done

- morph78 named phrases settled · force/hard **236/277** · soft_ceiling train complete.
- **PROMOTE_BEST** (ceiling_escape): broad **0.9883** > PRIOR morph65 **0.8867** n=256 + E2 PASS.
- Card rename: Hub card `hyperlex-structure-149m`; eval packets set `name_gate` true only for a trunk-forward eval of `seed-morph78`.
- Real inference: `hyperlexical.infer --model-dir ~/.hyperlex/models/BEST` → `MODEL_EMBEDDING` packet (`hyperlex-structure-149m`), verified on Spark.
- Danny **`flip name_gate`** → `seed-morph78` may be called **Hyperlexical** (receipt `specs/007-hyperlexical-model/receipts/20260924-name-gate-yes-morph78.md`).

## Gate

soft_ceiling **spent** for this climb (morph78 now PRIOR/BEST). Further climbs need a new authorize/acquire card.

## Next (each a separate operator sentence)

1. Hub: **recommend do not publish yet** — publish audit `specs/007-hyperlexical-model/PUBLISH-AUDIT-20260924.md`. Blockers: promotion metric train-contaminated (leak-free val morph78 = morph65 = 1.0, n=63); weights not reproducible from `main`.
   Fix order: canonicalize Spark training code → fix gate eval → score test split once → data/licence → calibration/A1 → loader → private Hub first.
   Detailed plan + operator decisions D1–D7: `specs/007-hyperlexical-model/PUBLISH-READINESS-PLAN.md`.
   Executed (no-decision items): `specs/007-hyperlexical-model/PUBLISH-READINESS-RESULTS-20260924.md`. Corrected gate REJECTs morph78 vs morph65 (tie 1.0, n=58); 709 Wiktionary rows (D5); vocab scrub needed (D8). Done 2026-09-24: D1, D5(a) relabel, D8 filter, D6→A7. Open: D3, D4, D5(b), D7; D2 skip recommended. Next: clean cold-start retrain (needs authorize sentence).
2. Optional T13 (promote `scripts/shadow/hyperlexical/` into `src/hyperlex/`).
3. HOLD morph78; no new climb without a new card.

Open findings (receipt `receipts/20260924-infer-model-morph78.md`): classify overconfident on val-settled phrases; trunk+heads = 150.55M vs A1 150M (trunk 149.0M).

Qwen stays stopped unless re-enabled.
