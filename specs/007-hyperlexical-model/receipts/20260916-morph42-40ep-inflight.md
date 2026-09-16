# morph42 IN FLIGHT — warm morph40 @ mem_fraction 0.3 (2026-09-16)

**Authority:** Spec 007. `name_gate=false`. Labeler authorized; **no new gold**.  
**BEST held:** **morph40** (`unbind_exact≈0.7368` ep9 on fair val n=228). morph41 REJECT_VS_BEST (0.7149).

## Lever

ONE lever vs morph41: exclusive **`HYPERLEX_CUDA_MEM_FRACTION=0.3`** (cap ~39 GB) instead of morph41’s **0.015** (~2 GB). Same warm-init morph40 BEST + `SAVE_BEST_UNBIND=1`; epochs=40; existing expanded gold only (force-train **135** / hard_atoms **180**).

| item | n / value |
|------|-----------|
| gold train-ready | **135** (unchanged) |
| hard_atoms | **180** (unchanged) |
| force-train | `force_train_morph40_expanded.jsonl` |
| val | **228** (unchanged) |
| mem_fraction | **0.3** (morph41 was 0.015) |

## Fair baseline (gate)

| surface | unbind_exact |
|---------|-------------:|
| **morph40 BEST (fair morph42 gate)** | **0.7368** |
| morph41 best (REJECT) | 0.7149 |

Gate: promote morph42→BEST only if best **> 0.7368** on same val; else REJECT and keep morph40 BEST.

## Train

| field | value |
|-------|-------|
| init | `HYPERLEX_INIT_FROM=...-seed-morph40` |
| SAVE_BEST_UNBIND | 1 |
| epochs | 40 |
| out | `...-seed-morph42` |
| container | `hlx-train-morph42-1789542688` |
| guard | `frac=0.3` env_override=True `cap=39.2GB` |

## Speed baseline (before)

| run | guard | wall (40ep) |
|-----|------:|------------:|
| morph39 | 0.015 | ~73 min |
| morph40 | 0.015 | ~80 min |
| morph41 | 0.015 | ~86 min |
| **morph42** | **0.3** | **~87 min** |

## Status

**COMPLETE → REJECT_VS_BEST** — see `20260916-morph42-40ep-reject-vs-best.md`.  
best **0.7149** (ep3) < fair morph40 **0.7368**; E2 PASS; BEST stays morph40.  
Wall **~87.1 min** @ mem **0.3** (no speedup vs morph39–41 @ 0.015).
