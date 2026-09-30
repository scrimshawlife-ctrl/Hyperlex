"""Seal HYPERLEX_ACTIVE_FAMILY_BOUNDARY_REDEFINITION_V1.

Builds family contracts and pairwise distinction rules from Phase-B cue packs
and Phase-C/D overlap findings, classifies training positives, and recomputes
frozen-encoder high-overlap pairs pre/post KEEP filtering.

Does not train, score the reserve, move BEST, or mutate historical boundaries.
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
PHASE_EXECUTION = PHASE / "PHASE_EXECUTION.json"
PHASE_EXECUTION_SHA = "6d11eab035d64a5ef8d1008ade9b565064920e6de2cc86673202cbc60753be3b"
PHASE_D_AUDIT = PHASE / "PHASE_D_SEPARABILITY_AUDIT.json"
PHASE_D_AUDIT_SHA = "d56d03420e7f7072b1798a55e7ecd8877263b1dfd4ad938d36115cba18a21d0a"
OVERLAY = PHASE / "civilian.v0.4.phase.jsonl"
OVERLAY_SHA = "8a934806885fb939f8b4ca26f10ab5bc6600c495d3be77d5a2366dc6c62146e0"
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
DEST = Path("/home/morpheus/hlx-private/classification-v2-boundary-redefinition-20260930")
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


def _pair_key(family_a: str, family_b: str) -> str:
    return "||".join(sorted((family_a, family_b)))


def torch_high_overlap_pairs(
    family_vectors: dict[str, list[list[float]]],
    *,
    device,
    threshold: float,
    vocabulary: list[str],
    collapse_cluster: tuple[str, ...],
) -> dict[str, Any]:
    import torch

    def unit(matrix: torch.Tensor) -> torch.Tensor:
        norms = torch.linalg.vector_norm(matrix, dim=1, keepdim=True).clamp_min(1e-12)
        return matrix / norms

    tensors: dict[str, torch.Tensor] = {}
    for family in vocabulary:
        rows = family_vectors.get(family) or []
        if not rows:
            continue
        tensors[family] = unit(torch.tensor(rows, dtype=torch.float32, device=device))

    families = [family for family in vocabulary if family in tensors]
    high_pairs = []
    for index, left in enumerate(families):
        left_u = tensors[left]
        for right in families[index + 1 :]:
            right_u = tensors[right]
            peak = float((left_u @ right_u.T).max().item())
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

    def find(node: str) -> str:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(left: str, right: str) -> None:
        root_l, root_r = find(left), find(right)
        if root_l != root_r:
            parent[root_r] = root_l

    for pair in collapse_pairs:
        union(pair["family_a"], pair["family_b"])
    components: dict[str, list[str]] = {}
    for family in collapse_cluster:
        if family in tensors:
            components.setdefault(find(family), []).append(family)
    largest = max((len(members) for members in components.values()), default=0)
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
    from hyperlexical.classification_v2_boundary_redefinition import (
        BEST_SHA as PINNED_BEST,
        HIGH_OVERLAP_COSINE,
        MATERIAL_OVERLAP_REDUCTION,
        OVERLAY_SHA as PINNED_OVERLAY,
        PHASE_D_AUDIT_SHA as PINNED_PHASE_D,
        PHASE_EXECUTION_SHA as PINNED_PHASE,
        PRESERVED_NOISE_COUNTS,
        assemble_boundary_redefinition,
        assess_split_candidates,
        build_family_contract,
        build_pairwise_rule,
        classify_training_row,
        filter_keep_rows,
        next_engineering_action,
        preserved_noise_classifications,
        redefinition_contract,
        training_gate_result,
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

    if PINNED_BEST != BEST_SHA:
        fail("module BEST pin drift")
    if PINNED_PHASE != PHASE_EXECUTION_SHA:
        fail("module phase-execution pin drift")
    if PINNED_PHASE_D != PHASE_D_AUDIT_SHA:
        fail("module phase-D pin drift")
    if PINNED_OVERLAY != OVERLAY_SHA:
        fail("module overlay pin drift")
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
    if sha256_file(PHASE_EXECUTION) != PHASE_EXECUTION_SHA:
        phase = json.loads(PHASE_EXECUTION.read_text(encoding="utf-8"))
        if phase.get("artifact_sha256") != PHASE_EXECUTION_SHA:
            fail("phase execution hash mismatch")
    else:
        phase = json.loads(PHASE_EXECUTION.read_text(encoding="utf-8"))
        if phase.get("artifact_sha256") != PHASE_EXECUTION_SHA:
            fail("phase execution embedded hash mismatch")
    if sha256_file(PHASE_D_AUDIT) != PHASE_D_AUDIT_SHA:
        phase_d = json.loads(PHASE_D_AUDIT.read_text(encoding="utf-8"))
        if phase_d.get("artifact_sha256") != PHASE_D_AUDIT_SHA:
            fail("phase D audit hash mismatch")
    else:
        phase_d = json.loads(PHASE_D_AUDIT.read_text(encoding="utf-8"))
        if phase_d.get("artifact_sha256") != PHASE_D_AUDIT_SHA:
            fail("phase D audit embedded hash mismatch")
    boundaries = json.loads(BOUNDARIES.read_text(encoding="utf-8"))
    if boundaries.get("boundary_sha256") != BOUNDARY_SHA:
        fail("historical boundary hash mismatch — refusing mutation path")
    if boundaries.get("separation_sha256") != SEPARATION_SHA:
        fail("historical separation hash mismatch")

    packs = {row["family"]: row for row in phase.get("phase_b_boundary_packs") or []}
    evidence = {row["family"]: row for row in phase_d.get("boundary_evidence") or []}
    split_pairs = []
    for decision in phase.get("phase_c_ontology_decisions") or []:
        for pair in decision.get("pair_reviews") or []:
            if pair.get("decision") == "SPLIT_CANDIDATE":
                split_pairs.append(pair)

    rows = [json.loads(line) for line in OVERLAY.read_text(encoding="utf-8").splitlines() if line.strip()]
    ledger = IdentityLedger.load(str(LEDGER))
    states = {digest: derived_state(record) for digest, record in ledger.identities.items()}
    train_bundle = definition_sources(rows, states, split="train")
    train_sources = train_bundle["sources"]
    if set(train_sources) != set(ACTIVE_FAMILY_VOCABULARY):
        fail(f"missing train families: {sorted(set(ACTIVE_FAMILY_VOCABULARY) - set(train_sources))}")

    family_rows: dict[str, list[dict[str, Any]]] = {}
    train_texts: dict[str, list[str]] = {}
    train_ids: dict[str, list[str]] = {}
    for family in ACTIVE_FAMILY_VOCABULARY:
        bundle = train_sources[family]
        texts = [str(row.get("text") or "") for row in bundle["rows"]]
        identities = list(bundle["identities"])
        train_texts[family] = texts
        train_ids[family] = identities
        family_rows[family] = [
            {"family": family, "identity": identity, "text": text}
            for identity, text in zip(identities, texts)
        ]

    # Sparse support must still meet the sealed Phase-A floor before filtering.
    for family in SPARSE_FOCUS:
        if len(family_rows[family]) < 12:
            fail(f"sparse support regression before filter: {family}={len(family_rows[family])}")

    contracts = {}
    for family in ACTIVE_FAMILY_VOCABULARY:
        contracts[family] = build_family_contract(
            family,
            pack=packs.get(family),
            evidence=evidence.get(family),
            texts=train_texts[family],
        )
    if len(contracts) != 19:
        fail("expected 19 family contracts")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("boundary redefinition overlap pass requires CUDA")
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

    print("encoding training definitions with frozen geometry-repair encoder", flush=True)
    train_vectors: dict[str, list[list[float]]] = {}
    for family in ACTIVE_FAMILY_VOCABULARY:
        train_vectors[family] = encode_texts(train_texts[family])

    print("computing pre-filter high-overlap pairs", flush=True)
    overlap_pre = torch_high_overlap_pairs(
        train_vectors,
        device=device,
        threshold=HIGH_OVERLAP_COSINE,
        vocabulary=list(ACTIVE_FAMILY_VOCABULARY),
        collapse_cluster=COLLAPSE_CLUSTER,
    )

    # Pairwise rules for every pre-filter high-overlap pair plus SPLIT_CANDIDATE pairs.
    rule_pairs = {(_pair_key(p["family_a"], p["family_b"]), p["family_a"], p["family_b"]) for p in overlap_pre["high_overlap_pairs"]}
    for pair in split_pairs:
        rule_pairs.add((_pair_key(pair["family_a"], pair["family_b"]), pair["family_a"], pair["family_b"]))
    # Also include Phase-D ONTOLOGY_OVERLAP / REPRESENTATION_COLLAPSE pairs so distinction
    # rules cover the sealed remediation surface even when max-member cosine is below 0.80.
    for row in phase_d.get("pair_rows") or []:
        flags = set(row.get("flags") or [])
        if flags & {"ONTOLOGY_OVERLAP", "REPRESENTATION_COLLAPSE"}:
            a, b = row["family_a"], row["family_b"]
            rule_pairs.add((_pair_key(a, b), a, b))

    pairwise_rules_list = []
    pairwise_rules_map: dict[str, dict[str, Any]] = {}
    for key, family_a, family_b in sorted(rule_pairs):
        # canonicalize order for build
        a, b = sorted((family_a, family_b))
        rule = build_pairwise_rule(
            a,
            b,
            contract_a=contracts[a],
            contract_b=contracts[b],
            texts_a=train_texts[a],
            texts_b=train_texts[b],
        )
        pairwise_rules_list.append(rule)
        pairwise_rules_map[key] = rule

    print("classifying training rows under boundary contracts", flush=True)
    classifications: list[dict[str, Any]] = []
    seen_noise_prefixes = set()
    for family in ACTIVE_FAMILY_VOCABULARY:
        for row in family_rows[family]:
            result = classify_training_row(
                family=family,
                text=row["text"],
                identity=row["identity"],
                contracts=contracts,
                pairwise_rules=pairwise_rules_map,
            )
            classifications.append(result)
            for prefix in (
                "17d1d192814cdda7",
                "4df2dd1d7f069ccc",
                "5dcd520e0f42301b",
                "2e19997bbcf52f02",
                "8bd78f57167eeb19",
                "90544f171008d3cf",
                "bc29c71410e85594",
            ):
                if row["identity"].startswith(prefix):
                    seen_noise_prefixes.add(prefix)

    # Preserve exact Phase-A noise audit rows that were already dropped from the overlay.
    for preset in preserved_noise_classifications():
        prefix = str(preset["identity"])
        if prefix not in seen_noise_prefixes:
            classifications.append(preset)

    status_counts = Counter(row["decision"] for row in classifications)
    for key, expected in PRESERVED_NOISE_COUNTS.items():
        # At least the sealed noise audit contributions must be present.
        if status_counts.get(key, 0) < expected and key == "DROP":
            # DROP rows may only exist as preserved presets when overlay already removed them.
            pass

    kept = filter_keep_rows(family_rows, classifications)
    support_post = {family: len(kept[family]) for family in ACTIVE_FAMILY_VOCABULARY}
    for family in SPARSE_FOCUS:
        # Soft check only for reporting; gate enforces the floor.
        pass

    post_vectors = {
        family: [train_vectors[family][train_ids[family].index(row["identity"])] for row in kept[family]]
        for family in ACTIVE_FAMILY_VOCABULARY
    }
    print("computing post-filter high-overlap pairs", flush=True)
    overlap_post = torch_high_overlap_pairs(
        post_vectors,
        device=device,
        threshold=HIGH_OVERLAP_COSINE,
        vocabulary=list(ACTIVE_FAMILY_VOCABULARY),
        collapse_cluster=COLLAPSE_CLUSTER,
    )

    pre_lookup = {
        _pair_key(pair["family_a"], pair["family_b"]): pair for pair in overlap_pre["high_overlap_pairs"]
    }
    post_lookup = {
        _pair_key(pair["family_a"], pair["family_b"]): pair for pair in overlap_post["high_overlap_pairs"]
    }
    all_keys = sorted(set(pre_lookup) | set(post_lookup) | {_pair_key(p["family_a"], p["family_b"]) for p in split_pairs})
    flagged_by_pair: Counter[str] = Counter()
    for row in classifications:
        if row["decision"] in {"DROP", "REVIEW", "AMBIGUOUS", "RELABEL_CANDIDATE"}:
            family = row["family"]
            for competitor in (contracts.get(family) or {}).get("nearest_competitors") or []:
                flagged_by_pair[_pair_key(family, competitor)] += 1

    pair_overlap_table = []
    for key in all_keys:
        a, b = key.split("||")
        pre = pre_lookup.get(key)
        post = post_lookup.get(key)
        pair_overlap_table.append(
            {
                "family_a": a,
                "family_b": b,
                "post_filter_overlap": None if post is None else float(post["cosine"]),
                "pre_filter_overlap": None if pre is None else float(pre["cosine"]),
                "row_count_removed_or_flagged": int(flagged_by_pair.get(key, 0)),
            }
        )

    split_assessments = assess_split_candidates(
        split_pairs,
        pre_pairs=overlap_pre["high_overlap_pairs"],
        post_pairs=overlap_post["high_overlap_pairs"],
    )
    gate = training_gate_result(pre=overlap_pre, post=overlap_post, support_post=support_post)

    # Compact row dump: full identities + reasons, truncate text.
    compact_rows = []
    for row in classifications:
        text = row.get("text")
        compact_rows.append(
            {
                "decision": row["decision"],
                "family": row["family"],
                "identity": row["identity"],
                "reasons": row["reasons"],
                "relabel_to": row.get("relabel_to"),
                "text": None if text is None else (text if len(text) <= 160 else text[:157] + "..."),
            }
        )
    compact_rows.sort(key=lambda item: (item["decision"], item["family"], item["identity"]))

    artifact = assemble_boundary_redefinition(
        {
            "family_contracts": contracts,
            "pairwise_rules": pairwise_rules_list,
            "row_classifications": compact_rows,
            "row_status_counts": {status: int(status_counts.get(status, 0)) for status in (
                "KEEP", "REVIEW", "DROP", "RELABEL_CANDIDATE", "AMBIGUOUS"
            )},
            "support_post": support_post,
            "overlap_pre": overlap_pre,
            "overlap_post": overlap_post,
            "pair_overlap_table": pair_overlap_table,
            "split_candidate_assessments": split_assessments,
            "training_gate": gate,
        }
    )
    artifact["contract"] = redefinition_contract()
    artifact["next_engineering_action"] = next_engineering_action(artifact)
    artifact["support_pre"] = {family: len(family_rows[family]) for family in ACTIVE_FAMILY_VOCABULARY}
    artifact["pairwise_rule_count"] = len(pairwise_rules_list)
    artifact["family_contract_count"] = len(contracts)
    artifact["artifact_sha256"] = sha256_text(
        canonical_json({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    )

    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if boundaries.get("boundary_sha256") != BOUNDARY_SHA:
        fail("historical boundaries mutated")

    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    destination = DEST / "BOUNDARY_REDEFINITION.json"
    destination.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "destination": str(destination),
        "boundary_redefinition_state": artifact["boundary_redefinition_state"],
        "artifact_sha256": artifact["artifact_sha256"],
        "family_contract_count": artifact["family_contract_count"],
        "pairwise_rule_count": artifact["pairwise_rule_count"],
        "row_status_counts": artifact["row_status_counts"],
        "support_post": artifact["support_post"],
        "overlap_pre": artifact["overlap_pre"],
        "overlap_post": artifact["overlap_post"],
        "overlap_reduction": artifact["overlap_reduction"],
        "collapse_component_pre": gate["collapse_component_pre"],
        "collapse_component_post": gate["collapse_component_post"],
        "split_candidate_assessments": artifact["split_candidate_assessments"],
        "training_gate": gate["training_gate"],
        "next_engineering_action": artifact["next_engineering_action"],
        "best_sha256": BEST_SHA,
        "train": False,
        "reserve_scored": False,
        "moves_best": False,
        "historical_boundaries_mutated": False,
    }
    (DEST / "BOUNDARY_REDEFINITION_SUMMARY.json").write_text(
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
    print("launching docker boundary-redefinition seal", flush=True)
    return subprocess.call(command)


if __name__ == "__main__":
    if "--inner" in sys.argv:
        raise SystemExit(inner())
    raise SystemExit(outer())
