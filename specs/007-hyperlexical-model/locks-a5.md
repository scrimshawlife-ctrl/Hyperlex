# Clarify addendum A5 — HF package + aligner

| ID | Question | Lock |
|----|----------|------|
| C47 | Unbind alignment? | Char-span of the atom + tokenizer `offset_mapping`. Pool those token states. `k+1` is forbidden. |
| C48 | Val metrics? | Each epoch: classify acc on val, unbind exact on val. Written to `train-receipt.json`. |
| C49 | Publish artifact shape? | HF directory: `config.json`, `layout.json`, `README.md`, `model.safetensors` (else `heads.pt`). |
| C50 | Hub upload in this unit? | No. Skeleton lives in-repo. Weights stay on Spark. |
| C51 | Card name? | `hyperlex-encoder-modernbert-base-seed` until E2. |
| C52 | `pipeline_tag`? | `text-classification`. Never `text-generation`. |
