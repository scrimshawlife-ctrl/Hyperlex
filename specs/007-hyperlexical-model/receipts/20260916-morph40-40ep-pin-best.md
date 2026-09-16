# morph40 — INFERRED→OBSERVED train promote PIN BEST (2026-09-16)

**Authority:** Spec 007. Operator labeler authority; high-confidence INFERRED→OBSERVED train promote. `name_gate=false`.  
**Prior BEST:** morph36 (artifacts preserved at `...-seed-morph36`). **New BEST:** **morph40**.

## Label expand

| item | n |
|------|--:|
| P1 labeled | 146 |
| authorized structure gold | **136** |
| abstain (unchanged) | **10** |
| original OBSERVED train-ready | **25** |
| INFERRED promoted → OBSERVED train | **110** |
| documentary hold (`punct_only_filler`) | **1** (`morph19-civ-res-002`) |
| **gold train-ready after expand** | **135** |
| hard_atoms | 75 → **180** (+105) |
| SoT class promotes (surfaces) | **105** |
| force-train moved | **135** |
| val | **363 → 228** |

Reparse QA: 110/110 promoted rows text-parse == gold. Bar not lowered; punct-only filler held.

## Fair-eval (val changed)

| model / surface | val n | unbind_exact |
|-----------------|------:|-------------:|
| morph36 old val | 363 | 0.5455 |
| morph36 fair morph39 | 338 | 0.5740 |
| **morph36 fair morph40** | **228** | **0.7325** |
| morph40 best ep9 | 228 | **0.7368** |
| morph40 final ep39 | 228 | 0.6930 |

## Gate

| check | result |
|-------|--------|
| morph40 best > fair morph36 (0.7325) same val? | **YES** (0.7368) |
| E2 trunk-forward | **PASS** (1.0) |
| Promote BEST? | **YES** |
| Ladder ≥0.55 on comparable (new) val | **HIT** (fair already 0.7325; morph40 0.7368) |
| Ladder ≥0.55 on old val n=363 | not re-scored; not the gate surface |

## Verdict

**PIN BEST morph40.** Lever (110 INFERRED→OBSERVED train + force-train 135 + hard_atoms 180, warm morph36, SAVE_BEST_UNBIND, 40ep) beat fair morph36 on the expanded-gold val. morph36 weights kept on disk.

## Artifacts

- Package: `receipts/danny-gold-review-partial-slot-miss-20260915/`
- Spark private: `~/hlx-private/p1-spark-morph40-40ep-inferred-promote-20260916/`
- Workspace copy: `receipts/morph40-40ep-inferred-promote-20260916/`
- Spark BEST symlink: `~/.hyperlex/models/BEST` → `...-seed-morph40`
