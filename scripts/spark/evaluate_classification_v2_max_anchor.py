"""Validation-only max-anchor family scorer comparison.

Compares residual, max-anchor, and diagnostic fusion on the repaired encoder.
Does not train, does not score the evaluation reserve, and does not move BEST.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
EXPORT = Path("/home/morpheus/hlx-private/classification-v2-surface-20260929/civilian.v0.3.jsonl")
EXPORT_SHA = "c4677011ea61f135c8fb82bed9d973dffe3a5db582d34421403e71498c5fd243"
BOUNDARIES = Path(
    "/home/morpheus/hlx-private/classification-v2-boundaries-20260930/FAMILY_SEMANTIC_BOUNDARIES.json"
)
BOUNDARY_SHA = "0ca6f34ce1abf68388e443371672ca36e16028079a175b6775e1968900e1c52f"
SEPARATION_SHA = "ab698d342d2d276f81d4baf3fed609bb6f8bf88cd6810bb1d1998c5e409f63c3"
REPAIR = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-classification-v2-geometry-repair"
)
REPAIR_SHA = "449bf3b303c95bc5d6b7d87173d50315616556c1379057414b970f3e5f0b18cf"
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
DESTINATION = Path(
    "/home/morpheus/hlx-private/classification-v2-max-anchor-20260930/MAX_ANCHOR_EVAL.json"
)
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"

sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def inner() -> int:
    import torch
    from safetensors.torch import load_file
    from transformers import AutoModel, AutoTokenizer

    from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY
    from hyperlexical.classification_v2_max_anchor import (
        artifact_sha256,
        decide_max_anchor,
        fusion_scores,
        load_sealed_anchors,
        max_anchor_scores,
        predict_family,
        residual_scores,
        score_report,
        scorer_contract,
    )
    from hyperlexical.classification_v2_surface import surface_form
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.layout import HIDDEN, MAX_LEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors
    from hyperlexical.training_routing import route_rows

    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if sha256_file(REPAIR / "model.safetensors") != REPAIR_SHA:
        fail("geometry-repair checkpoint changed")
    if sha256_file(EXPORT) != EXPORT_SHA:
        fail("surface export changed")
    boundaries = json.loads(BOUNDARIES.read_text(encoding="utf-8"))
    if boundaries.get("boundary_sha256") != BOUNDARY_SHA:
        fail("boundary hash mismatch")
    if boundaries.get("separation_sha256") != SEPARATION_SHA:
        fail("separation hash mismatch")
    sealed = load_sealed_anchors(boundaries)
    names = list(ACTIVE_FAMILY_VOCABULARY)
    rows = [json.loads(line) for line in EXPORT.read_text(encoding="utf-8").splitlines() if line.strip()]
    validation = route_rows(rows)[0]["classify"]["val"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("max-anchor eval requires CUDA")
    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tokenizer.padding_side = "right"
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    freeze_encoder(encoder)
    warm = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    tensors = split_weight_tensors(load_file(str(REPAIR / "model.safetensors"), device="cpu"))
    if apply_encoder_trainable(encoder, warm["encoder"])["loaded"] != 48:
        fail("production overlay missed 48 tensors")
    if apply_encoder_trainable(encoder, tensors["encoder"])["loaded"] != 12:
        fail("repair overlay missed 12 tensors")
    residual = torch.nn.Linear(HIDDEN, len(names))
    family_blob = tensors["family_head"]
    if "residual.weight" in family_blob:
        with torch.no_grad():
            residual.weight.copy_(family_blob["residual.weight"])
            residual.bias.copy_(family_blob["residual.bias"])
    elif "weight" in family_blob:
        residual.load_state_dict({"weight": family_blob["weight"], "bias": family_blob["bias"]})
    else:
        fail(f"unexpected family_head keys: {sorted(family_blob)[:20]}")
    encoder.to(device).eval()
    residual.to(device).eval()
    for parameter in encoder.parameters():
        parameter.requires_grad = False
    for parameter in residual.parameters():
        parameter.requires_grad = False

    golds = []
    surfaces = []
    residual_preds = []
    anchor_preds = []
    fusion_preds = []
    residual_score_rows = []
    anchor_score_rows = []
    fusion_score_rows = []
    prohibited = {"held_out", "evaluation_reserve", "settlement", "measurement", "test"}
    with torch.no_grad():
        for row in validation:
            lineage = str(row.get("lineage") or "")
            if lineage not in ACTIVE_FAMILY_VOCABULARY:
                continue
            if (
                row.get("evaluation_reserve")
                or row.get("held_out")
                or row.get("split") == "test"
                or row.get("surface") in prohibited
            ):
                fail("evaluation_isolation")
            text = str(row.get("text") or "")
            encoded = tokenizer(
                text,
                truncation=True,
                max_length=MAX_LEN,
                padding=False,
                return_tensors="pt",
            )
            encoded = {key: value.to(device) for key, value in encoded.items()}
            pooled = encoder(**encoded).last_hidden_state[:, 0]
            logits = residual(pooled)[0].detach().cpu().tolist()
            representation = pooled[0].detach().cpu().tolist()
            residual_row = residual_scores(logits)
            anchor_row = max_anchor_scores(representation, sealed["anchors"])
            fusion_row = fusion_scores(anchor_row, residual_row)
            golds.append(lineage)
            surfaces.append(surface_form(text))
            residual_preds.append(predict_family(residual_row))
            anchor_preds.append(predict_family(anchor_row))
            fusion_preds.append(predict_family(fusion_row))
            residual_score_rows.append(residual_row)
            anchor_score_rows.append(anchor_row)
            fusion_score_rows.append(fusion_row)

    if not golds:
        fail("no validation family rows")
    residual_report = score_report(golds, residual_preds, residual_score_rows, surfaces=surfaces)
    max_anchor_report = score_report(golds, anchor_preds, anchor_score_rows, surfaces=surfaces)
    fusion_report = score_report(golds, fusion_preds, fusion_score_rows, surfaces=surfaces)
    decision = decide_max_anchor(max_anchor_report)
    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if sha256_file(REPAIR / "model.safetensors") != REPAIR_SHA:
        fail("geometry-repair checkpoint changed")
    artifact = {
        "anchor_ids": sealed["anchor_ids"],
        "best_sha256": BEST_SHA,
        "boundary_sha256": BOUNDARY_SHA,
        "contract": scorer_contract(),
        "decision": decision,
        "fusion": fusion_report,
        "jev": "OFF",
        "max_anchor": max_anchor_report,
        "moves_best": False,
        "n_anchors": sealed["n_anchors"],
        "n_family": len(golds),
        "repair_primary_sha256": REPAIR_SHA,
        "reserve_scored": False,
        "residual": residual_report,
        "schema": "hyperlex.classification.v2.max_anchor_eval.v1",
        "separation_sha256": SEPARATION_SHA,
        "surface": "validation",
        "surfaces_present": sorted(set(surfaces)),
        "train": False,
    }
    artifact["artifact_sha256"] = artifact_sha256(artifact)
    DESTINATION.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    DESTINATION.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(DESTINATION, 0o644)
    print(
        json.dumps(
            {
                "artifact_sha256": artifact["artifact_sha256"],
                "decision": decision,
                "fusion_macro_f1": fusion_report["active_family_macro_f1"],
                "max_anchor_breadth": max_anchor_report["breadth"],
                "max_anchor_macro_f1": max_anchor_report["active_family_macro_f1"],
                "max_anchor_surfaces": max_anchor_report["macro_f1_by_surface"],
                "n_family": len(golds),
                "residual_macro_f1": residual_report["active_family_macro_f1"],
                "wrote": str(DESTINATION),
            },
            sort_keys=True,
        )
    )
    return 0


def outer() -> int:
    if DESTINATION.exists():
        fail(f"max-anchor eval already exists: {DESTINATION}")
    command = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "--name",
        "hlx-v2-max-anchor-eval",
        "-v",
        "/home/morpheus/Hyperlex:/home/morpheus/Hyperlex",
        "-v",
        "/home/morpheus/hlx-private:/home/morpheus/hlx-private",
        "-v",
        "/home/morpheus/.hyperlex:/home/morpheus/.hyperlex",
        "-w",
        "/home/morpheus/Hyperlex",
        "-e",
        "HOME=/home/morpheus",
        "-e",
        "HF_HUB_OFFLINE=1",
        "-e",
        "TRANSFORMERS_OFFLINE=1",
        "-e",
        "PYTHONUNBUFFERED=1",
        "-e",
        "HLX_MAX_ANCHOR_INNER=1",
        IMAGE,
        "python",
        "-u",
        "scripts/spark/evaluate_classification_v2_max_anchor.py",
    ]
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(inner() if os.environ.get("HLX_MAX_ANCHOR_INNER") == "1" else outer())
