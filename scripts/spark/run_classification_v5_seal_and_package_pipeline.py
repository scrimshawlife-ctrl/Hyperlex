"""SEAL_AND_PACKAGE_HYPERLEX_V5_STAGE_A_B_V1R2_PIPELINE — Spark GPU seal.

Cold-loads canonical Stage-A + V1R2 Stage-B index, re-scores validation under
frozen floors (no index rebuild / no retune), round-trips package config in a
clean subprocess, audits stale refs, and seals the package receipt.
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
    "classification-v5-stage-a-identifiability-filtered-v1r2-20261001"
)
DATASET = SURFACE / "EVIDENCE_SURFACE.jsonl"
DATASET_SHA = "492ed36751c7fdc40fe10bcdfabb69fa8783f8680259c31b3a64ee6903326d73"
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
INDEX_PATH = Path(
    "/home/morpheus/hlx-private/classification-v5-stage-b-v1r2-20261001/"
    "STAGE_B_INDEX.json"
)
INDEX_SHA = "4febe96ea179597eb7792b376ed9eedbc9295a2fd8b5fa0eec969719f015c1f4"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
PRIVATE = Path(
    "/home/morpheus/hlx-private/classification-v5-stage-a-b-v1r2-seal-20261001"
)
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
REPO_ART = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V5-STAGE-A-B-V1R2-SEAL-001"
)
SPEC = REPO / "specs" / "007-hyperlexical-model"
MAX_LEN = 256

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
    if os.access(path, os.R_OK):
        return path.read_text(encoding="utf-8")
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


def write_repo(path: Path, payload: dict | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


def fail(msg: str) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(2)


def code_revision() -> str:
    env = os.environ.get("HLX_V5_STAGE_A_CODE_REVISION")
    if env:
        return env
    try:
        return subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def run_round_trip_subprocess(package_config_path: Path, replay_path: Path) -> dict:
    """Clean-process cold-load of package config + compare replay forwards."""
    script = r'''
import json, os, sys
from pathlib import Path
os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, os.environ["HLX_SHADOW"])
from hyperlexical.classification_v5_seal_and_package import (
    compose_runtime_row,
    FROZEN_INDEX_SHA256,
    FROZEN_MINIMUM_FAMILY_SCORE,
    FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
    STAGE_A_BEST_SHA256,
    MODEL_WIDE_BEST_SHA256,
    package_contract,
)
cfg = json.loads(Path(sys.argv[1]).read_text())
replay = json.loads(Path(sys.argv[2]).read_text())
# Fail closed on pin mismatch.
assert cfg["STAGE_A_BEST"] == STAGE_A_BEST_SHA256
assert cfg["MODEL_WIDE_BEST"] == MODEL_WIDE_BEST_SHA256
assert cfg["STAGE_B_INDEX_SHA256"] == FROZEN_INDEX_SHA256
assert cfg["floors"]["minimum_family_score"] == FROZEN_MINIMUM_FAMILY_SCORE
assert cfg["floors"]["minimum_top1_top2_margin"] == FROZEN_MINIMUM_TOP1_TOP2_MARGIN
# Contract rebuild must match sealed manifest sha.
contract = package_contract(code_revision=cfg["code_revision"])
assert (
    contract["PIPELINE_DEPENDENCY_MANIFEST_SHA256"]
    == cfg["PIPELINE_DEPENDENCY_MANIFEST_SHA256"]
)
sa_mismatch = sb_mismatch = final_mismatch = 0
for row in replay:
    out = compose_runtime_row(
        stage_a_decision=row["stage_a_decision"],
        p_relation=row["p_relation"],
        p_resolvable=row["p_resolvable"],
        ranked_candidates=row.get("ranked_candidates"),
    )
    if out["stage_a_decision"] != row["expected"]["stage_a_decision"]:
        sa_mismatch += 1
    if bool(out["stage_b_executed"]) != bool(row["expected"]["stage_b_executed"]):
        sb_mismatch += 1
    if out["final_decision"] != row["expected"]["final_decision"]:
        final_mismatch += 1
    if out.get("predicted_family") != row["expected"].get("predicted_family"):
        final_mismatch += 1
print(json.dumps({
    "pass": sa_mismatch == 0 and sb_mismatch == 0 and final_mismatch == 0,
    "mismatches": {
        "stage_a_decision_mismatch_count": sa_mismatch,
        "stage_b_execution_mismatch_count": sb_mismatch,
        "family_final_decision_mismatch_count": final_mismatch,
    },
    "n_replay": len(replay),
    "manifest_sha_match": True,
}))
'''
    env = os.environ.copy()
    env["HLX_SHADOW"] = str(REPO / "scripts" / "shadow")
    env["HLX_V2_FORWARD_ONTOLOGY"] = "1"
    completed = subprocess.run(
        [sys.executable, "-c", script, str(package_config_path), str(replay_path)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if completed.returncode != 0:
        fail(f"round_trip_subprocess_failed:{completed.stderr[-2000:]}")
    return json.loads(completed.stdout.strip().splitlines()[-1])


def inner() -> int:
    import torch
    import torch.nn.functional as F
    from torch import nn
    from safetensors.torch import load_file
    from transformers import AutoModel, AutoTokenizer

    from hyperlexical.classification_v5_seal_and_package import (
        build_seal_receipt,
        compose_runtime_row,
        package_contract,
        pipeline_dependency_manifest,
        utc_now_iso,
        validate_integration_metrics,
        validate_round_trip,
    )
    from hyperlexical.classification_v5_stage_a_canonical import (
        decide_canonical_stage_a,
        may_invoke_stage_b,
        verify_canonical_checkpoint_keys,
    )
    from hyperlexical.classification_v5_stage_a_b_pipeline import (
        verify_entry_gating,
        verify_stage_b_parent_and_floors,
    )
    from hyperlexical.classification_v5_stage_b import (
        FROZEN_INDEX_SHA256,
        FROZEN_MINIMUM_FAMILY_SCORE,
        FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
        evaluate_end_to_end,
        gold_end_to_end,
        retrieval_candidates_from_embedding,
    )
    from hyperlexical.classification_v5_stale_reference_audit import (
        audit_tree,
        seal_audit_receipt,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.layout import HIDDEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors

    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("MODEL_WIDE_BEST_mismatch")
    if sudo_sha256(STAGE_A_BEST_WEIGHTS) != STAGE_A_BEST_SHA:
        fail("STAGE_A_BEST_mismatch")
    if sha256_file(DATASET) != DATASET_SHA and sudo_sha256(DATASET) != DATASET_SHA:
        # dataset may need sudo
        try:
            ds_sha = sudo_sha256(DATASET)
        except Exception:
            ds_sha = sha256_file(DATASET)
        if ds_sha != DATASET_SHA:
            fail(f"dataset_sha_mismatch:{ds_sha}")

    parent = verify_stage_b_parent_and_floors()
    entry = verify_entry_gating()
    if not parent["pass"] or not entry["pass"]:
        fail(json.dumps({"parent": parent, "entry": entry}, sort_keys=True))

    index_payload = json.loads(sudo_read_text(INDEX_PATH))
    index_sha = index_payload.get("index_sha256")
    if index_sha != INDEX_SHA or index_sha != FROZEN_INDEX_SHA256:
        fail(f"frozen_index_sha_mismatch:{index_sha}")
    if len(index_payload.get("records") or []) != 948:
        fail(f"index_row_count_mismatch:{len(index_payload.get('records') or [])}")

    tensors = load_file(str(STAGE_A_BEST_WEIGHTS), device="cpu")
    keys_ok = verify_canonical_checkpoint_keys(list(tensors.keys()))
    if not keys_ok["pass"]:
        fail(f"checkpoint_incomplete:{json.dumps(keys_ok, sort_keys=True)}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("seal package verify requires CUDA")

    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    relation_head = nn.Linear(HIDDEN, 2)
    resolvability_head = nn.Linear(HIDDEN, 2)
    best_split = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    apply_encoder_trainable(encoder, best_split.get("encoder") or {})
    split = split_weight_tensors(tensors)
    loaded = apply_encoder_trainable(encoder, split.get("encoder") or {})
    if loaded["loaded"] != 12:
        fail(f"overlay_incomplete:{loaded['loaded']}")
    # Fail closed on head shapes.
    if tuple(split["relation_head"]["weight"].shape) != (2, HIDDEN):
        fail("relation_head_shape_mismatch")
    if tuple(split["resolvability_head"]["weight"].shape) != (2, HIDDEN):
        fail("resolvability_head_shape_mismatch")
    freeze_encoder(encoder, last_trainable=2)
    with torch.no_grad():
        relation_head.weight.copy_(split["relation_head"]["weight"])
        relation_head.bias.copy_(split["relation_head"]["bias"])
        resolvability_head.weight.copy_(split["resolvability_head"]["weight"])
        resolvability_head.bias.copy_(split["resolvability_head"]["bias"])
    encoder.to(device).eval()
    relation_head.to(device).eval()
    resolvability_head.to(device).eval()

    cold_load = {
        "pass": True,
        "n_keys": keys_ok["n_keys"],
        "factorized_heads_pass": True,
        "overlay_loaded": loaded["loaded"],
        "index_sha256": index_sha,
        "index_n_records": len(index_payload["records"]),
        "MODEL_WIDE_BEST": BEST_SHA,
        "STAGE_A_BEST": STAGE_A_BEST_SHA,
        "load_sequence": [
            "ModernBERT",
            "MODEL_WIDE_BEST",
            "STAGE_A_BEST",
            "relation_head",
            "resolvability_head",
            "Stage-B index",
        ],
    }

    rows = load_jsonl(DATASET)
    val_rows = [r for r in rows if r.get("split") == "validation"]
    score_rows = []
    replay_rows = []
    with torch.no_grad():
        for row in val_rows:
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
            hidden = F.normalize(pooled, dim=-1)[0].detach().cpu().tolist()
            ranked = retrieval_candidates_from_embedding(
                hidden,
                index_payload["records"],
                family_vocabulary=index_payload.get("family_vocabulary"),
            )
            gold = gold_end_to_end(row)
            candidates = ranked["candidates"]
            top3 = candidates[2] if len(candidates) > 2 else None
            ranked_for_compose = [
                {"family": ranked["top1"]["family"], "score": ranked["top1"]["score"]},
                {"family": ranked["top2"]["family"], "score": ranked["top2"]["score"]},
            ]
            if top3 is not None:
                ranked_for_compose.append(
                    {"family": top3["family"], "score": top3["score"]}
                )
            forward = compose_runtime_row(
                stage_a_decision=decision,
                p_relation=float(rel[1]),
                p_resolvable=float(res[1]),
                ranked_candidates=ranked_for_compose,
            )
            score_rows.append(
                {
                    "evidence_decision": decision,
                    "evidence_label": row["evidence_label"],
                    "evidence_subtype": row["evidence_subtype"],
                    "gold_decision_type": gold["decision_type"],
                    "gold_family": gold["family"],
                    "identity": row["identity"],
                    "invoked_stage_b": may_invoke_stage_b(decision),
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
            replay_rows.append(
                {
                    "stage_a_decision": decision,
                    "p_relation": float(rel[1]),
                    "p_resolvable": float(res[1]),
                    "ranked_candidates": ranked_for_compose
                    if may_invoke_stage_b(decision)
                    else None,
                    "expected": {
                        "stage_a_decision": forward["stage_a_decision"],
                        "stage_b_executed": forward["stage_b_executed"],
                        "final_decision": forward["final_decision"],
                        "predicted_family": forward["predicted_family"],
                    },
                }
            )

    metrics = evaluate_end_to_end(
        score_rows,
        family_score_min=FROZEN_MINIMUM_FAMILY_SCORE,
        family_margin_min=FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
    )
    none_entered = sum(
        1
        for r in score_rows
        if r["evidence_decision"] == "NO_EVIDENCE" and r["invoked_stage_b"]
    )
    uncertain_entered = sum(
        1
        for r in score_rows
        if r["evidence_decision"] == "UNCERTAIN" and r["invoked_stage_b"]
    )
    present_permitted = sum(
        1
        for r in score_rows
        if r["evidence_decision"] == "EVIDENCE_PRESENT" and r["invoked_stage_b"]
    )
    metrics["gating"] = {
        "none_entered_stage_b": none_entered,
        "uncertain_entered_stage_b": uncertain_entered,
        "present_permitted_stage_b": present_permitted,
        "pass": none_entered == 0 and uncertain_entered == 0,
    }
    integration = validate_integration_metrics(metrics)

    revision = code_revision()
    sealed_at = utc_now_iso()
    manifest = pipeline_dependency_manifest(code_revision=revision)
    contract = package_contract(code_revision=revision)
    package_config = {
        "STAGE_A_BEST": STAGE_A_BEST_SHA,
        "MODEL_WIDE_BEST": BEST_SHA,
        "STAGE_B_INDEX_SHA256": INDEX_SHA,
        "thresholds": {"relation": 0.60, "resolvability": 0.75},
        "floors": {
            "minimum_family_score": FROZEN_MINIMUM_FAMILY_SCORE,
            "minimum_top1_top2_margin": FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
        },
        "PIPELINE_DEPENDENCY_MANIFEST_SHA256": manifest[
            "PIPELINE_DEPENDENCY_MANIFEST_SHA256"
        ],
        "code_revision": revision,
        "pipeline_version": contract["PIPELINE_ID"],
        "schema": contract["schema"],
    }

    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    cfg_path = PRIVATE / "PACKAGE_CONFIG.json"
    replay_path = PRIVATE / "ROUND_TRIP_REPLAY.json"
    write_private(cfg_path, package_config)
    # Deterministic replay surface: full validation set (composition is pure).
    write_private(replay_path, replay_rows)
    round_raw = run_round_trip_subprocess(cfg_path, replay_path)
    round_trip = validate_round_trip(round_raw["mismatches"])
    round_trip["n_replay"] = round_raw.get("n_replay")
    round_trip["manifest_sha_match"] = round_raw.get("manifest_sha_match")
    round_trip["subprocess_pass"] = round_raw.get("pass")

    audit = audit_tree(REPO)
    stale_sealed = seal_audit_receipt(audit)

    receipt = build_seal_receipt(
        code_revision=revision,
        cold_load=cold_load,
        integration=integration,
        round_trip=round_trip,
        stale_audit=audit,
        sealed_at=sealed_at,
    )

    # Pointer integrity after run.
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mutated")
    if sudo_sha256(STAGE_A_BEST_WEIGHTS) != STAGE_A_BEST_SHA:
        fail("STAGE_A_BEST_mutated")

    summary = {
        "BEST_MUTATED": False,
        "EXPERIMENT_ID": receipt["EXPERIMENT_ID"],
        "HUB_STATUS": receipt["HUB_STATUS"],
        "MODEL_WIDE_BEST": BEST_SHA,
        "NEXT_ACTION": receipt["NEXT_ACTION"],
        "PACKAGING_ID": receipt["PACKAGING_ID"],
        "PIPELINE_DEPENDENCY_MANIFEST_SHA256": receipt[
            "PIPELINE_DEPENDENCY_MANIFEST_SHA256"
        ],
        "PIPELINE_ID": receipt["PIPELINE_ID"],
        "RESERVE_CONSUMED": False,
        "SEAL_PACKAGE_RECEIPT_SHA256": receipt["SEAL_PACKAGE_RECEIPT_SHA256"],
        "STAGE_A_BEST": STAGE_A_BEST_SHA,
        "STAGE_B_INDEX_SHA256": INDEX_SHA,
        "TRAIN": False,
        "V5_STAGE_A_B_PIPELINE_STATE": receipt["freeze_state"][
            "V5_STAGE_A_B_PIPELINE_STATE"
        ],
        "V5_STAGE_A_STATE": receipt["freeze_state"]["V5_STAGE_A_STATE"],
        "V5_STAGE_B_STATE": receipt["freeze_state"]["V5_STAGE_B_STATE"],
        "cold_load_pass": cold_load["pass"],
        "false_evidence_entry_rate_on_none": metrics[
            "false_evidence_entry_rate_on_none"
        ],
        "family_emission_precision": metrics.get("family_emission_precision"),
        "floors": {
            "minimum_family_score": FROZEN_MINIMUM_FAMILY_SCORE,
            "minimum_top1_top2_margin": FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
        },
        "gating_pass": metrics["gating"]["pass"],
        "integration_pass": integration["pass"],
        "n_index_records": 948,
        "n_validation": len(score_rows),
        "round_trip_pass": round_trip["pass"],
        "sealed": receipt["freeze_state"]["sealed"],
        "selective_accuracy": metrics.get("selective_accuracy"),
        "stale_audit_pass": audit["pass"],
        "thresholds": {"relation": 0.60, "resolvability": 0.75},
    }

    write_private(PRIVATE / "SEAL_PACKAGE_RECEIPT.json", receipt)
    write_private(PRIVATE / "SUMMARY.json", summary)
    write_private(PRIVATE / "DEPENDENCY_MANIFEST.json", manifest)
    write_private(PRIVATE / "PACKAGE_CONTRACT.json", contract)
    write_private(PRIVATE / "INTEGRATION_METRICS.json", metrics)
    write_private(PRIVATE / "STALE_AUDIT.json", stale_sealed)
    write_private(PRIVATE / "COLD_LOAD.json", cold_load)
    write_private(PRIVATE / "ROUND_TRIP.json", round_trip)

    write_repo(REPO_ART / "seal_package_receipt.json", receipt)
    write_repo(REPO_ART / "SUMMARY.json", summary)
    write_repo(REPO_ART / "dependency_manifest.json", manifest)
    write_repo(REPO_ART / "package_contract.json", contract)
    write_repo(REPO_ART / "integration_metrics.json", {
        "metrics": metrics,
        "validation": integration,
    })
    write_repo(REPO_ART / "stale_audit.json", stale_sealed)
    write_repo(REPO_ART / "cold_load.json", cold_load)
    write_repo(REPO_ART / "round_trip.json", round_trip)
    write_repo(REPO_ART / "package_config.json", package_config)

    write_repo(
        SPEC / "classification-v5-stage-a-b-v1r2-seal-package-receipt-20261001.json",
        receipt,
    )
    write_repo(
        SPEC / "classification-v5-stage-a-b-v1r2-dependency-manifest-20261001.json",
        manifest,
    )
    write_repo(
        SPEC / "classification-v5-stale-reference-audit-20261001.json",
        stale_sealed,
    )
    write_repo(
        SPEC / "classification-v5-stage-a-b-v1r2-seal-package-20261001.md",
        f"""# SEAL_AND_PACKAGE_HYPERLEX_V5_STAGE_A_B_V1R2_PIPELINE

```text
V5_STAGE_A_STATE = {summary['V5_STAGE_A_STATE']}
V5_STAGE_B_STATE = {summary['V5_STAGE_B_STATE']}
V5_STAGE_A_B_PIPELINE_STATE = {summary['V5_STAGE_A_B_PIPELINE_STATE']}
PIPELINE = {summary['PIPELINE_ID']}
STAGE_A_BEST = {STAGE_A_BEST_SHA}
MODEL_WIDE_BEST = {BEST_SHA}
STAGE_B_INDEX = {INDEX_SHA}
floors = {FROZEN_MINIMUM_FAMILY_SCORE} / {FROZEN_MINIMUM_TOP1_TOP2_MARGIN}
thresholds = 0.60 / 0.75
false_entry = {metrics['false_evidence_entry_rate_on_none']}
family_precision = {metrics.get('family_emission_precision')}
selective_accuracy = {metrics.get('selective_accuracy')}
cold_load = {cold_load['pass']}
integration = {integration['pass']}
round_trip = {round_trip['pass']}
stale_audit = {audit['pass']}
MANIFEST = {summary['PIPELINE_DEPENDENCY_MANIFEST_SHA256']}
RECEIPT = {summary['SEAL_PACKAGE_RECEIPT_SHA256']}
NEXT_ACTION = {summary['NEXT_ACTION']}
```

Historical V1R9 Stage-B retained. Reserve unscored. No train / retune / index rebuild.
""",
    )

    # Refresh hf-package card fragment.
    from hyperlexical.classification_v5_seal_and_package import hf_card_section

    write_repo(
        SPEC / "hf-package" / "V5_PIPELINE_CARD_FRAGMENT.md",
        hf_card_section(),
    )

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if receipt["freeze_state"]["sealed"] else 2


def main() -> int:
    if os.environ.get("HLX_V5_SEAL_PACKAGE_INNER") == "1":
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
        "HLX_V5_SEAL_PACKAGE_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={revision}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(
            REPO
            / "scripts/spark/run_classification_v5_seal_and_package_pipeline.py"
        ),
    ]
    log = PRIVATE / "seal_console.log"
    with log.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(cmd, check=False, stdout=handle, stderr=subprocess.STDOUT)
    try:
        print(log.read_text(encoding="utf-8")[-12000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
