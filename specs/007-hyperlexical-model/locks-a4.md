# Clarify addendum A4

| ID | Question | Lock |
|----|----------|------|
| C41 | Which encoder layers train? | Last 2 only. Embeddings + layers 0..19 frozen. |
| C42 | Classify tensor? | `Linear(768, 9)` on `last_hidden_state[:, 0]`. |
| C43 | Unbind tensors? | `role_head` and `filler_head`, both `Linear(768, vocab)`, read token states. |
| C44 | Token index for filler k? | `min(k+1, seq-1)` in v0. |
| C45 | May this smoke unfreeze the full encoder? | No. |
| C46 | Do layout locks produce weight values? | No. Values only from Spark `--run`. |
