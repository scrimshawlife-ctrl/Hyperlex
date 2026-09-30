"""Seal HYPERLEX_FAMILY_RETRIEVAL_DECISION_V1 on the forward-hub representation.

Builds the training-side embedding index, calibrates two global thresholds on
validation, and evaluates calibrated emission. Does not train, does not score
the evaluation reserve, and does not move BEST.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
PRIVATE = Path("/home/morpheus/hlx-private/classification-v2-family-retrieval-20260930")
EXPORT = Path(
    "/home/morpheus/hlx-private/classification-v2-train-forward-20260930/civilian.v0.7.hub.jsonl"
)
EXPORT_SHA = "0d8f4532f84ed9fade3fd4e69af0d1e0717fb1098d40754e95c0090d8282bfe1"
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
CALIBRATION = OUT / "classification-v2-calibration.json"
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
DEST = PRIVATE / "FAMILY_RETRIEVAL.json"
INDEX_DEST = PRIVATE / "FAMILY_RETRIEVAL_INDEX.json"

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
        fail("export digest mismatch")
    hub = json.loads(HUB.read_text(encoding="utf-8"))
    if hub.get("artifact_sha256") != HUB_SHA:
        fail("hub boundary digest mismatch")
    if sudo_sha256(WEIGHTS) != WEIGHTS_SHA:
        fail("forward-hub weights digest mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if not BEST_LINK.is_symlink() or BEST_LINK.resolve() != INIT_FROM.resolve():
        fail("BEST symlink is not the production checkpoint")
    calibration = json.loads(sudo_read_text(CALIBRATION))
    if calibration.get("surface") != "validation" or calibration.get("reserve_used") is not False:
        fail("applicability calibration is not the validation freeze")
    return {"applicability_calibration": calibration}


def _embed_texts(texts: list[str], encoder, tokenizer, device, max_len: int) -> list[list[float]]:
    import torch

    vectors: list[list[float]] = []
    with torch.no_grad():
        for start in range(0, len(texts), 16):
            chunk = texts[start : start + 16]
            encoded = tokenizer(
                chunk,
                padding=True,
                truncation=True,
                max_length=max_len,
                return_tensors="pt",
            )
            encoded = {key: value.to(device) for key, value in encoded.items()}
            pooled = encoder(**encoded).last_hidden_state[:, 0]
            pooled = torch.nn.functional.normalize(pooled, dim=-1)
            vectors.extend(pooled.detach().cpu().tolist())
    return vectors


def inner() -> int:
    import torch
    from safetensors.torch import load_file
    from torch import nn
    from transformers import AutoModel, AutoTokenizer

    from hyperlexical.classification_v2 import (
        ACTIVE_FAMILY_VOCABULARY,
        APPLICABILITY_NONE,
        APPLICABILITY_PRESENT,
        FORWARD_ONTOLOGY,
        V1_NONE_CLASS,
        _softmax,
    )
    from hyperlexical.classification_v2_family_retrieval import (
        RULE,
        assemble_family_retrieval_artifact,
        build_index_records,
        calibrate_thresholds,
        compare_residual,
        evaluate_retrieval_decisions,
        family_scores,
        is_admissible_index_row,
        next_action_for_gate,
        reserve_gate,
    )
    from hyperlexical.classification_v2_surface import (
        applicability_invariance,
        calibrated_present_probability,
        surface_form,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.holdout_guard import normalized_text_sha256
    from hyperlexical.layout import HIDDEN, MAX_LEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors

    if not FORWARD_ONTOLOGY:
        fail("HLX_V2_FORWARD_ONTOLOGY must be enabled")
    pinned = pin_inputs()
    names = list(ACTIVE_FAMILY_VOCABULARY)
    if len(names) != 18:
        fail("forward vocabulary width drift")

    rows = [
        json.loads(line)
        for line in EXPORT.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    train_rows = [row for row in rows if is_admissible_index_row(row)]
    val_rows = []
    for row in rows:
        if row.get("split") != "val":
            continue
        if row.get("task") not in {"classify", "classify+unbind"}:
            continue
        if row.get("evaluation_reserve") or row.get("held_out"):
            fail("validation row marked reserve/held_out")
        if row.get("surface") in {"held_out", "evaluation_reserve", "settlement", "measurement"}:
            fail("validation row on prohibited surface")
        lineage = row.get("lineage")
        if lineage not in names and lineage != V1_NONE_CLASS:
            continue
        val_rows.append(row)
    if len(train_rows) < 18 or len(val_rows) < 2:
        fail("insufficient train/val rows")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("family retrieval seal requires CUDA")
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
    applicability = nn.Linear(HIDDEN, 2)
    family_head = nn.Linear(HIDDEN, len(names))
    applicability.load_state_dict(tensors["applicability"])
    family_head.load_state_dict(tensors["family_head"])
    encoder.to(device).eval()
    applicability.to(device).eval()
    family_head.to(device).eval()

    # Deduplicate train identities in text order for embedding.
    train_identity_text: dict[str, str] = {}
    for row in train_rows:
        identity = normalized_text_sha256(str(row["text"]))
        train_identity_text.setdefault(identity, str(row["text"]))
    train_identities = sorted(train_identity_text)
    train_texts = [train_identity_text[identity] for identity in train_identities]
    train_vectors = _embed_texts(train_texts, encoder, tokenizer, device, MAX_LEN)
    embeddings_by_identity = {
        identity: vector for identity, vector in zip(train_identities, train_vectors)
    }
    index = build_index_records(train_rows, embeddings_by_identity)
    write_private(INDEX_DEST, index)

    cal = pinned["applicability_calibration"]
    app_temperature = float(cal["applicability_temperature"])
    app_threshold = float(cal["applicability_threshold"])

    score_rows = []
    residual_golds = []
    residual_preds = []
    invariance_records = []
    with torch.no_grad():
        for row in val_rows:
            text = str(row["text"])
            encoded = tokenizer(
                [text],
                padding=True,
                truncation=True,
                max_length=MAX_LEN,
                return_tensors="pt",
            )
            encoded = {key: value.to(device) for key, value in encoded.items()}
            pooled = encoder(**encoded).last_hidden_state[:, 0]
            hidden = torch.nn.functional.normalize(pooled, dim=-1)[0].detach().cpu().tolist()
            app_logits = [float(value) for value in applicability(pooled)[0].detach().cpu()]
            fam_logits = [float(value) for value in family_head(pooled)[0].detach().cpu()]
            app_distribution = _softmax(app_logits, app_temperature)
            p_present = float(app_distribution[1])
            applicability_label = (
                APPLICABILITY_PRESENT if p_present >= app_threshold else APPLICABILITY_NONE
            )
            ranked = family_scores(hidden, index["records"])
            gold = row.get("lineage")
            score_rows.append(
                {
                    "applicability": applicability_label,
                    "gold_lineage": gold,
                    "top1_family": ranked["top1"]["family"],
                    "top1_score": ranked["top1"]["score"],
                    "top2_family": ranked["top2"]["family"],
                    "top2_score": ranked["top2"]["score"],
                }
            )
            if gold in names:
                residual_golds.append(str(gold))
                residual_preds.append(names[max(range(len(fam_logits)), key=fam_logits.__getitem__)])
            invariance_records.append(
                {
                    "family_prediction": ranked["top1"]["family"],
                    "lineage": gold,
                    "prediction": applicability_label,
                    "probability": calibrated_present_probability(app_logits, app_temperature),
                    "text": text,
                    "surface": surface_form(text),
                }
            )

    calibration = calibrate_thresholds(score_rows)
    if calibration.get("feasible"):
        evaluation = evaluate_retrieval_decisions(
            score_rows,
            minimum_family_score=float(calibration["minimum_family_score"]),
            minimum_top1_top2_margin=float(calibration["minimum_top1_top2_margin"]),
        )
    else:
        # Still report unconstrained retrieval ranking quality with open thresholds.
        evaluation = evaluate_retrieval_decisions(
            score_rows,
            minimum_family_score=0.0,
            minimum_top1_top2_margin=0.0,
        )
        evaluation["calibration_feasible"] = False
    comparison = compare_residual(
        golds=residual_golds,
        residual_preds=residual_preds,
        retrieval_eval=evaluation,
    )
    invariance = applicability_invariance(invariance_records)
    gate = reserve_gate(
        family_emission_precision=evaluation.get("family_emission_precision")
        if calibration.get("feasible")
        else None,
        applicability_invariance_pass=bool(invariance.get("pass")),
    )
    if not calibration.get("feasible"):
        gate = {
            "decision": "RESERVE_EVAL_NOT_JUSTIFIED",
            "family_emission_precision": None,
            "applicability_invariance_pass": bool(invariance.get("pass")),
            "precision_ok": False,
            "remaining_failure": "calibration_infeasible_no_threshold_pair_met_precision_min",
        }
    next_action = next_action_for_gate(gate)
    artifact = assemble_family_retrieval_artifact(
        {
            "applicability_invariance": {
                "pass": bool(invariance.get("pass")),
                "guard_results": invariance.get("guard_results"),
                "none_surface_gap": invariance.get("none_surface_gap"),
                "residualized_length_correlation": (
                    (invariance.get("residualized_length_correlation") or {}).get("correlation")
                ),
            },
            "calibration": calibration,
            "comparison_with_residual": comparison,
            "evaluation": evaluation,
            "family_support": index["family_support"],
            "index_sha256": index["index_sha256"],
            "n_index_embeddings": index["n_embeddings"],
            "next_action": next_action,
            "reserve_gate": gate,
        }
    )
    artifact["pinned"] = {
        "applicability_threshold": app_threshold,
        "applicability_temperature": app_temperature,
        "best_sha256": BEST_SHA,
        "export_sha256": EXPORT_SHA,
        "hub_boundary_sha256": HUB_SHA,
        "rule": RULE,
        "weights_sha256": WEIGHTS_SHA,
    }
    from hyperlexical.classification_v2 import canonical_json, sha256_text

    bare = {key: value for key, value in artifact.items() if key != "artifact_sha256"}
    artifact["artifact_sha256"] = sha256_text(canonical_json(bare))
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed during seal")
    if sudo_sha256(WEIGHTS) != WEIGHTS_SHA:
        fail("forward-hub weights changed during seal")
    write_private(DEST, artifact)
    print(
        json.dumps(
            {
                "artifact_sha256": artifact["artifact_sha256"],
                "coverage": evaluation.get("coverage"),
                "destination": str(DEST),
                "family_emission_precision": evaluation.get("family_emission_precision")
                if calibration.get("feasible")
                else None,
                "index_sha256": index["index_sha256"],
                "n_index_embeddings": index["n_embeddings"],
                "reserve_gate": gate["decision"],
                "thresholds": artifact["thresholds"],
                "top1_accuracy": evaluation.get("top1_accuracy"),
                "top2_accuracy": evaluation.get("top2_accuracy"),
            },
            indent=2,
            sort_keys=True,
        )
    )
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
            "export_sha256": EXPORT_SHA,
            "hub_boundary_sha256": HUB_SHA,
            "moves_best": False,
            "reserve_scored": False,
            "train": False,
            "weights_sha256": WEIGHTS_SHA,
            "applicability_calibration_surface": pinned["applicability_calibration"].get("surface"),
        },
    )
    command = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "--name",
        "hlx-classification-v2-family-retrieval",
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
        str(REPO / "scripts/spark/run_classification_v2_family_retrieval.py"),
        "--inner",
    ]
    log_path = PRIVATE / "family_retrieval.log"
    print(json.dumps({"launching": str(DEST), "log": str(log_path)}), flush=True)
    with log_path.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, check=False)
    write_private(PRIVATE / "EXIT.json", {"code": completed.returncode})
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed during seal")
    if completed.returncode != 0:
        fail(f"family retrieval exit {completed.returncode}; see {log_path}")
    artifact = json.loads(sudo_read_text(DEST))
    print(
        json.dumps(
            {
                "artifact_sha256": artifact["artifact_sha256"],
                "coverage": artifact["evaluation"].get("coverage"),
                "destination": str(DEST),
                "family_emission_precision": artifact["evaluation"].get(
                    "family_emission_precision"
                ),
                "index_sha256": artifact["index_sha256"],
                "next_action": artifact["next_action"],
                "reserve_gate": artifact["reserve_gate"]["decision"],
                "thresholds": artifact["thresholds"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
