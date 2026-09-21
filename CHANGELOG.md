# Changelog

## Unreleased

- **Spec 007 morph67 INFLIGHT (SoT flip):** METHOD morph43 labeled morph65 force
  residuals → AUTHORIZE 2 / ABSTAIN 6; force expand **force_added=0** (dead INFERRED
  keys). Flipped those 2 to OBSERVED in harvest sidecar. Fair morph65 **0.9698492462311558**
  (193/199). Warm morph65, UPSAMPLE=8 + SECOND_SLOT=2 held, same force/hard as morph66.
  Container `hlx-train-morph67-1790010500`. Exclusive mem 0.3; Qwen stopped+disabled.
  `name_gate=false`. PIN iff best > fair and E2 exact 1.0.
  Receipts: `receipts/20260921-morph65-force-residual-label.md`,
  `receipts/20260921-morph67-sot-flip-inflight.md`.

- **Spec 007 morph66 REJECT_VS_BEST:** residual gold force/hard 164/206
  warm morph65, UPSAMPLE=8 + SECOND_SLOT=2 held. Best **0.9502487562189055**
  (ep9, 191/201) < fair morph65 **0.9601990049751243** (n=201). E2
  trunk-forward PASS. BEST stays morph65. Container
  `hlx-train-morph66-1789969749` exit 0. Exclusive mem 0.3; Qwen stayed
  stopped+disabled. `name_gate=false`. Do not replay same force/hard.
  Receipt: `receipts/20260921-morph66-40ep-reject-vs-best.md`.

- **Spec 007 morph65 PROMOTE_BEST:** `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=10`
  warm morph63, second-slot weight 2 held. Best **0.8584070796460177**
  (ep6, 194/226) > fair morph63 **0.8539823008849557** (n=226). E2
  trunk-forward PASS (`unbind_exact=1.0`). Spark BEST → morph65. morph63
  weights kept. Container `hlx-train-morph65-1789947808` exit 0.
  Exclusive mem 0.3; Qwen stayed stopped+disabled. `name_gate=false`.
  Upsample ladder freeze after this step (no 11+). Next: morph66 residual
  gold force/hard on fair morph65 **0.9601990049751243** n=201.
  Receipt: `receipts/20260921-morph65-40ep-promote-best.md`.

- **Spec 007 morph64 REJECT_VS_BEST:** `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=9`
  warm morph63, second-slot weight 2 held. Best **0.8539823008849557**
  (ep28, 193/226) **ties** fair morph63 on n=226. E2 trunk-forward PASS.
  Tie is not a promote. BEST stays morph63. Container
  `hlx-train-morph64-1789928581` exit 0. Exclusive mem 0.3; Qwen stayed
  stopped+disabled. `name_gate=false`. No new gold.
  Receipt: `receipts/20260920-morph64-40ep-reject-vs-best.md`.

- **Spec 007 morph63 PROMOTE_BEST:** `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=8`
  warm morph62, second-slot weight 2 held. Best **0.8539823008849557**
  (ep13, 193/226) > fair morph62 **0.8495575221238938** (n=226). E2
  trunk-forward PASS (`unbind_exact=1.0`). Spark BEST → morph63. morph62
  weights kept. Container `hlx-train-morph63-1789911656` exit 0.
  Exclusive mem 0.3; Qwen stayed stopped+disabled. `name_gate=false`. No new gold.
  Receipt: `receipts/20260920-morph63-40ep-promote-best.md`.

- **Spec 007 morph62 PROMOTE_BEST:** `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=7`
  warm morph61, second-slot weight 2 held. Best **0.8495575221238938**
  (ep21, 192/226) > fair morph61 **0.8451327433628318** (n=226). E2
  trunk-forward PASS (`unbind_exact=1.0`). Spark BEST → morph62. morph61
  weights kept. Container `hlx-train-morph62-1789896471` exit 0.
  Exclusive mem 0.3; Qwen stayed stopped+disabled. `name_gate=false`. No new gold.
  Receipt: `receipts/20260920-morph62-40ep-promote-best.md`.

- **Spec 007 morph61 PROMOTE_BEST:** `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=6`
  warm morph60, second-slot weight 2 held. Best **0.8451327433628318**
  (ep26, 191/226) > fair morph60 **0.8407079646017699** (n=226). E2
  trunk-forward PASS (`unbind_exact=1.0`). Spark BEST → morph61. morph60
  weights kept. Container `hlx-train-morph61-1789880707` exit 0 after
  exclusive remount (Qwen stopped+disabled). `name_gate=false`. No new gold.
  Receipt: `receipts/20260920-morph61-40ep-promote-best.md`.

- **Spec 007 morph60 PROMOTE_BEST:** `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=5`
  warm morph59, second-slot weight 2 held. Best **0.8407079646017699**
  (ep9, 190/226) > fair morph59 **0.831858407079646** (n=226). E2
  trunk-forward PASS (`unbind_exact=1.0`). Spark BEST → morph60. morph59
  weights kept. Container `hlx-train-morph60-1789829154` exit 0.
  `name_gate=false`. No new gold.
  Receipt: `receipts/20260919-morph60-40ep-promote-best.md`.

- **Spec 007 morph59 PROMOTE_BEST:** `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=4`
  warm morph58, second-slot weight 2 held. Best **0.831858407079646**
  (ep14, 188/226) > fair morph58 **0.8230088495575221** (n=226). E2
  trunk-forward PASS (`unbind_exact=1.0`). Spark BEST → morph59. morph58
  weights kept. Container `hlx-train-morph59-1789803430` exit 0.
  `name_gate=false`. No new gold.
  Receipt: `receipts/20260919-morph59-40ep-promote-best.md`.

- **Spec 007 morph58 PROMOTE_BEST:** `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=3`
  warm morph56, second-slot weight 2 held. Best **0.8230088495575221**
  (ep37, 186/226) > fair morph56 **0.8185840707964602** (n=226). E2
  trunk-forward PASS (`unbind_exact=1.0`). Spark BEST → morph58. morph56
  weights kept. Container `hlx-train-morph58-1789793254` exit 0.
  `name_gate=false`. No new gold.
  Receipt: `receipts/20260919-morph58-40ep-promote-best.md`.

- **Spec 007 morph57 REJECT_VS_BEST:** `HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT=3`
  warm morph56. Best **0.8185840707964602** (ep34, 185/226) ties fair
  morph56 on n=226. E2 PASS. Tie is not a promote. BEST stays morph56.
  Container `hlx-train-morph57-1789775196` exit 0. `name_gate=false`.
  Receipt: `receipts/20260919-morph57-40ep-reject-tie.md`.

- **Spec 007 morph56 PROMOTE_BEST:** `HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT=2`
  on the morph50 surface. Best **0.8185840707964602** (ep10, 185/226) >
  fair morph50 **0.8097345132743363** (n=226). E2 trunk-forward PASS
  (`unbind_exact=1.0`). Spark BEST → morph56. morph50 weights kept.
  Container `hlx-train-morph56-1789766977` exit 0. `name_gate=false`.
  Receipt: `receipts/20260918-morph56-40ep-promote-best.md`.

- **Earlier Unreleased Spec 007 / docs / P1 entries:** preserved in git at commit `bd3f86c5` (`CHANGELOG.md` blob `4a4481e6`). Restored tip after a docs-push content mishap; full text remains in that blob and in operator payload `MORPH64_REJECT_CHANGELOG.json`.

## 0.4.0 — Automatic backend pipeline (2026-08-05)

- `run_pipeline` / CLI `pipeline`: ingest → analyze → receipt → forecasts → score log → Phase 5 risk
- `ingest` and `run` default to the full auto path (`ingest --raw-only` for signal-only)
- Multi-term bags auto-expand to one full result unit per lexicon atom
- Never auto-settles; `brier` always null until operator `settle`
- Package API: `run_pipeline`, `run_one`
