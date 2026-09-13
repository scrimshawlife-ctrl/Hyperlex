"""Explicit reviewed-dataset trainer. Does not open the legacy loop.

Consumes prepare_reviewed plans only. Preserves occurrence IDs, pinned
token_indices and train_only_vocabularies. Unknown held-out targets never
score as exact matches via unk-unk identity. Gold-span diagnostics stay
separate from surface extraction / bound-vector recovery. Legacy run_loop
still rejects role_scheme=reviewed_occurrences.

Provenance: Hyperlex Spec 007 WF-003 trainer integration on
264a0b35143a6920aaeb1872581550847b54fd12.
"""
from __future__ import annotations

import json
import os
import random
from pathlib import Path

from .training_contracts import digest

ALLOWED_PLAN_STATUS = "PREPARED_NOT_RUNNABLE"
REVIEWED_SCHEME = "reviewed_occurrences"


def _require_torch():
    try:
        import torch
        from torch import nn
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("torch required for reviewed trainer") from exc
    return torch, nn


def assert_plan_eligible(plan):
    if not isinstance(plan, dict):
        raise TypeError("plan must be a dict")
    if plan.get("status") != ALLOWED_PLAN_STATUS:
        raise ValueError("plan status is not PREPARED_NOT_RUNNABLE")
    if plan.get("blockers"):
        raise ValueError("plan still blocked")
    if plan.get("training_ready") is True or plan.get("name_gate") is True:
        raise ValueError("plan must not claim training_ready or name_gate")
    rows = plan.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("plan has no rows")
    for row in rows:
        masks = row.get("loss_masks") or {}
        if (masks.get("family") or masks.get("structure")) and row.get("role_scheme") != REVIEWED_SCHEME:
            raise ValueError("reviewed rows missing role_scheme=reviewed_occurrences")
    return plan


def select_split_rows(plan, split, head=None):
    assert_plan_eligible(plan)
    out = []
    for row in plan["rows"]:
        if row.get("split") != split:
            continue
        if head is not None and not (row.get("loss_masks") or {}).get(head):
            continue
        if head == "structure" and "aligned_occurrences" not in row:
            continue
        out.append(row)
    return out


def collate_reviewed_batch(rows, *, families, vocabularies):
    """Preserve occurrence IDs, known-masks and pinned token_indices."""
    if not rows:
        raise ValueError("empty batch")
    batch = {
        "example_ids": [],
        "texts": [],
        "family_target_ids": [],
        "family_loss_masks": [],
        "occurrence_ids": [],
        "token_indices": [],
        "role_target_ids": [],
        "filler_target_ids": [],
        "role_known": [],
        "filler_known": [],
        "structure_loss_masks": [],
        "gold_spans": [],
        "families": list(families),
        "vocabularies": {k: list(v) for k, v in vocabularies.items()},
    }
    for row in rows:
        batch["example_ids"].append(row["example_id"])
        batch["texts"].append(row["text"])
        fam_active = bool((row.get("loss_masks") or {}).get("family"))
        batch["family_loss_masks"].append(fam_active)
        batch["family_target_ids"].append(row["family_target_id"] if fam_active else -1)
        struct_active = bool((row.get("loss_masks") or {}).get("structure")) and "aligned_occurrences" in row
        batch["structure_loss_masks"].append(struct_active)
        if not struct_active:
            for key in (
                "occurrence_ids",
                "token_indices",
                "role_target_ids",
                "filler_target_ids",
                "role_known",
                "filler_known",
                "gold_spans",
            ):
                batch[key].append([])
            continue
        aligned = row["aligned_occurrences"]
        batch["occurrence_ids"].append([s["occurrence_id"] for s in aligned])
        batch["token_indices"].append([list(s["token_indices"]) for s in aligned])
        batch["role_target_ids"].append(list(row["target_ids"]["roles"]))
        batch["filler_target_ids"].append(list(row["target_ids"]["fillers"]))
        batch["role_known"].append(list(row["target_known"]["roles"]))
        batch["filler_known"].append(list(row["target_known"]["fillers"]))
        batch["gold_spans"].append(
            [
                {
                    "occurrence_id": s["occurrence_id"],
                    "start": s["start"],
                    "end": s["end"],
                    "text": s["text"],
                    "role": s["role"],
                    "token_indices": list(s["token_indices"]),
                }
                for s in aligned
            ]
        )
        for known, tid in zip(row["target_known"]["fillers"], row["target_ids"]["fillers"], strict=True):
            if known and not (0 < tid < len(vocabularies["fillers"])):
                raise ValueError("known filler id outside train-only vocabulary")
            if not known and tid != 0:
                raise ValueError("unknown filler must map to reserved unk id 0")
        for known, tid in zip(row["target_known"]["roles"], row["target_ids"]["roles"], strict=True):
            if known and not (0 < tid < len(vocabularies["roles"])):
                raise ValueError("known role id outside train-only vocabulary")
            if not known and tid != 0:
                raise ValueError("unknown role must map to reserved unk id 0")
    return batch


def structure_exact_match(pred_filler_ids, gold_filler_ids, known_mask):
    if len(pred_filler_ids) != len(gold_filler_ids) or len(gold_filler_ids) != len(known_mask):
        return False
    if not known_mask or not all(known_mask):
        return False
    return list(pred_filler_ids) == list(gold_filler_ids)


def gold_span_diagnostics(gold_spans, predicted_surface_spans):
    gold = {(s["occurrence_id"], s["start"], s["end"], s["text"]) for s in gold_spans}
    pred = {
        (s.get("occurrence_id"), s.get("start"), s.get("end"), s.get("text"))
        for s in predicted_surface_spans
    }
    return {
        "n_gold": len(gold),
        "n_pred": len(pred),
        "n_span_exact": len(gold & pred),
        "kind": "gold_span_diagnostic",
        "not": "bound_vector_recovery",
    }


def seed_everything(seed):
    if not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a non-negative int")
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    torch, _ = _require_torch()
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    return {"seed": seed, "python_hash_seed": os.environ["PYTHONHASHSEED"]}


def _rng_state(torch):
    state = {"python": random.getstate(), "torch": torch.get_rng_state()}
    if torch.cuda.is_available():
        state["cuda"] = torch.cuda.get_rng_state_all()
    return state


def _set_rng_state(torch, state):
    random.setstate(state["python"])
    torch.set_rng_state(state["torch"])
    if "cuda" in state and torch.cuda.is_available():
        torch.cuda.set_rng_state_all(state["cuda"])


def build_reviewed_model(n_families, n_roles, n_fillers, hidden=32):
    torch, nn = _require_torch()

    class ReviewedModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.embed = nn.Embedding(512, hidden, padding_idx=0)
            self.family = nn.Linear(hidden, n_families)
            self.role = nn.Linear(hidden, n_roles)
            self.filler = nn.Linear(hidden, n_fillers)

        def encode(self, token_id_seqs):
            outs = []
            for seq in token_id_seqs:
                if not seq:
                    outs.append(torch.zeros(hidden))
                    continue
                ids = torch.tensor(seq, dtype=torch.long)
                outs.append(self.embed(ids).mean(0))
            return torch.stack(outs, 0)

        def forward_family(self, pooled):
            return self.family(pooled)

        def forward_slot(self, pooled):
            return self.role(pooled), self.filler(pooled)

    return ReviewedModel()


def _hash_text_tokens(text, n_positions):
    tokens = [1]
    for ch in text[: max(0, n_positions - 2)]:
        tokens.append(2 + (ord(ch) % 500))
    tokens.append(1)
    while len(tokens) < n_positions:
        tokens.insert(-1, 0)
    return tokens[:n_positions]


def materialize_token_ids(row):
    if row.get("aligned_occurrences"):
        max_idx = max(max(s["token_indices"]) for s in row["aligned_occurrences"])
        n = max(max_idx + 1, 3)
    else:
        n = max(3, min(16, len(row["text"]) + 2))
    return _hash_text_tokens(row["text"], n)


def batch_step(model, batch, torch, nn, *, optimizer=None):
    model.train(optimizer is not None)
    token_seqs = []
    slot_meta = []
    for i, text in enumerate(batch["texts"]):
        indices = batch["token_indices"][i]
        need = 1 + (max((max(ix) for ix in indices), default=0))
        token_seqs.append(_hash_text_tokens(text, max(need + 1, 3)))
        for slot_i, tok_ix in enumerate(indices):
            slot_meta.append((i, slot_i, tok_ix))
    pooled_examples = model.encode(token_seqs)
    loss = pooled_examples.new_zeros(())
    n_terms = 0
    for i, active in enumerate(batch["family_loss_masks"]):
        if not active:
            continue
        logits = model.forward_family(pooled_examples[i : i + 1])
        target = torch.tensor([batch["family_target_ids"][i]], dtype=torch.long)
        loss = loss + nn.functional.cross_entropy(logits, target)
        n_terms += 1
    for ex_i, slot_i, tok_ix in slot_meta:
        if not batch["structure_loss_masks"][ex_i]:
            continue
        seq = torch.tensor(token_seqs[ex_i], dtype=torch.long)
        emb = model.embed(seq)
        h = emb[list(tok_ix)].mean(0, keepdim=True)
        role_logits, filler_logits = model.forward_slot(h)
        role_t = torch.tensor([batch["role_target_ids"][ex_i][slot_i]], dtype=torch.long)
        fill_t = torch.tensor([batch["filler_target_ids"][ex_i][slot_i]], dtype=torch.long)
        if batch["role_known"][ex_i][slot_i]:
            loss = loss + nn.functional.cross_entropy(role_logits, role_t)
            n_terms += 1
        if batch["filler_known"][ex_i][slot_i]:
            loss = loss + nn.functional.cross_entropy(filler_logits, fill_t)
            n_terms += 1
    if n_terms == 0:
        loss = pooled_examples.sum() * 0.0
    if optimizer is not None:
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    return float(loss.detach().item()), n_terms


def evaluate_reviewed(model, rows, plan, torch, nn):
    if not rows:
        return {
            "n_examples": 0,
            "family_exact": None,
            "structure_exact": None,
            "structure_exact_known_only": None,
            "gold_span_diagnostic": None,
            "split_source": "empty",
            "train_eval_fallback": False,
        }
    vocabularies = plan["train_only_vocabularies"]
    batch = collate_reviewed_batch(rows, families=plan["families"], vocabularies=vocabularies)
    model.eval()
    fam_correct = fam_total = 0
    struct_correct = struct_total = 0
    struct_known_correct = struct_known_total = 0
    span_diag = []
    with torch.no_grad():
        for i, row in enumerate(rows):
            toks = materialize_token_ids(row)
            pooled = model.encode([toks])
            if batch["family_loss_masks"][i]:
                pred = int(model.forward_family(pooled).argmax(-1).item())
                fam_total += 1
                fam_correct += int(pred == batch["family_target_ids"][i])
            if batch["structure_loss_masks"][i]:
                pred_fillers = []
                surface_preds = []
                for slot_i, tok_ix in enumerate(batch["token_indices"][i]):
                    seq = torch.tensor(toks, dtype=torch.long)
                    h = model.embed(seq)[list(tok_ix)].mean(0, keepdim=True)
                    _, filler_logits = model.forward_slot(h)
                    pred_id = int(filler_logits.argmax(-1).item())
                    pred_fillers.append(pred_id)
                    surface_preds.append(
                        {
                            "occurrence_id": batch["occurrence_ids"][i][slot_i],
                            "start": batch["gold_spans"][i][slot_i]["start"],
                            "end": batch["gold_spans"][i][slot_i]["end"],
                            "text": vocabularies["fillers"][pred_id]
                            if pred_id < len(vocabularies["fillers"])
                            else "<unk>",
                        }
                    )
                struct_total += 1
                hit = structure_exact_match(
                    pred_fillers, batch["filler_target_ids"][i], batch["filler_known"][i]
                )
                if hit:
                    struct_correct += 1
                if all(batch["filler_known"][i]):
                    struct_known_total += 1
                    struct_known_correct += int(hit)
                span_diag.append(gold_span_diagnostics(batch["gold_spans"][i], surface_preds))
    return {
        "n_examples": len(rows),
        "family_exact": (fam_correct / fam_total) if fam_total else None,
        "structure_exact": (struct_correct / struct_total) if struct_total else None,
        "structure_exact_known_only": (struct_known_correct / struct_known_total)
        if struct_known_total
        else None,
        "n_family": fam_total,
        "n_structure": struct_total,
        "gold_span_diagnostic": {
            "n_rows": len(span_diag),
            "n_span_exact_total": sum(d["n_span_exact"] for d in span_diag),
            "kind": "gold_span_diagnostic",
            "not": "bound_vector_recovery",
        },
        "split_source": "provided_rows",
        "train_eval_fallback": False,
    }


def write_consumption_receipt(path, receipt):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(receipt)
    payload["receipt_sha256"] = digest({k: v for k, v in payload.items() if k != "receipt_sha256"})
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return payload


def save_reviewed_checkpoint(path, *, model, optimizer, scheduler, step, seed, sampler_state, plan_digest, torch):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict() if optimizer is not None else None,
        "scheduler": scheduler.state_dict() if scheduler is not None else None,
        "step": step,
        "seed": seed,
        "sampler_state": sampler_state,
        "rng": _rng_state(torch),
        "plan_digest": plan_digest,
        "name_gate": False,
        "kind": "reviewed_trainer_checkpoint.v1",
    }
    torch.save(payload, path)
    return {"path": str(path), "step": step, "plan_digest": plan_digest}


def load_reviewed_checkpoint(path, *, model, optimizer=None, scheduler=None, torch=None):
    torch = torch or _require_torch()[0]
    payload = torch.load(Path(path), map_location="cpu", weights_only=False)
    if payload.get("kind") != "reviewed_trainer_checkpoint.v1":
        raise ValueError("not a reviewed trainer checkpoint")
    model.load_state_dict(payload["model"])
    if optimizer is not None and payload.get("optimizer") is not None:
        optimizer.load_state_dict(payload["optimizer"])
    if scheduler is not None and payload.get("scheduler") is not None:
        scheduler.load_state_dict(payload["scheduler"])
    _set_rng_state(torch, payload["rng"])
    return payload


def plan_content_digest(plan):
    return digest(
        {
            "dataset_sha256": plan["dataset_sha256"],
            "rows_sha256": plan["rows_sha256"],
            "tokenizer_revision": plan.get("tokenizer_revision"),
            "train_only_vocabularies": plan["train_only_vocabularies"],
        }
    )


def run_reviewed_train(
    plan,
    *,
    out_dir,
    seed=0,
    max_steps=20,
    batch_size=2,
    lr=1e-2,
    resume_from=None,
    eval_split="val",
    hidden=32,
    forbid_train_eval_fallback=True,
    scheduler_step_size=10,
):
    assert_plan_eligible(plan)
    torch, nn = _require_torch()
    out_dir = Path(out_dir)
    if resume_from is None and out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite existing out_dir: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    seed_meta = seed_everything(seed)
    train_rows = select_split_rows(plan, "train")
    if not train_rows:
        raise ValueError("no train rows")
    if eval_split == "train":
        raise ValueError("eval_split=train is forbidden")
    eval_rows = select_split_rows(plan, eval_split)
    if forbid_train_eval_fallback and not eval_rows:
        raise ValueError("eval split empty; refusing train-set evaluation fallback")

    model = build_reviewed_model(
        len(plan["families"]),
        len(plan["train_only_vocabularies"]["roles"]),
        len(plan["train_only_vocabularies"]["fillers"]),
        hidden=hidden,
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=scheduler_step_size, gamma=0.5)
    plan_digest = plan_content_digest(plan)
    step = 0
    order = list(range(len(train_rows)))
    random.shuffle(order)
    cursor = 0
    if resume_from is not None:
        loaded = load_reviewed_checkpoint(
            resume_from, model=model, optimizer=optimizer, scheduler=scheduler, torch=torch
        )
        if loaded["plan_digest"] != plan_digest:
            raise ValueError("checkpoint plan digest mismatch")
        if loaded["seed"] != seed:
            raise ValueError("checkpoint seed mismatch")
        step = int(loaded["step"])
        order = list(loaded["sampler_state"]["order"])
        cursor = int(loaded["sampler_state"]["cursor"])

    losses = []
    while step < max_steps:
        if cursor >= len(order):
            random.shuffle(order)
            cursor = 0
        take = order[cursor : cursor + batch_size]
        if not take:
            random.shuffle(order)
            cursor = 0
            continue
        cursor += len(take)
        batch_rows = [train_rows[i] for i in take]
        batch = collate_reviewed_batch(
            batch_rows,
            families=plan["families"],
            vocabularies=plan["train_only_vocabularies"],
        )
        loss, n_terms = batch_step(model, batch, torch, nn, optimizer=optimizer)
        scheduler.step()
        step += 1
        losses.append(
            {"step": step, "loss": loss, "n_terms": n_terms, "example_ids": batch["example_ids"]}
        )

    ckpt_path = out_dir / "checkpoint.pt"
    save_reviewed_checkpoint(
        ckpt_path,
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        step=step,
        seed=seed,
        sampler_state={"order": order, "cursor": cursor},
        plan_digest=plan_digest,
        torch=torch,
    )
    metrics = evaluate_reviewed(model, eval_rows, plan, torch, nn)
    receipt = write_consumption_receipt(
        out_dir / "consumption_receipt.json",
        {
            "kind": "reviewed_consumption_receipt.v1",
            "status": "RAN_REVIEWED_TRAINER",
            "name_gate": False,
            "training_ready_claim": False,
            "seed": seed_meta,
            "max_steps": max_steps,
            "steps_run": step,
            "batch_size": batch_size,
            "lr": lr,
            "plan_digest": plan_digest,
            "dataset_sha256": plan["dataset_sha256"],
            "rows_sha256": plan["rows_sha256"],
            "tokenizer_revision": plan.get("tokenizer_revision"),
            "n_train_rows_available": len(train_rows),
            "n_eval_rows": len(eval_rows),
            "eval_split": eval_split,
            "consumed_example_ids_last_batches": [x["example_ids"] for x in losses[-5:]],
            "losses": losses,
            "metrics": metrics,
            "checkpoint": str(ckpt_path),
            "legacy_loop_guard_preserved": True,
            "train_eval_fallback": False,
            "note": "Reviewed trainer path only. Does not authorize publication or BEST overwrite.",
        },
    )
    return {"model": model, "receipt": receipt, "checkpoint": str(ckpt_path), "metrics": metrics}


def compare_uninterrupted_vs_resumed(
    plan,
    *,
    out_root,
    seed=0,
    max_steps=8,
    interrupt_at=4,
    batch_size=1,
    scheduler_step_size=10,
):
    torch, _ = _require_torch()
    out_root = Path(out_root)
    full = run_reviewed_train(
        plan,
        out_dir=out_root / "full",
        seed=seed,
        max_steps=max_steps,
        batch_size=batch_size,
        scheduler_step_size=scheduler_step_size,
    )
    part = run_reviewed_train(
        plan,
        out_dir=out_root / "part1",
        seed=seed,
        max_steps=interrupt_at,
        batch_size=batch_size,
        scheduler_step_size=scheduler_step_size,
    )
    resumed = run_reviewed_train(
        plan,
        out_dir=out_root / "resume",
        seed=seed,
        max_steps=max_steps,
        batch_size=batch_size,
        resume_from=part["checkpoint"],
        scheduler_step_size=scheduler_step_size,
    )
    full_state = torch.load(full["checkpoint"], map_location="cpu", weights_only=False)["model"]
    resume_state = torch.load(resumed["checkpoint"], map_location="cpu", weights_only=False)["model"]
    equal = all(torch.equal(full_state[k], resume_state[k]) for k in full_state)
    return {
        "uninterrupted_checkpoint": full["checkpoint"],
        "resumed_checkpoint": resumed["checkpoint"],
        "weights_equal": equal,
        "full_metrics": full["metrics"],
        "resumed_metrics": resumed["metrics"],
    }
