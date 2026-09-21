# labeled_new_atoms — reconstruct (MCP-safe encodings)

Full packet is **460** JSONL rows. Plain `.partNN.jsonl` files are **not** on the branch (MCP mangled/truncated large JSONL). Use the zlib sidecars below.

## Reconstruct

```bash
python3 - <<'PY'
import base64, zlib, hashlib
from pathlib import Path
base = Path('.')

def b64z(name: str) -> bytes:
    return zlib.decompress(base64.b64decode((base / name).read_text().strip()))

def b64z_join(*names: str) -> bytes:
    raw = ''.join((base / n).read_text().strip() for n in names)
    return zlib.decompress(base64.b64decode(raw))

def hexz_join(*names: str) -> bytes:
    hx = ''.join((base / n).read_text().strip() for n in names)
    return zlib.decompress(bytes.fromhex(hx))

parts = [
    b64z('labeled_new_atoms.part00.jsonl.zlib.b64'),
    b64z('labeled_new_atoms.part01.jsonl.zlib.b64'),
    b64z('labeled_new_atoms.part02.jsonl.zlib.b64'),
    hexz_join(*[f'labeled_new_atoms.part03.jsonl.zlib.hex.q{i}' for i in range(6)]),
    b64z_join('labeled_new_atoms.part04.jsonl.zlib.b64.a',
              'labeled_new_atoms.part04.jsonl.zlib.b64.b'),
    b64z('labeled_new_atoms.part05.jsonl.zlib.b64'),
]
out = b''.join(parts)
Path('labeled_new_atoms.jsonl').write_bytes(out)
print('rows', out.count(b'\n'), 'sha256', hashlib.sha256(out).hexdigest())
PY
```

Expected `sha256`: `82c609716126efbb395bbc8ccf31a7d3fdd9862db422fe3b76711b5862f4823c`

## Canonical shard payloads (keep)

| shard | encoding | rows |
|-------|----------|-----:|
| part00 | `labeled_new_atoms.part00.jsonl.zlib.b64` | 80 |
| part01 | `labeled_new_atoms.part01.jsonl.zlib.b64` | 80 |
| part02 | `labeled_new_atoms.part02.jsonl.zlib.b64` | 80 |
| part03 | `labeled_new_atoms.part03.jsonl.zlib.hex.q0`…`q5` | 80 |
| part04 | `labeled_new_atoms.part04.jsonl.zlib.b64.a` + `.b` | 80 |
| part05 | `labeled_new_atoms.part05.jsonl.zlib.b64` | 60 |
| **total** | | **460** |

Ignore probe/`_*.txt`/`_*.jsonl` leftovers and unused `.zlib.b64.q*` / plain stub `.jsonl` files if present — MCP push experiments.

Not force-trained. INFERRED proposals only. `name_gate=false`.
