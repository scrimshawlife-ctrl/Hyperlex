# Spec 007 — next: morph78 soft_ceiling train IN_FLIGHT

`name_gate=false`. BEST=**morph65** (held). Upsample freeze = **11+**. Do not run SECOND_SLOT=4.

## Done

- morph78 named phrases settled OBSERVED val · force/hard **236/277** · **SOFT_CEILING_CONTINUE**.
- Train **`hlx-train-morph78-1790221699`** IN_FLIGHT (poller alive).

## Live (poll 2026-09-24 ~04:53Z)

| epoch | unbind_exact | best |
|------:|-------------:|-----:|
| 0–6 | … | **0.9939** (ep3) |

No `train-receipt` yet (40ep). soft_ceiling finish after train + E2 + broad.

## Next

1. Await train complete → poll E2 + PRIOR/candidate broad → soft_ceiling decide.
2. Do not flip `name_gate`. Do not Hub.

Qwen stays stopped unless re-enabled.
