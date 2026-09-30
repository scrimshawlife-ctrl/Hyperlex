"""Seal HYPERLEX_ACTIVE_FAMILY_BOUNDARY_TIGHTENING_V2.

Reclassifies unresolved boundary-redefinition rows, applies structural-pair
comparison on KEEP rows in the three SPLIT_CANDIDATE families, and reseals the
frozen-encoder overlap gate. Does not train, score the reserve, or move BEST.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path("/home/morpheus/Hyperlex")
PHASE = Path("/home/morpheus/hlx-private/classification-v2-phase-execution-20260930")
REDEF = Path(
    "/home/morpheus/hlx-private/classification-v2-boundary-redefinition-20260930/BOUNDARY_REDEFINITION.json"
)
REDEF_SHA = "4757d46aa7f0c95732378d5f710cbd1a28d048f60bee2fc35dfb6d5c0fe8cad1"
OVERLAY = PHASE / "civilian.v0.4.phase.jsonl"
OVERLAY_SHA = "8a934806885fb939f8b4ca26f10ab5bc6600c495d3be77d5a2366dc6c62146e0"
BOUNDARIES = Path(
    "/home/morpheus/hlx-private/classification-v2-boundaries-20260930/FAMILY_SEMANTIC_BOUNDARIES.json"
)
BOUNDARY_SHA = "0ca6f34ce1abf68388e443371672ca36e16028079a175b6775e1968900e1c52f"
REPAIR = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-classification-v2-geometry-repair"
)
REPAIR_SHA = "449bf3b303c95bc5d6b7d87173d50315616556c1379057414b970f3e5f0b18cf"
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
DEST = Path("/home/morpheus/hlx-private/classification-v2-boundary-tightening-v2-20260930")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"

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
                        "in_collapse_cluster": left in collapse_cluster and right in collapse_cluster,
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

    from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY, canonical_json, sha256_text
    from hyperlexical.classification_v2_boundary_tightening_v2 import (
        BOUNDARY_REDEFINITION_SHA,
        HIGH_OVERLAP_COSINE,
        MATERIAL_OVERLAP_REDUCTION,
        STRUCTURAL_FAMILIES,
        STRUCTURAL_SPLIT_PAIRS,
        UNRESOLVED_STATUSES,
        assess_structural_splits,
        assemble_tightening,
        build_final_keep_identities,
        classify_structural_keep_for_comparison,
        classify_unresolved_row,
        delta_counts,
        family_semantic_contract,
        pairwise_discriminator,
        training_gate_v2,
        tightening_contract,
    )
    from hyperlexical.classification_v2_separability_audit import (
        COLLAPSE_CLUSTER,
        SPARSE_FOCUS,
        definition_sources,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.identity_ledger import IdentityLedger, derived_state
    from hyperlexical.layout import MAX_LEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors

    if MATERIAL_OVERLAP_REDUCTION != 0.30:
        fail("material reduction threshold drifted")
    if HIGH_OVERLAP_COSINE != 0.80:
        fail("high-overlap cosine drifted")
    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if sha256_file(REPAIR / "model.safetensors") != REPAIR_SHA:
        fail("geometry-repair checkpoint changed")
    if sha256_file(OVERLAY) != OVERLAY_SHA:
        fail("phase overlay changed")
    redef = json.loads(REDEF.read_text(encoding="utf-8"))
    if redef.get("artifact_sha256") != REDEF_SHA:
        fail("boundary redefinition hash mismatch")
    if BOUNDARY_REDEFINITION_SHA != REDEF_SHA:
        fail("module redefinition pin drift")
    boundaries = json.loads(BOUNDARIES.read_text(encoding="utf-8"))
    if boundaries.get("boundary_sha256") != BOUNDARY_SHA:
        fail("historical boundary hash mismatch")

    prior_rows = redef["row_classifications"]
    prior_counts = Counter(row["decision"] for row in prior_rows)
    unresolved = [row for row in prior_rows if row["decision"] in UNRESOLVED_STATUSES]
    prior_keep = [row for row in prior_rows if row["decision"] == "KEEP"]
    expected_unresolved = {"REVIEW": 425, "AMBIGUOUS": 9, "DROP": 17, "RELABEL_CANDIDATE": 2}
    for status, count in expected_unresolved.items():
        if prior_counts.get(status, 0) != count:
            fail(f"sealed unresolved count drift: {status}={prior_counts.get(status)} expected {count}")

    print(f"reclassifying {len(unresolved)} unresolved rows", flush=True)
    unresolved_results = []
    for row in unresolved:
        unresolved_results.append(
            classify_unresolved_row(
                identity=str(row["identity"]),
                current_family=str(row["family"]),
                text=row.get("text"),
                prior_decision=str(row["decision"]),
            )
        )
    unresolved_counts = Counter(row["decision"] for row in unresolved_results)

    print("structural KEEP comparison for split-candidate families", flush=True)
    structural_overrides = []
    for row in prior_keep:
        if row["family"] not in STRUCTURAL_FAMILIES:
            continue
        override = classify_structural_keep_for_comparison(
            identity=str(row["identity"]),
            current_family=str(row["family"]),
            text=row.get("text"),
        )
        if override is not None:
            structural_overrides.append(override)
    override_counts = Counter(row["decision"] for row in structural_overrides)

    keep_bundle = build_final_keep_identities(
        prior_rows=prior_rows,
        unresolved_results=unresolved_results,
        structural_keep_overrides=structural_overrides,
    )
    if keep_bundle["support_floor_failure"]:
        print("TRAINING_SUPPORT_FLOOR_FAILURE", keep_bundle["support"], flush=True)

    # Frozen-encoder overlap on full train defs (pre) and final KEEP (post).
    rows = [json.loads(line) for line in OVERLAY.read_text(encoding="utf-8").splitlines() if line.strip()]
    ledger = IdentityLedger.load(str(LEDGER))
    states = {digest: derived_state(record) for digest, record in ledger.identities.items()}
    train_sources = definition_sources(rows, states, split="train")["sources"]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("boundary tightening overlap pass requires CUDA")
    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tokenizer.padding_side = "right"
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    freeze_encoder(encoder)
    warm = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    tensors = split_weight_tensors(load_file(str(REPAIR / "model.safetensors"), device="cpu"))
    if apply_encoder_trainable(encoder, warm["encoder"])["loaded"] != 48:
        fail("production overlay missed 48 tensors")
    if apply_encoder_trainable(encoder, tensors["encoder"])["loaded"] != 12:
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

    print("encoding full train definitions for pre-overlap", flush=True)
    train_ids = {}
    train_texts = {}
    train_vectors = {}
    for family in ACTIVE_FAMILY_VOCABULARY:
        bundle = train_sources[family]
        texts = [str(row.get("text") or "") for row in bundle["rows"]]
        ids = list(bundle["identities"])
        train_texts[family] = texts
        train_ids[family] = ids
        train_vectors[family] = encode_texts(texts)

    overlap_pre = torch_high_overlap_pairs(
        train_vectors,
        device=device,
        threshold=HIGH_OVERLAP_COSINE,
        vocabulary=list(ACTIVE_FAMILY_VOCABULARY),
        collapse_cluster=COLLAPSE_CLUSTER,
    )

    # Map KEEP identities to vectors (identity may be prefix for preserved noise — skip missing).
    id_to_index = {
        family: {identity: index for index, identity in enumerate(train_ids[family])}
        for family in ACTIVE_FAMILY_VOCABULARY
    }
    post_vectors: dict[str, list[list[float]]] = {family: [] for family in ACTIVE_FAMILY_VOCABULARY}
    missing_keep = 0
    for family, identities in keep_bundle["keep_identities"].items():
        for identity in identities:
            index = id_to_index[family].get(identity)
            if index is None:
                # try prefix match for truncated noise identities
                matches = [i for i, full in enumerate(train_ids[family]) if full.startswith(identity)]
                if not matches:
                    missing_keep += 1
                    continue
                index = matches[0]
            post_vectors[family].append(train_vectors[family][index])

    print("computing post-tightening overlap", flush=True)
    overlap_post = torch_high_overlap_pairs(
        post_vectors,
        device=device,
        threshold=HIGH_OVERLAP_COSINE,
        vocabulary=list(ACTIVE_FAMILY_VOCABULARY),
        collapse_cluster=COLLAPSE_CLUSTER,
    )

    # Final status totals across unresolved reclassifications + structural overrides
    # (KEEP prior unchanged except overrides). Report unresolved reclass totals as requested.
    row_status_counts = {status: int(unresolved_counts.get(status, 0)) for status in ("KEEP", "DROP", "RELABEL_CANDIDATE", "AMBIGUOUS")}
    # Also expose final training KEEP support counts separately via support.

    split_assessments = assess_structural_splits(
        pre_pairs=overlap_pre["high_overlap_pairs"],
        post_pairs=overlap_post["high_overlap_pairs"],
    )
    gate = training_gate_v2(
        pre_count=int(overlap_pre["high_overlap_pair_count"]),
        post_count=int(overlap_post["high_overlap_pair_count"]),
        support=keep_bundle["support"],
        collapse_pre=int(overlap_pre["largest_collapse_component"]),
        collapse_post=int(overlap_post["largest_collapse_component"]),
        support_floor_failure=bool(keep_bundle["support_floor_failure"]),
    )

    semantics = {family: family_semantic_contract(family) for family in ACTIVE_FAMILY_VOCABULARY}
    discriminators = []
    for a, b in STRUCTURAL_SPLIT_PAIRS:
        item = pairwise_discriminator(a, b)
        if item:
            discriminators.append(item)

    compact_unresolved = []
    for row in unresolved_results:
        text = row.get("text")
        compact_unresolved.append(
            {
                "collision_pair": row.get("collision_pair"),
                "current_family": row["current_family"],
                "decision": row["decision"],
                "matched_exclusion": row.get("matched_exclusion"),
                "matched_required_core": row.get("matched_required_core") or [],
                "prior_decision": row.get("prior_decision"),
                "proposed_family": row.get("proposed_family"),
                "reason_code": row["reason_code"],
                "source_identity": row["source_identity"],
                "text": None if text is None else (text if len(text) <= 160 else text[:157] + "..."),
            }
        )
    compact_unresolved.sort(key=lambda item: (item["decision"], item["current_family"], item["source_identity"]))
    compact_overrides = []
    for row in structural_overrides:
        text = row.get("text")
        compact_overrides.append(
            {
                "collision_pair": row.get("collision_pair"),
                "current_family": row["current_family"],
                "decision": row["decision"],
                "matched_exclusion": row.get("matched_exclusion"),
                "matched_required_core": row.get("matched_required_core") or [],
                "prior_decision": row.get("prior_decision"),
                "proposed_family": row.get("proposed_family"),
                "reason_code": row["reason_code"],
                "source_identity": row["source_identity"],
                "text": None if text is None else (text if len(text) <= 160 else text[:157] + "..."),
            }
        )

    artifact = assemble_tightening(
        {
            "family_semantics": semantics,
            "pairwise_discriminators": discriminators,
            "unresolved_reclassifications": compact_unresolved,
            "structural_keep_overrides": compact_overrides,
            "row_status_counts": row_status_counts,
            "delta": {
                **delta_counts(prior_counts, unresolved_counts, structural_override_counts=override_counts),
                "missing_keep_vectors": missing_keep,
                "final_keep_total": sum(keep_bundle["support"].values()),
                "structural_overrides_n": len(structural_overrides),
            },
            "support": keep_bundle["support"],
            "overlap_pre": overlap_pre,
            "overlap_post": overlap_post,
            "split_candidate_assessments": split_assessments,
            "training_gate": gate,
        }
    )
    artifact["contract"] = tightening_contract()
    artifact["artifact_sha256"] = sha256_text(
        canonical_json({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    )

    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if boundaries.get("boundary_sha256") != BOUNDARY_SHA:
        fail("historical boundaries mutated")

    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    destination = DEST / "BOUNDARY_TIGHTENING_V2.json"
    destination.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "destination": str(destination),
        "boundary_tightening_state": artifact["boundary_tightening_state"],
        "artifact_sha256": artifact["artifact_sha256"],
        "row_status_counts": artifact["row_status_counts"],
        "delta": artifact["delta"],
        "support": artifact["support"],
        "sparse_support": artifact["sparse_support"],
        "overlap_pre": artifact["overlap_pre"],
        "overlap_post": artifact["overlap_post"],
        "overlap_absolute_reduction": artifact["overlap_absolute_reduction"],
        "overlap_reduction": artifact["overlap_reduction"],
        "collapse_component_pre": artifact["collapse_component_pre"],
        "collapse_component_post": artifact["collapse_component_post"],
        "split_candidate_assessments": artifact["split_candidate_assessments"],
        "training_gate": gate["training_gate"],
        "residual_blockers": gate["residual_blockers"],
        "next_engineering_action": artifact["next_engineering_action"],
        "best_sha256": BEST_SHA,
        "train": False,
        "reserve_scored": False,
        "moves_best": False,
        "historical_boundaries_mutated": False,
    }
    (DEST / "BOUNDARY_TIGHTENING_V2_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2), flush=True)
    return 0


def outer() -> int:
    script = Path(__file__).resolve()
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
        "-e",
        f"PYTHONPATH={REPO}/scripts/shadow",
        "-w",
        str(REPO),
        IMAGE,
        "python3",
        str(script),
        "--inner",
    ]
    print("launching docker boundary-tightening-v2 seal", flush=True)
    return subprocess.call(command)


if __name__ == "__main__":
    if "--inner" in sys.argv:
        raise SystemExit(inner())
    raise SystemExit(outer())
