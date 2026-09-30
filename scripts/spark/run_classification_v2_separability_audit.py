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
        embedding_pair_report,
        family_status_for,
        find_ambiguous_and_violating_rows,
        lexical_pair_report,
        overall_decision,
        pairwise_probe,
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

    def encode_texts(texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        with torch.no_grad():
            for text in texts:
                encoded = tokenizer(
                    text,
                    truncation=True,
                    max_length=MAX_LEN,
                    padding=False,
                    return_tensors="pt",
                )
                encoded = {key: value.to(device) for key, value in encoded.items()}
                pooled = encoder(**encoded).last_hidden_state[:, 0][0].detach().cpu().tolist()
                out.append(pooled)
        return out

    train_texts: dict[str, list[str]] = {}
    train_ids: dict[str, list[str]] = {}
    train_weights: dict[str, list[float]] = {}
    train_vectors: dict[str, list[list[float]]] = {}
    val_texts: dict[str, list[str]] = {}
    val_vectors: dict[str, list[list[float]]] = {}
    support: dict[str, dict[str, int]] = {}
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
    ambiguous, violating = find_ambiguous_and_violating_rows(
        train_vectors,
        train_ids,
        train_texts,
        centroids,
    )

    pair_rows = []
    for index_a, family_a in enumerate(ACTIVE_FAMILY_VOCABULARY):
        for family_b in ACTIVE_FAMILY_VOCABULARY[index_a + 1 :]:
            lexical = lexical_pair_report(train_texts[family_a], train_texts[family_b])
            embedding = embedding_pair_report(
                train_vectors[family_a],
                train_vectors[family_b],
                sealed["anchors"][family_a],
                sealed["anchors"][family_b],
                left_weights=train_weights[family_a],
                right_weights=train_weights[family_b],
            )
            probe = pairwise_probe(
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
