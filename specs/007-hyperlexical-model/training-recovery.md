# Training recovery: Spec 007 morph log

> WF-003 / prep contract body: unchanged from Hyperlex `main` @ `ede3d6c` (pre-existing mid-sentence truncate). This tip restores that body from main and appends morph47/48 settlement.

## BOUNDARY

This does not govern or activate. Existing doctrine, ontology, name gate and
operator authority remain unchanged. No Notion writeback, training or promotion.

### 2026-09-17 — morph47 curriculum POS=3 → REJECT_VS_BEST

- Lever: `HYPERLEX_UNBIND_CURRICULUM_POS_EPOCHS=3` (was 1); TYPE=1 / HARD=4 / HEAD_SLOT=2 held; morph40 gold; warm morph40 + SAVE_BEST; mem 0.3; 40ep.
- Result: best `unbind_exact=0.7149122807017544` (ep8) < fair morph40 **0.7368421052631579** (n=228) → **REJECT_VS_BEST**.
- Container: `hlx-train-morph47-1789633911` exit 0. E2 PASS. BEST remains morph40.
- Workspace: `receipts/20260917-morph47-40ep-reject-vs-best.md`, `receipts/morph47-40ep-curriculum-pos3-20260917/`.

### 2026-09-17 — morph48 LAST_TRAINABLE=6 → PROMOTE_BEST

- Lever: `HYPERLEX_LAST_TRAINABLE=6` (was 4); POS=1 / HARD=4 / HEAD_SLOT=2 held; morph40 gold; warm morph40 + SAVE_BEST; mem 0.3; 40ep.
- Result: best `unbind_exact=0.7412280701754386` (ep19) > fair morph40 **0.7368421052631579** (n=228); E2 PASS → **PROMOTE_BEST**.
- Spark BEST symlink → `seed-morph48`. morph40 + morph36 preserved. `name_gate=false`.
- Container: `hlx-train-morph48-1789639062` exit 0 (launched by `bc-3e55c42d`).
- Workspace: `receipts/20260917-morph48-40ep-promote-best.md`, `receipts/morph48-40ep-last6-20260917/`.

### 2026-09-17 — morph49 LAST=7 intent LEGAL; launch BLOCKED (SSH tunnel)

- Planned lever: `HYPERLEX_LAST_TRAINABLE=7` (was 6 on BEST); POS/HARD/HEAD held; morph40 gold; warm **morph48** + SAVE_BEST; mem 0.3; 40ep.
- Fair gate: morph48 **0.7412280701754386** on n=228.
- Blocker: Cloudflare Tunnel **1033** on `ssh.zer0state.com` and `qwen.zer0state.com` (`websocket: bad handshake`). WAN/LAN SSH timeout. No container. BEST stays morph48.
- Workspace: `receipts/20260917-morph49-ssh-blocked.md`, `receipts/morph49-40ep-last7-20260917/`.

### 2026-09-18 — morph49 LAST=7 resumed → PROMOTE_BEST

- Tunnel recovered (`ssh spark` → `spark-bf46` / `morpheus`). Launched `hlx-train-morph49-1789694077` (no duplicate train).
- Result: best `unbind_exact=0.7850877192982456` (ep27) > fair morph48 **0.7412280701754386** (n=228); E2 PASS → **PROMOTE_BEST**.
- Spark BEST symlink → `seed-morph49`. morph48 + morph40 + morph36 preserved. `name_gate=false`.
- Single pin via `GATE_LOCK.json` (owner `bc-ad3024d5-f1c6-5e5a-8c5e-757ca53e37d1`).
- Workspace: `receipts/20260918-morph49-40ep-promote-best.md`, `receipts/morph49-40ep-last7-20260917/`.

### 2026-09-18 — morph50 LAST=8 +2 residual gold IN FLIGHT

- Confirmed Spark BEST=`seed-morph49`. Morph49 residuals n=49: authorize **39** / abstain **10**; **+2** new train-ready (`TOKEN:jailbreak SLOT:prompt`, `boon coon` + SoT flip).
- Force 135→137; hard 180→182. Fair morph49 recomputed **0.7920353982300885** (n=226).
- Lever: `HYPERLEX_LAST_TRAINABLE=8` (MAX) warm morph49 + SAVE_BEST; mem 0.3; 40ep.
- Gate: morph50 best > fair morph49 on n=226. Workspace: `receipts/20260918-morph50-40ep-inflight.md`, `receipts/morph50-40ep-last8-20260918/`.

### 2026-09-18 — morph50 LAST=8 +2 gold → PROMOTE_BEST

- Container `hlx-train-morph50-1789703143` Exited 0. best `unbind_exact=0.8097345132743363` (ep38) > fair morph49 **0.7920353982300885** (n=226); E2 PASS → **PROMOTE_BEST**.
- Spark BEST symlink → `seed-morph50`. morph49 + morph48 + morph40 + morph36 preserved. `name_gate=false`.
- Sibling gate owner `bc-b4ecc915-ddac-5aaa-9cce-e29d15c18061` RUNNING/silent; coordinator claimed `morph50-gate.lock` and completed gate.
- Workspace: `receipts/20260918-morph50-40ep-promote-best.md`, `receipts/morph50-40ep-last8-20260918/`.
- LAST=8 is MAX — no further LAST one-delta without new gold / other legal family.
