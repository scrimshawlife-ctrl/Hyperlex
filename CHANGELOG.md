# Changelog

## Unreleased

- **Spec 007 morph73 IN FLIGHT (INIT_EXPAND_VOCAB warm morph65):** after morph72
  REJECT, one-knob `HYPERLEX_INIT_EXPAND_VOCAB=1` + `HYPERLEX_INIT_FROM=seed-morph65`
  on morph72 force/hard 217/258. UPSAMPLE=10 held. Fair morph65
  **0.9649122807017544** n=171. Container `hlx-train-morph73-1790148566`.
  Receipt: `receipts/20260923-morph73-expand-warm-inflight.md`.

- **Spec 007 morph72 REJECT_VS_BEST:** UPSAMPLE=10 non-warm on morph71 force/hard
  217/258. Best **0.9532163742690059** (ep22) < fair **0.9649122807017544** n=171 →
  REJECT. E2 PASS. BEST stays morph65. Residual AUTHORIZE=0 — hold.
  Receipt: `receipts/20260923-morph72-40ep-reject-vs-best.md`.

- **Spec 007 morph72 IN FLIGHT / morph71 REJECT:** prior ladder docs in workspace
  CHANGELOG / receipts.

- **Earlier Unreleased Spec 007 / docs / P1 entries:** morph70→morph56 ladder and
  0.4.0… history preserved in branch history / operator workspace `CHANGELOG.md`.
