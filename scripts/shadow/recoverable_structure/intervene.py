from .tpr import phi_span, reconstruct


def filler_edit(scheme, snap, fit_res, predictor):
    fillers = {k: v[:] for k, v in fit_res["fillers"].items()}
    items = list(fillers)
    if len(items) < 2:
        return {"edit": "none", "expected": 0, "observed": 0, "hit": False}
    src, dst = items[0], items[1]
    span = snap["spans"][0]
    edited_items = [dst if tok == src else tok for tok in span["item_ids"]]
    phi_before = phi_span(scheme, span["item_ids"], span["type_tags"], fillers, snap["max_len"])
    phi_after = phi_span(scheme, edited_items, span["type_tags"], fillers, snap["max_len"])
    vec_b = reconstruct(fit_res["W"], fit_res["b"], phi_before)
    vec_a = reconstruct(fit_res["W"], fit_res["b"], phi_after)
    obs_a = predictor([vec_a])[0]
    if span["item_ids"][0] == src:
        expected = _item_label(dst)
    else:
        expected = _item_label(span["item_ids"][0])
    return {
        "edit": f"{src}->{dst}",
        "expected": expected,
        "observed": obs_a,
        "hit": bool(obs_a == expected),
    }


def _item_label(item):
    order = ["a", "b", "c", "d"]
    return order.index(item) if item in order else -1
