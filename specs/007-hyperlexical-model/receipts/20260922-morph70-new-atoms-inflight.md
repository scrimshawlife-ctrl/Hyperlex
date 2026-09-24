# morph70 IN FLIGHT — settled new-atoms AUTHORIZE (role-vocab filter) (2026-09-22)

**Authority:** operator recommend-and-continue. `name_gate=false`.

## Recommendation (executed)

After morph69 REJECT (tie fair 0.9649 n=171) with residual AUTHORIZE=0 and METHOD residual gold exhausted, integrate settled `local-label-new-atoms` AUTHORIZE (SoT OBSERVED via PACKET_SETTLE; never force-trained).

## Role-vocab filter

First launch aborted: `HYPERLEX_INIT_FROM role_vocab mismatch (init=10 current=12)`.
morph65 role head is `pos_0..pos_5` only. 23 AUTHORIZE atoms need `pos_6`/`pos_7` → dropped for this warm climb.

| | n |
|--|--:|
| packet AUTHORIZE | 25 |
| role-vocab compat (fillers≤6) | **2** (`took an L`, `big W`) |
| dropped | 23 |

## Knob

| | |
|--|--|
| force_added | **2** (192→**194**) |
| hard_added | **2** (233→**235**) |
| fair morph65 | **0.9649122807017544** n=171 |
| warm | morph65 |
| UPSAMPLE / SECOND_SLOT | 8 / 2 held |
| container | `hlx-train-morph70-1790092833` (relaunch after role-vocab filter) |

PIN iff best > fair **0.9649122807017544** n=171 and E2 trunk-forward `unbind_exact=1.0`.

Longer atoms remain held for a future non-warm / role-head-expand path — not this card.
