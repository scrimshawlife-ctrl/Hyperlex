from . import linalg as L
from .schemes import n_roles, role_ids


def phi_span(scheme, item_ids, type_tags, fillers, max_len):
    """Flattened TPR: concat over roles of summed fillers on that role."""
    nr = n_roles(scheme, max_len)
    df = len(next(iter(fillers.values())))
    acc = L.zeros(nr * df)
    roles = role_ids(scheme, len(item_ids), type_tags)
    for item, role in zip(item_ids, roles):
        f = fillers[item]
        base = role * df
        for i, val in enumerate(f):
            acc[base + i] += val
    return acc


def reconstruct(W, b, phi):
    return L.add(L.matvec(W, phi), b)
