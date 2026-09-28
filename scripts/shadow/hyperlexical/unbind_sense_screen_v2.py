"""Sense screen procedure v2.

Three states are recorded before the class. A whole-expression co-lemma
is lexicalization. It is not a compositional no, and it is not high.
"""

from __future__ import annotations

import re

from hyperlexical.unbind_sense_screen_v1 import (
    Pointer,
    Synset,
    load_exceptions,
    load_wordnet,
    parse_data_line,
)

RULE_VERSION = "RUNE.UNBIND_SENSE_SCREEN.v1"
PROCEDURE = "hyperlex.unbind_sense_screen_v1_classification_procedure.v2"
_LIFESPAN = re.compile(r"\([0-9]{4}-[0-9]{4}\)")
_COMPARATIVE = re.compile(r"^used to form the comparative\b")
_SUPERLATIVE = re.compile(r"^used to form the superlative\b")
_LEXICAL_SYMBOLS = frozenset({"!", "+", "\\", "^", "*", "&", "<", "$"})
_RELATION_SYMBOLS = frozenset({"+", "\\"})
_PREDICATE_TYPES = frozenset({"r", "a", "s"})
_BUCKETS = {
    "REFERENTIAL": "REJECT",
    "LEXICALIZED_NONCOMPOSITIONAL": "HIGH",
    "LEXICALIZED_COMPOSITIONAL": "SECONDARY",
    "ORDINARY_COMPOSITIONAL": "SECONDARY",
    "AMBIGUOUS": "QUARANTINE",
}
_FAMILY_ORDER = (
    "referential_designation",
    "whole_expression_lexicalization",
    "compositional_semantic_relation",
    "productive_grammatical_frame",
    "noncompositional_semantic_mapping",
    "insufficient_record_evidence",
    "conflicting_record_evidence",
)
_SOURCE_ORDER = (
    "synset.instance_hypernym",
    "synset.gloss.lifespan",
    "synset.ss_type.predicate",
    "synset.lemmas.unrelated_single_word",
    "synset.lexical_pointer",
    "synset.gloss.grammatical_operator",
    "synset.lexical_pointer.derivation_or_pertainym_to_constituent",
    "synset.lemmas.productive_alternation",
)

__all__ = [
    "Pointer",
    "Synset",
    "classify",
    "load_exceptions",
    "load_wordnet",
    "parse_data_line",
]


def classify(surface: str, gloss: str, synset: Synset, exceptions: dict[str, set[str]], targets: dict[tuple[str, str], tuple[str, ...]]) -> dict:
    """Apply procedure v2 once. Compositional NO is not produced."""
    text = gloss or ""
    tokens = _tokens(surface)
    referential, referential_hits = _referential(text, synset)
    lexicalized, lexicalized_hits = _lexicalized(tokens, synset, exceptions, text)
    compositional, compositional_hits = _compositional(tokens, synset, exceptions, targets, text)
    if compositional in {"NO", "CONFLICT"}:
        raise RuntimeError("procedure v2 has no compositional NO signal")
    hits = referential_hits + lexicalized_hits + compositional_hits
    if referential == "CONFLICT" or (referential != "YES" and lexicalized == "CONFLICT"):
        return _decision(
            "AMBIGUOUS",
            "conflicting_record_evidence",
            "CONTRADICTORY",
            referential,
            lexicalized,
            compositional,
            hits,
            None,
        )
    if referential == "YES":
        return _decision(
            "REFERENTIAL",
            "referential_designation",
            "DETERMINATE",
            referential,
            lexicalized,
            compositional,
            hits,
            referential_hits[0][0],
        )
    if lexicalized == "YES" and compositional == "NO":
        return _decision(
            "LEXICALIZED_NONCOMPOSITIONAL",
            "noncompositional_semantic_mapping",
            "DETERMINATE",
            referential,
            lexicalized,
            compositional,
            hits,
            None,
        )
    if lexicalized == "YES" and compositional == "YES":
        source, family = compositional_hits[0]
        return _decision(
            "LEXICALIZED_COMPOSITIONAL",
            family,
            "DETERMINATE",
            referential,
            lexicalized,
            compositional,
            hits,
            source,
        )
    if lexicalized == "NO" and compositional == "YES":
        return _decision(
            "ORDINARY_COMPOSITIONAL",
            "productive_grammatical_frame",
            "DETERMINATE",
            referential,
            lexicalized,
            compositional,
            hits,
            "synset.gloss.grammatical_operator",
        )
    return _decision(
        "AMBIGUOUS",
        "insufficient_record_evidence",
        "INSUFFICIENT",
        referential,
        lexicalized,
        compositional,
        hits,
        None,
    )


def _decision(sense_class, primary, confidence, referential, lexicalized, compositional, hits, deciding):
    families = []
    fired = []
    for source, family in hits:
        if source not in fired:
            fired.append(source)
        if family and family not in families:
            families.append(family)
    sources = [name for name in _SOURCE_ORDER if name in fired and name != deciding]
    if deciding:
        sources.insert(0, deciding)
    if not sources:
        sources = ["none"]
    supporting = [name for name in _FAMILY_ORDER if name in families and name != primary]
    return {
        "rule": RULE_VERSION,
        "procedure": PROCEDURE,
        "referential_state": referential,
        "lexicalized_state": lexicalized,
        "compositional_state": compositional,
        "sense_class": sense_class,
        "bucket": _BUCKETS[sense_class],
        "primary_evidence_code": primary,
        "supporting_evidence_codes": supporting,
        "evidence_sources": sources,
        "confidence_status": confidence,
    }


def _referential(gloss: str, synset: Synset):
    if any(pointer.symbol == "@i" for pointer in synset.pointers):
        return "YES", [("synset.instance_hypernym", "referential_designation")]
    if _LIFESPAN.search(gloss):
        return "YES", [("synset.gloss.lifespan", "referential_designation")]
    hits = []
    if synset.ss_type in _PREDICATE_TYPES:
        hits.append(("synset.ss_type.predicate", None))
    if _operator(gloss):
        hits.append(("synset.gloss.grammatical_operator", "productive_grammatical_frame"))
    if hits:
        return "NO", hits
    return "UNKNOWN", []


def _lexicalized(tokens, synset: Synset, exceptions, gloss: str):
    hits = []
    if _unrelated(tokens, synset, exceptions):
        hits.append(("synset.lemmas.unrelated_single_word", "whole_expression_lexicalization"))
    if _lexical_pointer(tokens, synset):
        hits.append(("synset.lexical_pointer", "whole_expression_lexicalization"))
    operator = [("synset.gloss.grammatical_operator", "productive_grammatical_frame")] if _operator(gloss) else []
    if hits and operator:
        return "CONFLICT", hits + operator
    if hits:
        return "YES", hits
    if operator:
        return "NO", operator
    return "UNKNOWN", []


def _compositional(tokens, synset: Synset, exceptions, targets, gloss: str):
    hits = []
    if _constituent_relation(tokens, synset, exceptions, targets):
        hits.append(("synset.lexical_pointer.derivation_or_pertainym_to_constituent", "compositional_semantic_relation"))
    if _alternation(tokens, synset):
        hits.append(("synset.lemmas.productive_alternation", "productive_grammatical_frame"))
    if _operator(gloss):
        hits.append(("synset.gloss.grammatical_operator", "productive_grammatical_frame"))
    if hits:
        return "YES", hits
    return "UNKNOWN", []


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(_norm(text).split())


def _norm(text: str) -> str:
    return " ".join(text.replace("_", " ").replace("-", " ").casefold().split())


def _operator(gloss: str) -> bool:
    return bool(_COMPARATIVE.match(gloss or "") or _SUPERLATIVE.match(gloss or ""))


def _surface_index(tokens: tuple[str, ...], synset: Synset) -> int:
    wanted = " ".join(tokens)
    for index, lemma in enumerate(synset.lemmas, start=1):
        if _norm(lemma) == wanted:
            return index
    return 0


def _unrelated(tokens: tuple[str, ...], synset: Synset, exceptions: dict[str, set[str]]) -> bool:
    owned = set(tokens)
    wanted = " ".join(tokens)
    for lemma in synset.lemmas:
        if _norm(lemma) == wanted:
            continue
        parts = _tokens(lemma)
        if len(parts) != 1:
            continue
        word = parts[0]
        if word in owned or _linked(word, owned, exceptions):
            continue
        return True
    return False


def _linked(word: str, tokens: set[str], exceptions: dict[str, set[str]]) -> bool:
    related = exceptions.get(word, set())
    for token in tokens:
        if token in related or word in exceptions.get(token, set()):
            return True
    return False


def _lexical_pointer(tokens: tuple[str, ...], synset: Synset) -> bool:
    source = _surface_index(tokens, synset)
    if source == 0:
        return False
    return any(pointer.source == source and pointer.symbol in _LEXICAL_SYMBOLS for pointer in synset.pointers)


def _alternation(tokens: tuple[str, ...], synset: Synset) -> bool:
    groups = [_tokens(lemma) for lemma in synset.lemmas if len(_tokens(lemma)) >= 2]
    for left in range(len(groups)):
        for right in range(left + 1, len(groups)):
            one = groups[left]
            other = groups[right]
            if len(one) != len(other):
                continue
            if sum(token != sibling for token, sibling in zip(one, other)) != 1:
                continue
            if one == tokens or other == tokens:
                return True
    return False


def _constituent_relation(tokens, synset: Synset, exceptions, targets) -> bool:
    source = _surface_index(tokens, synset)
    if source == 0:
        return False
    owned = set(tokens)
    for pointer in synset.pointers:
        if pointer.source != source or pointer.symbol not in _RELATION_SYMBOLS or pointer.target < 1:
            continue
        lemmas = targets.get((pointer.pos, pointer.offset), ())
        if pointer.target > len(lemmas):
            continue
        parts = _tokens(lemmas[pointer.target - 1])
        if len(parts) == 1 and (parts[0] in owned or _linked(parts[0], owned, exceptions)):
            return True
    return False
