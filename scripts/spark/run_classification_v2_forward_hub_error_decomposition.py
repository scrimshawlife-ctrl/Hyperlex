"""Seal HYPERLEX_FORWARD_HUB_ERROR_DECOMPOSITION_V1 on the forward-hub checkpoint.

Read-only validation scoring. Does not train, does not score the evaluation
reserve, and does not move BEST.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
PRIVATE = Path(
    "/home/morpheus/hlx-private/classification-v2-forward-hub-error-decomposition-20260930"
)
EXPORT = Path(
    "/home/morpheus/hlx-private/classification-v2-train-forward-20260930/civilian.v0.7.hub.jsonl"
)
EXPORT_SHA = "0d8f4532f84ed9fade3fd4e69af0d1e0717fb1098d40754e95c0090d8282bfe1"
WITNESS = Path(
    "/home/morpheus/hlx-private/classification-v2-train-forward-20260930/PROTOTYPE_WITNESS.json"
)
WITNESS_SHA = "acca1594b49aa624d0d4dc97f03c7ccc69176568dfde0bebb7fb81c5085ca294"
SETTLEMENT = Path(
    "/home/morpheus/hlx-private/classification-v2-train-forward-20260930/SETTLEMENT.json"
)
MERGE = Path(
    "/home/morpheus/hlx-private/classification-v2-ontology-merge-pair-20260930/"
    "ONTOLOGY_MERGE_PAIR.json"
)
MERGE_SHA = "c901badb70c0c72f1af20fe4dd0b64bcbdfad917568682e9abb2cc9321ad69d5"
HUB = Path(
    "/home/morpheus/hlx-private/classification-v2-residual-hub-boundary-20260930/"
    "RESIDUAL_HUB_BOUNDARY.json"
)
HUB_SHA = "96a0587c06fac352872e462445f2eaaf773e35a48ab4c987e267b479cab72a83"
OUT = Path(
    "/home/morpheus/.hyperlex/models/"
    "hyperlex-encoder-modernbert-base-seed-classification-v2-forward-hub"
)
WEIGHTS = OUT / "model.safetensors"
WEIGHTS_SHA = "adf5db93dfe258290be531f0a25035dfaae03873bd800fd929bee43b38c9f89c"
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
BEST_LINK = Path("/home/morpheus/.hyperlex/models/BEST")
INIT_FROM = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004"
)
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
DEST = PRIVATE / "FORWARD_HUB_ERROR_DECOMPOSITION.json"

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sudo_sha256(path: Path) -> str:
    try:
        return sha256_file(path)
    except PermissionError:
        pass
    completed = subprocess.run(
        ["sudo", "-n", "sha256sum", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.split()[0]


def sudo_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except PermissionError:
        completed = subprocess.run(
            ["sudo", "-n", "cat", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def write_private(path: Path, payload: dict) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def pin_inputs() -> dict:
    if sha256_file(EXPORT) != EXPORT_SHA:
        fail("forward-hub export digest mismatch")
    witness = json.loads(WITNESS.read_text(encoding="utf-8"))
    if witness.get("witness_sha256") != WITNESS_SHA:
        fail("prototype witness digest mismatch")
    merge = json.loads(MERGE.read_text(encoding="utf-8"))
    if merge.get("artifact_sha256") != MERGE_SHA:
        fail("merge pair digest mismatch")
    hub = json.loads(HUB.read_text(encoding="utf-8"))
    if hub.get("artifact_sha256") != HUB_SHA:
        fail("hub boundary digest mismatch")
    if sudo_sha256(WEIGHTS) != WEIGHTS_SHA:
        fail("forward-hub weights digest mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if not BEST_LINK.is_symlink() or BEST_LINK.resolve() != INIT_FROM.resolve():
        fail("BEST symlink is not the production checkpoint")
    settlement = json.loads(SETTLEMENT.read_text(encoding="utf-8"))
    validation = settlement.get("validation") or {}
    if abs(float(validation.get("active_family_macro_f1") or 0.0) - 0.18562993635457403) > 1e-9:
        fail("settlement AF drift")
    return {
        "export_sha256": EXPORT_SHA,
        "hub_boundary_sha256": HUB_SHA,
        "merge_pair_sha256": MERGE_SHA,
        "overlap_pairs": list(merge.get("overlap_post_pairs") or []),
        "settlement_active_family_macro_f1": validation.get("active_family_macro_f1"),
        "settlement_prototype_family_macro_f1": validation.get("prototype_family_macro_f1"),
        "weights_sha256": WEIGHTS_SHA,
        "witness": witness,
        "witness_sha256": WITNESS_SHA,
    }


def inner() -> int:
    import torch
    from safetensors.torch import load_file
    from torch import nn
    from transformers import AutoModel, AutoTokenizer

    from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY, FORWARD_ONTOLOGY
    from hyperlexical.classification_v2_forward_hub_error_decomposition import (
        RULE,
        score_validation_bundle_from_tensors,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.layout import HIDDEN, MAX_LEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors
    from hyperlexical.training_routing import route_rows

    if not FORWARD_ONTOLOGY:
        fail("HLX_V2_FORWARD_ONTOLOGY must be enabled")
    pinned = pin_inputs()
    names = list(ACTIVE_FAMILY_VOCABULARY)
    if len(names) != 18:
        fail("forward vocabulary width drift")
    witness = pinned["witness"]
    if [row["family"] for row in witness["rows"]] != names:
        fail("prototype witness family order drifted")
    initialization = {
        str(row["family"]): str(row.get("initialization_mode") or "")
        for row in witness["rows"]
    }
    rows = [
        json.loads(line)
        for line in EXPORT.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    routed = route_rows(rows)[0]["classify"]
    validation = routed["val"]
    train_rows = [
        row
        for row in routed["train"]
        if row.get("lineage") in names and not row.get("evaluation_reserve")
    ]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("error decomposition requires CUDA")
    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tokenizer.padding_side = "right"
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    freeze_encoder(encoder)
    warm = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    tensors = split_weight_tensors(load_file(str(WEIGHTS), device="cpu"))
    if apply_encoder_trainable(encoder, warm.get("encoder") or {})["loaded"] != 48:
        fail("production overlay missed 48 tensors")
    if apply_encoder_trainable(encoder, tensors.get("encoder") or {})["loaded"] != 12:
        fail("forward-hub overlay missed 12 tensors")
    family_head = nn.Linear(HIDDEN, len(names))
    family_head.load_state_dict(tensors["family_head"])
    prototypes = torch.tensor(witness["weight"], dtype=torch.float32, device=device)
    encoder.to(device).eval()
    family_head.to(device).eval()

    golds: list[str] = []
    texts: list[str] = []
    evidence_classes: list[str] = []
    residual_logits: list[list[float]] = []
    prototype_logits: list[list[float]] = []
    prohibited = {"held_out", "evaluation_reserve", "settlement", "measurement"}
    with torch.no_grad():
        for row in validation:
            if row.get("split") != "val" or row.get("evaluation_reserve") or row.get("held_out"):
                fail("refused a non-validation row")
            if row.get("surface") in prohibited:
                fail("refused a reserved surface")
            lineage = row.get("lineage")
            if lineage not in names:
                continue
            text = str(row.get("text") or "")
            encoded = tokenizer(
                [text],
                padding=True,
                truncation=True,
                max_length=MAX_LEN,
                return_tensors="pt",
            )
            encoded = {key: value.to(device) for key, value in encoded.items()}
            pooled = encoder(**encoded).last_hidden_state[:, 0]
            residual = family_head(pooled)[0].detach().cpu().tolist()
            hidden = torch.nn.functional.normalize(pooled, dim=-1)
            anchors = torch.nn.functional.normalize(prototypes, dim=-1)
            cosine = (hidden @ anchors.T)[0].detach().cpu().tolist()
            golds.append(str(lineage))
            texts.append(text)
            evidence_classes.append(str(row.get("class") or "UNKNOWN"))
            residual_logits.append([float(value) for value in residual])
            prototype_logits.append([float(value) for value in cosine])

    if len(golds) < 2:
        fail("validation family rows missing")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed during audit")
    if sudo_sha256(WEIGHTS) != WEIGHTS_SHA:
        fail("forward-hub weights changed during audit")

    artifact = score_validation_bundle_from_tensors(
        labels=names,
        residual_logits=residual_logits,
        prototype_logits=prototype_logits,
        golds=golds,
        texts=texts,
        evidence_classes=evidence_classes,
        initialization_by_family=initialization,
        overlap_pairs=pinned["overlap_pairs"],
        train_rows=train_rows,
    )
    if abs(float(artifact["active_family_macro_f1"]) - float(pinned["settlement_active_family_macro_f1"])) > 1e-6:
        fail(
            "recomputation AF drifted from settlement: "
            f"{artifact['active_family_macro_f1']} vs {pinned['settlement_active_family_macro_f1']}"
        )
    artifact["pinned"] = {
        "best_sha256": BEST_SHA,
        "export_sha256": EXPORT_SHA,
        "hub_boundary_sha256": HUB_SHA,
        "merge_pair_sha256": MERGE_SHA,
        "rule": RULE,
        "weights_sha256": WEIGHTS_SHA,
        "witness_sha256": WITNESS_SHA,
    }
    # Re-seal hash after pinned metadata.
    from hyperlexical.classification_v2 import canonical_json, sha256_text

    bare = {key: value for key, value in artifact.items() if key != "artifact_sha256"}
    artifact["artifact_sha256"] = sha256_text(canonical_json(bare))
    write_private(DEST, artifact)
    summary = {
        "active_family_macro_f1": artifact["active_family_macro_f1"],
        "artifact_sha256": artifact["artifact_sha256"],
        "confusion_matrix_sha256": artifact["confusion_matrix_sha256"],
        "decision": artifact["decision"],
        "destination": str(DEST),
        "macro_f1_excluding_exact_copy": artifact["macro_f1_excluding_exact_copy"],
        "n_family_rows": artifact["n_family_rows"],
        "next_action": artifact["next_action"],
        "prediction_hubs": [row["family"] for row in artifact["prediction_hubs"]],
        "prototype_family_macro_f1": artifact["prototype_family_macro_f1"],
        "reserve_scored": False,
        "social_evaluation_flag": artifact["social_evaluation"]["flag"],
        "train": False,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def main() -> int:
    if "--inner" in sys.argv:
        return inner()
    pinned = pin_inputs()
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    write_private(
        PRIVATE / "LAUNCH.json",
        {
            "best_sha256": BEST_SHA,
            "export_sha256": pinned["export_sha256"],
            "hub_boundary_sha256": pinned["hub_boundary_sha256"],
            "merge_pair_sha256": pinned["merge_pair_sha256"],
            "moves_best": False,
            "reserve_scored": False,
            "train": False,
            "weights_sha256": pinned["weights_sha256"],
            "witness_sha256": pinned["witness_sha256"],
        },
    )
    command = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "--name",
        "hlx-classification-v2-forward-hub-error-decomp",
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
        "HLX_V2_FORWARD_ONTOLOGY=1",
        "-e",
        "PYTHONDONTWRITEBYTECODE=1",
        "-e",
        "PYTHONPATH=/home/morpheus/Hyperlex/scripts/shadow",
        "-e",
        "PYTHONUNBUFFERED=1",
        "-e",
        "TRANSFORMERS_OFFLINE=1",
        IMAGE,
        "python3",
        "-u",
        str(REPO / "scripts/spark/run_classification_v2_forward_hub_error_decomposition.py"),
        "--inner",
    ]
    log_path = PRIVATE / "error_decomposition.log"
    print(json.dumps({"launching": str(DEST), "log": str(log_path)}), flush=True)
    with log_path.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, check=False)
    write_private(PRIVATE / "EXIT.json", {"code": completed.returncode})
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed during audit")
    if completed.returncode != 0:
        fail(f"error decomposition exit {completed.returncode}; see {log_path}")
    artifact = json.loads(sudo_read_text(DEST))
    print(
        json.dumps(
            {
                "active_family_macro_f1": artifact["active_family_macro_f1"],
                "artifact_sha256": artifact["artifact_sha256"],
                "confusion_matrix_sha256": artifact["confusion_matrix_sha256"],
                "decision": artifact["decision"],
                "destination": str(DEST),
                "next_action": artifact["next_action"],
                "prediction_hubs": [row["family"] for row in artifact["prediction_hubs"]],
                "reserve_scored": False,
                "social_evaluation_flag": artifact["social_evaluation"]["flag"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
