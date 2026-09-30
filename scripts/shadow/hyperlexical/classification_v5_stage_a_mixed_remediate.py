"""REMEDIATE_V5_STAGE_A_MIXED_FAILURE_V1 — joint ordinary-NONE + PRESENT support.

Dataset-level remediation only. Does not train, score reserves, move BEST,
change architecture, or modify frozen readiness thresholds.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from typing import Any, Mapping, Sequence

from .classification_v2 import ACTIVE_FAMILY_VOCABULARY
from .classification_v5_stage_a_negative_evidence_surface import (
    ACQUISITION_FLOORS,
    BEST_SHA,
    DESIGN_RULE,
    EVIDENCE_SUBTYPES,
    STAGE_A_TRAIN_CONTRACT,
    VALIDATION_FLOORS,
    build_example,
    canonical_json,
    ordinary_domain_fill_rows,
    sha256_text,
)
from .classification_v5_stage_a_surface_remediate import (
    balance_lengths,
    build_near_dup_components,
    dedupe_within_label,
    downsample_ai_native,
    enforce_source_cap,
    make_observed_ordinary_rows,
    make_prose_family_positives,
    make_shared_vocab_negatives,
    pair_for_floors,
    repair_surface_balance,
    select_to_floors,
    top_up_subtype_floors,
)
from .classification_v5_surface_readiness_gates import (
    GATE_RULE,
    evaluate_surface_readiness,
    frozen_readiness_gates,
)

REMEDIATE_RULE = "REMEDIATE_V5_STAGE_A_MIXED_FAILURE_V1"
SURFACE_RULE_V1R8 = "HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R8"
PARENT_SURFACE_SHA = (
    "a81ca68ad3310981c60d2500a83a0989adeb967cbee6ad6dff003ed2c705efa9"
)
PARENT_DIAGNOSIS = "MIXED_STAGE_A_FAILURE"
DIAGNOSIS_RECEIPT_SHA = (
    "246bbae77d55d8b0c97193b4452f13ac33410dd552ab7eaeadc4e85466abe9cd"
)
SELECTED_CHECKPOINT_SHA = (
    "3b1b574acceea183363b8cea41e1b7e4e13dc934bacc66deb4b3b8caeabc90a7"
)
SPLIT_SEED = "hlx.v5.stage_a.mixed.remediate.component.split.v1"

# Train support floors justified by diagnosis (train ordinary OBSERVED was 0).
TRAIN_ORDINARY_OBSERVED_FLOOR = 160
TRAIN_PRESENT_OBSERVED_FLOOR = 140

# Families with concentrated PRESENT→NONE mass in the sealed diagnosis.
PRESENT_SUPPORT_PRIORITY = (
    "workplace-career",
    "conflict-aggression",
    "politics-civic",
    "regional-cultural",
    "social-evaluation",
    "internet-slang",
    "crypto-degen",
    "technology-ai",
    "sports-competition",
    "betting-sharp",
    "memetic",
    "gaming-meta",
    "fashion-aesthetic",
    "identity-affiliation",
)


def remediate_contract() -> dict[str, Any]:
    return {
        "best": "UNCHANGED",
        "best_sha256": BEST_SHA,
        "design_rule": DESIGN_RULE,
        "diagnosis_receipt_sha256": DIAGNOSIS_RECEIPT_SHA,
        "gate_rule": GATE_RULE,
        "parent_diagnosis": PARENT_DIAGNOSIS,
        "parent_surface_dataset_sha256": PARENT_SURFACE_SHA,
        "provenance_association": "OBSERVED",
        "provenance_causality": "NOT_ESTABLISHED",
        "readiness_thresholds_modified": False,
        "remediate_rule": REMEDIATE_RULE,
        "reserve": False,
        "selected_checkpoint_sha256": SELECTED_CHECKPOINT_SHA,
        "surface_rule": SURFACE_RULE_V1R8,
        "train": False,
        "train_authorized": False,
        "train_ordinary_observed_floor": TRAIN_ORDINARY_OBSERVED_FLOOR,
        "train_present_observed_floor": TRAIN_PRESENT_OBSERVED_FLOOR,
    }


def _source_bucket_for(row: Mapping[str, Any], *, shard: int) -> str:
    url = str(row.get("source_url") or "")
    domain = str(row.get("topic_domain") or "wiki")
    if "wikipedia.org" in url:
        return f"v5_src_wp_{domain}_{shard % 4}"
    if "wiktionary.org" in url:
        return f"v5_src_wik_{domain}_{shard % 4}"
    if url:
        return f"v5_src_url_{domain}_{shard % 4}"
    if row.get("provenance") == "OBSERVED":
        fam = (row.get("active_family_support") or ["none"])[0]
        return f"v5_src_hub_obs_{fam}_{shard % 3}"
    subtype = str(row.get("evidence_subtype"))
    return f"v5_src_inf_{subtype}_{shard % 4}"


def stamp_source_buckets_mixed(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        item = dict(row)
        shard = int(item["identity"][:8], 16)
        item["source_bucket"] = _source_bucket_for(item, shard=shard)
        notes = str(item.get("notes") or "")
        if not notes.startswith("v5_src_"):
            item["notes"] = f"{item['source_bucket']}:{notes}" if notes else item["source_bucket"]
        out.append(item)
    return out


def assign_component_splits_mixed(
    components: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    """Component→split: reserve train OBSERVED support, then fill validation floors."""
    group_split: dict[str, str] = {}

    def _meta(key: str, members: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        anchor = sorted(m["identity"] for m in members)[0]
        digest = hashlib.sha256(f"{SPLIT_SEED}:{anchor}".encode("utf-8")).hexdigest()
        ord_obs = sum(
            1
            for m in members
            if m.get("provenance") == "OBSERVED"
            and m.get("evidence_subtype") == "ORDINARY_DOMAIN_NONE"
        )
        pos_obs = sum(
            1
            for m in members
            if m.get("provenance") == "OBSERVED"
            and m.get("evidence_subtype") == "POSITIVE_EVIDENCE"
        )
        obs_n = sum(1 for m in members if m.get("provenance") == "OBSERVED")
        is_repair = any(
            "v5_remediate_surface_repair" in str(m.get("notes") or "")
            or "v5_remediate_punct" in str(m.get("notes") or "")
            or "v5_remediate_length" in str(m.get("notes") or "")
            or "v5_mixed_surface_repair" in str(m.get("notes") or "")
            for m in members
        )
        return {
            "anchor": anchor,
            "digest": digest,
            "is_repair": is_repair,
            "mod": int(digest[:8], 16) % 5,
            "obs_n": obs_n,
            "ord_obs": ord_obs,
            "pos_obs": pos_obs,
        }

    metas = {key: _meta(key, members) for key, members in components.items()}

    # Pass 1: default INFERRED / repair → mostly train; other OBSERVED → val-biased.
    for key, members in components.items():
        meta = metas[key]
        if meta["is_repair"] and meta["obs_n"] == 0:
            group_split[key] = "train"
        elif meta["ord_obs"] > 0 or meta["pos_obs"] > 0:
            # Tentative; reserved below.
            group_split[key] = "validation"
        elif meta["obs_n"] > 0:
            group_split[key] = "validation" if meta["mod"] <= 2 else "train"
        else:
            group_split[key] = "validation" if meta["mod"] == 0 else "train"

    # Pass 2: reserve train OBSERVED ordinary / PRESENT floors first (deterministic).
    ord_keys = sorted(
        (
            (-metas[k]["ord_obs"], metas[k]["anchor"], k)
            for k in components
            if metas[k]["ord_obs"] > 0
        )
    )
    reserved_ord = 0
    for _score, _anchor, key in ord_keys:
        if reserved_ord >= TRAIN_ORDINARY_OBSERVED_FLOOR:
            break
        group_split[key] = "train"
        reserved_ord += metas[key]["ord_obs"]

    pos_keys = sorted(
        (
            (-metas[k]["pos_obs"], metas[k]["anchor"], k)
            for k in components
            if metas[k]["pos_obs"] > 0
        )
    )
    reserved_pos = 0
    for _score, _anchor, key in pos_keys:
        if reserved_pos >= TRAIN_PRESENT_OBSERVED_FLOOR:
            break
        # Do not steal an ordinary-reserved component unless it also carries PRESENT.
        if group_split[key] == "train" and metas[key]["ord_obs"] > 0:
            reserved_pos += metas[key]["pos_obs"]
            continue
        group_split[key] = "train"
        reserved_pos += metas[key]["pos_obs"]

    def recount() -> dict[str, dict[str, int]]:
        counts = {s: {"train": 0, "validation": 0} for s in EVIDENCE_SUBTYPES}
        for key, members in components.items():
            split = group_split[key]
            for row in members:
                counts[str(row["evidence_subtype"])][split] += 1
        return counts

    def _support_counts() -> dict[str, int]:
        train_ord_obs = 0
        train_pos_obs = 0
        val_n = 0
        val_obs = 0
        ord_val_n = 0
        ord_val_obs = 0
        for key, members in components.items():
            split = group_split[key]
            for row in members:
                if split == "validation":
                    val_n += 1
                    if row.get("provenance") == "OBSERVED":
                        val_obs += 1
                    if row["evidence_subtype"] == "ORDINARY_DOMAIN_NONE":
                        ord_val_n += 1
                        if row.get("provenance") == "OBSERVED":
                            ord_val_obs += 1
                elif split == "train":
                    if row.get("provenance") == "OBSERVED":
                        if row["evidence_subtype"] == "ORDINARY_DOMAIN_NONE":
                            train_ord_obs += 1
                        if row["evidence_subtype"] == "POSITIVE_EVIDENCE":
                            train_pos_obs += 1
        return {
            "ord_val_n": ord_val_n,
            "ord_val_obs": ord_val_obs,
            "train_ord_obs": train_ord_obs,
            "train_pos_obs": train_pos_obs,
            "val_n": val_n,
            "val_obs": val_obs,
        }

    def _can_promote(key: str) -> bool:
        support = _support_counts()
        ord_loss = metas[key]["ord_obs"]
        pos_loss = metas[key]["pos_obs"]
        # Soft floors: never drop below min(configured floor, available/2).
        ord_floor = min(
            TRAIN_ORDINARY_OBSERVED_FLOOR,
            max(1, sum(metas[k]["ord_obs"] for k in components) // 2),
        )
        pos_floor = min(
            TRAIN_PRESENT_OBSERVED_FLOOR,
            max(1, sum(metas[k]["pos_obs"] for k in components) // 2),
        )
        if support["train_ord_obs"] - ord_loss < ord_floor:
            return False
        if support["train_pos_obs"] - pos_loss < pos_floor:
            return False
        return True

    # Pass 3: validation subtype floors — promote from train without breaching floors.
    for subtype in EVIDENCE_SUBTYPES:
        floor = VALIDATION_FLOORS[subtype]
        candidates = []
        for key, members in components.items():
            if group_split[key] != "train":
                continue
            if not any(str(m["evidence_subtype"]) == subtype for m in members):
                continue
            candidates.append((-metas[key]["obs_n"], metas[key]["anchor"], key))
        candidates.sort()
        for _obs, _anchor, key in candidates:
            counts = recount()
            if counts[subtype]["validation"] >= floor:
                break
            if not _can_promote(key):
                continue
            group_split[key] = "validation"

    # Pass 4: provenance fractions — promote non-reserved OBSERVED from train.
    for prefer_ordinary in (False, True):
        train_obs = []
        for key in components:
            if group_split[key] != "train":
                continue
            if metas[key]["obs_n"] <= 0:
                continue
            if prefer_ordinary:
                score = (-metas[key]["ord_obs"], -metas[key]["obs_n"], metas[key]["anchor"])
            else:
                score = (metas[key]["ord_obs"], -metas[key]["obs_n"], metas[key]["anchor"])
            train_obs.append((*score, key))
        train_obs.sort()
        for *_score, key in train_obs:
            support = _support_counts()
            val_frac = (support["val_obs"] / support["val_n"]) if support["val_n"] else 0.0
            ord_frac = (
                (support["ord_val_obs"] / support["ord_val_n"])
                if support["ord_val_n"]
                else 0.0
            )
            if val_frac >= 0.52 and ord_frac >= 0.52:
                break
            if not _can_promote(key):
                continue
            group_split[key] = "validation"

    rows: list[dict[str, Any]] = []
    witness = []
    for key, members in sorted(components.items()):
        split = group_split[key]
        for row in members:
            row = dict(row)
            row["split"] = split
            row["component_id"] = key
            rows.append(row)
        witness.append(
            {
                "component_id": key,
                "n": len(members),
                "observed_n": sum(1 for m in members if m.get("provenance") == "OBSERVED"),
                "split": split,
                "identities": [m["identity"] for m in members[:8]],
            }
        )
    rows.sort(key=lambda item: (item["evidence_subtype"], item["identity"]))
    return {
        "group_split": group_split,
        "rows": rows,
        "component_witness": witness,
        "support_floors": {
            "train_ordinary_observed_floor": TRAIN_ORDINARY_OBSERVED_FLOOR,
            "train_present_observed_floor": TRAIN_PRESENT_OBSERVED_FLOOR,
            **_support_counts(),
        },
    }


def prioritize_present_fills(
    hub_rows: Sequence[Mapping[str, Any]],
    *,
    blocked: set[str],
    per_priority_family: int = 70,
    per_other_family: int = 35,
) -> list[dict[str, Any]]:
    """Extra PRESENT prose for diagnosis-underrepresented families."""
    priority = set(PRESENT_SUPPORT_PRIORITY)
    # Two-pass: priority families first at higher density.
    first = make_prose_family_positives(
        [r for r in hub_rows if r.get("lineage") in priority],
        blocked=blocked,
        per_family=per_priority_family,
    )
    blocked2 = set(blocked) | {r["identity"] for r in first}
    second = make_prose_family_positives(
        hub_rows,
        blocked=blocked2,
        per_family=per_other_family,
    )
    return first + second


def parent_support_snapshot(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    train = [r for r in rows if r.get("split") == "train"]
    return {
        "ordinary_none_total": sum(
            1 for r in rows if r.get("evidence_subtype") == "ORDINARY_DOMAIN_NONE"
        ),
        "ordinary_none_train": sum(
            1 for r in train if r.get("evidence_subtype") == "ORDINARY_DOMAIN_NONE"
        ),
        "ordinary_none_train_observed": sum(
            1
            for r in train
            if r.get("evidence_subtype") == "ORDINARY_DOMAIN_NONE"
            and r.get("provenance") == "OBSERVED"
        ),
        "present_total": sum(
            1 for r in rows if r.get("evidence_subtype") == "POSITIVE_EVIDENCE"
        ),
        "present_train": sum(
            1 for r in train if r.get("evidence_subtype") == "POSITIVE_EVIDENCE"
        ),
        "present_train_observed": sum(
            1
            for r in train
            if r.get("evidence_subtype") == "POSITIVE_EVIDENCE"
            and r.get("provenance") == "OBSERVED"
        ),
    }


def _step(msg: str) -> None:
    import sys
    import time as _time

    print(f"[mixed-remediate {_time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def remediate_mixed_surface(
    *,
    prior_rows: Sequence[Mapping[str, Any]],
    hub_rows: Sequence[Mapping[str, Any]],
    observed_acquire_rows: Sequence[Mapping[str, Any]],
    blocked_ids: set[str],
    ontology: Sequence[str],
    embedding_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    parent_snap = parent_support_snapshot(prior_rows)
    stats = {
        "added": 0,
        "removed": 0,
        "reassigned": 0,
        "from_prior": 0,
        "from_hub_rebuild": 0,
        "from_observed_acquire": 0,
        "from_shared_vocab": 0,
        "from_present_priority_fills": 0,
        "parent_support": parent_snap,
    }
    _step(
        f"start prior={len(prior_rows)} hub={len(hub_rows)} "
        f"obs={len(observed_acquire_rows)} parent_ord_train_obs="
        f"{parent_snap['ordinary_none_train_observed']}"
    )

    working: list[dict[str, Any]] = []
    seen: set[str] = set(blocked_ids)

    # Keep V1R7 body (minus blocked); trim SHORT_ATOM mass slightly.
    prior_short = [
        dict(row)
        for row in prior_rows
        if row.get("evidence_subtype") == "SHORT_ATOM_NONE"
        and row.get("identity") not in blocked_ids
    ]
    prior_short = sorted(prior_short, key=lambda item: item["identity"])[:240]
    prior_other = [
        dict(row)
        for row in prior_rows
        if row.get("evidence_subtype") != "SHORT_ATOM_NONE"
        and row.get("identity") not in blocked_ids
    ]
    for item in prior_other + prior_short:
        # Drop prior split — reassigned after remediation.
        item = dict(item)
        item.pop("split", None)
        item.pop("component_id", None)
        if item["identity"] in seen:
            continue
        working.append(item)
        seen.add(item["identity"])
        stats["from_prior"] += 1

    from .classification_v5_stage_a_negative_evidence_surface import (
        _is_admissible_source_row,
        classify_hub_subtype,
    )
    from .classification_v5_surface_readiness_gates import tokens

    pos_union: set[str] = set()
    for row in hub_rows:
        if row.get("lineage") in ACTIVE_FAMILY_VOCABULARY and _is_admissible_source_row(row):
            pos_union |= tokens(str(row.get("text") or ""))
    for row in hub_rows:
        if not _is_admissible_source_row(row):
            continue
        lineage = row.get("lineage")
        if lineage == "ai-native":
            continue
        subtype = classify_hub_subtype(row, positive_token_union=pos_union)
        if subtype is None:
            continue
        try:
            example = build_example(row, subtype)
        except ValueError:
            continue
        if example["identity"] in seen or example["identity"] in blocked_ids:
            continue
        if subtype == "POSITIVE_EVIDENCE":
            example["topic_domain"] = str(lineage)
        working.append(example)
        seen.add(example["identity"])
        stats["from_hub_rebuild"] += 1

    observed_examples = make_observed_ordinary_rows(observed_acquire_rows)
    for example in observed_examples:
        if example["identity"] in seen or example["identity"] in blocked_ids:
            continue
        working.append(example)
        seen.add(example["identity"])
        stats["from_observed_acquire"] += 1
    _step(f"after OBSERVED acquire merge n={len(working)} +obs={stats['from_observed_acquire']}")

    present_fills = prioritize_present_fills(hub_rows, blocked=seen)
    working.extend(present_fills)
    stats["from_present_priority_fills"] = len(present_fills)
    stats["added"] += len(present_fills)
    for row in present_fills:
        seen.add(row["identity"])
    _step(f"present priority fills +{len(present_fills)} n={len(working)}")

    positives_now = [r for r in working if r["evidence_subtype"] == "POSITIVE_EVIDENCE"]
    shared = make_shared_vocab_negatives(positives_now, blocked=seen, per_family=14)
    working.extend(shared)
    stats["from_shared_vocab"] = len(shared)
    for row in shared:
        seen.add(row["identity"])
    _step(f"shared_vocab +{len(shared)} n={len(working)}")

    before = len(working)
    working = balance_lengths(working)
    stats["added"] += len(working) - before
    working = downsample_ai_native(working, max_share=0.30)
    working = select_to_floors(working)
    working = top_up_subtype_floors(working, blocked=seen, hub_rows=hub_rows)
    working = select_to_floors(working)
    _step(f"select_to_floors n={len(working)}")

    working, pair_records = pair_for_floors(working)
    working, dedupe_witness = dedupe_within_label(working)
    stats["removed"] += dedupe_witness["removed"]
    working, pair_records = pair_for_floors(working)

    working = stamp_source_buckets_mixed(working)
    working = enforce_source_cap(working, label="EVIDENCE_PRESENT", max_share=0.25)
    working = enforce_source_cap(working, label="NO_EVIDENCE", max_share=0.25)
    working = stamp_source_buckets_mixed(working)

    counts = Counter(r["evidence_subtype"] for r in working)
    if counts.get("ORDINARY_DOMAIN_NONE", 0) < ACQUISITION_FLOORS["ORDINARY_DOMAIN_NONE"]:
        need = ACQUISITION_FLOORS["ORDINARY_DOMAIN_NONE"] - counts.get(
            "ORDINARY_DOMAIN_NONE", 0
        )
        bank = ordinary_domain_fill_rows(blocked_ids=seen)
        for src in bank:
            if need <= 0:
                break
            ex = build_example(src, "ORDINARY_DOMAIN_NONE")
            if ex["identity"] in seen:
                continue
            working.append(ex)
            seen.add(ex["identity"])
            need -= 1
        working = stamp_source_buckets_mixed(working)

    working, pair_records = pair_for_floors(working)
    working = select_to_floors(working)
    working = top_up_subtype_floors(working, blocked=seen, hub_rows=hub_rows)
    working = balance_lengths(working)
    working = downsample_ai_native(working, max_share=0.30)
    working = select_to_floors(working)
    working = top_up_subtype_floors(working, blocked=seen, hub_rows=hub_rows)
    working, dedupe_witness2 = dedupe_within_label(working)
    stats["removed"] += dedupe_witness2["removed"]
    working = top_up_subtype_floors(working, blocked=seen, hub_rows=hub_rows)
    before_sb = len(working)
    working = repair_surface_balance(working)
    stats["added"] += len(working) - before_sb
    working, pair_records = pair_for_floors(working)
    working = stamp_source_buckets_mixed(working)
    working = enforce_source_cap(working, label="EVIDENCE_PRESENT", max_share=0.25)
    working = enforce_source_cap(working, label="NO_EVIDENCE", max_share=0.25)
    working = stamp_source_buckets_mixed(working)
    before_sb2 = len(working)
    working = repair_surface_balance(working)
    stats["added"] += len(working) - before_sb2
    working = stamp_source_buckets_mixed(working)
    _step(f"pre-component n={len(working)} pairs={len(pair_records)}")

    components = build_near_dup_components(working)
    _step(f"components={len(components)}")
    split_result = assign_component_splits_mixed(components)
    rows = split_result["rows"]
    stats["reassigned"] = len(rows)
    final_snap = parent_support_snapshot(rows)
    stats["final_support"] = final_snap
    stats["present_train_support_change"] = (
        final_snap["present_train"] - parent_snap["present_train"]
    )
    stats["ordinary_none_train_support_change"] = (
        final_snap["ordinary_none_train"] - parent_snap["ordinary_none_train"]
    )
    stats["ordinary_none_train_observed_change"] = (
        final_snap["ordinary_none_train_observed"]
        - parent_snap["ordinary_none_train_observed"]
    )
    stats["present_train_observed_change"] = (
        final_snap["present_train_observed"] - parent_snap["present_train_observed"]
    )
    _step(
        f"split n={len(rows)} train_ord_obs={final_snap['ordinary_none_train_observed']} "
        f"train_pos_obs={final_snap['present_train_observed']}"
    )

    readiness = evaluate_surface_readiness(
        rows,
        pair_records=pair_records,
        ontology=ontology,
        blocked={i: "spent" for i in blocked_ids},
        embedding_report=embedding_report,
    )
    _step(
        f"readiness state={readiness.get('state')} "
        f"missing={sorted((readiness.get('missing_evidence') or {}).keys())}"
    )

    dataset_lines = [canonical_json(row) for row in rows]
    dataset_body = "\n".join(dataset_lines) + ("\n" if dataset_lines else "")
    dataset_sha = sha256_text(dataset_body)

    split_manifest = {
        "schema": "hyperlex.classification.v5.evidence_split_manifest.v1r8",
        "splits": {
            "train": sorted(r["identity"] for r in rows if r["split"] == "train"),
            "validation": sorted(r["identity"] for r in rows if r["split"] == "validation"),
        },
        "surface_rule": SURFACE_RULE_V1R8,
    }
    split_manifest["manifest_sha256"] = sha256_text(
        canonical_json({k: v for k, v in split_manifest.items() if k != "manifest_sha256"})
    )

    train_contract = {
        **STAGE_A_TRAIN_CONTRACT,
        "preregistered": True,
        "surface_dataset_sha256": dataset_sha,
        "surface_ready": readiness["state"] == "READY",
        "surface_rule": SURFACE_RULE_V1R8,
        "train_authorized": False,
    }
    train_contract["contract_sha256"] = sha256_text(
        canonical_json({k: v for k, v in train_contract.items() if k != "contract_sha256"})
    )

    # Source / domain balance witnesses for settlement.
    train_rows = [r for r in rows if r["split"] == "train"]
    ordinary_train = [
        r for r in train_rows if r["evidence_subtype"] == "ORDINARY_DOMAIN_NONE"
    ]
    source_balance = {
        "class_x_source": {
            label: dict(Counter(r.get("source_bucket") for r in rows if r["evidence_label"] == label))
            for label in ("EVIDENCE_PRESENT", "NO_EVIDENCE", "UNCERTAIN")
        },
        "ordinary_train_source": dict(Counter(r.get("source_bucket") for r in ordinary_train)),
        "ordinary_wiki_share_among_ordinary_observed": (
            (
                sum(
                    1
                    for r in rows
                    if r["evidence_subtype"] == "ORDINARY_DOMAIN_NONE"
                    and r.get("provenance") == "OBSERVED"
                    and str(r.get("source_bucket") or "").startswith("v5_src_wik_")
                )
                / max(
                    1,
                    sum(
                        1
                        for r in rows
                        if r["evidence_subtype"] == "ORDINARY_DOMAIN_NONE"
                        and r.get("provenance") == "OBSERVED"
                    ),
                )
            )
        ),
        "subtype_x_domain": {
            subtype: dict(
                Counter(
                    r.get("topic_domain")
                    for r in rows
                    if r["evidence_subtype"] == subtype
                )
            )
            for subtype in ("ORDINARY_DOMAIN_NONE", "POSITIVE_EVIDENCE")
        },
    }

    receipt = {
        "BEST": "UNCHANGED",
        "best_sha256": BEST_SHA,
        "dataset_sha256": dataset_sha,
        "design_rule": DESIGN_RULE,
        "diagnosis_receipt_sha256": DIAGNOSIS_RECEIPT_SHA,
        "gate_pass": readiness["gate_pass"],
        "gate_rule": GATE_RULE,
        "gates": frozen_readiness_gates(),
        "missing_evidence": readiness.get("missing_evidence") or {},
        "model_acceptance_gates_separate": readiness["model_acceptance_gates_separate"],
        "n": len(rows),
        "parent_diagnosis": PARENT_DIAGNOSIS,
        "parent_surface_dataset_sha256": PARENT_SURFACE_SHA,
        "provenance_association": "OBSERVED",
        "provenance_causality": "NOT_ESTABLISHED",
        "readiness_details": readiness.get("details"),
        "remediate_rule": REMEDIATE_RULE,
        "remediation_stats": stats,
        "schema": "hyperlex.classification.v5.evidence_surface_readiness.v1r8",
        "selected_checkpoint_sha256": SELECTED_CHECKPOINT_SHA,
        "source_balance": source_balance,
        "split_support_floors": split_result.get("support_floors"),
        "stage_a_train_contract": train_contract,
        "state": readiness["state"],
        "surface_rule": SURFACE_RULE_V1R8,
        "train": False,
    }
    receipt["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in receipt.items() if k != "receipt_sha256"})
    )

    return {
        "component_witness": split_result["component_witness"],
        "dataset_body": dataset_body,
        "dataset_sha256": dataset_sha,
        "dedupe_witness": dedupe_witness,
        "pair_records": pair_records,
        "readiness": readiness,
        "receipt": receipt,
        "remediation_stats": stats,
        "rows": rows,
        "source_balance": source_balance,
        "split_manifest": split_manifest,
        "split_support_floors": split_result.get("support_floors"),
        "stage_a_train_contract": train_contract,
    }
