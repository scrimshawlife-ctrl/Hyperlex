# labeled_new_atoms.jsonl — sharded for git MCP size limits

Full packet is 460 JSONL rows. Reconstruct:

```bash
cat labeled_new_atoms.part00.jsonl \
    labeled_new_atoms.part01.jsonl \
    labeled_new_atoms.part02.jsonl \
    labeled_new_atoms.part03.jsonl \
    labeled_new_atoms.part04.jsonl \
    labeled_new_atoms.part05.jsonl \
  > labeled_new_atoms.jsonl
```

| shard | rows |
|-------|-----:|
| part00 | 80 |
| part01 | 80 |
| part02 | 80 |
| part03 | 80 |
| part04 | 80 |
| part05 | 60 |
| **total** | **460** |

Not force-trained. INFERRED proposals only. `name_gate=false`.
