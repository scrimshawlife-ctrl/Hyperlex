# Spec 007 — famcls48 KEEP pin; famcls49 relaunched; SSH flaky

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.
**Climb KEEP ≠ BEST.**

## Pins
| pin | path | note |
|-----|------|------|
| **weight (climb KEEP)** | `~/hlx-private/p1-structure-unbind-famcls48-20260914/` | family **0.9949** / struct·role·ptr **1.0** — aux=0.35/up=12 — **not** BEST |
| **data** | `~/hlx-private/p1-classify-accept26-20260914/prepare` | +14 force-train (`sigma grindset`) |
| **preserved (not BEST)** | `~/hlx-private/preserved/famcls45-20260914/` | snapshot; originals intact |
| **BEST** | morph19 | **untouched** |

## Ladder (recent)
| run | data | aux / up | family | structure | climb verdict | BEST? |
|-----|------|----------|--------|-----------|---------------|-------|
| famcls46 | accept24 | 0.25 / 8 | **0.9899** | **1.0** | KEEP (climb) | no |
| famcls47 | accept25 | 0.25 / 8 | **0.9949** | **0.958** | REJECT | no |
| famcls48 | accept25 | **0.35** / **12** | **0.9949** | **1.0** | **KEEP** | **no** |
| famcls49 | accept26 | 0.35 / 12 | — | — | **RELAUNCHED** (was dead @ep7; clean 40ep restart 2026-09-15 ~04:28Z; last polled ~ep22 before SSH drop) | — |

## Ops
- Spark briefly reachable 2026-09-15 ~04:27Z: confirmed famcls48 KEEP smoke; famcls49 had died mid-run; GPU idle → relaunched.
- SSH via cloudflared failing again (`websocket: bad handshake` / port 65535) as of ~04:49Z.
- On resume: poll famcls49 SMOKE; gate family > **0.9949494949494949** AND structure/role/pointer == **1.0**.

## Policy
OBSERVED hold. No BEST overwrite. Climb KEEP ≠ BEST. Full 40-epoch runs.
