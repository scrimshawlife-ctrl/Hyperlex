"""Score the frozen EVAL_RESERVE classify identities once.

Reads sealed text already stored beside those identities. Does not train,
does not write a checkpoint, does not move BEST, and does not change the ledger.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
EXPORT = Path("/home/morpheus/hlx-private/classification-v2-acquire-20260929/civilian.v0.1.jsonl")
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926/ledger.json")
BEST_WEIGHTS = Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/model.safetensors")
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
INIT_FROM = BEST_WEIGHTS
V2_WEIGHTS = Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-classification-v2/model.safetensors")
V2_SHA = "405107de9b9ca580fc578f47314d3a18490e598c56c988cfc5f8ac53409cecea"
CALIBRATION = Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-classification-v2/classification-v2-calibration.json")
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
PRIVATE = Path("/home/morpheus/hlx-private/classification-v2-train-20260929")
ROWS_PATH = PRIVATE / "reserve-eval-rows.jsonl"
RESULT_PATH = PRIVATE / "RESERVE_EVAL.json"
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
RAW_FILES = (
    Path("/home/morpheus/hlx-private/exp-20260929-select-006/reserve-acquisition-002/RAW_CANDIDATES.jsonl"),
    Path("/home/morpheus/hlx-private/exp-20260929-select-007/reserve-001/RAW_CANDIDATES.jsonl"),
    Path("/home/morpheus/hlx-private/exp-20260927-select-005/source-fetch-001/RAW_CANDIDATES.jsonl"),
)
HARVEST = Path("/home/morpheus/hlx-private/exp-20260927-select-005/harvest-002/RAW_HARVEST.jsonl")

sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def sudo_sha256(path: Path) -> str:
    completed = subprocess.run(
        ["sudo", "-n", "sha256sum", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.split()[0]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reserve_labels() -> dict[str, list[dict]]:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    found: dict[str, list[dict]] = {}
    for record in ledger["identities"]:
        if record.get("state") != "EVAL_RESERVE":
            continue
        labels = [label for label in (record.get("labels") or []) if label.get("task") == "classify"]
        if labels:
            found[record["normalized_text_sha256"]] = labels
    return found


def remember(store: dict[str, dict], text: str, source: str, reserve: dict[str, list[dict]]) -> None:
    from hyperlexical.holdout_guard import normalized_text_sha256

    digest = normalized_text_sha256(text)
    if digest not in reserve:
        return
    previous = store.get(digest)
    if previous is not None and previous["text"] != text:
        fail(f"two strings share one reserve identity: {digest}")
    if previous is None:
        store[digest] = {"text": text, "source": source, "normalized_text_sha256": digest}


def build_rows() -> list[dict]:
    from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY

    reserve = reserve_labels()
    if len(reserve) != 115:
        fail(f"classify EVAL_RESERVE count {len(reserve)} != 115")
    store: dict[str, dict] = {}
    for path in RAW_FILES:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                text = row.get("normalized_text")
                if isinstance(text, str) and text.strip():
                    remember(store, text, str(path), reserve)
    with HARVEST.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            text = row.get("text")
            if isinstance(text, str) and text.strip():
                remember(store, text, str(HARVEST), reserve)
    missing = sorted(set(reserve) - set(store))
    if missing:
        fail(f"reserve identities without stored text: {len(missing)}")
    train_hashes = set()
    with EXPORT.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            from hyperlexical.holdout_guard import normalized_text_sha256

            train_hashes.add(normalized_text_sha256(str(row.get("text") or "")))
    overlap = sorted(set(store) & train_hashes)
    if overlap:
        fail(f"reserve text also appears in the training export: {len(overlap)}")
    rows = []
    for digest in sorted(store):
        labels = reserve[digest]
        lineages = {label.get("lineage") for label in labels}
        classes = {label.get("class") for label in labels}
        if len(lineages) != 1 or len(classes) != 1:
            fail(f"reserve identity has conflicting labels: {digest}")
        lineage = next(iter(lineages))
        klass = next(iter(classes))
        if lineage != "none" and lineage not in ACTIVE_FAMILY_VOCABULARY:
            fail(f"reserve lineage is outside the active vocabulary: {lineage}")
        if klass not in {"OBSERVED", "INFERRED"}:
            fail(f"reserve class is not OBSERVED or INFERRED: {klass}")
        item = store[digest]
        rows.append(
            {
                "class": klass,
                "lineage": lineage,
                "normalized_text_sha256": digest,
                "source": item["source"],
                "text": item["text"],
            }
        )
    return rows


def _ece(probabilities: list[float], labels: list[int], bins: int = 10) -> float:
    if len(probabilities) != len(labels) or not probabilities:
        fail("ece inputs differ")
    total = 0.0
    for index in range(bins):
        low = index / bins
        high = (index + 1) / bins
        chosen = [
            (probability, label)
            for probability, label in zip(probabilities, labels)
            if (low <= probability < high) or (index == bins - 1 and probability == 1.0)
        ]
        if not chosen:
            continue
        mean_p = sum(probability for probability, _label in chosen) / len(chosen)
        mean_y = sum(label for _probability, label in chosen) / len(chosen)
        total += abs(mean_p - mean_y) * len(chosen) / len(probabilities)
    return total


def score_rows(rows: list[dict]) -> dict:
    import torch
    from safetensors.torch import load_file
    from torch import nn
    from transformers import AutoModel, AutoTokenizer

    from hyperlexical.classification_v2 import (
        ACTIVE_FAMILY_VOCABULARY,
        APPLICABILITY,
        APPLICABILITY_NONE,
        APPLICABILITY_PRESENT,
        V2_ABSTAIN,
        V2_FAMILY,
        V2_NONE,
        _softmax,
        build_result,
        prf_table,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.layout import HIDDEN, MAX_LEN
    from hyperlexical.save_pretrained import split_weight_tensors

    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    if calibration.get("surface") != "validation" or calibration.get("reserve_used") is not False:
        fail("calibration artifact is not the validation freeze")
    if file_sha256(V2_WEIGHTS) != V2_SHA:
        fail("v2 weights changed")
    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    init_split = split_weight_tensors(load_file(str(INIT_FROM), device="cpu"))
    v2_split = split_weight_tensors(load_file(str(V2_WEIGHTS), device="cpu"))
    init_applied = apply_encoder_trainable(encoder, init_split.get("encoder") or {})
    v2_applied = apply_encoder_trainable(encoder, v2_split.get("encoder") or {})
    if init_applied["loaded"] != 48 or v2_applied["loaded"] != 12:
        fail(f"encoder overlay {init_applied['loaded']}/{v2_applied['loaded']} != 48/12")
    applicability = nn.Linear(HIDDEN, 2)
    family = nn.Linear(HIDDEN, len(ACTIVE_FAMILY_VOCABULARY))
    applicability.load_state_dict(v2_split["applicability"])
    family.load_state_dict(v2_split["family_head"])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    encoder.to(device).eval()
    applicability.to(device).eval()
    family.to(device).eval()
    app_temperature = float(calibration["applicability_temperature"])
    app_threshold = float(calibration["applicability_threshold"])
    family_temperature = float(calibration["family_temperature"])
    emit_threshold = float(calibration["family_emit_threshold"])
    decisions = []
    app_gold: list[str] = []
    app_pred: list[str] = []
    fam_gold: list[str] = []
    fam_pred: list[str] = []
    observed_app_gold: list[str] = []
    observed_app_pred: list[str] = []
    inferred_app_gold: list[str] = []
    inferred_app_pred: list[str] = []
    observed_fam_gold: list[str] = []
    observed_fam_pred: list[str] = []
    probabilities: list[float] = []
    present_labels: list[int] = []
    with torch.no_grad():
        for start in range(0, len(rows), 8):
            chunk = rows[start : start + 8]
            encoded = tokenizer(
                [row["text"] for row in chunk],
                padding=True,
                truncation=True,
                max_length=MAX_LEN,
                return_tensors="pt",
            )
            encoded = {key: value.to(device) for key, value in encoded.items()}
            pooled = encoder(**encoded).last_hidden_state[:, 0]
            app_logits = applicability(pooled).detach().cpu()
            family_logits = family(pooled).detach().cpu()
            for row, app_logit, family_logit in zip(chunk, app_logits, family_logits):
                app_distribution = _softmax([float(value) for value in app_logit], app_temperature)
                family_distribution = _softmax(
                    [float(value) for value in family_logit],
                    family_temperature,
                )
                named = {
                    name: family_distribution[index]
                    for index, name in enumerate(ACTIVE_FAMILY_VOCABULARY)
                }
                result = build_result(
                    p_family_present=app_distribution[1],
                    applicability_threshold_value=app_threshold,
                    family_distribution=named,
                    family_emit_threshold_value=emit_threshold,
                    confidence=max(app_distribution),
                    provenance_context=row["class"],
                )
                if result["brier"] is not None or result["jev"]["invoked"] is not False:
                    fail("decision packet left the sealed nulls")
                decisions.append(
                    {
                        "ambiguous_candidate": result["ambiguous_candidate"],
                        "class": row["class"],
                        "decision": result["decision"],
                        "family": result["family"],
                        "lineage": row["lineage"],
                        "margin": result["margin"],
                        "normalized_text_sha256": row["normalized_text_sha256"],
                        "p_family_present": result["applicability_score"],
                        "stage": result["stage"],
                    }
                )
                gold_app = APPLICABILITY_NONE if row["lineage"] == "none" else APPLICABILITY_PRESENT
                app_gold.append(gold_app)
                app_pred.append(result["applicability"])
                probabilities.append(result["applicability_score"])
                present_labels.append(0 if gold_app == APPLICABILITY_NONE else 1)
                if row["class"] == "OBSERVED":
                    observed_app_gold.append(gold_app)
                    observed_app_pred.append(result["applicability"])
                else:
                    inferred_app_gold.append(gold_app)
                    inferred_app_pred.append(result["applicability"])
                if row["lineage"] in ACTIVE_FAMILY_VOCABULARY:
                    fam_gold.append(row["lineage"])
                    emitted = result["family"] if result["decision"] == V2_FAMILY else "ABSTAIN"
                    fam_pred.append(emitted)
                    if row["class"] == "OBSERVED":
                        observed_fam_gold.append(row["lineage"])
                        observed_fam_pred.append(emitted)
    n = len(decisions)
    abstained = sum(1 for row in decisions if row["decision"] == V2_ABSTAIN)
    none_decisions = sum(1 for row in decisions if row["decision"] == V2_NONE)
    emitted = [row for row in decisions if row["decision"] == V2_FAMILY]
    selective_hits = sum(1 for row in emitted if row["family"] == row["lineage"])
    family_table = prf_table(fam_gold, fam_pred, ACTIVE_FAMILY_VOCABULARY)
    observed_family = prf_table(observed_fam_gold, observed_fam_pred, ACTIVE_FAMILY_VOCABULARY)
    applicability = prf_table(app_gold, app_pred, APPLICABILITY)
    return {
        "schema": "hyperlex.classification.v2.reserve_eval.v1",
        "abstention_rate": abstained / n,
        "active_family_macro_f1": family_table["macro_f1"],
        "applicability_brier": sum(
            (probability - label) ** 2 for probability, label in zip(probabilities, present_labels)
        )
        / n,
        "applicability_ece_10": _ece(probabilities, present_labels),
        "applicability_macro_f1": applicability["macro_f1"],
        "applicability_per_label": applicability["per_label"],
        "calibration_checkpoint": calibration["checkpoint_identity"],
        "coverage": len(emitted) / n,
        "decisions": decisions,
        "encoder_overlay": {"production": init_applied["loaded"], "v2": v2_applied["loaded"]},
        "inferred_slice": prf_table(inferred_app_gold, inferred_app_pred, APPLICABILITY),
        "jev": "OFF",
        "n": n,
        "none_decision_rate": none_decisions / n,
        "observed_active_family_macro_f1": observed_family["macro_f1"],
        "observed_slice": prf_table(observed_app_gold, observed_app_pred, APPLICABILITY),
        "packet_brier": None,
        "per_family": family_table["per_label"],
        "predicted_none_rate": app_pred.count(APPLICABILITY_NONE) / n,
        "reserve_identities_scored": n,
        "reserve_text_missing": 0,
        "rows_used_for_training": False,
        "rows_used_for_calibration": False,
        "selective_accuracy": None if not emitted else selective_hits / len(emitted),
        "selective_emitted": len(emitted),
        "surface": "EVAL_RESERVE",
        "unbind_clean_exact": None,
        "weights_sha256": V2_SHA,
    }


def docker_score() -> int:
    command = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "--name",
        "hlx-classification-v2-reserve-eval",
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
        "PYTHONDONTWRITEBYTECODE=1",
        "-e",
        "PYTHONPATH=/home/morpheus/Hyperlex/scripts/shadow",
        "-e",
        "HLX_V2_RESERVE_SCORE=1",
        IMAGE,
        "python",
        "-u",
        "scripts/spark/run_classification_v2_reserve_eval.py",
    ]
    log_path = PRIVATE / "reserve-eval.log"
    with log_path.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, check=False)
    return completed.returncode


def main() -> int:
    if os.environ.get("HLX_V2_RESERVE_SCORE") == "1":
        rows = [json.loads(line) for line in ROWS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
        payload = score_rows(rows)
        RESULT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(RESULT_PATH, 0o600)
        summary = {key: payload[key] for key in payload if key != "decisions"}
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST changed before scoring")
    rows = build_rows()
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    ROWS_PATH.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    os.chmod(ROWS_PATH, 0o600)
    code = docker_score()
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST changed during scoring")
    if sudo_sha256(V2_WEIGHTS) != V2_SHA:
        fail("v2 weights changed during scoring")
    if code != 0:
        fail(f"reserve scoring exit {code}")
    print(json.dumps({"reserve_eval": str(RESULT_PATH), "rows": len(rows)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
