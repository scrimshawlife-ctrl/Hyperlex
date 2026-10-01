"""RETRY_PROMOTE_STAGE_A_IDENT_FILTERED_FACTORIZED_CANDIDATE — REPRO STAGE_A_BEST.

Promotes the complete REPRO-001 checkpoint f2b00c5d…. Never promotes the
historical incomplete 8b2de447…. Does not retrain, alter thresholds/V1R2,
score spent reserve, or mutate MODEL_WIDE_BEST.
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
ANNOTATIONS = SURFACE / "FACTORIZED_ANNOTATIONS.jsonl"
EXCLUSION = SURFACE / "EXCLUSION_MANIFEST.jsonl"
DATASET_SHA = "492ed36751c7fdc40fe10bcdfabb69fa8783f8680259c31b3a64ee6903326d73"
ANNOTATION_SHA = (
    "95d5436555da33ef7aaccf4c32194c29f00caced9a17adf2d2f65f12db7dc1fc"
)
EXCLUSION_SHA = (
    "661c9edb095f7f7dc28a24256b42e0a2796f9ab78fbabc24b23cf9bd57b06d69"
)
AUTH_DEST = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-ident-filtered-factorized-repro-v1-20261001"
)
RUN_ROOT = AUTH_DEST / "classification-v5-stage-a-ident-filtered-factorized-repro-001"
SELECTED = RUN_ROOT / "selected" / "model.safetensors"
TRAIN_RECEIPT = RUN_ROOT / "RUN_RECEIPT.json"
PUBLIC_TRAIN_RECEIPT = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-REPRO-001"
    / "train_once_receipt.json"
)
SELECTED_PUBLISHED = Path(
    "/home/morpheus/.hyperlex/models/"
    "hyperlex-encoder-modernbert-base-seed-classification-v5-stage-a-ident-filtered-factorized-repro-001"
)
INCOMPLETE_HISTORICAL = (
    "8b2de4472dc0ebd65a6b4b7577dc3272d63db2490a1b6f6dbbcc54db50077e41"
)
PREVIOUS_PUBLISHED = Path(
    "/home/morpheus/.hyperlex/models/"
    "hyperlex-encoder-modernbert-base-seed-classification-v5-stage-a-two-stage-001"
)
PROMOTE_DEST = AUTH_DEST / "promotion"
MODELS = Path("/home/morpheus/.hyperlex/models")
BEST_LINK = MODELS / "BEST"
BEST_PATH_FILE = MODELS / "BEST.path"
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
PREVIOUS_STAGE_A_BEST_SHA = (
    "cd2829c1b5fb823fc03f18efe66a7387124ef44be2545b9e385a17eb6237bf5c"
)
STAGE_A_BEST_LINK = MODELS / "STAGE_A_BEST"
STAGE_A_BEST_PATH_FILE = MODELS / "STAGE_A_BEST.path"
STAGE_A_BEST_POINTER = MODELS / "STAGE_A_BEST.json"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
REPO_ARTIFACTS = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-REPRO-001"
)
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


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except PermissionError:
        completed = subprocess.run(
            ["sudo", "-n", "cat", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(completed.stdout)


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
        completed = subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def read_previous_stage_a_best() -> str | None:
    if STAGE_A_BEST_POINTER.exists():
        try:
            payload = load_json(STAGE_A_BEST_POINTER)
            return payload.get("STAGE_A_BEST") or payload.get("checkpoint_sha256")
        except (OSError, json.JSONDecodeError):
            pass
    return None


def install_stage_a_best_pointer(pointer: dict) -> None:
    """Create STAGE_A_BEST symlink + path file. Never touch model-wide BEST."""
    target = SELECTED_PUBLISHED
    if not (target / "model.safetensors").exists():
        fail(f"published_selected_missing:{target}")
    if sudo_sha256(target / "model.safetensors") != pointer["checkpoint_sha256"]:
        fail("published_selected_sha_mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mutated_during_promotion")

    if STAGE_A_BEST_LINK.exists() or STAGE_A_BEST_LINK.is_symlink():
        STAGE_A_BEST_LINK.unlink()
    STAGE_A_BEST_LINK.symlink_to(target)
    STAGE_A_BEST_PATH_FILE.write_text(str(target) + "\n", encoding="utf-8")
    os.chmod(STAGE_A_BEST_PATH_FILE, 0o644)
    write_private(STAGE_A_BEST_POINTER, pointer)
    write_repo(MODELS / "STAGE_A_BEST.public.json", pointer)


def restore_previous_pointer(previous: str | None) -> None:
    """Restore superseded two-stage STAGE_A_BEST on promotion invalidation."""
    if previous != PREVIOUS_STAGE_A_BEST_SHA:
        fail(f"cannot_auto_restore_unexpected_previous:{previous}")
    if not (PREVIOUS_PUBLISHED / "model.safetensors").exists():
        fail("previous_published_missing")
    if sudo_sha256(PREVIOUS_PUBLISHED / "model.safetensors") != PREVIOUS_STAGE_A_BEST_SHA:
        fail("previous_published_sha_mismatch")
    if STAGE_A_BEST_LINK.exists() or STAGE_A_BEST_LINK.is_symlink():
        STAGE_A_BEST_LINK.unlink()
    STAGE_A_BEST_LINK.symlink_to(PREVIOUS_PUBLISHED)
    STAGE_A_BEST_PATH_FILE.write_text(str(PREVIOUS_PUBLISHED) + "\n", encoding="utf-8")
    # Leave STAGE_A_BEST.json as last-good two-stage pointer content if present;
    # rewrite a minimal restore marker.
    restore_pointer = {
        "STAGE_A_BEST": PREVIOUS_STAGE_A_BEST_SHA,
        "checkpoint_sha256": PREVIOUS_STAGE_A_BEST_SHA,
        "restored_after_invalid_promotion": True,
        "weights_path": str(PREVIOUS_PUBLISHED / "model.safetensors"),
    }
    write_private(STAGE_A_BEST_POINTER, restore_pointer)
    write_repo(MODELS / "STAGE_A_BEST.public.json", restore_pointer)


def cold_load_via_canonical_path(*, prefer_published_selected: bool = False) -> dict:
    """Load: trunk → MODEL_WIDE_BEST → STAGE_A_BEST factorized heads.

    Before pointer mutation, pass prefer_published_selected=True so the
    candidate weights are loaded (current STAGE_A_BEST still points at the
    superseded two-stage checkpoint).
    """
    import torch
    from torch import nn
    from transformers import AutoModel, AutoTokenizer
    from safetensors.torch import load_file

    from hyperlexical.classification_v5_stage_a import canonical_json, sha256_text
    from hyperlexical.classification_v5_stage_a_ident_filtered_repro_promote import (
        CANONICAL_RELATION_THRESHOLD,
        CANONICAL_RESOLVABILITY_THRESHOLD,
        STAGE_A_BEST_SHA256,
        decide_canonical_stage_a,
        post_promotion_replay_check,
        verify_canonical_overlay,
        verify_head_completeness,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.layout import HIDDEN, MAX_LEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors

    if prefer_published_selected:
        candidates = (
            SELECTED_PUBLISHED / "model.safetensors",
            SELECTED,
            STAGE_A_BEST_LINK / "model.safetensors",
        )
    else:
        candidates = (
            STAGE_A_BEST_LINK / "model.safetensors",
            SELECTED_PUBLISHED / "model.safetensors",
            SELECTED,
        )
    stage_a_weights = next((p for p in candidates if p.exists()), None)
    if stage_a_weights is None:
        fail("stage_a_weights_missing")

    try:
        ckpt_sha = sha256_file(stage_a_weights)
    except PermissionError:
        ckpt_sha = sudo_sha256(stage_a_weights)
    if ckpt_sha != STAGE_A_BEST_SHA256:
        fail(f"stage_a_best_sha_mismatch:{ckpt_sha}")
    if ckpt_sha == INCOMPLETE_HISTORICAL:
        fail("refusing_incomplete_historical_8b2de447")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mutated_before_canonical_load")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("promotion cold-load requires CUDA")

    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tokenizer.padding_side = "right"
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    relation_head = nn.Linear(HIDDEN, 2)
    resolvability_head = nn.Linear(HIDDEN, 2)

    best_split = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    best_loaded = apply_encoder_trainable(encoder, best_split.get("encoder") or {})
    if best_loaded["loaded"] != 48:
        fail(f"BEST_encoder_overlay_incomplete:{best_loaded['loaded']}")

    tensors = load_file(str(stage_a_weights), device="cpu")
    tensor_keys = list(tensors.keys())
    head_completeness = verify_head_completeness(tensor_keys)
    if not head_completeness["pass"]:
        fail(
            "head_completeness_fail:"
            + json.dumps(head_completeness, sort_keys=True)
        )
    overlay = verify_canonical_overlay(
        parent_best_sha256=BEST_SHA,
        stage_a_tensor_keys=tensor_keys,
    )
    if not overlay["pass"]:
        fail(f"canonical_overlay_fail:{json.dumps(overlay['checks'], sort_keys=True)}")
    if any(k.startswith("evidence_head.") for k in tensor_keys):
        fail("flat_evidence_head_present_in_canonical_load")
    if any(k.startswith("gate1_head.") for k in tensor_keys) or any(
        k.startswith("gate2_head.") for k in tensor_keys
    ):
        fail("legacy_two_stage_heads_present_in_canonical_load")

    split = split_weight_tensors(tensors)
    loaded = apply_encoder_trainable(encoder, split.get("encoder") or {})
    if loaded["loaded"] != 12:
        fail(f"stage_a_overlay_incomplete:{loaded['loaded']}")
    freeze_encoder(encoder, last_trainable=2)
    with torch.no_grad():
        relation_head.weight.copy_(split["relation_head"]["weight"])
        relation_head.bias.copy_(split["relation_head"]["bias"])
        resolvability_head.weight.copy_(split["resolvability_head"]["weight"])
        resolvability_head.bias.copy_(split["resolvability_head"]["bias"])

    encoder.to(device)
    relation_head.to(device)
    resolvability_head.to(device)
    encoder.eval()
    relation_head.eval()
    resolvability_head.eval()

    rows = [r for r in load_jsonl(DATASET) if r.get("split") == "validation"]
    golds, p_rel, p_res = [], [], []
    decisions, rel_logits, res_logits = [], [], []
    max_len = int(MAX_LEN)

    def softmax2(logits):
        import torch.nn.functional as F

        return F.softmax(torch.tensor(logits, dtype=torch.float32), dim=-1).tolist()

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
            pooled = encoder(**encoded).last_hidden_state[:, 0]
            rel_raw = relation_head(pooled)[0].detach().cpu().tolist()
            res_raw = resolvability_head(pooled)[0].detach().cpu().tolist()
            rel_probs = softmax2(rel_raw)
            res_probs = softmax2(res_raw)
            decision = decide_canonical_stage_a(
                p_relation=float(rel_probs[1]),
                p_resolvable=float(res_probs[1]),
            )
            golds.append(str(row["evidence_label"]))
            p_rel.append(float(rel_probs[1]))
            p_res.append(float(res_probs[1]))
            decisions.append(decision)
            rel_logits.append([float(x) for x in rel_raw])
            res_logits.append([float(x) for x in res_raw])

    replay = post_promotion_replay_check(
        golds=golds, p_relation=p_rel, p_resolvable=p_res, rows=rows
    )
    head_manifest = {
        k: sha256_text(canonical_json([float(x) for x in tensors[k].reshape(-1).tolist()[:8]]))
        for k in (
            "relation_head.weight",
            "relation_head.bias",
            "resolvability_head.weight",
            "resolvability_head.bias",
        )
    }
    # Full-tensor hashes for factorized heads (serialization defect closure).
    for k in list(head_manifest):
        digest = hashlib.sha256()
        digest.update(tensors[k].detach().cpu().contiguous().numpy().tobytes())
        head_manifest[k] = digest.hexdigest()
    tensor_manifest_hash = sha256_text(canonical_json(sorted(tensor_keys)))
    replay["overlay"] = overlay
    replay["head_completeness"] = head_completeness
    replay["factorized_head_manifest_hashes"] = head_manifest
    replay["checkpoint_tensor_manifest_hash"] = tensor_manifest_hash
    replay["n_validation"] = len(rows)
    replay["stage_a_best_sha256"] = ckpt_sha
    replay["decisions"] = decisions
    replay["relation_logits"] = rel_logits
    replay["resolvability_logits"] = res_logits
    replay["thresholds"] = {
        "relation_threshold": CANONICAL_RELATION_THRESHOLD,
        "resolvability_threshold": CANONICAL_RESOLVABILITY_THRESHOLD,
    }
    return replay


def inner() -> int:
    from safetensors import safe_open

    from hyperlexical.classification_v5_stage_a_ident_filtered_repro_promote import (
        STAGE_A_BEST_SHA256,
        build_promotion_receipt,
        build_stage_a_best_pointer,
        preflight_promotion,
        round_trip_logit_parity,
        utc_now_iso,
    )

    for path in (
        DATASET,
        ANNOTATIONS,
        EXCLUSION,
        BEST_WEIGHTS,
        SELECTED_PUBLISHED / "model.safetensors",
    ):
        if not path.exists():
            fail(f"missing_required_artifact:{path}")

    # Selected may be root-owned; prefer published digest + private receipt.
    if SELECTED.exists():
        selected_sha = (
            sha256_file(SELECTED)
            if SELECTED.stat().st_uid == os.getuid()
            else sudo_sha256(SELECTED)
        )
    else:
        selected_sha = sudo_sha256(SELECTED_PUBLISHED / "model.safetensors")

    if sha256_file(DATASET) != DATASET_SHA:
        fail("dataset_digest_mismatch")
    if sha256_file(ANNOTATIONS) != ANNOTATION_SHA:
        fail("annotation_digest_mismatch")
    if sha256_file(EXCLUSION) != EXCLUSION_SHA:
        fail("exclusion_digest_mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mutated_preflight")
    if selected_sha != STAGE_A_BEST_SHA256:
        fail(f"selected_sha_mismatch:{selected_sha}")
    if selected_sha == INCOMPLETE_HISTORICAL:
        fail("refusing_incomplete_historical_8b2de447")
    if sudo_sha256(SELECTED_PUBLISHED / "model.safetensors") != STAGE_A_BEST_SHA256:
        fail("published_selected_sha_mismatch")

    if TRAIN_RECEIPT.exists():
        train_receipt = load_json(TRAIN_RECEIPT)
    elif PUBLIC_TRAIN_RECEIPT.exists():
        train_receipt = load_json(PUBLIC_TRAIN_RECEIPT)
    else:
        fail("train_receipt_missing")

    previous = read_previous_stage_a_best()
    if previous != PREVIOUS_STAGE_A_BEST_SHA:
        fail(f"current_STAGE_A_BEST_unexpected:{previous}")
    if sudo_sha256(PREVIOUS_PUBLISHED / "model.safetensors") != PREVIOUS_STAGE_A_BEST_SHA:
        fail("previous_STAGE_A_BEST_weights_mismatch")

    with safe_open(str(SELECTED_PUBLISHED / "model.safetensors"), framework="pt") as handle:
        tensor_keys = list(handle.keys())

    preflight = preflight_promotion(
        train_receipt=train_receipt,
        selected_checkpoint_sha256=selected_sha,
        model_wide_best_sha256=BEST_SHA,
        current_stage_a_best_sha256=previous,
        dataset_sha256=DATASET_SHA,
        annotation_sha256=ANNOTATION_SHA,
        exclusion_manifest_sha256=EXCLUSION_SHA,
        v1r2_mutated=False,
        stage_a_tensor_keys=tensor_keys,
    )
    PROMOTE_DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not preflight["pass"]:
        write_private(PROMOTE_DEST / "PREFLIGHT_FAIL.json", preflight)
        print(json.dumps(preflight, indent=2, sort_keys=True))
        return 2

    promoted_at = utc_now_iso()
    revision = code_revision()
    pointer = build_stage_a_best_pointer(
        weights_path=str(SELECTED_PUBLISHED / "model.safetensors"),
        previous_stage_a_best=previous,
        code_revision=revision,
        promoted_at=promoted_at,
    )

    # Pre-mutation cold-load — fail closed to PROMOTION_INVALID (do not mutate pointer).
    try:
        pre_replay = cold_load_via_canonical_path(prefer_published_selected=True)
    except SystemExit as exc:
        overlay_fail = {
            "pass": False,
            "checks": {
                "cold_load_exception": True,
                "required_factorized_heads_present": False,
            },
            "architecture": {
                "pass": False,
                "note": "pre_mutation_cold_load_failed_for_repro_candidate",
            },
        }
        receipt = build_promotion_receipt(
            preflight=preflight,
            pointer=pointer,
            overlay=overlay_fail,
            post_replay={
                "pass": False,
                "metrics": {},
                "replay_hash": None,
                "reason": "pre_mutation_cold_load_failed",
                "exit_code": int(getattr(exc, "code", 2) or 2),
            },
            previous_stage_a_best=previous,
            code_revision=revision,
            promoted_at=promoted_at,
            head_completeness=preflight.get("head_completeness"),
        )
        write_private(PROMOTE_DEST / "PROMOTION_INVALID.json", receipt)
        write_private(AUTH_DEST / "STAGE_A_PROMOTION.json", receipt)
        write_repo(REPO_ARTIFACTS / "stage_a_promotion_receipt.json", receipt)
        write_repo(
            SPEC_DIR
            / "classification-v5-stage-a-ident-filtered-factorized-repro-promotion-receipt-20261001.json",
            receipt,
        )
        summary = {
            "STAGE_A_PROMOTION": "PROMOTION_INVALID",
            "PROMOTION_INVALID": True,
            "STAGE_A_BEST": previous,
            "PREVIOUS_STAGE_A_BEST": previous,
            "MODEL_WIDE_BEST": BEST_SHA,
            "MODEL_WIDE_BEST_MUTATED": False,
            "PROMOTION_LOADABLE": False,
            "RESERVE_CONSUMED": False,
            "reason": "pre_mutation_cold_load_failed",
            "NEXT_ACTION": "PROMOTION_INVALID",
            "STAGE_A_PROMOTION_RECEIPT_SHA256": receipt[
                "STAGE_A_PROMOTION_RECEIPT_SHA256"
            ],
            "TRAIN": False,
        }
        write_private(PROMOTE_DEST / "SUMMARY.json", summary)
        write_repo(REPO_ARTIFACTS / "stage_a_promotion_summary.json", summary)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 2

    if not pre_replay["pass"]:
        fail(f"pre_mutation_cold_load_fail:{pre_replay.get('replay_hash')}")

    install_stage_a_best_pointer(pointer)

    post_replay = cold_load_via_canonical_path()
    overlay = post_replay.pop("overlay")
    head_completeness = post_replay.pop("head_completeness", None)
    head_manifest = post_replay.pop("factorized_head_manifest_hashes", None)
    tensor_manifest_hash = post_replay.pop("checkpoint_tensor_manifest_hash", None)
    post_decisions = post_replay.pop("decisions")
    post_rel_logits = post_replay.pop("relation_logits")
    post_res_logits = post_replay.pop("resolvability_logits")

    # Round-trip: save already persisted; cold-load again and compare logits.
    round_trip_replay = cold_load_via_canonical_path()
    for ephemeral in (
        "overlay",
        "head_completeness",
        "factorized_head_manifest_hashes",
        "checkpoint_tensor_manifest_hash",
    ):
        round_trip_replay.pop(ephemeral, None)
    rt_decisions = round_trip_replay.pop("decisions")
    rt_rel = round_trip_replay.pop("relation_logits")
    rt_res = round_trip_replay.pop("resolvability_logits")
    combined_logits_a = [a + b for a, b in zip(post_rel_logits, post_res_logits)]
    combined_logits_b = [a + b for a, b in zip(rt_rel, rt_res)]
    round_trip = round_trip_logit_parity(
        decisions_a=post_decisions,
        decisions_b=rt_decisions,
        logits_a=combined_logits_a,
        logits_b=combined_logits_b,
    )
    # Also parity vs pre-mutation cold-load (same weights, different pointer path).
    pre_decisions = pre_replay.get("decisions") or []
    pre_rel = pre_replay.get("relation_logits") or []
    pre_res = pre_replay.get("resolvability_logits") or []
    pre_vs_post = round_trip_logit_parity(
        decisions_a=pre_decisions,
        decisions_b=post_decisions,
        logits_a=[a + b for a, b in zip(pre_rel, pre_res)],
        logits_b=combined_logits_a,
    )
    round_trip["pre_vs_post_pointer"] = pre_vs_post
    if not pre_vs_post["pass"]:
        round_trip["pass"] = False

    if not post_replay["pass"] or not round_trip["pass"]:
        restore_previous_pointer(previous)
        receipt = build_promotion_receipt(
            preflight=preflight,
            pointer=pointer,
            overlay=overlay,
            post_replay=post_replay,
            previous_stage_a_best=previous,
            code_revision=revision,
            promoted_at=promoted_at,
            head_completeness=head_completeness,
            round_trip=round_trip,
            factorized_head_manifest_hashes=head_manifest,
            checkpoint_tensor_manifest_hash=tensor_manifest_hash,
        )
        write_private(PROMOTE_DEST / "PROMOTION_INVALID.json", receipt)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 2

    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mutated_after_promotion")
    expected_best_path = str(
        Path(
            "/home/morpheus/.hyperlex/models/"
            "hyperlex-encoder-modernbert-base-seed-select004"
        )
    )
    if BEST_PATH_FILE.exists() and BEST_PATH_FILE.read_text(encoding="utf-8").strip() != expected_best_path:
        fail("BEST_path_mutated")

    receipt = build_promotion_receipt(
        preflight=preflight,
        pointer=pointer,
        overlay=overlay,
        post_replay=post_replay,
        previous_stage_a_best=previous,
        code_revision=revision,
        promoted_at=promoted_at,
        head_completeness=head_completeness,
        round_trip=round_trip,
        factorized_head_manifest_hashes=head_manifest,
        checkpoint_tensor_manifest_hash=tensor_manifest_hash,
    )
    write_private(PROMOTE_DEST / "STAGE_A_BEST.json", pointer)
    write_private(PROMOTE_DEST / "STAGE_A_PROMOTION.json", receipt)
    write_private(PROMOTE_DEST / "POST_PROMOTION_REPLAY.json", post_replay)
    write_private(PROMOTE_DEST / "ROUND_TRIP.json", round_trip)
    write_private(AUTH_DEST / "STAGE_A_PROMOTION.json", receipt)
    write_repo(REPO_ARTIFACTS / "stage_a_best_pointer.json", pointer)
    write_repo(REPO_ARTIFACTS / "stage_a_promotion_receipt.json", receipt)
    write_repo(REPO_ARTIFACTS / "stage_a_post_promotion_replay.json", post_replay)
    write_repo(REPO_ARTIFACTS / "stage_a_round_trip_logit_parity.json", round_trip)
    write_repo(
        SPEC_DIR
        / "classification-v5-stage-a-ident-filtered-factorized-repro-promotion-receipt-20261001.json",
        receipt,
    )
    write_repo(
        SPEC_DIR
        / "classification-v5-stage-a-ident-filtered-repro-best-pointer-20261001.json",
        pointer,
    )

    summary = {
        "BEST_MUTATED": False,
        "MODEL_WIDE_BEST": BEST_SHA,
        "MODEL_WIDE_BEST_MUTATED": False,
        "NEXT_ACTION": receipt["NEXT_ACTION"],
        "PREVIOUS_STAGE_A_BEST": previous,
        "PROMOTION_LOADABLE": True,
        "RESERVE_CONSUMED": False,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "STAGE_A_PROMOTION": receipt["STAGE_A_PROMOTION"],
        "STAGE_A_PROMOTION_RECEIPT_SHA256": receipt[
            "STAGE_A_PROMOTION_RECEIPT_SHA256"
        ],
        "TRAIN": False,
        "factorized_heads_cold_loadable": True,
        "n_keys": 16,
        "post_replay_hash": post_replay["replay_hash"],
        "post_replay_pass": post_replay["pass"],
        "round_trip_pass": round_trip["pass"],
        "decision_mismatch_count": round_trip["decision_mismatch_count"],
        "relation_threshold": 0.60,
        "resolvability_threshold": 0.75,
    }
    write_private(PROMOTE_DEST / "SUMMARY.json", summary)
    write_repo(REPO_ARTIFACTS / "stage_a_promotion_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if receipt["STAGE_A_PROMOTION"] == "APPLIED" else 2


def main() -> int:
    if os.environ.get("HLX_V5_STAGE_A_IDENT_FILTERED_REPRO_PROMOTE_INNER") == "1":
        return inner()

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
        "HLX_V5_STAGE_A_IDENT_FILTERED_REPRO_PROMOTE_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={revision}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(
            REPO
            / "scripts/spark/run_classification_v5_stage_a_ident_filtered_repro_promote.py"
        ),
    ]
    print(json.dumps({"launch": cmd[-1], "image": IMAGE}, sort_keys=True), flush=True)
    PROMOTE_DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    log_path = PROMOTE_DEST / "promotion_console.log"
    with log_path.open("w", encoding="utf-8") as log_handle:
        completed = subprocess.run(
            cmd, check=False, stdout=log_handle, stderr=subprocess.STDOUT
        )
    try:
        print(log_path.read_text(encoding="utf-8")[-12000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
