# Spec 007 — famcls47 REJECT; famcls48 aux=0.35/up=12 in flight; BEST unchanged

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.
**Climb KEEP ≠ BEST.** Human review + Danny `name_gate` required before any promotion.

## Pins
| pin | path | note |
|-----|------|------|
| **weight (climb KEEP)** | `~/hlx-private/p1-structure-unbind-famcls46-20260914/` | family **0.9899** / struct·role·ptr **1.0** — **not** BEST |
| **data** | `~/hlx-private/p1-classify-accept25-20260914/prepare` | `rows_sha256=e037bbeee940…` |
| **preserved (not BEST)** | `~/hlx-private/preserved/famcls45-20260914/` | snapshot; originals intact |
| **BEST** | morph19 | **untouched** |

## Ladder (recent)
| run | data | aux / up | family | structure | climb verdict | BEST? |
|-----|------|----------|--------|-----------|---------------|-------|
| famcls45 | accept23 | 0.25 / 8 | **0.9545** | **1.0** | KEEP (climb) | **no — preserved** |
| famcls46 | accept24 | 0.25 / 8 | **0.9899** | **1.0** | KEEP (climb) | **no** |
| famcls47 | accept25 | 0.25 / 8 | **0.9949** | **0.958** | **REJECT** | no |
| famcls48 | accept25 | **0.35** / **12** | — | — | **IN FLIGHT** | — |

## famcls47 REJECT
Init famcls46 · aux=0.25 · up=8 · 40 ep (best 8).  
family **0.9949** > 0.9899 PASS; structure/pointer **0.958** FAIL; role 1.0; `best_unchanged=true`.  
Single miss: **`sheesh moment`** positional — pointer slot1 gold_start=3 pred_start=2 (same hole as 43/44).

## Gate (famcls48) — IN FLIGHT
Init famcls46 · accept25 · N=8 · LR 5e-6 · **aux=0.35** · **upsample=12** · 40 ep.  
family > **0.98989898989899** AND structure/role/pointer == **1.0**.

## Non-promotion
famcls45 preserved; famcls46 climb KEEP only; no morph19 civilian eval yet. No Hub. No BEST overwrite.

## Dataset SHAs
| prepare | rows_sha256 |
|---------|-------------|
| accept23 | `9828e140c541403f2409c4ba5c7b826dbfe882ff512dcd43209d864f0c933199` |
| accept24 | `4e34f57d0f4bcc0bb504e89e43e9bb052cd0026a453fe818535e078da18a716a` |
| accept25 | `e037bbeee940b06eedd9be2ecf26a039003bb617455a4e4805504d15bb351730` |

## Policy
OBSERVED hold. Full 40-epoch runs. Record checkpoint + dataset SHA + config + eval receipt before any future promotion. Do not clear GPU while famcls48 runs.
