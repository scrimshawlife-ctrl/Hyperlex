"""Seal HYPERLEX_ACTIVE_FAMILY_SEPARABILITY_AUDIT_V1 on training definitions.

Read-only. Does not train, does not score the evaluation reserve, and does not
move BEST. Embedding metrics use the frozen geometry-repair encoder.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
EXPORT = Path("/home/morpheus/hlx-private/classification-v2-surface-20260929/civilian.v0.3.jsonl")
EXPORT_SHA = "c4677011ea61f135c8fb82bed9d973dffe3a5db582d34421403e71498c5fd243"
BOUNDARIES = Path(
    "/home/morpheus/hlx-private/classification-v2-boundaries-20260930/FAMILY_SEMANTIC_BOUNDARIES.json"
)
BOUNDARY_SHA = "0ca6f34ce1abf68388e443371672ca36e16028079a175b6775e1968900e1c52f"
SEPARATION_SHA = "ab698d342d2d276f81d4baf3fed609bb6f8bf88cd6810bb1d1998c5e409f63c3"
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
DESTINATION = Path(
    "/home/morpheus/hlx-private/classification-v2-separability-audit-20260930/SEPARABILITY_AUDIT.json"
)
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"

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


def inner() -> int:
    import torch
    from safetensors.torch import load_file
    from transformers import AutoModel, AutoTokenizer

    from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY
    from hyperlexical.classification_v2_max_anchor import load_sealed_anchors
    from hyperlexical.classification_v2_separability_audit import (
        assemble_audit,
        assemble_pair_matrices,
        audit_contract,
        boundary_evidence_for_family,
        classify_pair_flags,
        definition_sources,
        family_status_for,
        lexical_pair_report,
        overall_decision,
        propose_boundary_refinements,
        rank_worst_pairs,
        remediation_for,
        sparse_family_treatment,
        COLLAPSE_CLUSTER,
        SPARSE_FOCUS,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.identity_ledger import IdentityLedger, derived_state
    from hyperlexical.layout import MAX_LEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors

    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if sha256_file(REPAIR / "model.safetensors") != REPAIR_SHA:
        fail("geometry-repair checkpoint changed")
    if sha256_file(EXPORT) != EXPORT_SHA:
        fail("surface export changed")
    boundaries = json.loads(BOUNDARIES.read_text(encoding="utf-8"))
    if boundaries.get("boundary_sha256") != BOUNDARY_SHA:
        fail("boundary hash mismatch")
    if boundaries.get("separation_sha256") != SEPARATION_SHA:
        fail("separation hash mismatch")
    sealed = load_sealed_anchors(boundaries)
    sealed_by_family = {item["family"]: item for item in boundaries.get("boundaries", [])}

    rows = [json.loads(line) for line in EXPORT.read_text(encoding="utf-8").splitlines() if line.strip()]
    ledger = IdentityLedger.load(str(LEDGER))
    states = {digest: derived_state(record) for digest, record in ledger.identities.items()}
    train_bundle = definition_sources(rows, states, split="train")
    val_bundle = definition_sources(rows, states, split="val")
    train_sources = train_bundle["sources"]
    val_sources = val_bundle["sources"]
    if set(train_sources) != set(ACTIVE_FAMILY_VOCABULARY):
        fail(f"missing train families: {sorted(set(ACTIVE_FAMILY_VOCABULARY) - set(train_sources))}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("separability audit embedding pass requires CUDA")
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

    def _scalar(value):
        import struct
        if value is None:
            return None
        return struct.unpack("<f", struct.pack("<f", float(value)))[0]

    def encode_texts(texts: list[str], batch_size: int = 32) -> list[list[float]]:
        if not texts:
            return []
        out: list[list[float]] = []
        with torch.no_grad():
            for start in range(0, len(texts), batch_size):
                chunk = texts[start : start + batch_size]
                encoded = tokenizer(
                    chunk,
                    truncation=True,
                    max_length=MAX_LEN,
                    padding=True,
                    return_tensors="pt",
                )
                encoded = {key: value.to(device) for key, value in encoded.items()}
                pooled = encoder(**encoded).last_hidden_state[:, 0].detach().cpu()
                out.extend(row.tolist() for row in pooled)
        return out

    def _torch_unit(matrix: torch.Tensor) -> torch.Tensor:
        norms = torch.linalg.vector_norm(matrix, dim=1, keepdim=True).clamp_min(1e-12)
        return matrix / norms

    def torch_embedding_pair_report(
        left_vectors,
        right_vectors,
        left_anchors,
        right_anchors,
        *,
        left_weights=None,
        right_weights=None,
    ):
        from hyperlexical.classification_v2_boundaries import COLLISION_COSINE

        left = torch.tensor(left_vectors, dtype=torch.float32, device=device)
        right = torch.tensor(right_vectors, dtype=torch.float32, device=device)
        left_u = _torch_unit(left)
        right_u = _torch_unit(right)
        within_a = None
        within_b = None
        if left_u.shape[0] >= 2:
            sim = left_u @ left_u.T
            mask = torch.triu(torch.ones_like(sim, dtype=torch.bool), diagonal=1)
            within_a = _scalar(sim[mask].mean().item())
        if right_u.shape[0] >= 2:
            sim = right_u @ right_u.T
            mask = torch.triu(torch.ones_like(sim, dtype=torch.bool), diagonal=1)
            within_b = _scalar(sim[mask].mean().item())
        cross = _scalar((left_u @ right_u.T).mean().item()) if left_u.numel() and right_u.numel() else None
        if left_weights is None:
            lw = torch.ones(left_u.shape[0], device=device)
        else:
            lw = torch.tensor(left_weights, dtype=torch.float32, device=device)
        if right_weights is None:
            rw = torch.ones(right_u.shape[0], device=device)
        else:
            rw = torch.tensor(right_weights, dtype=torch.float32, device=device)
        centroid_a = _torch_unit((lw[:, None] * left).sum(dim=0, keepdim=True) / lw.sum().clamp_min(1e-12))
        centroid_b = _torch_unit((rw[:, None] * right).sum(dim=0, keepdim=True) / rw.sum().clamp_min(1e-12))
        centroid_cosine = _scalar((centroid_a * centroid_b).sum().item())
        centroid_distance = _scalar(1.0 - float(centroid_cosine))
        # NN confusion A->B
        def nn_rate(query_u, same_u, other_u):
            if query_u.shape[0] == 0 or other_u.shape[0] == 0:
                return None
            cross_best = (query_u @ other_u.T).max(dim=1).values
            if same_u.shape[0] == 1:
                confused = (cross_best >= COLLISION_COSINE).sum().item()
                return _scalar(confused / query_u.shape[0])
            same_sim = query_u @ same_u.T
            # mask self
            same_sim.fill_diagonal_(-2.0)
            same_best = same_sim.max(dim=1).values
            confused = (cross_best > same_best).sum().item()
            return _scalar(confused / query_u.shape[0])

        nn_a = nn_rate(left_u, left_u, right_u)
        nn_b = nn_rate(right_u, right_u, left_u)
        la = torch.tensor(left_anchors, dtype=torch.float32, device=device)
        ra = torch.tensor(right_anchors, dtype=torch.float32, device=device)
        la_u = _torch_unit(la)
        ra_u = _torch_unit(ra)
        anchor_sim = la_u @ ra_u.T
        colliding = (anchor_sim >= COLLISION_COSINE).sum().item()
        support_pairs = int(anchor_sim.numel())
        return {
            "anchor_collision_max_cosine": _scalar(anchor_sim.max().item()),
            "anchor_collision_rate": _scalar(colliding / support_pairs) if support_pairs else None,
            "centroid_cosine": centroid_cosine,
            "centroid_distance": centroid_distance,
            "cross_family_similarity": cross,
            "nearest_neighbor_confusion_a": nn_a,
            "nearest_neighbor_confusion_b": nn_b,
            "within_family_similarity_a": within_a,
            "within_family_similarity_b": within_b,
        }

    def torch_pairwise_probe(train_left, train_right, val_left, val_right, train_left_weights=None, train_right_weights=None):
        from hyperlexical.classification_v2_separability_audit import PROBE_MIN_TRAIN, PROBE_MIN_VAL
        if (
            len(train_left) < PROBE_MIN_TRAIN
            or len(train_right) < PROBE_MIN_TRAIN
            or len(val_left) < PROBE_MIN_VAL
            or len(val_right) < PROBE_MIN_VAL
        ):
            return {
                "accuracy": None,
                "f1": None,
                "n_train": len(train_left) + len(train_right),
                "n_val": len(val_left) + len(val_right),
                "status": "NOT_COMPUTABLE",
            }
        tl = torch.tensor(train_left, dtype=torch.float32, device=device)
        tr = torch.tensor(train_right, dtype=torch.float32, device=device)
        if train_left_weights is None:
            lw = torch.ones(tl.shape[0], device=device)
        else:
            lw = torch.tensor(train_left_weights, dtype=torch.float32, device=device)
        if train_right_weights is None:
            rw = torch.ones(tr.shape[0], device=device)
        else:
            rw = torch.tensor(train_right_weights, dtype=torch.float32, device=device)
        mean_l = (lw[:, None] * tl).sum(0) / lw.sum().clamp_min(1e-12)
        mean_r = (rw[:, None] * tr).sum(0) / rw.sum().clamp_min(1e-12)
        direction = mean_l - mean_r
        direction = direction / direction.norm().clamp_min(1e-12)
        threshold = 0.5 * ((mean_l * direction).sum() + (mean_r * direction).sum())
        vl = _torch_unit(torch.tensor(val_left, dtype=torch.float32, device=device))
        vr = _torch_unit(torch.tensor(val_right, dtype=torch.float32, device=device))
        pred_l = (vl @ direction) >= threshold
        pred_r = (vr @ direction) >= threshold
        # A = True, B = False
        gold = torch.cat([torch.ones(vl.shape[0], dtype=torch.bool, device=device), torch.zeros(vr.shape[0], dtype=torch.bool, device=device)])
        pred = torch.cat([pred_l, pred_r])
        accuracy = (gold == pred).float().mean().item()
        f1s = []
        for label_true in (True, False):
            g = gold == label_true
            p = pred == label_true
            hit = (g & p).sum().item()
            gold_n = g.sum().item()
            pred_n = p.sum().item()
            if gold_n == 0 and pred_n == 0:
                continue
            precision = hit / pred_n if pred_n else 0.0
            recall = hit / gold_n if gold_n else 0.0
            f1s.append(0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall))
        return {
            "accuracy": _scalar(accuracy),
            "f1": _scalar(sum(f1s) / len(f1s)) if f1s else None,
            "n_train": len(train_left) + len(train_right),
            "n_val": len(val_left) + len(val_right),
            "status": "OK",
            "threshold": _scalar(threshold.item()),
        }

    train_texts: dict[str, list[str]] = {}
    train_ids: dict[str, list[str]] = {}
    train_weights: dict[str, list[float]] = {}
    train_vectors: dict[str, list[list[float]]] = {}
    val_texts: dict[str, list[str]] = {}
    val_vectors: dict[str, list[list[float]]] = {}
    support: dict[str, dict[str, int]] = {}
    print("encoding train/val definitions", flush=True)
    for family in ACTIVE_FAMILY_VOCABULARY:
        bundle = train_sources[family]
        texts = [str(row.get("text") or "") for row in bundle["rows"]]
        train_texts[family] = texts
        train_ids[family] = list(bundle["identities"])
        train_weights[family] = list(bundle["weights"])
        train_vectors[family] = encode_texts(texts)
        support[family] = {
            "inferred": int(bundle["inferred"]),
            "n": len(texts),
            "observed": int(bundle["observed"]),
            "n_val_definitions": len(val_sources.get(family, {}).get("rows", [])),
        }
        val_rows = val_sources.get(family, {}).get("rows", [])
        val_text_list = [str(row.get("text") or "") for row in val_rows]
        val_texts[family] = val_text_list
        val_vectors[family] = encode_texts(val_text_list) if val_text_list else []

    centroids = {
        family: [
            sum(weight * value for weight, value in zip(train_weights[family], column))
            / max(sum(train_weights[family]), 1e-12)
            for column in zip(*train_vectors[family])
        ]
        for family in ACTIVE_FAMILY_VOCABULARY
    }
    # Torch nearest-centroid ambiguity / violation scan (same decision rule as the pure helper).
    from hyperlexical.classification_v2_separability_audit import AMBIGUOUS_MARGIN
    ambiguous = {family: [] for family in ACTIVE_FAMILY_VOCABULARY}
    violating = {family: [] for family in ACTIVE_FAMILY_VOCABULARY}
    centroid_mat = torch.stack(
        [
            torch.tensor(centroids[family], dtype=torch.float32, device=device)
            for family in ACTIVE_FAMILY_VOCABULARY
        ]
    )
    centroid_mat = _torch_unit(centroid_mat)
    for family_index, family in enumerate(ACTIVE_FAMILY_VOCABULARY):
        if not train_vectors[family]:
            continue
        mat = _torch_unit(torch.tensor(train_vectors[family], dtype=torch.float32, device=device))
        scores = mat @ centroid_mat.T
        best_scores, best_idx = scores.max(dim=1)
        # second best
        neg = scores.clone()
        neg[torch.arange(scores.shape[0], device=device), best_idx] = -2.0
        second_scores, second_idx = neg.max(dim=1)
        for row_index in range(mat.shape[0]):
            best_family = ACTIVE_FAMILY_VOCABULARY[int(best_idx[row_index].item())]
            second_family = ACTIVE_FAMILY_VOCABULARY[int(second_idx[row_index].item())]
            row = {
                "best_family": best_family,
                "best_score": _scalar(best_scores[row_index].item()),
                "identity": train_ids[family][row_index],
                "second_family": second_family,
                "second_score": _scalar(second_scores[row_index].item()),
                "text": train_texts[family][row_index],
            }
            if best_family != family:
                violating[family].append(row)
            if abs(best_scores[row_index].item() - second_scores[row_index].item()) <= AMBIGUOUS_MARGIN:
                ambiguous[family].append(row)

    print("pairwise separability", flush=True)
    pair_rows = []
    for index_a, family_a in enumerate(ACTIVE_FAMILY_VOCABULARY):
        for family_b in ACTIVE_FAMILY_VOCABULARY[index_a + 1 :]:
            lexical = lexical_pair_report(train_texts[family_a], train_texts[family_b])
            embedding = torch_embedding_pair_report(
                train_vectors[family_a],
                train_vectors[family_b],
                sealed["anchors"][family_a],
                sealed["anchors"][family_b],
                left_weights=train_weights[family_a],
                right_weights=train_weights[family_b],
            )
            probe = torch_pairwise_probe(
                train_vectors[family_a],
                train_vectors[family_b],
                val_vectors[family_a],
                val_vectors[family_b],
                train_left_weights=train_weights[family_a],
                train_right_weights=train_weights[family_b],
            )
            flags = classify_pair_flags(
                n_a=support[family_a]["n"],
                n_b=support[family_b]["n"],
                lexical=lexical,
                embedding=embedding,
                probe=probe,
            )
            pair_rows.append(
                {
                    "embedding": embedding,
                    "family_a": family_a,
                    "family_b": family_b,
                    "flags": flags,
                    "lexical": lexical,
                    "n_train_a": support[family_a]["n"],
                    "n_train_b": support[family_b]["n"],
                    "probe": probe,
                }
            )

    matrices = assemble_pair_matrices(ACTIVE_FAMILY_VOCABULARY, pair_rows)
    pair_flags_by_family: dict[str, list[list[str]]] = {
        family: [] for family in ACTIVE_FAMILY_VOCABULARY
    }
    for row in pair_rows:
        pair_flags_by_family[row["family_a"]].append(row["flags"])
        pair_flags_by_family[row["family_b"]].append(row["flags"])

    family_status = {}
    suspected_label_noise = []
    for family in ACTIVE_FAMILY_VOCABULARY:
        noisy_rows = len(violating[family])
        family_status[family] = family_status_for(
            family,
            n_train=support[family]["n"],
            pair_flags=pair_flags_by_family[family],
            noisy_rows=noisy_rows,
        )
        for row in violating[family]:
            suspected_label_noise.append(
                {
                    "family": family,
                    "identity": row["identity"],
                    "nearest_family": row["best_family"],
                    "score": row["best_score"],
                    "text": row["text"],
                }
            )

    boundary_evidence = []
    for family in ACTIVE_FAMILY_VOCABULARY:
        competitors = {
            other: train_texts[other]
            for other in ACTIVE_FAMILY_VOCABULARY
            if other != family
        }
        boundary_evidence.append(
            boundary_evidence_for_family(
                family,
                train_texts[family],
                competitors,
                sealed_boundary=sealed_by_family.get(family),
                ambiguous_rows=ambiguous[family],
                violating_rows=violating[family],
            )
        )

    flag_counts: Counter[str] = Counter()
    for row in pair_rows:
        for flag in row["flags"]:
            flag_counts[flag] += 1
    decision = overall_decision(family_status, dict(flag_counts))
    worst = rank_worst_pairs(pair_rows, limit=25)
    refinements = propose_boundary_refinements(family_status, boundary_evidence, worst)

    remediation = []
    for family in ACTIVE_FAMILY_VOCABULARY:
        flat = [flag for flags in pair_flags_by_family[family] for flag in flags]
        dominant = [name for name, _count in Counter(flat).most_common(4)]
        remediation.append(remediation_for(family, family_status[family], dominant))

    sparse_treatment = []
    for family in SPARSE_FOCUS:
        related = [
            row
            for row in pair_rows
            if family in (row["family_a"], row["family_b"])
        ]
        best_lex = None
        best_probe = None
        if related:
            best_lex = min(
                related,
                key=lambda row: float(row["lexical"]["shared_token_ratio"]),
            )["lexical"]
            ok_probes = [row["probe"] for row in related if row["probe"]["status"] == "OK"]
            if ok_probes:
                best_probe = max(ok_probes, key=lambda probe: float(probe["f1"] or 0.0))
        sparse_treatment.append(
            sparse_family_treatment(
                family,
                n_train=support[family]["n"],
                n_val=support[family]["n_val_definitions"],
                lexical_pair_best=best_lex,
                probe_best=best_probe,
            )
        )

    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if sha256_file(REPAIR / "model.safetensors") != REPAIR_SHA:
        fail("geometry-repair checkpoint changed")

    # Keep the sealed artifact lean: store summary pair rows without full matrices.
    summary_pairs = []
    for row in pair_rows:
        summary_pairs.append(
            {
                "embedding": row["embedding"],
                "family_a": row["family_a"],
                "family_b": row["family_b"],
                "flags": row["flags"],
                "lexical": {
                    "shared_token_ratio": row["lexical"]["shared_token_ratio"],
                    "shared_high_frequency_tokens": row["lexical"]["shared_high_frequency_tokens"],
                    "tokens_enriched_in_a": row["lexical"]["tokens_enriched_in_a"],
                    "tokens_enriched_in_b": row["lexical"]["tokens_enriched_in_b"],
                    "distinctive_phrases_a": row["lexical"]["distinctive_phrases_a"],
                    "distinctive_phrases_b": row["lexical"]["distinctive_phrases_b"],
                },
                "n_train_a": row["n_train_a"],
                "n_train_b": row["n_train_b"],
                "probe": row["probe"],
            }
        )

    artifact = assemble_audit(
        {
            "boundary_evidence": boundary_evidence,
            "decision": decision,
            "embedding_matrix_sha256": matrices["embedding_matrix_sha256"],
            "family_status": family_status,
            "lexical_matrix_sha256": matrices["lexical_matrix_sha256"],
            "pair_flag_counts": dict(sorted(flag_counts.items())),
            "pair_rows": summary_pairs,
            "proposed_boundary_refinements": refinements,
            "remediation": remediation,
            "sparse_treatment": sparse_treatment,
            "support": support,
            "suspected_label_noise": suspected_label_noise[:100],
            "worst_collision_pairs": worst,
        }
    )
    artifact["contract"] = audit_contract()
    artifact["excluded_train_identities"] = train_bundle["excluded_identities"]
    artifact["excluded_val_identities"] = val_bundle["excluded_identities"]
    artifact["n_pairs"] = len(pair_rows)
    artifact["collapse_cluster_statuses"] = {
        family: family_status[family] for family in COLLAPSE_CLUSTER
    }
    # Re-hash after optional diagnostic fields that are part of the sealed record.
    from hyperlexical.classification_v2 import canonical_json, sha256_text

    artifact["artifact_sha256"] = sha256_text(
        canonical_json({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    )

    DESTINATION.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    DESTINATION.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    matrices_path = DESTINATION.with_name("SEPARABILITY_MATRICES.json")
    matrices_path.write_text(
        json.dumps(
            {
                "embedding_matrix": matrices["embedding_matrix"],
                "embedding_matrix_sha256": matrices["embedding_matrix_sha256"],
                "lexical_matrix": matrices["lexical_matrix"],
                "lexical_matrix_sha256": matrices["lexical_matrix_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"destination": str(DESTINATION), "decision": decision, "artifact_sha256": artifact["artifact_sha256"]}, indent=2))
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
        "-w",
        str(REPO),
        "-e",
        "PYTHONPATH=/home/morpheus/Hyperlex/scripts/shadow",
        IMAGE,
        "python3",
        str(script),
        "--inner",
    ]
    print(" ".join(command), flush=True)
    return subprocess.call(command)


if __name__ == "__main__":
    if "--inner" in sys.argv:
        raise SystemExit(inner())
    raise SystemExit(outer())
