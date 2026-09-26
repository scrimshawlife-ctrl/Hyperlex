# Spec 007 — next: HOLD morph78 after rc1 REJECT

`name_gate` **true** for `seed-morph78` (Danny `flip name_gate`, 2026-09-24, amendment A6). BEST=**morph78**. Upsample freeze = **11+**. Do not run SECOND_SLOT=4.

## Done

- morph78 named phrases settled · force/hard **236/277** · soft_ceiling train complete.
- **PROMOTE_BEST** (ceiling_escape): broad **0.9883** > PRIOR morph65 **0.8867** n=256 + E2 PASS (contaminated promote surface; see audit).
- Card rename: Hub card `hyperlex-structure-149m`; eval packets set `name_gate` true only for trunk-forward eval of `seed-morph78`.
- Real inference: `hyperlexical.infer --model-dir ~/.hyperlex/models/BEST` → `MODEL_EMBEDDING` packet (`hyperlex-structure-149m`), verified on Spark (#106).
- Danny **`flip name_gate`** → `seed-morph78` may be called **Hyperlexical**.
- Publish readiness (no-decision items): soft_ceiling/provenance/calibration/loader on `main`; D1, D5(a), D8, A7 done.
- **rc1** clean cold-start retrain + one holdout score: **REJECT** (2026-09-24 PT). Receipt: `specs/007-hyperlexical-model/receipts/rc1-result-20260924/OPERATOR-CARD.md`.
- Selection-surface audit: **NO_RULE_MATCH** / HOLD. Receipt: `receipts/selection-surface-audit-20260924/`.

## Gate

soft_ceiling **spent** for the morph78 climb. rc1 is **not** the release candidate. Holdout manifest `holdout-manifest-rc1.json` is **`SCORED_SPENT`** — do not re-score it for selection. Further climbs need a **new** hashed holdout before training, plus a new authorize/acquire card vs morph78 PRIOR.

### rc1 vs morph78 (test, once)

| Criterion | rc1 | morph78 | Result |
|---|--:|--:|---|
| Unbind clean exact (n=306) | 0.6797 | 0.7255 | FAIL (≥0.7155) |
| Classify accuracy all (n=444) | 0.7905 | 0.8176 | FAIL (≥0.7976) |
| Classify OBSERVED (n=72) | 0.5694 | 0.6389 | FAIL (≥0.5889) |
| E2 / clean-val tie / vocab | PASS | — | PASS |

BEST unchanged (`seed-morph78`). `name_gate` untouched. No Hub.

## Next (each a separate operator sentence)

1. **Default HOLD** `seed-morph78`. No new climb without a named authorize/acquire card and a fresh holdout draw.
2. **Hub:** still recommend **do not publish**. Audit + readiness: corrected clean gate ties morph78 to morph65; Wiktionary/data licence (D4, D5(b) for future release trains); open D3. Plan: `PUBLISH-READINESS-PLAN.md` / `PUBLISH-AUDIT-20260924.md`.
3. Optional **T13** (promote `scripts/shadow/hyperlexical/` into `src/hyperlex/`).
4. **D3** — keep morph78 BEST vs treat morph65/morph78 as tied on corrected gate (A6 already names morph78).

Open findings (receipt `receipts/20260924-infer-model-morph78.md`): classify overconfident on val-settled phrases; trunk+heads = 150.55M vs A1 150M (A7: A1 counts trunk).

Qwen stays stopped unless re-enabled.
