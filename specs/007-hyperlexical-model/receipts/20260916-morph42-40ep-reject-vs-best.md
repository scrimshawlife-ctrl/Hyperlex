# morph42 — warm morph40 @ mem 0.3 REJECT_VS_BEST (2026-09-16)

**Authority:** Spec 007. `name_gate=false`. Labeler authorized; **no new gold** this climb.  
**BEST held:** **morph40** (`unbind_exact≈0.7368` ep9 on fair val n=228). morph36 artifacts preserved.

## Lever

ONE lever vs morph41: exclusive **`HYPERLEX_CUDA_MEM_FRACTION=0.3`** (cap ~39 GB) instead of morph41’s **0.015** (~2 GB). Warm-init morph40 BEST + `SAVE_BEST_UNBIND=1`; epochs=40; existing expanded gold only (force-train **135** / hard_atoms **180**).

## Scores (same val n=228)

| surface | unbind_exact |
|---------|-------------:|
| **morph40 BEST (fair gate)** | **0.7368** |
| morph41 best ep3 @ 0.015 | 0.7149 |
| morph42 best ep3 @ **0.3** | **0.7149** |
| morph42 final ep39 | 0.6711 |

Container `hlx-train-morph42-1789542688` exited 0. Guard **`frac=0.3`** `cap=39.2GB` env_override=True.

## Speed note (before / after)

| run | guard | wall (40ep) |
|-----|------:|------------:|
| morph39 | 0.015 | ~73 min |
| morph40 | 0.015 | ~80 min |
| morph41 | 0.015 | ~85 min |
| **morph42** | **0.3** | **~87 min** |

**No wall speedup** at 0.3 vs 0.015. Resident train GPU mem stayed ~1.2 GiB (ModernBERT last-N / batch 8); allocator thrash was not the bottleneck. Keep default **0.3** for headroom; do not expect shorter climbs from the fraction alone on this recipe.

## Gate

| check | result |
|-------|--------|
| morph42 best > fair morph40 (0.7368) same val? | **NO** (0.7149) |
| E2 trunk-forward | **PASS** (1.0) |
| Promote BEST? | **NO** |

## Verdict

**REJECT_VS_BEST.** Mem-fraction 0.3 alone (same warm morph40 + gold) did not beat fair morph40 — score matched morph41’s peak. BEST stays **morph40**.

## Artifacts

- Spark BEST symlink: `~/.hyperlex/models/BEST` → `...-seed-morph40` (unchanged)
- Spark private: `~/hlx-private/p1-spark-morph42-40ep-warm-morph40-mem03-20260916/`
- Workspace: `receipts/morph42-40ep-warm-morph40-mem03-20260916/` (`STATUS.txt` = REJECT_VS_BEST)
- Pin JSON: `pin-no-promote.json` / `pin-morph42.json`
