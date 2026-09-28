"""Development-only alignment for the Korkontzelos–Manandhar candidate.

A compositionality label supports semantic evidence only when the item
is tied to one PWN 3.0 synset by a source identifier or by a unique
lemma reconstruction. Multiple synsets stay unresolved. Gloss text,
operator labels, and surface overlap are not tie breaks.
"""

from __future__ import annotations

EXACT_SOURCE_ID = "EXACT_SOURCE_ID"
EXACT_UNIQUE_RECONSTRUCTION = "EXACT_UNIQUE_RECONSTRUCTION"
AMBIGUOUS_MULTIPLE_SYNSETS = "AMBIGUOUS_MULTIPLE_SYNSETS"
NO_PWN3_MATCH = "NO_PWN3_MATCH"
VERSION_CONFLICT = "VERSION_CONFLICT"
UNKNOWN = "UNKNOWN"

SUPPORTING = frozenset({EXACT_SOURCE_ID, EXACT_UNIQUE_RECONSTRUCTION})

YES = "YES"
NO = "NO"

CODE_NONCOMPOSITIONAL = "km_exact_noncompositional"
CODE_COMPOSITIONAL = "km_exact_compositional"
CODE_AMBIGUOUS = "km_ambiguous_synset"
CODE_NONE = "km_no_match"
CODE_VERSION = "km_version_conflict"
CODE_UNRESOLVED = "km_source_id_unresolved"

NONCOMPOSITIONAL = "NONCOMPOSITIONAL"
COMPOSITIONAL = "COMPOSITIONAL"


def lookup_key(text: str) -> str:
    """Orthographic key for a WordNet lemma. Hyphens stay in the key."""
    folded = text.casefold()
    folded = folded.replace("\u2019", "'").replace("\u2018", "'").replace("`", "'")
    folded = folded.replace("_", " ")
    return "_".join(folded.split())


def alignment_status(source_identifier: str | None, candidate_synset_ids: list[str]) -> str:
    """Classify sense identity. The candidate list is not ranked."""
    identifiers = list(dict.fromkeys(candidate_synset_ids))
    if source_identifier:
        if len(identifiers) == 1 and identifiers[0] == source_identifier:
            return EXACT_SOURCE_ID
        if source_identifier not in identifiers:
            return VERSION_CONFLICT
        return AMBIGUOUS_MULTIPLE_SYNSETS
    if len(identifiers) == 1:
        return EXACT_UNIQUE_RECONSTRUCTION
    if not identifiers:
        return NO_PWN3_MATCH
    return AMBIGUOUS_MULTIPLE_SYNSETS


def semantic_noncompositional(source_label: str, status: str) -> str:
    if status not in SUPPORTING:
        return UNKNOWN
    if source_label == NONCOMPOSITIONAL:
        return YES
    if source_label == COMPOSITIONAL:
        return NO
    return UNKNOWN


def evidence_code(status: str, semantic: str) -> str:
    if semantic == YES and status in SUPPORTING:
        return CODE_NONCOMPOSITIONAL
    if semantic == NO and status in SUPPORTING:
        return CODE_COMPOSITIONAL
    if status == AMBIGUOUS_MULTIPLE_SYNSETS:
        return CODE_AMBIGUOUS
    if status == VERSION_CONFLICT:
        return CODE_VERSION
    if status == UNKNOWN:
        return CODE_UNRESOLVED
    return CODE_NONE


def align_item(
    source_label: str,
    source_identifier: str | None,
    candidate_synset_ids: list[str],
) -> dict:
    status = alignment_status(source_identifier, candidate_synset_ids)
    semantic = semantic_noncompositional(source_label, status)
    aligned = candidate_synset_ids[0] if status in SUPPORTING and len(set(candidate_synset_ids)) == 1 else None
    if status in SUPPORTING and aligned is None:
        raise RuntimeError("supporting alignment has no single synset")
    if status not in SUPPORTING and semantic != UNKNOWN:
        raise RuntimeError("non-aligned item assigned semantic evidence")
    return {
        "aligned_pwn30_synset": aligned,
        "alignment_status": status,
        "primary_evidence_code": evidence_code(status, semantic),
        "semantic_noncompositional": semantic,
    }


def join_synset(synset: str, exact: dict[str, dict], ambiguous: dict[str, list[str]]) -> dict:
    """Join a Hyperlex synset. The surface is not an argument."""
    exact_item = exact.get(synset)
    ambiguous_ids = list(ambiguous.get(synset, []))
    if exact_item is not None and ambiguous_ids:
        status = AMBIGUOUS_MULTIPLE_SYNSETS
        semantic = UNKNOWN
        item_id = None
        aligned = None
    elif exact_item is not None:
        status = exact_item["alignment_status"]
        semantic = exact_item["semantic_noncompositional"]
        item_id = exact_item["source_item_id"]
        aligned = exact_item["aligned_pwn30_synset"]
    elif len(ambiguous_ids) == 1:
        status = AMBIGUOUS_MULTIPLE_SYNSETS
        semantic = UNKNOWN
        item_id = ambiguous_ids[0]
        aligned = None
    elif ambiguous_ids:
        status = AMBIGUOUS_MULTIPLE_SYNSETS
        semantic = UNKNOWN
        item_id = None
        aligned = None
    else:
        status = UNKNOWN
        semantic = UNKNOWN
        item_id = None
        aligned = None
        code = CODE_NONE
    if semantic != UNKNOWN and status not in SUPPORTING:
        raise RuntimeError("join assigned semantic evidence without exact alignment")
    if status != UNKNOWN:
        code = evidence_code(status, semantic)
    return {
        "alignment_status": status,
        "candidate_aligned_synset": aligned,
        "candidate_source_item_id": item_id,
        "primary_evidence_code": code,
        "semantic_noncompositional": semantic,
    }
