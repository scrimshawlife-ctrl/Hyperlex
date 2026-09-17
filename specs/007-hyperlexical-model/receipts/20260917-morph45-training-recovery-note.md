# training-recovery note — morph45 (2026-09-17)

Append to `training-recovery.md` operator log:

### 2026-09-17 — morph45 BLOCKED (invalid Spark loop.py)

- Intent: LEGAL recipe `HEAD_SLOT=3` on morph40 gold (force 135 / hard 180), warm INIT_FROM + SAVE_BEST, mem 0.3.
- Live env matched intent; Spark `loop.py` at launch was a **471-line regression** (no INIT_FROM / SAVE_BEST / force-train).
- Decision: **BLOCKED** — `docker stop` morph45; no promote; BEST remains morph40.
- Remediation: restored workspace `loop.py` + `unbind_recipe.py` on Spark; bad copies under `~/hlx/backups/`.
- Workspace: `receipts/20260917-morph45-blocked-invalid-launch.md`, `receipts/morph45-40ep-head-slot3-20260916/BLOCKED_INVALID_LAUNCH.md`.

### 2026-09-17 — morph45 RELAUNCH IN FLIGHT (restored loop)

- Preflight: Spark `loop.py` **712** lines; INIT_FROM / SAVE_BEST / `apply_unbind_force_train` confirmed inside container.
- Same intent card: HEAD_SLOT=3, warm morph40, SAVE_BEST=1, force 135 / hard 180, mem 0.3, 40ep.
- Fair surface: **morph40 n=228** baseline **0.7368** — no recompute (force path unchanged).
- Container: `hlx-train-morph45-1789620853`. BEST still morph40 until gate.
- Single gate: relaunch agent; escalate peer empty transcript.
- Workspace: `receipts/20260917-morph45-relaunch-inflight.md`, `receipts/morph45-40ep-head-slot3-relaunch-20260917/`.
