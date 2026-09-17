# morph45 — BLOCKED / REJECT (invalid launch code)

**Observed:** 2026-09-17T04:49Z UTC · `spark-bf46`  
**Authority:** Spec 007. `name_gate=false`.  
**Decision:** **BLOCKED** — train **stopped**; **do not promote**. BEST stays **morph40**.

## Recipe intent (documented) vs live code

Documented morph45 lever was legal on paper: `HEAD_SLOT=3` on morph40 gold (force 135 / hard 180), warm `INIT_FROM=morph40`, `SAVE_BEST_UNBIND=1`, val n=228.

Live container env matched that intent. **But** Spark `~/Hyperlex/scripts/shadow/hyperlexical/loop.py` at launch was a **regressed 471-line** tree (mtime 2026-09-16 22:26, rewritten at start) that **ignored**:

| env / lever | documented | live `loop.py` at launch |
|-------------|------------|--------------------------|
| `HYPERLEX_INIT_FROM=morph40` | warm start | **absent** (cold train) |
| `HYPERLEX_SAVE_BEST_UNBIND=1` | best-by-unbind primary | **absent** |
| `HYPERLEX_UNBIND_FORCE_TRAIN_PATH` (morph40 135) | fair morph40 surface | **absent** (`prepare_unbind_splits` left val untouched; no `apply_unbind_force_train`) |
| `HYPERLEX_UNBIND_HARD_ATOMS_PATH` | via recipe | present in `unbind_recipe` only if imported path used |
| `HYPERLEX_UNBIND_HEAD_SLOT_WEIGHT=3` | recipe delta | present in regressed file |

So this was **not** a fair morph40-surface HEAD_SLOT climb, and **not** the documented warm+SAVE_BEST recipe. It is also **not** a morph43/44 residual warm+force clone (force path pointed at morph40 files; residual gold unused) — it is an **invalid launch**.

## Actions taken

1. `docker stop hlx-train-morph45-1789619192` (exit 137). No `train-receipt.json` written.
2. BEST symlink unchanged → `...-seed-morph40`. `model.safetensors` mtime unchanged.
3. Backed up bad files under `~/hlx/backups/loop.py.morph45-bad-*` / `unbind_recipe.py.morph45-bad-*`.
4. Restored workspace `loop.py` (711 lines, SAVE_BEST+INIT_FROM) and `unbind_recipe.py` (force_train) onto Spark Hyperlex for the next legal relaunch.

## Scores

| metric | value |
|--------|------:|
| morph45 best unbind_exact | **n/a** (stopped mid-run; no receipt) |
| morph40 fair baseline (n=228) | **0.7368** |
| Promote? | **NO** |

## Gate ownership

Single gate: this watch agent. Escalate agent `bc-9ecde051…` RUNNING with **empty** transcript — did not own gate.

## Next

Relaunch morph45 only after confirming Spark imports restored `loop.py` (`SAVE_BEST` / `INIT_FROM` / force-train). Same intent card; fair gate unchanged.
