import hashlib
from .schemes import n_roles


ITEMS = ["a", "b", "c", "d"]
TYPES = ["TOKEN", "SLOT", "MARKER"]


def _hash_int(s):
    return int(hashlib.sha256(s.encode()).hexdigest()[:8], 16)


def _vec(seed, dim):
    out = []
    x = seed % (2**31 - 1) or 1
    for _ in range(dim):
        x = (1103515245 * x + 12345) % (2**31)
        out.append((x / 2**31) * 2 - 1)
    return out


def make_spans(n=64, length=4, seed=7):
    spans = []
    x = seed % (2**31 - 1) or 1
    for i in range(n):
        items = []
        tags = []
        for k in range(length):
            x = (1103515245 * x + 12345) % (2**31)
            items.append(ITEMS[(x >> 16) % len(ITEMS)])
            tags.append(TYPES[(i + k) % len(TYPES)])
        label = ITEMS.index(items[0])
        spans.append({"item_ids": items, "type_tags": tags, "label": label})
    return spans


def _tpr_encode(spans, dim, max_len, seed):
    df = 4
    fillers = {it: _vec(_hash_int(f"tpr-f-{it}-{seed}"), df) for it in ITEMS}
    W = []
    for r in range(dim):
        W.append(_vec(_hash_int(f"tpr-W-{r}-{seed}"), n_roles("positional", max_len) * df))
    b = _vec(_hash_int(f"tpr-b-{seed}"), dim)
    encodings = []
    from .tpr import phi_span, reconstruct
    for sp in spans:
        phi = phi_span("positional", sp["item_ids"], sp["type_tags"], fillers, max_len)
        encodings.append(reconstruct(W, b, phi))
    return encodings


def _atomic_encode(spans, dim, max_len, seed):
    encodings = []
    for sp in spans:
        key = "seq-" + "-".join(sp["item_ids"]) + f"-{seed}"
        encodings.append(_vec(_hash_int(key), dim))
    return encodings


def snapshot(kind, n=64, length=4, dim=12, seed=7):
    if kind not in {"tpr", "atomic_pair"}:
        raise ValueError(kind)
    spans = make_spans(n=n, length=length, seed=seed)
    max_len = length
    if kind == "tpr":
        encodings = _tpr_encode(spans, dim, max_len, seed)
        fid = "fixture:tpr:v0.1"
    else:
        encodings = _atomic_encode(spans, dim, max_len, seed)
        fid = "fixture:atomic_pair:v0.1"
    return {
        "encoder_id": fid,
        "weight_hash": hashlib.sha256(f"{kind}-{seed}-{dim}".encode()).hexdigest()[:16],
        "encodings": encodings,
        "spans": spans,
        "max_len": max_len,
        "dim": dim,
        "kind": kind,
    }
