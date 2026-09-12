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
from .save_pretrained import collect_encoder_trainable, save_heads, write_skeleton
from .unbind_curriculum import (
    plan_unbind_curriculum,
    resolve_curriculum_schedule,
    select_unbind_for_epoch,
)
from .unbind_metrics import mapped_filler, mapped_pred, summarize_unbind_pairs
from .unbind_recipe import (
    resolve_unbind_inferred_weight,
    resolve_unbind_morph_margin,
    shape_unbind_train,
    unbind_row_sample_weight,
)
from .unbind_head_slot import (
    apply_head_slot_weight,
    resolve_unbind_head_slot_weight,
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
UNBIND_LOSS_WEIGHT_DEFAULT = 1.0
UNBIND_EVERY_N_DEFAULT = 1


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


def should_interleave_unbind(classify_batch_index: int, every_n: int) -> bool:
    """True after classify batch `index` (0-based) when every_n > 1."""
    if every_n <= 1:
        return False
    return (classify_batch_index + 1) % every_n == 0


def prepare_unbind_splits(rows: list) -> tuple[list, list, dict]:
    """Train recipe only. Val list is untouched (frozen lexical split)."""
    train = [r for r in rows if r.get("task") == "unbind" and r.get("split") == "train"]
    val = [r for r in rows if r.get("task") == "unbind" and r.get("split") == "val"]
    shaped, stats = shape_unbind_train(train)
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
    write_export(root / "specs" / "007-hyperlexical-model" / "exports", bundle)
    classify_tr = [r for r in bundle["rows"] if r["task"] == "classify" and r["split"] == "train"]
    classify_va = [r for r in bundle["rows"] if r["task"] == "classify" and r["split"] == "val"]
    unbind_tr, unbind_va, unbind_recipe = prepare_unbind_splits(bundle["rows"])
    if len(classify_tr) < 8:
        raise RuntimeError("not enough classify train rows")

    import torch
    from torch import nn
    from torch.optim import AdamW

    maps = label_maps(unbind_tr + unbind_va)
    tok, encoder = _require_local_model(trunk)
    hidden = int(getattr(encoder.config, "hidden_size", HIDDEN))
    if hidden != HIDDEN:
        raise RuntimeError(f"hidden {hidden} != {HIDDEN}")
    n_unfrozen, last_trainable_used = freeze_encoder(encoder)
    classify = nn.Linear(hidden, len(FAMILIES))
    role_head = nn.Linear(hidden, len(maps["role_vocab"]))
    filler_head = nn.Linear(hidden, len(maps["filler_vocab"]))
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
        return combine_unbind_train_terms(
            weighted_slots,
            aux_terms,
            primary=unbind_primary,
            aux_lambda=UNBIND_SLOT_CE_AUX_LAMBDA,
        )

    def step_unbind(row) -> None:
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
        losses.append(float(scaled.detach().cpu()))

    residual_dump_path = resolve_unbind_residual_dump_path()
    last_residual_records: list[dict] = []

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
            losses.append(float(loss.detach().cpu()))
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

    out_dir.mkdir(parents=True, exist_ok=True)
    layout = describe(maps)
    layout["last_trainable"] = last_trainable_used
    layout["aligner"] = "char_span + offset_mapping"
    encoder_state = collect_encoder_trainable(encoder)
    state = {
        "classify": classify.state_dict(),
        "role_head": role_head.state_dict(),
        "filler_head": filler_head.state_dict(),
        "encoder": encoder_state,
        "maps": {k: v for k, v in maps.items() if k not in {"family_of", "role_of", "filler_of"}},
        "layout": layout,
    }
    write_skeleton(out_dir, maps=maps)
    weight_file = save_heads(out_dir, state)
    last = epoch_metrics[-1] if epoch_metrics else {}
    residual_receipt: dict = {
        "unbind_residual_dump": "",
        "n_unbind_residual": 0,
        "unbind_residual_themes": {},
    }
    if residual_dump_path:
        residual_receipt = write_residual_dump(residual_dump_path, last_residual_records)
    receipt = {
        "schema": "hyperlex.hyperlexical.train_receipt.v0.1",
        "model_id": MODEL_ID_SEED,
        "trunk": TRUNK,
        "trunk_dir": str(trunk),
        "device": str(device),
        "cuda": bool(torch.cuda.is_available()),
        "epochs": epochs,
        "n_train_classify": len(classify_tr),
        "n_train_unbind": len(unbind_tr),
        "n_unfrozen_encoder": n_unfrozen,
        "n_encoder_tensors": len(encoder_state),
        "last_trainable": last_trainable_used,
        "unbind_loss_weight": unbind_loss_weight,
        "unbind_every_n": unbind_every_n,
        "unbind_primary": slot_ce_mode["unbind_primary"],
        "unbind_slot_ce_armed": slot_ce_mode["unbind_slot_ce_armed"],
        "unbind_slot_ce_aux_lambda": slot_ce_mode["unbind_slot_ce_aux_lambda"],
        "unbind_head_slot_weight": head_slot_weight,
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
        "n_unbind_hard_extra_copies": unbind_recipe.get("n_unbind_hard_extra_copies", 0),
        "unbind_residual_dump": residual_receipt.get("unbind_residual_dump", ""),
        "n_unbind_residual": residual_receipt.get("n_unbind_residual", 0),
        "unbind_residual_themes": residual_receipt.get("unbind_residual_themes", {}),
        "unbind_residual_by_scheme": residual_receipt.get("unbind_residual_by_scheme", {}),
        "unbind_residual_by_class": residual_receipt.get("unbind_residual_by_class", {}),
        "unbind_residual_summary": residual_receipt.get("unbind_residual_summary", ""),
        "last_loss": losses[-1] if losses else None,
        "val": last,
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
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return receipt
