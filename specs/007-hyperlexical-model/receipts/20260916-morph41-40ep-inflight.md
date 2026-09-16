# morph41 IN FLIGHT — warm morph40, no new gold (2026-09-16)

**Authority:** Spec 007. `name_gate=false`. Labeler authorized; **no new gold promoted**.  
**BEST held:** **morph40** (artifacts preserved). morph36 preserved.

## Lever

ONE lever: warm-init from morph40 BEST (primary = best ep9 **0.7368**) + `SAVE_BEST_UNBIND=1`; epochs=40; **existing** expanded gold only.

| item | n / value |
|------|-----------|
| gold train-ready | **135** (unchanged) |
| hard_atoms | **180** (unchanged) |
| force-train | `force_train_morph40_expanded.jsonl` |
| val | **228** (unchanged) |
| residual review | 20 auth / 8 abstain / **0** train promote |

## Fair baseline (gate)

| surface | unbind_exact |
|---------|-------------:|
| morph36 fair morph40 val (n=228) | 0.7325 |
| **morph40 BEST (fair morph41 gate)** | **0.7368** |

Gate: promote morph41→BEST only if best **> 0.7368** on same val; else REJECT and keep morph40 BEST.

## Train

| field | value |
|-------|-------|
| init | `HYPERLEX_INIT_FROM=...-seed-morph40` |
| SAVE_BEST_UNBIND | 1 |
| epochs | 40 |
| out | `...-seed-morph41` |
| container | `hlx-train-morph41-1789537012` |

## Status

**IN FLIGHT** — awaiting 40ep + E2 + gate vs fair morph40 0.7368.
