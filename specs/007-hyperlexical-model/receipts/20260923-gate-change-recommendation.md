# Gate change recommendation — force fair ceiling (2026-09-23)

`name_gate=false`. BEST=**morph65**. Force fair **1.0** n=164. Broad OBSERVED **0.890** n=254.

## Problem

Current promote gate: **same-surface force-fair** — score BEST on val **after** `apply_unbind_force_train`, require **strictly greater** + E2 trunk-forward exact 1.0.

At fair=1.0 that gate is impossible to beat. Force expand cannot help: force keys are removed from val before fair scoring, so fair n does not grow (morph75–77 CANCELLED_FAIR_CEILING).

## Jev

| step | result |
|--|--|
| choice (5 options) | `broad_observed_primary` 0.32 (runner-up `soft_ceiling_tiebreak` 0.29) |
| A/B compare | prefers **soft_ceiling_tiebreak** 0.80 vs broad_observed_primary 0.20 |
| adopt strength | **moderate** — adopt with explicit operator authorize |

## Recommendation (adopt on authorize)

**soft_ceiling_tiebreak** — keep force-fair as primary when it has headroom; when force-fair is already **1.0**, allow promote on a secondary same-surface:

1. **Primary (unchanged when fair < 1.0):** candidate best unbind_exact **>** force-fair exact on that force surface + E2 = 1.0.
2. **Ceiling escape (only when force-fair exact = 1.0):** candidate **broad OBSERVED val** unbind_exact (no force shrink) **>** morph65 baseline **0.889763779527559** n=254 + E2 = 1.0.
3. Force surface remains the train recipe (force/hard expand still legal one-knobs); it is no longer the sole promote wall at the ceiling.
4. Still: no Hub, `name_gate=false`, schemes positional|type_slot, upsample freeze 11+, no SECOND_SLOT=4, no invented OBSERVED.

### Why not full broad-primary yet

Pairwise prefers keeping force-fair when it still discriminates. Soft ceiling preserves ladder history (morph63–74) and only opens a measured escape at the mathematical wall.

### Rejected / deferred

| option | why not now |
|--|--|
| fair_pre_force | Changes surface identity; train≠fair mismatch risk |
| fair_holdout_force | New holdout design + leakage risk; heavier |
| lower_surface_n | Gaming n; can fake progress by deleting hard val |

## Implement only after authorize

Say **`authorize gate soft_ceiling`** (or equivalent). Then:

1. Pin morph65 broad OBSERVED baseline receipt (already in `morph65-broad-residual-diag`).
2. Wire promote/finish scripts: if force-fair == 1.0 → require broad OBSERVED strictly greater; else force-fair strictly greater.
3. Next morph card: one-knob aimed at broad OBSERVED residuals (not force-only ceiling burns).

## Status

**ARMED 2026-09-23** — operator `authorize gate soft_ceiling`. See `20260923-authorize-gate-soft-ceiling.md` + `gate-soft-ceiling-20260923/GATE_SOFT_CEILING.json`.

## Alternate (if you want the larger redesign)

**`authorize gate broad_observed_primary`** — make broad OBSERVED the sole promote metric; force-fair advisory only.
