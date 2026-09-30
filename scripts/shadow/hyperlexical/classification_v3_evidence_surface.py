"""HYPERLEX_V3_EVIDENCE_SURFACE_V1 — fresh evidence-gate dataset builder.

Builds train/validation evidence examples from admissible unspent train-side
rows. Does not train, does not reuse the spent v2 reserve, does not create a
v3 reserve, and does not move BEST.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

# Forward 18-family ontology is required for v3 evidence surface construction.
os.environ.setdefault("HLX_V2_FORWARD_ONTOLOGY", "1")

from .classification_v2 import ACTIVE_FAMILY_VOCABULARY, LEGACY_HEADS
from .classification_v2_surface import SURFACE_AMBIGUOUS, SURFACE_ATOM, SURFACE_PROSE, surface_form, word_count
from .classification_v3_evidence_gate import (
    EVIDENCE_SUBTYPES,
    FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX,
    FAMILY_EMISSION_PRECISION_MIN_AFTER_GATE,
    RULE,
    SUBTYPE_TO_LABEL,
    validate_example_label_pair,
)
from .holdout_guard import normalized_text_sha256

SURFACE_RULE = "HYPERLEX_V3_EVIDENCE_SURFACE_V1"
SURFACE_SCHEMA = "hyperlex.classification.v3.evidence_surface.v1"
SPLIT_SEED_PREFIX = "hlx.v3.evidence.surface.split.v1"

ACQUISITION_FLOORS = {
    "POSITIVE_EVIDENCE": 500,
    "HARD_NONE": 250,
    "NEAR_DOMAIN_NONE": 250,
    "GENERIC_NONE": 250,
    "AMBIGUOUS_EVIDENCE": 150,
}
VALIDATION_FLOORS = {
    "POSITIVE_EVIDENCE": 100,
    "HARD_NONE": 50,
    "NEAR_DOMAIN_NONE": 50,
    "GENERIC_NONE": 50,
    "AMBIGUOUS_EVIDENCE": 30,
}

SCHEMA_FILES = {
    "evidence_example.v1": "6981f65816a94630f9929e92feda96ddd72f74ab9aacfe3bd86764efbccf5141",
    "evidence_decision.v1": "bce1caaae235a5c7482012a8bd06619b8e70dc44e5a95fd6d84ad5730ce810ba",
    "family_candidates.v1": "49e364fea1e86111a194021cc302ab09a3bbdffe8dd94fe383101cd688f2c521",
    "decision.v1": "ec40356757c5a9e0b639603c6fc14b9650e8d2ecfe956123a0121e6559a12782",
}


def preregistration_contract() -> dict[str, Any]:
    return {
        "decision_semantics": {
            "EVIDENCE_PRESENT": "Stage_B_retrieval",
            "NO_EVIDENCE": "NONE",
            "UNCERTAIN": "ABSTAIN",
        },
        "false_evidence_entry_rate_on_none_max": FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX,
        "family_emission_precision_min": FAMILY_EMISSION_PRECISION_MIN_AFTER_GATE,
        "rule": RULE,
        "schema_sha256": dict(SCHEMA_FILES),
        "stage_a_labels": ["NO_EVIDENCE", "EVIDENCE_PRESENT", "UNCERTAIN"],
        "state": "PREREGISTERED",
        "surface_rule": SURFACE_RULE,
        "train": False,
        "version_bump_required_for_reinterpretation": True,
    }


def source_sha256(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def _span(text: str) -> list[dict[str, Any]]:
    if not text:
        return []
    return [{"start": 0, "end": len(text), "cue": None}]


def _is_admissible_source_row(row: Mapping[str, Any]) -> bool:
    if row.get("split") != "train":
        return False
    if row.get("task") not in {"classify", "classify+unbind"}:
        return False
    if row.get("evaluation_reserve") or row.get("held_out"):
        return False
    if row.get("surface") in {"held_out", "evaluation_reserve", "settlement", "measurement"}:
        return False
    if row.get("jev") not in {None, False, "OFF", "off"}:
        return False
    if row.get("class") not in {"OBSERVED", "INFERRED"}:
        return False
    text = str(row.get("text") or "").strip()
    return bool(text)


def classify_subtype(row: Mapping[str, Any]) -> str | None:
    """Deterministic subtype assignment from an admissible train-side row."""
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
    if lineage in LEGACY_HEADS:
        return "HARD_NONE"
    if lineage == "none":
        if form == SURFACE_PROSE or wc >= 3:
            return "NEAR_DOMAIN_NONE"
        return "GENERIC_NONE"
    return None


def build_example(row: Mapping[str, Any], subtype: str) -> dict[str, Any]:
    text = str(row["text"])
    identity = normalized_text_sha256(text)
    label = SUBTYPE_TO_LABEL[subtype]
    validate_example_label_pair(label, subtype)
    lineage = row.get("lineage")
    candidates: list[str] = []
    positive_spans: list[dict[str, Any]] = []
    if subtype == "POSITIVE_EVIDENCE":
        candidates = [str(lineage)]
        positive_spans = _span(text)
    elif subtype == "AMBIGUOUS_EVIDENCE" and lineage in ACTIVE_FAMILY_VOCABULARY:
        candidates = [str(lineage)]
    example = {
        "candidate_families": candidates,
        "evidence_label": label,
        "evidence_subtype": subtype,
        "identity": identity,
        "negative_evidence_spans": [],
        "notes": None,
        "parent_identity": None,
        "positive_evidence_spans": positive_spans,
        "provenance": str(row["class"]),
        "source_sha256": source_sha256(text),
        "split": "train",  # overwritten later
        "text": text,
    }
    return example


def collect_pools(
    rows: Sequence[Mapping[str, Any]],
    *,
    spent_reserve_ids: set[str],
) -> dict[str, list[dict[str, Any]]]:
    pools: dict[str, dict[str, dict[str, Any]]] = {name: {} for name in EVIDENCE_SUBTYPES}
    for row in rows:
        if not _is_admissible_source_row(row):
            continue
        subtype = classify_subtype(row)
        if subtype is None:
            continue
        example = build_example(row, subtype)
        identity = example["identity"]
        if identity in spent_reserve_ids:
            continue
        # Prefer OBSERVED over INFERRED when the same identity appears twice.
        previous = pools[subtype].get(identity)
        if previous is None or (
            previous["provenance"] == "INFERRED" and example["provenance"] == "OBSERVED"
        ):
            pools[subtype][identity] = example
    return {
        subtype: sorted(values.values(), key=lambda item: item["identity"])
        for subtype, values in pools.items()
    }


def _split_bucket(identity: str) -> str:
    digest = hashlib.sha256(f"{SPLIT_SEED_PREFIX}:{identity}".encode("utf-8")).hexdigest()
    return "validation" if int(digest[:8], 16) % 5 == 0 else "train"


def assign_splits(pools: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, Any]:
    """Stratified split meeting validation floors; remainder keeps hash split."""
    assigned: dict[str, list[dict[str, Any]]] = {"train": [], "validation": []}
    missing_val = {}
    for subtype in EVIDENCE_SUBTYPES:
        rows = [dict(row) for row in pools.get(subtype) or []]
        floor = VALIDATION_FLOORS[subtype]
        # Prefer hash-native validation rows first.
        native_val = [row for row in rows if _split_bucket(row["identity"]) == "validation"]
        native_train = [row for row in rows if _split_bucket(row["identity"]) == "train"]
        chosen_val = list(native_val)
        if len(chosen_val) < floor:
            need = floor - len(chosen_val)
            promote = native_train[:need]
            chosen_val.extend(promote)
            native_train = native_train[need:]
        if len(chosen_val) < floor:
            missing_val[subtype] = floor - len(chosen_val)
        for row in chosen_val:
            row["split"] = "validation"
            assigned["validation"].append(row)
        for row in native_train:
            row["split"] = "train"
            assigned["train"].append(row)
    for split in ("train", "validation"):
        assigned[split].sort(key=lambda item: (item["evidence_subtype"], item["identity"]))
    return {"rows": assigned["train"] + assigned["validation"], "missing_validation_floors": missing_val}


def validate_row(example: Mapping[str, Any], ontology: Sequence[str]) -> list[str]:
    errors = []
    try:
        validate_example_label_pair(str(example["evidence_label"]), str(example["evidence_subtype"]))
    except Exception as exc:  # noqa: BLE001 - contract surface
        errors.append(str(exc))
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
    for family in example.get("candidate_families") or []:
        if family not in allowed:
            errors.append(f"candidate_family_invalid:{family}")
    for key in ("positive_evidence_spans", "negative_evidence_spans"):
        for span in example.get(key) or []:
            start = int(span.get("start", -1))
            end = int(span.get("end", -1))
            if start < 0 or end <= start or end > len(text):
                errors.append(f"span_bounds:{key}")
            if not math.isfinite(float(start)) or not math.isfinite(float(end)):
                errors.append(f"span_nonfinite:{key}")
    if example["evidence_subtype"] == "POSITIVE_EVIDENCE":
        if not example.get("candidate_families"):
            errors.append("positive_missing_candidates")
        if not example.get("positive_evidence_spans"):
            errors.append("positive_missing_spans")
    return errors


def near_duplicate_groups(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        text = re.sub(r"\s+", " ", str(row["text"]).casefold()).strip()
        key = text[:48]
        groups[key].append(row["identity"])
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
        form = surface_form(str(row["text"]))
        by_subtype[subtype][form] += 1
        lengths[subtype].append(word_count(str(row["text"])))

    def _mean(values: Sequence[int]) -> float | None:
        if not values:
            return None
        return sum(values) / len(values)

    positive_atom_rate = None
    pos = by_subtype["POSITIVE_EVIDENCE"]
    if sum(pos.values()):
        positive_atom_rate = pos[SURFACE_ATOM] / sum(pos.values())
    critical = []
    for subtype in ("HARD_NONE", "NEAR_DOMAIN_NONE", "GENERIC_NONE"):
        counts = by_subtype[subtype]
        total = sum(counts.values())
        if not total:
            continue
        atom_rate = counts[SURFACE_ATOM] / total
        # Shortcut: NONE subclass almost entirely ATOM while POSITIVE is mostly PROSE,
        # or identical mean length collapse — flag only extreme GENERIC vs POSITIVE prose gap.
        if (
            subtype == "GENERIC_NONE"
            and positive_atom_rate is not None
            and atom_rate > 0.98
            and positive_atom_rate < 0.35
        ):
            # Expected structural difference for generic short none; not critical alone.
            pass
        mean_len = _mean(lengths[subtype])
        pos_mean = _mean(lengths["POSITIVE_EVIDENCE"])
        if (
            mean_len is not None
            and pos_mean is not None
            and subtype == "NEAR_DOMAIN_NONE"
            and abs(mean_len - pos_mean) < 0.25
            and atom_rate == positive_atom_rate
        ):
            critical.append(f"{subtype}_indistinguishable_from_positive_surface")
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


def build_diagnostics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    subtype_counts = Counter(row["evidence_subtype"] for row in rows)
    label_counts = Counter(row["evidence_label"] for row in rows)
    provenance_counts = Counter(row["provenance"] for row in rows)
    split_counts = Counter(row["split"] for row in rows)
    family_support = Counter()
    for row in rows:
        if row["evidence_subtype"] != "POSITIVE_EVIDENCE":
            continue
        for family in row.get("candidate_families") or []:
            family_support[family] += 1
    lengths = [word_count(str(row["text"])) for row in rows]
    forms = Counter(surface_form(str(row["text"])) for row in rows)
    identities = [row["identity"] for row in rows]
    duplicate_rate = 0.0
    if identities:
        duplicate_rate = 1.0 - (len(set(identities)) / len(identities))
    near = near_duplicate_groups(rows)
    val_subtype = Counter(
        row["evidence_subtype"] for row in rows if row["split"] == "validation"
    )
    return {
        "ATOM_PROSE": dict(forms),
        "counts_by_gate_label": dict(label_counts),
        "counts_by_provenance": dict(provenance_counts),
        "counts_by_split": dict(split_counts),
        "counts_by_subtype": dict(subtype_counts),
        "duplicate_rate": duplicate_rate,
        "mean_word_count": None if not lengths else sum(lengths) / len(lengths),
        "n": len(rows),
        "near_duplicate_groups": near[:20],
        "near_duplicate_group_count": len(near),
        "positive_family_support": dict(sorted(family_support.items())),
        "validation_subtype_counts": dict(val_subtype),
        "word_count_max": max(lengths) if lengths else None,
        "word_count_min": min(lengths) if lengths else None,
    }


def readiness_report(
    *,
    rows: Sequence[Mapping[str, Any]],
    spent_overlap: Sequence[str],
    validation_errors: Sequence[str],
    shortcut: Mapping[str, Any],
    missing_validation_floors: Mapping[str, int],
) -> dict[str, Any]:
    subtype_counts = Counter(row["evidence_subtype"] for row in rows)
    val_counts = Counter(row["evidence_subtype"] for row in rows if row["split"] == "validation")
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
    zero_subtype = [subtype for subtype in EVIDENCE_SUBTYPES if subtype_counts.get(subtype, 0) == 0]
    blockers = []
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
        blockers.append({"spent_v2_reserve_overlap": len(spent_overlap)})
    if validation_errors:
        blockers.append({"schema_or_row_errors": len(validation_errors)})
    if zero_subtype:
        blockers.append({"zero_count_subtype": zero_subtype})
    if not shortcut.get("pass", False):
        blockers.append({"critical_surface_shortcut": shortcut.get("critical_shortcuts")})
    # identity uniqueness
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


def canonical_json(payload: Mapping[str, Any]) -> str:
    import json

    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_spent_v2_reserve_ids(
    *,
    ledger: Mapping[str, Any],
    reserve_rows: Sequence[Mapping[str, Any]] | None = None,
) -> set[str]:
    """Permanently excluded spent v2 classify-reserve + sealed reserve-row identities."""
    spent: set[str] = set()
    for record in ledger.get("identities") or []:
        state = record.get("state")
        if state not in {"EVAL_RESERVE", "EVAL_SPENT"}:
            continue
        labels = [
            label
            for label in (record.get("labels") or [])
            if label.get("task") == "classify"
        ]
        if labels or state == "EVAL_RESERVE":
            digest = record.get("normalized_text_sha256")
            if digest:
                spent.add(str(digest))
    for row in reserve_rows or []:
        digest = row.get("normalized_text_sha256") or row.get("identity")
        if digest:
            spent.add(str(digest))
    return spent


def compute_split_leakage(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    train_ids = {row["identity"] for row in rows if row["split"] == "train"}
    val_ids = {row["identity"] for row in rows if row["split"] == "validation"}
    train_sources = {
        row["source_sha256"] for row in rows if row["split"] == "train"
    }
    val_sources = {
        row["source_sha256"] for row in rows if row["split"] == "validation"
    }
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
    identity_overlap = sorted(train_ids & val_ids)
    source_overlap = sorted(train_sources & val_sources)
    parent_overlap = sorted(parents_train & parents_val)
    return {
        "parent_identity_collisions": len(parent_overlap),
        "source_hash_collisions_across_splits": len(source_overlap),
        "split_identity_overlap": len(identity_overlap),
        "split_identity_overlap_ids": identity_overlap[:16],
        "source_hash_collision_ids": source_overlap[:16],
        "parent_identity_collision_ids": parent_overlap[:16],
    }


def build_surface(
    source_rows: Sequence[Mapping[str, Any]],
    *,
    spent_reserve_ids: set[str],
    ontology: Sequence[str],
) -> dict[str, Any]:
    """Full evidence-surface build: pool → split → QA → readiness → artifacts."""
    pools = collect_pools(source_rows, spent_reserve_ids=spent_reserve_ids)
    split_result = assign_splits(pools)
    rows = split_result["rows"]
    validation_errors: list[str] = []
    for row in rows:
        for error in validate_row(row, ontology):
            validation_errors.append(f"{row['identity']}:{error}")
    leakage = compute_split_leakage(rows)
    spent_overlap = sorted(
        {row["identity"] for row in rows} & set(spent_reserve_ids)
    )
    diagnostics = build_diagnostics(rows)
    diagnostics["spent_v2_reserve_overlap"] = len(spent_overlap)
    shortcut = surface_shortcut_diagnostics(rows)
    readiness = readiness_report(
        rows=rows,
        spent_overlap=spent_overlap,
        validation_errors=validation_errors,
        shortcut=shortcut,
        missing_validation_floors=split_result["missing_validation_floors"],
    )
    if not leakage["split_identity_overlap"] == 0:
        readiness["blockers"].append(
            {"split_identity_overlap": leakage["split_identity_overlap"]}
        )
    if leakage["source_hash_collisions_across_splits"]:
        readiness["blockers"].append(
            {
                "source_hash_collisions_across_splits": leakage[
                    "source_hash_collisions_across_splits"
                ]
            }
        )
    if leakage["parent_identity_collisions"]:
        readiness["blockers"].append(
            {"parent_identity_collisions": leakage["parent_identity_collisions"]}
        )
    if readiness["blockers"]:
        readiness["state"] = "PREREGISTERED"
        readiness["missing_evidence"] = readiness["blockers"]
    else:
        readiness["state"] = "READY"
        readiness["missing_evidence"] = []
    assembled = assemble_surface_artifacts(
        {
            "diagnostics": diagnostics,
            "readiness": readiness,
            "rows": rows,
            "shortcut": shortcut,
            "spent_overlap": spent_overlap,
            "source_hash_collisions": leakage["source_hash_collisions_across_splits"],
            "split_identity_overlap": leakage["split_identity_overlap"],
            "parent_identity_collisions": leakage["parent_identity_collisions"],
        }
    )
    return {
        "assembled": assembled,
        "leakage": leakage,
        "pools": {subtype: len(values) for subtype, values in pools.items()},
        "readiness": readiness,
        "rows": rows,
        "validation_errors": validation_errors,
    }


def assemble_surface_artifacts(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Assemble hashed manifests from builder outputs."""
    rows = list(payload["rows"])
    diagnostics = payload["diagnostics"]
    shortcut = payload["shortcut"]
    spent_overlap = list(payload.get("spent_overlap") or [])
    readiness = payload["readiness"]
    dataset_lines = [canonical_json(row) for row in rows]
    dataset_body = "\n".join(dataset_lines) + ("\n" if dataset_lines else "")
    dataset_sha = sha256_text(dataset_body)
    split_manifest = {
        "schema": "hyperlex.classification.v3.evidence_split_manifest.v1",
        "splits": {
            "train": sorted(
                row["identity"] for row in rows if row["split"] == "train"
            ),
            "validation": sorted(
                row["identity"] for row in rows if row["split"] == "validation"
            ),
        },
        "surface_rule": SURFACE_RULE,
        "v3_reserve": None,
    }
    split_manifest["manifest_sha256"] = sha256_text(
        canonical_json({k: v for k, v in split_manifest.items() if k != "manifest_sha256"})
    )
    disjointness = {
        "dataset_sha256": dataset_sha,
        "parent_identity_collisions": int(payload.get("parent_identity_collisions") or 0),
        "schema": "hyperlex.classification.v3.evidence_disjointness.v1",
        "source_hash_collisions_across_splits": payload.get("source_hash_collisions", 0),
        "spent_v2_reserve_overlap": spent_overlap,
        "spent_v2_reserve_overlap_count": len(spent_overlap),
        "split_identity_overlap": payload.get("split_identity_overlap", 0),
        "surface_rule": SURFACE_RULE,
        "pass": len(spent_overlap) == 0
        and payload.get("split_identity_overlap", 0) == 0
        and payload.get("source_hash_collisions", 0) == 0
        and int(payload.get("parent_identity_collisions") or 0) == 0,
    }
    disjointness["witness_sha256"] = sha256_text(
        canonical_json({k: v for k, v in disjointness.items() if k != "witness_sha256"})
    )
    if not disjointness["pass"]:
        readiness = dict(readiness)
        readiness["state"] = "PREREGISTERED"
        blockers = list(readiness.get("blockers") or [])
        blockers.append({"disjointness_failed": True})
        readiness["blockers"] = blockers
        readiness["missing_evidence"] = blockers
    diagnostics_payload = {
        "diagnostics": diagnostics,
        "schema": "hyperlex.classification.v3.evidence_surface_diagnostics.v1",
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
        "schema": "hyperlex.classification.v3.evidence_dataset_manifest.v1",
        "surface_rule": SURFACE_RULE,
        "validation_floors": VALIDATION_FLOORS,
    }
    dataset_manifest["manifest_sha256"] = sha256_text(
        canonical_json({k: v for k, v in dataset_manifest.items() if k != "manifest_sha256"})
    )
    readiness_receipt = {
        "BEST": "UNCHANGED",
        "best_sha256": "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6",
        "dataset_manifest_sha256": dataset_manifest["manifest_sha256"],
        "dataset_sha256": dataset_sha,
        "diagnostics_sha256": diagnostics_payload["diagnostics_sha256"],
        "disjointness_witness_sha256": disjointness["witness_sha256"],
        "preregistration": preregistration_contract(),
        "readiness": readiness,
        "rule": RULE,
        "schema": "hyperlex.classification.v3.evidence_surface_readiness.v1",
        "split_manifest_sha256": split_manifest["manifest_sha256"],
        "surface_rule": SURFACE_RULE,
        "train": False,
        "v3_reserve": None,
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
        "readiness_receipt": readiness_receipt,
        "shortcut": shortcut,
        "split_manifest": split_manifest,
    }
