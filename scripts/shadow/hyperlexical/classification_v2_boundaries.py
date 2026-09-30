"""Multi-anchor semantic boundaries for the 19 active families.

A family is a set of frozen anchors plus explicit boundaries. The canonical
semantic score is the maximum cosine to that family's anchors, not the mean
of every member. This module does not train, fetch, or read the evaluation
reserve.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from .classification_v2 import (
    ACTIVE_FAMILY_VOCABULARY,
    ClassificationContractError,
    canonical_json,
    sha256_text,
    _f32_hash,
)
from .classification_v2_prototype import (
    PROTOTYPE_WEIGHT,
    _f32_round,
    _markup_text,
    _prose,
    _unit,
    cosine_matrix,
    weighted_mean,
)
from .holdout_guard import normalized_text_sha256

BOUNDARY_SCHEMA = "hyperlex.classification.v2.family_semantic_boundaries.v1"
BOUNDARY_RULE = "HYPERLEX_FAMILY_SEMANTIC_BOUNDARIES_V1"
CLUSTER_SEED = 0
CLUSTER_MAX_ITERATIONS = 32
SILHOUETTE_MIN = 0.20
ANCHOR_MIN = 1
ANCHOR_MAX = 5
COLLISION_COSINE = 0.80
NEAREST_COMPETITORS = 3
FACET_LIMIT = 4
REPRESENTATIVE_LIMIT = 3
SUPPORT_SPARSE = "SPARSE"
SUPPORT_OK = "SUPPORTED"
CLASSIFICATION_TASKS = frozenset({"classify", "classify+unbind"})
BLOCKED_IDENTITY_STATES = frozenset({"EVAL_RESERVE", "EVAL_SPENT", "EVAL_BOUND"})
BLOCKED_SURFACES = frozenset({"evaluation_reserve", "held_out", "measurement", "settlement", "test"})
SOURCE_RULE = "training_definition_text_classify_split_only"
REJECTED_REPRESENTATION = "single_family_centroid"
CANONICAL_REPRESENTATION = "multi_anchor"
_TOKEN = re.compile(r"[a-z]{4,}")
_STOPWORDS = frozenset(
    {
        "about", "above", "after", "again", "against", "all", "also", "among",
        "and", "another", "any", "are", "around", "because", "been", "before",
        "being", "below", "between", "both", "but", "can", "could", "does",
        "doing", "down", "during", "each", "else", "especially", "every",
        "from", "further", "generally", "have", "having", "here", "hers",
        "herself", "himself", "into", "itself", "just", "more", "most",
        "much", "must", "none", "only", "onto", "other", "others", "otherwise",
        "over", "same", "shall", "should", "some", "someone", "something",
        "such", "than", "that", "their", "theirs", "them", "themselves",
        "then", "there", "these", "they", "this", "those", "through", "under",
        "until", "used", "using", "usually", "very", "what", "when", "where",
        "which", "while", "whom", "whose", "will", "with", "within", "without",
        "would", "your",
    }
)


def anchor_count_bounds(n: int) -> dict[str, Any]:
    """Support band first. Cluster search applies only when ``k_max`` is set."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", "support")
    if n <= 2:
        return {"fixed_k": 1, "k_max": None, "support_status": SUPPORT_SPARSE}
    if n <= 5:
        return {"fixed_k": 2, "k_max": None, "support_status": SUPPORT_OK}
    if n <= 11:
        k_max = 3
    elif n <= 23:
        k_max = 4
    else:
        k_max = 5
    return {"fixed_k": None, "k_max": k_max, "support_status": SUPPORT_OK}


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _clamp_cosine(value: float) -> float:
    if value > 1.0:
        return 1.0
    if value < -1.0:
        return -1.0
    return value


def _member_unit(member: Mapping[str, Any]) -> list[float]:
    return _f32_round(_unit(member["vector"]))


def _centroid(members: Sequence[Mapping[str, Any]]) -> list[float]:
    mean = weighted_mean(
        [_member_unit(member) for member in members],
        [float(member["weight"]) for member in members],
    )
    return _f32_round(_unit(mean))


def _repair(
    units: Sequence[Sequence[float]],
    clusters: list[list[int]],
    identities: Sequence[str],
) -> list[list[int]]:
    """Fill empty clusters, then raise singletons when the point count allows it."""
    guard = 0
    limit = max(1, len(identities) * 2)
    while guard < limit:
        guard += 1
        empty = [index for index, cluster in enumerate(clusters) if not cluster]
        small = [index for index, cluster in enumerate(clusters) if len(cluster) == 1]
        if not empty and not small:
            break
        if not empty and len(identities) < 2 * len(clusters):
            break
        target = empty[0] if empty else small[0]
        donor_floor = 1 if empty else 2
        donors = [
            index
            for index, cluster in enumerate(clusters)
            if index != target and len(cluster) > donor_floor
        ]
        if not donors:
            break
        donors.sort(key=lambda index: (-len(clusters[index]), min(identities[i] for i in clusters[index])))
        donor = donors[0]
        donor_members = [units[index] for index in clusters[donor]]
        donor_centroid = _centroid(
            [
                {"vector": units[index], "weight": 1.0}
                for index in clusters[donor]
            ]
        )
        if clusters[target]:
            target_centroid = _centroid(
                [{"vector": units[index], "weight": 1.0} for index in clusters[target]]
            )
            pick = min(
                clusters[donor],
                key=lambda index: (-_clamp_cosine(_dot(units[index], target_centroid)), identities[index]),
            )
        else:
            pick = min(
                clusters[donor],
                key=lambda index: (_clamp_cosine(_dot(units[index], donor_centroid)), identities[index]),
            )
        del donor_members
        clusters[donor].remove(pick)
        clusters[target].append(pick)
    return clusters


def cluster_indices(
    units: Sequence[Sequence[float]],
    identities: Sequence[str],
    weights: Sequence[float],
    k: int,
) -> list[list[int]]:
    """Farthest-first spherical k-means. Ties break by lowest identity hash."""
    count = len(units)
    if k < 1 or k > count or len(identities) != count or len(weights) != count:
        raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", "cluster_shape")
    if len(set(identities)) != count:
        raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", "duplicate_identity")
    order = sorted(range(count), key=lambda index: identities[index])
    seeds = [order[0]]
    while len(seeds) < k:
        remaining = [index for index in order if index not in seeds]
        seeds.append(
            min(
                remaining,
                key=lambda index: (
                    max(_clamp_cosine(_dot(units[index], units[seed])) for seed in seeds),
                    identities[index],
                ),
            )
        )
    centroids = [list(units[seed]) for seed in seeds]
    previous: tuple[tuple[int, ...], ...] | None = None
    clusters: list[list[int]] = [[] for _seed in seeds]
    for _iteration in range(CLUSTER_MAX_ITERATIONS):
        clusters = [[] for _seed in seeds]
        for index in range(count):
            choice = min(
                range(k),
                key=lambda slot: (-_clamp_cosine(_dot(units[index], centroids[slot])), slot),
            )
            clusters[choice].append(index)
        clusters = _repair(units, clusters, identities)
        signature = tuple(tuple(sorted(cluster)) for cluster in clusters)
        centroids = []
        for cluster in clusters:
            if not cluster:
                raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", "empty_cluster")
            centroids.append(
                _centroid(
                    [{"vector": units[index], "weight": weights[index]} for index in cluster]
                )
            )
        if signature == previous:
            break
        previous = signature
    ordered = sorted(clusters, key=lambda cluster: min(identities[index] for index in cluster))
    return [sorted(cluster, key=lambda index: identities[index]) for cluster in ordered]


def mean_silhouette(units: Sequence[Sequence[float]], clusters: Sequence[Sequence[int]]) -> float:
    if len(clusters) < 2:
        return 0.0
    scores: list[float] = []
    for cluster in clusters:
        for index in cluster:
            if len(cluster) == 1:
                scores.append(0.0)
                continue
            intra = [
                1.0 - _clamp_cosine(_dot(units[index], units[other]))
                for other in cluster
                if other != index
            ]
            cohesion = sum(intra) / len(intra)
            separation = None
            for other_cluster in clusters:
                if other_cluster is cluster or not other_cluster:
                    continue
                distance = sum(
                    1.0 - _clamp_cosine(_dot(units[index], units[other])) for other in other_cluster
                ) / len(other_cluster)
                if separation is None or distance < separation:
                    separation = distance
            if separation is None:
                scores.append(0.0)
                continue
            scale = cohesion if cohesion > separation else separation
            scores.append(0.0 if scale == 0.0 else (separation - cohesion) / scale)
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def choose_anchor_count(members: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Smallest adequately separated ``k``. Identical inputs follow the support band."""
    prepared = _prepare(members)
    bounds = anchor_count_bounds(len(prepared))
    units = [_member_unit(member) for member in prepared]
    identities = [str(member["identity"]) for member in prepared]
    weights = [float(member["weight"]) for member in prepared]
    trace: list[dict[str, Any]] = []
    if bounds["fixed_k"] is not None:
        k = int(bounds["fixed_k"])
    else:
        k = 2
        k_max = int(bounds["k_max"])
        for candidate in range(2, k_max + 1):
            grouped = cluster_indices(units, identities, weights, candidate)
            silhouette = mean_silhouette(units, grouped)
            supports = [len(group) for group in grouped]
            accepted = min(supports) >= 2 and silhouette >= SILHOUETTE_MIN
            trace.append(
                {
                    "accepted": accepted,
                    "k": candidate,
                    "min_support": min(supports),
                    "silhouette": silhouette,
                }
            )
            if accepted:
                k = candidate
                break
        else:
            k = 2
    if not ANCHOR_MIN <= k <= ANCHOR_MAX:
        raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", "anchor_bounds")
    return {
        "k": k,
        "n": len(prepared),
        "random_seed": CLUSTER_SEED,
        "support_status": bounds["support_status"],
        "trace": trace,
    }


def _prepare(members: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if not members:
        raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", "empty_family")
    ordered = sorted(members, key=lambda member: str(member["identity"]))
    prepared: list[dict[str, Any]] = []
    for member in ordered:
        identity = str(member["identity"])
        weight = float(member["weight"])
        if weight not in (1.0, 0.5):
            raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", "weight")
        prepared.append(
            {
                "class": str(member.get("class") or ""),
                "identity": identity,
                "text": str(member.get("text") or ""),
                "vector": _member_unit(member),
                "weight": weight,
            }
        )
    return prepared


def anchor_id_for(family: str, identities: Sequence[str]) -> str:
    body = {"family": family, "source_identity_hashes": sorted(identities)}
    return sha256_text(canonical_json(body))


def build_family_anchors(family: str, members: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    prepared = _prepare(members)
    decision = choose_anchor_count(prepared)
    units = [member["vector"] for member in prepared]
    identities = [member["identity"] for member in prepared]
    grouped = cluster_indices(units, identities, [member["weight"] for member in prepared], int(decision["k"]))
    anchors: list[dict[str, Any]] = []
    for group in grouped:
        chosen = [prepared[index] for index in group]
        vector = _centroid(chosen)
        source_ids = [member["identity"] for member in chosen]
        representatives = sorted(chosen, key=lambda member: (-float(member["weight"]), member["identity"]))[
            :REPRESENTATIVE_LIMIT
        ]
        anchors.append(
            {
                "anchor_id": anchor_id_for(family, source_ids),
                "centroid_hash": _f32_hash(vector),
                "family": family,
                "inferred_count": sum(1 for member in chosen if member["class"] == "INFERRED"),
                "observed_count": sum(1 for member in chosen if member["class"] == "OBSERVED"),
                "representative_examples": [
                    {
                        "class": member["class"],
                        "identity": member["identity"],
                        "text": member["text"],
                    }
                    for member in representatives
                ],
                "source_identity_hashes": sorted(source_ids),
                "support_count": len(chosen),
                "vector": vector,
            }
        )
    supports = [int(anchor["support_count"]) for anchor in anchors]
    if decision["support_status"] != SUPPORT_SPARSE and decision["n"] >= 4 and min(supports) < 2:
        raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", family)
    if sum(supports) != decision["n"]:
        raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", family)
    return {
        "anchors": anchors,
        "decision": decision,
        "family": family,
        "support_status": decision["support_status"],
    }


def _tokens(texts: Sequence[str]) -> list[str]:
    counts: dict[str, int] = {}
    for text in texts:
        seen: set[str] = set()
        for token in _TOKEN.findall(str(text).lower()):
            if token in _STOPWORDS or token in seen:
                continue
            seen.add(token)
            counts[token] = counts.get(token, 0) + 1
    return sorted(counts, key=lambda token: (-counts[token], token))


def distinguishing_tokens(left_texts: Sequence[str], right_texts: Sequence[str]) -> list[str]:
    right = set(_tokens(right_texts))
    return [token for token in _tokens(left_texts) if token not in right][:FACET_LIMIT]


def _family_texts(anchors: Sequence[Mapping[str, Any]]) -> list[str]:
    texts: list[str] = []
    seen: set[str] = set()
    for anchor in anchors:
        for example in anchor["representative_examples"]:
            identity = str(example["identity"])
            if identity in seen:
                continue
            seen.add(identity)
            texts.append(str(example["text"]))
    return texts


def _anchor_public(anchor: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "anchor_id": anchor["anchor_id"],
        "centroid_hash": anchor["centroid_hash"],
        "family": anchor["family"],
        "inferred_count": anchor["inferred_count"],
        "observed_count": anchor["observed_count"],
        "representative_identities": [item["identity"] for item in anchor["representative_examples"]],
        "source_identity_hashes": list(anchor["source_identity_hashes"]),
        "support_count": anchor["support_count"],
    }


def future_discriminator_contract() -> dict[str, Any]:
    """Specified for a later trainer. This pass does not fit it."""
    return {
        "alpha": 1.0,
        "anchors": "frozen",
        "beta": 1.0,
        "formula": "population_zscore(max_anchor_cosine)+population_zscore(residual)",
        "hard_negative_count": NEAREST_COMPETITORS,
        "hard_negative_multiplier": 2.0,
        "hard_negatives": "nearest_competing_anchors",
        "jev": "OFF",
        "rejected_semantic_score": REJECTED_REPRESENTATION,
        "representation": CANONICAL_REPRESENTATION,
        "residual": "learned_linear_logit",
        "semantic_score": "max_anchor_cosine",
        "train": False,
    }


def anchor_witness_sha256(families: Sequence[Mapping[str, Any]]) -> str:
    body = {
        "families": [
            {
                "anchors": [_anchor_public(anchor) for anchor in family["anchors"]],
                "family": family["family"],
                "k": len(family["anchors"]),
                "n": family["decision"]["n"],
                "support_status": family["support_status"],
            }
            for family in families
        ],
        "rule": BOUNDARY_RULE,
        "seed": CLUSTER_SEED,
    }
    return sha256_text(canonical_json(body))


def separation_sha256(rows: Sequence[Mapping[str, Any]]) -> str:
    return sha256_text(canonical_json({"rows": list(rows), "rule": BOUNDARY_RULE}))


def _cosine_pairs(
    families: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[list[float]]]:
    flat: list[dict[str, Any]] = []
    for family in families:
        for anchor in family["anchors"]:
            flat.append(anchor)
    matrix = cosine_matrix([anchor["vector"] for anchor in flat])
    rounded = [[_f32_round((value,))[0] for value in row] for row in matrix]
    return flat, rounded


def _best_cross(
    flat: Sequence[Mapping[str, Any]],
    matrix: Sequence[Sequence[float]],
    left: str,
    right: str,
) -> dict[str, Any]:
    best: tuple[tuple[float, str, str], float, str, str] | None = None
    for i, anchor in enumerate(flat):
        if anchor["family"] != left:
            continue
        for j, other in enumerate(flat):
            if other["family"] != right:
                continue
            cosine = float(matrix[i][j])
            left_id = str(anchor["anchor_id"])
            right_id = str(other["anchor_id"])
            rank = (-cosine, left_id, right_id)
            if best is None or rank < best[0]:
                best = (rank, cosine, str(anchor["anchor_id"]), str(other["anchor_id"]))
    if best is None:
        raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", "pair")
    return {
        "closest_anchor_pair": [best[2], best[3]],
        "cosine_similarity": best[1],
    }


def assemble_boundaries(
    family_members: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    vocabulary: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Build the sealed multi-anchor boundary artifact from prepared members."""
    vocab = tuple(vocabulary) if vocabulary is not None else ACTIVE_FAMILY_VOCABULARY
    if set(family_members) != set(vocab):
        missing = [family for family in vocab if family not in family_members]
        raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", missing or "coverage")
    built = [build_family_anchors(family, family_members[family]) for family in vocab]
    flat, matrix = _cosine_pairs(built)
    anchor_ids = [anchor["anchor_id"] for anchor in flat]
    collisions: list[dict[str, Any]] = []
    for i, left in enumerate(flat):
        for j in range(i + 1, len(flat)):
            cosine = float(matrix[i][j])
            if cosine < COLLISION_COSINE:
                continue
            right = flat[j]
            collisions.append(
                {
                    "anchor_a": left["anchor_id"],
                    "anchor_b": right["anchor_id"],
                    "cosine": cosine,
                    "family_a": left["family"],
                    "family_b": right["family"],
                    "same_family": left["family"] == right["family"],
                }
            )
    collisions.sort(key=lambda item: (-float(item["cosine"]), item["anchor_a"], item["anchor_b"]))
    max_similarity: dict[str, dict[str, float]] = {}
    min_distance: dict[str, dict[str, float]] = {}
    nearest: dict[str, list[dict[str, Any]]] = {}
    texts = {family["family"]: _family_texts(family["anchors"]) for family in built}
    boundaries: list[dict[str, Any]] = []
    for family in built:
        name = family["family"]
        scores: list[tuple[float, str, dict[str, Any]]] = []
        max_similarity[name] = {}
        min_distance[name] = {}
        for other in built:
            if other["family"] == name:
                continue
            cross = _best_cross(flat, matrix, name, other["family"])
            cosine = float(cross["cosine_similarity"])
            max_similarity[name][other["family"]] = cosine
            min_distance[name][other["family"]] = _f32_round((1.0 - cosine,))[0]
            scores.append((cosine, other["family"], cross))
        scores.sort(key=lambda item: (-item[0], item[1]))
        competitors = scores[:NEAREST_COMPETITORS]
        nearest[name] = [
            {"cosine": cosine, "family": other, "closest_anchor_pair": cross["closest_anchor_pair"]}
            for cosine, other, cross in competitors
        ]
        own_tokens = _tokens(texts[name])[:FACET_LIMIT]
        cues: list[str] = []
        exclusions: list[str] = []
        counterexamples: list[dict[str, str]] = []
        for cosine, other, cross in competitors:
            cues.extend(distinguishing_tokens(texts[name], texts[other]))
            other_only = distinguishing_tokens(texts[other], texts[name])
            own_word = own_tokens[0] if own_tokens else name
            other_word = other_only[0] if other_only else other
            exclusions.append(f"{other_word} ({other}) without {own_word}")
            anchor_id = cross["closest_anchor_pair"][1]
            example = _representative_for(built, other, anchor_id)
            counterexamples.append(
                {
                    "anchor_id": anchor_id,
                    "family": other,
                    "identity": example["identity"],
                    "text": example["text"],
                }
            )
        deduped_cues: list[str] = []
        for cue in cues:
            if cue not in deduped_cues:
                deduped_cues.append(cue)
        boundaries.append(
            {
                "counterexample_patterns": counterexamples,
                "distinguishing_cues": deduped_cues[:FACET_LIMIT],
                "exclude_when": exclusions,
                "family": name,
                "nearest_competitors": [{"cosine": item["cosine"], "family": item["family"]} for item in nearest[name]],
                "positive_facets": own_tokens,
            }
        )
    separation: list[dict[str, Any]] = []
    for left in vocab:
        for right in vocab:
            if left == right:
                continue
            cross = _best_cross(flat, matrix, left, right)
            cosine = float(cross["cosine_similarity"])
            evidence = [
                *[f"only_a:{token}" for token in distinguishing_tokens(texts[left], texts[right])],
                *[f"only_b:{token}" for token in distinguishing_tokens(texts[right], texts[left])],
            ]
            separation.append(
                {
                    "boundary_confidence": _f32_round((1.0 - cosine,))[0],
                    "closest_anchor_pair": cross["closest_anchor_pair"],
                    "collidable": cosine >= COLLISION_COSINE,
                    "cosine_similarity": cosine,
                    "family_a": left,
                    "family_b": right,
                    "known_distinguishing_evidence": evidence,
                }
            )
    competing_pairs = [
        item
        for item in collisions
        if not item["same_family"]
    ]
    artifact = {
        "anchor_count_rule": {
            "fallback_k": 2,
            "initialization": "farthest_first_lowest_identity_hash",
            "max_anchors": ANCHOR_MAX,
            "max_iterations": CLUSTER_MAX_ITERATIONS,
            "min_anchors": ANCHOR_MIN,
            "random_seed": CLUSTER_SEED,
            "rule": BOUNDARY_RULE,
            "silhouette_min": SILHOUETTE_MIN,
            "support_bands": "n<=2 => 1 SPARSE; 3<=n<=5 => 2; 6<=n<=11 => k_max 3; 12<=n<=23 => k_max 4; else k_max 5",
            "tie_break": "lowest_source_identity_hash",
        },
        "anchor_ids": anchor_ids,
        "anchor_cosine": matrix,
        "boundaries": boundaries,
        "collisions": collisions,
        "families": [
            {
                "anchors": family["anchors"],
                "family": family["family"],
                "k": len(family["anchors"]),
                "n": family["decision"]["n"],
                "support_status": family["support_status"],
                "trace": family["decision"]["trace"],
            }
            for family in built
        ],
        "family_max_similarity": max_similarity,
        "family_min_distance": min_distance,
        "future_discriminator": future_discriminator_contract(),
        "jev": "OFF",
        "nearest_competing_anchor_pairs": competing_pairs[:20],
        "nearest_competitors": nearest,
        "representation": CANONICAL_REPRESENTATION,
        "schema": BOUNDARY_SCHEMA,
        "separation": separation,
        "source_rule": SOURCE_RULE,
    }
    artifact["anchor_witness_sha256"] = anchor_witness_sha256(built)
    artifact["separation_sha256"] = separation_sha256(separation)
    artifact["boundary_sha256"] = boundary_sha256(artifact)
    return artifact


def _representative_for(
    families: Sequence[Mapping[str, Any]],
    family_name: str,
    anchor_id: str,
) -> dict[str, str]:
    for family in families:
        if family["family"] != family_name:
            continue
        for anchor in family["anchors"]:
            if anchor["anchor_id"] != anchor_id:
                continue
            example = anchor["representative_examples"][0]
            return {"identity": str(example["identity"]), "text": str(example["text"])}
    raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", anchor_id)


def boundary_sha256(artifact: Mapping[str, Any]) -> str:
    body = {
        "anchor_witness_sha256": artifact["anchor_witness_sha256"],
        "collisions": [
            {
                "anchor_a": item["anchor_a"],
                "anchor_b": item["anchor_b"],
                "cosine": item["cosine"],
                "family_a": item["family_a"],
                "family_b": item["family_b"],
            }
            for item in artifact["collisions"]
        ],
        "future_discriminator": artifact["future_discriminator"],
        "representation": artifact["representation"],
        "rule": BOUNDARY_RULE,
        "separation_sha256": artifact["separation_sha256"],
        "source_rule": artifact["source_rule"],
    }
    return sha256_text(canonical_json(body))


def assess_boundary_artifact(
    artifact: Mapping[str, Any],
    *,
    vocabulary: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Refuse a single-centroid witness as the v1 boundary representation."""
    vocab = tuple(vocabulary) if vocabulary is not None else ACTIVE_FAMILY_VOCABULARY
    try:
        if artifact.get("schema") != BOUNDARY_SCHEMA:
            raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", "schema")
        if artifact.get("representation") != CANONICAL_REPRESENTATION:
            raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", "representation")
        contract = artifact.get("future_discriminator")
        if contract != future_discriminator_contract():
            raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", "contract")
        if contract["rejected_semantic_score"] != REJECTED_REPRESENTATION:
            raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", "centroid")
        if contract["semantic_score"] != "max_anchor_cosine":
            raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", "centroid")
        families = list(artifact["families"])
        names = [family["family"] for family in families]
        if names != list(vocab):
            raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", "coverage")
        reserved = set(artifact.get("excluded_identities") or [])
        for family in families:
            k = int(family["k"])
            n = int(family["n"])
            if not ANCHOR_MIN <= k <= ANCHOR_MAX or k != len(family["anchors"]):
                raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", family["family"])
            if n <= 2:
                if family["support_status"] != SUPPORT_SPARSE or k != 1:
                    raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", family["family"])
            elif family["support_status"] != SUPPORT_OK or k < 2:
                raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", family["family"])
            supports = []
            for anchor in family["anchors"]:
                hashes = list(anchor["source_identity_hashes"])
                if anchor["anchor_id"] != anchor_id_for(family["family"], hashes):
                    raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", "anchor_id")
                if anchor["centroid_hash"] != _f32_hash(anchor["vector"]):
                    raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", "centroid_hash")
                if set(hashes) & reserved:
                    raise ClassificationContractError("evaluation_isolation")
                supports.append(int(anchor["support_count"]))
                if int(anchor["support_count"]) != len(hashes):
                    raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", "support")
            if sum(supports) != n:
                raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", family["family"])
            if n >= 4 and min(supports) < 2:
                raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", family["family"])
            if any(support < 1 for support in supports):
                raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", "empty_cluster")
        if artifact.get("anchor_witness_sha256") != anchor_witness_sha256(
            [
                {
                    "anchors": family["anchors"],
                    "decision": {"n": family["n"]},
                    "family": family["family"],
                    "support_status": family["support_status"],
                }
                for family in families
            ]
        ):
            raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", "anchor_witness")
        if artifact.get("separation_sha256") != separation_sha256(artifact["separation"]):
            raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", "separation")
        expected_pairs = len(vocab) * (len(vocab) - 1)
        if len(artifact["separation"]) != expected_pairs:
            raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", "separation")
        if artifact.get("boundary_sha256") != boundary_sha256(artifact):
            raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", "boundary_hash")
        if artifact.get("jev") != "OFF":
            raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", "jev")
    except (ClassificationContractError, KeyError, TypeError, ValueError) as exc:
        return {"pass": False, "reason": "FAMILY_BOUNDARY_UNAVAILABLE", "detail": str(exc)}
    return {
        "anchor_witness_sha256": artifact["anchor_witness_sha256"],
        "boundary_sha256": artifact["boundary_sha256"],
        "families": len(vocab),
        "pass": True,
        "separation_sha256": artifact["separation_sha256"],
    }


def _blocked_row(row: Mapping[str, Any], identity_state: Mapping[str, str]) -> str | None:
    if row.get("evaluation_reserve") or row.get("held_out"):
        return "row_flag"
    surface = str(row.get("surface") or "")
    if surface in BLOCKED_SURFACES:
        return "surface"
    stage = str(row.get("stage") or "")
    if stage in BLOCKED_SURFACES:
        return "surface"
    provenance = row.get("provenance")
    if isinstance(provenance, dict):
        if provenance.get("jev") or str(provenance.get("source") or "").lower() == "jev":
            return "jev"
    if row.get("jev"):
        return "jev"
    digest = normalized_text_sha256(str(row.get("text") or ""))
    if identity_state.get(digest) in BLOCKED_IDENTITY_STATES:
        return str(identity_state[digest])
    return None


def boundary_training_sources(
    rows: Sequence[Mapping[str, Any]],
    identity_state: Mapping[str, str] | None = None,
    *,
    vocabulary: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Training-split definition text for every active family.

    Stored definition prose is the source when the row text is that prose.
    Exact-copy families have no stored definition, so their classification
    prose is the training definition. Validation, reserve, spent, held-out,
    measurement, and Jev rows are not sources.
    """
    from .classification_v2 import EXACT_COPY_FAMILIES
    from .classification_v2_surface import SURFACE_PROSE, surface_form

    vocab = tuple(vocabulary) if vocabulary is not None else ACTIVE_FAMILY_VOCABULARY
    states = identity_state or {}
    grouped: dict[str, dict[str, Mapping[str, Any]]] = {family: {} for family in vocab}
    excluded: list[dict[str, str]] = []
    for row in rows:
        if row.get("split") != "train":
            continue
        lineage = str(row.get("lineage") or "")
        if lineage not in grouped or row.get("class") not in PROTOTYPE_WEIGHT:
            continue
        if str(row.get("task") or "") not in CLASSIFICATION_TASKS:
            continue
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        if lineage in EXACT_COPY_FAMILIES:
            if _markup_text(text) or surface_form(text) != SURFACE_PROSE:
                continue
        else:
            prose = _prose(row)
            if not prose or text != prose:
                continue
        digest = normalized_text_sha256(text)
        reason = _blocked_row(row, states)
        if reason is not None:
            excluded.append({"identity": digest, "reason": reason})
            continue
        current = grouped[lineage].get(digest)
        if current is not None and current.get("class") == "OBSERVED":
            continue
        if current is not None and row.get("class") != "OBSERVED":
            continue
        grouped[lineage][digest] = row
    sources: dict[str, dict[str, Any]] = {}
    for family in vocab:
        items = sorted(grouped[family].items(), key=lambda item: item[0])
        if not items:
            continue
        sources[family] = {
            "identities": [digest for digest, _row in items],
            "inferred": sum(1 for _digest, row in items if row.get("class") == "INFERRED"),
            "observed": sum(1 for _digest, row in items if row.get("class") == "OBSERVED"),
            "rows": [row for _digest, row in items],
            "weights": [PROTOTYPE_WEIGHT[str(row.get("class"))] for _digest, row in items],
        }
    return {
        "excluded_identities": sorted({item["identity"] for item in excluded}),
        "exclusions": excluded,
        "sources": sources,
    }


def canonical_boundary_representation(artifact: Mapping[str, Any]) -> str:
    if artifact.get("schema") != BOUNDARY_SCHEMA:
        raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", "schema")
    if artifact.get("representation") != CANONICAL_REPRESENTATION:
        raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", "representation")
    if artifact.get("future_discriminator", {}).get("rejected_semantic_score") != REJECTED_REPRESENTATION:
        raise ClassificationContractError("FAMILY_BOUNDARY_UNAVAILABLE", "centroid")
    return CANONICAL_REPRESENTATION
