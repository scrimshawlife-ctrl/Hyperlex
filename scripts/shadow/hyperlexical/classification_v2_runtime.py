"""Torch heads for Classification v2. Imported only on the v2 training path."""

from __future__ import annotations

from typing import Any, Sequence

from .classification_v2 import (
    ACTIVE_FAMILY_VOCABULARY,
    APPLICABILITY,
    example_loss,
    family_index,
    map_family_rows,
)


def _torch():
    import torch
    from torch import nn

    return torch, nn


def zero_linear(hidden: int, outputs: int):
    """Exact-zero linear. The constructor's random values do not survive."""
    torch, nn = _torch()
    layer = nn.Linear(hidden, outputs)
    with torch.no_grad():
        layer.weight.zero_()
        if layer.bias is not None:
            layer.bias.zero_()
    return layer


def build_v2_heads(hidden: int, v1_classify, source_labels: Sequence[str], witness: dict | None = None):
    """Copy exact rows and install frozen semantic prototypes. Zeros do not survive."""
    torch, _nn = _torch()
    from .classification_v2_prototype import verify_witness_against_copy

    applicability = zero_linear(hidden, len(APPLICABILITY))
    family = zero_linear(hidden, len(ACTIVE_FAMILY_VOCABULARY))
    weight = v1_classify.weight.detach().cpu().tolist()
    bias = v1_classify.bias.detach().cpu().tolist()
    mapped = map_family_rows(source_labels, weight, bias)
    if witness is None:
        raise RuntimeError("FAMILY_PROTOTYPE_UNAVAILABLE")
    verified = verify_witness_against_copy(mapped, witness)
    with torch.no_grad():
        family.weight.copy_(torch.tensor(verified["weight"], dtype=family.weight.dtype))
        family.bias.copy_(torch.tensor(verified["bias"], dtype=family.bias.dtype))
        if not torch.equal(applicability.weight, torch.zeros_like(applicability.weight)):
            raise RuntimeError("applicability head retained a random initialization")
    return applicability, family, verified


def batch_classify_loss(applicability, family, pooled, rows: Sequence[dict], contract: dict[str, Any]):
    """Mean of masked per-row losses. Unbind is not included."""
    torch, nn = _torch()
    index = family_index()
    app_index: list[int] = []
    app_target: list[int] = []
    app_weight: list[float] = []
    fam_index: list[int] = []
    fam_target: list[int] = []
    fam_weight: list[float] = []
    for position, row in enumerate(rows):
        plan = example_loss(row, contract)
        if plan["applicability_weight"] is not None:
            app_index.append(position)
            app_target.append(APPLICABILITY.index(plan["applicability_target"]))
            app_weight.append(float(plan["applicability_weight"]))
        if plan["family_weight"] is not None:
            fam_index.append(position)
            fam_target.append(index[plan["family_target"]])
            fam_weight.append(float(plan["family_weight"]))

    def _weighted(layer, positions: list[int], targets: list[int], weights: list[float]):
        if not positions:
            return None
        logits = layer(pooled[positions])
        gold = torch.tensor(targets, device=logits.device)
        nll = nn.functional.cross_entropy(logits, gold, reduction="none")
        scale = torch.tensor(weights, device=logits.device, dtype=nll.dtype)
        return (nll * scale).mean()

    applicability_loss = _weighted(applicability, app_index, app_target, app_weight)
    family_loss = _weighted(family, fam_index, fam_target, fam_weight)
    terms = [term for term in (applicability_loss, family_loss) if term is not None]
    if not terms:
        return None
    total = terms[0] if len(terms) == 1 else terms[0] + terms[1]
    return {
        "total": total,
        "applicability": applicability_loss,
        "family": family_loss,
    }
