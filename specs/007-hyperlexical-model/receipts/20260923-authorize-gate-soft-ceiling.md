# Authorize gate soft_ceiling — ARMED (2026-09-23)

`name_gate=false`. BEST=**morph65** (held).

## Authority

Operator: **`authorize gate soft_ceiling`**.

Implements `soft_ceiling_tiebreak` from `20260923-gate-change-recommendation.md` (Jev pairwise prefer 0.80).

## Pin

| surface | exact | n |
|--|--:|--:|
| force-fair morph65 | **1.0** | 164 |
| broad OBSERVED authorize pin (historical) | **0.889763779527559** | 254 |
| broad OBSERVED live prior post-morph77 settle | **0.88671875** | 256 |

Durable pin: `gate-soft-ceiling-20260923/GATE_SOFT_CEILING.json`.

Live ceiling escape compares candidate vs **fresh PRIOR morph65** broad eval on current SoT (same n). Authorize pin is fallback only.

## Promote rules (armed)

1. **force-fair < 1.0:** candidate best **>** force-fair + same n + E2 1.0 (unchanged).
2. **force-fair = 1.0:** candidate **broad OBSERVED** (no force) **>** PRIOR morph65 broad on same live surface + E2 1.0. Do **not** cancel solely because force-fair is already 1.0.

## Spark wire

- `~/hlx/GATE_SOFT_CEILING.json`
- `~/hlx/eval_broad_observed.py` — score any model on broad OBSERVED val
- `~/hlx/gate_soft_ceiling_decide.py` — shared promote decision
- `~/hlx/finish_soft_ceiling.py` — finish template for morphs under this gate

## Next morph

Gold force card from morph65 residual AUTHORIZE is **empty** (Jev defer_quality=8). Under soft_ceiling: **fresh acquire + METHOD morph43** aimed at broad OBSERVED residuals → settle → morph78 warm morph65. Not force-only ceiling burns. Upsample freeze 11+. No SECOND_SLOT=4.
