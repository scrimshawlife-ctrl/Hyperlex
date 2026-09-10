# Weights 007 — layout before train

Values are produced on Spark. This file is the layout Aaron must write into `heads.pt`.

| Part | Shape | Trainable |
|------|-------|-----------|
| ModernBERT-base body | ~149M, hidden 768, 22 layers | last **2** layers only |
| `classify` | `Linear(768, 9)` | yes |
| `role_head` | `Linear(768, \|role_vocab\|)` | yes |
| `filler_head` | `Linear(768, \|filler_vocab\|)` | yes |

Classify reads `last_hidden_state[:, 0]`.
Unbind reads `last_hidden_state` token rows (C29). Alignment in v0 is index `k+1` for filler k.

Forbidden tensors: refusal head, Brier head, chat embeddings.

On-disk after `--run` (not git):

- `heads.pt`
- `layout.json`
- `train-receipt.json` (`brier: null`, `e2_pass: false`, `name_gate: false`)
- `config-train.json`

Code: `scripts/shadow/hyperlexical/layout.py` + `loop.py`.
