"""BUILD_V5_STAGE_A_GENERALIZATION_SURFACE_V1 — matched boundary Stage-A surface.

Fresh train/validation surface targeting surface-conditioned Stage-A gaps.
Parallel gate set (does not mutate V1R9 readiness). Does not train, retune
thresholds, modify Stage B, reuse spent reserve rows, or move BEST pointers.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

os.environ.setdefault("HLX_V2_FORWARD_ONTOLOGY", "1")

from .classification_v2 import ACTIVE_FAMILY_VOCABULARY, LEGACY_HEADS
from .classification_v2_surface import (
    SURFACE_ATOM,
    SURFACE_PROSE,
    surface_form,
    word_count,
)
from .classification_v5_stage_a_gold_label_mapping import SUBTYPE_TO_GOLD
from .classification_v5_surface_readiness_gates import (
    REQUIRED_EVIDENCE_PRESENT,
    SUBTYPE_TO_LABEL,
    are_near_duplicates,
    definition_style,
    domain_key,
    evaluate_disjointness,
    evaluate_duplicate_quality,
    evaluate_schema_integrity,
    jaccard,
    near_duplicate_key,
    normalized_text,
    punctuation_present,
    source_category,
    tokens,
)
from .holdout_guard import normalized_text_sha256

SURFACE_RULE = "HYPERLEX_V5_STAGE_A_GENERALIZATION_SURFACE_V1"
DESIGN_RULE = "BUILD_V5_STAGE_A_GENERALIZATION_SURFACE_V1"
GATE_RULE = "HYPERLEX_V5_STAGE_A_GENERALIZATION_SURFACE_READINESS_GATES_V1"
PARENT_DIAGNOSIS = "STAGE_A_GENERALIZATION_FAILURE"
STAGE_A_BEST_SHA = (
    "cd2829c1b5fb823fc03f18efe66a7387124ef44be2545b9e385a17eb6237bf5c"
)
MODEL_WIDE_BEST_SHA = (
    "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
)
SPENT_RESERVE = "HYPERLEX_V5_PROMOTION_RESERVE_001"
V1R9_SURFACE_SHA = (
    "8d4be8301b89b191841342fe11ef647c838b32e56e6d133b610c232264c5d00a"
)
SPLIT_SEED_PREFIX = "hlx.v5.stage_a.generalization.surface.split.v1"
SCHEMA_SHA = {
    "evidence_example.v1": "7af99e521fe27bcbc5af54bf9187e91fd4d7756b8a7756405ecb3c120ba0f026",
}

EVIDENCE_LABELS = ("NO_EVIDENCE", "EVIDENCE_PRESENT", "UNCERTAIN")
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

PRIMARY_CELLS = (
    "SHORT_ATOM/NO_EVIDENCE",
    "SHORT_ATOM/EVIDENCE_PRESENT",
    "PROSE/NO_EVIDENCE",
    "PROSE/EVIDENCE_PRESENT",
    "DEFINITION_STYLE/NO_EVIDENCE",
    "DEFINITION_STYLE/EVIDENCE_PRESENT",
    "ORDINARY_PROSE/NO_EVIDENCE",
    "ORDINARY_PROSE/EVIDENCE_PRESENT",
)
CRITICAL_CELLS = (
    "SHORT_ATOM/NO_EVIDENCE",
    "SHORT_ATOM/EVIDENCE_PRESENT",
    "DEFINITION_STYLE/NO_EVIDENCE",
    "DEFINITION_STYLE/EVIDENCE_PRESENT",
)

CELL_TRAIN_FLOOR = 150
CELL_VAL_FLOOR = 50
CRITICAL_VAL_FLOOR = 80

PAIRING_FLOORS = {
    "matched_positive_negative_pairs": 500,
    "matched_SHORT_ATOM": 150,
    "matched_DEFINITION_STYLE": 150,
    "matched_ORDINARY_PROSE": 100,
}

SURFACE_BALANCE = {
    "median_token_count_ratio_min": 0.85,
    "median_token_count_ratio_max": 1.18,
    "atom_rate_abs_diff_max": 0.10,
    "prose_rate_abs_diff_max": 0.10,
    "definition_style_rate_diff_max": 0.10,
    "punctuation_present_rate_diff_max": 0.10,
    "max_single_source_family_share": 0.25,
}

LEXICAL_OVERLAP = {
    "top_100_token_jaccard_min": 0.35,
    "shared_high_frequency_tokens_min": 60,
}

EMBEDDING_HARDNESS = {
    "median_nearest_opposite_label_cosine_min": 0.65,
    "frac_nearest_opposite_cosine_ge_0_75_min": 0.40,
}

SHALLOW_SHORTCUT = {
    "length_only_balanced_accuracy_max": 0.57,
    "surface_only_balanced_accuracy_max": 0.60,
    "surface_only_macro_f1_max": 0.60,
    "tfidf_balanced_accuracy_max": 0.75,
}

PROVENANCE = {
    "observed_validation_fraction_min": 0.50,
    "critical_cell_observed_fraction_min": 0.40,
}

SOURCE_DIVERSITY = {
    "max_source_family_share": 0.25,
    "min_source_families_definition_style": 3,
    "min_source_families_short_atom": 3,
}

TOPIC_BALANCE = {
    "support_min_for_opposite_requirement": 20,
    "matching_opposite_min": 20,
}

ORDINARY_DOMAIN_LABELS = (
    "botany",
    "chemistry",
    "ornithology",
    "meteorology",
    "geology",
    "mathematics",
    "anatomy",
    "zoology",
    "physics",
    "astronomy",
)
ORDINARY_CUE_RE = re.compile(
    r"\b(plant|flower|chemical|compound|bird|weather|rock|mineral|equation|"
    r"theorem|bone|organ|animal|species|molecule|atom|temperature|soil|"
    r"xylem|chloroplast|catalyst|titration|migratory|raptor|cirrus|"
    r"sediment|fault|integer|prime|femur|cortex|mammal|habitat|"
    r"velocity|photon|orbit|galaxy|planet|"
    r"botany|chemistry|ornithology|meteorology|geology|mathematics|"
    r"anatomy|zoology|physics|astronomy|laboratory|textbook|fieldwork|"
    r"specimen|photosynthesis|electron|neuron|isotope|tectonic)\b",
    re.I,
)
DOMAIN_SLANG_CUE_RE = re.compile(
    r"\b(slang|meme|online|internet|viral|gaming|crypto|betting|discord|"
    r"tiktok|reddit|status|flex|aura|degen|rizz|simp|cap|mid|sus)\b",
    re.I,
)
_TOKEN_RE = re.compile(r"[a-z0-9']+")
_WIKT_FAMILY_RE = re.compile(r"wiktionary|wikt|v5_src_wik", re.I)


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def source_sha256(text: str) -> str:
    return sha256_text(str(text))


def frozen_generalization_gates() -> dict[str, Any]:
    return {
        "cell_train_floor": CELL_TRAIN_FLOOR,
        "cell_val_floor": CELL_VAL_FLOOR,
        "critical_cells": list(CRITICAL_CELLS),
        "critical_val_floor": CRITICAL_VAL_FLOOR,
        "embedding_hardness": dict(EMBEDDING_HARDNESS),
        "gate_rule": GATE_RULE,
        "lexical_overlap": dict(LEXICAL_OVERLAP),
        "pairing_floors": dict(PAIRING_FLOORS),
        "primary_cells": list(PRIMARY_CELLS),
        "provenance": dict(PROVENANCE),
        "shallow_shortcut": dict(SHALLOW_SHORTCUT),
        "source_diversity": dict(SOURCE_DIVERSITY),
        "surface_balance": dict(SURFACE_BALANCE),
        "topic_balance": dict(TOPIC_BALANCE),
        "weighted_score_allowed": False,
    }


def preregistration_contract() -> dict[str, Any]:
    return {
        "best_pointers": {
            "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA,
            "STAGE_A_BEST": STAGE_A_BEST_SHA,
            "status": "UNCHANGED",
        },
        "design_rule": DESIGN_RULE,
        "gate_rule": GATE_RULE,
        "parent_diagnosis": PARENT_DIAGNOSIS,
        "reserve_status": "SPENT / IMMUTABLE",
        "schema_sha256": dict(SCHEMA_SHA),
        "spent_reserve": SPENT_RESERVE,
        "stage_a_labels": list(EVIDENCE_LABELS),
        "stage_b": "UNCHANGED",
        "state": "PREREGISTERED",
        "surface_readiness_gates": frozen_generalization_gates(),
        "surface_rule": SURFACE_RULE,
        "thresholds": "UNCHANGED",
        "train": False,
        "v1r9_surface_sha256": V1R9_SURFACE_SHA,
        "version_bump_required_for_reinterpretation": True,
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


def source_family(row: Mapping[str, Any]) -> str:
    """Aggregate source family; related Wiktionary shards collapse to one family."""
    bucket = str(row.get("source_bucket") or row.get("notes") or "")
    url = str(row.get("source_url") or "")
    if _WIKT_FAMILY_RE.search(bucket) or "wiktionary.org" in url:
        return "wiktionary_aggregate"
    if "wikipedia.org" in url or "v5_src_wp_" in bucket:
        # keep domain shard diversity but family = wikipedia + domain group
        domain = str(row.get("topic_domain") or "general")
        shard = int(str(row.get("identity") or "0")[:2], 16) % 4
        return f"wikipedia_{domain}_{shard}"
    if bucket.startswith("v5_src_hub_obs_"):
        fam = (row.get("active_family_support") or ["none"])[0]
        return f"hub_observed_{fam}"
    if bucket.startswith("v5_src_inf_") or "v5_" in bucket:
        subtype = str(row.get("evidence_subtype") or "unknown")
        shard = int(str(row.get("identity") or "0")[:2], 16) % 4
        return f"inferred_{subtype}_{shard}"
    if row.get("provenance") == "OBSERVED":
        fam = (row.get("active_family_support") or ["none"])[0]
        return f"hub_observed_{fam}"
    subtype = str(row.get("evidence_subtype") or "unknown")
    shard = int(str(row.get("identity") or "0")[:2], 16) % 4
    return f"inferred_{subtype}_{shard}"


def stamp_source_buckets(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        item = dict(row)
        shard = int(str(item.get("identity") or "0")[:8], 16)
        url = str(item.get("source_url") or "")
        if "wiktionary.org" in url:
            domain = str(item.get("topic_domain") or "wiki")
            item["source_bucket"] = f"v5_src_wik_{domain}_{shard % 4}"
        elif "wikipedia.org" in url:
            domain = str(item.get("topic_domain") or "wiki")
            item["source_bucket"] = f"v5_src_wp_{domain}_{shard % 4}"
        elif item.get("provenance") == "OBSERVED":
            fam = (item.get("active_family_support") or ["none"])[0]
            item["source_bucket"] = f"v5_src_hub_obs_{fam}_{shard % 3}"
        else:
            subtype = str(item.get("evidence_subtype") or "unknown")
            item["source_bucket"] = f"v5_src_inf_{subtype}_{shard % 4}"
        note = str(item.get("notes") or "")
        if not note.startswith("v5_src_"):
            item["notes"] = f"{item['source_bucket']}:{note}" if note else item["source_bucket"]
        item["source_family"] = source_family(item)
        out.append(item)
    return out


def assign_primary_cell(
    *,
    text: str,
    evidence_label: str,
) -> str | None:
    if evidence_label not in {"NO_EVIDENCE", "EVIDENCE_PRESENT"}:
        return None
    form = surface_form(text)
    defn = definition_style(text)
    if form == SURFACE_ATOM:
        return f"SHORT_ATOM/{evidence_label}"
    if defn:
        return f"DEFINITION_STYLE/{evidence_label}"
    if form == SURFACE_PROSE:
        ordinary = bool(ORDINARY_CUE_RE.search(text))
        slang = bool(DOMAIN_SLANG_CUE_RE.search(text))
        if ordinary and not slang:
            return f"ORDINARY_PROSE/{evidence_label}"
        return f"PROSE/{evidence_label}"
    return None


def classify_hub_subtype(
    row: Mapping[str, Any],
    *,
    positive_token_union: set[str],
) -> str | None:
    forced = row.get("evidence_subtype")
    if forced in EVIDENCE_SUBTYPES:
        return str(forced)
    lineage = row.get("lineage")
    text = str(row.get("text") or "")
    form = surface_form(text)
    wc = word_count(text)
    klass = row.get("class")
    if form == "AMBIGUOUS" and lineage in ACTIVE_FAMILY_VOCABULARY and klass == "INFERRED" and wc <= 2:
        return "AMBIGUOUS_EVIDENCE"
    if lineage in ACTIVE_FAMILY_VOCABULARY:
        return "POSITIVE_EVIDENCE"
    tok = tokens(text)
    overlap = jaccard(tok, positive_token_union) if positive_token_union else 0.0
    if lineage in LEGACY_HEADS:
        if overlap >= 0.12:
            return "LEXICAL_LOOKALIKE_NONE"
        return "HARD_NONE"
    if lineage == "none":
        if form == SURFACE_ATOM and wc <= 2:
            return "SHORT_ATOM_NONE"
        if ORDINARY_CUE_RE.search(text) and not DOMAIN_SLANG_CUE_RE.search(text):
            return "ORDINARY_DOMAIN_NONE"
        if overlap >= 0.18 and wc >= 3:
            return "LEXICAL_LOOKALIKE_NONE"
        if DOMAIN_SLANG_CUE_RE.search(text) or (form == SURFACE_PROSE and wc >= 4):
            return "NEAR_DOMAIN_NONE"
        if form == SURFACE_ATOM:
            return "GENERIC_NONE"
        return "GENERIC_NONE"
    return None


def _span(text: str) -> list[dict[str, Any]]:
    if not text:
        return []
    return [{"start": 0, "end": len(text), "cue": None}]


def build_example(row: Mapping[str, Any], subtype: str) -> dict[str, Any]:
    text = str(row["text"]).strip()
    identity = normalized_text_sha256(text)
    label = SUBTYPE_TO_LABEL[subtype]
    lineage = row.get("lineage")
    support: list[str] = []
    spans: list[dict[str, Any]] = []
    missing: list[str] = []
    if subtype == "POSITIVE_EVIDENCE":
        fam = lineage if lineage in ACTIVE_FAMILY_VOCABULARY else None
        if fam is None:
            cands = list(row.get("candidate_families") or row.get("active_family_support") or [])
            fam = cands[0] if cands and cands[0] in ACTIVE_FAMILY_VOCABULARY else None
        if fam is None:
            raise ValueError(f"positive_without_active_family:{lineage}")
        support = [str(fam)]
        spans = _span(text)
    elif subtype == "AMBIGUOUS_EVIDENCE" and lineage in ACTIVE_FAMILY_VOCABULARY:
        support = [str(lineage)]
        missing = ["evidence_sufficiency_unresolved"]
    elif subtype in NONE_SUBTYPES:
        missing = ["active_family_evidence_absent", f"subtype:{subtype}"]
    cell = assign_primary_cell(text=text, evidence_label=label)
    example = {
        "active_family_support": support,
        "candidate_families": list(support),
        "evidence_label": label,
        "evidence_spans": list(spans),
        "evidence_subtype": subtype,
        "identity": identity,
        "missing_required_semantics": missing,
        "negative_evidence_spans": [],
        "notes": row.get("notes"),
        "pair_group_id": None,
        "paired_positive_identity": None,
        "parent_identity": row.get("parent_identity"),
        "positive_evidence_spans": list(spans),
        "primary_cell": cell,
        "provenance": str(row.get("class") or row.get("provenance")),
        "required_evidence_present": REQUIRED_EVIDENCE_PRESENT[subtype],
        "rights": row.get("rights"),
        "revision_id": row.get("revision_id"),
        "shared_cues": [],
        "source_sha256": source_sha256(text),
        "source_url": row.get("source_url"),
        "split": "train",
        "text": text,
        "topic_domain": row.get("topic_domain"),
    }
    return example


def _is_admissible_source_row(row: Mapping[str, Any]) -> bool:
    if row.get("split") not in {None, "train"}:
        return False
    if row.get("task") not in {"classify", "classify+unbind", None}:
        if row.get("task") is not None:
            return False
    if row.get("evaluation_reserve") or row.get("held_out"):
        return False
    if row.get("surface") in {"held_out", "evaluation_reserve", "settlement", "measurement"}:
        return False
    if row.get("jev") not in {None, False, "OFF", "off"}:
        return False
    if row.get("class") not in {"OBSERVED", "INFERRED"} and row.get("provenance") not in {
        "OBSERVED",
        "INFERRED",
    }:
        return False
    return bool(str(row.get("text") or "").strip())


def collect_examples(
    rows: Sequence[Mapping[str, Any]],
    *,
    blocked_ids: set[str],
    blocked_source_hashes: set[str] | None = None,
) -> list[dict[str, Any]]:
    blocked_source_hashes = set(blocked_source_hashes or set())
    positives = []
    for row in rows:
        if not _is_admissible_source_row(row):
            continue
        lineage = row.get("lineage")
        if lineage in ACTIVE_FAMILY_VOCABULARY:
            positives.append(str(row.get("text") or ""))
        elif row.get("evidence_subtype") == "POSITIVE_EVIDENCE":
            positives.append(str(row.get("text") or ""))
    positive_token_union: set[str] = set()
    for text in positives:
        positive_token_union |= tokens(text)

    chosen: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not _is_admissible_source_row(row):
            continue
        # Already-built surface rows may carry subtype + provenance.
        working = dict(row)
        if working.get("provenance") and not working.get("class"):
            working["class"] = working["provenance"]
        subtype = classify_hub_subtype(working, positive_token_union=positive_token_union)
        if subtype is None:
            continue
        try:
            example = build_example(working, subtype)
        except ValueError:
            continue
        if example["identity"] in blocked_ids:
            continue
        if example["source_sha256"] in blocked_source_hashes:
            continue
        if example.get("parent_identity") in blocked_ids:
            continue
        if example["evidence_label"] in {"NO_EVIDENCE", "EVIDENCE_PRESENT"} and not example.get(
            "primary_cell"
        ):
            continue
        prev = chosen.get(example["identity"])
        rank = (
            0 if example.get("provenance") == "OBSERVED" else 1,
            0 if example.get("primary_cell") in CRITICAL_CELLS else 1,
            example["identity"],
        )
        if prev is None:
            chosen[example["identity"]] = example
        else:
            prev_rank = (
                0 if prev.get("provenance") == "OBSERVED" else 1,
                0 if prev.get("primary_cell") in CRITICAL_CELLS else 1,
                prev["identity"],
            )
            if rank < prev_rank:
                chosen[example["identity"]] = example
    return sorted(chosen.values(), key=lambda item: item["identity"])


def build_matched_contrast_pairs(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Semantic matched pairs: same surface/domain/similar length; different evidence.

    Pair membership is cue/surface/domain based — never model scores.
    """
    by_id = {row["identity"]: dict(row) for row in rows}
    positives = [
        by_id[i]
        for i in by_id
        if by_id[i]["evidence_label"] == "EVIDENCE_PRESENT" and by_id[i].get("primary_cell")
    ]
    negatives = [
        by_id[i]
        for i in by_id
        if by_id[i]["evidence_label"] == "NO_EVIDENCE" and by_id[i].get("primary_cell")
    ]
    unused_neg = {row["identity"] for row in negatives}
    pair_records: list[dict[str, Any]] = []

    def surface_class(cell: str | None) -> str:
        if not cell:
            return "OTHER"
        return cell.split("/", 1)[0]

    for pos in sorted(positives, key=lambda item: item["identity"]):
        pos_tok = tokens(pos["text"])
        pos_wc = word_count(pos["text"])
        pos_surf = surface_class(pos.get("primary_cell"))
        pos_domain = domain_key(pos)
        best = None
        best_score = -1.0
        for neg_id in list(unused_neg):
            neg = by_id[neg_id]
            if surface_class(neg.get("primary_cell")) != pos_surf:
                continue
            neg_domain = domain_key(neg)
            # Prefer same domain; allow unspecified↔family soft match via cues.
            domain_bonus = 0.15 if (pos_domain == neg_domain and pos_domain != "unspecified") else 0.0
            if pos_domain != "unspecified" and neg_domain not in {pos_domain, "unspecified"}:
                if domain_bonus == 0.0 and jaccard(pos_tok, tokens(neg["text"])) < 0.20:
                    continue
            neg_tok = tokens(neg["text"])
            overlap = jaccard(pos_tok, neg_tok)
            wc_delta = abs(word_count(neg["text"]) - pos_wc)
            if wc_delta > 12:
                continue
            # Allow cue-light short-atom pairs when lengths match closely.
            # Definition-style matched NONE often share only a few content tokens.
            if pos_surf == "SHORT_ATOM":
                min_overlap = 0.0
            elif pos_surf == "DEFINITION_STYLE":
                min_overlap = 0.04
            else:
                min_overlap = 0.08
            if overlap < min_overlap and not (
                pos_surf == "SHORT_ATOM" and wc_delta <= 2 and pos_wc <= 4
            ):
                continue
            score = overlap + domain_bonus - 0.01 * wc_delta
            if pos_surf == "SHORT_ATOM" and wc_delta <= 1:
                score += 0.05
            if score > best_score:
                best_score = score
                best = neg
        if best is None:
            continue
        shared = sorted(pos_tok & tokens(best["text"]))[:16]
        if not shared:
            # Synthesize length/surface shared cue witness for short atoms.
            if pos_surf == "SHORT_ATOM":
                shared = [f"surface:{pos_surf}", f"len:{pos_wc}"]
            else:
                continue
        group = sha256_text(f"gpair:{pos['identity']}:{best['identity']}")[:16]
        pos_core = sorted(pos.get("active_family_support") or pos_tok)[:8]
        neg_missing = sorted(
            set(best.get("missing_required_semantics") or [])
            | {"paired_against_positive_lacks_family_evidence"}
        )
        pos["pair_group_id"] = group
        pos["shared_cues"] = shared
        best["pair_group_id"] = group
        best["paired_positive_identity"] = pos["identity"]
        best["shared_cues"] = shared
        best["missing_required_semantics"] = neg_missing
        unused_neg.discard(best["identity"])
        pair_records.append(
            {
                "negative_identity": best["identity"],
                "negative_missing_core": neg_missing,
                "pair_group_id": group,
                "positive_identity": pos["identity"],
                "positive_required_core": pos_core,
                "shared_cues": shared,
                "shared_domain": pos_domain
                if pos_domain == domain_key(best)
                else f"{pos_domain}|{domain_key(best)}",
                "shared_surface": pos_surf,
            }
        )
        by_id[pos["identity"]] = pos
        by_id[best["identity"]] = best

    out_rows = sorted(by_id.values(), key=lambda item: item["identity"])
    return out_rows, pair_records


def _split_bucket(identity: str) -> str:
    digest = hashlib.sha256(f"{SPLIT_SEED_PREFIX}:{identity}".encode("utf-8")).hexdigest()
    return "validation" if int(digest[:8], 16) % 5 == 0 else "train"


def assign_splits_by_component(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Split by connected lineage/near-dup/pair component; keep pairs co-located."""
    items = [dict(row) for row in rows]
    parent = {row["identity"]: row["identity"] for row in items}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    by_pair: dict[str, list[str]] = defaultdict(list)
    by_parent: dict[str, list[str]] = defaultdict(list)
    by_norm: dict[str, list[str]] = defaultdict(list)
    for row in items:
        if row.get("pair_group_id"):
            by_pair[str(row["pair_group_id"])].append(row["identity"])
        if row.get("parent_identity"):
            by_parent[str(row["parent_identity"])].append(row["identity"])
        by_norm[near_duplicate_key(row["text"])].append(row["identity"])
    for ids in list(by_pair.values()) + list(by_parent.values()) + list(by_norm.values()):
        head = ids[0]
        for other in ids[1:]:
            union(head, other)

    # Jaccard near-dups within prefix buckets.
    by_prefix: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in items:
        by_prefix[normalized_text(row["text"])[:24]].append(row)
    for bucket_rows in by_prefix.values():
        ordered = sorted(bucket_rows, key=lambda item: item["identity"])
        limit = len(ordered) if len(ordered) <= 48 else None
        for i, left in enumerate(ordered):
            right_iter = (
                ordered[i + 1 :] if limit is not None else ordered[i + 1 : i + 9]
            )
            for right in right_iter:
                if are_near_duplicates(left["text"], right["text"]):
                    union(left["identity"], right["identity"])

    components: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in items:
        components[find(row["identity"])].append(row)

    group_split: dict[str, str] = {}
    for key, members in components.items():
        anchor = sorted(m["identity"] for m in members)[0]
        group_split[key] = _split_bucket(anchor)

    def recount() -> dict[str, dict[str, int]]:
        counts = {cell: {"train": 0, "validation": 0} for cell in PRIMARY_CELLS}
        for key, members in components.items():
            split = group_split[key]
            for row in members:
                cell = row.get("primary_cell")
                if cell in counts:
                    counts[cell][split] += 1
        return counts

    # Promote train→validation groups until cell floors met (critical first).
    # Prefer OBSERVED-rich groups so critical-cell OBSERVED floors are reachable.
    order = list(CRITICAL_CELLS) + [c for c in PRIMARY_CELLS if c not in CRITICAL_CELLS]
    for cell in order:
        floor = CRITICAL_VAL_FLOOR if cell in CRITICAL_CELLS else CELL_VAL_FLOOR
        train_groups = []
        for key, members in components.items():
            if group_split[key] != "train":
                continue
            if any(m.get("primary_cell") == cell for m in members):
                obs = sum(1 for m in members if m.get("provenance") == "OBSERVED")
                cell_n = sum(1 for m in members if m.get("primary_cell") == cell)
                anchor = sorted(m["identity"] for m in members)[0]
                train_groups.append((-obs, -cell_n, anchor, key))
        train_groups.sort()
        for _obs, _cell_n, _anchor, key in train_groups:
            counts = recount()
            if counts[cell]["validation"] >= floor:
                break
            # Avoid overshoot that starves train floors for small cells.
            group_n = sum(1 for m in components[key] if m.get("primary_cell") == cell)
            if counts[cell]["validation"] + group_n > floor + 15 and counts[cell]["train"] - group_n < CELL_TRAIN_FLOOR:
                continue
            group_split[key] = "validation"

    # Second pass: boost overall validation OBSERVED toward 50% without
    # breaking cell floors (move OBSERVED train singletons → validation).
    def val_obs_frac() -> float:
        val_rows = [
            m
            for members in components.values()
            for m in members
            if group_split[find(m["identity"])] == "validation"
        ]
        if not val_rows:
            return 0.0
        return sum(1 for m in val_rows if m.get("provenance") == "OBSERVED") / len(val_rows)

    obs_train = []
    for key, members in components.items():
        if group_split[key] != "train":
            continue
        obs = sum(1 for m in members if m.get("provenance") == "OBSERVED")
        if obs == 0:
            continue
        anchor = sorted(m["identity"] for m in members)[0]
        obs_train.append((-obs, len(members), anchor, key))
    obs_train.sort()
    for _obs, _n, _anchor, key in obs_train:
        if val_obs_frac() >= PROVENANCE["observed_validation_fraction_min"]:
            break
        group_split[key] = "validation"

    # Critical-cell OBSERVED fraction boost (especially SHORT_ATOM NONE).
    def cell_obs_frac(cell: str) -> tuple[float, int, int]:
        cell_val = [
            m
            for key, members in components.items()
            if group_split[key] == "validation"
            for m in members
            if m.get("primary_cell") == cell
        ]
        if not cell_val:
            return 0.0, 0, 0
        obs = sum(1 for m in cell_val if m.get("provenance") == "OBSERVED")
        return obs / len(cell_val), obs, len(cell_val)

    for cell in CRITICAL_CELLS:
        candidates = []
        for key, members in components.items():
            if group_split[key] != "train":
                continue
            if not any(m.get("primary_cell") == cell and m.get("provenance") == "OBSERVED" for m in members):
                continue
            # Prefer small OBSERVED-pure groups so we do not drag huge train mass.
            obs = sum(1 for m in members if m.get("provenance") == "OBSERVED")
            anchor = sorted(m["identity"] for m in members)[0]
            candidates.append((len(members), -obs, anchor, key))
        candidates.sort()
        for _n, _obs, _anchor, key in candidates:
            frac, _o, _nval = cell_obs_frac(cell)
            if frac >= PROVENANCE["critical_cell_observed_fraction_min"]:
                break
            group_split[key] = "validation"

    assigned = []
    witness = []
    for key, members in components.items():
        split = group_split[key]
        for row in members:
            row["split"] = split
            row["near_duplicate_component"] = key
            assigned.append(row)
        witness.append(
            {
                "component": key,
                "identities": [m["identity"] for m in members[:12]],
                "n": len(members),
                "observed_n": sum(1 for m in members if m.get("provenance") == "OBSERVED"),
                "split": split,
            }
        )
    assigned.sort(key=lambda item: (item.get("primary_cell") or "", item["identity"]))
    return {
        "component_witness": sorted(witness, key=lambda item: item["component"]),
        "rows": assigned,
        "validation_cell_counts": recount(),
    }


def evaluate_cell_floors(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    train = Counter(
        r["primary_cell"] for r in rows if r["split"] == "train" and r.get("primary_cell")
    )
    val = Counter(
        r["primary_cell"] for r in rows if r["split"] == "validation" and r.get("primary_cell")
    )
    gaps = {}
    for cell in PRIMARY_CELLS:
        if train.get(cell, 0) < CELL_TRAIN_FLOOR:
            gaps[f"train:{cell}"] = CELL_TRAIN_FLOOR - train.get(cell, 0)
        floor = CRITICAL_VAL_FLOOR if cell in CRITICAL_CELLS else CELL_VAL_FLOOR
        if val.get(cell, 0) < floor:
            gaps[f"validation:{cell}"] = floor - val.get(cell, 0)
    return {
        "gaps": gaps,
        "pass": not gaps,
        "train_counts": dict(train),
        "validation_counts": dict(val),
    }


def evaluate_pairing_generalization(
    rows: Sequence[Mapping[str, Any]],
    pair_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    by_id = {row["identity"]: row for row in rows}
    valid = []
    by_surface: Counter[str] = Counter()
    for pair in pair_records:
        pos = by_id.get(str(pair.get("positive_identity")))
        neg = by_id.get(str(pair.get("negative_identity")))
        if pos is None or neg is None:
            continue
        shared = list(pair.get("shared_cues") or [])
        if not shared:
            continue
        if pos.get("evidence_label") == neg.get("evidence_label"):
            continue
        if pos.get("split") != neg.get("split"):
            continue
        surf = str(pair.get("shared_surface") or "")
        valid.append(pair)
        by_surface[surf] += 1
    gaps = {}
    if len(valid) < PAIRING_FLOORS["matched_positive_negative_pairs"]:
        gaps["matched_positive_negative_pairs"] = (
            PAIRING_FLOORS["matched_positive_negative_pairs"] - len(valid)
        )
    for key, surf in (
        ("matched_SHORT_ATOM", "SHORT_ATOM"),
        ("matched_DEFINITION_STYLE", "DEFINITION_STYLE"),
        ("matched_ORDINARY_PROSE", "ORDINARY_PROSE"),
    ):
        if by_surface.get(surf, 0) < PAIRING_FLOORS[key]:
            gaps[key] = PAIRING_FLOORS[key] - by_surface.get(surf, 0)
    return {
        "gaps": gaps,
        "matched_by_surface": dict(by_surface),
        "matched_positive_negative_pairs": len(valid),
        "pass": not gaps,
    }


def evaluate_source_diversity(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    failures = []
    by_label: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["evidence_label"] in {"EVIDENCE_PRESENT", "NO_EVIDENCE"}:
            by_label[str(row["evidence_label"])].append(row)
    distributions = {}
    for label, label_rows in by_label.items():
        fams = Counter(source_family(r) for r in label_rows)
        n = len(label_rows) or 1
        top_share = (fams.most_common(1)[0][1] / n) if fams else 0.0
        distributions[label] = {
            "counts": dict(fams),
            "n": len(label_rows),
            "top_share": top_share,
        }
        if top_share > SOURCE_DIVERSITY["max_source_family_share"]:
            failures.append(f"{label}_source_family_share={top_share:.4f}")
    for cell_prefix, min_fams in (
        ("DEFINITION_STYLE", SOURCE_DIVERSITY["min_source_families_definition_style"]),
        ("SHORT_ATOM", SOURCE_DIVERSITY["min_source_families_short_atom"]),
    ):
        cell_rows = [r for r in rows if str(r.get("primary_cell") or "").startswith(cell_prefix)]
        fams = {source_family(r) for r in cell_rows}
        if len(fams) < min_fams:
            failures.append(f"{cell_prefix}_source_families={len(fams)}<{min_fams}")
    return {"distributions": distributions, "failures": failures, "pass": not failures}


def evaluate_domain_coverage(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    present: Counter[str] = Counter()
    none: Counter[str] = Counter()
    for row in rows:
        key = domain_key(row)
        if key == "unspecified":
            continue
        if row["evidence_label"] == "EVIDENCE_PRESENT":
            present[key] += 1
        elif row["evidence_label"] == "NO_EVIDENCE":
            none[key] += 1
    failures = []
    missing_none = {}
    missing_present = {}
    floor = TOPIC_BALANCE["support_min_for_opposite_requirement"]
    need = TOPIC_BALANCE["matching_opposite_min"]
    for domain, count in present.items():
        if count >= floor and none.get(domain, 0) < need:
            missing_none[domain] = need - none.get(domain, 0)
    for domain, count in none.items():
        if count >= floor and present.get(domain, 0) < need:
            missing_present[domain] = need - present.get(domain, 0)
    if missing_none:
        failures.append({"missing_none_for_present_domains": missing_none})
    if missing_present:
        failures.append({"missing_present_for_none_domains": missing_present})
    return {
        "failures": failures,
        "none_domain_counts": dict(sorted(none.items())),
        "pass": not failures,
        "present_domain_counts": dict(sorted(present.items())),
    }


def evaluate_provenance_generalization(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    val = [r for r in rows if r["split"] == "validation"]
    val_obs = sum(1 for r in val if r.get("provenance") == "OBSERVED")
    val_frac = (val_obs / len(val)) if val else 0.0
    failures = []
    if val_frac < PROVENANCE["observed_validation_fraction_min"]:
        failures.append(f"observed_validation_fraction={val_frac:.4f}")
    critical = {}
    for cell in CRITICAL_CELLS:
        cell_val = [r for r in val if r.get("primary_cell") == cell]
        obs = sum(1 for r in cell_val if r.get("provenance") == "OBSERVED")
        frac = (obs / len(cell_val)) if cell_val else 0.0
        critical[cell] = {"n": len(cell_val), "observed": obs, "observed_fraction": frac}
        if frac < PROVENANCE["critical_cell_observed_fraction_min"]:
            failures.append(f"{cell}_observed_fraction={frac:.4f}")
    # Integrity: never invent OBSERVED from INFERRED.
    invalid_prov = sum(
        1 for r in rows if r.get("provenance") not in {"OBSERVED", "INFERRED"}
    )
    if invalid_prov:
        failures.append(f"invalid_provenance_rows={invalid_prov}")
    return {
        "critical_cells": critical,
        "failures": failures,
        "observed_validation_fraction": val_frac,
        "pass": not failures,
        "provenance_counts": dict(Counter(r.get("provenance") for r in rows)),
    }


def evaluate_surface_balance_generalization(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_label: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["evidence_label"] in {"EVIDENCE_PRESENT", "NO_EVIDENCE"}:
            by_label[str(row["evidence_label"])].append(row)

    def stats(label_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        n = len(label_rows) or 1
        atom = sum(1 for r in label_rows if surface_form(r["text"]) == SURFACE_ATOM) / n
        prose = sum(1 for r in label_rows if surface_form(r["text"]) == SURFACE_PROSE) / n
        punct = sum(1 for r in label_rows if punctuation_present(r["text"])) / n
        definition = sum(1 for r in label_rows if definition_style(r["text"])) / n
        median_tokens = _median([word_count(r["text"]) for r in label_rows])
        return {
            "ATOM_rate": atom,
            "PROSE_rate": prose,
            "definition_style_rate": definition,
            "median_token_count": median_tokens,
            "n": len(label_rows),
            "punctuation_present_rate": punct,
        }

    present = stats(by_label.get("EVIDENCE_PRESENT") or [])
    none = stats(by_label.get("NO_EVIDENCE") or [])
    failures = []
    ratio = None
    if present["median_token_count"] and none["median_token_count"]:
        ratio = present["median_token_count"] / none["median_token_count"]
        if (
            ratio < SURFACE_BALANCE["median_token_count_ratio_min"]
            or ratio > SURFACE_BALANCE["median_token_count_ratio_max"]
        ):
            failures.append(f"median_token_count_ratio={ratio:.4f}")
    if abs(present["ATOM_rate"] - none["ATOM_rate"]) > SURFACE_BALANCE["atom_rate_abs_diff_max"]:
        failures.append("ATOM_rate_diff")
    if abs(present["PROSE_rate"] - none["PROSE_rate"]) > SURFACE_BALANCE["prose_rate_abs_diff_max"]:
        failures.append("PROSE_rate_diff")
    if (
        abs(present["definition_style_rate"] - none["definition_style_rate"])
        > SURFACE_BALANCE["definition_style_rate_diff_max"]
    ):
        failures.append("definition_style_rate_diff")
    if (
        abs(present["punctuation_present_rate"] - none["punctuation_present_rate"])
        > SURFACE_BALANCE["punctuation_present_rate_diff_max"]
    ):
        failures.append("punctuation_present_rate_diff")
    return {
        "EVIDENCE_PRESENT": present,
        "NO_EVIDENCE": none,
        "failures": failures,
        "median_token_count_ratio": ratio,
        "pass": not failures,
    }


def evaluate_lexical_overlap_generalization(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    present = [r for r in rows if r["evidence_label"] == "EVIDENCE_PRESENT"]
    none = [r for r in rows if r["evidence_label"] == "NO_EVIDENCE"]
    pos_freq: Counter[str] = Counter()
    neg_freq: Counter[str] = Counter()
    for row in present:
        pos_freq.update(tokens(row["text"]))
    for row in none:
        neg_freq.update(tokens(row["text"]))
    top_pos = {tok for tok, _ in pos_freq.most_common(100)}
    top_neg = {tok for tok, _ in neg_freq.most_common(100)}
    top_jacc = jaccard(top_pos, top_neg)
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


def evaluate_embedding_hardness_generalization(
    embedding_report: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not embedding_report:
        return {
            "failures": ["embedding_hardness_report_missing"],
            "pass": False,
            "report": None,
        }
    failures = []
    median_opp = embedding_report.get("median_nearest_opposite_label_cosine")
    frac = embedding_report.get("frac_nearest_opposite_cosine_ge_0_75")
    if median_opp is None:
        # accept legacy key none_frac style if present as median only
        median_opp = embedding_report.get("median_nearest_opposite_label_cosine")
    if median_opp is None or float(median_opp) < EMBEDDING_HARDNESS[
        "median_nearest_opposite_label_cosine_min"
    ]:
        failures.append(f"median_nearest_opposite_label_cosine={median_opp}")
    if frac is None or float(frac) < EMBEDDING_HARDNESS[
        "frac_nearest_opposite_cosine_ge_0_75_min"
    ]:
        failures.append(f"frac_nearest_opposite_cosine_ge_0_75={frac}")
    return {"failures": failures, "pass": not failures, "report": dict(embedding_report)}


def evaluate_shallow_shortcut_generalization(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    labels = ("EVIDENCE_PRESENT", "NO_EVIDENCE")
    train = [
        r for r in rows if r["split"] == "train" and r["evidence_label"] in labels
    ]
    val = [
        r for r in rows if r["split"] == "validation" and r["evidence_label"] in labels
    ]
    if not train or not val:
        return {"failures": ["insufficient_binary_rows"], "pass": False}
    train_y = [str(r["evidence_label"]) for r in train]
    val_y = [str(r["evidence_label"]) for r in val]

    best_thr = 0
    best_ba = -1.0
    lengths = sorted({word_count(str(r["text"])) for r in train})
    for thr in lengths:
        pred = [
            "EVIDENCE_PRESENT" if word_count(str(r["text"])) >= thr else "NO_EVIDENCE"
            for r in train
        ]
        ba = _balanced_accuracy(train_y, pred, labels)
        if ba > best_ba:
            best_ba = ba
            best_thr = thr
    length_pred = [
        "EVIDENCE_PRESENT" if word_count(str(r["text"])) >= best_thr else "NO_EVIDENCE"
        for r in val
    ]
    length_ba = _balanced_accuracy(val_y, length_pred, labels)

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
        )

    pos_vecs = [feats(r) for r, y in zip(train, train_y) if y == "EVIDENCE_PRESENT"]
    neg_vecs = [feats(r) for r, y in zip(train, train_y) if y == "NO_EVIDENCE"]

    def mean_vec(vecs: Sequence[tuple[float, ...]]) -> tuple[float, ...]:
        if not vecs:
            return tuple(0.0 for _ in range(6))
        dim = len(vecs[0])
        return tuple(sum(v[i] for v in vecs) / len(vecs) for i in range(dim))

    pos_mu = mean_vec(pos_vecs)
    neg_mu = mean_vec(neg_vecs)

    def nearest(row: Mapping[str, Any]) -> str:
        vec = feats(row)
        d_pos = sum((a - b) ** 2 for a, b in zip(vec, pos_mu))
        d_neg = sum((a - b) ** 2 for a, b in zip(vec, neg_mu))
        return "EVIDENCE_PRESENT" if d_pos <= d_neg else "NO_EVIDENCE"

    surface_pred = [nearest(r) for r in val]
    surface_ba = _balanced_accuracy(val_y, surface_pred, labels)
    surface_f1 = _macro_f1(val_y, surface_pred, labels)

    # Train-only TF-IDF → validation balanced accuracy (no exception).
    df: Counter[str] = Counter()
    docs = []
    for row in train:
        bag = tokens(row["text"])
        docs.append(bag)
        df.update(set(bag))
    n_docs = len(docs) or 1
    idf = {tok: math.log((1 + n_docs) / (1 + df[tok])) + 1.0 for tok in df}

    def tfidf_vec(bag: set[str]) -> dict[str, float]:
        if not bag:
            return {}
        tf = 1.0 / len(bag)
        return {tok: tf * idf.get(tok, 0.0) for tok in bag}

    pos_acc: dict[str, float] = defaultdict(float)
    neg_acc: dict[str, float] = defaultdict(float)
    pos_n = sum(1 for y in train_y if y == "EVIDENCE_PRESENT") or 1
    neg_n = sum(1 for y in train_y if y == "NO_EVIDENCE") or 1
    for row, y in zip(train, train_y):
        vec = tfidf_vec(tokens(row["text"]))
        target = pos_acc if y == "EVIDENCE_PRESENT" else neg_acc
        for tok, weight in vec.items():
            target[tok] += weight
    for tok in list(pos_acc):
        pos_acc[tok] /= pos_n
    for tok in list(neg_acc):
        neg_acc[tok] /= neg_n

    def tfidf_pred(text: str) -> str:
        vec = tfidf_vec(tokens(text))
        s_pos = sum(vec.get(t, 0.0) * pos_acc.get(t, 0.0) for t in vec)
        s_neg = sum(vec.get(t, 0.0) * neg_acc.get(t, 0.0) for t in vec)
        return "EVIDENCE_PRESENT" if s_pos >= s_neg else "NO_EVIDENCE"

    tfidf_preds = [tfidf_pred(str(r["text"])) for r in val]
    tfidf_ba = _balanced_accuracy(val_y, tfidf_preds, labels)

    failures = []
    if length_ba > SHALLOW_SHORTCUT["length_only_balanced_accuracy_max"]:
        failures.append(f"length_only_balanced_accuracy={length_ba:.4f}")
    if surface_ba > SHALLOW_SHORTCUT["surface_only_balanced_accuracy_max"]:
        failures.append(f"surface_only_balanced_accuracy={surface_ba:.4f}")
    if surface_f1 > SHALLOW_SHORTCUT["surface_only_macro_f1_max"]:
        failures.append(f"surface_only_macro_f1={surface_f1:.4f}")
    if tfidf_ba > SHALLOW_SHORTCUT["tfidf_balanced_accuracy_max"]:
        failures.append(f"tfidf_balanced_accuracy={tfidf_ba:.4f}")
    return {
        "failures": failures,
        "length_only_balanced_accuracy": length_ba,
        "length_only_threshold_words": best_thr,
        "pass": not failures,
        "surface_only_balanced_accuracy": surface_ba,
        "surface_only_macro_f1": surface_f1,
        "tfidf_balanced_accuracy": tfidf_ba,
    }


def cell_diagnostics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    out = {}
    for cell in PRIMARY_CELLS:
        cell_rows = [r for r in rows if r.get("primary_cell") == cell]
        if not cell_rows:
            out[cell] = {"support": 0}
            continue
        lengths = [word_count(r["text"]) for r in cell_rows]
        out[cell] = {
            "domain_distribution": dict(
                Counter(domain_key(r) for r in cell_rows).most_common(20)
            ),
            "length_distribution": {
                "max": max(lengths),
                "median": _median([float(x) for x in lengths]),
                "min": min(lengths),
            },
            "observed_share": sum(1 for r in cell_rows if r.get("provenance") == "OBSERVED")
            / len(cell_rows),
            "source_distribution": dict(
                Counter(source_family(r) for r in cell_rows).most_common(20)
            ),
            "split_counts": dict(Counter(r["split"] for r in cell_rows)),
            "support": len(cell_rows),
        }
    return out


def evaluate_spent_reserve_overlap(
    rows: Sequence[Mapping[str, Any]],
    *,
    spent_ids: set[str],
) -> dict[str, Any]:
    overlap = sorted({r["identity"] for r in rows} & set(spent_ids))
    return {
        "overlap_identities": overlap[:32],
        "overlap_n": len(overlap),
        "pass": len(overlap) == 0,
    }


def evaluate_generalization_readiness(
    rows: Sequence[Mapping[str, Any]],
    *,
    pair_records: Sequence[Mapping[str, Any]],
    ontology: Sequence[str],
    blocked: Mapping[str, str] | None = None,
    heldout_ids: set[str] | None = None,
    measurement_ids: set[str] | None = None,
    spent_ids: set[str] | None = None,
    embedding_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    cells = evaluate_cell_floors(rows)
    pairing = evaluate_pairing_generalization(rows, pair_records)
    source = evaluate_source_diversity(rows)
    domain = evaluate_domain_coverage(rows)
    provenance = evaluate_provenance_generalization(rows)
    surface_balance = evaluate_surface_balance_generalization(rows)
    lexical = evaluate_lexical_overlap_generalization(rows)
    embedding = evaluate_embedding_hardness_generalization(embedding_report)
    shallow = evaluate_shallow_shortcut_generalization(rows)
    disjointness = evaluate_disjointness(
        rows,
        blocked=blocked,
        heldout_ids=heldout_ids,
        measurement_ids=measurement_ids,
    )
    duplicates = evaluate_duplicate_quality(rows)
    schema = evaluate_schema_integrity(rows, ontology=ontology)
    spent = evaluate_spent_reserve_overlap(rows, spent_ids=set(spent_ids or set()))
    # Gold mapping integrity: subtypes must match frozen mapping.
    gold_invalid = 0
    for row in rows:
        if SUBTYPE_TO_GOLD.get(str(row.get("evidence_subtype"))) != row.get("evidence_label"):
            gold_invalid += 1
        if row.get("required_evidence_present") != REQUIRED_EVIDENCE_PRESENT.get(
            str(row.get("evidence_subtype"))
        ):
            gold_invalid += 1

    gate_pass = {
        "cell_support_floors_pass": cells["pass"],
        "source_provenance_floors_pass": source["pass"] and provenance["pass"],
        "domain_coverage_pass": domain["pass"],
        "all_disjointness_pass": disjointness["pass"],
        "duplicate_quality_pass": duplicates["pass"],
        "pairing_pass": pairing["pass"],
        "surface_balance_pass": surface_balance["pass"],
        "lexical_overlap_pass": lexical["pass"],
        "embedding_hardness_pass": embedding["pass"],
        "shallow_shortcut_pass": shallow["pass"],
        "schema_integrity_pass": schema["pass"] and gold_invalid == 0,
        "spent_reserve_overlap_pass": spent["pass"],
        "label_provenance_invalid_rows_zero": gold_invalid == 0,
    }
    ready = all(gate_pass.values())
    return {
        "cell_diagnostics": cell_diagnostics(rows),
        "details": {
            "cells": cells,
            "disjointness": disjointness,
            "domain_coverage": domain,
            "duplicate_quality": duplicates,
            "embedding_hardness": embedding,
            "gold_invalid_rows": gold_invalid,
            "lexical_overlap": lexical,
            "pairing": pairing,
            "provenance": provenance,
            "schema_integrity": schema,
            "shallow_shortcut": shallow,
            "source_diversity": source,
            "spent_reserve_overlap": spent,
            "surface_balance": surface_balance,
        },
        "gate_pass": gate_pass,
        "gate_rule": GATE_RULE,
        "ready": ready,
        "state": "READY" if ready else "PREREGISTERED",
        "surface_rule": SURFACE_RULE,
        "weighted_score_allowed": False,
    }


def select_cell_balanced(
    rows: Sequence[Mapping[str, Any]],
    *,
    targets: Mapping[str, int] | None = None,
) -> list[dict[str, Any]]:
    """Downsample excess SHORT_ATOM NONE while preserving floors and OBSERVED."""
    targets = dict(targets or {})
    default_cap = {
        # Keep SHORT_ATOM NONE near PRESENT mass so length/surface balance holds.
        "SHORT_ATOM/NO_EVIDENCE": 250,
        "SHORT_ATOM/EVIDENCE_PRESENT": 250,
        "PROSE/NO_EVIDENCE": 400,
        "PROSE/EVIDENCE_PRESENT": 340,
        "DEFINITION_STYLE/NO_EVIDENCE": 340,
        "DEFINITION_STYLE/EVIDENCE_PRESENT": 340,
        "ORDINARY_PROSE/NO_EVIDENCE": 380,
        "ORDINARY_PROSE/EVIDENCE_PRESENT": 380,
    }
    default_cap.update(targets)
    by_cell: dict[str, list[dict[str, Any]]] = defaultdict(list)
    uncertain = []
    for row in rows:
        item = dict(row)
        cell = item.get("primary_cell")
        if item["evidence_label"] == "UNCERTAIN":
            uncertain.append(item)
        elif cell:
            by_cell[str(cell)].append(item)

    def pref(row: Mapping[str, Any]) -> tuple:
        note = str(row.get("notes") or "")
        matched = (
            0
            if (
                "lookalike" in note
                or "def_matched" in note
                or "ordinary_present_fill" in note
                or "nearcopy" in note
                or "wikt_atom_none" in note
            )
            else 1
        )
        return (
            0 if row.get("provenance") == "OBSERVED" else 1,
            matched,
            0 if row.get("pair_group_id") else 1,
            word_count(str(row["text"])),
            row["identity"],
        )

    selected: list[dict[str, Any]] = []
    for cell in PRIMARY_CELLS:
        pool = sorted(by_cell.get(cell) or [], key=pref)
        cap = default_cap.get(cell, 400)
        # Always keep at least train+val floors when available.
        floor = CELL_TRAIN_FLOOR + (
            CRITICAL_VAL_FLOOR if cell in CRITICAL_CELLS else CELL_VAL_FLOOR
        )
        keep_n = min(len(pool), max(floor, min(len(pool), cap)))
        # Reserve matched/lookalike NONE slots so OBSERVED mass cannot eject them.
        matched_pool = [
            r
            for r in pool
            if (
                "lookalike" in str(r.get("notes") or "")
                or "def_matched" in str(r.get("notes") or "")
                or "nearcopy" in str(r.get("notes") or "")
                or "wikt_atom_none" in str(r.get("notes") or "")
            )
        ]
        matched_ids = {r["identity"] for r in matched_pool}
        other_pool = [r for r in pool if r["identity"] not in matched_ids]
        reserve_matched = (
            min(len(matched_pool), max(160, keep_n // 2))
            if cell.endswith("/NO_EVIDENCE")
            else 0
        )
        kept: list[dict[str, Any]] = []
        kept.extend(sorted(matched_pool, key=pref)[:reserve_matched])
        for row in sorted(other_pool, key=pref):
            if len(kept) >= keep_n:
                break
            kept.append(row)
        if len(kept) < keep_n:
            for row in sorted(matched_pool, key=pref)[reserve_matched:]:
                if len(kept) >= keep_n:
                    break
                if row["identity"] not in {k["identity"] for k in kept}:
                    kept.append(row)
        # Critical cells: ensure OBSERVED mass can support 40% validation.
        if cell in CRITICAL_CELLS:
            obs = [r for r in pool if r.get("provenance") == "OBSERVED"]
            need_obs = max(
                int(0.45 * (CRITICAL_VAL_FLOOR + 10)),
                int(0.40 * keep_n * 0.5),
            )
            have_obs_ids = {r["identity"] for r in kept if r.get("provenance") == "OBSERVED"}
            for row in obs:
                if len(have_obs_ids) >= min(need_obs, len(obs)):
                    break
                if row["identity"] in have_obs_ids:
                    continue
                if len(kept) >= keep_n:
                    for j in range(len(kept) - 1, -1, -1):
                        if kept[j].get("provenance") != "OBSERVED" and "def_matched" not in str(
                            kept[j].get("notes") or ""
                        ):
                            have_obs_ids.discard(kept[j]["identity"])
                            kept[j] = row
                            have_obs_ids.add(row["identity"])
                            break
                else:
                    kept.append(row)
                    have_obs_ids.add(row["identity"])
        selected.extend(kept[:keep_n])
    # Cap uncertain retention (not primary remediation target).
    uncertain_sorted = sorted(uncertain, key=pref)[:200]
    selected.extend(uncertain_sorted)

    # Enforce max source-family share per gate label (wiktionary aggregate included).
    selected = enforce_source_family_cap(selected, max_share=SOURCE_DIVERSITY["max_source_family_share"])
    selected.sort(key=lambda item: item["identity"])
    return selected


def enforce_source_family_cap(
    rows: Sequence[Mapping[str, Any]],
    *,
    max_share: float,
) -> list[dict[str, Any]]:
    """Prefer diluting with non-offender rows; drop unpaired offenders only if needed."""
    out = [dict(r) for r in rows]
    for _guard in range(64):
        changed = False
        for label in ("EVIDENCE_PRESENT", "NO_EVIDENCE"):
            labeled = [r for r in out if r["evidence_label"] == label]
            other = [r for r in out if r["evidence_label"] != label]
            n = len(labeled)
            if n == 0:
                continue
            counts = Counter(source_family(r) for r in labeled)
            top_fam, top_n = counts.most_common(1)[0]
            if top_n / n <= max_share:
                continue
            # Dilute first: keep all labeled, but if share still high after prior
            # loops, drop unpaired non-OBSERVED offenders.
            offenders = sorted(
                [
                    r
                    for r in labeled
                    if source_family(r) == top_fam
                    and r.get("provenance") != "OBSERVED"
                    and not r.get("pair_group_id")
                ],
                key=lambda item: item["identity"],
            )
            # Need top_n / (n - drop) <= max_share => drop >= n - top_n/max_share
            need_drop = max(1, int(n - (top_n / max_share) + 1))
            drop_ids = {r["identity"] for r in offenders[:need_drop]}
            if not drop_ids:
                # Last resort: drop unpaired OBSERVED offenders outside critical cells.
                offenders = sorted(
                    [
                        r
                        for r in labeled
                        if source_family(r) == top_fam
                        and not r.get("pair_group_id")
                        and r.get("primary_cell") not in CRITICAL_CELLS
                    ],
                    key=lambda item: item["identity"],
                )
                drop_ids = {r["identity"] for r in offenders[:need_drop]}
            if not drop_ids:
                continue
            labeled = [r for r in labeled if r["identity"] not in drop_ids]
            out = other + labeled
            changed = True
        if not changed:
            break
    return out


def load_blocked_ids(
    *,
    ledger: Mapping[str, Any],
    spent_row_files: Sequence[Sequence[Mapping[str, Any]]] = (),
    surface_row_files: Sequence[Sequence[Mapping[str, Any]]] = (),
) -> tuple[set[str], set[str], dict[str, str]]:
    """Block spent reserves, V1R9/held-out/measurement/diagnostic identities."""
    blocked: set[str] = set()
    blocked_src: set[str] = set()
    reasons: dict[str, str] = {}
    for record in ledger.get("identities") or []:
        state = str(record.get("state") or "")
        if (
            record.get("evaluation_spent")
            or record.get("evaluation_reserved")
            or record.get("evaluation_abandoned")
            or state
            in {"EVAL_SPENT", "EVAL_RESERVE", "EVAL_BOUND", "EVAL_ABANDONED"}
        ):
            digest = record.get("normalized_text_sha256")
            if digest:
                blocked.add(str(digest))
                reasons[str(digest)] = "ledger_eval"
    for rows in spent_row_files:
        for row in rows:
            digest = row.get("normalized_text_sha256") or row.get("identity")
            if digest:
                blocked.add(str(digest))
                reasons[str(digest)] = "spent_reserve"
            text = row.get("text")
            if isinstance(text, str) and text.strip():
                blocked.add(normalized_text_sha256(text))
            src = row.get("source_sha256")
            if src:
                blocked_src.add(str(src))
            parent = row.get("parent_identity")
            if parent:
                blocked.add(str(parent))
    for rows in surface_row_files:
        for row in rows:
            digest = row.get("identity") or row.get("normalized_text_sha256")
            if digest:
                blocked.add(str(digest))
                reasons[str(digest)] = "v1r9_or_surface"
            text = row.get("text")
            if isinstance(text, str) and text.strip():
                blocked.add(normalized_text_sha256(text))
            src = row.get("source_sha256")
            if src:
                blocked_src.add(str(src))
            parent = row.get("parent_identity")
            if parent:
                blocked.add(str(parent))
    return blocked, blocked_src, reasons


def assemble_surface_artifacts(payload: Mapping[str, Any]) -> dict[str, Any]:
    rows = list(payload["rows"])
    pair_records = list(payload["pair_records"])
    readiness = payload["readiness"]
    dataset_body = "\n".join(canonical_json(row) for row in rows) + ("\n" if rows else "")
    dataset_sha = sha256_text(dataset_body)
    split_manifest = {
        "split_seed_prefix": SPLIT_SEED_PREFIX,
        "train_identities": sorted(
            r["identity"] for r in rows if r["split"] == "train"
        ),
        "validation_identities": sorted(
            r["identity"] for r in rows if r["split"] == "validation"
        ),
    }
    counts = {
        "total": len(rows),
        "train": sum(1 for r in rows if r["split"] == "train"),
        "validation": sum(1 for r in rows if r["split"] == "validation"),
        "by_label": dict(Counter(r["evidence_label"] for r in rows)),
        "by_primary_cell": dict(
            Counter(r.get("primary_cell") for r in rows if r.get("primary_cell"))
        ),
        "by_provenance": dict(Counter(r.get("provenance") for r in rows)),
    }
    manifest = {
        "counts": counts,
        "dataset_sha256": dataset_sha,
        "design_rule": DESIGN_RULE,
        "gate_rule": GATE_RULE,
        "parent_diagnosis": PARENT_DIAGNOSIS,
        "schema_sha256": dict(SCHEMA_SHA),
        "spent_reserve": SPENT_RESERVE,
        "stage_a_best_sha256": STAGE_A_BEST_SHA,
        "model_wide_best_sha256": MODEL_WIDE_BEST_SHA,
        "state": readiness.get("state"),
        "surface_rule": SURFACE_RULE,
        "v1r9_surface_sha256": V1R9_SURFACE_SHA,
    }
    return {
        "contrast_pair_witness": {
            "n": len(pair_records),
            "pairs": pair_records,
        },
        "dataset_body": dataset_body,
        "dataset_sha256": dataset_sha,
        "disjointness_witness": readiness["details"]["disjointness"],
        "label_provenance_witness": readiness["details"]["provenance"],
        "manifest": manifest,
        "provenance_witness": readiness["details"]["provenance"],
        "readiness_receipt": readiness,
        "shortcut_diagnostics": readiness["details"]["shallow_shortcut"],
        "source_domain_witness": {
            "domain_coverage": readiness["details"]["domain_coverage"],
            "source_diversity": readiness["details"]["source_diversity"],
        },
        "split_manifest": split_manifest,
        "summary": {
            "counts": counts,
            "ready": readiness.get("ready"),
            "state": readiness.get("state"),
            "surface_rule": SURFACE_RULE,
        },
    }


def _force_surface_matched_pairs(
    rows: Sequence[Mapping[str, Any]],
    pair_records: Sequence[Mapping[str, Any]],
    *,
    surface: str,
    min_overlap: float = 0.03,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Force additional pairs for a surface using lookalike/matched NONE."""
    by_id = {row["identity"]: dict(row) for row in rows}
    existing = {
        (p.get("positive_identity"), p.get("negative_identity")) for p in pair_records
    }
    used_pos = {p.get("positive_identity") for p in pair_records}
    used_neg = {p.get("negative_identity") for p in pair_records}
    out_pairs = list(pair_records)
    pos_rows = [
        by_id[i]
        for i in by_id
        if str(by_id[i].get("primary_cell") or "").startswith(surface + "/")
        and by_id[i].get("evidence_label") == "EVIDENCE_PRESENT"
        and i not in used_pos
    ]
    neg_rows = [
        by_id[i]
        for i in by_id
        if str(by_id[i].get("primary_cell") or "").startswith(surface + "/")
        and by_id[i].get("evidence_label") == "NO_EVIDENCE"
        and i not in used_neg
    ]
    # Prefer lookalike/matched negatives first.
    neg_rows.sort(
        key=lambda item: (
            0
            if ("lookalike" in str(item.get("notes") or "") or "def_matched" in str(item.get("notes") or ""))
            else 1,
            item["identity"],
        )
    )
    for pos in sorted(pos_rows, key=lambda item: item["identity"]):
        pos_tok = tokens(pos["text"])
        best = None
        best_score = -1.0
        for neg in neg_rows:
            if neg["identity"] in used_neg:
                continue
            overlap = jaccard(pos_tok, tokens(neg["text"]))
            if overlap < min_overlap and surface != "SHORT_ATOM":
                continue
            score = overlap - 0.01 * abs(word_count(pos["text"]) - word_count(neg["text"]))
            if score > best_score:
                best_score = score
                best = neg
        if best is None:
            continue
        shared = sorted(pos_tok & tokens(best["text"]))[:16] or [
            f"surface:{surface}",
            f"len:{word_count(pos['text'])}",
        ]
        group = sha256_text(f"gpair:{pos['identity']}:{best['identity']}")[:16]
        pos["pair_group_id"] = group
        pos["shared_cues"] = shared
        best["pair_group_id"] = group
        best["paired_positive_identity"] = pos["identity"]
        best["shared_cues"] = shared
        used_neg.add(best["identity"])
        used_pos.add(pos["identity"])
        by_id[pos["identity"]] = pos
        by_id[best["identity"]] = best
        key = (pos["identity"], best["identity"])
        if key not in existing:
            out_pairs.append(
                {
                    "negative_identity": best["identity"],
                    "negative_missing_core": list(best.get("missing_required_semantics") or []),
                    "pair_group_id": group,
                    "positive_identity": pos["identity"],
                    "positive_required_core": list(pos.get("active_family_support") or [])[:8],
                    "shared_cues": shared,
                    "shared_domain": f"{domain_key(pos)}|{domain_key(best)}",
                    "shared_surface": surface,
                }
            )
    return sorted(by_id.values(), key=lambda item: item["identity"]), out_pairs


def _force_definition_matched_pairs(
    rows: Sequence[Mapping[str, Any]],
    pair_records: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows, pairs = _force_surface_matched_pairs(
        rows, pair_records, surface="DEFINITION_STYLE", min_overlap=0.03
    )
    rows, pairs = _force_surface_matched_pairs(
        rows, pairs, surface="ORDINARY_PROSE", min_overlap=0.05
    )
    rows, pairs = _force_surface_matched_pairs(
        rows, pairs, surface="SHORT_ATOM", min_overlap=0.0
    )
    return rows, pairs


def dedupe_near_duplicates_within_split(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Drop near-duplicate extras within each split; keep OBSERVED/paired first."""
    by_split: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_split[str(row["split"])].append(dict(row))
    kept: list[dict[str, Any]] = []
    for split, split_rows in by_split.items():
        ordered = sorted(
            split_rows,
            key=lambda item: (
                0 if item.get("provenance") == "OBSERVED" else 1,
                0 if item.get("pair_group_id") else 1,
                item["identity"],
            ),
        )
        accepted: list[dict[str, Any]] = []
        for row in ordered:
            duplicate = False
            row_prefix = normalized_text(row["text"])[:24]
            for prev in accepted:
                if normalized_text(prev["text"])[:24] != row_prefix and abs(
                    word_count(prev["text"]) - word_count(row["text"])
                ) > 2:
                    continue
                if are_near_duplicates(prev["text"], row["text"]):
                    # Keep pair members even if near-dup with unpaired rows.
                    if row.get("pair_group_id") and prev.get("pair_group_id") == row.get(
                        "pair_group_id"
                    ):
                        continue
                    duplicate = True
                    break
            if not duplicate:
                accepted.append(row)
        kept.extend(accepted)
    kept.sort(key=lambda item: item["identity"])
    return kept


def build_generalization_surface(
    source_rows: Sequence[Mapping[str, Any]],
    *,
    blocked_ids: set[str],
    blocked_source_hashes: set[str] | None = None,
    ontology: Sequence[str],
    blocked_reasons: Mapping[str, str] | None = None,
    heldout_ids: set[str] | None = None,
    measurement_ids: set[str] | None = None,
    spent_ids: set[str] | None = None,
    embedding_report: Mapping[str, Any] | None = None,
    cell_caps: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    examples = collect_examples(
        source_rows,
        blocked_ids=blocked_ids,
        blocked_source_hashes=blocked_source_hashes,
    )
    examples = stamp_source_buckets(examples)
    examples = select_cell_balanced(examples, targets=cell_caps)
    paired_rows, pair_records = build_matched_contrast_pairs(examples)
    paired_rows, pair_records = _force_definition_matched_pairs(paired_rows, pair_records)
    paired_rows = stamp_source_buckets(paired_rows)
    split_result = assign_splits_by_component(paired_rows)
    rows = dedupe_near_duplicates_within_split(split_result["rows"])
    # Recompute pair records against surviving ids.
    alive = {r["identity"] for r in rows}
    pair_records = [
        p
        for p in pair_records
        if p.get("positive_identity") in alive and p.get("negative_identity") in alive
    ]
    readiness = evaluate_generalization_readiness(
        rows,
        pair_records=pair_records,
        ontology=ontology,
        blocked=blocked_reasons,
        heldout_ids=heldout_ids,
        measurement_ids=measurement_ids,
        spent_ids=spent_ids if spent_ids is not None else blocked_ids,
        embedding_report=embedding_report,
    )
    assembled = assemble_surface_artifacts(
        {
            "pair_records": pair_records,
            "readiness": readiness,
            "rows": rows,
        }
    )
    return {
        "assembled": assembled,
        "component_witness": split_result["component_witness"],
        "pair_records": pair_records,
        "readiness": readiness,
        "rows": rows,
        "validation_cell_counts": split_result["validation_cell_counts"],
    }
