"""Sense-first unbind screen.

The class comes from the frozen WordNet record of the supplied synset.
Membership in WordNet is not a class. Absence of a signal is not secondary.
"""

from __future__ import annotations

import re
from pathlib import Path

RULE_VERSION = "RUNE.UNBIND_SENSE_SCREEN.v1"
_LIFESPAN = re.compile(r"\([0-9]{4}-[0-9]{4}\)")
_COMPARATIVE = re.compile(r"^used to form the comparative\b")
_SUPERLATIVE = re.compile(r"^used to form the superlative\b")
_LEXICAL_SYMBOLS = frozenset({"!", "+", "\\", "^", "*", "&", "<", "$"})
_RELATION_SYMBOLS = frozenset({"+", "\\"})
_PREDICATE_TYPES = frozenset({"r", "a", "s"})
_FILES = {
    "noun": "data.noun",
    "verb": "data.verb",
    "adj": "data.adj",
    "adv": "data.adv",
}
_EXC = {
    "noun": "noun.exc",
    "verb": "verb.exc",
    "adj": "adj.exc",
    "adv": "adv.exc",
}
_CODES = {
    "REFERENTIAL": "referential_designation",
    "ORDINARY_COMPOSITIONAL": "productive_grammatical_frame",
    "LEXICALIZED_NONCOMPOSITIONAL": "noncompositional_semantic_mapping",
    "LEXICALIZED_COMPOSITIONAL": "compositional_lexical_unit",
    "AMBIGUOUS": "insufficient_record_evidence",
}
_BUCKETS = {
    "REFERENTIAL": "REJECT",
    "LEXICALIZED_NONCOMPOSITIONAL": "HIGH",
    "LEXICALIZED_COMPOSITIONAL": "SECONDARY",
    "ORDINARY_COMPOSITIONAL": "SECONDARY",
    "AMBIGUOUS": "QUARANTINE",
}


class Pointer:
    def __init__(self, symbol: str, offset: str, pos: str, source: int, target: int):
        self.symbol = symbol
        self.offset = offset
        self.pos = pos
        self.source = source
        self.target = target


class Synset:
    def __init__(self, offset: str, ss_type: str, lemmas: tuple[str, ...], pointers: tuple[Pointer, ...]):
        self.offset = offset
        self.ss_type = ss_type
        self.lemmas = lemmas
        self.pointers = pointers


def parse_data_line(line: str) -> tuple[Synset, str] | None:
    """Return the synset and the first gloss clause.

    The word count and the source/target word numbers are hexadecimal.
    The pointer count is a decimal integer. Verb frames follow the pointers
    and are not pointers.
    """
    if not line or line[0] == " ":
        return None
    meta, bar, gloss = line.partition("|")
    if not bar:
        return None
    tokens = meta.split()
    offset = tokens[0]
    ss_type = tokens[2]
    word_count = int(tokens[3], 16)
    index = 4
    lemmas = []
    for _ in range(word_count):
        lemmas.append(tokens[index])
        index += 2
    pointer_count = int(tokens[index], 10)
    index += 1
    pointers = []
    for _ in range(pointer_count):
        symbol = tokens[index]
        target = tokens[index + 1]
        pos = tokens[index + 2]
        link = tokens[index + 3]
        pointers.append(Pointer(symbol, target, pos, int(link[:2], 16), int(link[2:], 16)))
        index += 4
    first = gloss.strip().split(";", 1)[0].strip()
    return Synset(offset, ss_type, tuple(lemmas), tuple(pointers)), first


def load_exceptions(root: str | Path) -> dict[str, set[str]]:
    linked: dict[str, set[str]] = {}
    base = Path(root)
    for name in _EXC.values():
        for line in (base / name).read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split()
            if len(parts) < 2:
                continue
            left = parts[0].casefold()
            right = parts[1].casefold()
            linked.setdefault(left, set()).add(right)
            linked.setdefault(right, set()).add(left)
    return linked


def load_wordnet(root: str | Path) -> tuple[dict[tuple[str, str], Synset], dict[tuple[str, str], str]]:
    synsets: dict[tuple[str, str], Synset] = {}
    glosses: dict[tuple[str, str], str] = {}
    base = Path(root)
    for pos, name in _FILES.items():
        for line in (base / name).read_text(encoding="utf-8", errors="replace").splitlines():
            parsed = parse_data_line(line)
            if parsed is None:
                continue
            synset, gloss = parsed
            for key in ((pos, synset.offset), (synset.ss_type, synset.offset)):
                synsets[key] = synset
                glosses[key] = gloss
    return synsets, glosses


def classify(surface: str, gloss: str, synset: Synset, exceptions: dict[str, set[str]], targets: dict[tuple[str, str], tuple[str, ...]]) -> dict:
    """Apply the frozen procedure once. The result is one class and one bucket."""
    text = gloss or ""
    tokens = _tokens(surface)
    ref_yes, ref_source = _referential_yes(text, synset)
    ref_no = _referential_no(text, synset, ref_yes)
    unrelated = _unrelated(tokens, synset, exceptions)
    pointer = _lexical_pointer(tokens, synset)
    alternation = _alternation(tokens, synset)
    operator = _operator(text)
    unit_yes = bool(unrelated) or pointer
    unit_no = alternation or operator
    constituent = _constituent_relation(tokens, synset, exceptions, targets)
    # The constituent signal is defined only when no unrelated co-lemma is present,
    # so those two signals do not fire together.
    if (ref_yes and unit_no) or (unit_yes and unit_no):
        return _emit("AMBIGUOUS", "none", insufficient=True)
    _ = ref_no
    if ref_yes:
        return _emit("REFERENTIAL", ref_source, insufficient=False)
    if unit_no:
        source = "synset.lemmas.productive_alternation" if alternation else "synset.gloss.grammatical_operator"
        return _emit("ORDINARY_COMPOSITIONAL", source, insufficient=False)
    if not unit_yes:
        return _emit("AMBIGUOUS", "none", insufficient=True)
    if unrelated:
        return _emit("LEXICALIZED_NONCOMPOSITIONAL", "synset.lemmas.unrelated_single_word", insufficient=False)
    if constituent:
        return _emit("LEXICALIZED_COMPOSITIONAL", "synset.lexical_pointer.derivation_or_pertainym_to_constituent", insufficient=False)
    return _emit("AMBIGUOUS", "none", insufficient=True)


def _emit(sense_class: str, source: str, *, insufficient: bool) -> dict:
    return {
        "rule": RULE_VERSION,
        "sense_class": sense_class,
        "bucket": _BUCKETS[sense_class],
        "primary_evidence_code": _CODES[sense_class],
        "evidence_source": source,
        "confidence_status": "INSUFFICIENT" if insufficient else "DETERMINATE",
    }


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(_norm(text).split())


def _norm(text: str) -> str:
    return " ".join(text.replace("_", " ").replace("-", " ").casefold().split())


def _referential_yes(gloss: str, synset: Synset) -> tuple[bool, str]:
    if any(pointer.symbol == "@i" for pointer in synset.pointers):
        return True, "synset.instance_hypernym"
    if _LIFESPAN.search(gloss):
        return True, "synset.gloss.lifespan"
    return False, "none"


def _referential_no(gloss: str, synset: Synset, ref_yes: bool) -> bool:
    if ref_yes:
        return False
    return synset.ss_type in _PREDICATE_TYPES or _operator(gloss)


def _operator(gloss: str) -> bool:
    return bool(_COMPARATIVE.match(gloss) or _SUPERLATIVE.match(gloss))


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


def _constituent_relation(tokens: tuple[str, ...], synset: Synset, exceptions: dict[str, set[str]], targets: dict[tuple[str, str], tuple[str, ...]]) -> bool:
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
