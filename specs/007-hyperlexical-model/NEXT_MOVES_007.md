# Spec 007 — accept20 prepared; famcls35 climb in flight

**Authority:** Spec 007 only. `name_gate` false. No Hub. No invented OBSERVED gold.
**BEST:** morph19 — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Pins

| pin | path | note |
|-----|------|------|
| **weight** | `~/hlx-private/p1-structure-unbind-famcls25-20260914/` | last KEEP |
| **data** | `~/hlx-private/p1-classify-accept20-20260914/prepare` | +149 residual contrastive |
| **BEST** | morph19 | untouched |

## This pass
1. Gated famcls29–34 REJECT chain (LR + aux/upsample brackets on accept19).
2. Dumped famcls25 on accept19-test (11 misses) → built **accept20** (+149).
3. Fair famcls25 on accept20-test: family **0.9286**, structure/role/pointer **1.0**.
4. **famcls35** N=8 LR 1e-5 **no aux**, full 40 ep — **IN FLIGHT**.

## Accept19 bracket (exhausted)
| run | knob | family | structure | verdict |
|-----|------|--------|-----------|---------|
| famcls28 | LR 1e-5 | 0.9598 | 0.958 | REJECT |
| famcls29–34 | LR/aux/upsample | ≤0.9138 | mixed | REJECT |

## Gate (famcls35)
family > **0.9285714285714286** AND structure/role/pointer == **1.0**.

## Policy
OBSERVED hold. No BEST overwrite. Full 40-epoch runs. Do not deepen N blindly.
