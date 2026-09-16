# Receipt — CUDA mem-fraction speed lever (2026-09-16)

**Authority:** Spec 007 operator / z0D flag. `name_gate=false`.  
**morph41:** left running at **0.015** (`hlx-train-morph41-1789537012`); **not** restarted. Later completed → **REJECT_VS_BEST** (best 0.7149 < fair morph40 0.7368); BEST stays morph40.

## Verdict

| question | answer |
|----------|--------|
| Intent of `~/hlx/guard.py`? | **Intentional shared-box safety** — trainer OOM instead of killing co-tenant |
| Leftover? | **`0.015` morph hardcode is over-tight leftover** after Qwen left; bring-up design was `0.03` |
| Env override before? | **No** — fraction was argv-only |
| GPU shared during morph41? | **No** — only morph41 python (~1.2 GiB) + display; Qwen/ComfyUI not running |

Evidence at investigation:

- `[guard] cap=2.0GB free=110.1GB total=130.7GB` on morph41 start
- Host util ~51–56%, power ~28–31 W (allocator capped, not compute-bound on VRAM)
- morph41 healthy mid-run: best-ckpt epoch **3**, `unbind_exact≈0.7149`; leave alone (warm morph40 + SAVE_BEST; restart would waste progress)

## Recommendation (130 GB Spark)

| frac | use |
|-----:|-----|
| **0.3** | exclusive morph default (~39 GB) — enough for ModernBERT last-N / batch 8; leaves ~90 GB if Qwen returns |
| **0.03** | co-tenant / beside live SGLang (original bring-up) |
| 0.5–0.8 | operator-only if exclusive + larger recipe needs it |
| ~~0.015~~ | retired |

Rationale: raising past ~2 GB removes artificial allocator thrash; 0.3 is the speed lever without pretending the box is single-tenant forever.

## Acted

1. Canonical template: `scripts/spark/guard.py` — `HYPERLEX_CUDA_MEM_FRACTION` overrides argv.
2. Canonical launcher: `scripts/spark/run_morph_train.sh` — default **`0.3`** (was hardcoded `0.015`).
3. Spark host: synced `~/hlx/guard.py` + `~/hlx/run_morph_train.sh` for **next** morph launch (morph41 untouched).
4. Docs: `SPARK-BRINGUP.md` S4, `HERMES-SPARK-RUN.md` A5 + hard-no clarified.

## Before / after (wall time)

| run | guard | wall (40ep) | note |
|-----|------:|------------:|------|
| morph39 | 0.015 | ~73 min | prior |
| morph40 | 0.015 | ~80 min | prior |
| morph41 | 0.015 | ~86 min | completed; REJECT_VS_BEST; not restarted for 0.3 |
| **morph42** | **0.3** | **~87 min** | `hlx-train-morph42-1789542688`; REJECT (0.7149); **no wall speedup** — resident ~1.2 GiB |

No throwaway retrain forced mid-morph41. morph42 measured exclusive **0.3**: wall unchanged vs 0.015 on this ModernBERT last-N / batch-8 recipe.
