"""Exact frozen readiness gates for HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1.

Dataset-readiness only. Model acceptance gates live in STAGE_A_TRAIN_CONTRACT and
are evaluated only after an authorized Stage-A train — never here.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from .classification_v2_surface import SURFACE_ATOM, SURFACE_PROSE, surface_form, word_count

GATE_RULE = "HYPERLEX_V5_STAGE_A_SURFACE_READINESS_GATES_V1"
NEAR_DUPLICATE_METHOD = "hlx.v5.near_duplicate.normalized_jaccard_v1"
NEAR_DUPLICATE_JACCARD_MIN = 0.90

EVIDENCE_SUBTYPES = (
    "POSITIVE_EVIDENCE",
    "ORDINARY_DOMAIN_NONE",
    "HARD_NONE",
    "NEAR_DOMAIN_NONE",
    "GENERIC_NONE",
    "LEXICAL_LOOKALIKE_NONE",
    "SHORT_ATOM_NONE",
    "AMBIGUOUS_EVIDENCE",
)
NONE_SUBTYPES = (
    "ORDINARY_DOMAIN_NONE",
    "HARD_NONE",
    "NEAR_DOMAIN_NONE",
    "GENERIC_NONE",
    "LEXICAL_LOOKALIKE_NONE",
    "SHORT_ATOM_NONE",
)
SUBTYPE_TO_LABEL = {
    "POSITIVE_EVIDENCE": "EVIDENCE_PRESENT",
    "ORDINARY_DOMAIN_NONE": "NO_EVIDENCE",
    "HARD_NONE": "NO_EVIDENCE",
    "NEAR_DOMAIN_NONE": "NO_EVIDENCE",
    "GENERIC_NONE": "NO_EVIDENCE",
    "LEXICAL_LOOKALIKE_NONE": "NO_EVIDENCE",
    "SHORT_ATOM_NONE": "NO_EVIDENCE",
    "AMBIGUOUS_EVIDENCE": "UNCERTAIN",
}
REQUIRED_EVIDENCE_PRESENT = {
    "POSITIVE_EVIDENCE": "true",
    "ORDINARY_DOMAIN_NONE": "false",
    "HARD_NONE": "false",
    "NEAR_DOMAIN_NONE": "false",
    "GENERIC_NONE": "false",
    "LEXICAL_LOOKALIKE_NONE": "false",
    "SHORT_ATOM_NONE": "false",
    "AMBIGUOUS_EVIDENCE": "uncertain",
}
ACQUISITION_FLOORS = {
    "POSITIVE_EVIDENCE": 800,
    "ORDINARY_DOMAIN_NONE": 400,
    "HARD_NONE": 300,
    "NEAR_DOMAIN_NONE": 300,
    "GENERIC_NONE": 250,
    "LEXICAL_LOOKALIKE_NONE": 250,
    "SHORT_ATOM_NONE": 200,
    "AMBIGUOUS_EVIDENCE": 200,
}
VALIDATION_FLOORS = {
    "POSITIVE_EVIDENCE": 150,
    "ORDINARY_DOMAIN_NONE": 80,
    "HARD_NONE": 60,
    "NEAR_DOMAIN_NONE": 60,
    "GENERIC_NONE": 50,
    "LEXICAL_LOOKALIKE_NONE": 50,
    "SHORT_ATOM_NONE": 40,
    "AMBIGUOUS_EVIDENCE": 40,
}

DATASET_FLOORS = {
    "TOTAL_ROWS": 2500,
    "TRAIN_ROWS": 1900,
    "VALIDATION_ROWS": 600,
}

_TOKEN_RE = re.compile(r"[a-z0-9']+")


def tokens(text: str) -> set[str]:
    return {tok for tok in _TOKEN_RE.findall(str(text).casefold()) if len(tok) >= 3}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0

PAIRING_FLOORS = {
    "paired_positive_negative_pairs": 300,
    "paired_ORDINARY_DOMAIN_NONE": 120,
    "paired_HARD_NONE": 80,
    "paired_NEAR_DOMAIN_NONE": 80,
}

DUPLICATE_QUALITY = {
    "exact_duplicate_rate_max": 0.005,
    "near_duplicate_rate_max": 0.03,
    "cross_split_near_duplicate_clusters_max": 0,
}

SURFACE_BALANCE = {
    "median_token_count_ratio_min": 0.80,
    "median_token_count_ratio_max": 1.25,
    "atom_rate_abs_diff_max": 0.15,
    "prose_rate_abs_diff_max": 0.15,
    "punctuation_present_rate_diff_max": 0.15,
    "definition_style_rate_diff_max": 0.15,
    "max_single_source_share": 0.25,
}

LEXICAL_OVERLAP = {
    "top_100_token_jaccard_min": 0.30,
    "shared_high_frequency_tokens_min": 50,
}

EMBEDDING_HARDNESS = {
    "median_nearest_opposite_label_cosine_min": 0.55,
    "ordinary_domain_median_nearest_positive_cosine_min": 0.60,
    "none_frac_nearest_positive_cosine_ge_0_65_min": 0.25,
}

SHALLOW_SHORTCUT = {
    "length_only_balanced_accuracy_max": 0.60,
    "surface_feature_balanced_accuracy_max": 0.65,
    "surface_feature_macro_f1_max": 0.65,
    "bow_balanced_accuracy_max": 0.80,
    "ordinary_domain_none_false_positive_rate_max": 0.25,
}

TOPIC_BALANCE = {
    "positive_domain_min_for_none_requirement": 20,
    "matching_none_min_per_positive_domain": 10,
    "domains_with_positive_support_but_zero_negative_support_max": 0,
    "max_single_positive_domain_share": 0.30,
}

PROVENANCE = {
    "observed_validation_fraction_min": 0.50,
    "observed_validation_ordinary_domain_fraction_min": 0.50,
}

_PUNCT_RE = re.compile(r"[.,;:!?()\[\]\"']")
_DEFINITION_RE = re.compile(
    r"\b(is|are|means|refers to|defined as|denotes|describes)\b",
    re.I,
)


def frozen_readiness_gates() -> dict[str, Any]:
    return {
        "acquisition_floors": dict(ACQUISITION_FLOORS),
        "dataset_floors": dict(DATASET_FLOORS),
        "duplicate_quality": dict(DUPLICATE_QUALITY),
        "embedding_hardness": dict(EMBEDDING_HARDNESS),
        "gate_rule": GATE_RULE,
        "lexical_overlap": dict(LEXICAL_OVERLAP),
        "near_duplicate_jaccard_min": NEAR_DUPLICATE_JACCARD_MIN,
        "near_duplicate_method": NEAR_DUPLICATE_METHOD,
        "pairing_floors": dict(PAIRING_FLOORS),
        "provenance": dict(PROVENANCE),
        "shallow_shortcut": dict(SHALLOW_SHORTCUT),
        "surface_balance": dict(SURFACE_BALANCE),
        "topic_balance": dict(TOPIC_BALANCE),
        "validation_floors": dict(VALIDATION_FLOORS),
        "weighted_score_allowed": False,
    }


def _median(values: Sequence[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return float(ordered[mid - 1] + ordered[mid]) / 2.0


def _balanced_accuracy(y_true: Sequence[str], y_pred: Sequence[str], labels: Sequence[str]) -> float:
    scores = []
    for label in labels:
        idxs = [i for i, y in enumerate(y_true) if y == label]
        if not idxs:
            continue
        correct = sum(1 for i in idxs if y_pred[i] == label)
        scores.append(correct / len(idxs))
    return sum(scores) / len(scores) if scores else 0.0


def _macro_f1(y_true: Sequence[str], y_pred: Sequence[str], labels: Sequence[str]) -> float:
    f1s = []
    for label in labels:
        tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == label and yp == label)
        fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt != label and yp == label)
        fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == label and yp != label)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1s.append(0.0 if (prec + rec) == 0 else 2 * prec * rec / (prec + rec))
    return sum(f1s) / len(f1s) if f1s else 0.0


def normalized_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).casefold()).strip()


def near_duplicate_key(text: str) -> str:
    """Frozen near-duplicate signature: normalized text identity bucket."""
    return normalized_text(text)


def are_near_duplicates(text_a: str, text_b: str) -> bool:
    """Frozen similarity: exact normalized match OR token Jaccard >= 0.90."""
    na = normalized_text(text_a)
    nb = normalized_text(text_b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    return jaccard(tokens(na), tokens(nb)) >= NEAR_DUPLICATE_JACCARD_MIN


def punctuation_present(text: str) -> bool:
    return bool(_PUNCT_RE.search(text))


def definition_style(text: str) -> bool:
    return bool(_DEFINITION_RE.search(text))


def source_category(row: Mapping[str, Any]) -> str:
    bucket = row.get("source_bucket")
    if isinstance(bucket, str) and bucket.strip():
        return bucket.strip()
    notes = str(row.get("notes") or "")
    if notes.startswith("v5_ordinary_domain_bank:"):
        return "ordinary_domain_bank"
    if notes.startswith("v5_"):
        return notes.split(":")[0]
    if row.get("source_url"):
        return "wiktionary_or_url"
    if row.get("provenance") == "OBSERVED" or row.get("class") == "OBSERVED":
        return "hub_observed"
    return "hub_or_inferred"


def domain_key(row: Mapping[str, Any]) -> str:
    topic = row.get("topic_domain")
    if isinstance(topic, str) and topic.strip() and topic != "unspecified":
        return topic.strip()
    support = list(row.get("active_family_support") or [])
    if support:
        return str(support[0])
    return "unspecified"


def evaluate_acquisition_floors(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    subtype_counts = Counter(row["evidence_subtype"] for row in rows)
    split_counts = Counter(row["split"] for row in rows)
    train_subtype = Counter(
        row["evidence_subtype"] for row in rows if row["split"] == "train"
    )
    missing_subtype = {
        subtype: floor - subtype_counts.get(subtype, 0)
        for subtype, floor in ACQUISITION_FLOORS.items()
        if subtype_counts.get(subtype, 0) < floor
    }
    zero_train = [s for s in EVIDENCE_SUBTYPES if train_subtype.get(s, 0) == 0]
    dataset_gaps = {}
    if len(rows) < DATASET_FLOORS["TOTAL_ROWS"]:
        dataset_gaps["TOTAL_ROWS"] = DATASET_FLOORS["TOTAL_ROWS"] - len(rows)
    if split_counts.get("train", 0) < DATASET_FLOORS["TRAIN_ROWS"]:
        dataset_gaps["TRAIN_ROWS"] = DATASET_FLOORS["TRAIN_ROWS"] - split_counts.get("train", 0)
    if split_counts.get("validation", 0) < DATASET_FLOORS["VALIDATION_ROWS"]:
        dataset_gaps["VALIDATION_ROWS"] = (
            DATASET_FLOORS["VALIDATION_ROWS"] - split_counts.get("validation", 0)
        )
    return {
        "dataset_gaps": dataset_gaps,
        "missing_subtype_floors": missing_subtype,
        "pass": not missing_subtype and not dataset_gaps and not zero_train,
        "subtype_counts": dict(subtype_counts),
        "train_subtype_counts": dict(train_subtype),
        "zero_train_subtypes": zero_train,
    }


def evaluate_validation_floors(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    val_counts = Counter(
        row["evidence_subtype"] for row in rows if row["split"] == "validation"
    )
    missing = {
        subtype: floor - val_counts.get(subtype, 0)
        for subtype, floor in VALIDATION_FLOORS.items()
        if val_counts.get(subtype, 0) < floor
    }
    return {
        "missing_validation_floors": missing,
        "pass": not missing,
        "validation_subtype_counts": dict(val_counts),
    }


def evaluate_disjointness(
    rows: Sequence[Mapping[str, Any]],
    *,
    blocked: Mapping[str, str] | None = None,
    heldout_ids: set[str] | None = None,
    measurement_ids: set[str] | None = None,
) -> dict[str, Any]:
    blocked = dict(blocked or {})
    heldout_ids = set(heldout_ids or set())
    measurement_ids = set(measurement_ids or set())
    identities = [row["identity"] for row in rows]
    spent = {
        "spent_v2_reserve_overlap": 0,
        "spent_v3_reserve_overlap": 0,
        "spent_v4_reserve_overlap": 0,
    }
    for row in rows:
        reason = blocked.get(row["identity"])
        if reason == "spent_v2":
            spent["spent_v2_reserve_overlap"] += 1
        elif reason == "spent_v3":
            spent["spent_v3_reserve_overlap"] += 1
        elif reason == "spent_v4":
            spent["spent_v4_reserve_overlap"] += 1
    id_set = set(identities)
    heldout_overlap = len(id_set & heldout_ids)
    measurement_overlap = len(id_set & measurement_ids)

    train = [row for row in rows if row["split"] == "train"]
    val = [row for row in rows if row["split"] == "validation"]
    train_ids = {row["identity"] for row in train}
    val_ids = {row["identity"] for row in val}
    train_sources = {row["source_sha256"] for row in train}
    val_sources = {row["source_sha256"] for row in val}
    train_parents = {
        row["parent_identity"] for row in train if row.get("parent_identity")
    }
    val_parents = {row["parent_identity"] for row in val if row.get("parent_identity")}
    train_groups = {
        row.get("pair_group_id") or near_duplicate_key(row["text"])
        for row in train
    }
    # Exact normalized-text clusters crossing splits.
    clusters: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        clusters[near_duplicate_key(row["text"])].add(str(row["split"]))
    cross_ids: set[str] = set()
    for key, splits in clusters.items():
        if len(splits) > 1:
            cross_ids.add(f"exact:{key}")
    # Prefix buckets + frozen Jaccard (windowed for large buckets).
    by_prefix: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        by_prefix[normalized_text(row["text"])[:24]].append(row)
    for prefix, bucket_rows in by_prefix.items():
        ordered = sorted(bucket_rows, key=lambda item: item["identity"])
        limit = len(ordered) if len(ordered) <= 64 else None
        for i, left in enumerate(ordered):
            right_iter = (
                ordered[i + 1 :]
                if limit is not None
                else ordered[i + 1 : i + 9]
            )
            for right in right_iter:
                if left["split"] == right["split"]:
                    continue
                if are_near_duplicates(left["text"], right["text"]):
                    cross_ids.add(
                        "jacc:"
                        + ":".join(sorted([left["identity"], right["identity"]]))
                    )
    metrics = {
        **spent,
        "heldout_overlap": heldout_overlap,
        "measurement_only_overlap": measurement_overlap,
        "train_validation_identity_overlap": len(train_ids & val_ids),
        "train_validation_source_hash_overlap": len(train_sources & val_sources),
        "train_validation_parent_lineage_overlap": len(train_parents & val_parents),
        "train_validation_near_duplicate_group_overlap": len(cross_ids),
        "cross_split_near_duplicate_clusters": len(cross_ids),
    }
    return {
        "metrics": metrics,
        "near_duplicate_method": NEAR_DUPLICATE_METHOD,
        "pass": all(value == 0 for value in metrics.values()),
    }


def evaluate_duplicate_quality(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_split: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        by_split[str(row["split"])].append(row)
    per_split = {}
    fail = False
    for split, split_rows in by_split.items():
        n = len(split_rows)
        if n == 0:
            continue
        exact_groups: dict[str, list[str]] = defaultdict(list)
        for row in split_rows:
            exact_groups[normalized_text(row["text"])].append(row["identity"])
        exact_dup_rows = sum(len(v) - 1 for v in exact_groups.values() if len(v) > 1)
        # Near-dup: union-find via prefix buckets + frozen similarity.
        parent = {row["identity"]: row["identity"] for row in split_rows}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: str, b: str) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        # Exact normalized text unions first.
        by_norm: dict[str, list[str]] = defaultdict(list)
        for row in split_rows:
            by_norm[normalized_text(row["text"])].append(row["identity"])
        for ids in by_norm.values():
            head = ids[0]
            for other in ids[1:]:
                union(head, other)
        buckets: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for row in split_rows:
            buckets[normalized_text(row["text"])[:24]].append(row)
        for bucket_rows in buckets.values():
            ordered = sorted(bucket_rows, key=lambda item: item["identity"])
            for i, left in enumerate(ordered):
                right_iter = (
                    ordered[i + 1 :]
                    if len(ordered) <= 64
                    else ordered[i + 1 : i + 9]
                )
                for right in right_iter:
                    if are_near_duplicates(left["text"], right["text"]):
                        union(left["identity"], right["identity"])
        comps: dict[str, list[str]] = defaultdict(list)
        for row in split_rows:
            comps[find(row["identity"])].append(row["identity"])
        near_dup_rows = sum(len(v) - 1 for v in comps.values() if len(v) > 1)
        exact_rate = exact_dup_rows / n
        near_rate = near_dup_rows / n
        per_split[split] = {
            "exact_duplicate_rate": exact_rate,
            "near_duplicate_rate": near_rate,
            "n": n,
        }
        if exact_rate > DUPLICATE_QUALITY["exact_duplicate_rate_max"]:
            fail = True
        if near_rate > DUPLICATE_QUALITY["near_duplicate_rate_max"]:
            fail = True
    cross = evaluate_disjointness(rows)["metrics"]["cross_split_near_duplicate_clusters"]
    if cross > DUPLICATE_QUALITY["cross_split_near_duplicate_clusters_max"]:
        fail = True
    return {
        "cross_split_near_duplicate_clusters": cross,
        "near_duplicate_method": NEAR_DUPLICATE_METHOD,
        "pass": not fail,
        "per_split": per_split,
    }


def evaluate_pairing(
    rows: Sequence[Mapping[str, Any]],
    pair_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    by_id = {row["identity"]: row for row in rows}
    valid_pairs = []
    subtype_counts: Counter[str] = Counter()
    for pair in pair_records:
        pos = by_id.get(str(pair.get("paired_positive_identity")))
        neg = by_id.get(str(pair.get("negative_identity")))
        if pos is None or neg is None:
            continue
        shared = list(pair.get("shared_cues") or [])
        if not shared:
            continue
        if pos.get("required_evidence_present") == neg.get("required_evidence_present"):
            continue
        valid_pairs.append(pair)
        subtype_counts[str(neg.get("evidence_subtype"))] += 1
    gaps = {}
    if len(valid_pairs) < PAIRING_FLOORS["paired_positive_negative_pairs"]:
        gaps["paired_positive_negative_pairs"] = (
            PAIRING_FLOORS["paired_positive_negative_pairs"] - len(valid_pairs)
        )
    for key, subtype in (
        ("paired_ORDINARY_DOMAIN_NONE", "ORDINARY_DOMAIN_NONE"),
        ("paired_HARD_NONE", "HARD_NONE"),
        ("paired_NEAR_DOMAIN_NONE", "NEAR_DOMAIN_NONE"),
    ):
        have = subtype_counts.get(subtype, 0)
        if have < PAIRING_FLOORS[key]:
            gaps[key] = PAIRING_FLOORS[key] - have
    return {
        "gaps": gaps,
        "paired_positive_negative_pairs": len(valid_pairs),
        "paired_subtype_counts": dict(subtype_counts),
        "pass": not gaps,
    }


def evaluate_surface_balance(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_label: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        by_label[str(row["evidence_label"])].append(row)

    def stats(label_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        n = len(label_rows) or 1
        atom = sum(1 for r in label_rows if surface_form(r["text"]) == SURFACE_ATOM) / n
        prose = sum(1 for r in label_rows if surface_form(r["text"]) == SURFACE_PROSE) / n
        punct = sum(1 for r in label_rows if punctuation_present(r["text"])) / n
        definition = sum(1 for r in label_rows if definition_style(r["text"])) / n
        median_tokens = _median([word_count(r["text"]) for r in label_rows])
        sources = Counter(source_category(r) for r in label_rows)
        top_share = (sources.most_common(1)[0][1] / n) if sources else 0.0
        return {
            "ATOM_rate": atom,
            "PROSE_rate": prose,
            "definition_style_rate": definition,
            "median_token_count": median_tokens,
            "n": len(label_rows),
            "punctuation_present_rate": punct,
            "source_counts": dict(sources),
            "top_source_share": top_share,
        }

    present = stats(by_label.get("EVIDENCE_PRESENT") or [])
    none = stats(by_label.get("NO_EVIDENCE") or [])
    uncertain = stats(by_label.get("UNCERTAIN") or [])
    failures = []
    ratio = None
    if present["median_token_count"] and none["median_token_count"]:
        ratio = present["median_token_count"] / none["median_token_count"]
        if ratio < SURFACE_BALANCE["median_token_count_ratio_min"] or ratio > SURFACE_BALANCE[
            "median_token_count_ratio_max"
        ]:
            failures.append(f"median_token_count_ratio={ratio:.4f}")
    if abs(present["ATOM_rate"] - none["ATOM_rate"]) > SURFACE_BALANCE["atom_rate_abs_diff_max"]:
        failures.append("ATOM_rate_diff")
    if abs(present["PROSE_rate"] - none["PROSE_rate"]) > SURFACE_BALANCE["prose_rate_abs_diff_max"]:
        failures.append("PROSE_rate_diff")
    if (
        abs(present["punctuation_present_rate"] - none["punctuation_present_rate"])
        > SURFACE_BALANCE["punctuation_present_rate_diff_max"]
    ):
        failures.append("punctuation_present_rate_diff")
    if (
        abs(present["definition_style_rate"] - none["definition_style_rate"])
        > SURFACE_BALANCE["definition_style_rate_diff_max"]
    ):
        failures.append("definition_style_rate_diff")
    if present["top_source_share"] > SURFACE_BALANCE["max_single_source_share"]:
        failures.append("present_source_share")
    if none["top_source_share"] > SURFACE_BALANCE["max_single_source_share"]:
        failures.append("none_source_share")
    return {
        "EVIDENCE_PRESENT": present,
        "NO_EVIDENCE": none,
        "UNCERTAIN": uncertain,
        "failures": failures,
        "median_token_count_ratio": ratio,
        "pass": not failures,
    }


def evaluate_lexical_overlap(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    present = [row for row in rows if row["evidence_label"] == "EVIDENCE_PRESENT"]
    none = [row for row in rows if row["evidence_label"] == "NO_EVIDENCE"]
    pos_freq: Counter[str] = Counter()
    neg_freq: Counter[str] = Counter()
    for row in present:
        pos_freq.update(tokens(row["text"]))
    for row in none:
        neg_freq.update(tokens(row["text"]))
    top_pos = {tok for tok, _ in pos_freq.most_common(100)}
    top_neg = {tok for tok, _ in neg_freq.most_common(100)}
    top_jacc = jaccard(top_pos, top_neg)
    # high-frequency shared: tokens in both top-200
    high_pos = {tok for tok, _ in pos_freq.most_common(200)}
    high_neg = {tok for tok, _ in neg_freq.most_common(200)}
    shared_high = sorted(high_pos & high_neg)
    failures = []
    if top_jacc < LEXICAL_OVERLAP["top_100_token_jaccard_min"]:
        failures.append(f"top_100_token_jaccard={top_jacc:.4f}")
    if len(shared_high) < LEXICAL_OVERLAP["shared_high_frequency_tokens_min"]:
        failures.append(f"shared_high_frequency_tokens={len(shared_high)}")
    return {
        "failures": failures,
        "pass": not failures,
        "shared_high_frequency_tokens": len(shared_high),
        "shared_high_frequency_tokens_sample": shared_high[:50],
        "top_100_token_jaccard": top_jacc,
    }


def evaluate_embedding_hardness(
    embedding_report: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not embedding_report:
        return {
            "pass": False,
            "failures": ["embedding_hardness_report_missing"],
            "report": None,
        }
    failures = []
    median_opp = embedding_report.get("median_nearest_opposite_label_cosine")
    ordinary_med = embedding_report.get("ordinary_domain_median_nearest_positive_cosine")
    frac = embedding_report.get("none_frac_nearest_positive_cosine_ge_0_65")
    if median_opp is None or float(median_opp) < EMBEDDING_HARDNESS[
        "median_nearest_opposite_label_cosine_min"
    ]:
        failures.append(f"median_nearest_opposite_label_cosine={median_opp}")
    if ordinary_med is None or float(ordinary_med) < EMBEDDING_HARDNESS[
        "ordinary_domain_median_nearest_positive_cosine_min"
    ]:
        failures.append(f"ordinary_domain_median_nearest_positive_cosine={ordinary_med}")
    if frac is None or float(frac) < EMBEDDING_HARDNESS[
        "none_frac_nearest_positive_cosine_ge_0_65_min"
    ]:
        failures.append(f"none_frac_nearest_positive_cosine_ge_0_65={frac}")
    return {"failures": failures, "pass": not failures, "report": dict(embedding_report)}


def evaluate_shallow_shortcut(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    labels = ("EVIDENCE_PRESENT", "NO_EVIDENCE")
    train = [
        row
        for row in rows
        if row["split"] == "train" and row["evidence_label"] in labels
    ]
    val = [
        row
        for row in rows
        if row["split"] == "validation" and row["evidence_label"] in labels
    ]
    if not train or not val:
        return {"pass": False, "failures": ["insufficient_binary_rows"]}

    train_y = [str(row["evidence_label"]) for row in train]
    val_y = [str(row["evidence_label"]) for row in val]

    # Length-only threshold search on train by balanced accuracy.
    best_thr = 0
    best_ba = -1.0
    lengths = sorted({word_count(str(row["text"])) for row in train})
    for thr in lengths:
        pred = [
            "EVIDENCE_PRESENT" if word_count(str(row["text"])) >= thr else "NO_EVIDENCE"
            for row in train
        ]
        ba = _balanced_accuracy(train_y, pred, labels)
        if ba > best_ba:
            best_ba = ba
            best_thr = thr
    length_pred = [
        "EVIDENCE_PRESENT" if word_count(str(row["text"])) >= best_thr else "NO_EVIDENCE"
        for row in val
    ]
    length_ba = _balanced_accuracy(val_y, length_pred, labels)

    # Surface-feature: threshold on a linear score of engineered features.
    def feats(row: Mapping[str, Any]) -> tuple[float, ...]:
        text = str(row["text"])
        form = surface_form(text)
        return (
            float(word_count(text)),
            float(len(text)),
            1.0 if punctuation_present(text) else 0.0,
            1.0 if form == SURFACE_ATOM else 0.0,
            1.0 if form == SURFACE_PROSE else 0.0,
            1.0 if definition_style(text) else 0.0,
            float(abs(hash(source_category(row))) % 97) / 97.0,
        )

    # Fit mean feature vectors per class; classify by nearer centroid (deterministic).
    pos_vecs = [feats(row) for row, y in zip(train, train_y) if y == "EVIDENCE_PRESENT"]
    neg_vecs = [feats(row) for row, y in zip(train, train_y) if y == "NO_EVIDENCE"]

    def mean_vec(vecs: Sequence[tuple[float, ...]]) -> tuple[float, ...]:
        if not vecs:
            return tuple(0.0 for _ in range(7))
        dim = len(vecs[0])
        return tuple(sum(v[i] for v in vecs) / len(vecs) for i in range(dim))

    pos_mu = mean_vec(pos_vecs)
    neg_mu = mean_vec(neg_vecs)

    def nearest(row: Mapping[str, Any]) -> str:
        vec = feats(row)
        d_pos = sum((a - b) ** 2 for a, b in zip(vec, pos_mu))
        d_neg = sum((a - b) ** 2 for a, b in zip(vec, neg_mu))
        return "EVIDENCE_PRESENT" if d_pos <= d_neg else "NO_EVIDENCE"

    surface_pred = [nearest(row) for row in val]
    surface_ba = _balanced_accuracy(val_y, surface_pred, labels)
    surface_f1 = _macro_f1(val_y, surface_pred, labels)

    # BoW polarity
    pos_counts: Counter[str] = Counter()
    neg_counts: Counter[str] = Counter()
    for row, y in zip(train, train_y):
        bag = tokens(row["text"])
        if y == "EVIDENCE_PRESENT":
            pos_counts.update(bag)
        else:
            neg_counts.update(bag)
    weight = {
        tok: math.log1p(pos_counts[tok]) - math.log1p(neg_counts[tok])
        for tok in set(pos_counts) | set(neg_counts)
    }

    def bow_pred(text: str) -> str:
        score = sum(weight.get(tok, 0.0) for tok in tokens(text))
        return "EVIDENCE_PRESENT" if score >= 0 else "NO_EVIDENCE"

    bow_preds = [bow_pred(str(row["text"])) for row in val]
    bow_ba = _balanced_accuracy(val_y, bow_preds, labels)

    # ORDINARY_DOMAIN_NONE false-positive rate under BoW: predicted PRESENT / ordinary none val
    ordinary_val = [
        row
        for row in rows
        if row["split"] == "validation" and row["evidence_subtype"] == "ORDINARY_DOMAIN_NONE"
    ]
    if ordinary_val:
        ordinary_fp = sum(
            1 for row in ordinary_val if bow_pred(str(row["text"])) == "EVIDENCE_PRESENT"
        ) / len(ordinary_val)
    else:
        ordinary_fp = 1.0

    failures = []
    if length_ba > SHALLOW_SHORTCUT["length_only_balanced_accuracy_max"]:
        failures.append(f"length_only_balanced_accuracy={length_ba:.4f}")
    if (
        surface_ba > SHALLOW_SHORTCUT["surface_feature_balanced_accuracy_max"]
        or surface_f1 > SHALLOW_SHORTCUT["surface_feature_macro_f1_max"]
    ):
        failures.append(
            f"surface_feature_balanced_accuracy={surface_ba:.4f},macro_f1={surface_f1:.4f}"
        )
    bow_fail = bow_ba > SHALLOW_SHORTCUT["bow_balanced_accuracy_max"]
    ordinary_fail = (
        ordinary_fp > SHALLOW_SHORTCUT["ordinary_domain_none_false_positive_rate_max"]
    )
    if bow_fail and ordinary_fail:
        failures.append(
            f"bow_balanced_accuracy={bow_ba:.4f}+ordinary_fp={ordinary_fp:.4f}"
        )

    return {
        "bow_balanced_accuracy": bow_ba,
        "failures": failures,
        "length_only_balanced_accuracy": length_ba,
        "length_only_threshold_words": best_thr,
        "ordinary_domain_none_false_positive_rate": ordinary_fp,
        "pass": not failures,
        "surface_feature_balanced_accuracy": surface_ba,
        "surface_feature_macro_f1": surface_f1,
    }


def evaluate_topic_balance(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    pos_domains: Counter[str] = Counter()
    none_domains: Counter[str] = Counter()
    for row in rows:
        key = domain_key(row)
        if row["evidence_subtype"] == "POSITIVE_EVIDENCE":
            pos_domains[key] += 1
        elif row["evidence_subtype"] in NONE_SUBTYPES:
            none_domains[key] += 1
    pos_n = sum(pos_domains.values()) or 1
    missing_none = {}
    zero_neg = []
    for domain, count in sorted(pos_domains.items()):
        if domain == "unspecified":
            continue
        if count >= TOPIC_BALANCE["positive_domain_min_for_none_requirement"]:
            have = none_domains.get(domain, 0)
            if have < TOPIC_BALANCE["matching_none_min_per_positive_domain"]:
                missing_none[domain] = (
                    TOPIC_BALANCE["matching_none_min_per_positive_domain"] - have
                )
        if none_domains.get(domain, 0) == 0 and count > 0 and domain != "unspecified":
            zero_neg.append(domain)
    top_share = 0.0
    top_domain = None
    if pos_domains:
        top_domain, top_count = pos_domains.most_common(1)[0]
        top_share = top_count / pos_n
    failures = []
    if missing_none:
        failures.append({"matching_none_shortfall": missing_none})
    if len(zero_neg) > TOPIC_BALANCE[
        "domains_with_positive_support_but_zero_negative_support_max"
    ]:
        failures.append({"domains_with_positive_support_but_zero_negative_support": zero_neg})
    if top_share > TOPIC_BALANCE["max_single_positive_domain_share"]:
        failures.append(
            {
                "max_single_positive_domain_share": top_share,
                "domain": top_domain,
                "documented_allowlist": False,
            }
        )
    return {
        "failures": failures,
        "none_domain_counts": dict(sorted(none_domains.items())),
        "pass": not failures,
        "positive_domain_counts": dict(sorted(pos_domains.items())),
        "top_positive_domain_share": top_share,
    }


def evaluate_provenance(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    prov = Counter(row.get("provenance") or row.get("class") for row in rows)
    val = [row for row in rows if row["split"] == "validation"]
    val_obs = sum(1 for row in val if (row.get("provenance") or row.get("class")) == "OBSERVED")
    val_frac = (val_obs / len(val)) if val else 0.0
    ordinary_val = [
        row
        for row in val
        if row["evidence_subtype"] == "ORDINARY_DOMAIN_NONE"
    ]
    ordinary_obs = sum(
        1
        for row in ordinary_val
        if (row.get("provenance") or row.get("class")) == "OBSERVED"
    )
    ordinary_frac = (ordinary_obs / len(ordinary_val)) if ordinary_val else 0.0
    failures = []
    if prov.get("OBSERVED", 0) <= 0:
        failures.append("OBSERVED=0")
    if prov.get("INFERRED", 0) <= 0:
        failures.append("INFERRED=0")
    if val_frac < PROVENANCE["observed_validation_fraction_min"]:
        failures.append(f"observed_validation_fraction={val_frac:.4f}")
    if ordinary_frac < PROVENANCE["observed_validation_ordinary_domain_fraction_min"]:
        failures.append(f"observed_validation_ordinary_domain_fraction={ordinary_frac:.4f}")
    return {
        "failures": failures,
        "observed_validation_fraction": val_frac,
        "observed_validation_ordinary_domain_fraction": ordinary_frac,
        "pass": not failures,
        "provenance_counts": dict(prov),
    }


def evaluate_schema_integrity(
    rows: Sequence[Mapping[str, Any]],
    *,
    ontology: Sequence[str],
) -> dict[str, Any]:
    from .holdout_guard import normalized_text_sha256

    invalid_schema = 0
    invalid_span = 0
    unknown_family = 0
    missing_hashes = 0
    label_mismatch = 0
    nonfinite = 0
    allowed = set(ontology)
    identities = [row["identity"] for row in rows]
    for row in rows:
        text = str(row.get("text") or "")
        subtype = str(row.get("evidence_subtype"))
        bad = False
        if subtype not in SUBTYPE_TO_LABEL:
            bad = True
        if SUBTYPE_TO_LABEL.get(subtype) != row.get("evidence_label"):
            label_mismatch += 1
            bad = True
        if row.get("required_evidence_present") != REQUIRED_EVIDENCE_PRESENT.get(subtype):
            label_mismatch += 1
            bad = True
        if not text.strip():
            bad = True
        if row.get("identity") != normalized_text_sha256(text):
            bad = True
        if row.get("provenance") not in {"OBSERVED", "INFERRED"}:
            bad = True
        if row.get("split") not in {"train", "validation"}:
            bad = True
        if not row.get("source_sha256"):
            missing_hashes += 1
            bad = True
        for family in list(row.get("active_family_support") or []) + list(
            row.get("candidate_families") or []
        ):
            if family not in allowed:
                unknown_family += 1
                bad = True
        if subtype == "POSITIVE_EVIDENCE":
            spans = row.get("evidence_spans") or []
            if not spans or not row.get("active_family_support"):
                bad = True
            for span in spans:
                try:
                    start = int(span["start"])
                    end = int(span["end"])
                except Exception:
                    invalid_span += 1
                    bad = True
                    continue
                if start < 0 or end > len(text) or start >= end:
                    invalid_span += 1
                    bad = True
        if subtype in NONE_SUBTYPES and row.get("active_family_support"):
            bad = True
        if bad:
            invalid_schema += 1
    metrics = {
        "duplicate_identities": len(identities) - len(set(identities)),
        "invalid_schema_rows": invalid_schema,
        "invalid_span_rows": invalid_span,
        "label_subtype_mismatches": label_mismatch,
        "missing_source_hashes": missing_hashes,
        "nonfinite_values": nonfinite,
        "unknown_family_refs": unknown_family,
    }
    return {"metrics": metrics, "pass": all(v == 0 for v in metrics.values())}


def evaluate_surface_readiness(
    rows: Sequence[Mapping[str, Any]],
    *,
    pair_records: Sequence[Mapping[str, Any]],
    ontology: Sequence[str],
    blocked: Mapping[str, str] | None = None,
    heldout_ids: set[str] | None = None,
    measurement_ids: set[str] | None = None,
    embedding_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    acquisition = evaluate_acquisition_floors(rows)
    validation = evaluate_validation_floors(rows)
    disjointness = evaluate_disjointness(
        rows,
        blocked=blocked,
        heldout_ids=heldout_ids,
        measurement_ids=measurement_ids,
    )
    duplicates = evaluate_duplicate_quality(rows)
    pairing = evaluate_pairing(rows, pair_records)
    surface_balance = evaluate_surface_balance(rows)
    lexical = evaluate_lexical_overlap(rows)
    embedding = evaluate_embedding_hardness(embedding_report)
    shallow = evaluate_shallow_shortcut(rows)
    topic = evaluate_topic_balance(rows)
    provenance = evaluate_provenance(rows)
    schema = evaluate_schema_integrity(rows, ontology=ontology)

    gate_pass = {
        "acquisition_floors_pass": acquisition["pass"],
        "validation_floors_pass": validation["pass"],
        "all_disjointness_pass": disjointness["pass"],
        "duplicate_quality_pass": duplicates["pass"],
        "pairing_pass": pairing["pass"],
        "surface_balance_pass": surface_balance["pass"],
        "lexical_overlap_pass": lexical["pass"],
        "embedding_hardness_pass": embedding["pass"],
        "shallow_shortcut_pass": shallow["pass"],
        "topic_balance_pass": topic["pass"],
        "provenance_pass": provenance["pass"],
        "schema_integrity_pass": schema["pass"],
    }
    ready = all(gate_pass.values())
    missing = {name: False for name, ok in gate_pass.items() if not ok}
    details = {
        "acquisition": acquisition,
        "disjointness": disjointness,
        "duplicate_quality": duplicates,
        "embedding_hardness": embedding,
        "lexical_overlap": lexical,
        "pairing": pairing,
        "provenance": provenance,
        "schema_integrity": schema,
        "shallow_shortcut": shallow,
        "surface_balance": surface_balance,
        "topic_balance": topic,
        "validation": validation,
    }
    return {
        "gate_pass": gate_pass,
        "gate_rule": GATE_RULE,
        "gates": frozen_readiness_gates(),
        "missing_evidence": missing,
        "details": details,
        "state": "READY" if ready else "PREREGISTERED",
        # Model gates are recorded but not used for dataset readiness.
        "model_acceptance_gates_separate": {
            "EVIDENCE_PRESENT_recall_min": 0.70,
            "NO_EVIDENCE_recall_min": 0.90,
            "false_evidence_entry_rate_on_none_max": 0.05,
            "note": "model gates; not dataset-readiness gates",
        },
    }
