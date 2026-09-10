# Weights 007 — layout before train

Values are produced on Spark. This file is the layout Aaron must write into the HF directory.

| Part | Shape | Trainable |
|------|-------|-----------|
| ModernBERT-base body | ~149M, hidden 768, 22 layers | last **2** layers only |
| `classify` | `Linear(768, 9)` | yes |
| `role_head` | `Linear(768, \|role_vocab\|)` | yes |
| `filler_head` | `Linear(768, \|filler_vocab\|)` | yes |

Classify reads `last_hidden_state[:, 0]`.
Unbind pools token states whose offsets overlap the atom's char span (C47).

On-disk after `--run` (not git):

- `config.json` `layout.json` `README.md`
- `model.safetensors` or `heads.pt`
- `train-receipt.json` with per-epoch val metrics

Forbidden: refusal head, Brier head, chat embeddings, `text-generation` pipeline.
