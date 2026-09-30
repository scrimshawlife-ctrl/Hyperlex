"""Read-only family-geometry diagnostic on the validation split.

Compares prototype-only, residual-only, and fused predictions. Does not train,
does not score the evaluation reserve, and does not move BEST.
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
WITNESS = Path("/home/morpheus/hlx-private/classification-v2-geometry-20260930/PROTOTYPE_GEOMETRY.json")
OUT = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-classification-v2-surface"
)
PRIMARY_SHA = "e3c0545424e7fe9ca93a9b8c5e423698974f5cecab405ed99590c8293a5bb463"
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
DESTINATION = Path(
    "/home/morpheus/hlx-private/classification-v2-geometry-20260930/GEOMETRY_DIAGNOSTIC.json"
)
PRIOR_MACRO = 0.1960828268105939

sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sudo_sha256(path: Path) -> str:
    completed = subprocess.run(
        ["sudo", "-n", "sha256sum", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.split()[0]


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def _confusion(golds, preds, names):
    table = {gold: {pred: 0 for pred in names} for gold in names}
    for gold, pred in zip(golds, preds):
        if gold in table and pred in table[gold]:
            table[gold][pred] += 1
    return table


def inner() -> int:
    import torch
    from safetensors.torch import load_file
    from transformers import AutoModel, AutoTokenizer

    from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY, prf_table
    from hyperlexical.classification_v2_prototype import family_margin_report, fuse_family_logits
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.layout import HIDDEN, MAX_LEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors
    from hyperlexical.training_routing import route_rows

    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if sha256_file(OUT / "model.safetensors") != PRIMARY_SHA:
        fail("surface checkpoint changed")
    if sha256_file(EXPORT) != EXPORT_SHA:
        fail("surface export changed")
    witness = json.loads(WITNESS.read_text(encoding="utf-8"))
    names = list(ACTIVE_FAMILY_VOCABULARY)
    if [row["family"] for row in witness["rows"]] != names:
        fail("prototype order drifted")
    rows = [json.loads(line) for line in EXPORT.read_text(encoding="utf-8").splitlines() if line.strip()]
    validation = route_rows(rows)[0]["classify"]["val"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("diagnostic requires CUDA")
    tokenizer = AutoTokenizer.from_pretrained(TRUNK)
    tokenizer.padding_side = "right"
    encoder = AutoModel.from_pretrained(TRUNK)
    freeze_encoder(encoder)
    warm = split_weight_tensors(load_file(str(BEST_WEIGHTS)))
    tensors = split_weight_tensors(load_file(OUT / "model.safetensors"))
    if apply_encoder_trainable(encoder, warm["encoder"])["loaded"] != 48:
        fail("production overlay missed 48 tensors")
    if apply_encoder_trainable(encoder, tensors["encoder"])["loaded"] != 12:
        fail("surface overlay missed 12 tensors")
    residual = torch.nn.Linear(HIDDEN, len(names))
    residual.load_state_dict(tensors["family_head"])
    prototypes = torch.tensor(witness["weight"], dtype=residual.weight.dtype, device=device)
    encoder.to(device).eval()
    residual.to(device).eval()
    golds = []
    proto_pred = []
    residual_pred = []
    residual_norm_pred = []
    fused_pred = []
    margin_records = []
    prohibited = {"held_out", "evaluation_reserve", "settlement", "measurement"}
    with torch.no_grad():
        for row in validation:
            if row.get("split") != "val" or row.get("evaluation_reserve") or row.get("held_out"):
                fail("diagnostic refused a non-validation row")
            if row.get("surface") in prohibited:
                fail("diagnostic refused a reserved surface")
            lineage = row.get("lineage")
            if lineage not in names:
                continue
            encoded = tokenizer(
                [row["text"]],
                padding=True,
                truncation=True,
                max_length=MAX_LEN,
                return_tensors="pt",
            )
            encoded = {key: value.to(device) for key, value in encoded.items()}
            pooled = encoder(**encoded).last_hidden_state[:, 0]
            hidden = torch.nn.functional.normalize(pooled, dim=-1)
            anchors = torch.nn.functional.normalize(prototypes, dim=-1)
            cosine = (hidden @ anchors.T)[0].detach().cpu().tolist()
            raw = residual(pooled)[0].detach().cpu().tolist()
            learned = residual(hidden)[0].detach().cpu().tolist()
            fused = fuse_family_logits(cosine, learned)
            golds.append(lineage)
            proto_pred.append(names[max(range(len(cosine)), key=cosine.__getitem__)])
            residual_pred.append(names[max(range(len(raw)), key=raw.__getitem__)])
            residual_norm_pred.append(names[max(range(len(learned)), key=learned.__getitem__)])
            fused_pred.append(names[max(range(len(fused)), key=fused.__getitem__)])
            margin_records.append({"lineage": lineage, "similarities": cosine})
    if len(golds) < 2:
        fail("validation family rows missing")
    prototype_table = prf_table(golds, proto_pred, names)
    residual_table = prf_table(golds, residual_pred, names)
    fused_table = prf_table(golds, fused_pred, names)
    artifact = {
        "checkpoint_identity": PRIMARY_SHA,
        "confusion": {
            "fused": _confusion(golds, fused_pred, names),
            "prototype_only": _confusion(golds, proto_pred, names),
            "residual_only": _confusion(golds, residual_pred, names),
        },
        "confusion_clusters": witness.get("confusion_clusters"),
        "confusable_pairs": witness.get("confusable_pairs"),
        "fused_macro_f1": fused_table["macro_f1"],
        "fused_per_family": fused_table["per_label"],
        "geometry_sha256": witness.get("geometry_sha256"),
        "hard_negatives": witness.get("hard_negatives"),
        "moves_best": False,
        "n_family": len(golds),
        "prior_active_family_macro_f1": PRIOR_MACRO,
        "prototype_only_macro_f1": prototype_table["macro_f1"],
        "prototype_only_per_family": prototype_table["per_label"],
        "prototype_similarity_margin": family_margin_report(margin_records, names),
        "reserve_scored": False,
        "residual_normalized_macro_f1": prf_table(golds, residual_norm_pred, names)["macro_f1"],
        "residual_only_macro_f1": residual_table["macro_f1"],
        "residual_only_per_family": residual_table["per_label"],
        "schema": "hyperlex.classification.v2.family_geometry_diagnostic.v1",
        "surface": "validation",
        "training": False,
        "witness_sha256": witness.get("witness_sha256"),
    }
    DESTINATION.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(DESTINATION, 0o644)
    print(json.dumps({
        "fused_macro_f1": artifact["fused_macro_f1"],
        "n_family": artifact["n_family"],
        "prototype_only_macro_f1": artifact["prototype_only_macro_f1"],
        "residual_only_macro_f1": artifact["residual_only_macro_f1"],
        "wrote": str(DESTINATION),
    }, sort_keys=True))
    return 0


def main() -> int:
    if os.environ.get("HLX_GEOMETRY_DIAG_INNER") == "1":
        return inner()
    if not WITNESS.is_file():
        fail(f"missing geometry witness {WITNESS}")
    before_best = sudo_sha256(BEST_WEIGHTS)
    before_primary = sudo_sha256(OUT / "model.safetensors")
    command = [
        "docker", "run", "--rm", "--gpus", "all", "--name", "hlx-v2-geometry-diag",
        "-v", "/home/morpheus/Hyperlex:/home/morpheus/Hyperlex",
        "-v", "/home/morpheus/hlx-private:/home/morpheus/hlx-private",
        "-v", "/home/morpheus/.hyperlex:/home/morpheus/.hyperlex",
        "-w", "/home/morpheus/Hyperlex",
        "-e", "HOME=/home/morpheus",
        "-e", "HF_HUB_OFFLINE=1",
        "-e", "TRANSFORMERS_OFFLINE=1",
        "-e", "PYTHONPATH=/home/morpheus/Hyperlex/scripts/shadow",
        "-e", "PYTHONUNBUFFERED=1",
        "-e", "HLX_GEOMETRY_DIAG_INNER=1",
        IMAGE,
        "python", "-u", "scripts/spark/diagnose_classification_v2_family_geometry.py",
    ]
    completed = subprocess.run(command, check=False)
    if sudo_sha256(BEST_WEIGHTS) != before_best or sudo_sha256(OUT / "model.safetensors") != before_primary:
        fail("weights changed during the diagnostic")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
