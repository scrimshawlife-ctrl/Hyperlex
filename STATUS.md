# Hyperlex status

**Naming:** repo **Hyperlex** is the transitional monorepo shell. Public products: **Hyperlexical** (Spec 007 model / train / eval / E2 / `name_gate` claim) and **ne0l0gist** (slang ingest). `name_gate` remains false.

**Version:** 0.4.0  
**Observed:** 2026-09-12  
**Posture:** Hermes skill = current operator surface. Spec 007 = model path (SHADOW). Spark BEST = `seed-morph40` (**held**; morph45 HEAD_SLOT=3 **REJECT_VS_BEST** 0.7237 < fair 0.7368 after restored-loop relaunch; morph43/44 residual-gold REJECT; gold exhausted) (val unbind_exact≈0.7368 on fair n=228; morph36 preserved). `name_gate` still false.  
**Install:** `bash install.sh` → `~/.hermes/skills/hyperlex`  
**Claude (optional):** `bash install.sh --claude` → `~/.claude/skills/hyperlex`  
**Track:** Phases 0–4 complete · Phase 5.0–5.3 · Pages static run history · Spec 007 SHADOW encoder on main

This file is the operator snapshot. The docs site copies it to [status](https://scrimshawlife-ctrl.github.io/Hyperlex/status/). Do not treat it as a Hub card or a Brier score.

## Spec 007 — honest gates (snapshot)

| Gate | State |
|------|--------|
| `name_gate` | **false** |
| Spark BEST | **`seed-morph40`** — 0.7368 on n=228. morph37–45 REJECT (morph45 best 0.7237 < fair 0.7368). |
| Hub publish | **No** |

## Recommended next

1. Spark BEST = **morph40** (0.7368). morph41–45 REJECT (morph45 HEAD_SLOT=3 relaunch 0.7237 < fair 0.7368 n=228). Next lever needs a new justified delta. See `NEXT_MOVES_007.md`.
2. Burn-in offline runs + settle path.
3. Do not Hub-upload. Do not flip `name_gate`.
