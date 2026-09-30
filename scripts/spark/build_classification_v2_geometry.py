"""Freeze semantic prototypes for all 19 active families.

Does not train, does not score the evaluation reserve, does not move BEST,
and does not rewrite the earlier prototype witness.
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
BASE = Path("/home/morpheus/hlx-private/classification-v2-prototype-20260929/PROTOTYPE_WITNESS.json")
BASE_SHA = "7faa98239b2d4f39bf722c776543ded9a6c5959646c09c5db1e977cd7e69855d"
OUT = Path("/home/morpheus/hlx-private/classification-v2-geometry-20260930/PROTOTYPE_GEOMETRY.json")
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/model.safetensors"
)
BEST_CONFIG = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/config.json"
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


def encode_sources(tok, encoder, sources: dict) -> dict:
    import torch

    encoded = {}
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
            encoded[family] = {
                "identities": list(payload["identities"]),
                "inferred": payload["inferred"],
                "observed": payload["observed"],
                "vectors": vectors,
                "weights": [1.0 if row["class"] == "OBSERVED" else 0.5 for row in payload["rows"]],
            }
    return encoded


def inner() -> int:
    import torch
    from safetensors.torch import load_file
    from transformers import AutoModel, AutoTokenizer

    from hyperlexical.classification_v2 import map_family_rows
    from hyperlexical.classification_v2_prototype import (
        assess_geometry_witness,
        assemble_geometry_witness,
        geometry_training_sources,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.save_pretrained import split_weight_tensors

    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if sha256_file(EXPORT) != EXPORT_SHA:
        fail("surface export changed")
    base = json.loads(BASE.read_text(encoding="utf-8"))
    if base.get("witness_sha256") != BASE_SHA:
        fail("base prototype witness changed")
    torch.manual_seed(0)
    try:
        torch.use_deterministic_algorithms(True)
    except Exception:
        pass
    config = json.loads(BEST_CONFIG.read_text(encoding="utf-8"))
    labels = [config["id2label"][str(index)] for index in range(len(config["id2label"]))]
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
    sources = geometry_training_sources(rows)
    mapped = map_family_rows(
        labels,
        split["classify"]["weight"].detach().cpu().tolist(),
        split["classify"]["bias"].detach().cpu().tolist(),
    )

    def once():
        return assemble_geometry_witness(base, encode_sources(tok, encoder, sources), mapped)

    first = once()
    second = once()
    if first["witness_sha256"] != second["witness_sha256"] or first["geometry_sha256"] != second["geometry_sha256"]:
        fail("FAMILY_PROTOTYPE_UNAVAILABLE nondeterministic")
    first["best_sha256"] = BEST_SHA
    first["build_sha256"] = [first["witness_sha256"], second["witness_sha256"]]
    first["base_prototype_witness_sha256"] = BASE_SHA
    first["determinism"] = "pass"
    first["encoder_tensors_loaded"] = applied["loaded"]
    first["jev"] = "OFF"
    first["max_len"] = MAX_LEN
    first["padding_side"] = "right"
    first["pooling"] = "last_hidden_state[:, 0]"
    first["prototypes"] = "FROZEN"
    first["source_rule"] = "verified_definition_prototypes_plus_exact_copy_training_prose"
    first["trunk"] = str(TRUNK)
    report = assess_geometry_witness(first, mapped)
    if not report["pass"]:
        fail(f"geometry witness failed: {report}")
    OUT.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    OUT.write_text(json.dumps(first, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(OUT, 0o644)
    reloaded = assess_geometry_witness(json.loads(OUT.read_text(encoding="utf-8")), mapped)
    if not reloaded["pass"] or reloaded["geometry_sha256"] != first["geometry_sha256"]:
        fail("geometry witness did not round-trip")
    print(json.dumps({
        "confusion_clusters": first["confusion_clusters"],
        "confusable_pairs": first["confusable_pairs"],
        "encoder_tensors_loaded": applied["loaded"],
        "geometry_sha256": first["geometry_sha256"],
        "hard_negatives": first["hard_negatives"],
        "prototype_source_counts": {
            row["family"]: {
                "inferred": row["inferred_count"],
                "observed": row["observed_count"],
                "source_identity_count": row["source_identity_count"],
            }
            for row in first["rows"]
        },
        "witness_sha256": first["witness_sha256"],
    }, indent=2, sort_keys=True))
    return 0


def outer() -> int:
    if OUT.exists():
        fail(f"geometry witness already exists: {OUT}")
    if not BASE.is_file():
        fail("base prototype witness missing")
    command = [
        "docker",
        "run",
        "--rm",
        "--name",
        "hlx-v2-geometry-witness",
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
        "HLX_GEOMETRY_INNER=1",
        IMAGE,
        "python",
        "-u",
        "scripts/spark/build_classification_v2_geometry.py",
    ]
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(inner() if os.environ.get("HLX_GEOMETRY_INNER") == "1" else outer())
