# labeled_new_atoms.jsonl — sharded for git MCP size limits

Full packet is 460 JSONL rows. Canonical `part00`–`part05` JSONL files are stored
as zlib+base64 sidecars (MCP `push_files` cannot embed ~40–54KB JSONL in one call).

Reconstruct:

```bash
python3 - <<'PY'
import pathlib, zlib, base64
for i in range(6):
    p = pathlib.Path(f"labeled_new_atoms.part{i:02d}.jsonl")
    b64 = pathlib.Path(f"labeled_new_atoms.part{i:02d}.jsonl.zlib.b64").read_text().strip()
    p.write_bytes(zlib.decompress(base64.b64decode(b64)))
pathlib.Path("labeled_new_atoms.jsonl").write_bytes(
    b"".join(pathlib.Path(f"labeled_new_atoms.part{i:02d}.jsonl").read_bytes() for i in range(6))
)
print("reconstructed part00-part05 + labeled_new_atoms.jsonl")
PY
```

| shard | rows | raw bytes | sha256 |
|-------|-----:|----------:|--------|
| part00 | 80 | 52567 | `b93b9669469dfe196bd7befc8ca601bb18e45e30e7b5c8b8fae08f36daed133b` |
| part01 | 80 | 52633 | `062b7ab3eed7879d6aaee4693dde8a395608adde1b1a1c187ed799e8378b1bef` |
| part02 | 80 | 53538 | `fceeca0770cf76b0470a5668152eb0914e4abc8f0be9ffeef35ef89cd54581cf` |
| part03 | 80 | 54067 | `705b06a36c8f53f01e41339444b6853f991ad6b22fdadc2d1641ada690e1bf82` |
| part04 | 80 | 53349 | `589c3bfeec3d6ed973972033fd3dbd0fad96ae153392953f8331020e7c03370c` |
| part05 | 60 | 40932 | `7ecd90a4aee59ec10a2efd454da63c3a86b16e3a7578d99ca078a0ff6805893c` |

Not force-trained. INFERRED proposals only. `name_gate=false`.
