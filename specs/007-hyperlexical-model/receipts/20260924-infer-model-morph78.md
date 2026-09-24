# Trained inference path — `seed-morph78` (2026-09-24)

**Scope:** first real (non-stub) inference for Hyperlexical. `hyperlexical.infer --model-dir` loads a local trained checkpoint and emits `hyperlex.hyperlexical.inference.v0.1` with `MODEL_EMBEDDING`. No Hub, no T13, no training. Default CLI stays the offline stub.

**Run:** Spark, container `lmsysorg/sglang:dev-qwen38-27b-dflash2`, branch code staged in `~/hlx-infer-test` (the Spark `~/Hyperlex` checkout was not touched). Model `~/.hyperlex/models/BEST` → `seed-morph78`. Outputs in `infer-model-morph78-20260924/`.

## OBSERVED

| Input | model_id / version | lineage (conf) | unbind_ok |
|---|---|---|---|
| `rizz` | `hyperlex-structure-149m` / `seed-morph78` | brainrot-aura (0.936) | true |
| `no cap fr` | same | brainrot-aura (0.880) | true |
| `touch grass` | same | gaming-meta (0.978) | true |
| `bet that up` | same | none (1.000) | true |
| `have fun staying poor` | same | none (1.000) | true |
| `rizz` on morph65 dir | `hyperlex-encoder-modernbert-base-seed-morph65` / `seed-morph65` | brainrot-aura (0.984) | true |

Trunk-forward E2 on `BEST` with this branch: `e2_pass: true`, unbind_exact 1.0, n_unbind_eval 24, **`name_gate: true`** (card-rename PR #104 behaviour confirmed on the real pin).

## Findings (recorded, not acted on)

1. **Classify overconfidence on val-settled phrases.** `bet that up` and `have fun staying poor` were settled OBSERVED `split=val` for unbind; the classify head returns `none` at confidence ≈1.0 instead of their card lineages (kinship-address, crypto-degen). Lineage confidence is not calibrated; treat it as INFERRED only.
2. **Parameter count vs A1.** Inference counts **150,546,889** parameters: trunk 149,014,272 + heads 1,532,617 (filler vocab 1,972). A1 says "T1 ≤ 150M". The trunk is within the ceiling; trunk + heads exceeds it by ~0.55M. Whether A1 counts heads is an operator reading; the card name `hyperlex-structure-149m` matches the trunk.

## NOT_COMPUTABLE

- Calibrated lineage accuracy of the inference path (no held-out classify receipt for this pin; E1 still NOT_COMPUTABLE).
- `type_slot` inference (CLI refuses it for `--model-dir` in this cut).
