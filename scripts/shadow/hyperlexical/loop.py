"""Spark train loop. Gate only."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .align import atom_token_index, offsets_from_tokenizer, pool_indices
from .export import export_dataset, repo_root, write_export
from .layout import (
    FAMILIES,
    HIDDEN,
    MAX_LEN,
    MODEL_ID_SEED,
    TRUNK,
    UNK,
    describe,
    label_maps,
    resolve_last_trainable,
)
from .eval_forward import apply_encoder_trainable
from .filler_filter import assert_publishable_vocab, filter_mode, filter_unbind_rows
from .provenance import provenance
from .release_set import maybe_release
from .save_pretrained import (
    collect_encoder_trainable,
    save_heads,
    split_weight_tensors,
    write_skeleton,
)
from .training_routing import route_rows
from .unbind_curriculum import (
    plan_unbind_curriculum,
    resolve_curriculum_schedule,
    select_unbind_for_epoch,
)
from .unbind_metrics import mapped_filler, mapped_pred, summarize_unbind_pairs
from .unbind_recipe import (
    apply_unbind_force_train,
    resolve_unbind_inferred_weight,
    resolve_unbind_morph_margin,
    shape_unbind_train,
    unbind_row_sample_weight,
)
from .unbind_head_slot import (
    apply_head_slot_weight,
    resolve_unbind_head_slot_weight,
)
from .unbind_second_slot import (
    apply_second_slot_weight,
    resolve_unbind_second_slot_weight,
)
from .unbind_residual import (
    residual_row_record,
    resolve_unbind_residual_dump_path,
    write_residual_dump,
)
from .unbind_slot_ce import (
    UNBIND_SLOT_CE_AUX_LAMBDA,
    combine_unbind_train_terms,
    resolve_unbind_primary_mode,
)

UNBIND_LOSS_WEIGHT_ENV = "HYPERLEX_UNBIND_LOSS_WEIGHT"
UNBIND_EVERY_N_ENV = "HYPERLEX_UNBIND_EVERY_N"
SAVE_BEST_UNBIND_ENV = "HYPERLEX_SAVE_BEST_UNBIND"
INIT_FROM_ENV = "HYPERLEX_INIT_FROM"
INIT_EXPAND_VOCAB_ENV = "HYPERLEX_INIT_EXPAND_VOCAB"
UNBIND_LOSS_WEIGHT_DEFAULT = 1.0
UNBIND_EVERY_N_DEFAULT = 1


def resolve_save_best_unbind(raw: str | None = None) -> bool:
    """When true, persist best-by-val-unbind_exact weights as primary model.safetensors.

    morph35 peak-not-saved: epoch_metrics recorded ep16 0.5372 but only final
    weights were written. Opt-in via HYPERLEX_SAVE_BEST_UNBIND=1.
    """
    if raw is None:
        raw = os.environ.get(SAVE_BEST_UNBIND_ENV)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return False
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def resolve_init_from(raw: str | None = None) -> Path | None:
    """Optional warm-start dir with model.safetensors (or heads.pt).

    Opt-in via HYPERLEX_INIT_FROM=/path/to/prior seed (e.g. morph36 best).
    """
    if raw is None:
        raw = os.environ.get(INIT_FROM_ENV)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None
    path = Path(str(raw).strip()).expanduser()
    if not path.is_dir():
        raise ValueError(f"{INIT_FROM_ENV} must be an existing directory, got {path}")
    return path


def resolve_init_expand_vocab(raw: str | None = None) -> bool:
    """When true, warm-load remaps shared role/filler rows into expanded vocabs.

    Default fail-closed on vocab mismatch. Opt-in via HYPERLEX_INIT_EXPAND_VOCAB=1
    so a smaller prior seed (e.g. morph65 max pos_5) can warm a harvest that added
    pos_6+/new fillers: copy overlapping labels by name, leave new rows at init.
    """
    if raw is None:
        raw = os.environ.get(INIT_EXPAND_VOCAB_ENV)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return False
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _init_weight_path(init_dir: Path) -> Path:
    for name in ("model.safetensors", "heads.pt"):
        candidate = init_dir / name
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"{INIT_FROM_ENV}={init_dir} missing model.safetensors or heads.pt"
    )


def _read_init_vocabs(init_dir: Path) -> tuple[list | None, list | None]:
    for name in ("layout.json", "config.json"):
        path = init_dir / name
        if not path.is_file():
            continue
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(blob, dict):
            continue
        role = blob.get("role_vocab")
        filler = blob.get("filler_vocab")
        if isinstance(role, list) and isinstance(filler, list) and filler:
            return role, filler
    return None, None


def _remap_linear_rows(module, state: dict, init_labels: list, current_labels: list, head: str) -> dict:
    """Copy overlapping out-rows from init Linear state into current module by label name."""
    weight = state.get("weight")
    if weight is None:
        raise ValueError(f"{INIT_FROM_ENV} {head} missing weight")
    if int(getattr(weight, "shape", [0])[0]) != len(init_labels):
        raise ValueError(
            f"{INIT_FROM_ENV} {head} weight rows {tuple(weight.shape)} != "
            f"init vocab {len(init_labels)}"
        )
    if int(module.weight.shape[0]) != len(current_labels):
        raise ValueError(
            f"{INIT_FROM_ENV} {head} module rows {tuple(module.weight.shape)} != "
            f"current vocab {len(current_labels)}"
        )
    current_of = {lab: i for i, lab in enumerate(current_labels)}
    mapped = 0
    skipped = 0
    for ii, lab in enumerate(init_labels):
        ci = current_of.get(lab)
        if ci is None:
            skipped += 1
            continue
        module.weight.data[ci].copy_(weight[ii].detach())
        mapped += 1
    bias = state.get("bias")
    if bias is not None and module.bias is not None:
        if int(getattr(bias, "shape", [0])[0]) != len(init_labels):
            raise ValueError(
                f"{INIT_FROM_ENV} {head} bias rows != init vocab {len(init_labels)}"
            )
        for ii, lab in enumerate(init_labels):
            ci = current_of.get(lab)
            if ci is None:
                continue
            module.bias.data[ci].copy_(bias[ii].detach())
    if mapped == 0:
        raise ValueError(
            f"{INIT_FROM_ENV} {head} expand remap matched 0/{len(init_labels)} labels"
        )
    return {
        "mapped": mapped,
        "skipped_init_only": skipped,
        "new_current_rows": len(current_labels) - mapped,
        "init_n": len(init_labels),
        "current_n": len(current_labels),
    }


def warm_load_checkpoint(
    encoder,
    classify,
    role_head,
    filler_head,
    maps: dict,
    init_dir: Path,
    *,
    expand_vocab: bool | None = None,
) -> dict:
    """Load heads + trainable encoder tensors from a prior seed dump. Fail closed.

    When expand_vocab is true (or HYPERLEX_INIT_EXPAND_VOCAB=1), role/filler heads
    remap overlapping labels by name into the current larger vocab; classify still
    loads strict. Default remains exact-vocab match.
    """
    if expand_vocab is None:
        expand_vocab = resolve_init_expand_vocab()
    weight_path = _init_weight_path(init_dir)
    init_roles, init_fillers = _read_init_vocabs(init_dir)
    cur_roles = list(maps.get("role_vocab") or [])
    cur_fillers = list(maps.get("filler_vocab") or [])
    roles_match = init_roles is None or init_roles == cur_roles
    fillers_match = init_fillers is None or init_fillers == cur_fillers
    vocab_match = roles_match and fillers_match
    if not vocab_match and not expand_vocab:
        if init_roles is not None and init_roles != cur_roles:
            raise ValueError(
                f"{INIT_FROM_ENV} role_vocab mismatch vs current export "
                f"(init={len(init_roles)} current={len(cur_roles)})"
            )
        raise ValueError(
            f"{INIT_FROM_ENV} filler_vocab mismatch vs current export "
            f"(init={len(init_fillers or [])} current={len(cur_fillers)})"
        )
    if not vocab_match and expand_vocab:
        if init_roles is None or init_fillers is None:
            raise ValueError(
                f"{INIT_EXPAND_VOCAB_ENV}=1 requires init role_vocab+filler_vocab "
                f"in {init_dir}/config.json (or layout.json)"
            )

    if weight_path.name == "model.safetensors":
        from safetensors.torch import load_file

        split = split_weight_tensors(load_file(str(weight_path), device="cpu"))
        heads_blob = None
    else:
        import torch

        try:
            blob = torch.load(str(weight_path), map_location="cpu", weights_only=False)
        except TypeError:
            blob = torch.load(str(weight_path), map_location="cpu")
        if not isinstance(blob, dict):
            raise ValueError(f"{weight_path} is not a heads state dict")
        split = {
            "classify": blob.get("classify") or {},
            "role_head": blob.get("role_head") or {},
            "filler_head": blob.get("filler_head") or {},
            "encoder": {
                k: v
                for k, v in (
                    {} if not isinstance(blob.get("encoder"), dict) else blob["encoder"]
                ).items()
            },
        }
        # normalize encoder keys to encoder.* for apply_encoder_trainable
        enc = {}
        for k, v in split["encoder"].items():
            key = str(k)
            enc[key if key.startswith("encoder.") else f"encoder.{key}"] = v
        split["encoder"] = enc
        heads_blob = blob

    classify_state = split.get("classify") or {}
    if not classify_state:
        raise ValueError(f"{weight_path} missing classify tensors")
    classify.load_state_dict(classify_state, strict=True)

    expand_receipt: dict = {
        "expand_vocab": bool(expand_vocab and not vocab_match),
        "vocab_match": vocab_match,
    }
    if vocab_match or not expand_vocab:
        for name, module in (("role_head", role_head), ("filler_head", filler_head)):
            state = split.get(name) or {}
            if not state:
                raise ValueError(f"{weight_path} missing {name} tensors")
            module.load_state_dict(state, strict=True)
    else:
        role_state = split.get("role_head") or {}
        filler_state = split.get("filler_head") or {}
        if not role_state or not filler_state:
            raise ValueError(f"{weight_path} missing role_head/filler_head tensors")
        expand_receipt["role"] = _remap_linear_rows(
            role_head, role_state, list(init_roles), cur_roles, "role_head"
        )
        expand_receipt["filler"] = _remap_linear_rows(
            filler_head, filler_state, list(init_fillers), cur_fillers, "filler_head"
        )

    applied = apply_encoder_trainable(encoder, split.get("encoder") or {})
    if applied["present"] and applied["loaded"] == 0:
        raise ValueError(
            f"{INIT_FROM_ENV} encoder tensors present but none matched trunk keys"
        )
    return {
        "init_from": str(init_dir),
        "weight_file": weight_path.name,
        "encoder_trainable_loaded": applied["loaded"],
        "encoder_trainable_present": applied["present"],
        "heads_blob": bool(heads_blob),
        "init_expand_vocab": bool(expand_vocab),
        **expand_receipt,
    }


def _cpu_module_state(module) -> dict:
    return {k: v.detach().cpu().contiguous() for k, v in module.state_dict().items()}


def _build_weight_state(encoder, classify, role_head, filler_head, maps, layout) -> dict:
    return {
        "classify": _cpu_module_state(classify),
        "role_head": _cpu_module_state(role_head),
        "filler_head": _cpu_module_state(filler_head),
        "encoder": collect_encoder_trainable(encoder),
        "maps": {k: v for k, v in maps.items() if k not in {"family_of", "role_of", "filler_of"}},
        "layout": layout,
    }


def resolve_unbind_loss_weight(raw: str | float | int | None = None) -> float:
    """Scale on unbind loss before backward. Default 1.0. Fail-closed if invalid."""
    if raw is None:
        raw = os.environ.get(UNBIND_LOSS_WEIGHT_ENV)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return UNBIND_LOSS_WEIGHT_DEFAULT
    try:
        weight = float(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{UNBIND_LOSS_WEIGHT_ENV} must be a finite number >= 0, got {raw!r}") from exc
    if weight < 0 or weight != weight or weight == float("inf"):
        raise ValueError(f"{UNBIND_LOSS_WEIGHT_ENV} must be a finite number >= 0, got {raw!r}")
    return weight


def resolve_unbind_every_n(raw: str | int | None = None) -> int:
    """Classify-batch stride for an extra unbind step. Default 1 = epoch-end only."""
    if raw is None:
        raw = os.environ.get(UNBIND_EVERY_N_ENV)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return UNBIND_EVERY_N_DEFAULT
    try:
        n = int(str(raw).strip(), 10)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{UNBIND_EVERY_N_ENV} must be a positive int, got {raw!r}") from exc
    if n < 1:
        raise ValueError(f"{UNBIND_EVERY_N_ENV} must be a positive int, got {n}")
    return n


TASK_ROUTING_ENV = "HYPERLEX_TASK_ROUTING"
TASK_ROUTINGS = ("route_rows", "legacy_split")


def task_routing(raw: str | None = None) -> str:
    """``route_rows`` (default) or ``legacy_split`` (pre-routing loop; reproduces morph75–78).

    ``legacy_split`` selects rows by ``task == "classify"`` / ``task == "unbind"`` only, so
    ``classify+unbind`` rows are not trained. Unknown values fail closed.
    """
    value = (os.environ.get(TASK_ROUTING_ENV, "") if raw is None else raw).strip() or "route_rows"
    if value not in TASK_ROUTINGS:
        raise ValueError(f"{TASK_ROUTING_ENV} must be one of {TASK_ROUTINGS}")
    return value


def should_interleave_unbind(classify_batch_index: int, every_n: int) -> bool:
    """True after classify batch `index` (0-based) when every_n > 1."""
    if every_n <= 1:
        return False
    return (classify_batch_index + 1) % every_n == 0


def prepare_unbind_splits(rows: list) -> tuple[list, list, dict]:
    """Train recipe after route_rows. Val frozen unless force-train env is set.

    ``HYPERLEX_UNBIND_FORCE_TRAIN_PATH`` may move authorized OBSERVED exacts
    from val→train (accept-style). Empty/unset → val untouched.
    """
    if task_routing() == "legacy_split":
        train = [r for r in rows if r.get("task") == "unbind" and r.get("split") == "train"]
        val = [r for r in rows if r.get("task") == "unbind" and r.get("split") == "val"]
    else:
        routed, _ = route_rows(rows)
        train = routed["unbind"]["train"]
        val = routed["unbind"]["val"]
    train, val, force_stats = apply_unbind_force_train(train, val)
    train, filt_train = filter_unbind_rows(train)
    val, filt_val = filter_unbind_rows(val)
    shaped, stats = shape_unbind_train(train)
    stats = {
        **stats,
        **force_stats,
        "filler_filter": filt_train["filler_filter"],
        "n_filler_rows_dropped_train": filt_train["n_filler_rows_dropped"],
        "n_filler_rows_dropped_val": filt_val["n_filler_rows_dropped"],
    }
    return shaped, val, stats


def _require_local_model(trunk: Path):
    from transformers import AutoModel, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(str(trunk), local_files_only=True)
    model = AutoModel.from_pretrained(str(trunk), local_files_only=True)
    return tok, model


def _layers(encoder):
    if hasattr(encoder, "layers"):
        return encoder.layers
    inner = getattr(encoder, "encoder", None)
    if inner is not None and hasattr(inner, "layers"):
        return inner.layers
    return None


def freeze_encoder(encoder, last_trainable: int | None = None) -> tuple[int, int]:
    layers = _layers(encoder)
    n_layers = len(list(layers)) if layers is not None else None
    used = resolve_last_trainable(last_trainable, layer_count=n_layers)
    for p in encoder.parameters():
        p.requires_grad = False
    n = 0
    if layers is None:
        return 0, used
    for block in list(layers)[-used:]:
        for p in block.parameters():
            p.requires_grad = True
            n += p.numel()
    return n, used


def _offsets(tok, text: str):
    try:
        return offsets_from_tokenizer(tok, text, max_len=MAX_LEN)
    except TypeError:
        return None


def run_loop(
    trunk: Path,
    out_dir: Path,
    *,
    include_live: bool = False,
    live_store: Path | None = None,
) -> dict:
    root = repo_root()
    bundle = export_dataset(root, include_live=include_live, live_store=live_store)
    release_rows_, release_stats = maybe_release(bundle["rows"])
    if release_stats["release_set"]:
        bundle = {**bundle, "rows": release_rows_}
    if any(r.get("role_scheme") == "reviewed_occurrences" for r in bundle["rows"]):
        raise ValueError("reviewed occurrences require occurrence-aware loop alignment")
    routed, task_accounting = route_rows(bundle["rows"])
    task_accounting = {**task_accounting, "task_routing": task_routing()}
    export_dir = Path(os.environ.get("HYPERLEX_EXPORT_DIR") or (root / "specs" / "007-hyperlexical-model" / "exports"))
    export_dir.mkdir(parents=True, exist_ok=True)
    write_export(export_dir, bundle)
    if task_routing() == "legacy_split":
        classify_tr = [r for r in bundle["rows"] if r["task"] == "classify" and r["split"] == "train"]
        classify_va = [r for r in bundle["rows"] if r["task"] == "classify" and r["split"] == "val"]
    else:
        classify_tr = routed["classify"]["train"]
        classify_va = routed["classify"]["val"]
    unbind_tr, unbind_va, unbind_recipe = prepare_unbind_splits(bundle["rows"])
    if len(classify_tr) < 8:
        raise RuntimeError("not enough classify train rows")

    import torch
    from torch import nn
    from torch.optim import AdamW

    maps = label_maps(unbind_tr + unbind_va)
    if filter_mode() == "strict":
        assert_publishable_vocab(maps["filler_vocab"])
    tok, encoder = _require_local_model(trunk)
    hidden = int(getattr(encoder.config, "hidden_size", HIDDEN))
    if hidden != HIDDEN:
        raise RuntimeError(f"hidden {hidden} != {HIDDEN}")
    n_unfrozen, last_trainable_used = freeze_encoder(encoder)
    classify = nn.Linear(hidden, len(FAMILIES))
    role_head = nn.Linear(hidden, len(maps["role_vocab"]))
    filler_head = nn.Linear(hidden, len(maps["filler_vocab"]))
    init_from = resolve_init_from()
    init_receipt: dict = {"init_from": None, "warm_start": False}
    if init_from is not None:
        init_receipt = {
            "warm_start": True,
            **warm_load_checkpoint(
                encoder, classify, role_head, filler_head, maps, init_from
            ),
        }
    trainable = [p for p in encoder.parameters() if p.requires_grad] + list(classify.parameters()) + list(role_head.parameters()) + list(filler_head.parameters())
    opt = AdamW(trainable, lr=float(os.environ.get("HYPERLEX_TRAIN_LR", "2e-5")))
    epochs = int(os.environ.get("HYPERLEX_TRAIN_EPOCHS", "2"))
    batch = int(os.environ.get("HYPERLEX_TRAIN_BATCH", "8"))
    unbind_loss_weight = resolve_unbind_loss_weight()
    unbind_every_n = resolve_unbind_every_n()
    morph_margin = resolve_unbind_morph_margin()
    inferred_weight = resolve_unbind_inferred_weight()
    slot_ce_mode = resolve_unbind_primary_mode()
    unbind_primary = slot_ce_mode["unbind_primary"]
    head_slot_weight = resolve_unbind_head_slot_weight()
    second_slot_weight = resolve_unbind_second_slot_weight()
    curriculum = resolve_curriculum_schedule()
    curriculum_plan = plan_unbind_curriculum(unbind_tr, epochs, curriculum)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    for mod in (encoder, classify, role_head, filler_head):
        mod.to(device)
    encoder.train()
    losses = []
    epoch_metrics = []

    def encode_texts(texts):
        enc = tok(texts, padding=True, truncation=True, max_length=MAX_LEN, return_tensors="pt")
        return {k: v.to(device) for k, v in enc.items()}

    def unbind_loss(row):
        fillers = list(row.get("fillers") or [])
        roles = list(row.get("roles") or [])
        if not fillers:
            return None
        out = encoder(**encode_texts([row["text"]]))
        states = out.last_hidden_state[0]
        offs = _offsets(tok, row["text"])
        slot_ces = []
        aux_terms = []
        for k, fill in enumerate(fillers):
            idxs = pool_indices(states.size(0), atom_token_index(row["text"], fill, offs))
            h = states[idxs].mean(0)
            gold_f = maps["filler_of"].get(fill, maps["filler_of"][UNK])
            logits = filler_head(h)
            slot_ces.append(
                nn.functional.cross_entropy(
                    logits.unsqueeze(0), torch.tensor([gold_f], device=device)
                )
            )
            hard = [nf for nf in (row.get("hard_neg_fillers") or []) if nf]
            if hard:
                gold_logit = logits[gold_f]
                neg_vals = []
                for nf in hard:
                    ni = maps["filler_of"].get(nf)
                    if ni is None or ni == gold_f:
                        continue
                    neg_vals.append(logits[ni])
                if neg_vals:
                    stacked = torch.stack(neg_vals)
                    aux_terms.append(torch.relu(stacked + morph_margin - gold_logit).sum())
            if k < len(roles):
                gold_r = maps["role_of"].get(roles[k], maps["role_of"][UNK])
                aux_terms.append(
                    nn.functional.cross_entropy(
                        role_head(h).unsqueeze(0), torch.tensor([gold_r], device=device)
                    )
                )
        weighted_slots = apply_head_slot_weight(slot_ces, head_slot_weight)
        weighted_slots = apply_second_slot_weight(weighted_slots, second_slot_weight)
        return combine_unbind_train_terms(
            weighted_slots,
            aux_terms,
            primary=unbind_primary,
            aux_lambda=UNBIND_SLOT_CE_AUX_LAMBDA,
        )

    # Keep last train loss on-device; avoid per-step .cpu() sync (morph68 hang:
    # post-SAVE_BEST host spin at ~98% CPU / GPU util 0 with mem held).
    last_train_loss = None

    def step_unbind(row) -> None:
        nonlocal last_train_loss
        if unbind_loss_weight == 0:
            return
        uloss = unbind_loss(row)
        if uloss is None:
            return
        row_w = unbind_row_sample_weight(row, inferred_weight)
        scaled = uloss * unbind_loss_weight * row_w
        opt.zero_grad()
        scaled.backward()
        opt.step()
        last_train_loss = scaled.detach()

    residual_dump_path = resolve_unbind_residual_dump_path()
    last_residual_records: list[dict] = []
    save_best_unbind = resolve_save_best_unbind()
    best_exact = float("-inf")
    best_metrics: dict | None = None
    best_state: dict | None = None
    best_residual_records: list[dict] = []
    progress_path = out_dir / "epoch-progress.jsonl"

    @torch.no_grad()
    def score():
        nonlocal last_residual_records
        encoder.eval()
        classify.eval()
        filler_head.eval()
        hit = tot = 0
        for row in classify_va or classify_tr[:8]:
            out = encoder(**encode_texts([row["text"]]))
            pred = int(classify(out.last_hidden_state[:, 0]).argmax(-1)[0])
            gold = maps["family_of"].get(row["lineage"], maps["family_of"]["none"])
            hit += int(pred == gold)
            tot += 1
        pairs: list[tuple[list[str], list[str]]] = []
        residual_records: list[dict] = []
        for row in unbind_va or unbind_tr[:8]:
            fillers = list(row.get("fillers") or [])
            if not fillers:
                continue
            out = encoder(**encode_texts([row["text"]]))
            states = out.last_hidden_state[0]
            offs = _offsets(tok, row["text"])
            gold_strs: list[str] = []
            pred_strs: list[str] = []
            for fill in fillers:
                idxs = pool_indices(states.size(0), atom_token_index(row["text"], fill, offs))
                pred = int(filler_head(states[idxs].mean(0)).argmax())
                gold_strs.append(mapped_filler(maps, fill))
                pred_strs.append(mapped_pred(maps, pred))
            pairs.append((gold_strs, pred_strs))
            if residual_dump_path:
                rec = residual_row_record(
                    text=str(row.get("text") or ""),
                    gold=gold_strs,
                    pred=pred_strs,
                    row=row,
                )
                if rec is not None:
                    residual_records.append(rec)
        last_residual_records = residual_records
        encoder.train()
        classify.train()
        filler_head.train()
        metrics = summarize_unbind_pairs(pairs)
        metrics["classify_acc"] = hit / max(1, tot)
        metrics["n_classify_eval"] = tot
        return metrics

    out_dir.mkdir(parents=True, exist_ok=True)
    layout = describe(maps)
    layout["last_trainable"] = last_trainable_used
    layout["aligner"] = "char_span + offset_mapping"
    write_skeleton(out_dir, maps=maps)

    for ep in range(epochs):
        phase_rows, phase_meta = select_unbind_for_epoch(unbind_tr, ep, curriculum)
        unbind_cycle = 0
        classify_batch_i = 0
        for i in range(0, len(classify_tr), batch):
            chunk = classify_tr[i : i + batch]
            y = torch.tensor([maps["family_of"].get(c["lineage"], maps["family_of"]["none"]) for c in chunk], device=device)
            out = encoder(**encode_texts([c["text"] for c in chunk]))
            loss = nn.functional.cross_entropy(classify(out.last_hidden_state[:, 0]), y)
            opt.zero_grad()
            loss.backward()
            opt.step()
            last_train_loss = loss.detach()
            if should_interleave_unbind(classify_batch_i, unbind_every_n) and phase_rows:
                step_unbind(phase_rows[unbind_cycle % len(phase_rows)])
                unbind_cycle += 1
            classify_batch_i += 1
        for row in phase_rows:
            step_unbind(row)
        metrics = score()
        metrics["epoch"] = ep
        metrics["unbind_phase"] = phase_meta["phase"]
        metrics["n_unbind_phase"] = phase_meta["n_rows"]
        metrics["unbind_phase_fallback_full_mix"] = phase_meta["fallback_full_mix"]
        epoch_metrics.append(metrics)
        exact = float(metrics.get("unbind_exact") or 0.0)
        if last_train_loss is not None:
            # One host sync per epoch (not per step).
            losses.append(float(last_train_loss.item()))
        saved_best = False
        if save_best_unbind and exact > best_exact:
            if device.type == "cuda":
                torch.cuda.synchronize()
            best_exact = exact
            best_metrics = dict(metrics)
            best_state = _build_weight_state(
                encoder, classify, role_head, filler_head, maps, layout
            )
            best_residual_records = list(last_residual_records)
            best_dir = out_dir / "best"
            write_skeleton(best_dir, maps=maps)
            save_heads(best_dir, best_state)
            (best_dir / "best-checkpoint.json").write_text(
                json.dumps(
                    {
                        "metric": "unbind_exact",
                        "epoch": ep,
                        "unbind_exact": exact,
                        "unbind_token_f1": best_metrics.get("unbind_token_f1"),
                        "unbind_slot_f1": best_metrics.get("unbind_slot_f1"),
                        "classify_acc": best_metrics.get("classify_acc"),
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            saved_best = True
            if device.type == "cuda":
                torch.cuda.synchronize()
                torch.cuda.empty_cache()
        # Durable heartbeat — morph68 hung silently after ep4 with frozen docker logs.
        progress = {
            "epoch": ep,
            "unbind_exact": exact,
            "best_unbind_exact": None if best_exact == float("-inf") else best_exact,
            "saved_best": saved_best,
            "n_unbind_phase": phase_meta["n_rows"],
            "unbind_phase": phase_meta["phase"],
            "classify_acc": metrics.get("classify_acc"),
        }
        with progress_path.open("a", encoding="utf-8") as pf:
            pf.write(json.dumps(progress, sort_keys=True) + "\n")
            pf.flush()
        print(
            f"[epoch {ep}] unbind_exact={exact:.6f} best={best_exact if best_exact != float('-inf') else None} saved_best={saved_best}",
            flush=True,
        )

    final_state = _build_weight_state(
        encoder, classify, role_head, filler_head, maps, layout
    )
    # Always write final epoch weights under a distinct name when best-save is on,
    # then promote best → primary model.safetensors (fixes morph35 peak-not-saved).
    if save_best_unbind and best_state is not None:
        final_file = save_heads(out_dir, final_state)
        # rename primary final dump aside, then write best as primary
        final_path = out_dir / final_file
        aside = out_dir / (
            "model.final.safetensors" if final_file == "model.safetensors" else "heads.final.pt"
        )
        if final_path.exists():
            final_path.replace(aside)
        weight_file = save_heads(out_dir, best_state)
        primary_val = best_metrics or {}
        gated_from = "best_unbind_exact"
        residual_for_dump = best_residual_records
    else:
        weight_file = save_heads(out_dir, final_state)
        primary_val = epoch_metrics[-1] if epoch_metrics else {}
        gated_from = "final_epoch"
        residual_for_dump = last_residual_records
        aside = None

    last = epoch_metrics[-1] if epoch_metrics else {}
    residual_receipt: dict = {
        "unbind_residual_dump": "",
        "n_unbind_residual": 0,
        "unbind_residual_themes": {},
    }
    if residual_dump_path:
        residual_receipt = write_residual_dump(residual_dump_path, residual_for_dump)
    receipt = {
        "schema": "hyperlex.hyperlexical.train_receipt.v0.1",
        "model_id": MODEL_ID_SEED,
        "trunk": TRUNK,
        "trunk_dir": str(trunk),
        "device": str(device),
        "cuda": bool(torch.cuda.is_available()),
        "epochs": epochs,
        **provenance(root),
        "n_train_classify": len(classify_tr),
        "task_accounting": task_accounting,
        "n_train_unbind": len(unbind_tr),
        "n_unfrozen_encoder": n_unfrozen,
        "n_encoder_tensors": len(final_state.get("encoder") or {}),
        "last_trainable": last_trainable_used,
        "unbind_loss_weight": unbind_loss_weight,
        "unbind_every_n": unbind_every_n,
        "unbind_primary": slot_ce_mode["unbind_primary"],
        "unbind_slot_ce_armed": slot_ce_mode["unbind_slot_ce_armed"],
        "unbind_slot_ce_aux_lambda": slot_ce_mode["unbind_slot_ce_aux_lambda"],
        "unbind_head_slot_weight": head_slot_weight,
        "unbind_second_slot_weight": second_slot_weight,
        "n_unbind_observed": unbind_recipe["n_unbind_observed"],
        "n_unbind_inferred": unbind_recipe["n_unbind_inferred"],
        "unbind_observed_upsample": unbind_recipe["unbind_observed_upsample"],
        "unbind_inferred_cap": unbind_recipe["unbind_inferred_cap"],
        "unbind_inferred_weight": inferred_weight,
        "n_unbind_morph_negatives": unbind_recipe["n_unbind_morph_negatives"],
        "unbind_morph_margin": morph_margin,
        "unbind_curriculum": curriculum_plan["enabled"],
        "unbind_curriculum_pos_epochs": curriculum_plan["pos_epochs"],
        "unbind_curriculum_type_epochs": curriculum_plan["type_epochs"],
        "unbind_curriculum_phases": curriculum_plan["phases"],
        "n_unbind_curriculum_positional": curriculum_plan["n_unbind_positional"],
        "n_unbind_curriculum_type_slot": curriculum_plan["n_unbind_type_slot"],
        "n_unbind_curriculum_joint": curriculum_plan["n_unbind_joint"],
        "unbind_filler_denylist_lineages": unbind_recipe.get("unbind_filler_denylist_lineages", 0),
        "unbind_hard_atoms_path": unbind_recipe.get("unbind_hard_atoms_path", ""),
        "unbind_hard_upsample": unbind_recipe.get("unbind_hard_upsample", 1),
        "n_unbind_hard_atoms_matched": unbind_recipe.get("n_unbind_hard_atoms_matched", 0),
        "unbind_force_train_path": unbind_recipe.get("unbind_force_train_path", ""),
        "release_set": release_stats,
        "filler_filter": unbind_recipe.get("filler_filter"),
        "n_filler_rows_dropped_train": unbind_recipe.get("n_filler_rows_dropped_train", 0),
        "n_filler_rows_dropped_val": unbind_recipe.get("n_filler_rows_dropped_val", 0),
        "n_unbind_force_train": unbind_recipe.get("n_unbind_force_train", 0),
        "n_unbind_force_train_keys": unbind_recipe.get("n_unbind_force_train_keys", 0),
        "n_unbind_val_after_force_train": unbind_recipe.get(
            "n_unbind_val_after_force_train", 0
        ),
        "n_unbind_hard_extra_copies": unbind_recipe.get("n_unbind_hard_extra_copies", 0),
        "unbind_residual_dump": residual_receipt.get("unbind_residual_dump", ""),
        "n_unbind_residual": residual_receipt.get("n_unbind_residual", 0),
        "unbind_residual_themes": residual_receipt.get("unbind_residual_themes", {}),
        "unbind_residual_by_scheme": residual_receipt.get("unbind_residual_by_scheme", {}),
        "unbind_residual_by_class": residual_receipt.get("unbind_residual_by_class", {}),
        "unbind_residual_summary": residual_receipt.get("unbind_residual_summary", ""),
        "last_loss": losses[-1] if losses else None,
        "val": primary_val,
        "val_final": last,
        "val_best": best_metrics,
        "save_best_unbind": save_best_unbind,
        "primary_weights_from": gated_from,
        "best_unbind_exact": None if best_metrics is None else best_metrics.get("unbind_exact"),
        "best_epoch": None if best_metrics is None else best_metrics.get("epoch"),
        "final_weight_file": None if aside is None else aside.name,
        "init_from": init_receipt.get("init_from"),
        "warm_start": bool(init_receipt.get("warm_start")),
        "init_weight_file": init_receipt.get("weight_file"),
        "init_encoder_trainable_loaded": init_receipt.get("encoder_trainable_loaded"),
        "init_expand_vocab": bool(init_receipt.get("init_expand_vocab")),
        "init_expand_vocab_applied": bool(init_receipt.get("expand_vocab")),
        "init_expand_role": init_receipt.get("role"),
        "init_expand_filler": init_receipt.get("filler"),
        "epoch_metrics": epoch_metrics,
        "weight_file": weight_file,
        "aligner": "char_span + offset_mapping",
        "data_sha256": bundle["sha256"],
        "include_live": include_live,
        "live_included": bundle["counts"].get("live_included", 0),
        "name_gate": False,
        "e2_pass": False,
        "brier": None,
        "forecast_eligible": False,
        "note": "HF-shaped dump. Not Hyperlexical until E2.",
    }
    (out_dir / "layout.json").write_text(json.dumps(layout, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "train-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "config-train.json").write_text(
        json.dumps(
            {
                "lr": os.environ.get("HYPERLEX_TRAIN_LR", "2e-5"),
                "epochs": epochs,
                "batch": batch,
                "max_len": MAX_LEN,
                "last_trainable": last_trainable_used,
                "unbind_loss_weight": unbind_loss_weight,
                "unbind_every_n": unbind_every_n,
                "unbind_primary": slot_ce_mode["unbind_primary"],
                "unbind_slot_ce_armed": slot_ce_mode["unbind_slot_ce_armed"],
                "unbind_slot_ce_aux_lambda": slot_ce_mode["unbind_slot_ce_aux_lambda"],
                "unbind_head_slot_weight": head_slot_weight,
                "unbind_second_slot_weight": second_slot_weight,
                "unbind_observed_upsample": unbind_recipe["unbind_observed_upsample"],
                "unbind_inferred_cap": unbind_recipe["unbind_inferred_cap"],
                "unbind_inferred_weight": inferred_weight,
                "n_unbind_morph_negatives": unbind_recipe["n_unbind_morph_negatives"],
                "unbind_morph_margin": morph_margin,
                "unbind_curriculum": curriculum_plan["enabled"],
                "unbind_curriculum_pos_epochs": curriculum_plan["pos_epochs"],
                "unbind_curriculum_type_epochs": curriculum_plan["type_epochs"],
                "unbind_filler_denylist_lineages": unbind_recipe.get(
                    "unbind_filler_denylist_lineages", 0
                ),
                "unbind_hard_atoms_path": unbind_recipe.get("unbind_hard_atoms_path", ""),
                "unbind_hard_upsample": unbind_recipe.get("unbind_hard_upsample", 1),
                "n_unbind_hard_atoms_matched": unbind_recipe.get(
                    "n_unbind_hard_atoms_matched", 0
                ),
                "n_unbind_hard_extra_copies": unbind_recipe.get(
                    "n_unbind_hard_extra_copies", 0
                ),
                "unbind_force_train_path": unbind_recipe.get("unbind_force_train_path", ""),
                "n_unbind_force_train": unbind_recipe.get("n_unbind_force_train", 0),
                "n_unbind_force_train_keys": unbind_recipe.get(
                    "n_unbind_force_train_keys", 0
                ),
                "n_unbind_val_after_force_train": unbind_recipe.get(
                    "n_unbind_val_after_force_train", 0
                ),
                "save_best_unbind": save_best_unbind,
                "init_from": init_receipt.get("init_from"),
                "warm_start": bool(init_receipt.get("warm_start")),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return receipt
