"""Seal HYPERLEX_ACTIVE_FAMILY_ONTOLOGY_MERGE_PAIR_V1.

Applies the approved forward AD+SS → social-evaluation merge, migrates forward
Classification v2 train/val surfaces, reseals 18-family boundaries, reruns the
overlap diagnostic and readiness. Does not train, score the reserve, or move BEST.
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
PHASE = Path("/home/morpheus/hlx-private/classification-v2-phase-execution-20260930")
OVERLAY = PHASE / "civilian.v0.4.phase.jsonl"
OVERLAY_SHA = "8a934806885fb939f8b4ca26f10ab5bc6600c495d3be77d5a2366dc6c62146e0"
REVIEW = Path(
    "/home/morpheus/hlx-private/classification-v2-ontology-refactor-review-20260930/"
    "ONTOLOGY_REFACTOR_REVIEW.json"
)
REVIEW_SHA = "ebab1e4d4d5a0f9169def6426de5b6137fb15f0b7c7d6b57d7aa295cbf6b7178"
TIGHT = Path(
    "/home/morpheus/hlx-private/classification-v2-boundary-tightening-v2-20260930/"
    "BOUNDARY_TIGHTENING_V2.json"
)
TIGHT_SHA = "8c9f88b0431b3598d5336bdb7fa25b80e8201c2ad8487d5aea878997cb6aa5a9"
HISTORICAL_BOUNDARIES = Path(
    "/home/morpheus/hlx-private/classification-v2-boundaries-20260930/"
    "FAMILY_SEMANTIC_BOUNDARIES.json"
)
HISTORICAL_BOUNDARY_SHA = "0ca6f34ce1abf68388e443371672ca36e16028079a175b6775e1968900e1c52f"
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
DEST = Path("/home/morpheus/hlx-private/classification-v2-ontology-merge-pair-20260930")
EXPORT = DEST / "civilian.v0.6.merge.jsonl"
NEW_BOUNDARIES = DEST / "FAMILY_SEMANTIC_BOUNDARIES.json"
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


def _f32_list(values) -> list[float]:
    return [struct.unpack("<f", struct.pack("<f", float(value)))[0] for value in values]


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

    from hyperlexical.classification_v2 import canonical_json, sha256_text
    from hyperlexical.classification_v2_boundaries import (
        assemble_boundaries,
        assess_boundary_artifact,
        boundary_training_sources,
    )
    from hyperlexical.classification_v2_ontology_merge_pair import (
        FORWARD_ACTIVE_FAMILY_VOCABULARY,
        FORWARD_COLLAPSE_CLUSTER,
        HIGH_OVERLAP_COSINE,
        KEEP_FAMILY,
        MERGED_LABEL,
        PRE_MERGE_OVERLAP_PIN,
        assemble_merge_artifact,
        count_definition_support,
        existing_overlap_gate_pass,
        forward_ontology_identity,
        forward_support_readiness,
        freeze_migration_map,
        head_initialization_policy,
        merge_contract,
        migrate_forward_rows,
        overlap_reduction,
        relationship_dating_post_merge_status,
        training_gate_from_readiness,
        verify_migration_counts,
    )
    from hyperlexical.classification_v2_separability_audit import definition_sources
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.identity_ledger import IdentityLedger, derived_state
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors

    if merge_contract()["ontology_review_sha256"] != REVIEW_SHA:
        fail("review pin drift")
    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if sha256_file(OVERLAY) != OVERLAY_SHA:
        fail("overlay changed")
    if sha256_file(REPAIR / "model.safetensors") != REPAIR_SHA:
        fail("geometry-repair checkpoint changed")
    review = json.loads(REVIEW.read_text(encoding="utf-8"))
    if review.get("artifact_sha256") != REVIEW_SHA:
        fail("ontology review hash mismatch")
    if review.get("primary_recommendation") != "MERGE_PAIR":
        fail("review recommendation is not MERGE_PAIR")
    tight = json.loads(TIGHT.read_text(encoding="utf-8"))
    if tight.get("artifact_sha256") != TIGHT_SHA:
        fail("tightening hash mismatch")
    historical = json.loads(HISTORICAL_BOUNDARIES.read_text(encoding="utf-8"))
    if historical.get("boundary_sha256") != HISTORICAL_BOUNDARY_SHA:
        fail("historical boundaries mutated")

    vocab = FORWARD_ACTIVE_FAMILY_VOCABULARY
    if len(vocab) != 18:
        fail(f"forward vocab width {len(vocab)}")

    ontology = forward_ontology_identity()
    migration = freeze_migration_map()
    head_init = head_initialization_policy()

    source_rows = [
        json.loads(line)
        for line in OVERLAY.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    migrated_bundle = migrate_forward_rows(
        source_rows, migration_map=migration["compatibility_map"]
    )
    migrated_rows = migrated_bundle["rows"]

    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    with EXPORT.open("w", encoding="utf-8") as handle:
        for row in migrated_rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    os.chmod(EXPORT, 0o644)
    export_sha = sha256_file(EXPORT)

    ledger = IdentityLedger.load(str(LEDGER))
    states = {digest: derived_state(record) for digest, record in ledger.identities.items()}
    train_sources = definition_sources(
        migrated_rows, states, split="train", vocabulary=vocab
    )["sources"]
    val_sources = definition_sources(
        migrated_rows, states, split="val", vocabulary=vocab
    )["sources"]
    train_support = count_definition_support(train_sources, vocabulary=vocab)
    val_support = count_definition_support(val_sources, vocabulary=vocab)
    verification = verify_migration_counts(
        definition_train=train_support,
        definition_val=val_support,
        affected_train=migrated_bundle["affected_train"],
        affected_val=migrated_bundle["affected_val"],
    )
    if not verification["ok"]:
        fail(f"migration count mismatch: {verification['errors']}")
    print(
        json.dumps(
            {
                "migration_ok": True,
                "affected_train_rows": migrated_bundle["affected_train"],
                "affected_val_rows": migrated_bundle["affected_val"],
                "definition_support": verification,
            },
            indent=2,
        ),
        flush=True,
    )

    # Boundary reseal with frozen BEST encoder (same as original boundary builder).
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

    collected = boundary_training_sources(migrated_rows, states, vocabulary=vocab)
    sources = collected["sources"]
    missing_boundary = [family for family in vocab if family not in sources]
    if missing_boundary:
        fail(f"boundary sources missing families: {missing_boundary}")

    def once():
        return assemble_boundaries(
            members_from(sources, encode_sources(tok, encoder, sources)),
            vocabulary=vocab,
        )

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
    first["forward_vocabulary_id"] = ontology["vocabulary_id"]
    first["max_len"] = MAX_LEN
    first["moves_best"] = False
    first["ontology_sha256"] = ontology["ontology_sha256"]
    first["padding_side"] = "right"
    first["pooling"] = "last_hidden_state[:, 0]"
    first["reserve_scored"] = False
    first["train"] = False
    first["trunk"] = str(TRUNK)
    report = assess_boundary_artifact(first, vocabulary=vocab)
    if not report["pass"]:
        fail(f"boundary artifact failed: {report}")
    # Do not mutate historical boundaries file.
    if historical.get("boundary_sha256") != HISTORICAL_BOUNDARY_SHA:
        fail("historical boundaries mutated during seal")
    NEW_BOUNDARIES.write_text(
        json.dumps(first, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.chmod(NEW_BOUNDARIES, 0o644)
    reloaded = assess_boundary_artifact(
        json.loads(NEW_BOUNDARIES.read_text(encoding="utf-8")), vocabulary=vocab
    )
    if not reloaded["pass"] or reloaded["boundary_sha256"] != first["boundary_sha256"]:
        fail("boundary artifact did not round-trip")

    # Overlap diagnostic with same frozen BEST+repair stack as tightening.
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("ontology merge overlap pass requires CUDA")
    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tokenizer.padding_side = "right"
    overlap_encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    freeze_encoder(overlap_encoder)
    warm = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    repair_tensors = split_weight_tensors(
        load_file(str(REPAIR / "model.safetensors"), device="cpu")
    )
    if apply_encoder_trainable(overlap_encoder, warm["encoder"])["loaded"] != 48:
        fail("production overlay missed 48 tensors")
    if apply_encoder_trainable(overlap_encoder, repair_tensors["encoder"])["loaded"] != 12:
        fail("repair overlay missed 12 tensors")
    overlap_encoder.to(device).eval()
    for parameter in overlap_encoder.parameters():
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
                pooled = overlap_encoder(**encoded).last_hidden_state[:, 0].detach().cpu()
                out.extend(row.tolist() for row in pooled)
        return out

    print("encoding forward train definitions for post-merge overlap", flush=True)
    post_vectors = {}
    for family in vocab:
        texts = [str(row.get("text") or "") for row in train_sources[family]["rows"]]
        post_vectors[family] = encode_texts(texts)

    overlap_pre = dict(PRE_MERGE_OVERLAP_PIN)
    # Pin must match sealed tightening post.
    sealed_post = tight.get("overlap_post") or {}
    if (
        int(sealed_post.get("high_overlap_pair_count", -1))
        != int(overlap_pre["high_overlap_pair_count"])
        or int(sealed_post.get("largest_collapse_component", -1))
        != int(overlap_pre["largest_collapse_component"])
    ):
        fail("pre-merge overlap pin drifted from sealed tightening post")

    overlap_post = torch_high_overlap_pairs(
        post_vectors,
        device=device,
        threshold=HIGH_OVERLAP_COSINE,
        vocabulary=list(vocab),
        collapse_cluster=FORWARD_COLLAPSE_CLUSTER,
    )
    reduction = overlap_reduction(overlap_pre, overlap_post)
    gate = existing_overlap_gate_pass(
        reduction=reduction, support=train_support, vocabulary=vocab
    )
    rd_status = relationship_dating_post_merge_status(overlap_post)

    isolation_pass = True
    # Reserved identities must not appear in boundary sources.
    reserved = set(collected.get("excluded_identities") or [])
    for family in vocab:
        for identity in train_sources[family]["identities"]:
            if identity in reserved:
                isolation_pass = False
    train_eval_separation_pass = historical.get("boundary_sha256") == HISTORICAL_BOUNDARY_SHA

    readiness = forward_support_readiness(
        train_support=train_support,
        val_support=val_support,
        ontology=ontology,
        migration=migration,
        boundary_assessment=report,
        overlap_gate=gate,
        isolation_pass=isolation_pass,
        train_eval_separation_pass=train_eval_separation_pass,
        vocabulary=vocab,
    )
    training_gate = training_gate_from_readiness(readiness, gate)

    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if historical.get("boundary_sha256") != HISTORICAL_BOUNDARY_SHA:
        fail("historical boundaries mutated")

    artifact = assemble_merge_artifact(
        {
            "ontology": ontology,
            "migration": migration,
            "migration_verification": verification,
            "boundary": {
                "boundary_sha256": first["boundary_sha256"],
                "separation_sha256": first["separation_sha256"],
                "anchor_witness_sha256": first["anchor_witness_sha256"],
                "pass": report["pass"],
            },
            "overlap_pre": overlap_pre,
            "overlap_post": overlap_post,
            "overlap_reduction": reduction,
            "overlap_gate": gate,
            "readiness": readiness,
            "training_gate": training_gate,
            "relationship_dating_status": rd_status,
            "head_initialization": head_init,
            "export_path": str(EXPORT),
            "export_sha256": export_sha,
        }
    )
    # Attach full post pairs for operator inspection (hashed separately via summary fields).
    artifact["overlap_post_pairs"] = overlap_post.get("high_overlap_pairs")
    artifact["artifact_sha256"] = sha256_text(
        canonical_json({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    )

    destination = DEST / "ONTOLOGY_MERGE_PAIR.json"
    destination.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "active_family_count": artifact["active_family_count"],
        "artifact_sha256": artifact["artifact_sha256"],
        "best_sha256": BEST_SHA,
        "boundary_sha256": artifact["boundary_sha256"],
        "destination": str(destination),
        "export_path": str(EXPORT),
        "export_sha256": export_sha,
        "forward_vocabulary_id": artifact["forward_vocabulary_id"],
        "largest_collapse_component_after": artifact["overlap_post"]["largest_collapse_component"],
        "largest_collapse_component_before": artifact["overlap_pre"]["largest_collapse_component"],
        "merge_application_state": artifact["merge_application_state"],
        "migration_map_sha256": artifact["migration_map_sha256"],
        "migrated_train": verification["migrated_train"],
        "migrated_val": verification["migrated_val"],
        "moves_best": False,
        "next_action": artifact["next_action"],
        "ontology_sha256": artifact["ontology_sha256"],
        "overlap_absolute_reduction": artifact["overlap_absolute_reduction"],
        "overlap_gate": gate["overlap_gate"],
        "overlap_percentage_reduction": artifact["overlap_percentage_reduction"],
        "overlap_post": artifact["overlap_post"],
        "overlap_pre": artifact["overlap_pre"],
        "readiness_state": readiness["state"],
        "relationship_dating_status": rd_status["status"],
        "residual_blockers": artifact["residual_blockers"],
        "separation_sha256": artifact["separation_sha256"],
        "social_evaluation_support": artifact["social_evaluation_support"],
        "relationship_dating_support": artifact["relationship_dating_support"],
        "train": False,
        "training_gate": artifact["training_gate"],
        "reserve_scored": False,
    }
    (DEST / "ONTOLOGY_MERGE_PAIR_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2), flush=True)
    return 0


def outer() -> int:
    if (DEST / "ONTOLOGY_MERGE_PAIR.json").exists():
        fail(f"merge artifact already exists: {DEST / 'ONTOLOGY_MERGE_PAIR.json'}")
    script = Path(__file__).resolve()
    command = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "--name",
        "hlx-v2-ontology-merge-pair",
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
    print("launching docker ontology-merge-pair seal", flush=True)
    return subprocess.call(command)


if __name__ == "__main__":
    if "--inner" in sys.argv:
        raise SystemExit(inner())
    raise SystemExit(outer())
