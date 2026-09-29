"""SELECT-006 reserve acquisition v2 policy.

This module checks the sealed label rule. It does not fetch, settle, or train.
"""

from __future__ import annotations

import re
from typing import Any

from .select_006_reserve_source_design_v2 import (
    DIRECT_LABELS,
    TARGET_FAMILIES,
    definition_prose,
    named_target_family,
    normalize_label,
    sense_label_arguments,
)

DESIGN_PINS = {
    "FUTURE_ACQUISITION_CONTRACT.json": "acf8b802c9ff8a3a99ef68587d89f4dc87cb522d861e158c1cdccf4e208dd740",
    "HEAD_MAPPING_WITNESS.json": "0453c63b90dd5d188557feaad2b95f8dbbcadd101a0b1e1c272b2fa8675118dc",
    "SOURCE_DESIGN_V2.json": "7e9c323ea4fb6683f160f548f66bc517876cbb64d6fce55e1cf6a691333d0e99",
    "SOURCE_RIGHTS_PROVENANCE_POLICY.json": "e28d0f0f536423efe2ca234e1a485d0d706812d14bf6d1ab85062cc475f2a56b",
}
PIN_MISMATCH = "SOURCE_DESIGN_PIN_MISMATCH"
FETCH_FAILURE = "SOURCE_FETCH_FAILURE"
RIGHTS_FAILURE = "SOURCE_RIGHTS_FAILURE"
PROVENANCE_FAILURE = "SOURCE_PROVENANCE_FAILURE"
LABEL_AMBIGUOUS = "SOURCE_LABEL_AMBIGUOUS"
LABEL_NOT_AUTHORIZED = "SOURCE_LABEL_NOT_AUTHORIZED"
ISOLATION_FAILURE = "SOURCE_ISOLATION_FAILURE"
REVIEW_EMPTY = "REVIEW_SURFACE_EMPTY"
SETTLEMENT_FAILURE = "SETTLEMENT_FAILURE"
ROUTING_FAILURE = "ROUTING_FAILURE"
QUOTA_UNFILLED = "RESERVE_QUOTA_UNFILLED"
SURFACE_INSUFFICIENT = "RESERVE_METRIC_SURFACE_INSUFFICIENT"
BINDING_CONFLICT = "LEDGER_BINDING_CONFLICT"
REPLAY_FAILURE = "LEDGER_REPLAY_FAILURE"
TEMPLATE_NAMES = ("lb", "lbl", "tlb")
_HEADING = re.compile(r"=+\s*([^=]+?)\s*=+")


def target_names(label_arguments: list[str]) -> list[str]:
    """Target families named by whole label arguments, in head order."""
    found: list[str] = []
    for argument in label_arguments:
        token = normalize_label(argument)
        for family in TARGET_FAMILIES:
            if token in DIRECT_LABELS[family] and family not in found:
                found.append(family)
    return found


def _english_section(wikitext: str) -> str:
    parts = re.split(r"\n(?===[^=])", "\n" + wikitext)
    for part in parts:
        lines = part.strip().splitlines()
        if not lines:
            continue
        if lines[0].strip("= ").casefold() == "english":
            return part
    return ""


def qualifying_sense(wikitext: str) -> dict[str, Any]:
    """First English definition line that names a frozen target family.

    A line that names two target families is ambiguous and ends the walk.
    Near-miss labels do not count. This does not assign OBSERVED.
    """
    absent = {
        "exact_definition_line": None,
        "exact_definition_prose": None,
        "part_of_speech": None,
        "sense_label_arguments": [],
        "status": "absent",
        "target_family": None,
    }
    if not wikitext or wikitext.lstrip().lower().startswith("#redirect"):
        return absent
    section = _english_section(wikitext)
    if not section:
        return absent
    pos = None
    for line in section.splitlines():
        heading = _HEADING.fullmatch(line.strip())
        if heading and line.strip().startswith("==="):
            pos = heading.group(1).strip()
            continue
        if not line.startswith("# ") or line.startswith(("#:", "##")):
            continue
        arguments = sense_label_arguments(line)
        names = target_names(arguments)
        if not names:
            continue
        payload = {
            "exact_definition_line": line,
            "exact_definition_prose": definition_prose(line),
            "part_of_speech": pos,
            "sense_label_arguments": arguments,
            "target_family": names[0] if len(names) == 1 else None,
        }
        if len(names) > 1:
            payload["status"] = "ambiguous"
            return payload
        if named_target_family(arguments) != names[0]:
            payload["status"] = "ambiguous"
            payload["target_family"] = None
            return payload
        payload["status"] = "unique"
        return payload
    return absent


def search_query(template: str, label: str) -> str:
    """Exact template text. This does not add an alias."""
    if template not in TEMPLATE_NAMES or label not in {item for labels in DIRECT_LABELS.values() for item in labels}:
        raise SystemExit(f"{PIN_MISMATCH}: search label")
    return 'insource:"{{' + template + "|en|" + label + '}}"'
