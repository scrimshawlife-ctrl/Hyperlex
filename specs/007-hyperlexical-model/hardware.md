# Hardware 007 — DGX Spark (normative home box)

**Box**: NVIDIA DGX Spark  
**SoC**: GB10 Grace Blackwell  
**Memory**: 128 GB coherent unified LPDDR5x, ~273 GB/s  
**CPU**: 20-core Arm (10× Cortex-X925 + 10× Cortex-A725), aarch64  
**GPU**: Blackwell, 6,144 CUDA cores, 5th-gen Tensor, compute capability 12.1 (`sm_121`)  
**AI peak (vendor)**: up to 1 PFLOP FP4 sparse / NVFP4 native  
**OS expectation**: DGX OS + CUDA / TensorRT  
**Cite**: NVIDIA DGX Spark datasheet (GB10, 128 GB unified). Re-check before a purchase claim.

## What this box is for in 007

T1 is 60–130M. Spark is overkill for the product card. The box is the **operator training and local-serve home**, not a reason to jump to a 7B chat LM.

| Job | Fits Spark? | 007 rule |
|-----|-------------|----------|
| U1 stub / pytest | yes, CPU enough | no GPU required in CI |
| T0 33M / T1 110M train | yes, tiny vs 128 GB | default train target |
| NVFP4 export of T1 | optional, later | not required to name Hyperlexical |
| Frozen uncensored **base** encoder as teacher (≤7B) | yes in memory | teacher only; not the Hub product name |
| 70B full-parameter SFT | vendor says yes | out of this spec |
| 200B inference | vendor ceiling | out of this spec |

## Packaging constraints

- Train and serve on aarch64. x86 CI may stub.
- Do not assume discrete VRAM. Memory is unified. Batch size is a RAM budget, not a 24 GB card budget.
- Bandwidth is ~273 GB/s, not HBM. Keep T1 small so unbind latency stays library-class.
- Weights live on local NVMe (`~/.hyperlex/models/` or operator path). Git does not hold binaries.
- Offline: Spark may cache Hub snapshots. Pytest still runs with `HYPERLEX_OFFLINE=1` and stub vectors.

## Not this box

Jetson Orin Nano remains a possible later *edge infer* target. It is not the train home for U3. Spec 007 does not retarget Orin in this cycle.
