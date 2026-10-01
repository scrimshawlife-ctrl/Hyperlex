"""PRESERVE_RESERVE_FAIL_AND_DIAGNOSE_V5_GENERALIZATION — Spark runner.

Read-only generalization diagnosis. Re-infers V1R9 validation + spent reserve
under frozen STAGE_A_BEST / Stage-B index for decomposition only. Does not
train, recalibrate, rebuild the index, or move BEST pointers.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

SURFACE = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-negative-evidence-surface-v1r9-20260930"
)
DATASET = SURFACE / "EVIDENCE_SURFACE.jsonl"
DATASET_SHA = "8d4be8301b89b191841342fe11ef647c838b32e56e6d133b610c232264c5d00a"
RESERVE_DIR = Path("/home/morpheus/hlx-private/classification-v5-reserve-20260930")
RESERVE_ROWS = RESERVE_DIR / "RESERVE.jsonl"
RESERVE_SEAL = RESERVE_DIR / "RESERVE_SEAL.json"
RESERVE_SCORE = RESERVE_DIR / "RESERVE_SCORE.json"
STAGE_B_INDEX = Path(
    "/home/morpheus/hlx-private/classification-v5-stage-b-20260930/STAGE_B_INDEX.json"
)
STAGE_B_INDEX_SHA = (
    "3fd6c87a5825f3f2a25a81f1a769a77aa69e03ddca5b370f9247672d93aaee21"
)
STAGE_B_VAL = Path(
    "/home/morpheus/hlx-private/classification-v5-stage-b-20260930/STAGE_B_VALIDATION.json"
)
STAGE_A_BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/STAGE_A_BEST/model.safetensors"
)
STAGE_A_BEST_SHA = "cd2829c1b5fb823fc03f18efe66a7387124ef44be2545b9e385a17eb6237bf5c"
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
BEST_PATH_FILE = Path("/home/morpheus/.hyperlex/models/BEST.path")
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
PRIVATE = Path(
    "/home/morpheus/hlx-private/classification-v5-reserve-fail-diagnose-20261001"
)
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
SPEC_DIR = REPO / "specs" / "007-hyperlexical-model"

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
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    os.chmod(path, 0o600)


def write_repo(path: Path, payload: dict | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def code_revision() -> str:
    override = (os.environ.get("HLX_V5_DIAG_CODE_REVISION") or "").strip()
    if override:
        return override
    try:
        completed = subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def pin_inputs() -> dict[str, Any]:
    if sha256_file(DATASET) != DATASET_SHA:
        fail("dataset_digest_mismatch")
    seal = json.loads(sudo_read_text(RESERVE_SEAL))
    score = json.loads(sudo_read_text(RESERVE_SCORE))
    if score.get("settlement") != "RESERVE_FAIL":
        fail("reserve_settlement_not_fail")
    if seal.get("rows_sha256") != score["reserve_hashes"]["rows_sha256"]:
        fail("reserve_hash_mismatch")
    index = json.loads(sudo_read_text(STAGE_B_INDEX))
    if index.get("index_sha256") != STAGE_B_INDEX_SHA:
        fail("stage_b_index_sha_mismatch")
    if sudo_sha256(STAGE_A_BEST_WEIGHTS) != STAGE_A_BEST_SHA:
        fail("STAGE_A_BEST_sha_mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_sha_mismatch")
    expected_best_path = str(
        Path(
            "/home/morpheus/.hyperlex/models/"
            "hyperlex-encoder-modernbert-base-seed-select004"
        )
    )
    if BEST_PATH_FILE.read_text(encoding="utf-8").strip() != expected_best_path:
        fail("BEST_path_mutated")
    return {"seal": seal, "score": score, "index": index}


def _cosine(a: list[float], b: list[float]) -> float:
    return float(sum(x * y for x, y in zip(a, b)))


def _max_sim(query: list[float], matrix: list[list[float]]) -> float:
    if not matrix:
        return 0.0
    best = -1.0
    for vector in matrix:
        score = _cosine(query, vector)
        if score > best:
            best = score
    return best


def _max_sim_family(
    query: list[float], records: list[dict[str, Any]], family: str
) -> float | None:
    best = None
    for rec in records:
        if rec.get("family") != family:
            continue
        score = _cosine(query, rec["embedding"])
        if best is None or score > best:
            best = score
    return best


def inner() -> int:
    import torch
    from torch import nn
    from transformers import AutoModel, AutoTokenizer
    from safetensors.torch import load_file

    from hyperlexical.classification_v5_stage_a_two_stage import (
        gate1_probabilities,
        gate2_probabilities,
    )
    from hyperlexical.classification_v5_stage_a_two_stage_promote import (
        decide_canonical_stage_a,
    )
    from hyperlexical.classification_v5_stage_b import (
        gold_end_to_end,
        retrieval_candidates_from_embedding,
    )
    from hyperlexical.classification_v5_reserve_fail_diagnose import (
        ACTION,
        PRESERVATION,
        assemble_diagnose_receipt,
        classify_distribution,
        cohort_shift_table,
        decide_generalization_diagnosis,
        explain_wrong_emissions,
        family_coverage_audit,
        label_metrics,
        next_action_for_diagnosis,
        representation_summary,
        routing_breakdown,
        stage_b_on_correct_present,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.holdout_guard import normalized_text_sha256
    from hyperlexical.layout import HIDDEN, MAX_LEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors

    pinned = pin_inputs()
    if PRIVATE.exists() and (PRIVATE / "DIAGNOSIS.json").exists():
        fail(f"output_already_exists:{PRIVATE}")
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    write_private(PRIVATE / "PRESERVATION.json", PRESERVATION)

    surface = load_jsonl(DATASET)
    train_rows = [r for r in surface if r.get("split") == "train"]
    val_rows = [r for r in surface if r.get("split") == "validation"]
    reserve_rows = load_jsonl(RESERVE_ROWS)
    index = pinned["index"]
    score_receipt = pinned["score"]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("diagnose_requires_cuda")

    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tokenizer.padding_side = "right"
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    gate1_head = nn.Linear(HIDDEN, 2)
    gate2_head = nn.Linear(HIDDEN, 2)
    best_split = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    if apply_encoder_trainable(encoder, best_split.get("encoder") or {})["loaded"] != 48:
        fail("BEST_encoder_overlay_incomplete")
    stage_a_split = split_weight_tensors(
        load_file(str(STAGE_A_BEST_WEIGHTS), device="cpu")
    )
    loaded_a = apply_encoder_trainable(encoder, stage_a_split.get("encoder") or {})
    if loaded_a["loaded"] != 12:
        fail(f"STAGE_A_BEST_overlay_incomplete:{loaded_a['loaded']}")
    freeze_encoder(encoder, last_trainable=2)
    with torch.no_grad():
        gate1_head.weight.copy_(stage_a_split["gate1_head"]["weight"])
        gate1_head.bias.copy_(stage_a_split["gate1_head"]["bias"])
        gate2_head.weight.copy_(stage_a_split["gate2_head"]["weight"])
        gate2_head.bias.copy_(stage_a_split["gate2_head"]["bias"])
    encoder.to(device).eval()
    gate1_head.to(device).eval()
    gate2_head.to(device).eval()

    def embed_texts(texts: list[str]) -> list[list[float]]:
        vectors = []
        with torch.no_grad():
            for start in range(0, len(texts), 32):
                batch = texts[start : start + 32]
                encoded = tokenizer(
                    batch,
                    padding=True,
                    truncation=True,
                    max_length=int(MAX_LEN),
                    return_tensors="pt",
                )
                encoded = {k: v.to(device) for k, v in encoded.items()}
                pooled = encoder(**encoded).last_hidden_state[:, 0]
                pooled = torch.nn.functional.normalize(pooled, dim=-1)
                vectors.extend(pooled.detach().cpu().tolist())
        return vectors

    def score_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        with torch.no_grad():
            for row in rows:
                text = str(row["text"])
                encoded = tokenizer(
                    [text],
                    padding=True,
                    truncation=True,
                    max_length=int(MAX_LEN),
                    return_tensors="pt",
                )
                encoded = {k: v.to(device) for k, v in encoded.items()}
                pooled = encoder(**encoded).last_hidden_state[:, 0]
                g1 = gate1_probabilities(
                    gate1_head(pooled)[0].detach().cpu().tolist()
                )
                g2 = gate2_probabilities(
                    gate2_head(pooled)[0].detach().cpu().tolist()
                )
                decision = decide_canonical_stage_a(
                    p_possible=float(g1["POSSIBLE_EVIDENCE"]),
                    p_confirmed=float(g2["CONFIRMED_PRESENT"]),
                )
                hidden = torch.nn.functional.normalize(pooled, dim=-1)[0].detach().cpu().tolist()
                ranked = retrieval_candidates_from_embedding(
                    hidden,
                    index["records"],
                    family_vocabulary=index.get("family_vocabulary"),
                )
                gold = gold_end_to_end(row) if "gold_decision_type" not in row else {
                    "decision_type": row["gold_decision_type"],
                    "family": row.get("gold_family"),
                }
                if "gold_family" not in row and row.get("evidence_subtype") == "POSITIVE_EVIDENCE":
                    gold = gold_end_to_end(row)
                candidates = ranked["candidates"]
                top3 = candidates[2] if len(candidates) > 2 else None
                family = row.get("gold_family")
                if family is None and row.get("candidate_families"):
                    family = row["candidate_families"][0]
                out.append(
                    {
                        **row,
                        "evidence_decision": decision,
                        "gold_decision_type": gold["decision_type"],
                        "gold_family": family if family is not None else gold.get("family"),
                        "identity": row.get("identity")
                        or normalized_text_sha256(text),
                        "p_confirmed": float(g2["CONFIRMED_PRESENT"]),
                        "p_possible": float(g1["POSSIBLE_EVIDENCE"]),
                        "embedding": hidden,
                        "top1_family": ranked["top1"]["family"],
                        "top1_score": ranked["top1"]["score"],
                        "top2_family": ranked["top2"]["family"],
                        "top2_score": ranked["top2"]["score"],
                        "top3_family": None if top3 is None else top3["family"],
                        "top3_score": None if top3 is None else top3["score"],
                    }
                )
        return out

    # Embed a stratified train pool for nearest-train similarity (cap for cost).
    train_pool = []
    by_label: dict[str, list[dict]] = {"NO_EVIDENCE": [], "EVIDENCE_PRESENT": [], "UNCERTAIN": []}
    for row in train_rows:
        by_label.setdefault(str(row["evidence_label"]), []).append(row)
    for label, bucket in by_label.items():
        ordered = sorted(bucket, key=lambda item: item["identity"])
        train_pool.extend(ordered[:400])
    train_emb = embed_texts([str(r["text"]) for r in train_pool])
    val_scored = score_rows(val_rows)
    reserve_scored = score_rows(reserve_rows)
    val_emb = [row["embedding"] for row in val_scored]

    for row in val_scored:
        row["nearest_train_sim"] = _max_sim(row["embedding"], train_emb)
        row["nearest_validation_sim"] = None  # not meaningful vs self-split
        row["distribution_class"] = classify_distribution(row["nearest_train_sim"])
        if row.get("gold_family"):
            row["nearest_index_family_sim"] = _max_sim_family(
                row["embedding"], index["records"], str(row["gold_family"])
            )
        del row["embedding"]

    for row in reserve_scored:
        row["nearest_train_sim"] = _max_sim(row["embedding"], train_emb)
        row["nearest_validation_sim"] = _max_sim(row["embedding"], val_emb)
        row["distribution_class"] = classify_distribution(row["nearest_train_sim"])
        if row.get("gold_family"):
            row["nearest_index_family_sim"] = _max_sim_family(
                row["embedding"], index["records"], str(row["gold_family"])
            )
        del row["embedding"]

    stage_a_val = label_metrics(val_scored)
    stage_a_reserve = label_metrics(reserve_scored)
    routing = routing_breakdown(reserve_scored)
    representation = {
        "validation": representation_summary(val_scored),
        "reserve": representation_summary(reserve_scored),
    }
    stage_b_val_receipt = json.loads(sudo_read_text(STAGE_B_VAL))
    stage_b_val_metrics = stage_b_val_receipt.get("metrics") or {}
    # Approximate validation top1 on correct-present via recompute.
    stage_b_val_correct = stage_b_on_correct_present(val_scored)
    stage_b_res_correct = stage_b_on_correct_present(reserve_scored)

    index_family_counts = Counter(str(r["family"]) for r in index["records"])
    validation_family_counts = Counter(
        str((r.get("candidate_families") or [None])[0])
        for r in val_rows
        if r.get("evidence_subtype") == "POSITIVE_EVIDENCE"
    )
    family_cov = family_coverage_audit(
        reserve_scored,
        index_family_counts=index_family_counts,
        validation_family_counts=validation_family_counts,
        stage_b_correct_present=stage_b_res_correct,
    )

    # Separate Stage-A-induced vs pure Stage-B family failures among FAMILY emissions.
    pure_b = 0
    induced_a = 0
    for row in reserve_scored:
        if row.get("evidence_decision") != "EVIDENCE_PRESENT":
            continue
        # reconstruct emission
        from hyperlexical.classification_v5_stage_b import compose_end_to_end
        from hyperlexical.classification_v5_promotion_reserve import (
            MINIMUM_FAMILY_MARGIN,
            MINIMUM_FAMILY_SCORE,
        )

        decided = compose_end_to_end(
            evidence_decision="EVIDENCE_PRESENT",
            ranked_candidates=[
                {"family": row["top1_family"], "score": row["top1_score"]},
                {"family": row["top2_family"], "score": row["top2_score"]},
            ],
            family_score_min=MINIMUM_FAMILY_SCORE,
            family_margin_min=MINIMUM_FAMILY_MARGIN,
        )
        if decided["decision_type"] != "FAMILY":
            continue
        if row.get("evidence_label") != "EVIDENCE_PRESENT":
            induced_a += 1
        elif decided.get("family") != row.get("gold_family"):
            pure_b += 1

    wrong = explain_wrong_emissions(
        score_receipt["metrics"].get("wrong_emissions") or [],
        {r["identity"]: r for r in reserve_rows},
    )

    diagnosis = decide_generalization_diagnosis(
        stage_a_val=stage_a_val,
        stage_a_reserve=stage_a_reserve,
        stage_b_val={
            "family_emission_precision": stage_b_val_metrics.get(
                "family_emission_precision"
            ),
            "top1_accuracy": stage_b_val_correct.get("top1_accuracy"),
        },
        stage_b_reserve_correct_present=stage_b_res_correct,
        representation_reserve=representation["reserve"],
    )
    next_action = next_action_for_diagnosis(diagnosis)

    # Dominant cohorts for the three headline Stage-A deltas.
    present_fn = cohort_shift_table(
        val_scored, reserve_scored, gold_label="EVIDENCE_PRESENT", error_pred="NO_EVIDENCE"
    )
    # Also count UNCERTAIN as PRESENT miss for recall decomposition helper table.
    none_fp = cohort_shift_table(
        val_scored,
        reserve_scored,
        gold_label="NO_EVIDENCE",
        error_pred="EVIDENCE_PRESENT",
    )
    none_miss = cohort_shift_table(
        val_scored,
        reserve_scored,
        gold_label="NO_EVIDENCE",
        error_pred="UNCERTAIN",
    )

    def top_non_all(table: list[dict[str, Any]], n: int = 8) -> list[dict[str, Any]]:
        return [row for row in table if row["cohort"] != "ALL"][:n]

    receipt = assemble_diagnose_receipt(
        {
            "stage_a": {
                "validation": stage_a_val,
                "reserve": stage_a_reserve,
                "deltas": {
                    "false_entry": (stage_a_reserve["false_entry"] or 0)
                    - (stage_a_val["false_entry"] or 0),
                    "PRESENT_recall": (stage_a_reserve["PRESENT_recall"] or 0)
                    - (stage_a_val["PRESENT_recall"] or 0),
                    "NONE_recall": (stage_a_reserve["NONE_recall"] or 0)
                    - (stage_a_val["NONE_recall"] or 0),
                    "UNCERTAIN_recall": (stage_a_reserve["UNCERTAIN_recall"] or 0)
                    - (stage_a_val["UNCERTAIN_recall"] or 0),
                },
                "dominant_false_entry_cohorts": top_non_all(none_fp),
                "dominant_PRESENT_miss_cohorts": top_non_all(present_fn),
                "dominant_NONE_to_UNCERTAIN_cohorts": top_non_all(none_miss),
            },
            "routing": routing,
            "representation": representation,
            "stage_b": {
                "validation_end_to_end": {
                    "family_emission_precision": stage_b_val_metrics.get(
                        "family_emission_precision"
                    ),
                    "family_emission_coverage": stage_b_val_metrics.get(
                        "family_emission_coverage"
                    ),
                    "family_emission_recall": stage_b_val_metrics.get(
                        "family_emission_recall"
                    ),
                },
                "validation_correct_present": {
                    k: v
                    for k, v in stage_b_val_correct.items()
                    if k != "rows"
                },
                "reserve_correct_present": {
                    k: v
                    for k, v in stage_b_res_correct.items()
                    if k != "rows"
                },
                "family_failure_split": {
                    "stage_a_induced_family_failures": induced_a,
                    "pure_stage_b_family_failures": pure_b,
                },
            },
            "family_coverage": family_cov,
            "wrong_emissions": wrong,
            "diagnosis": diagnosis,
            "next_action": next_action,
            "reserve_hashes": score_receipt["reserve_hashes"],
        }
    )
    receipt["code_revision"] = code_revision()
    from hyperlexical.classification_v5_stage_a import canonical_json, sha256_text

    receipt["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in receipt.items() if k != "receipt_sha256"})
    )

    write_private(PRIVATE / "DIAGNOSIS.json", receipt)
    write_private(
        PRIVATE / "SUMMARY.json",
        {
            "ACTION": ACTION,
            "diagnosis": diagnosis["diagnosis"],
            "remediation": diagnosis["remediation"],
            "next_action": next_action,
            "receipt_sha256": receipt["receipt_sha256"],
            "STAGE_A_BEST_MUTATED": False,
            "MODEL_WIDE_BEST_MUTATED": False,
            "preservation": PRESERVATION,
        },
    )
    # Strip huge row lists from repo receipt.
    public = {
        k: v
        for k, v in receipt.items()
        if k
        not in {
            # keep all; family coverage is fine
        }
    }
    write_repo(
        SPEC_DIR / "classification-v5-reserve-fail-diagnose-receipt-20261001.json",
        public,
    )

    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mutated_during_diagnose")
    if sudo_sha256(STAGE_A_BEST_WEIGHTS) != STAGE_A_BEST_SHA:
        fail("STAGE_A_BEST_mutated_during_diagnose")
    print(json.dumps(json.loads((PRIVATE / "SUMMARY.json").read_text()), indent=2, sort_keys=True))
    return 0


def main() -> int:
    if os.environ.get("HLX_V5_DIAG_INNER") == "1" or "--inner" in sys.argv:
        return inner()

    from hyperlexical.classification_v5_reserve_fail_diagnose import (
        ACTION,
        PRESERVATION,
    )

    pin_inputs()
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    write_private(PRIVATE / "LAUNCH.json", {"action": ACTION, "preservation": PRESERVATION})
    revision = code_revision()
    command = [
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
        "HLX_V5_DIAG_INNER=1",
        "-e",
        f"HLX_V5_DIAG_CODE_REVISION={revision}",
        "-e",
        "HF_HUB_OFFLINE=1",
        "-e",
        "TRANSFORMERS_OFFLINE=1",
        "--entrypoint",
        "python3",
        IMAGE,
        str(REPO / "scripts/spark/run_classification_v5_reserve_fail_diagnose.py"),
        "--inner",
    ]
    log_path = PRIVATE / "diagnose.log"
    print(json.dumps({"launch": command[-1], "log": str(log_path)}, sort_keys=True), flush=True)
    with log_path.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(
            command, check=False, stdout=handle, stderr=subprocess.STDOUT
        )
    try:
        print(log_path.read_text(encoding="utf-8")[-14000:])
    except OSError:
        pass
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mutated_after_diagnose")
    if sudo_sha256(STAGE_A_BEST_WEIGHTS) != STAGE_A_BEST_SHA:
        fail("STAGE_A_BEST_mutated_after_diagnose")
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
