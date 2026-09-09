import hashlib
import time

from . import linalg as L
from .receipt import build_receipt, render_card
from .schemes import UnknownScheme, validate_schemes
from .tpr import phi_span, reconstruct


class Abort(RuntimeError):
    pass


def _split(n, seed=7, train_frac=0.75):
    idx = list(range(n))
    x = seed % (2**31 - 1) or 1
    for i in range(n - 1, 0, -1):
        x = (1103515245 * x + 12345) % (2**31)
        j = x % (i + 1)
        idx[i], idx[j] = idx[j], idx[i]
    cut = int(n * train_frac)
    train, test = sorted(idx[:cut]), sorted(idx[cut:])
    raw = ",".join(map(str, train)) + "|" + ",".join(map(str, test))
    return train, test, hashlib.sha256(raw.encode()).hexdigest()[:16]


def _init_fillers(spans, df=4):
    items = sorted({it for sp in spans for it in sp["item_ids"]})
    fillers = {}
    for i, it in enumerate(items):
        v = L.zeros(df)
        v[i % df] = 1.0
        fillers[it] = v
    return fillers


def _stack_phi(spans, scheme, fillers, max_len):
    return [phi_span(scheme, sp["item_ids"], sp["type_tags"], fillers, max_len) for sp in spans]


def _fit_affine(phis, targets, ridge=1e-4):
    n = len(phis)
    d = len(targets[0])
    X = [phi + [1.0] for phi in phis]
    W, b = [], []
    for dim in range(d):
        y = [targets[i][dim] for i in range(n)]
        w = L.lstsq(X, y, ridge=ridge)
        W.append(w[:-1])
        b.append(w[-1])
    return W, b


def fit_scheme(scheme, snap, train_idx, test_idx):
    t0 = time.monotonic()
    spans = snap["spans"]
    enc = snap["encodings"]
    max_len = snap["max_len"]
    fillers = _init_fillers(spans)
    train_spans = [spans[i] for i in train_idx]
    train_tgt = [enc[i] for i in train_idx]
    phis_tr = _stack_phi(train_spans, scheme, fillers, max_len)
    W, b = _fit_affine(phis_tr, train_tgt)
    pred_tr = [reconstruct(W, b, p) for p in phis_tr]
    train_mse = L.mse(pred_tr, train_tgt)
    test_spans = [spans[i] for i in test_idx]
    test_tgt = [enc[i] for i in test_idx]
    phis_te = _stack_phi(test_spans, scheme, fillers, max_len)
    pred_te = [reconstruct(W, b, p) for p in phis_te]
    test_mse = L.mse(pred_te, test_tgt)
    elapsed = time.monotonic() - t0
    if elapsed >= 30:
        raise Abort(f"fit exceeded 30s: {elapsed:.2f}")
    return {
        "scheme": scheme,
        "W": W,
        "b": b,
        "fillers": fillers,
        "train_mse": train_mse,
        "test_mse": test_mse,
        "pred_train": pred_tr,
        "pred_test": pred_te,
        "elapsed": elapsed,
    }


def swap_accuracy(fit_res, snap, train_idx, test_idx):
    labels_tr = [snap["spans"][i]["label"] for i in train_idx]
    labels_te = [snap["spans"][i]["label"] for i in test_idx]
    classes = sorted(set(labels_tr + labels_te))
    Xtr = [p + [1.0] for p in fit_res["pred_train"]]
    weights = {}
    for c in classes:
        y = [1.0 if lab == c else 0.0 for lab in labels_tr]
        weights[c] = L.lstsq(Xtr, y, ridge=1e-4)

    def predict(vecs):
        out = []
        for v in vecs:
            x = v + [1.0]
            scores = {c: L.dot(weights[c], x) for c in classes}
            out.append(max(scores, key=scores.get))
        return out

    pred = predict(fit_res["pred_test"])
    hit = sum(int(a == b) for a, b in zip(pred, labels_te))
    return hit / max(1, len(labels_te)), predict


def run_probe(snap, schemes=("positional", "type_slot"), selection_proxy="unspecified", seed=7):
    try:
        schemes = validate_schemes(schemes)
    except UnknownScheme as exc:
        raise Abort(str(exc)) from exc
    train_idx, test_idx, split_hash = _split(len(snap["spans"]), seed=seed)
    batch_raw = repr([(s["item_ids"], s["label"]) for s in snap["spans"]])
    batch_hash = hashlib.sha256(batch_raw.encode()).hexdigest()[:16]
    scheme_blocks = []
    raw_fits = []
    for sch in schemes:
        fr = fit_scheme(sch, snap, train_idx, test_idx)
        acc, predictor = swap_accuracy(fr, snap, train_idx, test_idx)
        from .intervene import filler_edit
        inter = filler_edit(sch, snap, fr, predictor)
        scheme_blocks.append({
            "scheme": sch,
            "train_mse": fr["train_mse"],
            "test_mse": fr["test_mse"],
            "swap_accuracy": acc,
            "intervention": inter,
        })
        raw_fits.append(fr)
    receipt = build_receipt(
        encoder_id=snap["encoder_id"],
        batch_hash=batch_hash,
        split_hash=split_hash,
        role_schemes=schemes,
        selection_proxy=selection_proxy,
        scheme_blocks=scheme_blocks,
        source_class="AAL-metric",
    )
    return {
        "receipt": receipt,
        "card": render_card(receipt),
        "fits": raw_fits,
        "train_idx": train_idx,
        "test_idx": test_idx,
    }
