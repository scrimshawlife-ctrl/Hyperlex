"""EVALUATE_FULL_V5_PIPELINE — Spark GPU eval under frozen Stage-A/B pins.

Uses factorized STAGE_A_BEST + frozen Stage-B index/floors. Does not rebuild
index, retune floors, score spent reserve, or mutate BEST.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

SURFACE = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-negative-evidence-surface-v1r9-20260930"
)
DATASET = SURFACE / "EVIDENCE_SURFACE.jsonl"
DATASET_SHA = "8d4be8301b89b191841342fe11ef647c838b32e56e6d133b610c232264c5d00a"
STAGE_A_BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/STAGE_A_BEST/model.safetensors"
)
STAGE_A_BEST_SHA = (
    "f2b00c5dfeb087288fc1686c901fbc8b52a8ba7a7b51cb83ff038656f93617fa"
)
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
FROZEN_INDEX = Path(
    "/home/morpheus/hlx-private/classification-v5-stage-b-20260930/STAGE_B_INDEX.json"
)
FROZEN_INDEX_SHA = (
    "3fd6c87a5825f3f2a25a81f1a769a77aa69e03ddca5b370f9247672d93aaee21"
)
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
PRIVATE = Path(
    "/home/morpheus/hlx-private/classification-v5-pipeline-eval-20261001"
)
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
REPO_ART = (
    REPO / "artifacts" / "experiments" / "HLX-CLASSIFICATION-V5-PIPELINE-EVAL-001"
)
PACK_ART = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V5-PRODUCTION-PACKAGING-V1"
)
SPEC = REPO / "specs" / "007-hyperlexical-model"

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
        return subprocess.run(
            ["sudo", "-n", "sha256sum", str(path)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.split()[0]


def sudo_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except PermissionError:
        return subprocess.run(
            ["sudo", "-n", "cat", str(path)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout


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
    override = (os.environ.get("HLX_V5_STAGE_A_CODE_REVISION") or "").strip()
    if override:
        return override
    try:
        return subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def fail(msg: str) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(2)


def inner() -> int:
    import torch
    import torch.nn.functional as F
    from torch import nn
    from safetensors.torch import load_file
    from transformers import AutoModel, AutoTokenizer

    from hyperlexical.classification_v5_pipeline_evaluate import (
        build_evaluation_receipt,
        evaluate_pipeline_rows,
        utc_now_iso,
    )
    from hyperlexical.classification_v5_production_packaging import (
        build_packaging_receipt,
        hf_package_v5_card_section,
        packaging_contract,
    )
    from hyperlexical.classification_v5_stage_a_canonical import (
        decide_canonical_stage_a,
        may_invoke_stage_b,
        verify_canonical_checkpoint_keys,
    )
    from hyperlexical.classification_v5_stage_b import (
        FROZEN_MINIMUM_FAMILY_SCORE,
        FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
        gold_end_to_end,
        retrieval_candidates_from_embedding,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.layout import HIDDEN, MAX_LEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors

    if sha256_file(DATASET) != DATASET_SHA:
        fail("dataset_digest_mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mismatch")
    if sudo_sha256(STAGE_A_BEST_WEIGHTS) != STAGE_A_BEST_SHA:
        fail("STAGE_A_BEST_mismatch")

    index = json.loads(sudo_read_text(FROZEN_INDEX))
    index_sha = index.get("index_sha256")
    if index_sha != FROZEN_INDEX_SHA:
        fail(f"frozen_index_sha_mismatch:{index_sha}")

    tensors = load_file(str(STAGE_A_BEST_WEIGHTS), device="cpu")
    keys_ok = verify_canonical_checkpoint_keys(list(tensors.keys()))
    if not keys_ok["pass"]:
        fail(f"checkpoint_incomplete:{json.dumps(keys_ok, sort_keys=True)}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("pipeline evaluate requires CUDA")

    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tokenizer.padding_side = "right"
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    relation_head = nn.Linear(HIDDEN, 2)
    resolvability_head = nn.Linear(HIDDEN, 2)

    best_split = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    if apply_encoder_trainable(encoder, best_split.get("encoder") or {})["loaded"] != 48:
        fail("BEST_encoder_overlay_incomplete")
    split = split_weight_tensors(tensors)
    loaded = apply_encoder_trainable(encoder, split.get("encoder") or {})
    if loaded["loaded"] != 12:
        fail(f"STAGE_A_overlay_incomplete:{loaded['loaded']}")
    freeze_encoder(encoder, last_trainable=2)
    with torch.no_grad():
        relation_head.weight.copy_(split["relation_head"]["weight"])
        relation_head.bias.copy_(split["relation_head"]["bias"])
        resolvability_head.weight.copy_(split["resolvability_head"]["weight"])
        resolvability_head.bias.copy_(split["resolvability_head"]["bias"])

    encoder.to(device).eval()
    relation_head.to(device).eval()
    resolvability_head.to(device).eval()

    rows = [r for r in load_jsonl(DATASET) if r.get("split") == "validation"]
    records = index["records"]
    vocab = index.get("family_vocabulary")
    score_rows = []
    with torch.no_grad():
        for row in rows:
            encoded = tokenizer(
                [str(row["text"])],
                padding=True,
                truncation=True,
                max_length=int(MAX_LEN),
                return_tensors="pt",
            )
            encoded = {k: v.to(device) for k, v in encoded.items()}
            pooled = encoder(**encoded).last_hidden_state[:, 0]
            rel = F.softmax(relation_head(pooled)[0], dim=-1).tolist()
            res = F.softmax(resolvability_head(pooled)[0], dim=-1).tolist()
            decision = decide_canonical_stage_a(
                p_relation=float(rel[1]), p_resolvable=float(res[1])
            )
            invoked = may_invoke_stage_b(decision)
            hidden = F.normalize(pooled, dim=-1)[0].detach().cpu().tolist()
            ranked = retrieval_candidates_from_embedding(
                hidden, records, family_vocabulary=vocab
            )
            gold = gold_end_to_end(row)
            candidates = ranked["candidates"]
            top3 = candidates[2] if len(candidates) > 2 else None
            score_rows.append(
                {
                    "evidence_decision": decision,
                    "evidence_label": row["evidence_label"],
                    "evidence_subtype": row["evidence_subtype"],
                    "gold_decision_type": gold["decision_type"],
                    "gold_family": gold["family"],
                    "identity": row["identity"],
                    "invoked_stage_b": invoked,
                    "p_relation": float(rel[1]),
                    "p_resolvable": float(res[1]),
                    "top1_family": ranked["top1"]["family"],
                    "top1_score": ranked["top1"]["score"],
                    "top2_family": ranked["top2"]["family"],
                    "top2_score": ranked["top2"]["score"],
                    "top3_family": None if top3 is None else top3["family"],
                    "top3_score": None if top3 is None else top3["score"],
                }
            )

    evaluation = evaluate_pipeline_rows(score_rows)
    revision = code_revision()
    evaluated_at = utc_now_iso()
    receipt = build_evaluation_receipt(
        evaluation=evaluation,
        code_revision=revision,
        surface_dataset_sha256=DATASET_SHA,
        index_sha256=index_sha,
        evaluated_at=evaluated_at,
    )
    packaging = build_packaging_receipt(
        code_revision=revision,
        pipeline_eval_receipt_sha256=receipt["PIPELINE_EVAL_RECEIPT_SHA256"],
        pipeline_eval_pass=bool(receipt["PIPELINE_EVAL_PASS"]),
        sealed_at=evaluated_at,
    )

    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    write_private(PRIVATE / "PIPELINE_EVAL.json", receipt)
    write_private(PRIVATE / "PACKAGING.json", packaging)
    write_private(
        PRIVATE / "SCORE_ROWS_META.json",
        {
            "n": len(score_rows),
            "decision_counts": evaluation["decision_counts"],
            "floors": evaluation["floors"],
        },
    )

    summary = {
        "BEST_MUTATED": False,
        "EXPERIMENT_ID": "HLX-CLASSIFICATION-V5-PIPELINE-EVAL-001",
        "MODEL_WIDE_BEST": BEST_SHA,
        "NEXT_ACTION": packaging["NEXT_ACTION"],
        "PACKAGING_ID": packaging["PACKAGING_ID"],
        "PACKAGING_RECEIPT_SHA256": packaging["PACKAGING_RECEIPT_SHA256"],
        "PIPELINE_EVAL_PASS": receipt["PIPELINE_EVAL_PASS"],
        "PIPELINE_EVAL_RECEIPT_SHA256": receipt["PIPELINE_EVAL_RECEIPT_SHA256"],
        "RESERVE_CONSUMED": False,
        "STAGE_A_BEST": STAGE_A_BEST_SHA,
        "TRAIN": False,
        "false_evidence_entry_rate_on_none": evaluation["metrics"][
            "false_evidence_entry_rate_on_none"
        ],
        "family_emission_coverage": evaluation["metrics"].get(
            "family_emission_coverage"
        ),
        "family_emission_precision": evaluation["metrics"].get(
            "family_emission_precision"
        ),
        "gating_pass": evaluation["gating"]["pass"],
        "index_rebuilt": False,
        "index_sha256": index_sha,
        "n_validation": len(score_rows),
        "primary_gate_pass": evaluation["metrics"]["primary_gate_pass"],
        "secondary_gate_pass": evaluation["metrics"]["secondary_gate_pass"],
        "selective_accuracy": evaluation["metrics"].get("selective_accuracy"),
        "thresholds": {
            "relation_threshold": 0.60,
            "resolvability_threshold": 0.75,
            "minimum_family_score": FROZEN_MINIMUM_FAMILY_SCORE,
            "minimum_top1_top2_margin": FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
        },
    }
    write_private(PRIVATE / "SUMMARY.json", summary)
    write_repo(REPO_ART / "pipeline_eval_receipt.json", receipt)
    write_repo(REPO_ART / "pipeline_eval_summary.json", summary)
    write_repo(PACK_ART / "packaging_receipt.json", packaging)
    write_repo(PACK_ART / "packaging_contract.json", packaging_contract(
        pipeline_eval_receipt_sha256=receipt["PIPELINE_EVAL_RECEIPT_SHA256"],
        pipeline_eval_pass=bool(receipt["PIPELINE_EVAL_PASS"]),
    ))
    write_repo(PACK_ART / "SUMMARY.json", summary)
    write_repo(
        SPEC / "classification-v5-pipeline-eval-receipt-20261001.json", receipt
    )
    write_repo(
        SPEC / "classification-v5-production-packaging-receipt-20261001.json",
        packaging,
    )
    write_repo(
        SPEC / "classification-v5-pipeline-eval-20261001.md",
        f"""# EVALUATE_FULL_V5_PIPELINE

```text
PIPELINE_EVAL_PASS = {receipt['PIPELINE_EVAL_PASS']}
PIPELINE_EVAL_RECEIPT_SHA256 = {receipt['PIPELINE_EVAL_RECEIPT_SHA256']}
STAGE_A_BEST = {STAGE_A_BEST_SHA}
index = {index_sha}
floors = {FROZEN_MINIMUM_FAMILY_SCORE} / {FROZEN_MINIMUM_TOP1_TOP2_MARGIN}
false_entry = {summary['false_evidence_entry_rate_on_none']}
family_precision = {summary['family_emission_precision']}
selective_accuracy = {summary['selective_accuracy']}
gating_pass = {summary['gating_pass']}
```

Index not rebuilt. Reserve not scored. Known limitation: index embeddings
parent is superseded two-stage Stage-A; queries use canonical factorized Stage-A.
""",
    )
    write_repo(
        SPEC / "classification-v5-production-packaging-20261001.md",
        "# HYPERLEX_V5_PRODUCTION_PACKAGING_V1\n\n"
        + hf_package_v5_card_section()
        + f"\n**PACKAGING_RECEIPT_SHA256** = `{packaging['PACKAGING_RECEIPT_SHA256']}`\n"
        + f"**NEXT_ACTION** = `{packaging['NEXT_ACTION']}`\n",
    )

    # Append V5 section to hf-package README if missing.
    hf_readme = SPEC / "hf-package" / "README.md"
    section = hf_package_v5_card_section()
    if hf_readme.exists():
        text = hf_readme.read_text(encoding="utf-8")
        marker = "## V5 classification pipeline"
        if marker not in text:
            hf_readme.write_text(text.rstrip() + "\n\n" + section + "\n", encoding="utf-8")

    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mutated")
    if sudo_sha256(STAGE_A_BEST_WEIGHTS) != STAGE_A_BEST_SHA:
        fail("STAGE_A_BEST_mutated")

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if receipt["PIPELINE_EVAL_PASS"] else 2


def main() -> int:
    if os.environ.get("HLX_V5_PIPELINE_EVAL_INNER") == "1":
        return inner()

    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    revision = code_revision()
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
        "HLX_V5_PIPELINE_EVAL_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={revision}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(REPO / "scripts/spark/run_classification_v5_pipeline_evaluate.py"),
    ]
    log = PRIVATE / "pipeline_eval_console.log"
    with log.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(
            cmd, check=False, stdout=handle, stderr=subprocess.STDOUT
        )
    try:
        print(log.read_text(encoding="utf-8")[-12000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
