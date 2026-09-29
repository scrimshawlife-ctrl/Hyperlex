"""SELECT-006 reserve acquisition policy.

This module freezes floors and checks surfaces. It does not train, bind a
ledger, or assign OBSERVED, semantic family, or unbind_clean.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from .layout import FAMILIES
from .select_006_efficiency_preservation import (
    EPSILON,
    EXPERIMENT_ID,
    vocabulary_expansion_pin,
)

SELECT_005_ID = "HLX-EXP-2026-09-27-SELECT-005"
TRANSITION = "SELECT_006_RESERVE_ACQUISITION"
BATCH_ID = "HLX-EVAL-RESERVE-SELECT-006-001"
HEAD_MAPPED_FAMILIES = tuple(
    name for name in FAMILIES if name != "none"
)
# Production-head families that are also active evaluation families.
# Legacy head names are not aliases.
COMPUTABLE_HEAD_FAMILIES = (
    "ai-native",
    "betting-sharp",
    "crypto-degen",
    "gaming-meta",
)
DISCOVERY_CATEGORIES = (
    "Category:English internet slang",
    "Category:English slang",
    "Category:English idioms",
    "Category:English gaming slang",
    "Category:English cryptocurrency",
    "Category:English poker terms",
)
DISCOVERY_PER_CATEGORY = 8
FLOORS = {
    "classify": 1,
    "classify_non_none": 1,
    "classify_observed": 1,
    "head_mapped_non_none": 1,
    "unbind_clean": 1,
}
FAILURE_SOURCE = "RESERVE_SOURCE_FAILURE"
FAILURE_RIGHTS = "RESERVE_RIGHTS_FAILURE"
FAILURE_PROVENANCE = "RESERVE_PROVENANCE_FAILURE"
FAILURE_ISOLATION = "RESERVE_ISOLATION_FAILURE"
FAILURE_SURFACE = "RESERVE_METRIC_SURFACE_INSUFFICIENT"
FAILURE_REVIEW = "REVIEW_SURFACE_EMPTY"
FAILURE_SETTLEMENT = "SETTLEMENT_FAILURE"
FAILURE_ROUTING = "ROUTING_FAILURE"
FAILURE_QUOTA = "RESERVE_QUOTA_UNFILLED"
FAILURE_BINDING = "LEDGER_BINDING_CONFLICT"
FAILURE_REPLAY = "LEDGER_REPLAY_FAILURE"
_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")
_LINK = re.compile(r"\[\[([^|\]]+\|)?([^\]]+)\]\]")
_MARKUP = re.compile(r"''+")


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def frozen_floors() -> dict[str, Any]:
    """Minimum computable surface. Written before any page is fetched."""
    return {
        "admission_floor_authority": (
            "Admission requires each active slice count to be at least 1. "
            "Planning targets are not that floor."
        ),
        "computable_head_families": list(COMPUTABLE_HEAD_FAMILIES),
        "discovery_categories": list(DISCOVERY_CATEGORIES),
        "discovery_per_category": DISCOVERY_PER_CATEGORY,
        "discovery_rule": "api_order_multiword_titles_not_previously_used",
        "epsilon_unchanged": EPSILON,
        "experiment_id": EXPERIMENT_ID,
        "floors": dict(FLOORS),
        "head_mapped_non_none_reason": (
            "classify_macro_f1_nonnone is computable only when at least one "
            "gold lineage is a production-head family other than none. "
            "A classify_non_none slice count can still map to head none."
        ),
        "schema": "hyperlex.select_006_reserve_floors.v1",
        "select_005_counts_not_transferred": [51, 11, 11, 27],
        "select_005_reserve_reuse": "FORBIDDEN",
        "source_families": ["wiktionary_multiword_lemma", "wiktionary_sense_gloss"],
    }


def execution_loader_status() -> str:
    return str(vocabulary_expansion_pin()["execution_loader_status"])


def _strip_templates(text: str) -> str:
    previous = None
    current = text
    while current != previous:
        previous = current
        current = _TEMPLATE.sub(" ", current)
    return current


def extract_primary_gloss(wikitext: str) -> dict[str, str | None]:
    """English primary definition prose. Topic labels inside templates are dropped."""
    if not wikitext or wikitext.lstrip().lower().startswith("#redirect"):
        return {"exact_gloss": None, "part_of_speech": None}
    english = _english_section(wikitext)
    if not english:
        return {"exact_gloss": None, "part_of_speech": None}
    pos = None
    for line in english.splitlines():
        heading = re.fullmatch(r"=+\s*([^=]+?)\s*=+", line.strip())
        if heading and line.strip().startswith("==="):
            pos = heading.group(1).strip()
        if line.startswith("# ") and not line.startswith("#:") and not line.startswith("##"):
            prose = _prose(line[2:])
            if prose:
                return {"exact_gloss": prose, "part_of_speech": pos}
    return {"exact_gloss": None, "part_of_speech": pos}


def _english_section(wikitext: str) -> str:
    parts = re.split(r"\n(?===[^=])", "\n" + wikitext)
    for part in parts:
        lines = part.strip().splitlines()
        if not lines:
            continue
        title = lines[0].strip("= ").casefold()
        if title == "english":
            return part
    return ""


def _prose(line: str) -> str:
    text = _strip_templates(line)
    text = _LINK.sub(lambda match: match.group(2), text)
    text = _MARKUP.sub("", text)
    text = text.replace("'''", "").replace("''", "")
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text


def review_surface_row(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Blind row. No quota, route, score, or semantic-family field."""
    return {
        "candidate_id": raw["candidate_id"],
        "exact_gloss": raw.get("exact_gloss"),
        "headword": raw["headword"],
        "page_url": raw["page_url"],
        "part_of_speech": raw.get("part_of_speech"),
        "revision_id": raw["revision_id"],
        "sense_labels": None,
        "source_family": raw["source_family"],
        "source_lemma_tokens": list(raw.get("source_lemma_tokens") or []),
    }


def blind_surface_errors(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    banned = {
        "attest",
        "decision",
        "desired_family",
        "model_score",
        "prediction",
        "quota",
        "routing_status",
        "semantic_family",
        "slice",
        "slices",
        "unbind_clean",
    }
    errors = []
    for row in rows:
        found = banned & set(row)
        if found:
            errors.append("review surface carries " + ",".join(sorted(found)))
    return errors


def exclusion_reason(digest: str, blocked: Mapping[str, str]) -> str | None:
    reason = blocked.get(digest)
    return reason or None


def metric_surface(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Count eligible slices and whether each sealed metric can be computed."""
    counts = {
        "classify": 0,
        "classify_non_none": 0,
        "classify_observed": 0,
        "unbind_clean": 0,
    }
    head_mapped = 0
    for record in records:
        if record.get("routing_status") != "ELIGIBLE":
            continue
        for name in record.get("slices") or []:
            if name in counts:
                counts[name] += 1
        lineage = str(record.get("lineage") or "")
        if (
            record.get("task") == "classify"
            and lineage in COMPUTABLE_HEAD_FAMILIES
            and lineage in HEAD_MAPPED_FAMILIES
        ):
            head_mapped += 1
    computable = {
        "classification_accuracy": counts["classify"] >= 1,
        "classify_macro_f1_nonnone": head_mapped >= 1,
        "observed_label_accuracy": counts["classify_observed"] >= 1,
        "unbind_clean_exact": counts["unbind_clean"] >= 1,
    }
    floors_met = all(counts[key] >= FLOORS[key] for key in counts) and head_mapped >= FLOORS["head_mapped_non_none"]
    return {
        "computable": computable,
        "floors_met": floors_met,
        "head_mapped_non_none": head_mapped,
        "slice_counts": counts,
    }


def forbidden_training() -> dict[str, Any]:
    return {
        "best_changed": False,
        "epochs": 0,
        "execution_loader_status": execution_loader_status(),
        "gradient_steps": 0,
        "optimizer_constructed": False,
        "training_launch_authorized": False,
        "training_started": False,
        "weights_mutated": False,
    }
