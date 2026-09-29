"""Deterministic role/filler row expansion.

Mapped names keep the warm-start weight and bias. Names that exist only in the
target vocabulary are exact zeros. Names that exist only in the warm start are
omitted. Nothing in this module trains or constructs an optimizer.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

SELECT006_EXPERIMENT = "HLX-EXP-2026-09-29-SELECT-006"
STOP_BEFORE_OPTIMIZER_ENV = "HLX_STOP_BEFORE_OPTIMIZER"
VERIFIED = "ZERO_INIT_LOADER_VERIFIED"

SOURCE_MISMATCH = "ZERO_INIT_LOADER_SOURCE_MISMATCH"
TARGET_MISMATCH = "ZERO_INIT_LOADER_TARGET_MISMATCH"
DUPLICATE_NAME = "ZERO_INIT_LOADER_DUPLICATE_NAME"
DIMENSION_MISMATCH = "ZERO_INIT_LOADER_DIMENSION_MISMATCH"
MAPPING_FAILURE = "ZERO_INIT_LOADER_MAPPING_FAILURE"
NONZERO_NEW_ROWS = "ZERO_INIT_LOADER_NONZERO_NEW_ROWS"
COPY_MISMATCH = "ZERO_INIT_LOADER_COPY_MISMATCH"
NONDETERMINISTIC = "ZERO_INIT_LOADER_NONDETERMINISTIC"
ENTRYPOINT_BYPASS = "ZERO_INIT_LOADER_ENTRYPOINT_BYPASS"
VERIFICATION_FAILURE = "ZERO_INIT_LOADER_VERIFICATION_FAILURE"


class ZeroInitLoaderError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


def select006_experiment_active() -> bool:
    return os.environ.get("HLX_EXPERIMENT_ID", "").strip() == SELECT006_EXPERIMENT


def pre_optimizer_stop_requested() -> bool:
    return os.environ.get(STOP_BEFORE_OPTIMIZER_ENV) == "1"


def _duplicates(labels: list[str]) -> list[str]:
    seen: set[str] = set()
    found: list[str] = []
    for label in labels:
        if label in seen and label not in found:
            found.append(label)
        seen.add(label)
    return found


def _require_string_labels(labels: list[Any], code: str, head: str, side: str) -> list[str]:
    if not isinstance(labels, list) or any(not isinstance(label, str) or label == "" for label in labels):
        raise ZeroInitLoaderError(code, f"{head} {side} vocabulary is not a list of names")
    duplicates = _duplicates(labels)
    if duplicates:
        raise ZeroInitLoaderError(DUPLICATE_NAME, f"{head} {side} vocabulary repeats {duplicates[0]}")
    return labels


def _tensor_sha256(tensor) -> str:
    raw = tensor.detach().cpu().contiguous()
    payload = raw.numpy().tobytes()
    return hashlib.sha256(payload).hexdigest()


def _labels_sha256(labels: list[str]) -> str:
    return hashlib.sha256("\n".join(labels).encode("utf-8")).hexdigest()


def expansion_expected(head: str) -> dict[str, Any] | None:
    """Sealed SELECT-006 counts. Other experiments keep the general name policy."""
    if not select006_experiment_active():
        return None
    from .select_006_efficiency_preservation import vocabulary_expansion_pin

    pin = vocabulary_expansion_pin()
    if head == "role_head":
        return {
            "source_count": pin["warm_start_role_count"],
            "target_count": pin["target_role_count"],
            "mapped": pin["mapped_existing_roles"],
            "new": pin["newly_initialized_roles"],
            "removed": pin["warm_start_only_roles"],
            "new_names": list(pin["new_role_names_in_sorted_order"]),
        }
    if head == "filler_head":
        filler = pin["filler_expansion"]
        return {
            "source_count": filler["warm_start_filler_count"],
            "target_count": filler["target_filler_count"],
            "mapped": filler["mapped_existing_fillers"],
            "new": filler["newly_initialized_fillers"],
            "removed": filler["skipped_warm_start_only"],
        }
    raise ZeroInitLoaderError(VERIFICATION_FAILURE, f"unknown head {head}")


def select006_guard_vocab(expand_vocab: bool, vocab_match: bool) -> None:
    if not select006_experiment_active():
        return
    if not expand_vocab:
        raise ZeroInitLoaderError(
            ENTRYPOINT_BYPASS,
            "SELECT-006 warm load requires vocabulary expansion",
        )
    if vocab_match:
        raise ZeroInitLoaderError(
            TARGET_MISMATCH,
            "SELECT-006 target vocabulary matches the warm start",
        )


def expand_named_linear(
    module,
    state: dict,
    source_labels: list[str],
    target_labels: list[str],
    head: str,
    *,
    expected: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Copy shared rows by name and set target-only rows to exact zero."""
    import torch

    source = _require_string_labels(list(source_labels), SOURCE_MISMATCH, head, "source")
    target = _require_string_labels(list(target_labels), TARGET_MISMATCH, head, "target")
    weight = state.get("weight")
    if weight is None:
        raise ZeroInitLoaderError(SOURCE_MISMATCH, f"{head} source weight is missing")
    if int(getattr(weight, "ndim", 0)) != 2:
        raise ZeroInitLoaderError(DIMENSION_MISMATCH, f"{head} source weight is not a matrix")
    if int(weight.shape[0]) != len(source):
        raise ZeroInitLoaderError(
            SOURCE_MISMATCH,
            f"{head} source rows {int(weight.shape[0])} != source vocabulary {len(source)}",
        )
    if int(module.weight.ndim) != 2 or int(module.weight.shape[0]) != len(target):
        raise ZeroInitLoaderError(
            TARGET_MISMATCH,
            f"{head} target rows {tuple(module.weight.shape)} != target vocabulary {len(target)}",
        )
    if int(weight.shape[1]) != int(module.weight.shape[1]):
        raise ZeroInitLoaderError(
            DIMENSION_MISMATCH,
            f"{head} hidden {int(weight.shape[1])} != target hidden {int(module.weight.shape[1])}",
        )
    source_bias = state.get("bias")
    if module.bias is None or source_bias is None:
        raise ZeroInitLoaderError(DIMENSION_MISMATCH, f"{head} weight/bias pair is incomplete")
    if int(getattr(source_bias, "ndim", 0)) != 1 or int(source_bias.shape[0]) != len(source):
        raise ZeroInitLoaderError(SOURCE_MISMATCH, f"{head} source bias length != source vocabulary")
    if int(module.bias.shape[0]) != len(target):
        raise ZeroInitLoaderError(TARGET_MISMATCH, f"{head} target bias length != target vocabulary")

    if expected is not None:
        if int(expected["source_count"]) != len(source):
            raise ZeroInitLoaderError(SOURCE_MISMATCH, f"{head} source count != sealed contract")
        if int(expected["target_count"]) != len(target):
            raise ZeroInitLoaderError(TARGET_MISMATCH, f"{head} target count != sealed contract")

    source_of = {label: index for index, label in enumerate(source)}
    target_set = set(target)
    src_weight = weight.detach().to(device=module.weight.device, dtype=module.weight.dtype)
    src_bias = source_bias.detach().to(device=module.bias.device, dtype=module.bias.dtype)
    mapped: list[str] = []
    new_names: list[str] = []
    with torch.no_grad():
        for index, label in enumerate(target):
            source_index = source_of.get(label)
            if source_index is None:
                module.weight.data[index].zero_()
                module.bias.data[index].zero_()
                new_names.append(label)
                continue
            module.weight.data[index].copy_(src_weight[source_index])
            module.bias.data[index].copy_(src_bias[source_index])
            mapped.append(label)
        for index, label in enumerate(target):
            source_index = source_of.get(label)
            if source_index is None:
                if not torch.equal(module.weight.data[index], torch.zeros_like(module.weight.data[index])):
                    raise ZeroInitLoaderError(NONZERO_NEW_ROWS, f"{head} new weight row {label}")
                if not torch.equal(module.bias.data[index], torch.zeros_like(module.bias.data[index])):
                    raise ZeroInitLoaderError(NONZERO_NEW_ROWS, f"{head} new bias row {label}")
                continue
            if not torch.equal(module.weight.data[index], src_weight[source_index]):
                raise ZeroInitLoaderError(COPY_MISMATCH, f"{head} weight row {label}")
            if not torch.equal(module.bias.data[index], src_bias[source_index]):
                raise ZeroInitLoaderError(COPY_MISMATCH, f"{head} bias row {label}")

    removed = [label for label in source if label not in target_set]
    if not mapped:
        raise ZeroInitLoaderError(MAPPING_FAILURE, f"{head} matched no source rows")
    if expected is not None:
        if int(expected["mapped"]) != len(mapped):
            raise ZeroInitLoaderError(MAPPING_FAILURE, f"{head} mapped count != sealed contract")
        if int(expected["new"]) != len(new_names):
            raise ZeroInitLoaderError(TARGET_MISMATCH, f"{head} new-row count != sealed contract")
        if int(expected["removed"]) != len(removed):
            raise ZeroInitLoaderError(SOURCE_MISMATCH, f"{head} removed count != sealed contract")
        sealed_new = expected.get("new_names")
        if sealed_new is not None and list(sealed_new) != new_names:
            raise ZeroInitLoaderError(TARGET_MISMATCH, f"{head} new names != sealed order")

    return {
        "mapped": len(mapped),
        "skipped_init_only": len(removed),
        "new_current_rows": len(new_names),
        "init_n": len(source),
        "current_n": len(target),
        "new_names": new_names,
        "new_row_policy": "exact_zero",
        "copy_comparison": "exact",
        "zero_comparison": "exact",
    }


def _require_zero_rows(module, labels: list[str], names: list[str]) -> None:
    import torch

    index_of = {label: index for index, label in enumerate(labels)}
    for name in names:
        index = index_of.get(name)
        if index is None:
            raise ZeroInitLoaderError(TARGET_MISMATCH, f"new row {name} is not in the target vocabulary")
        if not torch.equal(module.weight.data[index], torch.zeros_like(module.weight.data[index])):
            raise ZeroInitLoaderError(NONZERO_NEW_ROWS, f"weight row {name}")
        if module.bias is None or not torch.equal(
            module.bias.data[index], torch.zeros_like(module.bias.data[index])
        ):
            raise ZeroInitLoaderError(NONZERO_NEW_ROWS, f"bias row {name}")


def select006_training_init_guard(maps: dict, role_head, filler_head, receipt: dict) -> None:
    """Fail closed unless SELECT-006 initialization used the zero-row loader."""
    if not select006_experiment_active():
        return
    if not receipt.get("expand_vocab"):
        raise ZeroInitLoaderError(
            ENTRYPOINT_BYPASS,
            "SELECT-006 training initialization did not expand through the loader",
        )
    from .select_006_efficiency_preservation import vocabulary_expansion_pin

    pin = vocabulary_expansion_pin()
    filler_pin = pin["filler_expansion"]
    role = receipt.get("role") or {}
    filler = receipt.get("filler") or {}
    if role.get("new_row_policy") != "exact_zero" or filler.get("new_row_policy") != "exact_zero":
        raise ZeroInitLoaderError(ENTRYPOINT_BYPASS, "training initialization left new rows uninitialized")
    if int(role.get("mapped", -1)) != int(pin["mapped_existing_roles"]):
        raise ZeroInitLoaderError(MAPPING_FAILURE, "role mapped count")
    if int(role.get("new_current_rows", -1)) != int(pin["newly_initialized_roles"]):
        raise ZeroInitLoaderError(TARGET_MISMATCH, "role new-row count")
    if list(role.get("new_names") or []) != list(pin["new_role_names_in_sorted_order"]):
        raise ZeroInitLoaderError(TARGET_MISMATCH, "role new names")
    if int(filler.get("mapped", -1)) != int(filler_pin["mapped_existing_fillers"]):
        raise ZeroInitLoaderError(MAPPING_FAILURE, "filler mapped count")
    if int(filler.get("new_current_rows", -1)) != int(filler_pin["newly_initialized_fillers"]):
        raise ZeroInitLoaderError(TARGET_MISMATCH, "filler new-row count")
    if int(filler.get("skipped_init_only", -1)) != int(filler_pin["skipped_warm_start_only"]):
        raise ZeroInitLoaderError(SOURCE_MISMATCH, "filler removed count")
    role_vocab = list(maps["role_vocab"])
    filler_vocab = list(maps["filler_vocab"])
    if len(role_vocab) != int(pin["target_role_count"]) or role_vocab[0] != pin["unk_token"]:
        raise ZeroInitLoaderError(TARGET_MISMATCH, "role target vocabulary")
    if role_vocab[1:] != sorted(role_vocab[1:]):
        raise ZeroInitLoaderError(TARGET_MISMATCH, "role row order")
    if len(filler_vocab) != int(filler_pin["target_filler_count"]) or filler_vocab[0] != pin["unk_token"]:
        raise ZeroInitLoaderError(TARGET_MISMATCH, "filler target vocabulary")
    if filler_vocab[1:] != sorted(filler_vocab[1:]):
        raise ZeroInitLoaderError(TARGET_MISMATCH, "filler row order")
    _require_zero_rows(role_head, role_vocab, list(role["new_names"]))
    _require_zero_rows(filler_head, filler_vocab, list(filler["new_names"]))


def expanded_loader_hashes(role_head, filler_head, maps: dict) -> dict[str, str]:
    role_weight = _tensor_sha256(role_head.weight.data)
    role_bias = _tensor_sha256(role_head.bias.data)
    filler_weight = _tensor_sha256(filler_head.weight.data)
    filler_bias = _tensor_sha256(filler_head.bias.data)
    body = json.dumps(
        {
            "filler_bias_sha256": filler_bias,
            "filler_vocab_sha256": _labels_sha256(list(maps["filler_vocab"])),
            "filler_weight_sha256": filler_weight,
            "role_bias_sha256": role_bias,
            "role_vocab_sha256": _labels_sha256(list(maps["role_vocab"])),
            "role_weight_sha256": role_weight,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return {
        "expanded_role_weight_sha256": role_weight,
        "expanded_role_bias_sha256": role_bias,
        "expanded_filler_weight_sha256": filler_weight,
        "expanded_filler_bias_sha256": filler_bias,
        "expanded_loader_witness_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
    }


def pre_optimizer_receipt(role_head, filler_head, maps: dict, init_receipt: dict) -> dict[str, Any]:
    role = init_receipt.get("role") or {}
    filler = init_receipt.get("filler") or {}
    return {
        "schema": "hyperlex.select_006_pre_optimizer.v1",
        "stopped_before_optimizer": True,
        "optimizer_constructed": False,
        "training_started": False,
        "training_launch_authorized": False,
        "epochs": 0,
        "gradient_steps": 0,
        "weights_mutated_by_training": False,
        "execution_loader_status": VERIFIED,
        "init_from": init_receipt.get("init_from"),
        "expand_vocab": bool(init_receipt.get("expand_vocab")),
        "role_mapped": role.get("mapped"),
        "role_new": role.get("new_current_rows"),
        "role_new_names": list(role.get("new_names") or []),
        "filler_mapped": filler.get("mapped"),
        "filler_new": filler.get("new_current_rows"),
        "filler_removed": filler.get("skipped_init_only"),
        "role_count": len(maps["role_vocab"]),
        "filler_count": len(maps["filler_vocab"]),
        **expanded_loader_hashes(role_head, filler_head, maps),
    }
