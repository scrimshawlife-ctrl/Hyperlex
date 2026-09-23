# Changelog

## Unreleased

- **Spec 007 morph72 IN FLIGHT (UPSAMPLE=10 non-warm):** after morph71 REJECT, restore
  BEST morph65 UPSAMPLE=10 (morph71 used 8) on morph71 force/hard 217/258. Non-warm.
  Fair **0.9649122807017544** n=171. Container `hlx-train-morph72-1790129677`.
  Receipt: `receipts/20260923-morph72-upsample10-nonwarm-inflight.md`.

- **Spec 007 morph71 REJECT_VS_BEST:** role-vocab expand / non-warm **force_added=23**.
  Best **0.9590643274853801** < fair **0.9649122807017544** n=171 → REJECT. E2 PASS.
  BEST stays morph65. Residual AUTHORIZE=0.
  Receipt: `receipts/20260922-morph71-40ep-reject-vs-best.md`.

- **Earlier Unreleased Spec 007 / docs / P1 entries:** morph70→morph56 ladder and
  0.4.0… history preserved in branch history / operator workspace `CHANGELOG.md`.
