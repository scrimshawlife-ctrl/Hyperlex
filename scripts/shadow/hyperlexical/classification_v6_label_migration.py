"""Deterministic V6 label migration under HYPERLEX_V6_FAMILY_ONTOLOGY_V1_FINAL.

Materializes domain_labels[] / function_labels[] / mediation_labels[] /
ontology_uncertainty. Does not train. Does not touch QUAL.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from .classification_v6_human_ontology_settlement import (
    AI_CUES,
    DOMAIN_CUES,
    FUNCTION_CUES,
    MEDIATION_CUES,
    _has_cues,
)
from .classification_v6_human_ontology_settlement import final_migration_map

_TOKEN = re.compile(r"[a-z0-9']{2,}")

DOMAIN_IDS = {
    "gaming": "domain.gaming",
    "gambling_betting": "domain.gambling",
    "crypto_markets": "domain.crypto",
    "sports": "domain.sports",
    "entertainment_media": "domain.entertainment",
    "fashion_style": "domain.fashion",
    "workplace": "domain.workplace",
    "politics_civic": "domain.politics",
    "spiritual_esoteric": "domain.spiritual",
    "technology": "domain.technology",
    "ai_discourse": "domain.technology.ai_discourse",
}

FUNCTION_IDS = {
    "evaluative_stance": "function.evaluative_stance",
    "relational_intimacy": "function.relational_intimacy",
    "conflictive_force": "function.conflictive_force",
    "memetic_form": "function.memetic_form",
}


def _direct_map_old_family(fam: str) -> dict[str, list[str]]:
    mmap = {
        m["old_label"]: m
        for m in final_migration_map(
            {"identity_affiliation": {"decision": "CONTEXT_ONLY"}}
        )
    }
    m = mmap.get(fam)
    if not m:
        return {"domain": [], "function": [], "mediation": [], "type": "UNUSABLE"}
    return {
        "domain": list(m.get("domain") or []),
        "function": list(m.get("function") or []),
        "mediation": list(m.get("mediation") or []),
        "type": m["mapping_type"],
        "human_review": bool(m.get("human_review_requirement")),
    }


def migrate_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Produce V6 multi-label fields for one foundation row."""
    text = str(row.get("text") or "")
    label = str(row.get("evidence_label") or "")
    fam = row.get("gold_family")
    out = {
        "identity": row.get("identity"),
        "text": text,
        "split": row.get("split"),
        "evidence_label": label,
        "legacy_gold_family": fam,
        "domain_labels": [],
        "function_labels": [],
        "mediation_labels": [],
        "ontology_uncertainty": None,
        "migration_type": None,
        "hierarchy_repaired": False,
        "human_resettlement_required": False,
        "schema": "hyperlex.classification.v6.migrated_row.v1",
    }
    if label != "EVIDENCE_PRESENT":
        out["migration_type"] = "DIRECT"
        out["ontology_uncertainty"] = (
            "INSUFFICIENT_CONTEXT" if label == "UNCERTAIN" else None
        )
        return out

    mapped = _direct_map_old_family(str(fam or ""))
    out["migration_type"] = mapped["type"]
    domains = list(mapped["domain"])
    functions = list(mapped["function"])
    mediation = list(mapped["mediation"])

    if mapped["type"] == "DEPRECATED":
        if fam == "regional-cultural":
            out["ontology_uncertainty"] = None
            out["domain_labels"] = []
            out["function_labels"] = []
            out["mediation_labels"] = []
            out["migration_type"] = "DEPRECATED"
            return out
        if fam == "identity-affiliation":
            out["human_resettlement_required"] = True
            out["ontology_uncertainty"] = "ONTOLOGY_BOUNDARY_UNCLEAR"
            out["migration_type"] = "HUMAN_REQUIRED"
            return out

    if mapped["type"] == "RULE_DERIVED":
        if fam == "betting-sharp":
            if not _has_cues(text, DOMAIN_CUES["gambling_betting"]):
                out["human_resettlement_required"] = True
                out["ontology_uncertainty"] = "ONTOLOGY_BOUNDARY_UNCLEAR"
                out["migration_type"] = "HUMAN_REQUIRED"
                return out
        if fam == "crypto-degen":
            if not _has_cues(
                text,
                ("crypto", "bitcoin", "ethereum", "blockchain", "defi", "nft", "airdrop"),
            ):
                out["human_resettlement_required"] = True
                out["ontology_uncertainty"] = "ONTOLOGY_BOUNDARY_UNCLEAR"
                out["migration_type"] = "HUMAN_REQUIRED"
                return out

    # Enrich with text-evident co-labels (multi-label naturalness) without inventing gold
    # Only add labels when cues fire AND legacy family already maps into that axis family
    # — keep enrichment conservative: add mediation/internet if cues; add AI child if AI cues
    if _has_cues(text, MEDIATION_CUES):
        if "mediation.internet_register" not in mediation:
            mediation.append("mediation.internet_register")
            if out["migration_type"] == "DIRECT":
                out["migration_type"] = "MULTI_LABEL"
    if _has_cues(text, AI_CUES):
        if "domain.technology" not in domains:
            domains.append("domain.technology")
        if "domain.technology.ai_discourse" not in domains:
            domains.append("domain.technology.ai_discourse")
            out["migration_type"] = "MULTI_LABEL"

    # Hierarchy constraint repair: ai_discourse requires technology
    if "domain.technology.ai_discourse" in domains and "domain.technology" not in domains:
        domains.append("domain.technology")
        out["hierarchy_repaired"] = True

    # Cross-axis co-labels from strong cues only when already PRESENT
    for fname, cues in FUNCTION_CUES.items():
        fid = FUNCTION_IDS[fname]
        if _has_cues(text, cues) and fid not in functions:
            # only auto-add if legacy family was function-adjacent or same cue family
            if fam in {
                "social-evaluation",
                "relationship-dating",
                "conflict-aggression",
                "memetic",
            } or (
                fname == "evaluative_stance" and fam == "social-evaluation"
            ):
                functions.append(fid)
                out["migration_type"] = "MULTI_LABEL"

    out["domain_labels"] = sorted(set(domains))
    out["function_labels"] = sorted(set(functions))
    out["mediation_labels"] = sorted(set(mediation))
    if (
        len(out["domain_labels"]) + len(out["function_labels"]) >= 2
        and not out["ontology_uncertainty"]
    ):
        out["ontology_uncertainty"] = "MULTI_LABEL_POSITIVE"
    return out


def hierarchy_violation(domain_labels: list[str]) -> bool:
    return (
        "domain.technology.ai_discourse" in domain_labels
        and "domain.technology" not in domain_labels
    )


# Vocabularies for model heads (fixed order)
DOMAIN_VOCAB = [
    "domain.gaming",
    "domain.gambling",
    "domain.crypto",
    "domain.sports",
    "domain.entertainment",
    "domain.fashion",
    "domain.workplace",
    "domain.politics",
    "domain.spiritual",
    "domain.technology",
    "domain.technology.ai_discourse",
]
FUNCTION_VOCAB = [
    "function.evaluative_stance",
    "function.relational_intimacy",
    "function.conflictive_force",
    "function.memetic_form",
]
MEDIATION_VOCAB = ["mediation.internet_register"]
