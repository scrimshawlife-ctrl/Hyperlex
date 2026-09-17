# Hyperlex status

**Naming:** repo **Hyperlex** is the transitional monorepo shell. Public products: **Hyperlexical** (Spec 007 model / train / eval / E2 / `name_gate` claim) and **ne0l0gist** (slang ingest). `name_gate` remains false.

**Version:** 0.4.0
**Observed:** 2026-09-12
**Posture:** Hermes skill = current operator surface. Spec 007 = model path (SHADOW). Spark BEST = `seed-morph48` (**PROMOTE**; LAST=6 beat fair morph40 0.7368 → **0.7412** on n=228; morph40+morph36 preserved; morph45–47 REJECT). morph49 LAST=7 intent LEGAL but **BLOCKED** (Cloudflare Tunnel 1033). `name_gate` still false.
**Install:** `bash install.sh` → `~/.hermes/skills/hyperlex`
**Claude (optional):** `bash install.sh --claude` → `~/.claude/skills/hyperlex`
**Track:** Phases 0–4 complete · Phase 5.0–5.3 · Pages static run history · Spec 007 SHADOW encoder on main

This file is the operator snapshot. The docs site copies it to [status](https://scrimshawlife-ctrl.github.io/Hyperlex/status/). Do not treat it as a Hub card or a Brier score.

## Spec 007 — honest gates (snapshot)

| Gate | State |
|------|--------|
| `name_gate` | **false** |
| Spark BEST | **`seed-morph48`** — val `unbind_exact≈0.7412` (ep19; fair n=228 vs morph40 **0.7368**). morph40 + morph36 preserved. Ladder ≥0.55 **HIT**. morph45–47 REJECT. morph48 **PROMOTE**. morph49 LAST=7 **BLOCKED_SSH** (tunnel 1033). |
| Hub publish | **No** |

## Recommended next

1. Spark BEST = **morph48** (0.7412). morph49 LAST=7 **BLOCKED** until tunnel recovers — see `NEXT_MOVES_007.md` / `receipts/20260917-morph49-ssh-blocked.md`.
2. Burn-in offline runs + settle path.
3. Do not Hub-upload. Do not flip `name_gate`.
