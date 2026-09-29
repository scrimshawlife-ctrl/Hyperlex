"""SELECT-006 zero-init loader witness. Does not train or construct an optimizer."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path("/home/morpheus/Hyperlex")
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.identity_ledger import IdentityLedger
from hyperlexical.layout import FAMILIES
from hyperlexical.loop import run_loop, warm_load_checkpoint
from hyperlexical.select_006_efficiency_preservation import (
    BEST_SHA256,
    BEST_WEIGHTS,
    EXPERIMENT_ID,
    TRUNK_DIR,
    TRUNK_SHA256,
    WARM_START_DIR,
    WARM_START_SHA256,
    vocabulary_expansion_pin,
)
from hyperlexical.zero_init_loader import (
    NONDETERMINISTIC,
    VERIFICATION_FAILURE,
    VERIFIED,
    expanded_loader_hashes,
)

LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
TARGET_CONFIG = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select005/config.json"
)
RESERVE_MANIFEST = Path(
    "/home/morpheus/hlx-private/exp-20260929-select-006/reserve-acquisition-002/RESERVE_MANIFEST.json"
)
RESERVE_MANIFEST_SHA256 = "33ee588bdd13a322020e2a0105a71265899b856b44b6c3fcde40eb943b36cab6"
SPEC = Path("/home/morpheus/hlx-private/exp-20260929-select-006/spec-001")
OUT = Path("/home/morpheus/hlx-private/exp-20260929-select-006/zero-init-loader-001")
TRAIN_OUT = Path("/tmp/select006-zero-init-out-41af")
EXPORT_DIR = Path("/tmp/select006-zero-init-export-41af")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fail(code: str, detail: str) -> None:
    raise SystemExit(f"{code}: {detail}")


class _AcceptEncoder:
    """Accept encoder tensors so head expansion can be built without a second trunk."""

    def __init__(self, keys: list[str]) -> None:
        self._keys = list(keys)
        self.loaded: dict = {}

    def state_dict(self) -> dict:
        import torch

        return {key: torch.zeros(1) for key in self._keys}

    def load_state_dict(self, state, strict=False):
        self.loaded = dict(state)
        return type("R", (), {"missing_keys": [], "unexpected_keys": []})()


def _load_split():
    from safetensors.torch import load_file
    from hyperlexical.save_pretrained import split_weight_tensors

    path = Path(WARM_START_DIR) / "model.safetensors"
    if _sha256(path) != WARM_START_SHA256:
        _fail("ZERO_INIT_LOADER_SOURCE_MISMATCH", "warm-start sha256")
    return split_weight_tensors(load_file(str(path), device="cpu"))


def _build(split: dict, maps: dict, seed: int):
    import torch
    from torch import nn

    torch.manual_seed(seed)
    classify = nn.Linear(int(split["classify"]["weight"].shape[1]), len(FAMILIES))
    role = nn.Linear(int(split["role_head"]["weight"].shape[1]), len(maps["role_vocab"]))
    filler = nn.Linear(int(split["filler_head"]["weight"].shape[1]), len(maps["filler_vocab"]))
    with torch.no_grad():
        role.weight.fill_(9.0)
        role.bias.fill_(9.0)
        filler.weight.fill_(9.0)
        filler.bias.fill_(9.0)
    receipt = warm_load_checkpoint(
        _AcceptEncoder(list(split["encoder"])),
        classify,
        role,
        filler,
        maps,
        Path(WARM_START_DIR),
        expand_vocab=True,
    )
    if not receipt.get("encoder_trainable_loaded"):
        _fail(VERIFICATION_FAILURE, "warm-start encoder tensors were not read")
    return receipt, role, filler


def _exact(module, state: dict, source: list[str], target: list[str], new_names: list[str]) -> None:
    import torch

    weight = state["weight"]
    bias = state["bias"]
    source_of = {label: index for index, label in enumerate(source)}
    for index, label in enumerate(target):
        source_index = source_of.get(label)
        if source_index is None:
            if label not in new_names:
                _fail(VERIFICATION_FAILURE, f"unexpected new row {label}")
            if not torch.equal(module.weight[index], torch.zeros_like(module.weight[index])):
                _fail("ZERO_INIT_LOADER_NONZERO_NEW_ROWS", label)
            if not torch.equal(module.bias[index], torch.zeros_like(module.bias[index])):
                _fail("ZERO_INIT_LOADER_NONZERO_NEW_ROWS", label)
            continue
        src_w = weight[source_index].to(dtype=module.weight.dtype)
        src_b = bias[source_index].to(dtype=module.bias.dtype)
        if not torch.equal(module.weight[index], src_w) or not torch.equal(module.bias[index], src_b):
            _fail("ZERO_INIT_LOADER_COPY_MISMATCH", label)


def _pins() -> dict[str, str]:
    return {
        "best_sha256": _sha256(Path(BEST_WEIGHTS)),
        "ledger_events_sha256": _sha256(LEDGER / "events.jsonl"),
        "ledger_projection_sha256": _sha256(LEDGER / "ledger.json"),
        "reserve_manifest_sha256": _sha256(RESERVE_MANIFEST),
        "warm_start_sha256": _sha256(Path(WARM_START_DIR) / "model.safetensors"),
    }


def _binding(before: dict[str, str]) -> None:
    ledger = IdentityLedger.load(LEDGER)
    active = ledger.active_reserve_records(EXPERIMENT_ID)
    counts = ledger.active_reserve_counts(EXPERIMENT_ID)
    expected = {
        "classify": 32,
        "classify_non_none": 32,
        "classify_observed": 32,
        "unbind_clean": 5,
    }
    if counts != expected or len(active) != 37:
        _fail(VERIFICATION_FAILURE, f"reserve counts {counts} identities {len(active)}")
    payload = {
        "counts": counts,
        "experiment_id": EXPERIMENT_ID,
        "identities": len(active),
        "ledger_dir": str(LEDGER),
        "ledger_events_sha256": before["ledger_events_sha256"],
        "ledger_projection_sha256": before["ledger_projection_sha256"],
        "lifecycle": "EVAL_RESERVE",
        "schema": "hyperlex.reserve_binding.v1",
        "scored": False,
    }
    path = OUT / "RESERVE_BINDING_FOR_INIT_DRY_RUN.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.environ["HLX_RESERVE_BINDING"] = str(path)


def _arm_environment() -> None:
    os.environ["HLX_EXPERIMENT_ID"] = EXPERIMENT_ID
    os.environ["HLX_SCHEDULE_ARM"] = "candidate"
    os.environ["HYPERLEX_ALLOW_TRAIN"] = "1"
    os.environ["HLX_STOP_BEFORE_OPTIMIZER"] = "1"
    os.environ["HLX_EVAL_RESERVE_LEDGER"] = str(LEDGER)
    os.environ["HLX_BASELINE_ENV"] = str(SPEC / "BASELINE_ENV.json")
    os.environ["HLX_CANDIDATE_ENV"] = str(SPEC / "CANDIDATE_ENV.json")
    os.environ["HLX_BEST_SHA256"] = BEST_SHA256
    os.environ["HLX_BEST_WEIGHTS"] = BEST_WEIGHTS
    os.environ["HLX_TRUNK_SHA256"] = TRUNK_SHA256
    os.environ["HYPERLEX_EXPORT_DIR"] = str(EXPORT_DIR)
    os.environ["HYPERLEX_TRAIN_OUT"] = str(TRAIN_OUT)
    for name in ("BASELINE_ENV.json", "CANDIDATE_ENV.json"):
        payload = json.loads((SPEC / name).read_text(encoding="utf-8"))
        for key, value in payload.items():
            os.environ[key] = str(value)
    os.environ["HLX_STOP_BEFORE_OPTIMIZER"] = "1"
    os.environ["HYPERLEX_ALLOW_TRAIN"] = "1"
    os.environ["HYPERLEX_TRAIN_OUT"] = str(TRAIN_OUT)
    os.environ["HYPERLEX_EXPORT_DIR"] = str(EXPORT_DIR)


def main() -> None:
    import torch

    OUT.mkdir(parents=True, exist_ok=True)
    if TRAIN_OUT.exists():
        _fail(VERIFICATION_FAILURE, "training output directory already exists")
    before = _pins()
    if before["best_sha256"] != BEST_SHA256:
        _fail(VERIFICATION_FAILURE, "BEST sha256")
    if before["warm_start_sha256"] != WARM_START_SHA256:
        _fail("ZERO_INIT_LOADER_SOURCE_MISMATCH", "warm start")
    if before["reserve_manifest_sha256"] != RESERVE_MANIFEST_SHA256:
        _fail(VERIFICATION_FAILURE, "reserve manifest")
    if _sha256(Path(TRUNK_DIR) / "model.safetensors") != TRUNK_SHA256:
        _fail(VERIFICATION_FAILURE, "trunk sha256")

    pin = vocabulary_expansion_pin()
    warm = json.loads((Path(WARM_START_DIR) / "config.json").read_text(encoding="utf-8"))
    target = json.loads(TARGET_CONFIG.read_text(encoding="utf-8"))
    source_roles = [str(item) for item in warm["role_vocab"]]
    source_fillers = [str(item) for item in warm["filler_vocab"]]
    target_roles = [str(item) for item in target["role_vocab"]]
    target_fillers = [str(item) for item in target["filler_vocab"]]
    if target_roles[0] != "<unk>" or target_roles[1:] != sorted(target_roles[1:]):
        _fail("ZERO_INIT_LOADER_TARGET_MISMATCH", "role order")
    if target_fillers[0] != "<unk>" or target_fillers[1:] != sorted(target_fillers[1:]):
        _fail("ZERO_INIT_LOADER_TARGET_MISMATCH", "filler order")
    maps = {"role_vocab": target_roles, "filler_vocab": target_fillers}
    os.environ["HLX_EXPERIMENT_ID"] = EXPERIMENT_ID
    split = _load_split()
    first, role, filler = _build(split, maps, 1)
    second, role_b, filler_b = _build(split, maps, 99)
    hashes = expanded_loader_hashes(role, filler, maps)
    again = expanded_loader_hashes(role_b, filler_b, maps)
    if hashes != again:
        _fail(NONDETERMINISTIC, "repeated loader hashes differ")
    new_roles = [label for label in target_roles if label not in set(source_roles)]
    new_fillers = [label for label in target_fillers if label not in set(source_fillers)]
    removed_fillers = [label for label in source_fillers if label not in set(target_fillers)]
    if new_roles != list(pin["new_role_names_in_sorted_order"]):
        _fail("ZERO_INIT_LOADER_TARGET_MISMATCH", "new role names")
    if len(removed_fillers) != pin["filler_expansion"]["skipped_warm_start_only"]:
        _fail("ZERO_INIT_LOADER_SOURCE_MISMATCH", "removed fillers")
    _exact(role, split["role_head"], source_roles, target_roles, new_roles)
    _exact(filler, split["filler_head"], source_fillers, target_fillers, new_fillers)
    if not torch.equal(role.weight, role_b.weight) or not torch.equal(filler.bias, filler_b.bias):
        _fail(NONDETERMINISTIC, "repeated tensors differ")

    _binding(before)
    _arm_environment()
    try:
        trained = run_loop(Path(TRUNK_DIR), TRAIN_OUT, include_live=False)
    except SystemExit as exc:
        receipt = getattr(exc, "receipt", None)
        if receipt is not None:
            print(json.dumps(receipt, indent=2, sort_keys=True))
        raise
    if trained.get("stopped_before_optimizer") is not True or trained.get("optimizer_constructed") is not False:
        _fail("ZERO_INIT_LOADER_ENTRYPOINT_BYPASS", "training entrypoint did not stop before the optimizer")
    if trained.get("execution_loader_status") != VERIFIED:
        _fail(VERIFICATION_FAILURE, "entrypoint status")
    for key, value in hashes.items():
        if trained.get(key) != value:
            _fail("ZERO_INIT_LOADER_ENTRYPOINT_BYPASS", key)
    if TRAIN_OUT.exists():
        _fail(VERIFICATION_FAILURE, "training output directory was created")
    after = _pins()
    if after != before:
        _fail(VERIFICATION_FAILURE, "pinned artifact changed")
    witness = {
        "best_sha256_after": after["best_sha256"],
        "best_sha256_before": before["best_sha256"],
        "copy_verification": "exact",
        "determinism": "identical",
        "epochs": 0,
        "execution_loader_status": VERIFIED,
        "expanded_filler_bias_sha256": hashes["expanded_filler_bias_sha256"],
        "expanded_filler_weight_sha256": hashes["expanded_filler_weight_sha256"],
        "expanded_loader_witness_sha256": hashes["expanded_loader_witness_sha256"],
        "expanded_role_bias_sha256": hashes["expanded_role_bias_sha256"],
        "expanded_role_weight_sha256": hashes["expanded_role_weight_sha256"],
        "filler_mapped": first["filler"]["mapped"],
        "filler_new": first["filler"]["new_current_rows"],
        "filler_removed": first["filler"]["skipped_init_only"],
        "filler_source_count": len(source_fillers),
        "filler_target_count": len(target_fillers),
        "gradient_steps": 0,
        "ledger_events_sha256_after": after["ledger_events_sha256"],
        "ledger_events_sha256_before": before["ledger_events_sha256"],
        "ledger_projection_sha256_after": after["ledger_projection_sha256"],
        "ledger_projection_sha256_before": before["ledger_projection_sha256"],
        "new_role_names": new_roles,
        "optimizer_constructed": False,
        "pre_optimizer": trained,
        "reserve_manifest_sha256_after": after["reserve_manifest_sha256"],
        "reserve_manifest_sha256_before": before["reserve_manifest_sha256"],
        "role_mapped": first["role"]["mapped"],
        "role_new": first["role"]["new_current_rows"],
        "role_order": "unk_then_sorted_labels",
        "role_source_count": len(source_roles),
        "role_target_count": len(target_roles),
        "row_order_verification": "exact",
        "schema": "hyperlex.select_006_zero_init_loader.v1",
        "training_entrypoint": "hyperlexical.loop.run_loop",
        "training_launch_authorized": False,
        "training_started": False,
        "warm_start_sha256": before["warm_start_sha256"],
        "weights_mutated_by_training": False,
        "zero_row_verification": "exact",
    }
    (OUT / "LOADER_WITNESS.json").write_text(
        json.dumps(witness, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({key: witness[key] for key in (
        "execution_loader_status",
        "expanded_role_weight_sha256",
        "expanded_role_bias_sha256",
        "expanded_filler_weight_sha256",
        "expanded_filler_bias_sha256",
        "expanded_loader_witness_sha256",
        "role_mapped",
        "role_new",
        "filler_mapped",
        "filler_new",
        "filler_removed",
        "optimizer_constructed",
        "training_started",
    )}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
