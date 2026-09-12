"""Opt-in ModernBERT forward for E2. Lazy torch. No Hub. No hyperlex import."""

from __future__ import annotations

import json
from pathlib import Path
from typing import NoReturn

from .align import atom_token_index, offsets_from_tokenizer, pool_indices
from .layout import HIDDEN, MAX_LEN, TRUNK, UNK
from .save_pretrained import flatten_weight_tensors, split_weight_tensors


def _error(message: str, cause: Exception | None = None) -> NoReturn:
    from .eval_unbind import TrunkForwardError

    if cause is None:
        raise TrunkForwardError(message)
    raise TrunkForwardError(message) from cause


def _import_torch():
    try:
        import torch
        from torch import nn
    except ImportError as exc:
        _error("trunk-forward requested but torch is not importable", exc)
    return torch, nn


def _load_maps(model_dir: Path, heads_blob: dict | None) -> dict:
    candidates: list[dict] = []
    for name in ("config.json", "layout.json"):
        path = model_dir / name
        if not path.is_file():
            continue
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(blob, dict):
            candidates.append(blob)
    if heads_blob:
        if isinstance(heads_blob.get("maps"), dict):
            candidates.append(heads_blob["maps"])
        if isinstance(heads_blob.get("layout"), dict):
            candidates.append(heads_blob["layout"])
    for blob in candidates:
        role_vocab = blob.get("role_vocab")
        filler_vocab = blob.get("filler_vocab")
        if isinstance(role_vocab, list) and isinstance(filler_vocab, list) and filler_vocab:
            families = blob.get("families")
            if not isinstance(families, list) or not families:
                from .layout import FAMILIES

                families = list(FAMILIES)
            return {
                "families": families,
                "family_of": {f: i for i, f in enumerate(families)},
                "role_vocab": role_vocab,
                "filler_vocab": filler_vocab,
                "role_of": {r: i for i, r in enumerate(role_vocab)},
                "filler_of": {f: i for i, f in enumerate(filler_vocab)},
            }
    _error(f"trunk-forward requested but role/filler vocab missing in {model_dir}")


def _torch_load(torch, path: Path, device):
    try:
        return torch.load(str(path), map_location=device, weights_only=False)
    except TypeError:
        return torch.load(str(path), map_location=device)


def encoder_forward_note(*, loaded: int, present: int) -> str:
    if present == 0:
        return (
            "No encoder.* tensors in artifact; last trainable layers stay at "
            "trunk snapshot — unbind_exact may diverge from train val."
        )
    if loaded == 0:
        return (
            "encoder.* tensors present but none matched trunk keys; "
            "unbind_exact may diverge from train val."
        )
    return f"Applied {loaded} saved encoder trainable tensors."


def apply_encoder_trainable(encoder, tensors: dict) -> dict:
    """Overlay saved encoder.* tensors. Unexpected keys ignored. Empty is a no-op."""
    if not tensors:
        return {"loaded": 0, "unexpected": [], "present": 0}
    sd_keys = set(encoder.state_dict().keys())
    mapped = {}
    unexpected = []
    for raw, value in tensors.items():
        dest = _resolve_encoder_key(str(raw), sd_keys)
        if dest is None:
            unexpected.append(raw)
            continue
        mapped[dest] = value
    if mapped:
        encoder.load_state_dict(mapped, strict=False)
    return {"loaded": len(mapped), "unexpected": unexpected, "present": len(tensors)}


def _resolve_encoder_key(raw: str, sd_keys: set) -> str | None:
    if raw.startswith("encoder."):
        candidates = (raw[len("encoder.") :], raw)
    else:
        candidates = (raw, f"encoder.{raw}")
    for key in candidates:
        if key in sd_keys:
            return key
    return None


def _weight_parts(weight_path: Path, torch) -> tuple[dict, dict, dict | None]:
    """filler_head state, encoder tensors (encoder.* keys), optional heads.pt blob."""
    if weight_path.name == "model.safetensors":
        try:
            from safetensors.torch import load_file
        except ImportError as exc:
            _error("trunk-forward requested but safetensors is not importable", exc)
        split = split_weight_tensors(load_file(str(weight_path), device="cpu"))
        if "weight" not in split["filler_head"]:
            _error("model.safetensors missing filler_head.weight")
        return split["filler_head"], split["encoder"], None
    blob = _torch_load(torch, weight_path, "cpu")
    if not isinstance(blob, dict) or "filler_head" not in blob:
        _error(f"{weight_path.name} missing filler_head")
    encoder = blob.get("encoder") if isinstance(blob.get("encoder"), dict) else {}
    encoder = {
        k: v
        for k, v in flatten_weight_tensors({"encoder": encoder}).items()
        if k.startswith("encoder.")
    }
    return blob["filler_head"], encoder, blob


def _load_filler_head(nn, hidden: int, state: dict, maps: dict):
    weight = state.get("weight")
    if weight is None:
        _error("filler_head missing weight")
    out_f, in_f = int(weight.shape[0]), int(weight.shape[1])
    if in_f != hidden:
        _error(f"filler_head in_features {in_f} != hidden {hidden}")
    n_vocab = len(maps["filler_vocab"])
    if out_f != n_vocab:
        _error(f"filler_vocab {n_vocab} != filler_head out {out_f}")
    head = nn.Linear(in_f, out_f)
    head.load_state_dict(state)
    return head


def _load_trunk(trunk_dir: Path, model_dir: Path):
    try:
        from transformers import AutoModel, AutoTokenizer
    except ImportError as exc:
        _error("trunk-forward requested but transformers is not importable", exc)
    cfg_path = model_dir / "config.json"
    if cfg_path.is_file():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cfg = {}
        if cfg.get("base_model") not in (None, TRUNK):
            _error(f"unexpected base_model {cfg.get('base_model')}")
    tok = AutoTokenizer.from_pretrained(str(trunk_dir), local_files_only=True)
    encoder = AutoModel.from_pretrained(str(trunk_dir), local_files_only=True)
    return tok, encoder


def _offsets(tok, text: str):
    try:
        return offsets_from_tokenizer(tok, text, max_len=MAX_LEN)
    except TypeError:
        return None


def score_unbind_exact(encoder, filler_head, tok, maps, rows, device) -> tuple[float, int]:
    """Same per-row exact filler metric as train val `unbind_exact`."""
    encoder.eval()
    filler_head.eval()
    uhit = utot = 0
    for row in rows:
        fillers = list(row.get("fillers") or [])
        if not fillers:
            continue
        enc = tok(
            [row["text"]],
            padding=True,
            truncation=True,
            max_length=MAX_LEN,
            return_tensors="pt",
        )
        enc = {k: v.to(device) for k, v in enc.items()}
        states = encoder(**enc).last_hidden_state[0]
        offs = _offsets(tok, row["text"])
        ok = True
        for fill in fillers:
            idxs = pool_indices(states.size(0), atom_token_index(row["text"], fill, offs))
            pred = int(filler_head(states[idxs].mean(0)).argmax())
            gold = maps["filler_of"].get(fill, maps["filler_of"][UNK])
            if pred != gold:
                ok = False
        uhit += int(ok)
        utot += 1
    return uhit / max(1, utot), utot


def run_unbind_exact(
    *,
    trunk_dir: Path,
    model_dir: Path,
    weight_path: Path,
    spans: list[dict],
) -> dict:
    torch, nn = _import_torch()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    filler_state, encoder_tensors, heads_blob = _weight_parts(weight_path, torch)
    maps = _load_maps(model_dir, heads_blob)
    tok, encoder = _load_trunk(trunk_dir, model_dir)
    hidden = int(getattr(encoder.config, "hidden_size", HIDDEN))
    if hidden != HIDDEN:
        _error(f"hidden {hidden} != {HIDDEN}")
    applied = apply_encoder_trainable(encoder, encoder_tensors)
    if applied["present"] and applied["loaded"] == 0:
        _error("encoder trainable tensors present but none matched trunk keys")
    filler_head = _load_filler_head(nn, hidden, filler_state, maps)
    encoder.to(device)
    filler_head.to(device)
    from .eval_unbind import spans_to_unbind_rows

    rows = spans_to_unbind_rows(spans)
    if not rows:
        _error("trunk-forward requested but no unbind test spans")
    acc, n_eval = score_unbind_exact(encoder, filler_head, tok, maps, rows, device)
    return {
        "unbind_exact": acc,
        "n_unbind_eval": n_eval,
        "device": str(device),
        "cuda": bool(torch.cuda.is_available()),
        "encoder_trainable_loaded": applied["loaded"],
        "encoder_trainable_present": applied["present"],
        "encoder_note": encoder_forward_note(
            loaded=applied["loaded"], present=applied["present"]
        ),
    }
