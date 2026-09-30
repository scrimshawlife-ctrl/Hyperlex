"""Wire Stage B retrieval behind Stage A and validate end-to-end.

Uses the sealed Stage A checkpoint and frozen Stage A thresholds. Builds a
fresh exemplar index from v3 surface train POSITIVE_EVIDENCE. Calibrates Stage B
floors on validation. Does not create a reserve, does not score the spent v2
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
SURFACE = Path("/home/morpheus/hlx-private/classification-v3-evidence-surface-20260930")
SURFACE_DATASET = SURFACE / "EVIDENCE_SURFACE.jsonl"
SURFACE_DATASET_SHA = "7339c044596a4cc2eb5ae17f3fbab185fface9abffb6151bdb0db69eca0d2d3a"
STAGE_A_DIR = Path(
    "/home/morpheus/.hyperlex/models/"
    "hyperlex-encoder-modernbert-base-seed-classification-v3-stage-a"
)
STAGE_A_WEIGHTS = STAGE_A_DIR / "model.safetensors"
STAGE_A_WEIGHTS_SHA = "0b7dbdac1f39e7b7ede1e51e86b9b938aa68e95692bf4b2f062329d487420ce7"
STAGE_A_CAL = STAGE_A_DIR / "stage_a_calibration.json"
PRIVATE = Path("/home/morpheus/hlx-private/classification-v3-stage-b-20260930")
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
DEST = PRIVATE / "STAGE_B_VALIDATION.json"
INDEX_DEST = PRIVATE / "STAGE_B_INDEX.json"

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


def write_private(path: Path, payload: dict | str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def pin_inputs() -> dict:
    if sha256_file(SURFACE_DATASET) != SURFACE_DATASET_SHA:
        fail("evidence surface dataset digest mismatch")
    if sudo_sha256(STAGE_A_WEIGHTS) != STAGE_A_WEIGHTS_SHA:
        fail("Stage A checkpoint digest mismatch")
    cal = json.loads(STAGE_A_CAL.read_text(encoding="utf-8"))
    if float(cal["none_threshold"]) != 0.05 or float(cal["present_threshold"]) != 0.55:
        fail("Stage A thresholds drifted")
    if cal.get("reserve_used") is not False:
        fail("Stage A calibration used reserve")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    try:
        best_ok = BEST_LINK.is_symlink() and BEST_LINK.resolve() == INIT_FROM.resolve()
    except PermissionError:
        target = subprocess.run(
            ["sudo", "-n", "readlink", "-f", str(BEST_LINK)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        best_ok = Path(target) == INIT_FROM.resolve()
    if not best_ok:
        fail("BEST symlink is not the production checkpoint")
    return {"stage_a_calibration": cal}


def load_surface() -> tuple[list[dict], list[dict]]:
    rows = [
        json.loads(line)
        for line in SURFACE_DATASET.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    train = [row for row in rows if row.get("split") == "train"]
    val = [row for row in rows if row.get("split") == "validation"]
    return train, val


def inner() -> int:
    import torch
    from torch import nn
    from transformers import AutoModel, AutoTokenizer
    from safetensors.torch import load_file

    from hyperlexical.classification_v3_evidence_gate import EVIDENCE_LABELS, decide_evidence
    from hyperlexical.classification_v3_stage_a import (
        evidence_score_from_probabilities,
        softmax_logits,
    )
    from hyperlexical.classification_v3_stage_b import (
        FROZEN_STAGE_A_THRESHOLDS,
        assemble_stage_b_receipt,
        build_stage_b_index,
        calibrate_stage_b_thresholds,
        evaluate_end_to_end,
        gold_end_to_end,
        is_index_positive_row,
        next_action_for_stage_b,
        reserve_authorization,
        retrieval_candidates_from_embedding,
        stage_b_contract,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.holdout_guard import normalized_text_sha256
    from hyperlexical.layout import HIDDEN, MAX_LEN
    from hyperlexical.save_pretrained import split_weight_tensors

    pin_inputs()
    train_rows, val_rows = load_surface()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("Stage B validation requires CUDA")

    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tokenizer.padding_side = "right"
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    # Warm from BEST then overlay Stage A trainable encoder tensors.
    best_split = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    stage_a_split = split_weight_tensors(load_file(str(STAGE_A_WEIGHTS), device="cpu"))
    if apply_encoder_trainable(encoder, best_split.get("encoder") or {})["loaded"] != 48:
        fail("BEST encoder overlay missed tensors")
    loaded_a = apply_encoder_trainable(encoder, stage_a_split.get("encoder") or {})
    if loaded_a["loaded"] != 12:
        fail(f"Stage A encoder overlay missed tensors: {loaded_a['loaded']}")
    evidence_head = nn.Linear(HIDDEN, len(EVIDENCE_LABELS))
    evidence_state = stage_a_split.get("evidence_head") or {}
    if "weight" not in evidence_state:
        fail("Stage A evidence_head missing")
    evidence_head.load_state_dict(evidence_state)
    encoder.to(device).eval()
    evidence_head.to(device).eval()

    def embed_texts(texts: list[str]) -> list[list[float]]:
        vectors = []
        with torch.no_grad():
            for start in range(0, len(texts), 32):
                batch = texts[start : start + 32]
                encoded = tokenizer(
                    batch,
                    padding=True,
                    truncation=True,
                    max_length=MAX_LEN,
                    return_tensors="pt",
                )
                encoded = {key: value.to(device) for key, value in encoded.items()}
                pooled = encoder(**encoded).last_hidden_state[:, 0]
                pooled = torch.nn.functional.normalize(pooled, dim=-1)
                vectors.extend(pooled.detach().cpu().tolist())
        return vectors

    # Build index from train POSITIVE_EVIDENCE.
    index_rows = [row for row in train_rows if is_index_positive_row(row)]
    identity_text = {}
    for row in index_rows:
        identity = normalized_text_sha256(str(row["text"]))
        identity_text.setdefault(identity, str(row["text"]))
    identities = sorted(identity_text)
    vectors = embed_texts([identity_text[identity] for identity in identities])
    embeddings = {identity: vector for identity, vector in zip(identities, vectors)}
    index = build_stage_b_index(train_rows, embeddings)
    write_private(INDEX_DEST, index)

    none_t = float(FROZEN_STAGE_A_THRESHOLDS["none_threshold"])
    present_t = float(FROZEN_STAGE_A_THRESHOLDS["present_threshold"])
    score_rows = []
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
            logits = evidence_head(pooled)[0].detach().cpu().tolist()
            probs = softmax_logits(logits)
            score = evidence_score_from_probabilities(probs)
            evidence_decision = decide_evidence(
                score, none_threshold=none_t, present_threshold=present_t
            )
            hidden = torch.nn.functional.normalize(pooled, dim=-1)[0].detach().cpu().tolist()
            ranked = retrieval_candidates_from_embedding(hidden, index["records"])
            gold = gold_end_to_end(row)
            candidates = ranked["candidates"]
            top3 = candidates[2] if len(candidates) > 2 else None
            score_rows.append(
                {
                    "evidence_decision": evidence_decision,
                    "evidence_label": row["evidence_label"],
                    "evidence_score": score,
                    "evidence_subtype": row["evidence_subtype"],
                    "gold_decision_type": gold["decision_type"],
                    "gold_family": gold["family"],
                    "identity": row["identity"],
                    "top1_family": ranked["top1"]["family"],
                    "top1_score": ranked["top1"]["score"],
                    "top2_family": ranked["top2"]["family"],
                    "top2_score": ranked["top2"]["score"],
                    "top3_family": None if top3 is None else top3["family"],
                    "top3_score": None if top3 is None else top3["score"],
                }
            )

    calibration = calibrate_stage_b_thresholds(score_rows)
    if calibration.get("feasible"):
        metrics = evaluate_end_to_end(
            score_rows,
            family_score_min=float(calibration["minimum_family_score"]),
            family_margin_min=float(calibration["minimum_top1_top2_margin"]),
        )
    else:
        # Report unconstrained Stage B floors for diagnosis.
        fallback = calibration.get("fallback") or {}
        score_min = float(fallback.get("minimum_family_score") or 0.0)
        margin_min = float(fallback.get("minimum_top1_top2_margin") or 0.0)
        metrics = evaluate_end_to_end(
            score_rows,
            family_score_min=score_min,
            family_margin_min=margin_min,
        )
        metrics["calibration_feasible"] = False
    # Authority: Stage A false-entry from frozen thresholds.
    metrics["false_evidence_entry_rate_on_none"] = calibration[
        "false_evidence_entry_rate_on_none"
    ]
    metrics["primary_gate_pass"] = calibration["primary_gate_pass"]
    metrics["secondary_gate_pass"] = bool(
        metrics["primary_gate_pass"]
        and metrics.get("family_emission_precision") is not None
        and float(metrics["family_emission_precision"]) + 1e-12 >= 0.80
    )
    authorization = reserve_authorization(metrics)
    next_action = next_action_for_stage_b(authorization)
    receipt = assemble_stage_b_receipt(
        {
            "authorization": authorization,
            "best_sha256": BEST_SHA,
            "calibration": calibration,
            "index_sha256": index["index_sha256"],
            "metrics": metrics,
            "next_action": next_action,
        }
    )
    write_private(DEST, receipt)
    write_private(PRIVATE / "CALIBRATION.json", calibration)
    write_private(
        PRIVATE / "SUMMARY.json",
        {
            "authorization": authorization["decision"],
            "false_evidence_entry_rate_on_none": metrics[
                "false_evidence_entry_rate_on_none"
            ],
            "family_emission_precision": metrics.get("family_emission_precision"),
            "family_emission_coverage": metrics.get("family_emission_coverage"),
            "index_sha256": index["index_sha256"],
            "next_action": next_action,
            "primary_gate_pass": metrics["primary_gate_pass"],
            "receipt_sha256": receipt["receipt_sha256"],
            "secondary_gate_pass": metrics["secondary_gate_pass"],
            "selective_accuracy": metrics.get("selective_accuracy"),
            "thresholds": {
                "minimum_family_score": calibration.get("minimum_family_score"),
                "minimum_top1_top2_margin": calibration.get("minimum_top1_top2_margin"),
                "none_threshold": none_t,
                "present_threshold": present_t,
            },
        },
    )
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed during Stage B validation")
    if sudo_sha256(STAGE_A_WEIGHTS) != STAGE_A_WEIGHTS_SHA:
        fail("Stage A weights changed during Stage B validation")
    print(
        json.dumps(
            {
                "authorization": authorization["decision"],
                "destination": str(DEST),
                "false_evidence_entry_rate_on_none": metrics[
                    "false_evidence_entry_rate_on_none"
                ],
                "family_emission_precision": metrics.get("family_emission_precision"),
                "feasible": calibration.get("feasible"),
                "index_sha256": index["index_sha256"],
                "next_action": next_action,
                "primary_gate_pass": metrics["primary_gate_pass"],
                "receipt_sha256": receipt["receipt_sha256"],
                "secondary_gate_pass": metrics["secondary_gate_pass"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    if "--inner" in sys.argv:
        return inner()
    from hyperlexical.classification_v3_stage_b import stage_b_contract

    pinned = pin_inputs()
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    write_private(
        PRIVATE / "LAUNCH.json",
        {
            "authorization": "WIRE_STAGE_B_RETRIEVAL_ON_EVIDENCE_PRESENT_THEN_VALIDATE",
            "best_sha256": BEST_SHA,
            "contract": stage_b_contract(),
            "dataset_sha256": SURFACE_DATASET_SHA,
            "moves_best": False,
            "stage_a_checkpoint_sha256": STAGE_A_WEIGHTS_SHA,
            "stage_a_thresholds": {
                "none_threshold": pinned["stage_a_calibration"]["none_threshold"],
                "present_threshold": pinned["stage_a_calibration"]["present_threshold"],
            },
            "train": False,
            "v3_reserve": None,
        },
    )
    command = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "--name",
        "hlx-classification-v3-stage-b",
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
        str(REPO / "scripts/spark/run_classification_v3_stage_b_validation.py"),
        "--inner",
    ]
    log_path = PRIVATE / "stage_b_validation.log"
    print(json.dumps({"launching": str(DEST), "log": str(log_path)}), flush=True)
    with log_path.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, check=False)
    write_private(PRIVATE / "EXIT.json", {"code": completed.returncode})
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed during Stage B validation")
    if completed.returncode != 0:
        fail(f"Stage B validation exit {completed.returncode}; see {log_path}")
    artifact = json.loads(sudo_read_text(DEST))
    print(
        json.dumps(
            {
                "authorization": artifact["authorization"]["decision"],
                "destination": str(DEST),
                "false_evidence_entry_rate_on_none": artifact["metrics"][
                    "false_evidence_entry_rate_on_none"
                ],
                "family_emission_precision": artifact["metrics"].get(
                    "family_emission_precision"
                ),
                "next_action": artifact["next_action"],
                "primary_gate_pass": artifact["metrics"]["primary_gate_pass"],
                "receipt_sha256": artifact["receipt_sha256"],
                "secondary_gate_pass": artifact["metrics"]["secondary_gate_pass"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
