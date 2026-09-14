# Spec 007 — famcls48 KEEP pin; famcls49 IN FLIGHT; SSH blocked

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.
**Climb KEEP ≠ BEST.** Human review + Danny `name_gate` required before any promotion.

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
| famcls46 | accept24 | 0.25 / 8 | **0.9899** | **1.0** | KEEP (climb) | **no** |
| famcls47 | accept25 | 0.25 / 8 | **0.9949** | **0.958** | **REJECT** | no |
| famcls48 | accept25 | **0.35** / **12** | **0.9949** | **1.0** | **KEEP** | **no** |
| famcls49 | accept26 | 0.35 / 12 | — | — | **IN FLIGHT** (last seen ep~7) | — |

## Blocked
Spark SSH via `cloudflared access` → `websocket: bad handshake` (2026-09-14 ~19:58Z onward).
famcls49 was launched cleanly before the outage; train should finish on-host. Resume poll when tunnel recovers: gate family > **0.9949494949494949** + structure/role/pointer == 1.0.

## Policy
OBSERVED hold. No BEST overwrite. Full 40-epoch runs. Climb KEEP ≠ BEST.
