"""Development-only matcher for the MAGPIE candidate evaluation.

Surface identity is orthographic. A surface hit does not assign
semantic noncompositionality. Sense alignment requires identifier
equality with the supplied synset. This module does not read operator
labels, gloss text, or a model judgment.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from decimal import Decimal

EXACT = "EXACT"
NORMALIZED = "NORMALIZED"
VARIANT = "VARIANT"
NONE = "NONE"
AMBIGUOUS = "AMBIGUOUS"
SURFACE_MATCHES = frozenset({EXACT, NORMALIZED, VARIANT, NONE, AMBIGUOUS})

ALIGNED_IDIOMATIC = "ALIGNED_IDIOMATIC"
ALIGNED_LITERAL = "ALIGNED_LITERAL"
MIXED = "MIXED"
CONFLICT = "CONFLICT"
UNKNOWN = "UNKNOWN"
ALIGNMENTS = frozenset({ALIGNED_IDIOMATIC, ALIGNED_LITERAL, MIXED, CONFLICT, UNKNOWN})

YES = "YES"
NO = "NO"

CODE_ALIGNED_IDIOMATIC = "magpie_aligned_idiomatic"
CODE_ALIGNED_LITERAL = "magpie_aligned_literal"
CODE_MIXED = "magpie_mixed_usage"
CODE_SURFACE = "magpie_surface_only"
CODE_CONFLICT = "magpie_sense_conflict"
CODE_NONE = "magpie_no_match"

_SENSE_FIELDS = frozenset({"synset", "synset_offset", "sense_key", "wordnet_offset"})
_APOSTROPHES = str.maketrans(
    {
        "\u2019": "'",
        "\u2018": "'",
        "\u02bc": "'",
        "\u2032": "'",
        "`": "'",
        "\u00b4": "'",
    }
)
_PUNCTUATION = str.maketrans(
    {
        "-": " ",
        "\u2010": " ",
        "\u2011": " ",
        "\u2013": " ",
        "\u2014": " ",
        ".": " ",
        ",": " ",
        ";": " ",
        ":": " ",
        "!": " ",
        "?": " ",
        '"': " ",
        "(": " ",
        ")": " ",
        "[": " ",
        "]": " ",
        "{": " ",
        "}": " ",
        "/": " ",
        "\\": " ",
    }
)


def exact_key(text: str) -> str:
    """Casefold and collapse separators. Punctuation stays in the key."""
    folded = text.casefold().replace("_", " ")
    return " ".join(folded.split())


def normalized_key(text: str) -> str:
    """Exact key plus apostrophe folding and punctuation removal.

    Apostrophes are kept. Possessive pronouns are not rewritten, and no
    stem or inflection is restored.
    """
    folded = exact_key(text).translate(_APOSTROPHES).translate(_PUNCTUATION)
    return " ".join(folded.split())


def _confidence_key(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError("confidence is not numeric")
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, int):
        return str(value)
    return format(Decimal(str(value)), "f")


def _sense_token(instance: dict) -> str | None:
    found = [
        field
        for field in sorted(_SENSE_FIELDS)
        if field in instance and instance[field] not in (None, "")
    ]
    if not found:
        return None
    if len(found) == 1:
        return str(instance[found[0]])
    return "|".join(f"{field}={instance[field]}" for field in found)


def _label_bucket(label: object) -> str:
    if label == "i":
        return "idiomatic"
    if label == "l":
        return "literal"
    return "unresolved"


class TypeUsage:
    def __init__(self, idiom: str) -> None:
        self.idiom = idiom
        self.literal_instance_count = 0
        self.idiomatic_instance_count = 0
        self.unresolved_instance_count = 0
        self.source_instance_ids: list[int] = []
        self.variant_types: Counter[str] = Counter()
        self.confidence_histogram: Counter[str] = Counter()
        self.judgment_counts: list[int] = []
        self.sense_ids: list[str] = []
        self.instances_with_sense_id = 0
        self.instance_count = 0

    def add(self, instance: dict) -> None:
        identifier = instance["id"]
        if isinstance(identifier, bool) or not isinstance(identifier, int):
            raise ValueError("instance id is not an int")
        bucket = _label_bucket(instance["label"])
        if bucket == "idiomatic":
            self.idiomatic_instance_count += 1
        elif bucket == "literal":
            self.literal_instance_count += 1
        else:
            self.unresolved_instance_count += 1
        self.source_instance_ids.append(identifier)
        variant = instance["variant_type"]
        if not isinstance(variant, str) or not variant:
            raise ValueError("variant_type is missing")
        self.variant_types[variant] += 1
        self.confidence_histogram[_confidence_key(instance["confidence"])] += 1
        if "judgment_count" in instance and instance["judgment_count"] is not None:
            judgment = instance["judgment_count"]
            if isinstance(judgment, bool) or not isinstance(judgment, int):
                raise ValueError("judgment_count is not an int")
            self.judgment_counts.append(judgment)
        token = _sense_token(instance)
        self.instance_count += 1
        if token is not None:
            self.instances_with_sense_id += 1
            self.sense_ids.append(token)

    def finish(self) -> None:
        self.source_instance_ids.sort()
        if len(self.source_instance_ids) != len(set(self.source_instance_ids)):
            raise ValueError("duplicate instance id inside one expression")


class CorpusIndex:
    def __init__(self) -> None:
        self.types: dict[str, TypeUsage] = {}
        self.by_exact: dict[str, list[str]] = {}
        self.by_normalized: dict[str, list[str]] = {}
        self.field_names: set[str] = set()
        self.instance_count = 0
        self.records_bound_sense = False

    @property
    def type_count(self) -> int:
        return len(self.types)


def build_index(instances: Iterable[dict]) -> CorpusIndex:
    index = CorpusIndex()
    seen_ids: set[int] = set()
    for instance in instances:
        index.field_names.update(instance.keys())
        idiom = instance["idiom"]
        if not isinstance(idiom, str) or not idiom.strip():
            raise ValueError("idiom string is empty")
        identifier = instance["id"]
        if identifier in seen_ids:
            raise ValueError("duplicate instance id")
        seen_ids.add(identifier)
        usage = index.types.get(idiom)
        if usage is None:
            usage = TypeUsage(idiom)
            index.types[idiom] = usage
        usage.add(instance)
        index.instance_count += 1
    if index.field_names & _SENSE_FIELDS:
        index.records_bound_sense = True
    exact_groups: dict[str, list[str]] = {}
    normal_groups: dict[str, list[str]] = {}
    for idiom, usage in index.types.items():
        usage.finish()
        exact_groups.setdefault(exact_key(idiom), []).append(idiom)
        key = normalized_key(idiom)
        if key:
            normal_groups.setdefault(key, []).append(idiom)
    for key, idioms in exact_groups.items():
        index.by_exact[key] = sorted(idioms)
    for key, idioms in normal_groups.items():
        index.by_normalized[key] = sorted(idioms)
    return index


def _confidence_summary(usage: TypeUsage | None) -> dict | None:
    if usage is None:
        return None
    summary = {
        "histogram": dict(sorted(usage.confidence_histogram.items())),
        "instance_count": usage.instance_count,
    }
    if usage.judgment_counts:
        summary["judgment_count_maximum"] = max(usage.judgment_counts)
        summary["judgment_count_minimum"] = min(usage.judgment_counts)
    return summary


def match_surface(surface: str, index: CorpusIndex) -> dict:
    """Return one surface relation. Variant metadata is not a second idiom."""
    exact_hits = index.by_exact.get(exact_key(surface), [])
    if len(exact_hits) == 1:
        relation = EXACT
        idiom = exact_hits[0]
        candidates: list[str] = []
    elif len(exact_hits) > 1:
        relation = AMBIGUOUS
        idiom = None
        candidates = list(exact_hits)
    else:
        normal_hits = index.by_normalized.get(normalized_key(surface), [])
        if len(normal_hits) == 1:
            relation = NORMALIZED
            idiom = normal_hits[0]
            candidates = []
        elif len(normal_hits) > 1:
            relation = AMBIGUOUS
            idiom = None
            candidates = list(normal_hits)
        else:
            relation = NONE
            idiom = None
            candidates = []
    usage = index.types[idiom] if idiom is not None else None
    attributed = usage is not None
    return {
        "ambiguous_candidates": candidates,
        "annotation_confidence": _confidence_summary(usage),
        "attributed": attributed,
        "idiomatic_instance_count": usage.idiomatic_instance_count if usage else None,
        "literal_instance_count": usage.literal_instance_count if usage else None,
        "matched_magpie_expression": idiom,
        "source_instance_ids": list(usage.source_instance_ids) if usage else [],
        "surface_match": relation,
        "unresolved_instance_count": usage.unresolved_instance_count if usage else None,
        "usage": usage,
        "variant_types": dict(sorted(usage.variant_types.items())) if usage else {},
    }


def align_sense(match: dict, supplied_synset: str, index: CorpusIndex) -> tuple[str, str]:
    """Align only by equality of a source sense identifier to the synset.

    Mixed literal and idiomatic counts do not by themselves create MIXED.
    The supplied gloss is not an argument.
    """
    relation = match["surface_match"]
    if relation == NONE:
        return UNKNOWN, "no_surface_match"
    if relation == AMBIGUOUS:
        return UNKNOWN, "ambiguous_surface"
    if relation == VARIANT:
        return UNKNOWN, "variant_without_sense_identifier"
    usage: TypeUsage = match["usage"]
    if not index.records_bound_sense or usage.instances_with_sense_id == 0:
        return UNKNOWN, "no_bound_sense_identifier"
    if usage.instances_with_sense_id != usage.instance_count:
        return UNKNOWN, "partial_sense_identifier"
    identifiers = set(usage.sense_ids)
    if supplied_synset in identifiers and len(identifiers) > 1:
        return CONFLICT, "sense_identifier_conflict"
    if identifiers != {supplied_synset}:
        return UNKNOWN, "sense_identifier_mismatch"
    literal = usage.literal_instance_count
    idiomatic = usage.idiomatic_instance_count
    unresolved = usage.unresolved_instance_count
    if idiomatic > 0 and literal == 0 and unresolved == 0:
        return ALIGNED_IDIOMATIC, "aligned_idiomatic"
    if literal > 0 and idiomatic == 0 and unresolved == 0:
        return ALIGNED_LITERAL, "aligned_literal"
    if idiomatic > 0 and literal > 0:
        return MIXED, "mixed_usage_on_aligned_sense"
    return UNKNOWN, "unresolved_labels_on_aligned_sense"


def evidence_code(surface_match: str, alignment: str) -> str:
    if alignment == ALIGNED_IDIOMATIC:
        return CODE_ALIGNED_IDIOMATIC
    if alignment == ALIGNED_LITERAL:
        return CODE_ALIGNED_LITERAL
    if alignment == MIXED:
        return CODE_MIXED
    if alignment == CONFLICT:
        return CODE_CONFLICT
    if surface_match == NONE:
        return CODE_NONE
    return CODE_SURFACE


def semantic_noncompositional(alignment: str) -> str:
    if alignment == ALIGNED_IDIOMATIC:
        return YES
    if alignment == ALIGNED_LITERAL:
        return NO
    return UNKNOWN


def evaluate_row(
    surface: str,
    synset: str,
    index: CorpusIndex,
    source_version: str,
    source_artifact_hash: str,
) -> dict:
    """One development row. Operator labels and glosses are not inputs."""
    match = match_surface(surface, index)
    alignment, basis = align_sense(match, synset, index)
    code = evidence_code(match["surface_match"], alignment)
    semantic = semantic_noncompositional(alignment)
    if match["surface_match"] != NONE and semantic == YES and alignment != ALIGNED_IDIOMATIC:
        raise RuntimeError("surface match assigned YES without aligned idiomatic evidence")
    return {
        "alignment_basis": basis,
        "ambiguous_candidates": match["ambiguous_candidates"],
        "annotation_confidence": match["annotation_confidence"],
        "idiomatic_instance_count": match["idiomatic_instance_count"],
        "literal_instance_count": match["literal_instance_count"],
        "matched_magpie_expression": match["matched_magpie_expression"],
        "primary_evidence_code": code,
        "semantic_noncompositional": semantic,
        "sense_alignment": alignment,
        "source_artifact_hash": source_artifact_hash,
        "source_instance_ids": match["source_instance_ids"],
        "source_name": "MAGPIE",
        "source_version": source_version,
        "surface_match": match["surface_match"],
        "unresolved_instance_count": match["unresolved_instance_count"],
        "variant_types": match["variant_types"],
    }
