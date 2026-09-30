"""Build forward 18-family prototype witness for TRAIN_CLASSIFICATION_V2.

Uses HLX_V2_FORWARD_ONTOLOGY=1. social-evaluation is semantic-prototyped from
merged training definitions (no silent predecessor row claim). Does not train,
score the reserve, or move BEST.
"""

from __future__ import annotations

import hashlib
import json
import os
import struct
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
EXPORT = Path(
    "/home/morpheus/hlx-private/classification-v2-train-forward-20260930/civilian.v0.7.hub.jsonl"
)
OUT = Path(
    "/home/morpheus/hlx-private/classification-v2-train-forward-20260930/PROTOTYPE_WITNESS.json"
)
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_CONFIG = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/config.json"
)
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
HUB_SHA = "96a0587c06fac352872e462445f2eaaf773e35a48ab4c987e267b479cab72a83"
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
MAX_LEN = 64

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


def _f32_list(values) -> list[float]:
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


def build_once(tok, encoder, labels, weight, bias, sources: dict) -> dict:
    from hyperlexical.classification_v2_prototype import assemble_initialization

    return assemble_initialization(labels, weight, bias, encode_sources(tok, encoder, sources))


def inner() -> int:
    import torch
    from safetensors.torch import load_file
    from transformers import AutoModel, AutoTokenizer

    from hyperlexical.classification_v2 import (
        ACTIVE_FAMILY_VOCABULARY,
        FORWARD_ONTOLOGY,
        EXACT_COPY_FAMILIES,
        map_family_rows,
    )
    from hyperlexical.classification_v2_prototype import (
        assess_witness,
        training_prototype_sources,
        verify_witness_against_copy,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.save_pretrained import split_weight_tensors

    if not FORWARD_ONTOLOGY:
        fail("HLX_V2_FORWARD_ONTOLOGY must be enabled")
    if len(ACTIVE_FAMILY_VOCABULARY) != 18:
        fail(f"forward vocab width {len(ACTIVE_FAMILY_VOCABULARY)}")
    if "social-evaluation" not in ACTIVE_FAMILY_VOCABULARY:
        fail("social-evaluation missing from forward vocab")
    if "social-evaluation" in EXACT_COPY_FAMILIES:
        fail("social-evaluation must not exact-copy a predecessor row")
    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if not EXPORT.is_file():
        fail(f"missing forward export: {EXPORT}")

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
    encoder.eval()
    for parameter in encoder.parameters():
        parameter.requires_grad = False
    classify_weight = split["classify"]["weight"].detach().cpu().tolist()
    classify_bias = split["classify"]["bias"].detach().cpu().tolist()
    rows = [json.loads(line) for line in EXPORT.read_text(encoding="utf-8").splitlines() if line.strip()]
    sources = training_prototype_sources(rows)
    copy_names = set(EXACT_COPY_FAMILIES)
    sources = {family: payload for family, payload in sources.items() if family not in copy_names}
    missing = [family for family in ACTIVE_FAMILY_VOCABULARY if family not in copy_names and family not in sources]
    if missing:
        fail(f"prototype sources missing: {missing}")
    first = build_once(tok, encoder, labels, classify_weight, classify_bias, sources)
    second = build_once(tok, encoder, labels, classify_weight, classify_bias, sources)
    if first["witness_sha256"] != second["witness_sha256"]:
        fail("FAMILY_PROTOTYPE_UNAVAILABLE nondeterministic")
    se_row = next(row for row in first["rows"] if row["family"] == "social-evaluation")
    if se_row.get("mode") == "EXACT_COPY":
        fail("social-evaluation silently inherited a legacy row")
    tokenizer_config = TRUNK / "tokenizer_config.json"
    witness = {
        **first,
        "best_sha256": BEST_SHA,
        "build_sha256": [first["witness_sha256"], second["witness_sha256"]],
        "determinism": "pass",
        "encoder_tensors_loaded": applied["loaded"],
        "forward_ontology": True,
        "hub_boundary_sha256": HUB_SHA,
        "jev": "OFF",
        "max_len": MAX_LEN,
        "padding_side": "right",
        "pooling": "last_hidden_state[:, 0]",
        "schema": "hyperlex.classification.v2.prototype_witness.v1",
        "tokenizer_config_sha256": sha256_file(tokenizer_config),
        "trunk": str(TRUNK),
        "warm_start": str(BEST_WEIGHTS.parent),
    }
    verify_witness_against_copy(
        map_family_rows(labels, classify_weight, classify_bias),
        witness,
    )
    report = assess_witness(witness)
    if not report["pass"]:
        fail(f"witness assessment failed: {report}")
    OUT.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    OUT.write_text(json.dumps(witness, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(OUT, 0o644)
    reloaded = assess_witness(json.loads(OUT.read_text(encoding="utf-8")))
    if not reloaded["pass"] or reloaded["witness_sha256"] != first["witness_sha256"]:
        fail("witness did not round-trip")
    print(
        json.dumps(
            {
                "determinism": "pass",
                "encoder_tensors_loaded": applied["loaded"],
                "exact_copy_families": first["exact_copy_families"],
                "forward_ontology": True,
                "prototype_families": first["prototype_families"],
                "social_evaluation_mode": se_row.get("mode"),
                "target_norm": first["target_norm"],
                "witness_sha256": first["witness_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def outer() -> int:
    if OUT.exists():
        fail(f"witness already exists: {OUT}")
    script = Path(__file__).resolve()
    command = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "--name",
        "hlx-v2-forward-prototypes",
        "-v",
        f"{REPO}:{REPO}",
        "-v",
        "/home/morpheus/hlx-private:/home/morpheus/hlx-private",
        "-v",
        "/home/morpheus/.hyperlex:/home/morpheus/.hyperlex",
        "-e",
        "HLX_V2_FORWARD_ONTOLOGY=1",
        "-e",
        f"PYTHONPATH={REPO}/scripts/shadow",
        "-e",
        "HOME=/home/morpheus",
        "-e",
        "HF_HUB_OFFLINE=1",
        "-e",
        "TRANSFORMERS_OFFLINE=1",
        "-e",
        "PYTHONUNBUFFERED=1",
        "-w",
        str(REPO),
        IMAGE,
        "python3",
        "-u",
        str(script),
        "--inner",
    ]
    print("launching docker forward prototype build", flush=True)
    return subprocess.call(command)


if __name__ == "__main__":
    if "--inner" in sys.argv:
        raise SystemExit(inner())
    raise SystemExit(outer())
