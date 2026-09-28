"""Secondary-only wrapper over a frozen v4 bucket.

HIGH and REJECT pass through uninspected. A SECONDARY row is inspected once.
Referential or terminological dominance moves it to REJECT. A conventionalized
surface whose gloss is not recoverable from the ordinary first senses of its
constituents moves it to HIGH. A lexicalized but compositional surface stays
SECONDARY.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from hyperlexical.unbind_screen_v3 import STOP
from hyperlexical.unbind_screen_v4 import canonical_bucket, normalize_lexical

RULE_VERSION = "RUNE.UNBIND_SCREEN.v5"
REJECT_EVIDENCE = "referential_terminological_dominance"
HIGH_EVIDENCE = "lexicalized_noncompositional"
_FUNCTION = set(STOP) | {"one's", "jr", "jr's"}
_META = frozenset({"used", "introducing"})
_LIFE = frozenset({"noun.plant", "noun.animal"})
_WORD = re.compile(r"[A-Za-z']+")
_TOKEN = re.compile(r"[a-z0-9']+")
_POS = ("noun", "verb", "adj", "adv")


@dataclass(frozen=True)
class Sense:
    token: str
    pos: str
    lex: str
    gloss: str


@dataclass(frozen=True)
class Entry:
    pos: str
    lemma: str
    lex: str
    lemmas: tuple[str, ...]
    hypernyms: tuple[tuple[str, ...], ...]


class EmptyLexicon:
    def entry(self, surface: str) -> Entry | None:
        return None

    def senses(self, token: str) -> tuple[Sense, ...]:
        return ()


class WordNetLexicon:
    """First-sense synsets. Gloss evidence, not a phrase list."""

    def __init__(self, root: str | Path):
        base = Path(root)
        lexnames = _lexnames(base / "lexnames")
        self._data = {pos: _load_data(base / f"data.{pos}") for pos in _POS}
        self._index = {pos: _load_index(base / f"index.{pos}") for pos in _POS}
        self._lexnames = lexnames
        self._entries: dict[str, tuple[str, str, str]] = {}
        for pos in _POS:
            for key, offsets in self._index[pos].items():
                if not offsets:
                    continue
                folded = key.casefold().replace("-", "_")
                self._entries.setdefault(folded, (pos, key, offsets[0]))

    def entry(self, surface: str) -> Entry | None:
        folded = surface.casefold().replace(" ", "_").replace("-", "_")
        found = self._entries.get(folded)
        if found is None:
            return None
        pos, key, offset = found
        built = self._entry(pos, offset)
        return Entry(built.pos, key, built.lex, built.lemmas, built.hypernyms)

    def senses(self, token: str) -> tuple[Sense, ...]:
        found = []
        for pos in _POS:
            offsets = self._index[pos].get(token)
            if not offsets:
                continue
            entry = self._entry(pos, offsets[0])
            gloss = self._gloss(pos, offsets[0])
            found.append(Sense(token, pos, entry.lex, gloss))
        return tuple(found)

    def _entry(self, pos: str, offset: str) -> Entry:
        lemmas, lex, hypers = _parse(self._data[pos][offset], self._lexnames, self._data["noun"])
        return Entry(pos, lemmas[0] if lemmas else "", lex, tuple(lemmas), tuple(tuple(item) for item in hypers))

    def _gloss(self, pos: str, offset: str) -> str:
        line = self._data[pos][offset]
        return line.split("|", 1)[1].split(";", 1)[0].strip()


def apply_v5(v4_bucket: str, surface: str, gloss: str, source_pos: str, lexicon) -> dict:
    """Return the v5 bucket. HIGH and REJECT are not inspected."""
    del source_pos
    bucket = canonical_bucket(v4_bucket)
    normalized = normalize_lexical(surface)
    if bucket != "SECONDARY":
        return _decision(bucket, bucket, None, normalized, inspected=False)
    evidence = _inspect(surface or "", gloss or "", lexicon)
    if evidence == REJECT_EVIDENCE:
        return _decision(bucket, "REJECT", evidence, normalized, inspected=True)
    if evidence == HIGH_EVIDENCE:
        return _decision(bucket, "HIGH", evidence, normalized, inspected=True)
    return _decision(bucket, "SECONDARY", None, normalized, inspected=True)


def assess(rows: list[dict], *, phrase_specific_rule_fired: bool, expected_rows: int = 141) -> dict:
    """Replay gate. This is not a precision score."""
    failures: list[str] = []
    surfaces = [str(row["surface"]) for row in rows]
    if len(rows) != expected_rows:
        failures.append(f"replay rows {len(rows)} != {expected_rows}")
    if len(set(surfaces)) != len(surfaces):
        failures.append("replay surface is duplicated")
    moves = {"secondary_to_high": 0, "secondary_to_reject": 0, "secondary_unchanged": 0}
    held = {"high": 0, "reject": 0}
    conflicts = 0
    for row in rows:
        prior = canonical_bucket(str(row["v4_bucket"]))
        nxt = canonical_bucket(str(row["v5_bucket"]))
        operator = canonical_bucket(str(row["operator_bucket"]))
        primary = row.get("primary_evidence")
        supporting = list(row.get("supporting_evidence") or [])
        if prior == "HIGH":
            held["high"] += 1
            if nxt != "HIGH":
                failures.append("HIGH row changed bucket")
            if operator == "HIGH" and nxt != "HIGH":
                failures.append("previously correct HIGH is no longer correct")
        elif prior == "REJECT":
            held["reject"] += 1
            if nxt != "REJECT":
                failures.append("REJECT row changed bucket")
            if operator == "REJECT" and nxt != "REJECT":
                failures.append("previously correct REJECT is no longer correct")
        elif prior == "SECONDARY":
            if nxt == "SECONDARY":
                moves["secondary_unchanged"] += 1
                if primary is not None or supporting:
                    failures.append("unchanged SECONDARY carries transition evidence")
            elif nxt == "HIGH":
                moves["secondary_to_high"] += 1
                if primary != HIGH_EVIDENCE or supporting:
                    failures.append("SECONDARY to HIGH lacks lexicalized_noncompositional")
            elif nxt == "REJECT":
                moves["secondary_to_reject"] += 1
                if primary != REJECT_EVIDENCE or supporting:
                    failures.append("SECONDARY to REJECT lacks referential_terminological_dominance")
            else:
                failures.append("SECONDARY moved outside HIGH and REJECT")
        else:
            failures.append("prior bucket is outside HIGH, REJECT, and SECONDARY")
        if prior != nxt and operator != nxt:
            conflicts += 1
            failures.append("operator conflict on a move")
        if prior != nxt and primary is None:
            failures.append("changed row has no primary evidence")
    if phrase_specific_rule_fired:
        failures.append("phrase-specific rule fired")
    verified = not failures
    return {
        "schema": "hyperlex.unbind_screen_v5_gate_report.v1",
        "rule": RULE_VERSION,
        "regression": "REGRESSION_VERIFIED" if verified else "REGRESSION_FAILED",
        "state": "REGRESSION_VERIFIED" if verified else "ENCODED",
        "failures": failures,
        "expected_rows": expected_rows,
        "replay_rows": len(rows),
        "unique_surfaces": len(set(surfaces)),
        "high_unchanged": held["high"],
        "reject_unchanged": held["reject"],
        "moves": moves,
        "operator_conflict_on_move": conflicts,
        "phrase_specific_rule_fired": bool(phrase_specific_rule_fired),
        "measurement_eligible": verified,
        "select_authorized": False,
        "revision_eligible": False,
    }


def measurement_allowed(report: dict) -> bool:
    return bool(
        report.get("regression") == "REGRESSION_VERIFIED"
        and report.get("phrase_specific_rule_fired") is False
        and not report.get("failures")
        and report.get("measurement_eligible") is True
        and report.get("operator_conflict_on_move") == 0
    )


def _decision(prior, nxt, primary, normalized, *, inspected: bool) -> dict:
    return {
        "rule": RULE_VERSION,
        "v4_bucket": prior,
        "v5_bucket": nxt,
        "primary_evidence": primary,
        "supporting_evidence": [],
        "normalized": normalized,
        "inspected": inspected,
    }


def _inspect(surface: str, gloss: str, lexicon) -> str | None:
    found = lexicon.entry(surface)
    if found is None:
        return None
    content = _content(surface)
    stems = {item for item in (_stem(token) for token in content) if item}
    ordinary, missing, senses = _ordinary(content, lexicon)
    if _designates(found, stems, content):
        return REJECT_EVIDENCE
    if _noncompositional(found, gloss, content, stems, ordinary, missing, senses):
        return HIGH_EVIDENCE
    return None


def _designates(found: Entry, stems: set[str], content: list[str]) -> bool:
    if any(char.isupper() for char in found.lemma):
        return True
    if found.lex == "adj.pert":
        return True
    if found.lex in _LIFE and _exocentric_life(found.hypernyms, stems):
        return True
    if _exocentric_category(found.hypernyms, stems) and not _ordinary_synonym(found.lemmas, content):
        return True
    return False


def _noncompositional(found: Entry, gloss, content, stems, ordinary, missing, senses) -> bool:
    if _blocked(gloss, ordinary, missing, content):
        return False
    if _orthographic(content) or _body_clash(found, gloss, content, senses):
        return True
    if _verb_shift(found, content, senses):
        return True
    return (
        found.pos == "adv"
        and _unrelated_paraphrase(found.lemmas, content, stems)
        and not _morphological(found.lemmas, content, stems)
    )


def _blocked(gloss: str, ordinary: set[str], missing: list[str], content: list[str]) -> bool:
    words = _WORD.findall(gloss or "")
    if words and words[0].casefold() in _META:
        return True
    if missing or len(content) != len(set(content)):
        return True
    return bool(_stems(gloss) & ordinary)


def _ordinary(content: list[str], lexicon):
    ordinary: set[str] = set()
    missing: list[str] = []
    senses: list[Sense] = []
    for token in content:
        if len(token) < 3:
            continue
        found = tuple(lexicon.senses(token))
        if not found:
            missing.append(token)
            continue
        for sense in found:
            ordinary |= _stems(sense.gloss)
            stemmed = _stem(token)
            if stemmed:
                ordinary.add(stemmed)
            senses.append(sense)
    return ordinary, missing, senses


def _exocentric_life(hypernyms, stems: set[str]) -> bool:
    if not hypernyms:
        return False
    for lemmas in hypernyms:
        for lemma in lemmas:
            if any(_stem(part) in stems for part in re.split(r"[_-]", lemma)):
                return False
    return True


def _exocentric_category(hypernyms, stems: set[str]) -> bool:
    for lemmas in hypernyms:
        for lemma in lemmas:
            if "_" not in lemma:
                continue
            parts = [part for part in (_stem(item) for item in re.split(r"[_-]", lemma)) if part]
            if parts and not any(part in stems for part in parts):
                return True
    return False


def _ordinary_synonym(lemmas, content: list[str]) -> bool:
    owned = set(content)
    for lemma in _single_words(lemmas):
        if _initialism(lemma):
            continue
        low = re.sub(r"[^a-z]", "", lemma.casefold())
        if low and low not in owned:
            return True
    return False


def _body_clash(found: Entry, gloss: str, content: list[str], senses: list[Sense]) -> bool:
    if found.lex == "noun.body":
        return False
    if not any(sense.lex == "noun.body" for sense in senses):
        return False
    gloss_l = (gloss or "").casefold()
    return not any(token in gloss_l for token in content)


def _verb_shift(found: Entry, content: list[str], senses: list[Sense]) -> bool:
    if found.pos != "verb" or not content or found.lex.endswith(".all"):
        return False
    head = content[0]
    head_lex = next((sense.lex for sense in senses if sense.token == head and sense.pos == "verb"), None)
    if not head_lex or head_lex.endswith(".all") or head_lex == found.lex:
        return False
    return True


def _unrelated_paraphrase(lemmas, content, stems) -> bool:
    return any(not _related(lemma, content, stems) for lemma in _single_words(lemmas))


def _morphological(lemmas, content, stems) -> bool:
    return any(_related(lemma, content, stems) for lemma in _single_words(lemmas))


def _related(lemma: str, content: list[str], stems: set[str]) -> bool:
    low = lemma.casefold()
    stemmed = _stem(low)
    if stemmed and stemmed in stems:
        return True
    return any(len(token) >= 4 and (token in low or low in token) for token in content)


def _orthographic(content: list[str]) -> bool:
    return any(len(token) == 1 and token.isalpha() for token in content)


def _single_words(lemmas) -> list[str]:
    return [lemma for lemma in lemmas if "_" not in lemma and "-" not in lemma and "(" not in lemma]


def _initialism(lemma: str) -> bool:
    letters = re.sub(r"[^A-Za-z]", "", lemma)
    return bool(letters) and letters.isupper()


def _content(surface: str) -> list[str]:
    text = surface.casefold().replace("-", " ")
    return [token for token in _TOKEN.findall(text) if token not in _FUNCTION]


def _stem(word: str) -> str:
    token = word.casefold().strip("'")
    if len(token) < 3 or token in _FUNCTION:
        return ""
    return token[:4]


def _stems(text: str) -> set[str]:
    return {item for item in (_stem(word) for word in _WORD.findall(text or "")) if item}


def _lexnames(path: Path) -> dict[int, str]:
    names = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        number, name, *_rest = line.split()
        names[int(number)] = name
    return names


def _load_index(path: Path) -> dict[str, list[str]]:
    found = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line[0] == " ":
            continue
        parts = line.split()
        synset_cnt = int(parts[2])
        pointer_cnt = int(parts[3])
        rest = parts[4 + pointer_cnt:]
        found[parts[0]] = rest[2:2 + synset_cnt]
    return found


def _load_data(path: Path) -> dict[str, str]:
    found = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line[0] == " ":
            continue
        found[line.split(" ", 1)[0]] = line
    return found


def _parse(line: str, lexnames: dict[int, str], noun_data: dict[str, str]):
    parts = line.split()
    lex = lexnames[int(parts[1])]
    count = int(parts[3], 16)
    lemmas = []
    index = 4
    for _ in range(count):
        lemmas.append(parts[index])
        index += 2
    pointer_cnt = int(parts[index])
    index += 1
    hypers = []
    for _ in range(pointer_cnt):
        symbol, target, target_pos = parts[index], parts[index + 1], parts[index + 2]
        index += 4
        if symbol in {"@", "@i"} and target_pos == "n" and target in noun_data:
            hyper, _lex, _nested = _parse(noun_data[target], lexnames, noun_data)
            hypers.append(hyper)
    return lemmas, lex, hypers
