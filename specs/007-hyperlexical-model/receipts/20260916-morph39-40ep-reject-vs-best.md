# morph39 — OBSERVED gold force-train REJECT_VS_BEST (2026-09-16)

**Authority:** Spec 007. Operator labeler authority 2026-09-16. `name_gate=false`.  
**BEST:** **morph36** held (`unbind_exact≈0.5455` on old val). Climb famcls52 separate.

## Label integrate

| item | n |
|------|--:|
| P1 labeled | 146 |
| authorized structure gold | **136** |
| abstain | **10** |
| OBSERVED force-train exacts | **25** |
| hard_atoms | 62 → **75** (+13 new) |
| INFERRED class promote | **no** |

## Fair-eval (val changed)

Force-train moved 25 OBSERVED exacts val→train → val **363 → 338**.

| model / surface | unbind_exact |
|-----------------|-------------:|
| morph36 old val (n=363) | 0.5455 |
| **morph36 fair new val (n=338)** | **0.5740** |
| morph39 best ep2 (n=338) | **0.5621** |

## Gate

| check | result |
|-------|--------|
| morph39 best > fair morph36 (0.5740)? | **NO** (0.5621) |
| morph39 best > old 0.5455? | yes (0.5621) — not fair when val changed |
| E2 trunk-forward | **PASS** (1.0) |
| Promote BEST? | **NO** |
| Ladder ≥0.55 on new val | morph36 fair already 0.5740 after removing misses; morph39 did not clear vs fair |

## Verdict

**REJECT_VS_BEST.** Lever (authorized OBSERVED gold force-train + hard_atoms) did not beat fair morph36 baseline on the force-train val. BEST stays **morph36**.

## Artifacts

- Package: `receipts/danny-gold-review-partial-slot-miss-20260915/` (`METHOD.md`, labeled JSONL, counts)
- Authorization: `receipts/20260916-labeler-authorized-observed-gold.md`
- Spark private: `~/hlx-private/p1-spark-morph39-40ep-observed-gold-20260916/`
- Workspace copy: `receipts/morph39-40ep-observed-gold-20260916/`
