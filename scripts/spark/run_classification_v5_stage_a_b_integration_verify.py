"""Read-only Stage-A → Stage-B integration verify after canonical freeze.

Cold-loads factorized STAGE_A_BEST, confirms frozen Stage-B index/floors,
and checks entry gating. Does not rebuild index, retune floors, or score reserve.
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

STAGE_A_BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/STAGE_A_BEST/model.safetensors"
)
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
STAGE_A_BEST_SHA = (
    "f2b00c5dfeb087288fc1686c901fbc8b52a8ba7a7b51cb83ff038656f93617fa"
)
FROZEN_INDEX = Path(
    "/home/morpheus/hlx-private/classification-v5-stage-b-20260930/STAGE_B_INDEX.json"
)
FROZEN_INDEX_SHA = (
    "3fd6c87a5825f3f2a25a81f1a769a77aa69e03ddca5b370f9247672d93aaee21"
)
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
DEST = Path(
    "/home/morpheus/hlx-private/classification-v5-stage-a-b-integration-20261001"
)
REPO_ART = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V5-STAGE-A-B-PIPELINE-V1"
)

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


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fail(msg: str) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(2)


def inner() -> int:
    import torch
    from torch import nn
    from safetensors.torch import load_file
    from transformers import AutoModel, AutoTokenizer

    from hyperlexical.classification_v5_stage_a_b_pipeline import (
        verify_entry_gating,
        verify_stage_b_parent_and_floors,
    )
    from hyperlexical.classification_v5_stage_a_canonical import (
        decide_canonical_stage_a,
        verify_canonical_checkpoint_keys,
    )
    from hyperlexical.classification_v5_stage_b import (
        FROZEN_INDEX_SHA256,
        FROZEN_MINIMUM_FAMILY_SCORE,
        FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
        stage_b_contract,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.layout import HIDDEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors

    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("MODEL_WIDE_BEST_mismatch")
    if sudo_sha256(STAGE_A_BEST_WEIGHTS) != STAGE_A_BEST_SHA:
        fail("STAGE_A_BEST_mismatch")

    parent = verify_stage_b_parent_and_floors()
    entry = verify_entry_gating()
    if not parent["pass"] or not entry["pass"]:
        fail(json.dumps({"parent": parent, "entry": entry}, sort_keys=True))

    index_payload = json.loads(
        subprocess.run(
            ["sudo", "-n", "cat", str(FROZEN_INDEX)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        if not os.access(FROZEN_INDEX, os.R_OK)
        else FROZEN_INDEX.read_text(encoding="utf-8")
    )
    index_sha = index_payload.get("index_sha256")
    if index_sha != FROZEN_INDEX_SHA or index_sha != FROZEN_INDEX_SHA256:
        fail(f"frozen_index_sha_mismatch:{index_sha}")

    tensors = load_file(str(STAGE_A_BEST_WEIGHTS), device="cpu")
    keys_ok = verify_canonical_checkpoint_keys(list(tensors.keys()))
    if not keys_ok["pass"]:
        fail(f"checkpoint_incomplete:{json.dumps(keys_ok, sort_keys=True)}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("integration verify requires CUDA")

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
    freeze_encoder(encoder, last_trainable=2)
    with torch.no_grad():
        relation_head.weight.copy_(split["relation_head"]["weight"])
        relation_head.bias.copy_(split["relation_head"]["bias"])
        resolvability_head.weight.copy_(split["resolvability_head"]["weight"])
        resolvability_head.bias.copy_(split["resolvability_head"]["bias"])
    encoder.to(device).eval()
    relation_head.to(device).eval()
    resolvability_head.to(device).eval()

    # Smoke: a few strings through canonical decision + Stage-B entry.
    samples = [
        "meme",
        "the discourse around aesthetic capitalism is getting weird",
        "asdf qwerty zxcv",
    ]
    decisions = []
    import torch.nn.functional as F

    with torch.no_grad():
        for text in samples:
            enc = tokenizer(
                [text], padding=True, truncation=True, max_length=256, return_tensors="pt"
            )
            enc = {k: v.to(device) for k, v in enc.items()}
            pooled = encoder(**enc).last_hidden_state[:, 0]
            rel = F.softmax(relation_head(pooled)[0], dim=-1).tolist()
            res = F.softmax(resolvability_head(pooled)[0], dim=-1).tolist()
            decision = decide_canonical_stage_a(
                p_relation=float(rel[1]), p_resolvable=float(res[1])
            )
            decisions.append(
                {
                    "text": text,
                    "decision": decision,
                    "p_relation": float(rel[1]),
                    "p_resolvable": float(res[1]),
                }
            )

    contract = stage_b_contract()
    report = {
        "STAGE_A_BEST": STAGE_A_BEST_SHA,
        "MODEL_WIDE_BEST": BEST_SHA,
        "cold_load_pass": True,
        "factorized_heads_pass": True,
        "n_keys": keys_ok["n_keys"],
        "frozen_index_sha256": index_sha,
        "index_rebuilt": False,
        "floors_retuned": False,
        "minimum_family_score": FROZEN_MINIMUM_FAMILY_SCORE,
        "minimum_top1_top2_margin": FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
        "entry_gating_pass": entry["pass"],
        "parent_pin_pass": parent["pass"],
        "stage_b_contract_stage_a": contract["STAGE_A_BEST"],
        "smoke_decisions": decisions,
        "pass": True,
    }
    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    write_json(DEST / "INTEGRATION_VERIFY.json", report)
    write_json(REPO_ART / "spark_integration_verify.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def main() -> int:
    if os.environ.get("HLX_V5_STAGE_A_B_INTEGRATION_INNER") == "1":
        return inner()
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
        "HLX_V5_STAGE_A_B_INTEGRATION_INNER=1",
        "--entrypoint",
        "python3",
        IMAGE,
        str(
            REPO
            / "scripts/spark/run_classification_v5_stage_a_b_integration_verify.py"
        ),
    ]
    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    log = DEST / "integration_console.log"
    with log.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(cmd, check=False, stdout=handle, stderr=subprocess.STDOUT)
    try:
        print(log.read_text(encoding="utf-8")[-8000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
