# Spec 007 — famcls46 climb KEEP; famcls47 in flight; BEST unchanged

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.
**Climb KEEP ≠ BEST.** Human review + Danny `name_gate` required before any promotion.

## Pins
| pin | path | note |
|-----|------|------|
| **weight (climb KEEP)** | `~/hlx-private/p1-structure-unbind-famcls46-20260914/` | family **0.9899** / struct·role·ptr **1.0** — **not** BEST |
| **data** | `~/hlx-private/p1-classify-accept25-20260914/prepare` | `rows_sha256=e037bbeee940…` (+24 force-train) |
| **preserved (not BEST)** | `~/hlx-private/preserved/famcls45-20260914/` | snapshot of famcls45; originals intact |
| **BEST** | morph19 | **untouched** (symlink + weights) |

## Ladder (recent)
| run | data | aux / up | family | structure | climb verdict | BEST? |
|-----|------|----------|--------|-----------|---------------|-------|
| famcls43 | accept23 | 0.12 / 4 | **0.9848** | **0.958** | REJECT | no |
| famcls44 | accept23 | 0.18 / 4 | **0.9697** | **0.958** | REJECT | no |
| famcls45 | accept23 | 0.25 / 8 | **0.9545** | **1.0** | KEEP (climb) | **no — preserved only** |
| famcls46 | accept24 | 0.25 / 8 | **0.9899** | **1.0** | KEEP (climb) | **no** |
| famcls47 | accept25 | 0.25 / 8 | — | — | **IN FLIGHT** | — |

## Holdout compare (fixed accept23)
Receipt: `specs/007-hyperlexical-model/receipts/20260914-famcls43-vs-44-accept23-holdout.md`  
Shared structure miss: `sheesh moment` positional pointer slot1 (3→2). Aux↑ from 0.12→0.18 hurt family, did not fix structure.

## Non-promotion
- famcls45: preserved under `~/hlx-private/preserved/famcls45-20260914/`; did not beat morph19 civilian val pin.
- famcls46: Climb KEEP only. Candidate `PROMOTION_RECEIPT.md` on Spark = **DO NOT PROMOTE**.
- Active model remains morph19. No Hub.

## Gate (famcls47) — IN FLIGHT
Init famcls46 · N=8 · LR 5e-6 · aux=0.25 · upsample=8 · 40 ep · accept25.  
family > **0.98989898989899** AND structure/role/pointer == **1.0**.  
(~epoch 5 as of doc update; do not clear GPU while running / Danny queue unknown.)

## Dataset SHAs
| prepare | rows_sha256 |
|---------|-------------|
| accept23 | `9828e140c541403f2409c4ba5c7b826dbfe882ff512dcd43209d864f0c933199` |
| accept24 | `4e34f57d0f4bcc0bb504e89e43e9bb052cd0026a453fe818535e078da18a716a` |
| accept25 | `e037bbeee940b06eedd9be2ecf26a039003bb617455a4e4805504d15bb351730` |

## Policy
OBSERVED hold. No BEST overwrite. Full 40-epoch runs. Record checkpoint + dataset SHA + config + eval receipt before any future promotion.
