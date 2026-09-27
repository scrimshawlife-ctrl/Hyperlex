"""Spark train loop. Gate only."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

from .align import atom_token_index, offsets_from_tokenizer, pool_indices
from .export import export_dataset, repo_root, write_export
from .admission import AdmissionError, admit_training_run
from .train_input import train_input_receipt
from .classify_metrics import (
    NONE_LABEL,
    SELECT_METRIC_CLASSIFY,
    SELECT_METRIC_ENV,
    macro_f1_nonnone,
    none_false_positive_rate,
    resolve_select_metric,
)
from .classify_split import apply_classify_split_file
from .seed_control import apply_training_seed
from .force_train_overlap import enforce_force_train_disjoint
from .layout import (
    FAMILIES,
    HIDDEN,
    MAX_LEN,
    MODEL_ID_SEED,
    TRUNK,
    UNK,
    describe,
    label_maps_for_splits,
    resolve_last_trainable,
    resolve_vocab_train_only,
)
from .eval_forward import apply_encoder_trainable
from .filler_filter import assert_publishable_vocab, filter_mode, filter_unbind_rows
from .holdout_guard import (
    assert_no_holdout,
    filter_holdout_rows,
    holdout_receipt,
    load_holdout_spec,
    log_holdout,
)
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
EARLY_STOP_ENV = "HYPERLEX_EARLY_STOP"
EARLY_STOP_PATIENCE_ENV = "HYPERLEX_EARLY_STOP_PATIENCE"
EARLY_STOP_MIN_EPOCHS_ENV = "HYPERLEX_EARLY_STOP_MIN_EPOCHS"
STOP_REASON_MAX_EPOCHS = "max_epochs"
STOP_REASON_EARLY_STOPPING = "early_stopping"
# Observational seconds on epoch-progress.jsonl and the completion receipt.
# Python round() to 6 decimal places (microseconds). Not a selection input.
WALLCLOCK_SECONDS_DECIMALS = 6
_EARLY_STOP_OFF = frozenset({"0", "false", "no", "off"})
_EARLY_STOP_ON = frozenset({"1", "true", "yes", "on"})
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


@dataclass(frozen=True)
class EarlyStopConfig:
    """Optional classify-metric early stop. Default-off. Does not change the epoch cap."""

    enabled: bool
    max_epochs: int
    patience: int | None = None
    minimum_epochs: int | None = None
    select_metric: str = ""


def _parse_early_stop_int(env_name: str, raw: str | None) -> int:
    if raw is None or not str(raw).strip():
        raise ValueError(f"{env_name} is required when {EARLY_STOP_ENV} is enabled")
    text = str(raw).strip()
    sign = ""
    digits = text
    if text[0] in "+-":
        sign, digits = text[0], text[1:]
    if sign == "+" and not digits:
        raise ValueError(f"{env_name} must be an integer, got {raw!r}")
    if not digits.isdigit():
        raise ValueError(f"{env_name} must be an integer, got {raw!r}")
    return int(sign + digits)


def resolve_early_stop_config(*, max_epochs: int, select_metric: str) -> EarlyStopConfig:
    """Read early-stop env before the optimizer is constructed.

    Unset or disabled (0/false/no/off) leaves the configured epoch schedule
    unchanged. ``HYPERLEX_TRAIN_EPOCHS`` is only the max-epoch cap and never
    turns this on. Enabled runs require ``HLX_SELECT_METRIC=classify_macro_f1_nonnone``,
    patience >= 0, and minimum scored epochs in ``1..max_epochs``.
    """
    raw = os.environ.get(EARLY_STOP_ENV)
    token = "" if raw is None else str(raw).strip().lower()
    if raw is None or token == "" or token in _EARLY_STOP_OFF:
        return EarlyStopConfig(
            enabled=False,
            max_epochs=max_epochs,
            select_metric=select_metric,
        )
    if token not in _EARLY_STOP_ON:
        raise ValueError(
            f"{EARLY_STOP_ENV} must be unset, off, or on (1/true/yes/on), got {raw!r}"
        )
    if select_metric != SELECT_METRIC_CLASSIFY:
        raise ValueError(
            f"{EARLY_STOP_ENV} requires {SELECT_METRIC_ENV}={SELECT_METRIC_CLASSIFY}; "
            f"got {select_metric!r}"
        )
    patience = _parse_early_stop_int(
        EARLY_STOP_PATIENCE_ENV, os.environ.get(EARLY_STOP_PATIENCE_ENV)
    )
    minimum_epochs = _parse_early_stop_int(
        EARLY_STOP_MIN_EPOCHS_ENV, os.environ.get(EARLY_STOP_MIN_EPOCHS_ENV)
    )
    if patience < 0:
        raise ValueError(f"{EARLY_STOP_PATIENCE_ENV} must be >= 0, got {patience}")
    if minimum_epochs < 1:
        raise ValueError(
            f"{EARLY_STOP_MIN_EPOCHS_ENV} must be >= 1 scored epoch, got {minimum_epochs}"
        )
    if minimum_epochs > max_epochs:
        raise ValueError(
            f"{EARLY_STOP_MIN_EPOCHS_ENV}={minimum_epochs} exceeds "
            f"HYPERLEX_TRAIN_EPOCHS={max_epochs}"
        )
    return EarlyStopConfig(
        enabled=True,
        max_epochs=max_epochs,
        patience=patience,
        minimum_epochs=minimum_epochs,
        select_metric=select_metric,
    )


def note_strict_improvement(
    best_value: float,
    best_epoch: int | None,
    score: float,
    epoch_index: int,
) -> tuple[float, int | None, bool]:
    """Strict increase replaces the checkpoint. A tie keeps the earlier epoch."""
    if score > best_value:
        return score, epoch_index, True
    return best_value, best_epoch, False


def early_stop_break(
    *,
    enabled: bool,
    epoch_index: int,
    best_epoch: int | None,
    epochs_scored: int,
    minimum_epochs: int | None,
    patience: int | None,
    max_epochs: int,
) -> bool:
    """Return true only when the loop should break before the epoch cap.

    Call this after the epoch is scored and any strict improvement is recorded.
    Patience is ``epoch_index - best_epoch`` completed epochs after the best
    (0-based indices). The best epoch itself does not consume patience.
    Ties do not move ``best_epoch``, so they do consume patience.
    Do not stop before ``minimum_epochs`` epochs have been scored.
    When the patience condition lands on the final configured epoch, the max
    epoch cap wins and this returns false so the loop records ``max_epochs``.
    """
    if not enabled:
        return False
    if epoch_index + 1 >= max_epochs:
        return False
    if minimum_epochs is None or patience is None or best_epoch is None:
        return False
    if epochs_scored < minimum_epochs:
        return False
    return (epoch_index - best_epoch) >= patience


def round_seconds(value: float) -> float:
    """Seconds rounded to 6 decimal places. Observational; not a selection input."""
    return round(float(value), WALLCLOCK_SECONDS_DECIMALS)


def monotonic_seconds() -> float:
    """Monotonic clock in seconds. Tests replace this; production uses time.monotonic."""
    return time.monotonic()


def epoch_timing_fields(
    *,
    epoch_started: float,
    epoch_ended: float,
    training_started: float,
) -> dict[str, float]:
    """Wall-clock fields for one epoch-progress.jsonl row.

    Units are seconds. Both values use ``round_seconds`` (6 decimal places).
    ``epoch_wallclock_seconds`` is this epoch's scored body
    (epoch_ended - epoch_started). ``training_elapsed_seconds`` is the time
    from the start of the epoch loop to this epoch's end. Neither value is
    read by checkpoint selection or early stopping.
    """
    return {
        "epoch_wallclock_seconds": round_seconds(epoch_ended - epoch_started),
        "training_elapsed_seconds": round_seconds(epoch_ended - training_started),
    }


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
    ``HLX_HOLDOUT_MANIFESTS`` rows are dropped before that move and before
    hard-atom copies, then checked again so neither injection can put them back.
    """
    spec = load_holdout_spec()
    if task_routing() == "legacy_split":
        train = [r for r in rows if r.get("task") == "unbind" and r.get("split") == "train"]
        val = [r for r in rows if r.get("task") == "unbind" and r.get("split") == "val"]
    else:
        routed, _ = route_rows(rows)
        train = routed["unbind"]["train"]
        val = routed["unbind"]["val"]
    train, n_train = filter_holdout_rows(train, spec)
    val, n_val = filter_holdout_rows(val, spec)
    train, val, force_stats = apply_unbind_force_train(train, val)
    train, n_train_injected = filter_holdout_rows(train, spec)
    val, n_val_injected = filter_holdout_rows(val, spec)
    train, filt_train = filter_unbind_rows(train)
    val, filt_val = filter_unbind_rows(val)
    shaped, stats = shape_unbind_train(train)
    shaped, n_hard = filter_holdout_rows(shaped, spec)
    assert_no_holdout(shaped, spec, "unbind train")
    assert_no_holdout(val, spec, "unbind val")
    stats = {
        **stats,
        **force_stats,
        "filler_filter": filt_train["filler_filter"],
        "n_filler_rows_dropped_train": filt_train["n_filler_rows_dropped"],
        "n_filler_rows_dropped_val": filt_val["n_filler_rows_dropped"],
        "n_holdout_removed_train": n_train + n_train_injected + n_hard,
        "n_holdout_removed_val": n_val + n_val_injected,
        "holdout_manifests": [dict(item) for item in spec.manifests],
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


def _enter_training_execution() -> None:
    """Reached only after admission. Admission-only mode returns before this."""
    return None


def run_loop(
    trunk: Path,
    out_dir: Path,
    *,
    include_live: bool = False,
    live_store: Path | None = None,
) -> dict:
    # Same gates as preflight. Admission-only returns before any optimizer.
    admission = admit_training_run(
        include_live=include_live,
        live_store=live_store,
        export_dataset=export_dataset,
        trunk=trunk,
        out_dir=out_dir,
    )
    if os.environ.get("HLX_ADMISSION_ONLY") == "1":
        if not admission.ready:
            raise AdmissionError(admission.error or "ADMISSION FAIL", admission.receipt)
        return admission.receipt
    bundle = admission.bundle
    holdout_spec = admission.holdout_spec
    input_receipt = train_input_receipt(bundle)
    disjoint_receipt = admission.disjoint_receipt
    reserve_receipt = admission.reserve_receipt
    if bundle is None:
        raise AdmissionError("ADMISSION FAIL: training bundle was not loaded", admission.receipt)
    root = repo_root()
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
    classify_tr, classify_va, classify_split_receipt = apply_classify_split_file(
        classify_tr, classify_va
    )
    unbind_tr, unbind_va, unbind_recipe = prepare_unbind_splits(bundle["rows"])
    from .classify_admission import apply_classify_admission

    classify_tr, classify_va, classify_admission_receipt = apply_classify_admission(
        bundle["rows"], classify_tr, classify_va
    )
    classify_tr, n_classify_train = filter_holdout_rows(classify_tr, holdout_spec)
    classify_va, n_classify_val = filter_holdout_rows(classify_va, holdout_spec)
    assert_no_holdout(classify_tr, holdout_spec, "classify train")
    assert_no_holdout(classify_va, holdout_spec, "classify val")
    assert_no_holdout(unbind_tr, holdout_spec, "unbind train")
    assert_no_holdout(unbind_va, holdout_spec, "unbind val")
    holdout_removed = {
        "classify_train": n_classify_train,
        "classify_val": n_classify_val,
        "unbind_train": unbind_recipe.get("n_holdout_removed_train", 0),
        "unbind_val": unbind_recipe.get("n_unbind_val_after_force_train", 0) and 0 or unbind_recipe.get("n_holdout_removed_val", 0),
    }
    log_holdout(holdout_spec, holdout_removed)
    if len(classify_tr) < 8:
        raise RuntimeError("not enough classify train rows")
