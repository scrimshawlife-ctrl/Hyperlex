# labeled_new_atoms.jsonl — sharded for git MCP size limits

Full packet is 460 JSONL rows. Each logical `partNN` is stored as `q*` pieces
(~12KB) because full shards exceed MCP `push_files` argument size.

Reconstruct canonical shards and the monolithic packet:

```bash
cat labeled_new_atoms.part00.q0.jsonl labeled_new_atoms.part00.q1.jsonl labeled_new_atoms.part00.q2.jsonl labeled_new_atoms.part00.q3.jsonl labeled_new_atoms.part00.q4.jsonl > labeled_new_atoms.part00.jsonl
cat labeled_new_atoms.part01.q0.jsonl labeled_new_atoms.part01.q1.jsonl labeled_new_atoms.part01.q2.jsonl labeled_new_atoms.part01.q3.jsonl labeled_new_atoms.part01.q4.jsonl > labeled_new_atoms.part01.jsonl
cat labeled_new_atoms.part02.q0.jsonl labeled_new_atoms.part02.q1.jsonl labeled_new_atoms.part02.q2.jsonl labeled_new_atoms.part02.q3.jsonl labeled_new_atoms.part02.q4.jsonl > labeled_new_atoms.part02.jsonl
cat labeled_new_atoms.part03.q0.jsonl labeled_new_atoms.part03.q1.jsonl labeled_new_atoms.part03.q2.jsonl labeled_new_atoms.part03.q3.jsonl labeled_new_atoms.part03.q4.jsonl > labeled_new_atoms.part03.jsonl
cat labeled_new_atoms.part04.q0.jsonl labeled_new_atoms.part04.q1.jsonl labeled_new_atoms.part04.q2.jsonl labeled_new_atoms.part04.q3.jsonl labeled_new_atoms.part04.q4.jsonl > labeled_new_atoms.part04.jsonl
cat labeled_new_atoms.part05.q0.jsonl labeled_new_atoms.part05.q1.jsonl labeled_new_atoms.part05.q2.jsonl labeled_new_atoms.part05.q3.jsonl > labeled_new_atoms.part05.jsonl
cat labeled_new_atoms.part0{0,1,2,3,4,5}.jsonl > labeled_new_atoms.jsonl
```

| shard | pieces | rows | sha256 (concat) |
|-------|--------|-----:|-----------------|
| part00 | q0–q4 (5) | 80 | `b93b9669469dfe196bd7befc8ca601bb18e45e30e7b5c8b8fae08f36daed133b` |
| part01 | q0–q4 (5) | 80 | `062b7ab3eed7879d6aaee4693dde8a395608adde1b1a1c187ed799e8378b1bef` |
| part02 | q0–q4 (5) | 80 | `fceeca0770cf76b0470a5668152eb0914e4abc8f0be9ffeef35ef89cd54581cf` |
| part03 | q0–q4 (5) | 80 | `705b06a36c8f53f01e41339444b6853f991ad6b22fdadc2d1641ada690e1bf82` |
| part04 | q0–q4 (5) | 80 | `589c3bfeec3d6ed973972033fd3dbd0fad96ae153392953f8331020e7c03370c` |
| part05 | q0–q3 (4) | 60 | `7ecd90a4aee59ec10a2efd454da63c3a86b16e3a7578d99ca078a0ff6805893c` |

Not force-trained. INFERRED proposals only. `name_gate=false`.
