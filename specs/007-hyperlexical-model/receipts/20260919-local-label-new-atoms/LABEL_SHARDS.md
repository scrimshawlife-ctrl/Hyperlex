# labeled_new_atoms.jsonl — sharded for git MCP size limits

Full packet is 460 JSONL rows. Canonical part00–part05 JSONL are stored as
compressed sidecars (MCP push_files cannot embed ~40–54KB JSONL in one call).

Encoding:
- part00, part01, part02, part05: `*.jsonl.zlib.b64` (single file)
- part03: `*.jsonl.zlib.hex.q0` … `q5` (hex; b64 hit a deterministic base64 alphabet corruption)
- part04: `*.jsonl.zlib.b64.a` + `*.jsonl.zlib.b64.b`

Reconstruct:

```bash
python3 - <<'PY'
import pathlib, zlib, base64
root = pathlib.Path(".")
for i in range(6):
    out = root / f"labeled_new_atoms.part{i:02d}.jsonl"
    if i == 3:
        hx = "".join((root / f"labeled_new_atoms.part03.jsonl.zlib.hex.q{j}").read_text().strip() for j in range(6))
        out.write_bytes(zlib.decompress(bytes.fromhex(hx)))
    elif i == 4:
        b64 = "".join((root / f"labeled_new_atoms.part04.jsonl.zlib.b64.{h}").read_text() for h in "ab").strip()
        out.write_bytes(zlib.decompress(base64.b64decode(b64)))
    else:
        b64 = (root / f"labeled_new_atoms.part{i:02d}.jsonl.zlib.b64").read_text().strip()
        out.write_bytes(zlib.decompress(base64.b64decode(b64)))
(root / "labeled_new_atoms.jsonl").write_bytes(
    b"".join((root / f"labeled_new_atoms.part{i:02d}.jsonl").read_bytes() for i in range(6))
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
| **total** | **460** | **307086** | concat of part00–part05 |

Ignore probe/ladder junk files in this directory; use only the sidecar paths above.
