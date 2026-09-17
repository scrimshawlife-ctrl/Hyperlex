# morph45 — recipe LEGAL verdict (live Spark inspect)

**Observed:** 2026-09-17T04:28Z UTC on `spark-bf46` via `ssh spark` (cloudflared).  
**Container:** `hlx-train-morph45-1789619192` Up; PID training on GPU (~1.2 GiB, util high).  
**Gate owner:** this run (`Verify morph45 and watch gate`). Escalate agent `bc-9ecde051-1694-549d-b3bc-c2a60e760650` RUNNING but transcript **empty** (0 msgs) — not owning gate. **Single gate = this agent.**

## Verdict: **LEGAL intent = Y; LEGAL execution = N (BLOCKED)**

Documented one-lever recipe delta on the **morph40 fair surface**. Not an illegal warm+force residual-gold clone of morph43/44.

**However:** Spark `loop.py` at launch was a 471-line regression missing `INIT_FROM` / `SAVE_BEST` / force-train — env was correct, code was not. Train **stopped**; see `BLOCKED_INVALID_LAUNCH.md`.

| check | live value | expected legal |
|-------|------------|----------------|
| `HYPERLEX_UNBIND_HEAD_SLOT_WEIGHT` | **3** | 3 (was 2) |
| `HYPERLEX_INIT_FROM` | `...-seed-morph40` | morph40 warm |
| `HYPERLEX_SAVE_BEST_UNBIND` | 1 | 1 |
| `HYPERLEX_UNBIND_FORCE_TRAIN_PATH` | `force_train_morph40_expanded.jsonl` | morph40 (**135** lines) |
| `HYPERLEX_UNBIND_HARD_ATOMS_PATH` | `hard_atoms_train_morph40.jsonl` | morph40 (**180** lines) |
| epochs / batch / LR | 40 / 8 / 2e-5 | hold |
| `HYPERLEX_CUDA_MEM_FRACTION` | 0.3 | 0.3 exclusive |
| OUT | `...-seed-morph45` | new dir |
| BEST symlink | → `...-seed-morph40` | held |

**Not used:** `force_train_morph43_expanded.jsonl` (186) / `force_train_morph44_expanded.jsonl` (187) residual gold surfaces.

## Fair gate (deferred until 40ep)

Promote morph45→BEST iff best `unbind_exact` **> 0.7368421052631579** on val n=228. Else REJECT; BEST stays morph40; morph36 untouched. `name_gate=false`.

## Artifacts

- Private: `~/hlx-private/p1-spark-morph45-40ep-head-slot3-20260916/`
- Intent (Spark): matches repo `morph45-intent.json`
