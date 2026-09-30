"""Seal a fresh v3 reserve from AVAILABLE identities and score it once.

Frozen Stage A/B thresholds. Does not retune, does not reuse the spent v2
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
EXPORT = Path(
    "/home/morpheus/hlx-private/classification-v2-train-forward-20260930/civilian.v0.7.hub.jsonl"
)
EXPORT_SHA = "0d8f4532f84ed9fade3fd4e69af0d1e0717fb1098d40754e95c0090d8282bfe1"
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926/ledger.json")
SPENT_ROWS = Path(
    "/home/morpheus/hlx-private/classification-v2-train-ready-20260929/reserve-eval-rows.jsonl"
)
SPENT_ROWS_SHA = "8c5276442ce37cf99fff597653a28917b3b4dc69ac87ad01f815fa458416ed36"
STAGE_A_DIR = Path(
    "/home/morpheus/.hyperlex/models/"
    "hyperlex-encoder-modernbert-base-seed-classification-v3-stage-a"
)
STAGE_A_WEIGHTS = STAGE_A_DIR / "model.safetensors"
STAGE_A_WEIGHTS_SHA = "0b7dbdac1f39e7b7ede1e51e86b9b938aa68e95692bf4b2f062329d487420ce7"
STAGE_B_DIR = Path("/home/morpheus/hlx-private/classification-v3-stage-b-20260930")
STAGE_B_INDEX = STAGE_B_DIR / "STAGE_B_INDEX.json"
STAGE_B_INDEX_SHA = "42ae85f3ee4e7f13656d2415a2152b11d5c2b14811b20b9c6352a3bb85c40285"
STAGE_B_RECEIPT_SHA = "6e3228ace25e09701febb91848411cfd3abf75fdfac3bfc3c49e1df4c49d8462"
PRIVATE = Path("/home/morpheus/hlx-private/classification-v3-reserve-20260930")
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
DEST = PRIVATE / "RESERVE_EVAL.json"
ROWS_DEST = PRIVATE / "reserve-rows.jsonl"

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
        fail("evidence surface digest mismatch")
    if sha256_file(EXPORT) != EXPORT_SHA:
        fail("hub export digest mismatch")
    if sha256_file(SPENT_ROWS) != SPENT_ROWS_SHA:
        fail("spent v2 reserve rows digest mismatch")
    if sudo_sha256(STAGE_A_WEIGHTS) != STAGE_A_WEIGHTS_SHA:
        fail("Stage A checkpoint digest mismatch")
    index = json.loads(sudo_read_text(STAGE_B_INDEX))
    if index.get("index_sha256") != STAGE_B_INDEX_SHA:
        fail("Stage B index digest mismatch")
    stage_b = json.loads(sudo_read_text(STAGE_B_DIR / "STAGE_B_VALIDATION.json"))
    if stage_b.get("receipt_sha256") != STAGE_B_RECEIPT_SHA:
        fail("Stage B validation receipt digest mismatch")
    if stage_b.get("authorization", {}).get("decision") != "RESERVE_SEAL_AUTHORIZED":
        fail("Stage B did not authorize reserve seal")
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
    return {"index": index, "stage_b": stage_b}


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
        evaluate_end_to_end,
        retrieval_candidates_from_embedding,
    )
    from hyperlexical.classification_v3_reserve import (
        FROZEN_THRESHOLDS,
        assemble_reserve_eval_receipt,
        collect_available_reserve_rows,
        decide_v3_reserve_disposition,
        next_action_for_v3_disposition,
        seal_reserve_manifest,
        validate_reserve_disjointness,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.layout import HIDDEN, MAX_LEN
    from hyperlexical.save_pretrained import split_weight_tensors

    pinned = pin_inputs()
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    surface_ids = {
        json.loads(line)["identity"]
        for line in SURFACE_DATASET.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    spent_v2_ids = {
        json.loads(line)["normalized_text_sha256"]
        for line in SPENT_ROWS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    hub_rows = [
        json.loads(line)
        for line in EXPORT.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    collected = collect_available_reserve_rows(
        ledger=ledger,
        hub_rows=hub_rows,
        surface_ids=surface_ids,
        spent_v2_ids=spent_v2_ids,
    )
    index_ids = {
        str(record["source_identity"])
        for record in pinned["index"].get("records") or []
    }
    invalid = validate_reserve_disjointness(
        collected["rows"],
        surface_ids=surface_ids,
        spent_v2_ids=spent_v2_ids,
        index_ids=index_ids,
    )
    sealed = seal_reserve_manifest(collected["rows"])
    write_private(ROWS_DEST, sealed["body"])
    if sha256_file(ROWS_DEST) != sealed["manifest"]["rows_sha256"]:
        fail("reserve rows digest mismatch after write")
    write_private(PRIVATE / "RESERVE_MANIFEST.json", sealed["manifest"])

    if invalid:
        disposition = decide_v3_reserve_disposition(invalid_reasons=invalid, metrics={})
        next_action = next_action_for_v3_disposition(disposition)
        receipt = assemble_reserve_eval_receipt(
            {
                "disposition": disposition,
                "metrics": {"n": collected["n"], "invalid": True},
                "next_action": next_action,
                "reserve_manifest_sha256": sealed["manifest"]["manifest_sha256"],
                "reserve_rows_sha256": sealed["manifest"]["rows_sha256"],
                "validation_reference": {
                    "false_evidence_entry_rate_on_none": pinned["stage_b"]["metrics"][
                        "false_evidence_entry_rate_on_none"
                    ],
                    "family_emission_precision": pinned["stage_b"]["metrics"][
                        "family_emission_precision"
                    ],
                },
            }
        )
        write_private(DEST, receipt)
        print(json.dumps({"disposition": disposition, "receipt_sha256": receipt["receipt_sha256"]}, indent=2, sort_keys=True))
        return 0

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("v3 reserve eval requires CUDA")
    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tokenizer.padding_side = "right"
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    best_split = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    stage_a_split = split_weight_tensors(load_file(str(STAGE_A_WEIGHTS), device="cpu"))
    if apply_encoder_trainable(encoder, best_split.get("encoder") or {})["loaded"] != 48:
        fail("BEST encoder overlay missed tensors")
    if apply_encoder_trainable(encoder, stage_a_split.get("encoder") or {})["loaded"] != 12:
        fail("Stage A encoder overlay missed tensors")
    evidence_head = nn.Linear(HIDDEN, len(EVIDENCE_LABELS))
    evidence_head.load_state_dict(stage_a_split["evidence_head"])
    encoder.to(device).eval()
    evidence_head.to(device).eval()

    none_t = float(FROZEN_THRESHOLDS["none_threshold"])
    present_t = float(FROZEN_THRESHOLDS["present_threshold"])
    score_min = float(FROZEN_THRESHOLDS["minimum_family_score"])
    margin_min = float(FROZEN_THRESHOLDS["minimum_top1_top2_margin"])
    index_records = pinned["index"]["records"]

    score_rows = []
    with torch.no_grad():
        for row in collected["rows"]:
            encoded = tokenizer(
                [str(row["text"])],
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
            ranked = retrieval_candidates_from_embedding(hidden, index_records)
            candidates = ranked["candidates"]
            top3 = candidates[2] if len(candidates) > 2 else None
            score_rows.append(
                {
                    "evidence_decision": evidence_decision,
                    "evidence_label": row["evidence_label"],
                    "evidence_score": score,
                    "evidence_subtype": row["evidence_subtype"],
                    "gold_decision_type": row["gold_decision_type"],
                    "gold_family": row["gold_family"],
                    "identity": row["identity"],
                    "top1_family": ranked["top1"]["family"],
                    "top1_score": ranked["top1"]["score"],
                    "top2_family": ranked["top2"]["family"],
                    "top2_score": ranked["top2"]["score"],
                    "top3_family": None if top3 is None else top3["family"],
                    "top3_score": None if top3 is None else top3["score"],
                }
            )

    metrics = evaluate_end_to_end(
        score_rows, family_score_min=score_min, family_margin_min=margin_min
    )
    disposition = decide_v3_reserve_disposition(invalid_reasons=[], metrics=metrics)
    next_action = next_action_for_v3_disposition(disposition)
    receipt = assemble_reserve_eval_receipt(
        {
            "disposition": disposition,
            "metrics": metrics,
            "next_action": next_action,
            "reserve_manifest_sha256": sealed["manifest"]["manifest_sha256"],
            "reserve_rows_sha256": sealed["manifest"]["rows_sha256"],
            "validation_reference": {
                "false_evidence_entry_rate_on_none": pinned["stage_b"]["metrics"][
                    "false_evidence_entry_rate_on_none"
                ],
                "family_emission_precision": pinned["stage_b"]["metrics"][
                    "family_emission_precision"
                ],
            },
        }
    )
    write_private(DEST, receipt)
    write_private(
        PRIVATE / "SUMMARY.json",
        {
            "disposition": disposition["disposition"],
            "false_evidence_entry_rate_on_none": metrics[
                "false_evidence_entry_rate_on_none"
            ],
            "family_emission_precision": metrics.get("family_emission_precision"),
            "n": metrics["n"],
            "next_action": next_action,
            "primary_gate_pass": metrics["primary_gate_pass"],
            "receipt_sha256": receipt["receipt_sha256"],
            "reserve_rows_sha256": sealed["manifest"]["rows_sha256"],
            "secondary_gate_pass": metrics["secondary_gate_pass"],
            "selective_accuracy": metrics.get("selective_accuracy"),
        },
    )
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed during reserve eval")
    print(
        json.dumps(
            {
                "disposition": disposition["disposition"],
                "false_evidence_entry_rate_on_none": metrics[
                    "false_evidence_entry_rate_on_none"
                ],
                "family_emission_precision": metrics.get("family_emission_precision"),
                "n": metrics["n"],
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
    from hyperlexical.classification_v3_reserve import reserve_contract

    pinned = pin_inputs()
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    write_private(
        PRIVATE / "LAUNCH.json",
        {
            "authorization": "AUTHORIZE_SEAL_NEW_V3_RESERVE_THEN_ONE_SHOT_SCORE",
            "best_sha256": BEST_SHA,
            "contract": reserve_contract(),
            "moves_best": False,
            "recalibrate": False,
            "spent_v2_reserve_reuse": False,
            "stage_a_checkpoint_sha256": STAGE_A_WEIGHTS_SHA,
            "stage_b_index_sha256": STAGE_B_INDEX_SHA,
            "stage_b_receipt_sha256": STAGE_B_RECEIPT_SHA,
            "surface_dataset_sha256": SURFACE_DATASET_SHA,
            "train": False,
            "validation_family_emission_precision": pinned["stage_b"]["metrics"].get(
                "family_emission_precision"
            ),
        },
    )
    command = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "--name",
        "hlx-classification-v3-reserve",
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
        str(REPO / "scripts/spark/run_classification_v3_reserve_eval.py"),
        "--inner",
    ]
    log_path = PRIVATE / "reserve_eval.log"
    print(json.dumps({"launching": str(DEST), "log": str(log_path)}), flush=True)
    with log_path.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, check=False)
    write_private(PRIVATE / "EXIT.json", {"code": completed.returncode})
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed during reserve eval")
    if completed.returncode != 0:
        fail(f"reserve eval exit {completed.returncode}; see {log_path}")
    artifact = json.loads(sudo_read_text(DEST))
    print(
        json.dumps(
            {
                "disposition": artifact["disposition"]["disposition"],
                "false_evidence_entry_rate_on_none": artifact["metrics"].get(
                    "false_evidence_entry_rate_on_none"
                ),
                "family_emission_precision": artifact["metrics"].get(
                    "family_emission_precision"
                ),
                "n": artifact["metrics"].get("n"),
                "next_action": artifact["next_action"],
                "receipt_sha256": artifact["receipt_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
