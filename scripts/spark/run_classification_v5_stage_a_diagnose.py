"""DIAGNOSE_V5_STAGE_A_SETTLED_FAIL — read-only Spark runner.

Scores the frozen SELECTED checkpoint on validation only. Does not train,
relabel, retune thresholds, use reserve, or move BEST.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
SURFACE = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-negative-evidence-surface-v1r7-20260930"
)
DATASET = SURFACE / "EVIDENCE_SURFACE.jsonl"
AUTH_DEST = Path("/home/morpheus/hlx-private/classification-v5-stage-a-train-20260930")
RUN_ROOT = AUTH_DEST / "classification-v5-stage-a-001"
SELECTED = RUN_ROOT / "selected" / "model.safetensors"
LABEL_PROVENANCE = AUTH_DEST / "LABEL_PROVENANCE.jsonl"
DIAG_DEST = AUTH_DEST / "diagnosis-settled-fail-20260930"
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
SELECTED_SHA = "3b1b574acceea183363b8cea41e1b7e4e13dc934bacc66deb4b3b8caeabc90a7"
DATASET_SHA = "a81ca68ad3310981c60d2500a83a0989adeb967cbee6ad6dff003ed2c705efa9"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"

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


def write_private(path: Path, payload: dict | str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    os.chmod(path, 0o600)


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def preflight() -> None:
    if sha256_file(DATASET) != DATASET_SHA:
        fail("dataset digest mismatch")
    if sha256_file(SELECTED) != SELECTED_SHA:
        fail("selected checkpoint digest mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST mutated")
    auth = json.loads((AUTH_DEST / "AUTHORIZATION.json").read_text(encoding="utf-8"))
    if auth.get("scientific_disposition") != "SETTLED_FAIL":
        fail(f"unexpected disposition:{auth.get('scientific_disposition')}")
    if auth.get("RESERVE_CONSUMED"):
        fail("reserve consumed")
    if DIAG_DEST.exists() and (DIAG_DEST / "DIAGNOSIS.json").exists():
        fail(f"diagnosis already sealed:{DIAG_DEST}")


def score_validation() -> dict:
    import torch
    from torch import nn
    from transformers import AutoModel, AutoTokenizer
    from safetensors.torch import load_file

    from hyperlexical.classification_v5_stage_a import (
        EVIDENCE_LABELS,
        TRAIN_HYPERPARAMS,
        evidence_score_from_probabilities,
        softmax_logits,
    )
    from hyperlexical.classification_v5_stage_a_diagnose import decide_diagnostic
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.layout import HIDDEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors

    rows = [r for r in load_jsonl(DATASET) if r.get("split") == "validation"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("diagnosis scoring requires CUDA")
    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tokenizer.padding_side = "right"
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    # SELECTED stores only last-2 trainable encoder tensors + head.
    # Reconstruct: trunk -> BEST overlay -> SELECTED overlay -> head.
    best_packed = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    best_loaded = apply_encoder_trainable(encoder, best_packed.get("encoder") or {})
    if best_loaded["loaded"] != 48:
        fail(f"BEST encoder overlay missed tensors: loaded={best_loaded['loaded']}")
    selected_packed = split_weight_tensors(load_file(str(SELECTED), device="cpu"))
    sel_loaded = apply_encoder_trainable(
        encoder, selected_packed.get("encoder") or {}
    )
    if sel_loaded["loaded"] < 1:
        fail("selected encoder overlay empty")
    freeze_encoder(encoder, last_trainable=0)
    head = nn.Linear(HIDDEN, len(EVIDENCE_LABELS))
    head_w = selected_packed.get("evidence_head") or {}
    if "weight" not in head_w or "bias" not in head_w:
        fail(f"evidence head missing in selected checkpoint: keys={list(head_w)}")
    with torch.no_grad():
        head.weight.copy_(head_w["weight"])
        head.bias.copy_(head_w["bias"])
    encoder.to(device)
    head.to(device)
    encoder.eval()
    head.eval()
    max_len = int(TRAIN_HYPERPARAMS["max_len"])
    embeddings = []
    probs = []
    decisions = []
    scores = []
    with torch.no_grad():
        for row in rows:
            encoded = tokenizer(
                [str(row["text"])],
                padding=True,
                truncation=True,
                max_length=max_len,
                return_tensors="pt",
            )
            encoded = {k: v.to(device) for k, v in encoded.items()}
            hidden = encoder(**encoded).last_hidden_state[:, 0]
            logits = head(hidden)[0].detach().cpu().tolist()
            prob = softmax_logits(logits)
            score = evidence_score_from_probabilities(prob)
            embeddings.append(hidden[0].detach().cpu().tolist())
            probs.append(prob)
            scores.append(score)
            decisions.append(decide_diagnostic(score))
    return {
        "rows": rows,
        "embeddings": embeddings,
        "probs": probs,
        "decisions": decisions,
        "scores": scores,
    }


def inner() -> int:
    from hyperlexical.classification_v5_stage_a_diagnose import (
        DIAGNOSE_RULE,
        attach_row_features,
        assemble_diagnosis,
    )

    preflight()
    scored = score_validation()
    provenance_rows = load_jsonl(LABEL_PROVENANCE)
    provenance_by_id = {str(r["identity"]): r for r in provenance_rows}
    surface_by_id = {str(r["identity"]): r for r in scored["rows"]}
    enriched = attach_row_features(
        scored["rows"],
        provenance_by_id=provenance_by_id,
        embeddings=scored["embeddings"],
        probs=scored["probs"],
        decisions=scored["decisions"],
    )
    revision = (
        os.environ.get("HLX_V5_STAGE_A_CODE_REVISION")
        or subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True
        ).strip()
    )
    diagnosis = assemble_diagnosis(
        enriched=enriched,
        surface_by_id=surface_by_id,
        code_revision=revision,
    )
    DIAG_DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(DIAG_DEST, 0o700)
    write_private(DIAG_DEST / "DIAGNOSIS.json", diagnosis)
    write_private(
        DIAG_DEST / "CONTROLLED_COMPARISON.json",
        diagnosis["controlled_comparison"],
    )
    write_private(DIAG_DEST / "ERROR_COHORTS.json", diagnosis["error_cohorts"])
    write_private(
        DIAG_DEST / "ORDINARY_DOMAIN_NONE_AUDIT.json",
        diagnosis["ordinary_domain_none_audit"],
    )
    write_private(
        DIAG_DEST / "LABEL_PROVENANCE_AUDIT.json",
        diagnosis["label_provenance_audit"],
    )
    write_private(
        DIAG_DEST / "SOURCE_DOMAIN_ERROR_TABLE.json",
        diagnosis["source_domain_error_table"],
    )
    write_private(
        DIAG_DEST / "REPRESENTATION_DIAGNOSTICS.json",
        diagnosis["representation_diagnostics"],
    )
    write_private(
        DIAG_DEST / "COUNTERFACTUAL_GATE_ACCOUNTING.json",
        diagnosis["counterfactual_gate_accounting"],
    )
    summary = {
        "EXPERIMENT_ID": diagnosis["EXPERIMENT_ID"],
        "NEXT_ACTION": "REMEDIATE_V5_STAGE_A_OBSERVED_ORDINARY_DOMAIN_NONE",
        "PRIMARY_DIAGNOSIS": diagnosis["decision"]["primary_diagnosis"],
        "RESERVE_CONSUMED": False,
        "BEST_MUTATED": False,
        "TRAIN": False,
        "architecture_change_justified": diagnosis["decision"][
            "architecture_change_justified"
        ],
        "controlled_interpretation": diagnosis["controlled_comparison"][
            "interpretation"
        ]["state"],
        "dataset_change_justified": diagnosis["decision"]["dataset_change_justified"],
        "diagnosis_rule": DIAGNOSE_RULE,
        "private_diag_dir": str(DIAG_DEST),
        "receipt_sha256": diagnosis["receipt_sha256"],
        "smallest_remediation": diagnosis["decision"]["smallest_remediation"],
    }
    # Refine next action from diagnosis.
    primary = diagnosis["decision"]["primary_diagnosis"]
    if primary == "DATA_LABEL_QUALITY_FAILURE":
        summary["NEXT_ACTION"] = "REMEDIATE_V5_STAGE_A_LABEL_QUALITY"
    elif primary == "SOURCE_DOMAIN_SHIFT_FAILURE":
        summary["NEXT_ACTION"] = "REMEDIATE_V5_STAGE_A_SOURCE_DOMAIN_SKEW"
    elif primary == "OBSERVED_ACQUISITION_FAILURE":
        summary["NEXT_ACTION"] = "REMEDIATE_V5_STAGE_A_OBSERVED_ACQUISITION"
    elif primary == "REPRESENTATION_FAILURE":
        summary["NEXT_ACTION"] = "REMEDIATE_V5_STAGE_A_REPRESENTATION"
    else:
        summary["NEXT_ACTION"] = "REMEDIATE_V5_STAGE_A_MIXED_FAILURE"
    write_private(DIAG_DEST / "SUMMARY.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def main() -> int:
    if os.environ.get("HLX_V5_STAGE_A_DIAGNOSE_INNER") == "1":
        return inner()
    preflight()
    cmd = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "-v",
        f"{REPO}:{REPO}",
        "-v",
        "/home/morpheus/hlx-private:/home/morpheus/hlx-private",
        "-v",
        "/home/morpheus/.hyperlex:/home/morpheus/.hyperlex",
        "-w",
        str(REPO),
        "-e",
        "PYTHONPATH=/home/morpheus/Hyperlex/scripts/shadow",
        "-e",
        "HLX_V2_FORWARD_ONTOLOGY=1",
        "-e",
        "HLX_V5_STAGE_A_DIAGNOSE_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={os.environ.get('HLX_V5_STAGE_A_CODE_REVISION', '')}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(REPO / "scripts/spark/run_classification_v5_stage_a_diagnose.py"),
    ]
    print(json.dumps({"launch": cmd[-1], "image": IMAGE}, sort_keys=True), flush=True)
    log_path = AUTH_DEST / "diagnose_console.log"
    with log_path.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(cmd, check=False, stdout=handle, stderr=subprocess.STDOUT)
    try:
        print(log_path.read_text(encoding="utf-8")[-12000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
