# Blocker — Spark Cloudflare Tunnel DOWN (2026-09-17)

**Authority:** Spec 007. `name_gate=false`.  
**Confirmed by:** Restore Spark SSH tunnel agent `bc-05254bda-8caf-598f-9998-55c0cef8a401`.  
**Paused agents:** Continue train vs morph48 (`bc-461a96cc`); this run.

## Verdict

**SSH DOWN** — Cloudflare Tunnel/Access **front door**, not SSH keys/config. Backoff exhausted.

| probe | result |
|-------|--------|
| `ssh.zer0state.com` | websocket **bad handshake**; HTTP **530** |
| `qwen.zer0state.com` | HTTP **530** (same origin/tunnel path) |
| Direct WAN / LAN :22 | unreachable (as previously noted) |

## Training pause

- **morph49+ PAUSED** — do **not** local fake-train; do **not** launch until `ssh spark` → `spark-bf46`.
- **BEST held:** **morph48** (`unbind_exact≈0.7412`, fair val **n=228**). morph40 + morph36 preserved.
- morph49 LAST=7 intent remains LEGAL (see `morph49-40ep-last7-20260917/`); not launched.

## Operator

Tunnel must recover (Cloudflare Tunnel / Access to Spark). Resume morph49 lever vs BEST morph48 only after SSH is up.
