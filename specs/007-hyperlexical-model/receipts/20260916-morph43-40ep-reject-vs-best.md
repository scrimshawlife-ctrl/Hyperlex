# morph43 — held residual gold REJECT_VS_BEST (2026-09-16)

**Authority:** Spec 007. `name_gate=false`. Labeler authorized. Schemes `positional` | `type_slot` only.  
**BEST held:** **morph40** (prior fair n=228 ≈0.7368; morph43-gate fair n=177 = **0.9492**). morph36 preserved.

## Lever

ONE lever vs morph41/42 warm-only REJECT: **promote held morph40 residual gold** into train.

| item | before → after |
|------|----------------|
| authorize / abstain | **51** / **9** (of 60 residuals) |
| force-train | **135 → 186** (+51) |
| hard_atoms | **180 → 226** (+46) |
| SoT flip INFERRED→OBSERVED | **45** surfaces |
| schemes | positional **32** / type_slot **19** |
| mem_fraction | **0.3** |
| init | warm morph40 BEST + `SAVE_BEST_UNBIND=1` |
| epochs | 40 |

Gold delta receipts: `morph43-held-gold-promote-20260916/` (`PROMOTE_SUMMARY.json`, `LABEL_COUNTS.json`, force/hard deltas).

## Scores (same val n=177)

| surface | unbind_exact |
|---------|-------------:|
| **morph40 BEST (fair gate)** | **0.9492** |
| morph43 best ep2 | **0.9379** |
| morph43 final ep39 | 0.8870 |

Container `hlx-train-morph43-1789549404` exited 0 (~**86.3 min**). Guard **`frac=0.3`** `cap=39.2GB` env_override=True. E2 PASS (1.0).

## Gate

| check | result |
|-------|--------|
| morph43 best > fair morph40 (0.9492) same val n=177? | **NO** (0.9379) |
| E2 trunk-forward | **PASS** (1.0) |
| Promote BEST? | **NO** |

## Verdict

**REJECT_VS_BEST.** Held-gold expand moved 51 rows val→train and recomputed fair morph40 on n=177 = **0.9492**; morph43 best **0.9379** (ep2) did not clear it (Δ ≈ −0.0113). BEST stays **morph40**. `name_gate` false.

## Artifacts

- Spark BEST symlink: `~/.hyperlex/models/BEST` → `...-seed-morph40` (unchanged)
- Spark private: `~/hlx-private/p1-spark-morph43-40ep-held-gold-20260916/`
- Workspace: `receipts/morph43-40ep-held-gold-20260916/` (`STATUS.txt` = REJECT_VS_BEST)
- Pin JSON: `pin-no-promote.json` / `pin-morph43.json`
- Inflight → complete: `receipts/20260916-morph43-40ep-inflight.md`
