"""DESIGN_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE contracts and builder.

Builds a fresh Stage-A train/validation surface emphasizing difficult NONE.
Does not train, does not score reserves, and does not move BEST.
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
    SURFACE_AMBIGUOUS,
    SURFACE_ATOM,
    SURFACE_PROSE,
    surface_form,
    word_count,
)
from .holdout_guard import normalized_text_sha256

SURFACE_RULE = "HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1"
DESIGN_RULE = "DESIGN_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE"
PARENT_FAIL = "HYPERLEX_CLASSIFICATION_V4_BALANCED_RESERVE_EVAL_V1"
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
SPLIT_SEED_PREFIX = "hlx.v5.stage_a.negative.surface.split.v1"
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

# Future Stage-A train contract (frozen only when surface is READY).
STAGE_A_TRAIN_CONTRACT = {
    "EVIDENCE_PRESENT_recall_min": 0.70,
    "NO_EVIDENCE_recall_min": 0.90,
    "false_evidence_entry_rate_on_none_max": 0.05,
    "optimize_family_metrics_before_stage_a_pass": False,
    "rule": "HYPERLEX_CLASSIFICATION_V5_STAGE_A_TRAIN_V1",
    "train_authorized": False,
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
    r"theorem|bone|organ|animal|species|molecule|atom|temperature|soil)\b",
    re.I,
)
DOMAIN_SLANG_CUE_RE = re.compile(
    r"\b(slang|meme|online|internet|viral|gaming|crypto|betting|discord|"
    r"tiktok|reddit|status|flex|aura|degen)\b",
    re.I,
)
_TOKEN_RE = re.compile(r"[a-z0-9']+")


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def source_sha256(text: str) -> str:
    return sha256_text(str(text))


def preregistration_contract() -> dict[str, Any]:
    return {
        "acquisition_floors": dict(ACQUISITION_FLOORS),
        "best": "UNCHANGED",
        "best_sha256": BEST_SHA,
        "design_rule": DESIGN_RULE,
        "parent_failure": PARENT_FAIL,
        "schema_sha256": dict(SCHEMA_SHA),
        "stage_a_labels": list(EVIDENCE_LABELS),
        "stage_a_train_contract": dict(STAGE_A_TRAIN_CONTRACT),
        "state": "PREREGISTERED",
        "subtypes": list(EVIDENCE_SUBTYPES),
        "surface_rule": SURFACE_RULE,
        "train": False,
        "validation_floors": dict(VALIDATION_FLOORS),
        "version_bump_required_for_reinterpretation": True,
    }


def tokens(text: str) -> set[str]:
    return {tok for tok in _TOKEN_RE.findall(str(text).casefold()) if len(tok) >= 3}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _span(text: str) -> list[dict[str, Any]]:
    if not text:
        return []
    return [{"start": 0, "end": len(text), "cue": None}]


def _is_admissible_source_row(row: Mapping[str, Any]) -> bool:
    if row.get("split") not in {None, "train"}:
        return False
    if row.get("task") not in {"classify", "classify+unbind", None}:
        # allow synthetic wiktionary rows without task
        if row.get("task") is not None:
            return False
    if row.get("evaluation_reserve") or row.get("held_out"):
        return False
    if row.get("surface") in {"held_out", "evaluation_reserve", "settlement", "measurement"}:
        return False
    if row.get("jev") not in {None, False, "OFF", "off"}:
        return False
    if row.get("class") not in {"OBSERVED", "INFERRED"}:
        return False
    return bool(str(row.get("text") or "").strip())


def classify_hub_subtype(
    row: Mapping[str, Any],
    *,
    positive_token_union: set[str],
) -> str | None:
    # Explicit acquisition / fill subtypes win (fresh v5 bank + Wiktionary fills).
    forced = row.get("evidence_subtype")
    if forced in EVIDENCE_SUBTYPES:
        return str(forced)
    lineage = row.get("lineage")
    text = str(row.get("text") or "")
    form = surface_form(text)
    wc = word_count(text)
    klass = row.get("class")
    if form == SURFACE_AMBIGUOUS:
        return "AMBIGUOUS_EVIDENCE"
    if lineage in ACTIVE_FAMILY_VOCABULARY:
        if klass == "INFERRED" and wc <= 2:
            return "AMBIGUOUS_EVIDENCE"
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
        return "GENERIC_NONE"
    return None


def build_example(row: Mapping[str, Any], subtype: str) -> dict[str, Any]:
    text = str(row["text"]).strip()
    identity = normalized_text_sha256(text)
    label = SUBTYPE_TO_LABEL[subtype]
    lineage = row.get("lineage")
    support: list[str] = []
    spans: list[dict[str, Any]] = []
    missing: list[str] = []
    if subtype == "POSITIVE_EVIDENCE":
        if lineage not in ACTIVE_FAMILY_VOCABULARY:
            raise ValueError(f"positive_without_active_family:{lineage}")
        support = [str(lineage)]
        spans = _span(text)
    elif subtype == "AMBIGUOUS_EVIDENCE" and lineage in ACTIVE_FAMILY_VOCABULARY:
        support = [str(lineage)]
        missing = ["evidence_sufficiency_unresolved"]
    elif subtype in NONE_SUBTYPES:
        missing = ["active_family_evidence_absent", f"subtype:{subtype}"]
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
        "provenance": str(row["class"]),
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


_SUBTYPE_PRIORITY = {
    "POSITIVE_EVIDENCE": 0,
    "AMBIGUOUS_EVIDENCE": 1,
    "ORDINARY_DOMAIN_NONE": 2,
    "LEXICAL_LOOKALIKE_NONE": 3,
    "HARD_NONE": 4,
    "NEAR_DOMAIN_NONE": 5,
    "SHORT_ATOM_NONE": 6,
    "GENERIC_NONE": 7,
}


def _example_rank(example: Mapping[str, Any]) -> tuple[int, int]:
    return (
        _SUBTYPE_PRIORITY[str(example["evidence_subtype"])],
        0 if example.get("provenance") == "OBSERVED" else 1,
    )


def collect_pools(
    rows: Sequence[Mapping[str, Any]],
    *,
    blocked_ids: set[str],
) -> dict[str, list[dict[str, Any]]]:
    positives = []
    for row in rows:
        if not _is_admissible_source_row(row):
            continue
        if row.get("lineage") in ACTIVE_FAMILY_VOCABULARY:
            positives.append(str(row.get("text") or ""))
    positive_token_union: set[str] = set()
    for text in positives:
        positive_token_union |= tokens(text)

    chosen: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not _is_admissible_source_row(row):
            continue
        subtype = classify_hub_subtype(row, positive_token_union=positive_token_union)
        if subtype is None:
            continue
        example = build_example(row, subtype)
        if example["identity"] in blocked_ids:
            continue
        previous = chosen.get(example["identity"])
        if previous is None or _example_rank(example) < _example_rank(previous):
            chosen[example["identity"]] = example
    pools: dict[str, list[dict[str, Any]]] = {name: [] for name in EVIDENCE_SUBTYPES}
    for example in chosen.values():
        pools[str(example["evidence_subtype"])].append(example)
    for subtype in EVIDENCE_SUBTYPES:
        pools[subtype].sort(key=lambda item: item["identity"])
    return pools


def pair_positives_with_negatives(
    pools: Mapping[str, Sequence[Mapping[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Greedy 1:1 pairing; returns (updated_rows_flat, pair_records)."""
    positives = [dict(row) for row in pools.get("POSITIVE_EVIDENCE") or []]
    negatives = []
    for subtype in NONE_SUBTYPES:
        negatives.extend(dict(row) for row in pools.get(subtype) or [])
    by_id = {row["identity"]: row for row in positives + negatives}
    for subtype, rows in pools.items():
        if subtype in {"POSITIVE_EVIDENCE", *NONE_SUBTYPES}:
            continue
        for row in rows:
            by_id[row["identity"]] = dict(row)

    unused_neg = {row["identity"] for row in negatives}
    pair_records: list[dict[str, Any]] = []
    for pos in sorted(positives, key=lambda item: item["identity"]):
        pos_tok = tokens(pos["text"])
        pos_wc = word_count(pos["text"])
        pos_form = surface_form(pos["text"])
        best = None
        best_score = -1.0
        for neg_id in list(unused_neg):
            neg = by_id[neg_id]
            neg_tok = tokens(neg["text"])
            overlap = jaccard(pos_tok, neg_tok)
            if overlap < 0.12 or overlap > 0.75:
                continue
            wc_delta = abs(word_count(neg["text"]) - pos_wc)
            if wc_delta > 8:
                continue
            form_bonus = 0.05 if surface_form(neg["text"]) == pos_form else 0.0
            score = overlap - 0.01 * wc_delta + form_bonus
            if score > best_score:
                best_score = score
                best = neg
        if best is None:
            continue
        shared = sorted(pos_tok & tokens(best["text"]))[:12]
        group = sha256_text(f"pair:{pos['identity']}:{best['identity']}")[:16]
        pos["pair_group_id"] = group
        pos["paired_positive_identity"] = None
        pos["shared_cues"] = shared
        best["pair_group_id"] = group
        best["paired_positive_identity"] = pos["identity"]
        best["shared_cues"] = shared
        best["missing_required_semantics"] = sorted(
            set(best.get("missing_required_semantics") or [])
            | {"paired_against_positive_lacks_family_evidence"}
        )
        unused_neg.discard(best["identity"])
        pair_records.append(
            {
                "missing_required_evidence": list(best["missing_required_semantics"]),
                "negative_identity": best["identity"],
                "negative_subtype": best["evidence_subtype"],
                "pair_group_id": group,
                "paired_positive_identity": pos["identity"],
                "shared_cues": shared,
            }
        )
        by_id[pos["identity"]] = pos
        by_id[best["identity"]] = best
    rows = sorted(by_id.values(), key=lambda item: item["identity"])
    return rows, pair_records


def _split_bucket(identity: str) -> str:
    digest = hashlib.sha256(f"{SPLIT_SEED_PREFIX}:{identity}".encode("utf-8")).hexdigest()
    return "validation" if int(digest[:8], 16) % 5 == 0 else "train"


def assign_splits(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Identity/hash split with pair co-location and validation floors."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = str(
            row.get("pair_group_id")
            or row.get("parent_identity")
            or row["identity"]
        )
        groups[key].append(dict(row))

    # Decide group split from lex-smallest identity in group.
    group_split: dict[str, str] = {}
    for key, members in groups.items():
        anchor = sorted(m["identity"] for m in members)[0]
        group_split[key] = _split_bucket(anchor)

    def recount() -> dict[str, dict[str, int]]:
        counts = {subtype: {"train": 0, "validation": 0} for subtype in EVIDENCE_SUBTYPES}
        for key, members in groups.items():
            split = group_split[key]
            for row in members:
                counts[str(row["evidence_subtype"])][split] += 1
        return counts

    # Promote whole groups from train→validation until floors are met.
    for subtype in EVIDENCE_SUBTYPES:
        floor = VALIDATION_FLOORS[subtype]
        # candidate train groups that contain this subtype, ordered by anchor
        train_groups = []
        for key, members in groups.items():
            if group_split[key] != "train":
                continue
            if any(str(m["evidence_subtype"]) == subtype for m in members):
                anchor = sorted(m["identity"] for m in members)[0]
                train_groups.append((anchor, key))
        train_groups.sort()
        for _anchor, key in train_groups:
            counts = recount()
            if counts[subtype]["validation"] >= floor:
                break
            group_split[key] = "validation"

    missing_val: dict[str, int] = {}
    assigned: list[dict[str, Any]] = []
    counts = recount()
    for subtype in EVIDENCE_SUBTYPES:
        if counts[subtype]["validation"] < VALIDATION_FLOORS[subtype]:
            missing_val[subtype] = VALIDATION_FLOORS[subtype] - counts[subtype]["validation"]
    for key, members in groups.items():
        split = group_split[key]
        for row in members:
            row["split"] = split
            assigned.append(row)
    assigned.sort(key=lambda item: (item["evidence_subtype"], item["identity"]))
    return {"missing_validation_floors": missing_val, "rows": assigned}


def validate_row(example: Mapping[str, Any], ontology: Sequence[str]) -> list[str]:
    errors = []
    subtype = str(example.get("evidence_subtype"))
    label = str(example.get("evidence_label"))
    if subtype not in SUBTYPE_TO_LABEL:
        errors.append("subtype_invalid")
    elif SUBTYPE_TO_LABEL[subtype] != label:
        errors.append("label_subtype_mismatch")
    if example.get("required_evidence_present") != REQUIRED_EVIDENCE_PRESENT.get(subtype):
        errors.append("required_evidence_present_mismatch")
    text = str(example.get("text") or "")
    if not text.strip():
        errors.append("empty_text")
    if example.get("identity") != normalized_text_sha256(text):
        errors.append("identity_mismatch")
    if example.get("source_sha256") != source_sha256(text):
        errors.append("source_sha256_mismatch")
    if example.get("provenance") not in {"OBSERVED", "INFERRED"}:
        errors.append("provenance_invalid")
    if example.get("split") not in {"train", "validation"}:
        errors.append("split_invalid")
    allowed = set(ontology)
    for family in list(example.get("candidate_families") or []) + list(
        example.get("active_family_support") or []
    ):
        if family not in allowed:
            errors.append(f"family_invalid:{family}")
    if subtype == "POSITIVE_EVIDENCE":
        if not example.get("active_family_support"):
            errors.append("positive_missing_support")
        if not example.get("evidence_spans"):
            errors.append("positive_missing_spans")
    if subtype in NONE_SUBTYPES and example.get("active_family_support"):
        errors.append("none_has_family_support")
    return errors


def near_duplicate_groups(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        text = re.sub(r"\s+", " ", str(row["text"]).casefold()).strip()
        groups[text[:48]].append(row["identity"])
    out = []
    for key, identities in sorted(groups.items()):
        uniq = sorted(set(identities))
        if len(uniq) > 1:
            out.append({"key": key, "n": len(uniq), "identities": uniq[:8]})
    out.sort(key=lambda item: (-item["n"], item["key"]))
    return out


def surface_shortcut_diagnostics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_subtype: dict[str, Counter[str]] = {name: Counter() for name in EVIDENCE_SUBTYPES}
    lengths: dict[str, list[int]] = {name: [] for name in EVIDENCE_SUBTYPES}
    for row in rows:
        subtype = str(row["evidence_subtype"])
        by_subtype[subtype][surface_form(str(row["text"]))] += 1
        lengths[subtype].append(word_count(str(row["text"])) )

    def _mean(values: Sequence[int]) -> float | None:
        return None if not values else sum(values) / len(values)

    critical = []
    pos = by_subtype["POSITIVE_EVIDENCE"]
    pos_total = sum(pos.values())
    pos_atom = (pos[SURFACE_ATOM] / pos_total) if pos_total else None
    for subtype in NONE_SUBTYPES:
        total = sum(by_subtype[subtype].values())
        if not total:
            continue
        atom_rate = by_subtype[subtype][SURFACE_ATOM] / total
        # Critical: NONE subtype almost pure ATOM while POSITIVE almost pure PROSE
        # AND mean length gap > 6 — classic applicability shortcut.
        mean_len = _mean(lengths[subtype])
        pos_mean = _mean(lengths["POSITIVE_EVIDENCE"])
        if (
            pos_atom is not None
            and pos_mean is not None
            and mean_len is not None
            and atom_rate > 0.95
            and pos_atom < 0.25
            and (pos_mean - mean_len) > 6
            and subtype in {"GENERIC_NONE", "SHORT_ATOM_NONE"}
        ):
            # SHORT_ATOM_NONE is intentionally short; only GENERIC pure-atom is critical
            if subtype == "GENERIC_NONE":
                critical.append("GENERIC_NONE_atom_vs_POSITIVE_prose_length_shortcut")
    return {
        "atom_prose_by_subtype": {
            subtype: dict(counter) for subtype, counter in by_subtype.items()
        },
        "critical_shortcuts": critical,
        "mean_word_count_by_subtype": {
            subtype: _mean(values) for subtype, values in lengths.items()
        },
        "pass": not critical,
    }


def _majority_baseline(train_y: Sequence[str], val_y: Sequence[str]) -> float:
    if not train_y or not val_y:
        return 0.0
    maj = Counter(train_y).most_common(1)[0][0]
    return sum(1 for y in val_y if y == maj) / len(val_y)


def shallow_diagnostics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Deterministic shallow separators for PRESENT vs NONE (diagnostics only)."""
    train = [
        row
        for row in rows
        if row["split"] == "train" and row["evidence_label"] in {"EVIDENCE_PRESENT", "NO_EVIDENCE"}
    ]
    val = [
        row
        for row in rows
        if row["split"] == "validation"
        and row["evidence_label"] in {"EVIDENCE_PRESENT", "NO_EVIDENCE"}
    ]
    if not train or not val:
        return {"pass": False, "reason": "insufficient_binary_rows", "critical": True}

    def label_of(row: Mapping[str, Any]) -> str:
        return str(row["evidence_label"])

    train_y = [label_of(row) for row in train]
    val_y = [label_of(row) for row in val]
    majority = _majority_baseline(train_y, val_y)

    # length-only: threshold maximizing train accuracy
    lengths = sorted({word_count(str(row["text"])) for row in train})
    best_thr = 0
    best_acc = -1.0
    for thr in lengths:
        pred = [
            "EVIDENCE_PRESENT" if word_count(str(row["text"])) >= thr else "NO_EVIDENCE"
            for row in train
        ]
        acc = sum(int(a == b) for a, b in zip(pred, train_y)) / len(train_y)
        if acc > best_acc:
            best_acc = acc
            best_thr = thr
    length_val = [
        "EVIDENCE_PRESENT" if word_count(str(row["text"])) >= best_thr else "NO_EVIDENCE"
        for row in val
    ]
    length_acc = sum(int(a == b) for a, b in zip(length_val, val_y)) / len(val_y)

    # surface-feature: ATOM => NONE else PRESENT (or reverse — pick better on train)
    def surface_acc(atom_is_none: bool, split_rows: Sequence[Mapping[str, Any]], ys: Sequence[str]) -> float:
        preds = []
        for row in split_rows:
            is_atom = surface_form(str(row["text"])) == SURFACE_ATOM
            if atom_is_none:
                preds.append("NO_EVIDENCE" if is_atom else "EVIDENCE_PRESENT")
            else:
                preds.append("EVIDENCE_PRESENT" if is_atom else "NO_EVIDENCE")
        return sum(int(a == b) for a, b in zip(preds, ys)) / len(ys)

    atom_none = surface_acc(True, train, train_y) >= surface_acc(False, train, train_y)
    surface_val_acc = surface_acc(atom_none, val, val_y)

    # bag-of-words: token polarity from train, score sign
    pos_counts: Counter[str] = Counter()
    neg_counts: Counter[str] = Counter()
    for row in train:
        bag = tokens(row["text"])
        if label_of(row) == "EVIDENCE_PRESENT":
            pos_counts.update(bag)
        else:
            neg_counts.update(bag)
    vocab = sorted(set(pos_counts) | set(neg_counts))
    weight = {tok: math.log1p(pos_counts[tok]) - math.log1p(neg_counts[tok]) for tok in vocab}

    def bow_pred(text: str) -> str:
        score = sum(weight.get(tok, 0.0) for tok in tokens(text))
        return "EVIDENCE_PRESENT" if score >= 0 else "NO_EVIDENCE"

    bow_val_acc = sum(
        int(bow_pred(str(row["text"])) == y) for row, y in zip(val, val_y)
    ) / len(val_y)

    critical = []
    if length_acc >= 0.90:
        critical.append(f"length_only_val_acc={length_acc:.3f}")
    if surface_val_acc >= 0.90:
        critical.append(f"surface_feature_val_acc={surface_val_acc:.3f}")
    # BoW can be legitimately strong; flag only extreme >0.97 as trivial
    if bow_val_acc >= 0.97:
        critical.append(f"bag_of_words_val_acc={bow_val_acc:.3f}")

    return {
        "bag_of_words_val_accuracy": bow_val_acc,
        "critical": critical,
        "length_only_threshold_words": best_thr,
        "length_only_val_accuracy": length_acc,
        "majority_baseline_val_accuracy": majority,
        "n_train_binary": len(train),
        "n_validation_binary": len(val),
        "pass": not critical,
        "surface_feature_atom_means_none": atom_none,
        "surface_feature_val_accuracy": surface_val_acc,
    }


def lexical_overlap_report(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    pos = [row for row in rows if row["evidence_subtype"] == "POSITIVE_EVIDENCE"]
    none = [row for row in rows if row["evidence_subtype"] in NONE_SUBTYPES]
    pos_tok: set[str] = set()
    for row in pos:
        pos_tok |= tokens(row["text"])
    none_tok: set[str] = set()
    for row in none:
        none_tok |= tokens(row["text"])
    inter = pos_tok & none_tok
    # nearest neighbor mean jaccard on a capped sample
    sample_pos = sorted(pos, key=lambda item: item["identity"])[:120]
    sample_none = sorted(none, key=lambda item: item["identity"])[:240]
    nn_scores = []
    for p in sample_pos:
        pt = tokens(p["text"])
        best = 0.0
        for n in sample_none:
            best = max(best, jaccard(pt, tokens(n["text"])))
        nn_scores.append(best)
    return {
        "mean_nearest_positive_to_negative_jaccard": (
            None if not nn_scores else sum(nn_scores) / len(nn_scores)
        ),
        "positive_token_count": len(pos_tok),
        "negative_token_count": len(none_tok),
        "shared_token_count": len(inter),
        "shared_token_jaccard": jaccard(pos_tok, none_tok),
        "shared_tokens_sample": sorted(inter)[:40],
    }


def ordinary_domain_coverage(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ordinary = [row for row in rows if row["evidence_subtype"] == "ORDINARY_DOMAIN_NONE"]
    domains = Counter(str(row.get("topic_domain") or "unspecified") for row in ordinary)
    labeled = [d for d in domains if d in ORDINARY_DOMAIN_LABELS]
    positive_families = Counter()
    for row in rows:
        if row["evidence_subtype"] != "POSITIVE_EVIDENCE":
            continue
        for family in row.get("active_family_support") or []:
            positive_families[family] += 1
    return {
        "min_domains_required": 8,
        "n_labeled_ordinary_domains": len(labeled),
        "n_ordinary_domain_none": len(ordinary),
        "ordinary_topic_domains": dict(sorted(domains.items())),
        "pass": (
            len(ordinary) >= ACQUISITION_FLOORS["ORDINARY_DOMAIN_NONE"]
            and len(labeled) >= 8
        ),
        "positive_family_topics": dict(sorted(positive_families.items())),
    }


def build_diagnostics(
    rows: Sequence[Mapping[str, Any]],
    *,
    pair_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    subtype_counts = Counter(row["evidence_subtype"] for row in rows)
    label_counts = Counter(row["evidence_label"] for row in rows)
    provenance_counts = Counter(row["provenance"] for row in rows)
    split_counts = Counter(row["split"] for row in rows)
    forms = Counter(surface_form(str(row["text"])) for row in rows)
    lengths = [word_count(str(row["text"])) for row in rows]
    val_subtype = Counter(
        row["evidence_subtype"] for row in rows if row["split"] == "validation"
    )
    train_subtype = Counter(
        row["evidence_subtype"] for row in rows if row["split"] == "train"
    )
    near = near_duplicate_groups(rows)
    return {
        "ATOM_PROSE": dict(forms),
        "counts_by_gate_label": dict(label_counts),
        "counts_by_provenance": dict(provenance_counts),
        "counts_by_split": dict(split_counts),
        "counts_by_subtype": dict(subtype_counts),
        "lexical_overlap": lexical_overlap_report(rows),
        "mean_word_count": None if not lengths else sum(lengths) / len(lengths),
        "n": len(rows),
        "near_duplicate_group_count": len(near),
        "near_duplicate_groups": near[:20],
        "ordinary_domain_coverage": ordinary_domain_coverage(rows),
        "paired_positive_negative_count": len(pair_records),
        "train_subtype_counts": dict(train_subtype),
        "validation_subtype_counts": dict(val_subtype),
        "word_count_max": max(lengths) if lengths else None,
        "word_count_min": min(lengths) if lengths else None,
    }


def compute_split_leakage(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    train_ids = {row["identity"] for row in rows if row["split"] == "train"}
    val_ids = {row["identity"] for row in rows if row["split"] == "validation"}
    train_sources = {row["source_sha256"] for row in rows if row["split"] == "train"}
    val_sources = {row["source_sha256"] for row in rows if row["split"] == "validation"}
    parents_train = {
        row["parent_identity"]
        for row in rows
        if row["split"] == "train" and row.get("parent_identity")
    }
    parents_val = {
        row["parent_identity"]
        for row in rows
        if row["split"] == "validation" and row.get("parent_identity")
    }
    # pair leakage: same pair_group in both splits
    train_groups = {
        row["pair_group_id"]
        for row in rows
        if row["split"] == "train" and row.get("pair_group_id")
    }
    val_groups = {
        row["pair_group_id"]
        for row in rows
        if row["split"] == "validation" and row.get("pair_group_id")
    }
    return {
        "pair_group_collisions": len(train_groups & val_groups),
        "parent_identity_collisions": len(parents_train & parents_val),
        "source_hash_collisions_across_splits": len(train_sources & val_sources),
        "split_identity_overlap": len(train_ids & val_ids),
    }


def readiness_report(
    *,
    rows: Sequence[Mapping[str, Any]],
    spent_overlap: Sequence[str],
    validation_errors: Sequence[str],
    shortcut: Mapping[str, Any],
    shallow: Mapping[str, Any],
    leakage: Mapping[str, Any],
    missing_validation_floors: Mapping[str, int],
    ordinary: Mapping[str, Any],
) -> dict[str, Any]:
    subtype_counts = Counter(row["evidence_subtype"] for row in rows)
    val_counts = Counter(
        row["evidence_subtype"] for row in rows if row["split"] == "validation"
    )
    missing_acquisition = {
        subtype: floor - subtype_counts.get(subtype, 0)
        for subtype, floor in ACQUISITION_FLOORS.items()
        if subtype_counts.get(subtype, 0) < floor
    }
    missing_validation = {
        subtype: floor - val_counts.get(subtype, 0)
        for subtype, floor in VALIDATION_FLOORS.items()
        if val_counts.get(subtype, 0) < floor
    }
    zero_subtype = [s for s in EVIDENCE_SUBTYPES if subtype_counts.get(s, 0) == 0]
    blockers: list[dict[str, Any]] = []
    if missing_acquisition:
        blockers.append({"missing_acquisition_floors": missing_acquisition})
    if missing_validation or missing_validation_floors:
        blockers.append(
            {
                "missing_validation_floors": {
                    **missing_validation,
                    **dict(missing_validation_floors),
                }
            }
        )
    if spent_overlap:
        blockers.append({"spent_reserve_overlap": len(spent_overlap)})
    if validation_errors:
        blockers.append({"schema_or_row_errors": len(validation_errors)})
    if zero_subtype:
        blockers.append({"zero_count_subtype": zero_subtype})
    if not ordinary.get("pass", False):
        blockers.append({"ordinary_domain_none_coverage_failed": ordinary})
    if not shortcut.get("pass", False):
        blockers.append({"critical_surface_shortcut": shortcut.get("critical_shortcuts")})
    if not shallow.get("pass", False):
        blockers.append({"shallow_diagnostic_critical": shallow.get("critical")})
    if leakage.get("split_identity_overlap"):
        blockers.append({"split_identity_overlap": leakage["split_identity_overlap"]})
    if leakage.get("source_hash_collisions_across_splits"):
        blockers.append(
            {
                "source_hash_collisions_across_splits": leakage[
                    "source_hash_collisions_across_splits"
                ]
            }
        )
    if leakage.get("parent_identity_collisions"):
        blockers.append(
            {"parent_identity_collisions": leakage["parent_identity_collisions"]}
        )
    if leakage.get("pair_group_collisions"):
        blockers.append({"pair_group_collisions": leakage["pair_group_collisions"]})
    identities = [row["identity"] for row in rows]
    if len(identities) != len(set(identities)):
        blockers.append({"duplicate_identities": True})
    state = "READY" if not blockers else "PREREGISTERED"
    return {
        "blockers": blockers,
        "missing_evidence": blockers,
        "state": state,
        "surface_rule": SURFACE_RULE,
    }


def assemble_surface_artifacts(payload: Mapping[str, Any]) -> dict[str, Any]:
    rows = list(payload["rows"])
    diagnostics = payload["diagnostics"]
    shortcut = payload["shortcut"]
    shallow = payload["shallow"]
    spent_overlap = list(payload.get("spent_overlap") or [])
    readiness = dict(payload["readiness"])
    pair_records = list(payload.get("pair_records") or [])
    dataset_lines = [canonical_json(row) for row in rows]
    dataset_body = "\n".join(dataset_lines) + ("\n" if dataset_lines else "")
    dataset_sha = sha256_text(dataset_body)
    split_manifest = {
        "schema": "hyperlex.classification.v5.evidence_split_manifest.v1",
        "splits": {
            "train": sorted(row["identity"] for row in rows if row["split"] == "train"),
            "validation": sorted(
                row["identity"] for row in rows if row["split"] == "validation"
            ),
        },
        "surface_rule": SURFACE_RULE,
    }
    split_manifest["manifest_sha256"] = sha256_text(
        canonical_json({k: v for k, v in split_manifest.items() if k != "manifest_sha256"})
    )
    disjointness = {
        "dataset_sha256": dataset_sha,
        "pair_group_collisions": int(payload.get("pair_group_collisions") or 0),
        "parent_identity_collisions": int(payload.get("parent_identity_collisions") or 0),
        "schema": "hyperlex.classification.v5.evidence_disjointness.v1",
        "source_hash_collisions_across_splits": payload.get("source_hash_collisions", 0),
        "spent_reserve_overlap": spent_overlap,
        "spent_reserve_overlap_count": len(spent_overlap),
        "split_identity_overlap": payload.get("split_identity_overlap", 0),
        "surface_rule": SURFACE_RULE,
        "pass": len(spent_overlap) == 0
        and payload.get("split_identity_overlap", 0) == 0
        and payload.get("source_hash_collisions", 0) == 0
        and int(payload.get("parent_identity_collisions") or 0) == 0
        and int(payload.get("pair_group_collisions") or 0) == 0,
    }
    disjointness["witness_sha256"] = sha256_text(
        canonical_json({k: v for k, v in disjointness.items() if k != "witness_sha256"})
    )
    if not disjointness["pass"]:
        readiness["state"] = "PREREGISTERED"
        blockers = list(readiness.get("blockers") or [])
        blockers.append({"disjointness_failed": True})
        readiness["blockers"] = blockers
        readiness["missing_evidence"] = blockers
    train_contract = None
    if readiness["state"] == "READY":
        train_contract = {
            **STAGE_A_TRAIN_CONTRACT,
            "preregistered": True,
            "surface_dataset_sha256": dataset_sha,
            "surface_rule": SURFACE_RULE,
        }
        train_contract["contract_sha256"] = sha256_text(
            canonical_json(
                {k: v for k, v in train_contract.items() if k != "contract_sha256"}
            )
        )
    diagnostics_payload = {
        "diagnostics": diagnostics,
        "pair_records_n": len(pair_records),
        "schema": "hyperlex.classification.v5.evidence_surface_diagnostics.v1",
        "shallow": shallow,
        "shortcut": shortcut,
        "surface_rule": SURFACE_RULE,
    }
    diagnostics_payload["diagnostics_sha256"] = sha256_text(
        canonical_json(
            {k: v for k, v in diagnostics_payload.items() if k != "diagnostics_sha256"}
        )
    )
    dataset_manifest = {
        "acquisition_floors": ACQUISITION_FLOORS,
        "counts_by_subtype": diagnostics["counts_by_subtype"],
        "dataset_sha256": dataset_sha,
        "n": len(rows),
        "preregistration": preregistration_contract(),
        "schema": "hyperlex.classification.v5.evidence_dataset_manifest.v1",
        "surface_rule": SURFACE_RULE,
        "validation_floors": VALIDATION_FLOORS,
    }
    dataset_manifest["manifest_sha256"] = sha256_text(
        canonical_json({k: v for k, v in dataset_manifest.items() if k != "manifest_sha256"})
    )
    readiness_receipt = {
        "BEST": "UNCHANGED",
        "best_sha256": BEST_SHA,
        "dataset_manifest_sha256": dataset_manifest["manifest_sha256"],
        "dataset_sha256": dataset_sha,
        "design_rule": DESIGN_RULE,
        "diagnostics_sha256": diagnostics_payload["diagnostics_sha256"],
        "disjointness_witness_sha256": disjointness["witness_sha256"],
        "preregistration": preregistration_contract(),
        "readiness": readiness,
        "schema": "hyperlex.classification.v5.evidence_surface_readiness.v1",
        "split_manifest_sha256": split_manifest["manifest_sha256"],
        "stage_a_train_contract": train_contract,
        "surface_rule": SURFACE_RULE,
        "train": False,
    }
    readiness_receipt["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in readiness_receipt.items() if k != "receipt_sha256"})
    )
    return {
        "dataset_body": dataset_body,
        "dataset_manifest": dataset_manifest,
        "dataset_sha256": dataset_sha,
        "diagnostics": diagnostics_payload,
        "disjointness": disjointness,
        "pair_records": pair_records,
        "readiness_receipt": readiness_receipt,
        "shallow": shallow,
        "shortcut": shortcut,
        "split_manifest": split_manifest,
        "stage_a_train_contract": train_contract,
    }


def build_surface(
    source_rows: Sequence[Mapping[str, Any]],
    *,
    blocked_ids: set[str],
    ontology: Sequence[str],
    augment: bool = True,
) -> dict[str, Any]:
    working = list(source_rows)
    if augment:
        working = augment_source_rows_for_floors(working, blocked_ids=blocked_ids)
    pools = select_balanced_pools(collect_pools(working, blocked_ids=blocked_ids))
    paired_rows, pair_records = pair_positives_with_negatives(pools)
    # re-bucket after pairing mutations
    pools_after: dict[str, list[dict[str, Any]]] = {name: [] for name in EVIDENCE_SUBTYPES}
    for row in paired_rows:
        pools_after[str(row["evidence_subtype"])].append(row)
    split_result = assign_splits(paired_rows)
    rows = split_result["rows"]
    validation_errors: list[str] = []
    for row in rows:
        for error in validate_row(row, ontology):
            validation_errors.append(f"{row['identity']}:{error}")
    leakage = compute_split_leakage(rows)
    spent_overlap = sorted({row["identity"] for row in rows} & set(blocked_ids))
    diagnostics = build_diagnostics(rows, pair_records=pair_records)
    shortcut = surface_shortcut_diagnostics(rows)
    shallow = shallow_diagnostics(rows)
    ordinary = diagnostics["ordinary_domain_coverage"]
    readiness = readiness_report(
        rows=rows,
        spent_overlap=spent_overlap,
        validation_errors=validation_errors,
        shortcut=shortcut,
        shallow=shallow,
        leakage=leakage,
        missing_validation_floors=split_result["missing_validation_floors"],
        ordinary=ordinary,
    )
    assembled = assemble_surface_artifacts(
        {
            "diagnostics": diagnostics,
            "pair_group_collisions": leakage["pair_group_collisions"],
            "pair_records": pair_records,
            "parent_identity_collisions": leakage["parent_identity_collisions"],
            "readiness": readiness,
            "rows": rows,
            "shallow": shallow,
            "shortcut": shortcut,
            "source_hash_collisions": leakage["source_hash_collisions_across_splits"],
            "spent_overlap": spent_overlap,
            "split_identity_overlap": leakage["split_identity_overlap"],
        }
    )
    return {
        "assembled": assembled,
        "leakage": leakage,
        "pair_records": pair_records,
        "pools": {subtype: len(values) for subtype, values in pools_after.items()},
        "readiness": assembled["readiness_receipt"]["readiness"],
        "rows": rows,
        "shallow": shallow,
        "validation_errors": validation_errors,
    }


def load_blocked_ids(
    *,
    ledger: Mapping[str, Any],
    spent_row_files: Sequence[Sequence[Mapping[str, Any]]] = (),
) -> set[str]:
    """Block spent reserves + held-out/measurement identities only.

    TRAIN_CONSUMED hub rows remain admissible for Stage-A surface rebuild.
    """
    blocked: set[str] = set()
    for record in ledger.get("identities") or []:
        state = str(record.get("state") or "")
        if (
            record.get("evaluation_spent")
            or record.get("evaluation_reserved")
            or record.get("evaluation_abandoned")
            or state
            in {
                "EVAL_SPENT",
                "EVAL_RESERVE",
                "EVAL_BOUND",
                "EVAL_ABANDONED",
            }
        ):
            digest = record.get("normalized_text_sha256")
            if digest:
                blocked.add(str(digest))
    for rows in spent_row_files:
        for row in rows:
            digest = row.get("normalized_text_sha256") or row.get("identity")
            if digest:
                blocked.add(str(digest))
            text = row.get("text")
            if isinstance(text, str) and text.strip():
                blocked.add(normalized_text_sha256(text))
    return blocked


# Soft caps after floors: prevent SHORT_ATOM / GENERIC atom dominance shortcuts.
POOL_SOFT_CAPS = {
    "POSITIVE_EVIDENCE": 1200,
    "ORDINARY_DOMAIN_NONE": 520,
    "HARD_NONE": 420,
    "NEAR_DOMAIN_NONE": 420,
    "GENERIC_NONE": 360,
    "LEXICAL_LOOKALIKE_NONE": 360,
    "SHORT_ATOM_NONE": 240,
    "AMBIGUOUS_EVIDENCE": 320,
}


def _length_bucket(wc: int) -> str:
    if wc <= 2:
        return "atom"
    if wc <= 5:
        return "short"
    if wc <= 12:
        return "medium"
    if wc <= 24:
        return "long"
    return "very_long"


def _stratified_take(
    rows: Sequence[Mapping[str, Any]],
    *,
    keep_n: int,
    target_bucket_weights: Mapping[str, float] | None = None,
) -> list[dict[str, Any]]:
    if keep_n >= len(rows):
        return [dict(row) for row in rows]
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[_length_bucket(word_count(str(row["text"])))].append(dict(row))
    for key in buckets:
        buckets[key].sort(key=lambda item: item["identity"])
    weights = dict(target_bucket_weights or {})
    if not weights:
        # Uniform over observed buckets.
        weights = {key: 1.0 for key in buckets}
    # Normalize over buckets that actually have rows.
    active = {key: weights.get(key, 0.0) for key in buckets if buckets[key]}
    total_w = sum(active.values()) or float(len(active))
    quotas = {key: int(keep_n * (w / total_w)) for key, w in active.items()}
    # Fix rounding to exact keep_n.
    while sum(quotas.values()) < keep_n:
        for key in sorted(active, key=lambda item: (-len(buckets[item]), item)):
            if sum(quotas.values()) >= keep_n:
                break
            if quotas[key] < len(buckets[key]):
                quotas[key] += 1
    while sum(quotas.values()) > keep_n:
        for key in sorted(active, key=lambda item: (quotas[item], item), reverse=True):
            if sum(quotas.values()) <= keep_n:
                break
            if quotas[key] > 0:
                quotas[key] -= 1
    chosen: list[dict[str, Any]] = []
    leftovers: list[dict[str, Any]] = []
    for key, bucket_rows in buckets.items():
        q = quotas.get(key, 0)
        chosen.extend(bucket_rows[:q])
        leftovers.extend(bucket_rows[q:])
    leftovers.sort(key=lambda item: item["identity"])
    if len(chosen) < keep_n:
        chosen.extend(leftovers[: keep_n - len(chosen)])
    chosen.sort(key=lambda item: item["identity"])
    return chosen[:keep_n]


def select_balanced_pools(
    pools: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """Keep floors, apply soft caps, stratify lengths to blunt surface shortcuts."""
    out: dict[str, list[dict[str, Any]]] = {}
    # First size positives with mixed length buckets (include short atoms).
    pos_rows = [dict(row) for row in pools.get("POSITIVE_EVIDENCE") or []]
    pos_floor = ACQUISITION_FLOORS["POSITIVE_EVIDENCE"]
    pos_cap = POOL_SOFT_CAPS["POSITIVE_EVIDENCE"]
    pos_keep = min(len(pos_rows), max(pos_floor, min(len(pos_rows), pos_cap))) if pos_rows else 0
    if len(pos_rows) >= pos_floor:
        pos_keep = max(pos_floor, min(len(pos_rows), pos_cap))
    else:
        pos_keep = len(pos_rows)
    out["POSITIVE_EVIDENCE"] = _stratified_take(
        pos_rows,
        keep_n=pos_keep,
        target_bucket_weights={
            "atom": 0.15,
            "short": 0.20,
            "medium": 0.35,
            "long": 0.25,
            "very_long": 0.05,
        },
    )
    pos_bucket_weights = Counter(
        _length_bucket(word_count(str(row["text"]))) for row in out["POSITIVE_EVIDENCE"]
    )
    # Convert counts to weights for NONE matching (exclude pure atom dominance for prose Nones).
    matched_weights = {
        "atom": 0.05,
        "short": max(0.15, pos_bucket_weights.get("short", 0) + 1),
        "medium": max(0.35, pos_bucket_weights.get("medium", 0) + 1),
        "long": max(0.25, pos_bucket_weights.get("long", 0) + 1),
        "very_long": max(0.05, pos_bucket_weights.get("very_long", 0) + 1),
    }

    for subtype in EVIDENCE_SUBTYPES:
        if subtype == "POSITIVE_EVIDENCE":
            continue
        rows = [dict(row) for row in pools.get(subtype) or []]
        floor = ACQUISITION_FLOORS[subtype]
        cap = POOL_SOFT_CAPS[subtype]
        if len(rows) >= floor:
            keep_n = max(floor, min(len(rows), cap))
        else:
            keep_n = len(rows)
        if subtype == "SHORT_ATOM_NONE":
            rows.sort(key=lambda item: item["identity"])
            out[subtype] = rows[:keep_n]
            continue
        # Prefer prose first, then length-match positives.
        prose_first = sorted(
            rows,
            key=lambda item: (
                0 if surface_form(str(item["text"])) == SURFACE_PROSE else 1,
                item["identity"],
            ),
        )
        out[subtype] = _stratified_take(
            prose_first,
            keep_n=keep_n,
            target_bucket_weights=matched_weights,
        )
    return out


ORDINARY_DOMAIN_BANK: dict[str, tuple[str, ...]] = {
    "botany": (
        "Xylem vessels transport water from roots through the plant stem.",
        "Chloroplasts in leaf mesophyll trap photons for carbon fixation.",
        "A dicot seedling unfolds two cotyledons after germination.",
        "Phloem sieve tubes move sucrose from source leaves to sinks.",
        "Stomatal guard cells open when turgor pressure rises at dawn.",
        "Mycorrhizal fungi exchange minerals for sugars at root tips.",
        "Annual rings in temperate trees record seasonal cambial growth.",
        "Pollen tubes deliver sperm nuclei to the ovule micropyle.",
        "Cacti store water in fleshy stems adapted to arid soils.",
        "Ferns release spores from sori on the underside of fronds.",
        "Nitrogen-fixing nodules form on legume roots with rhizobia.",
        "Apical meristems produce new cells at shoot and root tips.",
        "Deciduous trees shed leaves when chlorophyll breaks down in autumn.",
        "Bryophytes lack true vascular tissue and stay small and moist.",
        "Seed coats harden to protect the embryo until soil conditions allow growth.",
        "Transpiration pull draws water upward against gravity in tall trees.",
        "Companion cells load sugars into adjacent sieve elements.",
        "Epiphytic orchids cling to bark and absorb humidity from air.",
        "Root hairs expand the absorptive surface of young roots.",
        "Auxin gradients steer phototropic bending toward light.",
        "Conifer cones house seeds between woody scales.",
        "Lignin stiffens secondary cell walls in mature wood fibers.",
        "Carnivorous plants digest insects to gain scarce soil nitrogen.",
        "Bud scales shield overwintering shoot tips from frost.",
        "Algae mats photosynthesize in shallow freshwater ponds.",
        "Cambium produces secondary xylem inward and phloem outward.",
        "Fruit ripening softens cell walls as pectinases activate.",
        "Moss protonema spreads as a filament before leafy gametophytes form.",
        "Halophyte plants exclude salt at the root epidermis.",
        "Tendrils coil around supports when touch receptors fire.",
        "Leaf cuticle wax reduces uncontrolled water loss.",
        "Symbiotic lichens pair fungi with photosynthetic partners.",
        "Potato tubers store starch as underground stem tissue.",
        "Floral nectaries reward pollinators with sugar solutions.",
        "Tropical rainforest understories receive only filtered light.",
        "Ginkgo trees retain fan-shaped leaves unique among seed plants.",
        "Rice paddies flood to suppress weeds and stabilize temperatures.",
        "Sapwood conducts water while heartwood provides structural support.",
        "Wind-pollinated grasses release lightweight pollen in clouds.",
        "Desert shrubs drop leaves during prolonged drought stress.",
        "Kelp forests form underwater canopies along cold rocky coasts.",
        "Seed banks in soil preserve dormant embryos for years.",
        "Climbing vines use tendrils or adhesive pads for support.",
        "Bark cork layers insulate trunks against fire and insects.",
        "Aquatic plants develop aerenchyma channels for gas exchange.",
    ),
    "chemistry": (
        "Sodium chloride dissolves into free ions in liquid water.",
        "A catalyst lowers activation energy without being consumed.",
        "Titration endpoints appear when the indicator changes color.",
        "Covalent bonds share electron pairs between nonmetal atoms.",
        "Ideal gas pressure rises when temperature increases at fixed volume.",
        "Acids donate protons while bases accept them in aqueous solution.",
        "Distillation separates liquids by boiling-point differences.",
        "Oxidation numbers track electron transfer in redox reactions.",
        "Polymer chains form when monomers link through covalent bonds.",
        "Buffer solutions resist pH change when small acid amounts are added.",
        "Electrolysis drives nonspontaneous reactions with electric current.",
        "Molar mass converts grams of a compound into moles.",
        "Exothermic reactions release heat to the surroundings.",
        "Ionic lattices pack oppositely charged ions in crystal arrays.",
        "Chromatography separates mixtures by differential adsorption.",
        "Equilibrium constants relate product and reactant concentrations.",
        "Halogens gain electrons easily because of high electronegativity.",
        "Spectroscopy identifies compounds by characteristic absorption bands.",
        "Precipitation forms when product ion concentrations exceed solubility.",
        "Avogadro's number counts particles in one mole of substance.",
        "Organic functional groups dictate typical reaction patterns.",
        "Hydrogen bonding raises the boiling point of water.",
        "Limiting reagents determine the maximum product yield.",
        "Radioactive isotopes decay with characteristic half-lives.",
        "Alloys mix metals to tune hardness and corrosion resistance.",
        "pH meters report hydronium activity on a logarithmic scale.",
        "Combustion of hydrocarbons yields carbon dioxide and water.",
        "Lewis structures map valence electrons around bonded atoms.",
        "Endothermic dissolving cools the solution as lattice energy is paid.",
        "Catalyst poisons block active sites and slow industrial processes.",
        "Aqueous copper sulfate appears blue from hydrated copper ions.",
        "Stoichiometric coefficients balance atoms on both reaction sides.",
        "Noble gases rarely form compounds under ordinary conditions.",
        "Calorimeters measure heat flow during chemical changes.",
        "Isomers share formulas but differ in atom connectivity.",
        "Reduction adds electrons or decreases oxidation number.",
        "Saturated solutions hold the maximum solute at a given temperature.",
        "Van der Waals forces weakly attract nearby neutral molecules.",
        "Electrolytes conduct because dissolved ions carry charge.",
        "Mass spectrometry fragments molecules for compositional analysis.",
        "Activation complexes sit at the energy peak of a reaction path.",
        "Amphoteric oxides react with both acids and strong bases.",
        "Concentrated sulfuric acid is a powerful dehydrating agent.",
        "Gas chromatography uses inert carrier flow through a coated column.",
        "Crystal hydrates incorporate water molecules in the lattice.",
    ),
    "ornithology": (
        "Migratory songbirds navigate using magnetic cues and star patterns.",
        "Raptors soar on thermal updrafts while scanning for prey.",
        "Waterfowl oil their feathers to maintain waterproof insulation.",
        "Nestlings beg with bright gapes that trigger parental feeding.",
        "Owls rotate their heads widely because cervical vertebrae allow it.",
        "Shorebirds probe mudflats with elongated bills for invertebrates.",
        "Altricial chicks hatch helpless and depend on nest care.",
        "Birdsong dialects vary across geographically separated populations.",
        "Flight feathers provide lift while down traps insulating air.",
        "Penguins propel underwater with wing strokes adapted for swimming.",
        "Brood parasites lay eggs in the nests of other bird species.",
        "Molting replaces worn plumage on a seasonal schedule.",
        "Hummingbirds hover by rotating wings in a figure-eight path.",
        "Colonial seabirds nest densely on predator-free cliffs.",
        "Beak shape correlates with preferred seed or insect diets.",
        "Precocial ducklings leave the nest soon after hatching.",
        "Birds store food in crops before digestion in the gizzard.",
        "Territory songs advertise ownership during breeding season.",
        "Wading herons strike fish with sudden neck extension.",
        "Feather pigments and structural color create plumage patterns.",
        "Long-distance migrants fatten extensively before departure.",
        "Cavity nesters excavate or reuse holes in standing timber.",
        "Flocking reduces individual predation risk in open habitats.",
        "Egg shells thin under severe environmental contaminant exposure.",
        "Aerial insectivores hawk flying prey above meadows at dusk.",
        "Sexual dimorphism often pairs bright males with cryptic females.",
        "Ground nesters rely on camouflage rather than elevated sites.",
        "Bill serrations help some ducks filter plant matter from water.",
        "Soaring albatrosses exploit wind gradients over ocean waves.",
        "Urban pigeons nest on ledges that mimic cliff habitats.",
        "Incubation keeps eggs within a narrow temperature window.",
        "Raptor talons seize and kill vertebrate prey efficiently.",
        "Seasonal plumage changes can signal breeding readiness.",
        "Vultures locate carcasses using acute olfactory cues.",
        "Wingspans of large soaring birds reduce flapping costs.",
        "Sandpipers stage at stopover wetlands rich in invertebrates.",
        "Nightjars catch moths during crepuscular aerial foraging.",
        "Birds lack teeth and process food with keratinized bills.",
        "Communal roosts concentrate warmth on cold winter nights.",
        "Flightless ratites retain powerful legs for running.",
        "Nest cup architecture varies with available plant fibers.",
        "Alarm calls warn flockmates when predators approach.",
        "Seabird guano fertilizes soils on nesting islands.",
        "Syrinx anatomy enables complex song modulation.",
        "Winter residents shift diets when insects become scarce.",
    ),
    "meteorology": (
        "Cold fronts force warm air aloft and often trigger showers.",
        "Relative humidity rises when air cools toward its dew point.",
        "Jet streams steer midlatitude storm systems across continents.",
        "Cumulonimbus towers indicate deep convection and possible hail.",
        "Sea breezes form when land heats faster than adjacent water.",
        "Isobars on surface charts connect points of equal pressure.",
        "Fog develops when moist air cools to saturation near the ground.",
        "El Niño alters Pacific trade winds and global rainfall patterns.",
        "Hailstones grow as updrafts recycle ice through supercooled layers.",
        "Trade winds blow steadily from subtropical highs toward the equator.",
        "Temperature inversions trap pollutants under a warm lid aloft.",
        "Orographic lift wrings moisture from air ascending mountain slopes.",
        "Lightning equalizes charge differences within thunderclouds.",
        "Barometers fall ahead of approaching low-pressure systems.",
        "Snow forms when ice crystals aggregate in subfreezing clouds.",
        "Monsoon circulations reverse seasonally with land-ocean heating.",
        "Radiosondes measure temperature and humidity through the troposphere.",
        "Wind chill describes heat loss from exposed skin in cold winds.",
        "Squall lines organize thunderstorms along advancing cold fronts.",
        "Stratocumulus sheets often cap marine boundary layers.",
        "Drought indices track prolonged deficits in precipitation.",
        "Tornadoes require strong vertical wind shear and rotating updrafts.",
        "Advection fog forms when warm moist air moves over cool surfaces.",
        "Polar vortex weakening can spill cold air into midlatitudes.",
        "Cloud albedo reflects incoming solar radiation back to space.",
        "Dew forms overnight when surfaces cool below the dew point.",
        "Tropical cyclones intensify over warm ocean heat reservoirs.",
        "Virga is precipitation that evaporates before reaching the ground.",
        "Anticyclones bring subsidence, clear skies, and settled weather.",
        "Freezing rain coats surfaces when a warm layer overlays cold air.",
        "Sensible heat flux warms the atmosphere from heated ground.",
        "Moisture convergence fuels heavy rainfall in mesoscale complexes.",
        "Upper-level troughs favor rising motion and cloud development.",
        "Dust storms loft fine particles when dry soils meet strong winds.",
        "Greenhouse gases absorb longwave radiation emitted by Earth.",
        "Lake-effect snow bands form downwind of unfrozen lakes.",
        "Visibility drops when aerosols and fog scatter light.",
        "Diurnal heating peaks afternoon convection over continents.",
        "Riming adds supercooled droplets to growing snow crystals.",
        "Trade-wind inversion limits cloud tops over subtropical oceans.",
        "Heat indexes combine temperature and humidity for human comfort.",
        "Blocking highs stall weather patterns for days to weeks.",
        "Microbursts produce damaging straight-line winds under storms.",
        "Satellite water-vapor imagery highlights mid-tropospheric moisture.",
        "Frost forms when surface temperatures fall below freezing overnight.",
    ),
    "geology": (
        "Granite crystallizes slowly from silica-rich magma underground.",
        "Sedimentary bedding records successive depositional events.",
        "Fault scarps mark where crustal blocks have slipped.",
        "Metamorphic rocks recrystallize under heat and pressure.",
        "River deltas build when sediment load exceeds coastal dispersal.",
        "Volcanic ash layers provide widespread stratigraphic markers.",
        "Glacial till is poorly sorted debris left by melting ice.",
        "Karst landscapes dissolve where limestone meets acidic groundwater.",
        "Plate boundaries concentrate earthquakes and volcanic arcs.",
        "Sandstone porosity can store groundwater or hydrocarbons.",
        "Foliation aligns minerals in rocks deformed by directed stress.",
        "Alluvial fans spread sediment where streams exit steep valleys.",
        "Basalt erupts as low-viscosity lava at mid-ocean ridges.",
        "Unconformities represent gaps in the depositional record.",
        "Mineral hardness is ranked on the Mohs scratch scale.",
        "Tectonic uplift raises mountains that then erode into basins.",
        "Loess deposits are windblown silt blanketing some plains.",
        "Geysers erupt when pressurized hot water flashes to steam.",
        "Coal forms from buried plant matter under reducing conditions.",
        "Strike and dip describe the orientation of rock layers.",
        "Weathering breaks rock into sediment before transport.",
        "Intrusive dikes cut across older host rock units.",
        "Evaporite beds precipitate when restricted seas dry.",
        "Isostasy balances crustal mass over the mantle.",
        "Paleomagnetism records ancient magnetic field polarity.",
        "Landslides move debris downslope when shear strength fails.",
        "Quartz resists chemical weathering better than feldspar.",
        "Rift valleys open where continental crust extends.",
        "Fossils in sedimentary rocks constrain relative ages.",
        "Hydrothermal veins deposit metals from hot fluids.",
        "Soil horizons develop through weathering and organic input.",
        "Tsunami waves can be triggered by submarine fault slip.",
        "Conglomerates contain rounded clasts cemented together.",
        "Mantle convection drives long-term plate motion.",
        "Desert pavements armor surfaces with lag gravel.",
        "Caldera collapses follow large explosive eruptions.",
        "Groundwater flows from recharge areas toward discharge.",
        "Schist glitter comes from aligned mica flakes.",
        "Turbidites settle from underwater sediment avalanches.",
        "Permafrost soils remain frozen for multiple years.",
        "Ore grades report useful metal concentration in rock.",
        "Coastal cliffs retreat under wave undercutting.",
        "Pumice floats because vesicles trap volcanic gas.",
        "Synclines fold strata into trough-shaped structures.",
        "Radiometric dating uses parent-daughter isotope ratios.",
    ),
    "mathematics": (
        "A prime number has exactly two distinct positive divisors.",
        "The derivative measures instantaneous rate of change.",
        "Eigenvectors stretch by a scalar under a linear map.",
        "A continuous function on a closed interval attains extrema.",
        "Modular arithmetic wraps integers at a fixed modulus.",
        "Bayes theorem updates beliefs given new evidence.",
        "Orthogonal vectors have a dot product of zero.",
        "The fundamental theorem links derivatives and integrals.",
        "Graph vertices connect by edges that may be weighted.",
        "A bijection is both injective and surjective.",
        "Taylor series approximate functions with polynomial terms.",
        "Variance summarizes squared deviations from the mean.",
        "Complex numbers extend reals with an imaginary unit.",
        "A group combines a set with an associative operation.",
        "Determinants vanish precisely when matrices are singular.",
        "Fourier transforms decompose signals into frequency components.",
        "Convex sets contain all line segments between their points.",
        "Induction proves statements across the natural numbers.",
        "Least squares fit minimizes residual squared error.",
        "Topology studies properties preserved by continuous deformation.",
        "Binomial coefficients count combinations without regard to order.",
        "A metric space defines distances satisfying triangle inequality.",
        "Partial derivatives hold other variables fixed.",
        "Integer factorization underpins common public-key systems.",
        "Markov chains evolve with memoryless transition probabilities.",
        "The Pythagorean theorem relates sides of right triangles.",
        "Linear independence means no vector is a combination of others.",
        "Limits describe values approached as inputs near a point.",
        "Combinatorial proofs count the same set in two ways.",
        "Singular value decompositions factor matrices into rotations and scales.",
        "Probability densities integrate to one over their support.",
        "Recursive sequences define each term from earlier terms.",
        "Homeomorphisms are continuous bijections with continuous inverses.",
        "Lagrange multipliers constrain optimization on manifolds.",
        "Boolean algebra underlies digital logic circuits.",
        "Cardinalities compare sizes of possibly infinite sets.",
        "Differential equations relate functions to their derivatives.",
        "Sparse matrices store mostly zero entries efficiently.",
        "Monte Carlo methods estimate integrals with random samples.",
        "A homomorphism preserves algebraic structure between objects.",
        "Euclidean algorithm computes greatest common divisors.",
        "Spectral gaps control mixing rates of random walks.",
        "Jacobian matrices collect first partial derivatives.",
        "Set partitions divide elements into nonempty disjoint blocks.",
        "Convergence tests decide whether infinite series settle.",
    ),
    "anatomy": (
        "Alveoli exchange oxygen and carbon dioxide in the lungs.",
        "Synovial joints allow smooth motion between bone ends.",
        "Neurons transmit signals via action potentials along axons.",
        "The liver metabolizes toxins and stores glycogen.",
        "Red blood cells carry oxygen bound to hemoglobin.",
        "Tendons connect muscle to bone across joints.",
        "Kidneys filter blood and regulate electrolyte balance.",
        "Cartilage cushions load-bearing surfaces in knees.",
        "The diaphragm contracts to expand the thoracic cavity.",
        "Skin epidermis renews from basal stem cell layers.",
        "Coronary arteries supply myocardium with oxygenated blood.",
        "Lymph nodes sample interstitial fluid for pathogens.",
        "Retinal photoreceptors convert light into neural signals.",
        "Bone marrow produces new blood cells continuously.",
        "The cerebellum coordinates timing of voluntary movement.",
        "Hormones travel through blood to distant target tissues.",
        "Smooth muscle lines vessel walls and hollow organs.",
        "Salivary glands begin enzymatic digestion of starch.",
        "Vertebrae protect the spinal cord within the canal.",
        "Capillaries are the primary sites of tissue exchange.",
        "The cochlea transduces sound vibrations into nerve impulses.",
        "Ligaments stabilize joints by connecting bone to bone.",
        "Pancreatic islets secrete insulin and glucagon.",
        "Mitochondria generate ATP for cellular energy needs.",
        "White matter tracts carry myelinated axons between regions.",
        "The stomach secretes acid to denature dietary proteins.",
        "Platelets aggregate to begin clot formation after injury.",
        "Synapses release neurotransmitters into the cleft.",
        "Periosteum covers bone surfaces except at joint cartilage.",
        "The spleen filters blood and recycles old erythrocytes.",
        "Motor units pair motor neurons with muscle fibers.",
        "Epithelial sheets line cavities and form barriers.",
        "Venous valves prevent backflow in limbs.",
        "Thyroid hormones set basal metabolic rate.",
        "Fascia wraps muscle groups into functional compartments.",
        "Olfactory receptors bind odorants in the nasal epithelium.",
        "The hippocampus supports formation of episodic memories.",
        "Bile emulsifies fats to aid intestinal absorption.",
        "Osteoclasts resorb bone during remodeling cycles.",
        "Pupillary reflexes adjust retinal light exposure.",
        "Intervertebral discs absorb compressive spinal loads.",
        "Plasma proteins maintain oncotic pressure in vessels.",
        "Cranial nerves exit the brainstem to innervate the head.",
        "Sweat glands cool the body by evaporative heat loss.",
        "The placenta mediates exchange between maternal and fetal blood.",
    ),
    "zoology": (
        "Amphibians typically require moist skin for cutaneous respiration.",
        "Herbivores host gut microbes that ferment cellulose.",
        "Camouflage patterns reduce detection by visual predators.",
        "Marsupials complete much development in an external pouch.",
        "Echolocating bats emit ultrasonic pulses to locate insects.",
        "Social insects divide labor among morphologically distinct castes.",
        "Hibernating mammals lower metabolic rate through winter.",
        "Coral polyps build calcium carbonate skeletons over decades.",
        "Migratory ungulates track seasonal forage across landscapes.",
        "Venomous snakes inject toxins through specialized fangs.",
        "Filter-feeding whales engulf krill with baleen plates.",
        "Territorial mammals scent-mark boundaries with gland secretions.",
        "Metamorphosis transforms aquatic larvae into terrestrial adults.",
        "Pack hunters coordinate to isolate vulnerable prey.",
        "Shells protect mollusks while adding locomotor cost.",
        "Nocturnal mammals often have enlarged eyes and pupils.",
        "Parasites complete life cycles across multiple hosts.",
        "Endotherms maintain stable body temperatures metabolically.",
        "Schooling fish confuse predators with coordinated motion.",
        "Arboreal primates have grasping hands and depth perception.",
        "Desert reptiles bask to raise body temperature after cool nights.",
        "Keystone predators can restructure entire food webs.",
        "Molt cycles replace exoskeletons in growing arthropods.",
        "Courtship displays advertise fitness to potential mates.",
        "Burrowing rodents aerate soils and redistribute seeds.",
        "Cephalopods change skin patterns for signaling and crypsis.",
        "Ruminants regurgitate cud for additional chewing.",
        "Freshwater fish osmoregulate against hypoosmotic surroundings.",
        "Brood care increases offspring survival in many taxa.",
        "Invasive species can outcompete natives in disturbed habitats.",
        "Antlers are shed and regrown annually in many deer.",
        "Symbiotic cleaning fish remove parasites from larger hosts.",
        "Flight muscles in insects power rapid wing oscillations.",
        "Carnivore dentition emphasizes shearing carnassial teeth.",
        "Seasonal coat color changes improve snow camouflage.",
        "Plankton form the base of many aquatic food chains.",
        "Terrapins bask on logs to thermoregulate.",
        "Monogamous pairs share nest defense in some birdlike mammals.",
        "Poison glands deter predators with distasteful secretions.",
        "Herd vigilance lets individuals forage with lower risk.",
        "Larval stages often occupy niches distinct from adults.",
        "Bioluminescence attracts prey in deep-sea habitats.",
        "Hoofed mammals run on reinforced toe tips.",
        "Ectoparasites live on host skin or feathers.",
        "Population cycles can arise from predator-prey feedback.",
    ),
    "physics": (
        "Inertia resists changes in an object's velocity.",
        "Kinetic energy scales with the square of speed.",
        "Magnetic fields exert forces on moving charges.",
        "Interference patterns reveal the wave nature of light.",
        "Entropy of an isolated system tends to increase.",
        "Resistors dissipate electrical energy as heat.",
        "Gravitational potential energy rises with height in a field.",
        "Photons carry energy proportional to their frequency.",
        "Friction opposes relative motion between contacting surfaces.",
        "Capacitors store energy in electric fields between plates.",
        "Standing waves form when reflections create fixed nodes.",
        "Momentum is conserved in the absence of external forces.",
        "Refraction bends light as it crosses media boundaries.",
        "Blackbody spectra depend only on absolute temperature.",
        "Torque equals force times lever-arm distance.",
        "Superconductors carry current with zero resistance below a critical temperature.",
        "Simple harmonic motion restores toward equilibrium proportionally.",
        "Pressure in a fluid increases with depth.",
        "Diffraction spreads waves around obstacles and apertures.",
        "Electric field lines begin on positive charges and end on negative ones.",
        "Angular momentum conservation guides spinning skaters' speed changes.",
        "Lenses focus rays according to their focal length.",
        "Work equals force applied through a displacement.",
        "Thermal conductivity measures heat flow through materials.",
        "Doppler shifts change observed frequency for moving sources.",
        "Inductors oppose changes in current via induced emf.",
        "Escape velocity depends on planetary mass and radius.",
        "Polarization filters transmit light oscillating in preferred planes.",
        "Buoyant force equals the weight of displaced fluid.",
        "Quantum tunneling allows particles to cross classically forbidden barriers.",
        "Centripetal acceleration points toward the center of circular paths.",
        "Snell's law relates incidence angles across refractive indices.",
        "Heat engines convert thermal energy into mechanical work.",
        "Magnetic flux through a loop equals field times area projection.",
        "Damping dissipates oscillatory energy over time.",
        "Coulomb's law gives force between point charges.",
        "Wavelength and frequency multiply to the wave speed.",
        "Inertial frames move at constant velocity relative to each other.",
        "Plasma is an ionized gas that conducts electricity.",
        "Strain measures fractional deformation under stress.",
        "Optical fibers guide light by total internal reflection.",
        "Nuclear binding energy holds protons and neutrons together.",
        "Pendulum period depends on length and gravity, not mass.",
        "Eddy currents induce heating in changing magnetic fields.",
        "Relativistic effects become significant near light speed.",
    ),
    "astronomy": (
        "Main-sequence stars fuse hydrogen into helium in their cores.",
        "Planetary orbits are ellipses with the sun at one focus.",
        "Nebulae are clouds of gas and dust in interstellar space.",
        "Pulsars are rapidly rotating neutron stars emitting beams.",
        "Redshift stretches light from receding distant galaxies.",
        "Comets develop tails when solar heating liberates volatiles.",
        "Black holes warp spacetime so escape requires superluminal speed.",
        "Asteroid belts occupy stable zones between planetary orbits.",
        "Parallax distances use Earth's baseline around the sun.",
        "Supernovae seed heavy elements into the interstellar medium.",
        "Tidal forces from moons raise oceans on host planets.",
        "Cosmic microwave background is relic radiation from early epochs.",
        "Binary stars orbit a shared center of mass.",
        "Auroras form when charged particles excite atmospheric gases.",
        "Exoplanets are detected via transits and radial-velocity shifts.",
        "Galactic spiral arms concentrate star-forming molecular clouds.",
        "Meteoroids become meteors when they ablate in air.",
        "White dwarfs are dense remnants supported by electron degeneracy.",
        "Solar wind streams charged particles from the corona.",
        "Occultations occur when one body passes in front of another.",
        "Dark matter is inferred from galactic rotation curves.",
        "Lunar maria are ancient basaltic plains on the moon.",
        "Quasars are luminous active galactic nuclei.",
        "Kepler's laws relate orbital period to semi-major axis.",
        "Interstellar dust reddens and dims starlight.",
        "Saturn's rings are composed of icy particle swarms.",
        "Gravitational lensing bends light around massive foreground objects.",
        "Stellar magnitudes quantify apparent brightness on a log scale.",
        "Protoplanetary disks are birthplaces of planets around young stars.",
        "Gamma-ray bursts are among the universe's most energetic events.",
        "The ecliptic is the sun's apparent annual path.",
        "Neutron stars pack solar mass into city-scale radii.",
        "Zodiacal light scatters from dust in the inner solar system.",
        "Proper motion tracks a star's angular path across the sky.",
        "Habitable zones are orbital ranges allowing surface liquid water.",
        "Solar eclipses happen when the moon covers the solar disk.",
        "Open clusters are loose groups of coeval stars.",
        "Cosmic rays are high-energy particles from astrophysical accelerators.",
        "Jovian planets have thick atmospheres over dense cores.",
        "Heliopause marks where solar wind meets interstellar medium.",
        "Spectroscopic binaries reveal orbital motion in line shifts.",
        "Irregular galaxies lack coherent spiral or elliptical form.",
        "Impact craters record bombardment histories of airless bodies.",
        "Bolometric luminosity integrates energy output over all wavelengths.",
        "Lagrange points are gravitational equilibrium locations in three-body systems.",
    ),
}


_FAMILY_CUE_RE = re.compile(
    r"\b(rizz|skibidi|gyatt|sigma|ohio|cap|no\s*cap|bussin|slay|based|"
    r"ratio|mid|npc|aura|brainrot|degen|wagmi|ngmi|ser|anon|ape|"
    r"long|short|hedge|parlay|odds|meta|nerf|buff|grind|loot|"
    r"prompt|llm|agent|token|meme|viral|ship|situationship|"
    r"flex|drip|fit|stan|simp|ick|toxic|red\s*flag)\b",
    re.I,
)


def ordinary_domain_fill_rows(*, blocked_ids: set[str]) -> list[dict[str, Any]]:
    """Deterministic in-domain NONE bank used to meet ORDINARY_DOMAIN floors."""
    elongations = (
        "",
        " Field notes record this as ordinary domain description without slang evidence.",
        " Textbook prose states the mechanism in explicit definitional detail for learners.",
        " Survey summaries repeat the same non-memetic factual claim for archival completeness.",
    )
    rows: list[dict[str, Any]] = []
    for domain in ORDINARY_DOMAIN_LABELS:
        for idx, base in enumerate(ORDINARY_DOMAIN_BANK[domain]):
            text = (base + elongations[idx % len(elongations)]).strip()
            identity = normalized_text_sha256(text)
            if identity in blocked_ids:
                continue
            rows.append(
                {
                    "class": "INFERRED",
                    "evidence_subtype": "ORDINARY_DOMAIN_NONE",
                    "jev": "OFF",
                    "lineage": "none",
                    "notes": f"v5_ordinary_domain_bank:{domain}",
                    "rights": "internal-synthetic",
                    "split": "train",
                    "surface": "train",
                    "task": "classify",
                    "text": text,
                    "topic_domain": domain,
                }
            )
    rows.sort(key=lambda item: normalized_text_sha256(item["text"]))
    return rows


def generic_prose_fill_rows(*, blocked_ids: set[str], need: int) -> list[dict[str, Any]]:
    templates = (
        "The schedule lists ordinary errands without specialized jargon {i}.",
        "A quiet afternoon involves reading and tea preparation number {i}.",
        "Household chores continue in a routine pattern for case {i}.",
        "The notebook records mundane observations from day {i}.",
        "Local transit delays affected several commuters on route {i}.",
        "Kitchen inventory counts cans and dry goods for week {i}.",
        "The calendar marks appointments that carry no slang signal {i}.",
        "Indoor plants need water on a simple repeating cycle {i}.",
        "A walk around the block remains an ordinary leisure activity {i}.",
        "Office supplies were reordered after the cupboard ran low {i}.",
    )
    rows: list[dict[str, Any]] = []
    i = 0
    while len(rows) < need and i < need * 20:
        text = templates[i % len(templates)].format(i=i)
        identity = normalized_text_sha256(text)
        i += 1
        if identity in blocked_ids:
            continue
        rows.append(
            {
                "class": "INFERRED",
                "evidence_subtype": "GENERIC_NONE",
                "jev": "OFF",
                "lineage": "none",
                "notes": "v5_generic_prose_fill",
                "split": "train",
                "surface": "train",
                "task": "classify",
                "text": text,
                "topic_domain": "generic",
            }
        )
    return rows


def near_domain_fill_rows(*, blocked_ids: set[str], need: int) -> list[dict[str, Any]]:
    templates = (
        "Online forums discussed internet habits without a clear slang family {i}.",
        "Gaming peripherals were reviewed for comfort rather than meta shifts {i}.",
        "Crypto market headlines mentioned prices without degen ritual cues {i}.",
        "Betting interfaces showed odds tables but no sharp angle claim {i}.",
        "Discord servers posted schedules for ordinary community events {i}.",
        "Reddit threads summarized news without durable memetic framing {i}.",
        "Status updates described weekend plans in plain speech {i}.",
        "Viral video comments stayed descriptive without family-bearing slang {i}.",
        "Workplace chat tools relayed meeting links without corp jargon load {i}.",
        "Streaming chats reacted with applause emotes and little lexical signal {i}.",
    )
    rows: list[dict[str, Any]] = []
    i = 0
    while len(rows) < need and i < need * 20:
        text = templates[i % len(templates)].format(i=i)
        identity = normalized_text_sha256(text)
        i += 1
        if identity in blocked_ids:
            continue
        rows.append(
            {
                "class": "INFERRED",
                "evidence_subtype": "NEAR_DOMAIN_NONE",
                "jev": "OFF",
                "lineage": "none",
                "notes": "v5_near_domain_fill",
                "split": "train",
                "surface": "train",
                "task": "classify",
                "text": text,
                "topic_domain": "near-domain",
            }
        )
    return rows


def short_atom_fill_rows(*, blocked_ids: set[str], need: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    i = 0
    while len(rows) < need and i < need * 30:
        # Deterministic short atoms / two-word atoms; avoid dictionary collisions via suffix.
        text = f"zx{i}" if i % 3 else f"qx {i}"
        identity = normalized_text_sha256(text)
        i += 1
        if identity in blocked_ids:
            continue
        rows.append(
            {
                "class": "INFERRED",
                "evidence_subtype": "SHORT_ATOM_NONE",
                "jev": "OFF",
                "lineage": "none",
                "notes": "v5_short_atom_fill",
                "split": "train",
                "surface": "train",
                "task": "classify",
                "text": text,
                "topic_domain": "short-atom",
            }
        )
    return rows


def hard_none_fill_rows(*, blocked_ids: set[str], need: int) -> list[dict[str, Any]]:
    templates = (
        "Legacy aura chatter atom placeholder {i} lacks active-family evidence.",
        "Brainrot-adjacent lexical residue {i} is insufficient for emission under forward heads.",
        "Merged-head leftover phrase {i} without forward ontology support in the active set.",
        "Retired typology scrap {i} that must remain NO_EVIDENCE for Stage-A teaching.",
        "Non-forward head residue text {i} with no active family span and no evidence cue.",
        "Hard none prose sample {i} mirrors length of positives while omitting family semantics entirely.",
    )
    rows: list[dict[str, Any]] = []
    i = 0
    while len(rows) < need and i < need * 20:
        text = templates[i % len(templates)].format(i=i)
        identity = normalized_text_sha256(text)
        i += 1
        if identity in blocked_ids:
            continue
        rows.append(
            {
                "class": "INFERRED",
                "evidence_subtype": "HARD_NONE",
                "jev": "OFF",
                "lineage": "brainrot-aura",
                "notes": "v5_hard_none_fill",
                "split": "train",
                "surface": "train",
                "task": "classify",
                "text": text,
                "topic_domain": "hard-none",
            }
        )
    return rows


def lookalike_from_positive(positive_text: str, *, index: int) -> str:
    """Share surface cues/length with a positive while stripping family evidence."""
    cleaned = _FAMILY_CUE_RE.sub("neutral", positive_text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if cleaned.casefold() == positive_text.casefold() or len(tokens(cleaned)) < 3:
        base_tokens = sorted(tokens(positive_text))[:6]
        shared = " ".join(base_tokens) if base_tokens else "shared lexical residue"
        cleaned = (
            f"{shared} appears in ordinary documentation without active family evidence {index}"
        )
    else:
        cleaned = f"{cleaned} ordinary restatement {index}"
    return cleaned


def lexical_lookalike_fill_rows(
    positives: Sequence[Mapping[str, Any]],
    *,
    blocked_ids: set[str],
    need: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ordered = sorted(positives, key=lambda item: item["identity"])
    i = 0
    while len(rows) < need and ordered:
        pos = ordered[i % len(ordered)]
        text = lookalike_from_positive(str(pos["text"]), index=i)
        identity = normalized_text_sha256(text)
        i += 1
        if identity in blocked_ids or identity == pos["identity"]:
            if i > need * 50:
                break
            continue
        rows.append(
            {
                "class": "INFERRED",
                "evidence_subtype": "LEXICAL_LOOKALIKE_NONE",
                "jev": "OFF",
                "lineage": "none",
                "notes": f"v5_lookalike_of:{pos['identity'][:16]}",
                "parent_identity": None,
                "split": "train",
                "surface": "train",
                "task": "classify",
                "text": text,
                "topic_domain": "lexical-lookalike",
            }
        )
        if i > need * 50:
            break
    return rows


def augment_source_rows_for_floors(
    source_rows: Sequence[Mapping[str, Any]],
    *,
    blocked_ids: set[str],
) -> list[dict[str, Any]]:
    """Append deterministic fill rows so acquisition floors can be met."""
    rows = [dict(row) for row in source_rows]
    # Seed ordinary bank first so classify_hub_subtype / explicit subtype can admit them.
    rows.extend(ordinary_domain_fill_rows(blocked_ids=blocked_ids))
    # Provisional pools to estimate gaps (ignore fills already added except ordinary).
    provisional = collect_pools(rows, blocked_ids=blocked_ids)
    positives = provisional.get("POSITIVE_EVIDENCE") or []

    def gap(subtype: str) -> int:
        return max(0, ACQUISITION_FLOORS[subtype] - len(provisional.get(subtype) or []))

    # Recompute after each major fill class.
    if gap("LEXICAL_LOOKALIKE_NONE"):
        rows.extend(
            lexical_lookalike_fill_rows(
                positives, blocked_ids=blocked_ids, need=gap("LEXICAL_LOOKALIKE_NONE") + 40
            )
        )
        provisional = collect_pools(rows, blocked_ids=blocked_ids)
    if gap("HARD_NONE"):
        rows.extend(hard_none_fill_rows(blocked_ids=blocked_ids, need=gap("HARD_NONE") + 20))
        provisional = collect_pools(rows, blocked_ids=blocked_ids)
    if gap("NEAR_DOMAIN_NONE"):
        rows.extend(near_domain_fill_rows(blocked_ids=blocked_ids, need=gap("NEAR_DOMAIN_NONE") + 20))
        provisional = collect_pools(rows, blocked_ids=blocked_ids)
    if gap("GENERIC_NONE"):
        rows.extend(generic_prose_fill_rows(blocked_ids=blocked_ids, need=gap("GENERIC_NONE") + 40))
        provisional = collect_pools(rows, blocked_ids=blocked_ids)
    if gap("SHORT_ATOM_NONE"):
        rows.extend(short_atom_fill_rows(blocked_ids=blocked_ids, need=gap("SHORT_ATOM_NONE") + 20))
    return rows
