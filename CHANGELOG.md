## Unreleased

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

- **Earlier Unreleased Spec 007:** preserved on `main` CHANGELOG through morph63 and prior; full history remains in git. Tip above is morph65 + morph64; do not truncate older Unreleased bullets on conflict — restore from `main` if needed.
