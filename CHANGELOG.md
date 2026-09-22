# Changelog

## Unreleased

- **Spec 007 morph68 REJECT_VS_BEST + morph69 unused METHOD gold INFLIGHT:** morph68
  best **0.9695431472081218** (ep27) = fair n=197 → REJECT (tie). E2 PASS. BEST stays
  morph65. Residual AUTHORIZE=0 (scaffolding). Goldens updated: unused METHOD AUTHORIZE
  morph43/morph50 residual gold **force_added=26** / hard_added=25 (192/233). Fair morph65
  **0.9649122807017544** n=171. morph69 warm morph65 UPSAMPLE=8 SECOND_SLOT=2 held;
  container `hlx-train-morph69-1790065790`. Hang-fix loop.py retained.
  Receipts: `receipts/20260922-morph68-40ep-reject-vs-best.md`,
  `receipts/20260922-morph69-unused-method-gold.md`.

- **Spec 007 morph68 hang-fix + relaunch:** Two post-ep4 hangs
  (`…-1790029975`, `…-1790040737`) — host CPU ~98%, GPU util 0, mem held after
  SAVE_BEST 0.964467. Root cause: per-step `loss.detach().cpu()` (~12k CUDA syncs/epoch)
  after SAVE_BEST encoder GPU→CPU copy. Fix in `loop.py`: on-device last loss
  (one `.item()`/epoch), synchronize+empty_cache after SAVE_BEST, epoch-progress
  heartbeat. Relaunch `hlx-train-morph68-1790047095` same one-knob without
  `expandable_segments`. Receipt: `receipts/morph68-residual-gold-20260921/HANG_FIX_20260922T0315Z.json`.

- **Spec 007 morph68 INFLIGHT (residual gold):** After morph67 REJECT, METHOD morph43
  labeled morph67 residuals → AUTHORIZE 2 / ABSTAIN 6. Force/hard expand
  **force_added=2** / **hard_added=2** (166/208) + harvest OBSERVED append. Fair morph65
  **0.9695431472081218** (191/197). Warm morph65, UPSAMPLE=8 + SECOND_SLOT=2 held.
  Container `hlx-train-morph68-1790029975`. Exclusive mem 0.3; Qwen stopped+disabled.
  `name_gate=false`. PIN iff best > fair and E2 exact 1.0.
  Receipts: `receipts/20260921-morph67-residual-label.md`,
  `receipts/20260921-morph68-residual-gold-inflight.md`.

- **Spec 007 morph67 REJECT_VS_BEST (SoT flip):** SoT INFERRED→OBSERVED for 2 AUTHORIZE
  morph65 force residuals. Best **0.9597989949748744** (ep18, 191/199) < fair morph65
  **0.9698492462311558** (193/199). E2 trunk-forward PASS. BEST stays morph65.
  Container `hlx-train-morph67-1790010500` exit 0. Exclusive mem 0.3; Qwen stayed
  stopped+disabled. `name_gate=false`. Do not replay same SoT flip.
  Receipt: `receipts/20260921-morph67-40ep-reject-vs-best.md`.

- **Spec 007 morph66 REJECT_VS_BEST:** residual gold force/hard 164/206
  warm morph65, UPSAMPLE=8 + SECOND_SLOT=2 held. Best **0.9502487562189055**
  (ep9, 191/201) < fair morph65 **0.9601990049751243** (n=201). E2
  trunk-forward PASS. BEST stays morph65. Container
  `hlx-train-morph66-1789969749` exit 0. Exclusive mem 0.3; Qwen stayed
  stopped+disabled. `name_gate=false`. Do not replay same force/hard.
  Receipt: `receipts/20260921-morph66-40ep-reject-vs-best.md`.

- **Earlier Unreleased Spec 007 / docs / P1 entries:** morph65→morph56 ladder and
  0.4.0… history preserved in branch history / operator workspace `CHANGELOG.md`.
