# morph41 — warm morph40 REJECT_VS_BEST (2026-09-16)

**Authority:** Spec 007. `name_gate=false`. Labeler authorized; **no new gold** this climb.  
**BEST held:** **morph40** (`unbind_exact≈0.7368` ep9 on fair val n=228). morph36 artifacts preserved.

## Lever

ONE lever: warm-init from morph40 BEST (primary = best ep9 **0.7368**) + `SAVE_BEST_UNBIND=1`; epochs=40; **existing** expanded gold only (force-train **135** / hard_atoms **180** unchanged). Residual review held 20 authorized structure out of train.

## Scores (same val n=228)

| surface | unbind_exact |
|---------|-------------:|
| morph36 fair morph40 | 0.7325 |
| **morph40 BEST (fair gate)** | **0.7368** |
| morph41 best ep3 | **0.7149** |
| morph41 final ep39 | 0.6711 |

Container `hlx-train-morph41-1789537012` exited 0 (~86 min wall). Guard **`mem_fraction=0.015`** (~2 GB) for this run — **not** restarted mid-flight. Next morph launch uses default **`0.3`** (PR #80 / `scripts/spark/run_morph_train.sh`).

## Gate

| check | result |
|-------|--------|
| morph41 best > fair morph40 (0.7368) same val? | **NO** (0.7149) |
| E2 trunk-forward | **PASS** (1.0) |
| Promote BEST? | **NO** |
| Competing Continue-agent pin? | none at gate time — single REJECT |

## Verdict

**REJECT_VS_BEST.** Warm morph40 alone on unchanged gold did not beat fair morph40. BEST stays **morph40**.

## Artifacts

- Spark BEST symlink: `~/.hyperlex/models/BEST` → `...-seed-morph40` (unchanged)
- Spark private: `~/hlx-private/p1-spark-morph41-40ep-warm-morph40-20260916/`
- Workspace: `receipts/morph41-40ep-warm-morph40-20260916/` (`STATUS.txt` = REJECT_VS_BEST)
- Pin JSON: `pin-no-promote.json` / `pin-morph41.json`
- Mem-fraction note: `receipts/20260916-cuda-mem-fraction-speed-lever.md` (morph41 left on 0.015)
