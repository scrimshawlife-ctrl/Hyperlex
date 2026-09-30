"""Seal multi-anchor family boundaries from training definition text.

Does not train, does not score the evaluation reserve, and does not move BEST.
The single-centroid geometry witness is left untouched.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
EXPORT = Path("/home/morpheus/hlx-private/classification-v2-surface-20260929/civilian.v0.3.jsonl")
EXPORT_SHA = "c4677011ea61f135c8fb82bed9d973dffe3a5db582d34421403e71498c5fd243"
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
OUT = Path("/home/morpheus/hlx-private/classification-v2-boundaries-20260930/FAMILY_SEMANTIC_BOUNDARIES.json")
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/model.safetensors"
)
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
MAX_LEN = 64

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


def _f32_list(values) -> list[float]:
    import struct

    return [struct.unpack("<f", struct.pack("<f", float(value)))[0] for value in values]


def encode_sources(tok, encoder, sources: dict) -> dict[str, list]:
    import torch

    encoded: dict[str, list] = {}
    with torch.no_grad():
        for family, payload in sources.items():
            vectors = []
            for row in payload["rows"]:
                tokens = tok(
                    row["text"],
                    truncation=True,
                    max_length=MAX_LEN,
                    padding=False,
                    return_tensors="pt",
                )
                hidden = encoder(**tokens).last_hidden_state[0, 0].detach().cpu()
                vectors.append(_f32_list(hidden.tolist()))
            encoded[family] = vectors
    return encoded


def members_from(sources: dict, vectors: dict[str, list]) -> dict:
    prepared = {}
    for family, payload in sources.items():
        family_vectors = vectors[family]
        if len(family_vectors) != len(payload["rows"]):
            fail(f"encode width {family}")
        prepared[family] = [
            {
                "class": row["class"],
                "identity": identity,
                "text": str(row["text"]),
                "vector": vector,
                "weight": weight,
            }
            for row, identity, weight, vector in zip(
                payload["rows"],
                payload["identities"],
                payload["weights"],
                family_vectors,
            )
        ]
    return prepared


def inner() -> int:
    import torch
    from safetensors.torch import load_file
    from transformers import AutoModel, AutoTokenizer

    from hyperlexical.classification_v2_boundaries import assemble_boundaries, assess_boundary_artifact
    from hyperlexical.classification_v2_boundaries import boundary_training_sources
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.identity_ledger import IdentityLedger, derived_state
    from hyperlexical.save_pretrained import split_weight_tensors

    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if sha256_file(EXPORT) != EXPORT_SHA:
        fail("surface export changed")
    torch.manual_seed(0)
    try:
        torch.use_deterministic_algorithms(True)
    except Exception:
        pass
    tok = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tok.padding_side = "right"
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    split = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    encoder_map = {}
    for key, value in split["encoder"].items():
        encoder_map[key if key.startswith("encoder.") else f"encoder.{key}"] = value
    applied = apply_encoder_trainable(encoder, encoder_map)
    if applied["loaded"] != 48:
        fail(f"encoder overlay loaded {applied['loaded']} tensors")
    encoder.eval()
    for parameter in encoder.parameters():
        parameter.requires_grad = False
    rows = [json.loads(line) for line in EXPORT.read_text(encoding="utf-8").splitlines() if line.strip()]
    ledger = IdentityLedger.load(LEDGER)
    identity_state = {
        digest: derived_state(record)
        for digest, record in ledger.identities.items()
    }
    collected = boundary_training_sources(rows, identity_state)
    sources = collected["sources"]

    def once():
        return assemble_boundaries(members_from(sources, encode_sources(tok, encoder, sources)))

    first = once()
    second = once()
    if (
        first["anchor_witness_sha256"] != second["anchor_witness_sha256"]
        or first["separation_sha256"] != second["separation_sha256"]
        or first["boundary_sha256"] != second["boundary_sha256"]
    ):
        fail("FAMILY_BOUNDARY_UNAVAILABLE nondeterministic")
    first["best_sha256"] = BEST_SHA
    first["encoder_tensors_loaded"] = applied["loaded"]
    first["excluded_identities"] = collected["excluded_identities"]
    first["exclusion_count"] = len(collected["excluded_identities"])
    first["max_len"] = MAX_LEN
    first["moves_best"] = False
    first["padding_side"] = "right"
    first["pooling"] = "last_hidden_state[:, 0]"
    first["reserve_scored"] = False
    first["train"] = False
    first["trunk"] = str(TRUNK)
    report = assess_boundary_artifact(first)
    if not report["pass"]:
        fail(f"boundary artifact failed: {report}")
    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    OUT.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    OUT.write_text(json.dumps(first, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(OUT, 0o644)
    reloaded = assess_boundary_artifact(json.loads(OUT.read_text(encoding="utf-8")))
    if not reloaded["pass"] or reloaded["boundary_sha256"] != first["boundary_sha256"]:
        fail("boundary artifact did not round-trip")
    summary = {
        "anchor_counts": {
            family["family"]: {
                "k": family["k"],
                "n": family["n"],
                "support_status": family["support_status"],
            }
            for family in first["families"]
        },
        "anchor_witness_sha256": first["anchor_witness_sha256"],
        "boundary_sha256": first["boundary_sha256"],
        "collisions_at_or_above_0_80": len(first["collisions"]),
        "encoder_tensors_loaded": applied["loaded"],
        "exclusion_count": first["exclusion_count"],
        "nearest_competitors": {
            family: first["nearest_competitors"][family]
            for family in first["nearest_competitors"]
        },
        "separation_sha256": first["separation_sha256"],
        "sparse_families": [
            family["family"] for family in first["families"] if family["support_status"] == "SPARSE"
        ],
        "top_collisions": first["collisions"][:15],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def outer() -> int:
    if OUT.exists():
        fail(f"boundary artifact already exists: {OUT}")
    command = [
        "docker",
        "run",
        "--rm",
        "--name",
        "hlx-v2-boundary-witness",
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
        "CUDA_VISIBLE_DEVICES=",
        "-e",
        "HLX_BOUNDARY_INNER=1",
        IMAGE,
        "python",
        "-u",
        "scripts/spark/build_classification_v2_boundaries.py",
    ]
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(inner() if os.environ.get("HLX_BOUNDARY_INNER") == "1" else outer())
