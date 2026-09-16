# CUDA memory fraction — Spark train guard (2026-09-16)

Canonical launcher: [`scripts/spark/guard.py`](../../scripts/spark/guard.py) → sync to `~/hlx/guard.py`.  
Morph wrapper: [`scripts/spark/run_morph_train.sh`](../../scripts/spark/run_morph_train.sh).

| knob | value |
|------|------:|
| Env override | `HYPERLEX_CUDA_MEM_FRACTION` (wins over argv) |
| Exclusive morph default | **0.3** (~39 GB / 130 GB) |
| Co-tenant / beside Qwen | **0.03** (~3.9 GB) |
| Retired morph hardcode | ~~0.015~~ (~2 GB) |

**Intent:** shared-box safety (trainer OOM, not co-tenant kill). The `0.015` morph hardcode was leftover after Qwen left.

Receipt: [`receipts/20260916-cuda-mem-fraction-speed-lever.md`](receipts/20260916-cuda-mem-fraction-speed-lever.md).

Updates the policy described in `SPARK-BRINGUP.md` §S4 and `HERMES-SPARK-RUN.md` §A5 (those sections still show the original bring-up `0.03` / argv-only snippet until they are rewritten to point here).
