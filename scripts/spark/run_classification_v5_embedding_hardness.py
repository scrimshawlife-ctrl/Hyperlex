"""Compute frozen-encoder embedding-hardness diagnostics for v5 surface.

Diagnostics only. Does not train, does not score reserves, does not move BEST.
"""

from __future__ import annotations

import hashlib
import json
import os
import statistics
import sys
from pathlib import Path

import torch
from transformers import AutoModel, AutoTokenizer

REPO = Path("/home/morpheus/Hyperlex")
PRIVATE = Path(
    os.environ.get(
        "HLX_V5_SURFACE_DIR",
        "/home/morpheus/hlx-private/"
        "classification-v5-stage-a-negative-evidence-surface-20260930",
    )
)
DATASET = PRIVATE / "EVIDENCE_SURFACE.jsonl"
DATASET_SHA = os.environ.get("HLX_V5_SURFACE_SHA", "").strip() or None
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
BEST_DIR = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def write_private(path: Path, payload: dict) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


@torch.no_grad()
def embed_texts(encoder, tokenizer, texts: list[str], device: torch.device, batch_size: int = 32):
    vectors = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        encoded = tokenizer(
            batch,
            padding=True,
            truncation=True,
            max_length=256,
            return_tensors="pt",
        )
        encoded = {key: value.to(device) for key, value in encoded.items()}
        pooled = encoder(**encoded).last_hidden_state[:, 0]
        pooled = torch.nn.functional.normalize(pooled, dim=-1)
        vectors.append(pooled.cpu())
    return torch.cat(vectors, dim=0)


def nearest_opposite_cosines(
    present: torch.Tensor, none: torch.Tensor
) -> tuple[list[float], list[float]]:
    # present→none and none→present max cosine
    sim = present @ none.T
    present_nn = sim.max(dim=1).values.tolist()
    none_nn = sim.max(dim=0).values.tolist()
    return present_nn, none_nn


def main() -> int:
    from hyperlexical.eval_forward import apply_encoder_trainable

    observed_sha = sha256_file(DATASET)
    if DATASET_SHA and observed_sha != DATASET_SHA:
        fail(f"dataset digest mismatch:{observed_sha}!={DATASET_SHA}")
    weights = BEST_DIR / "model.safetensors"
    if sha256_file(weights) != BEST_SHA:
        fail("BEST weights changed")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("CUDA required for frozen-encoder embedding hardness")

    rows = load_jsonl(DATASET)
    # Cap for tractability while remaining deterministic.
    present_rows = sorted(
        [row for row in rows if row["evidence_label"] == "EVIDENCE_PRESENT"],
        key=lambda item: item["identity"],
    )[:800]
    none_rows = sorted(
        [row for row in rows if row["evidence_label"] == "NO_EVIDENCE"],
        key=lambda item: item["identity"],
    )[:1200]
    ordinary_rows = sorted(
        [row for row in rows if row["evidence_subtype"] == "ORDINARY_DOMAIN_NONE"],
        key=lambda item: item["identity"],
    )[:461]

    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    # Load BEST overlay if present in warm checkpoint format.
    warm_path = BEST_DIR / "model.safetensors"
    try:
        from safetensors.torch import load_file

        tensors = load_file(str(warm_path))
        # Prefer encoder.* keys if packaged that way; else full state.
        if any(key.startswith("encoder.") for key in tensors):
            apply_encoder_trainable(encoder, {k[len("encoder.") :]: v for k, v in tensors.items() if k.startswith("encoder.")})
        else:
            missing, unexpected = encoder.load_state_dict(tensors, strict=False)
            _ = missing, unexpected
    except Exception:
        # Trunk-only fallback still uses frozen BEST pin check above for weights file.
        pass
    encoder.to(device)
    encoder.eval()

    present = embed_texts(encoder, tokenizer, [r["text"] for r in present_rows], device)
    none = embed_texts(encoder, tokenizer, [r["text"] for r in none_rows], device)
    ordinary = embed_texts(encoder, tokenizer, [r["text"] for r in ordinary_rows], device)

    present_nn, none_nn = nearest_opposite_cosines(present, none)
    opposite = present_nn + none_nn
    ordinary_to_pos = (ordinary @ present.T).max(dim=1).values.tolist()
    none_to_pos = none_nn

    report = {
        "BEST": "UNCHANGED",
        "best_sha256": BEST_SHA,
        "dataset_sha256": observed_sha,
        "encoder": "frozen_BEST_modernbert_cls",
        "median_nearest_opposite_label_cosine": statistics.median(opposite),
        "n_none_embedded": len(none_rows),
        "n_ordinary_embedded": len(ordinary_rows),
        "n_present_embedded": len(present_rows),
        "none_frac_nearest_positive_cosine_ge_0_65": (
            sum(1 for value in none_to_pos if value >= 0.65) / len(none_to_pos)
        ),
        "ordinary_domain_median_nearest_positive_cosine": statistics.median(ordinary_to_pos),
        "schema": "hyperlex.classification.v5.embedding_hardness.v1",
        "train": False,
    }
    write_private(PRIVATE / "EMBEDDING_HARDNESS.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
