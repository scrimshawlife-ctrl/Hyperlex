# Publish audit — `seed-morph78` weights (2026-09-24)

**Question:** should the `seed-morph78` weights (`hyperlex-structure-149m`) be published to the Hugging Face Hub now?

**Recommendation: DO NOT PUBLISH YET.** Keep weights local-only. Two blockers are about correctness, not paperwork: the promotion metric is contaminated, and the weights cannot be rebuilt from the canonical repo. Evidence: `receipts/publish-audit-20260924/`.

This audit does not revert `name_gate`, BEST, or any receipt. Hub stays an operator decision (C11).

## Blockers

### B1 — Promotion metric is train-contaminated (OBSERVED)

The soft_ceiling "broad OBSERVED val" eval (`eval_broad_observed.py`, off-git on Spark) scores every OBSERVED unbind row with `split=val`, but the force-train file adds val rows to training.

| Surface | n | morph78 | morph65 |
|---|--:|--:|--:|
| Broad val used for PROMOTE_BEST | 256 | 0.9883 | 0.8867 |
| … of which in `force_train_morph78_expanded.jsonl` | 193 | — | — |
| **Leak-free val** (not force-trained, text not in train split) | **63** | **1.0** | **1.0** |

The entire promotion margin comes from rows morph78 trained on. On leak-free val the two pins tie. PROMOTE_BEST shows better fit, not better generalization. (`clean-val-scores.json`, `audit_clean_val.py`.)

Related prior evidence: `receipts/2026-09-14-dual-scheme-holdout.md` scored structure-exact **0.0 (n=12)** on held-out structure bases while val was 0.625. The **test split (440 SoT rows) has never been scored** for any climb pin.

### B2 — Weights are not reproducible from the canonical repo (OBSERVED)

- morph78 trained from Spark `~/Hyperlex` at `78c4d83` (branch `cursor/morph51-reject-escalate-963d`), **39 commits behind `main`**.
- That checkout has **uncommitted edits** to `export.py`, `loop.py`, `unbind_recipe.py` (799-line diff, including data-filtering rules not on `main`): `spark-uncommitted-edits.diff`.
- Settle / force-expand / finish / broad-eval logic lives in **86 scripts under `~/hlx`, outside git** (e.g. `promote_launch_morph78_val_settle.py`, `eval_broad_observed.py`).
- `train-receipt.json` records `data_sha256` but no code commit or patch hash.

A Hub card claiming these metrics could not cite code that produces them.

## Other gaps

| # | Gap | State |
|---|---|---|
| G1 | Data rights | SoT 4,297 rows: `operator-local` 3,580, `operator-attested` 647, CC BY-SA (Wiktionary) 14, crawl 7. No dataset statement or redistribution basis for a model trained on crawled web slang; README already warns web text is not automatically redistributable. |
| G2 | License conflict | Personal repo MIT · org repo Zero State Proprietary · card frontmatter apache-2.0 (trunk's license). Weights licence and owner (Zero State vs personal) undecided. |
| G3 | Calibration | Classify returns `none` at confidence ≈1.0 on val-settled phrases (`receipts/20260924-infer-model-morph78.md`). E1 / E3 NOT_COMPUTABLE. |
| G4 | Size ceiling | 150,546,889 params (trunk 149,014,272 + heads) vs A1 "T1 ≤ 150M". Operator reading pending. |
| G5 | Loadability | Custom heads; no `trust_remote_code` modeling file or packaged loader on the card. Hub users could not load it without this repo. |
| G6 | Card evidence | Card metrics are val (contaminated) and train-val; no test table, no data statement. |

## What is already up to practice

safetensors weights · no chat template or generation head · Brier null / not a forecast · restricted inputs drop surface · dual-use gate rows 1–12 hold and the card has out-of-scope text (row 9) · local-only trunk, no Hub fetch · receipts for every promote/reject · public claim is Restricted (CLAIM-HLX-NAME-004).

## Path to a publishable release (in order)

1. **Canonicalize training code.** Commit the Spark checkout edits and the `~/hlx` settle/finish/eval scripts into `scripts/shadow/` on `main`. Record `code_commit` in train receipts.
2. **Fix the gate eval.** Broad val must exclude rows present in the force-train file (and any text in train). Re-run soft_ceiling decide for morph78 vs morph65 on the corrected surface.
3. **Spend the test split once.** Score morph78 (and morph65) on `split=test` with canonical code. That number goes on the card.
4. **Decide data + licence.** Dataset statement; which rows may train a public model (drop or isolate CC BY-SA if share-alike is a concern); weights licence and owner.
5. **Calibration + A1.** Either calibrate classify or omit lineage confidence from the card; record the A1 reading.
6. **Package.** Loader (`trust_remote_code` file or pip extra), card with test metrics and data statement.
7. **Then** a private/gated Hub repo first; public only on a separate sentence.

## Name gate note

`name_gate` rests on trained E2 PASS vs the Spec 004 probe, which this audit does not contradict. The PROMOTE_BEST decision over morph65 is not supported on leak-free val; whether to keep morph78 as BEST or treat morph65/morph78 as tied is an operator call.
