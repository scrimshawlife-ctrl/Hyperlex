"""Seal HYPERLEX_ACTIVE_FAMILY_RESIDUAL_HUB_BOUNDARY_PASS_V1.

Applies hub exclusivity KEEP/DROP filtering on the forward merge export, then
reseals the frozen-encoder overlap gate. Keeps SE/RD separate. Does not train,
score the reserve, or move BEST.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
MERGE_DIR = Path("/home/morpheus/hlx-private/classification-v2-ontology-merge-pair-20260930")
MERGE = MERGE_DIR / "ONTOLOGY_MERGE_PAIR.json"
MERGE_SHA = "c901badb70c0c72f1af20fe4dd0b64bcbdfad917568682e9abb2cc9321ad69d5"
EXPORT = MERGE_DIR / "civilian.v0.6.merge.jsonl"
EXPORT_SHA = "a8c064151973d7b2b9f439dc9fab499c69c2dd8a22a19206d7f486d970975130"
RESIDUAL = Path(
    "/home/morpheus/hlx-private/classification-v2-post-merge-residual-review-20260930/"
    "POST_MERGE_RESIDUAL_REVIEW.json"
)
RESIDUAL_SHA = "617ba9eebfe9955ed3931ab659738a25de99b79a7301bc8a6ed5d952439955bc"
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
REPAIR = Path(
    "/home/morpheus/.hyperlex/models/"
    "hyperlex-encoder-modernbert-base-seed-classification-v2-geometry-repair"
)
REPAIR_SHA = "449bf3b303c95bc5d6b7d87173d50315616556c1379057414b970f3e5f0b18cf"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
DEST = Path("/home/morpheus/hlx-private/classification-v2-residual-hub-boundary-20260930")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
MAX_LEN = 64

sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sha256_file(path: Path) -> str:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except PermissionError:
        return subprocess.check_output(["sudo", "sha256sum", str(path)], text=True).split()[0]


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def torch_high_overlap_pairs(family_vectors, *, device, threshold, vocabulary, collapse_cluster):
    import torch

    def unit(matrix):
        norms = torch.linalg.vector_norm(matrix, dim=1, keepdim=True).clamp_min(1e-12)
        return matrix / norms

    tensors = {}
    for family in vocabulary:
        rows = family_vectors.get(family) or []
        if rows:
            tensors[family] = unit(torch.tensor(rows, dtype=torch.float32, device=device))
    families = [family for family in vocabulary if family in tensors]
    high_pairs = []
    for index, left in enumerate(families):
        left_u = tensors[left]
        for right in families[index + 1 :]:
            peak = float((left_u @ tensors[right].T).max().item())
            if peak >= threshold:
                high_pairs.append(
                    {
                        "cosine": peak,
                        "family_a": left,
                        "family_b": right,
                        "in_collapse_cluster": left in collapse_cluster
                        and right in collapse_cluster,
                    }
                )
    collapse_pairs = [pair for pair in high_pairs if pair["in_collapse_cluster"]]
    parent = {family: family for family in collapse_cluster}

    def find(node):
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for pair in collapse_pairs:
        union(pair["family_a"], pair["family_b"])
    components = {}
    for family in collapse_cluster:
        if family in tensors:
            components.setdefault(find(family), []).append(family)
    largest = max((len(v) for v in components.values()), default=0)
    return {
        "collapse_high_overlap_pairs": len(collapse_pairs),
        "high_overlap_pairs": high_pairs,
        "high_overlap_pair_count": len(high_pairs),
        "largest_collapse_component": largest,
        "threshold": threshold,
    }


def inner() -> int:
    import torch
    from safetensors.torch import load_file
    from transformers import AutoModel, AutoTokenizer

    from hyperlexical.classification_v2 import canonical_json, sha256_text
    from hyperlexical.classification_v2_ontology_merge_pair import (
        FORWARD_ACTIVE_FAMILY_VOCABULARY,
        FORWARD_COLLAPSE_CLUSTER,
        HIGH_OVERLAP_COSINE,
    )
    from hyperlexical.classification_v2_residual_hub_boundary import (
        RESIDUAL_REVIEW_SHA,
        assemble_hub_pass,
        build_hub_competitors,
        classify_hub_row,
        enforce_support_floors,
        hub_contract,
        overlap_reduction,
        training_gate_hub,
    )
    from hyperlexical.classification_v2_separability_audit import definition_sources
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.identity_ledger import IdentityLedger, derived_state
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors

    if RESIDUAL_REVIEW_SHA != RESIDUAL_SHA:
        fail("residual review pin drift")
    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if sha256_file(EXPORT) != EXPORT_SHA:
        fail("merge export changed")
    if sha256_file(REPAIR / "model.safetensors") != REPAIR_SHA:
        fail("geometry-repair checkpoint changed")
    merge = json.loads(MERGE.read_text(encoding="utf-8"))
    if merge.get("artifact_sha256") != MERGE_SHA:
        fail("merge artifact hash mismatch")
    residual = json.loads(RESIDUAL.read_text(encoding="utf-8"))
    if residual.get("artifact_sha256") != RESIDUAL_SHA:
        fail("residual review hash mismatch")
    if residual.get("primary_recommendation") != "KEEP_SE_RD_SEPARATE_REFINE_HUBS":
        fail("residual recommendation drift")

    vocab = FORWARD_ACTIVE_FAMILY_VOCABULARY
    rows = [
        json.loads(line)
        for line in EXPORT.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    ledger = IdentityLedger.load(str(LEDGER))
    states = {digest: derived_state(record) for digest, record in ledger.identities.items()}
    train_sources = definition_sources(rows, states, split="train", vocabulary=vocab)["sources"]

    # Pre-overlap pinned to sealed merge post (authoritative residual baseline).
    overlap_pre = {
        "collapse_high_overlap_pairs": merge["overlap_post"]["collapse_high_overlap_pairs"],
        "high_overlap_pair_count": merge["overlap_post"]["high_overlap_pair_count"],
        "largest_collapse_component": merge["overlap_post"]["largest_collapse_component"],
        "threshold": HIGH_OVERLAP_COSINE,
        "high_overlap_pairs": list(merge.get("overlap_post_pairs") or []),
    }
    if int(overlap_pre["high_overlap_pair_count"]) != 34:
        fail("unexpected pre-overlap baseline")

    hub_competitors = build_hub_competitors(overlap_pre["high_overlap_pairs"])
    classifications = []
    support_pre = {}
    for family in vocab:
        bundle = train_sources.get(family) or {"rows": [], "identities": []}
        support_pre[family] = len(bundle["rows"])
        for identity, row in zip(bundle["identities"], bundle["rows"]):
            classifications.append(
                classify_hub_row(
                    family=family,
                    text=str(row.get("text") or ""),
                    identity=str(identity),
                    hub_competitors=hub_competitors,
                )
            )
    classifications = enforce_support_floors(classifications, vocabulary=vocab)
    keep_ids = {
        family: {
            str(row["identity"])
            for row in classifications
            if row["family"] == family and row["decision"] == "KEEP"
        }
        for family in vocab
    }
    support_post = {family: len(keep_ids[family]) for family in vocab}

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("residual hub overlap pass requires CUDA")
    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tokenizer.padding_side = "right"
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    freeze_encoder(encoder)
    warm = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    repair_tensors = split_weight_tensors(
        load_file(str(REPAIR / "model.safetensors"), device="cpu")
    )
    if apply_encoder_trainable(encoder, warm["encoder"])["loaded"] != 48:
        fail("production overlay missed 48 tensors")
    if apply_encoder_trainable(encoder, repair_tensors["encoder"])["loaded"] != 12:
        fail("repair overlay missed 12 tensors")
    encoder.to(device).eval()
    for parameter in encoder.parameters():
        parameter.requires_grad = False

    def encode_texts(texts: list[str], batch_size: int = 32) -> list[list[float]]:
        if not texts:
            return []
        out: list[list[float]] = []
        with torch.no_grad():
            for start in range(0, len(texts), batch_size):
                chunk = texts[start : start + batch_size]
                encoded = tokenizer(
                    chunk, truncation=True, max_length=MAX_LEN, padding=True, return_tensors="pt"
                )
                encoded = {key: value.to(device) for key, value in encoded.items()}
                pooled = encoder(**encoded).last_hidden_state[:, 0].detach().cpu()
                out.extend(row.tolist() for row in pooled)
        return out

    print("encoding KEEP definitions for post-hub overlap", flush=True)
    post_vectors = {}
    for family in vocab:
        bundle = train_sources[family]
        texts = []
        for identity, row in zip(bundle["identities"], bundle["rows"]):
            if str(identity) in keep_ids[family]:
                texts.append(str(row.get("text") or ""))
        post_vectors[family] = encode_texts(texts)

    overlap_post = torch_high_overlap_pairs(
        post_vectors,
        device=device,
        threshold=HIGH_OVERLAP_COSINE,
        vocabulary=list(vocab),
        collapse_cluster=FORWARD_COLLAPSE_CLUSTER,
    )
    reduction = overlap_reduction(overlap_pre, overlap_post)
    gate = training_gate_hub(
        reduction=reduction, support_post=support_post, vocabulary=vocab
    )

    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")

    artifact = assemble_hub_pass(
        {
            "classifications": classifications,
            "hub_competitors": hub_competitors,
            "overlap_pre": overlap_pre,
            "overlap_post": overlap_post,
            "overlap_reduction": reduction,
            "support_pre": support_pre,
            "support_post": support_post,
            "training_gate": gate,
            "export_path": str(EXPORT),
            "export_sha256": EXPORT_SHA,
        }
    )
    artifact["overlap_post_pairs"] = overlap_post.get("high_overlap_pairs")
    artifact["contract"] = hub_contract()
    artifact["artifact_sha256"] = sha256_text(
        canonical_json({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    )

    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    destination = DEST / "RESIDUAL_HUB_BOUNDARY.json"
    destination.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "artifact_sha256": artifact["artifact_sha256"],
        "best_sha256": BEST_SHA,
        "destination": str(destination),
        "hub_families": list(artifact["hub_families"]),
        "keeps_se_rd_separate": True,
        "moves_best": False,
        "next_engineering_action": artifact["next_engineering_action"],
        "overlap_absolute_reduction": artifact["overlap_absolute_reduction"],
        "overlap_percentage_reduction": artifact["overlap_percentage_reduction"],
        "overlap_post": artifact["overlap_post"],
        "overlap_pre": {
            "collapse_high_overlap_pairs": overlap_pre["collapse_high_overlap_pairs"],
            "high_overlap_pair_count": overlap_pre["high_overlap_pair_count"],
            "largest_collapse_component": overlap_pre["largest_collapse_component"],
            "threshold": overlap_pre["threshold"],
        },
        "relationship_dating_merged": False,
        "residual_blockers": artifact["residual_blockers"],
        "row_status_counts": artifact["row_status_counts"],
        "support_post_hubs": {family: support_post[family] for family in artifact["hub_families"]},
        "train": False,
        "training_gate": artifact["training_gate"],
        "reserve_scored": False,
    }
    (DEST / "RESIDUAL_HUB_BOUNDARY_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2), flush=True)
    return 0


def outer() -> int:
    if (DEST / "RESIDUAL_HUB_BOUNDARY.json").exists():
        fail(f"hub boundary artifact already exists: {DEST / 'RESIDUAL_HUB_BOUNDARY.json'}")
    script = Path(__file__).resolve()
    command = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "--name",
        "hlx-v2-residual-hub-boundary",
        "-v",
        f"{REPO}:{REPO}",
        "-v",
        "/home/morpheus/hlx-private:/home/morpheus/hlx-private",
        "-v",
        "/home/morpheus/.hyperlex:/home/morpheus/.hyperlex",
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
    print("launching docker residual-hub-boundary seal", flush=True)
    return subprocess.call(command)


if __name__ == "__main__":
    if "--inner" in sys.argv:
        raise SystemExit(inner())
    raise SystemExit(outer())
