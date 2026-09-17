# morph45 — HEAD_SLOT=3 RELAUNCH IN FLIGHT (2026-09-17)

**Authority:** Spec 007. `name_gate=false`. Labeler authorized.  
**BEST held:** morph40 (`unbind_exact≈0.7368`, fair val **n=228**).

## Prior attempt

Attempt 1 **BLOCKED** — Spark `loop.py` 471-line regression ignored INIT_FROM/SAVE_BEST/FORCE_TRAIN. See `20260917-morph45-blocked-invalid-launch.md`.

## Relaunch preflight (OBSERVED)

| check | result |
|-------|--------|
| Spark `loop.py` lines | **712** (workspace md5 match) |
| `HYPERLEX_INIT_FROM` in loop | **Y** (in-container) |
| `HYPERLEX_SAVE_BEST_UNBIND` in loop | **Y** |
| `apply_unbind_force_train` | **Y** |
| GPU free before launch | **Y** (no other `hlx-train-*` running) |
| Escalate peer train/gate | **N** — `bc-9ecde051…` empty transcript |

## Intent card (unchanged)

- `HEAD_SLOT=3` (was 2)
- Warm `INIT_FROM=morph40` + `SAVE_BEST_UNBIND=1`
- Force 135 / hard 180 morph40 paths
- 40ep, batch 8, LR 2e-5, mem **0.3** exclusive

## Fair surface

**Same morph40 surface — no fair recompute.** Force-train leaves val **n=228**; gate **> 0.7368421052631579**.

## Artifacts

- Container: `hlx-train-morph45-1789620853`
- Out: `~/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph45`
- Private: `~/hlx-private/p1-spark-morph45-40ep-head-slot3-relaunch-20260917/`
- Gate owner: `bc-cc8b0f28-51fa-551f-8edc-8f9abb7744a4`
