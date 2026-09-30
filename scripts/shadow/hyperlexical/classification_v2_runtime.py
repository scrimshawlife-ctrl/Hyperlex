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
from .classification_v2_prototype import (
    FUSION_ALPHA,
    FUSION_BETA,
    LAMBDA_PROTO,
    PROTO_TAU,
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


def _prototype_family_type():
    torch, nn = _torch()

    class PrototypeFamilyHead(nn.Module):
        """Frozen prototype cosine plus a learned residual. Prototypes are buffers."""

        def __init__(self, hidden: int, prototypes, residual_weight, residual_bias, multipliers):
            super().__init__()
            self.residual = nn.Linear(hidden, len(ACTIVE_FAMILY_VOCABULARY))
            proto = torch.tensor(prototypes, dtype=self.residual.weight.dtype)
            resid_w = torch.tensor(residual_weight, dtype=self.residual.weight.dtype)
            resid_b = torch.tensor(residual_bias, dtype=self.residual.bias.dtype)
            scale = torch.tensor(multipliers, dtype=self.residual.weight.dtype)
            self.register_buffer("prototypes", proto)
            self.register_buffer("denominator_weights", scale)
            with torch.no_grad():
                self.residual.weight.copy_(resid_w)
                self.residual.bias.copy_(resid_b)
            if self.prototypes.requires_grad or any(parameter.requires_grad for name, parameter in self.named_parameters() if name.startswith("prototypes")):
                raise RuntimeError("FAMILY_PROTOTYPE_UNAVAILABLE")

        def cosine(self, pooled):
            hidden = torch.nn.functional.normalize(pooled, dim=-1)
            anchors = torch.nn.functional.normalize(self.prototypes, dim=-1)
            return hidden @ anchors.T

        def forward(self, pooled):
            hidden = torch.nn.functional.normalize(pooled, dim=-1)
            cosine = self.cosine(pooled)
            residual = self.residual(hidden)
            return _fuse(cosine, residual)

        def contrastive_nll(self, pooled, targets):
            cosine = self.cosine(pooled)
            logits = cosine / PROTO_TAU
            peak = logits.max(dim=-1, keepdim=True).values
            weights = self.denominator_weights[targets]
            shifted = (logits - peak).exp() * weights
            log_denom = shifted.sum(dim=-1).log() + peak.squeeze(-1)
            gold = logits.gather(1, targets.unsqueeze(1)).squeeze(1)
            return log_denom - gold

    return PrototypeFamilyHead


def _fuse(cosine, residual):
    torch, _nn = _torch()

    def _standardize(values):
        mean = values.mean(dim=-1, keepdim=True)
        variance = (values - mean).pow(2).mean(dim=-1, keepdim=True)
        deviation = variance.sqrt()
        scaled = (values - mean) / deviation.clamp_min(1e-12)
        return torch.where(deviation > 0, scaled, torch.zeros_like(scaled))

    proto = _standardize(cosine / PROTO_TAU)
    learned = _standardize(residual)
    return FUSION_ALPHA * proto + FUSION_BETA * learned


def build_geometry_heads(hidden: int, v1_classify, source_labels: Sequence[str], witness: dict | None = None):
    """Install frozen semantic anchors and the residual initialization."""
    from .classification_v2_prototype import assess_geometry_witness, denominator_multipliers

    applicability = zero_linear(hidden, len(APPLICABILITY))
    if witness is None:
        raise RuntimeError("FAMILY_PROTOTYPE_UNAVAILABLE")
    weight = v1_classify.weight.detach().cpu().tolist()
    bias = v1_classify.bias.detach().cpu().tolist()
    mapped = map_family_rows(source_labels, weight, bias)
    verified = assess_geometry_witness(witness, mapped)
    if not verified.get("pass"):
        raise RuntimeError(verified.get("detail") or "FAMILY_PROTOTYPE_UNAVAILABLE")
    multipliers = denominator_multipliers(list(ACTIVE_FAMILY_VOCABULARY), witness["hard_negatives"])
    family = _prototype_family_type()(
        hidden,
        witness["weight"],
        witness["residual_weight"],
        witness["residual_bias"],
        multipliers,
    )
    if any(name.startswith("prototypes") for name, _parameter in family.named_parameters()):
        raise RuntimeError("FAMILY_PROTOTYPE_UNAVAILABLE")
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
    family_ce = _weighted(family, fam_index, fam_target, fam_weight)
    family_proto = None
    if family_ce is not None and hasattr(family, "contrastive_nll"):
        gold = torch.tensor(fam_target, device=pooled.device)
        nll = family.contrastive_nll(pooled[fam_index], gold)
        scale = torch.tensor(fam_weight, device=nll.device, dtype=nll.dtype)
        family_proto = (nll * scale).mean()
    if family_ce is None:
        family_loss = None
    elif family_proto is None:
        family_loss = family_ce
    else:
        family_loss = family_ce + (LAMBDA_PROTO * family_proto)
    terms = [term for term in (applicability_loss, family_loss) if term is not None]
    if not terms:
        return None
    total = terms[0] if len(terms) == 1 else terms[0] + terms[1]
    return {
        "total": total,
        "applicability": applicability_loss,
        "family": family_loss,
        "family_ce": family_ce,
        "family_proto": family_proto,
    }
