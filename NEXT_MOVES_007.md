# Spec 007 — next: soft_ceiling armed · fresh acquire for morph78

`name_gate=false`. BEST=**morph65** (held). Upsample freeze = **11+**. Do not run SECOND_SLOT=4.

## Done

- Force-surface climb STOP at fair **1.0** n=164 (morph75–77 ceiling). morph77 val-settle kept.
- Operator **`authorize gate soft_ceiling`** → gate **ARMED**.
- Pin: broad OBSERVED morph65 authorize **0.889763779527559** n=254 (historical); live prior post-morph77 **0.88671875** n=256.
- Spark: `GATE_SOFT_CEILING.json`, `eval_broad_observed.py`, `run_broad_eval.sh`, `gate_soft_ceiling_decide.py`, `finish_soft_ceiling.py`.

## Gate (armed)

**soft_ceiling_tiebreak:**

- If force-fair **< 1.0**: promote on strictly greater force-fair + E2 1.0 (unchanged).
- If force-fair **= 1.0**: promote on candidate broad OBSERVED **>** PRIOR morph65 broad on same live SoT + E2 1.0. Do not cancel solely for force-fair 1.0.

See `receipts/20260923-authorize-gate-soft-ceiling.md`.

## Next

Gold force card from morph65 residual AUTHORIZE is **empty** (Jev defer_quality). Under soft_ceiling: **fresh acquire + METHOD morph43** aimed at broad OBSERVED residuals → settle qualify → morph78 warm morph65 (force/hard expand still legal; promote uses ceiling escape). Await operator authorize on the acquire/settle card before train.

Qwen stays stopped unless the operator re-enables `qwen38-27b.service`.
