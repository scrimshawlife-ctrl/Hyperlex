"""Classification v4 — balanced fresh reserve acquisition contracts.

Preregisters balance floors before any fetch. Pins spent v2 + spent v3 + v3
evidence surface as permanent exclusions. Does not train, does not retune
thresholds, does not score a reserve, and does not move BEST.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Mapping, Sequence

from .classification_v2 import ACTIVE_FAMILY_VOCABULARY
from .classification_v3_reserve import BEST_SHA, SPENT_V2_ROWS_SHA, SURFACE_DATASET_SHA
from .holdout_guard import normalized_text_sha256

ACQUIRE_RULE = "HYPERLEX_CLASSIFICATION_V4_BALANCED_RESERVE_ACQUIRE_V1"
PARENT_RULE = "HYPERLEX_CLASSIFICATION_V3_EVIDENCE_GATE"
SPENT_V3_ROWS_SHA = (
    "abb8bf22012bb450dba05ce3129e32c2f28fabe9911030b28c68c5b99d39b937"
)
SPENT_V3_MANIFEST_SHA = (
    "4a13d7a76352fd0e0008a0b3f36ca2976876c945896e28c945be00f4cabc2ef5"
)
SPENT_V3_RECEIPT_SHA = (
    "61daa47383bb8c711476a3c4100b55897e1099687c5eca869e19d9130fd914ec"
)

# Preregistered before fetch. Not fitted from spent v3 reserve metrics.
BALANCE_FLOORS = {
    "max_single_family_share_of_present": 0.20,
    "min_distinct_active_families": 12,
    "min_n": 120,
    "min_none": 40,
    "min_per_covered_family": 3,
    "min_present": 80,
}

# Per-family discovery caps used by the fetcher (also preregistered).
DISCOVERY_PER_FAMILY = 8
DISCOVERY_NONE = 48

# Sense-label arguments → forward family (unique match only).
FAMILY_SENSE_LABELS: dict[str, tuple[str, ...]] = {
    "ai-native": ("artificial intelligence",),
    "betting-sharp": ("betting", "gambling"),
    "crypto-degen": ("cryptocurrency",),
    "gaming-meta": ("gaming", "video game", "video games"),
    "internet-slang": ("internet slang", "reddit slang", "2channel slang"),
    "memetic": ("meme",),
    "social-evaluation": ("honorific", "derogatory", "endearing"),
    "relationship-dating": ("dating",),
    "conflict-aggression": (
        "military",
        "military slang",
        "military ranks",
        "naval slang",
    ),
    "technology-ai": (
        "programming",
        "software",
        "computer science",
        "software engineering",
        "computer hardware",
        "computer security",
    ),
    "workplace-career": ("business",),
    "sports-competition": ("sports", "ball games", "winter sports", "water sports"),
    "music-entertainment": ("music", "film", "television", "music industry"),
    "fashion-aesthetic": ("fashion", "clothing", "aesthetic"),
    "regional-cultural": (
        "southern us",
        "cockney",
        "african-american vernacular",
        "scottish",
        "yorkshire",
        "australian",
        "indian english",
        "ireland",
        "new zealand",
    ),
    "spiritual-mystic": (
        "occult",
        "mysticism",
        "astrology",
        "wicca",
        "paganism",
        "spiritualism",
    ),
    "identity-affiliation": (
        "demonym",
        "lgbtq slang",
        "gay slang",
        "transgender slang",
        "ethnic slur",
    ),
    "politics-civic": ("politics", "government", "political science", "geopolitics"),
}

# Ordinary-domain labels that authorize NO_EVIDENCE / HARD_NONE candidates.
NONE_SENSE_LABELS: tuple[str, ...] = (
    "botany",
    "chemistry",
    "ornithology",
    "meteorology",
    "geology",
    "mathematics",
    "anatomy",
    "zoology",
)


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def acquire_contract() -> dict[str, Any]:
    return {
        "balance_floors": dict(BALANCE_FLOORS),
        "best": "UNCHANGED",
        "best_sha256": BEST_SHA,
        "discovery_none": DISCOVERY_NONE,
        "discovery_per_family": DISCOVERY_PER_FAMILY,
        "family_sense_labels": {
            family: list(labels) for family, labels in FAMILY_SENSE_LABELS.items()
        },
        "none_sense_labels": list(NONE_SENSE_LABELS),
        "parent_rule": PARENT_RULE,
        "recalibrate": False,
        "rule": ACQUIRE_RULE,
        "score_reserve": False,
        "spent_v2_reserve_reuse": False,
        "spent_v3_reserve_reuse": False,
        "spent_v2_rows_sha256": SPENT_V2_ROWS_SHA,
        "spent_v3_manifest_sha256": SPENT_V3_MANIFEST_SHA,
        "spent_v3_receipt_sha256": SPENT_V3_RECEIPT_SHA,
        "spent_v3_rows_sha256": SPENT_V3_ROWS_SHA,
        "surface_dataset_sha256": SURFACE_DATASET_SHA,
        "train": False,
    }


def normalize_label(argument: str) -> str:
    return " ".join(str(argument or "").casefold().split())


def family_for_sense_labels(arguments: Sequence[str]) -> dict[str, Any]:
    """Map whole sense-label arguments to at most one forward family."""
    tokens = [normalize_label(item) for item in arguments if str(item or "").strip()]
    hits: list[str] = []
    for family, labels in FAMILY_SENSE_LABELS.items():
        wanted = {normalize_label(label) for label in labels}
        if any(token in wanted for token in tokens):
            hits.append(family)
    if len(hits) == 1:
        return {"status": "unique", "family": hits[0]}
    if len(hits) > 1:
        return {"status": "ambiguous", "family": None, "families": hits}
    none_hits = [token for token in tokens if token in {normalize_label(x) for x in NONE_SENSE_LABELS}]
    if none_hits and not hits:
        return {"status": "none", "family": None, "none_labels": none_hits}
    return {"status": "absent", "family": None}


def build_acquire_row(source: Mapping[str, Any]) -> dict[str, Any]:
    text = str(source["text"]).strip()
    if not text:
        raise ValueError("empty_acquire_text")
    identity = normalized_text_sha256(text)
    lineage = str(source["lineage"])
    if lineage in ACTIVE_FAMILY_VOCABULARY:
        evidence_label = "EVIDENCE_PRESENT"
        evidence_subtype = "POSITIVE_EVIDENCE"
        gold_decision_type = "FAMILY"
        gold_family = lineage
        candidate_families = [lineage]
    elif lineage == "none":
        evidence_label = "NO_EVIDENCE"
        evidence_subtype = str(source.get("evidence_subtype") or "HARD_NONE")
        if evidence_subtype not in {"HARD_NONE", "NEAR_DOMAIN_NONE", "GENERIC_NONE"}:
            raise ValueError(f"none_subtype_invalid:{evidence_subtype}")
        gold_decision_type = "NONE"
        gold_family = None
        candidate_families = []
    else:
        raise ValueError(f"lineage_not_admissible:{lineage}")
    return {
        "candidate_families": candidate_families,
        "class": source["class"],
        "evidence_label": evidence_label,
        "evidence_subtype": evidence_subtype,
        "gold_decision_type": gold_decision_type,
        "gold_family": gold_family,
        "identity": identity,
        "lineage": lineage,
        "normalized_text_sha256": identity,
        "provenance": source["class"],
        "revision_id": source.get("revision_id"),
        "revision_sha1": source.get("revision_sha1"),
        "revision_timestamp": source.get("revision_timestamp"),
        "rights": source.get("rights") or "CC-BY-SA",
        "source_url": source.get("source_url"),
        "split": "reserve_acquire",
        "text": text,
        "title": source.get("title"),
    }


def audit_balance(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    lineage_counts = Counter(str(row["lineage"]) for row in rows)
    n = len(rows)
    n_none = int(lineage_counts.get("none", 0))
    present_counts = {
        family: count
        for family, count in lineage_counts.items()
        if family in ACTIVE_FAMILY_VOCABULARY
    }
    n_present = sum(present_counts.values())
    distinct = sorted(present_counts)
    max_share = 0.0
    dominant = None
    if n_present:
        dominant, top = max(present_counts.items(), key=lambda item: (item[1], item[0]))
        max_share = top / n_present
    under_min = sorted(
        family
        for family, count in present_counts.items()
        if count < BALANCE_FLOORS["min_per_covered_family"]
    )
    reasons: list[str] = []
    if n < BALANCE_FLOORS["min_n"]:
        reasons.append(f"min_n:{n}<{BALANCE_FLOORS['min_n']}")
    if n_none < BALANCE_FLOORS["min_none"]:
        reasons.append(f"min_none:{n_none}<{BALANCE_FLOORS['min_none']}")
    if n_present < BALANCE_FLOORS["min_present"]:
        reasons.append(f"min_present:{n_present}<{BALANCE_FLOORS['min_present']}")
    if len(distinct) < BALANCE_FLOORS["min_distinct_active_families"]:
        reasons.append(
            "min_distinct_active_families:"
            f"{len(distinct)}<{BALANCE_FLOORS['min_distinct_active_families']}"
        )
    if max_share > BALANCE_FLOORS["max_single_family_share_of_present"]:
        reasons.append(
            "max_single_family_share_of_present:"
            f"{max_share:.4f}>{BALANCE_FLOORS['max_single_family_share_of_present']}"
            f":{dominant}"
        )
    if under_min:
        reasons.append(f"min_per_covered_family:{','.join(under_min)}")
    return {
        "balance_pass": not reasons,
        "dominant_family": dominant,
        "lineage_counts": dict(sorted(lineage_counts.items())),
        "max_single_family_share_of_present": max_share,
        "n": n,
        "n_distinct_active_families": len(distinct),
        "n_none": n_none,
        "n_present": n_present,
        "reasons": reasons,
        "under_min_per_family": under_min,
    }


def validate_acquire_disjointness(
    rows: Sequence[Mapping[str, Any]],
    *,
    blocked_ids: Mapping[str, str],
) -> list[str]:
    reasons: list[str] = []
    identities = [str(row["identity"]) for row in rows]
    if len(identities) != len(set(identities)):
        reasons.append("duplicate_acquire_identities")
    overlaps: Counter[str] = Counter()
    for identity in identities:
        reason = blocked_ids.get(identity)
        if reason:
            overlaps[reason] += 1
    for reason, count in sorted(overlaps.items()):
        reasons.append(f"blocked_overlap:{reason}:{count}")
    if not rows:
        reasons.append("empty_acquire")
    return reasons


def decide_acquire_disposition(
    *,
    invalid_reasons: Sequence[str],
    balance: Mapping[str, Any],
) -> dict[str, Any]:
    if invalid_reasons:
        return {
            "disposition": "ACQUIRE_INVALID",
            "balance_pass": False,
            "reasons": list(invalid_reasons),
            "seal_authorized": False,
        }
    if balance.get("balance_pass"):
        return {
            "disposition": "ACQUIRE_READY",
            "balance_pass": True,
            "reasons": ["balance_floors_met"],
            "seal_authorized": True,
        }
    return {
        "disposition": "ACQUIRE_QUOTA_UNFILLED",
        "balance_pass": False,
        "reasons": list(balance.get("reasons") or []),
        "seal_authorized": False,
    }


def next_action_for_acquire_disposition(disposition: Mapping[str, Any]) -> str:
    name = disposition.get("disposition")
    if name == "ACQUIRE_READY":
        return (
            "BALANCED_RESERVE_ACQUIRE_READY — freeze acquire rows as the fresh "
            "promotion reserve pool; do not score until a new evidence-gate climb "
            "authorizes one-shot eval; BEST unchanged."
        )
    if name == "ACQUIRE_QUOTA_UNFILLED":
        return (
            "CONTINUE_ACQUIRE — expand Wiktionary discovery under the same frozen "
            "floors; do not relax floors; do not score spent reserves; do not move BEST."
        )
    return (
        "ACQUIRE_INVALID — fix isolation/provenance/duplicate failure; "
        "do not treat balance metrics as the failure mode; do not move BEST."
    )


def assemble_acquire_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    receipt = {
        "BEST": "UNCHANGED",
        "audit_state": {
            "authorization": "AUTHORIZE_BALANCED_FRESH_RESERVE_ACQUIRE",
            "best_moved": False,
            "recalibrated": False,
            "reserve_scored": False,
            "thresholds_changed": False,
            "train": False,
        },
        "balance": payload["balance"],
        "best_sha256": BEST_SHA,
        "contract": acquire_contract(),
        "disposition": payload["disposition"],
        "next_action": payload["next_action"],
        "rows_sha256": payload["rows_sha256"],
        "rule": ACQUIRE_RULE,
        "schema": "hyperlex.classification.v4.balanced_reserve_acquire.v1",
        "spent_v3_rows_sha256": SPENT_V3_ROWS_SHA,
        "surface_dataset_sha256": SURFACE_DATASET_SHA,
    }
    receipt["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in receipt.items() if k != "receipt_sha256"})
    )
    return receipt
