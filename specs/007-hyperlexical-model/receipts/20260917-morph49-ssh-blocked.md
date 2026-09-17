# morph49 — BLOCKED (Spark tunnel down) (2026-09-17)

**Authority:** Spec 007. `name_gate=false`.
**BEST held:** **morph48** (`unbind_exact≈0.7412`, fair val **n=228**). morph40 + morph36 preserved.

## Planned LEGAL lever (not launched)

| field | value |
|-------|-------|
| morph | **49** |
| delta | `HYPERLEX_LAST_TRAINABLE=7` (was 6 on BEST) |
| warm | `INIT_FROM=morph48` + `SAVE_BEST_UNBIND=1` |
| gold | morph40 force 135 / hard 180 |
| held | POS=1 / TYPE=1 / HARD=4 / HEAD_SLOT=2 / LR=2e-5 / mem=0.3 / 40ep |
| fair gate | best **> 0.7412280701754386** on n=228 |

Justification: escalate last-N after morph48 KEEP; ≠ identical LAST=6; ≠ residual warm+force; ≠ HEAD_SLOT=3 / HARD=6 / POS=3.

## Blocker

Cloudflare Tunnel to Spark is **down**:

- `https://ssh.zer0state.com/` → HTTP **530** / error **1033**
- `cloudflared access ssh` → `websocket: bad handshake`
- Direct WAN `12.38.208.106:22` and LAN `192.168.12.202:22` → timeout
- Qwen gateway `https://qwen.zer0state.com/` also **530/1033** (origin offline, not SSH-key-only)

No container launch. No BEST overwrite. No Hub.

## Resume

When `ssh spark 'hostname'` returns `spark-bf46`:

1. Confirm `BEST` → `seed-morph48` and restored `loop.py` (INIT_FROM / SAVE_BEST / force-train).
2. Launch morph49 via `~/hlx/run_morph_train.sh 49` with ENV from `receipts/morph49-40ep-last7-20260917/ENV.txt`.
3. Fair-gate vs morph48; promote only if best > fair; else REJECT → morph50 (e.g. LAST=8 or LAST=6+mild LR).

## Coordination

Agent `bc-461a96cc`. Intent + LEGAL card landed under `receipts/morph49-40ep-last7-20260917/`.
