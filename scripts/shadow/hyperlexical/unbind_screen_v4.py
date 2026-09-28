"""Secondary-only coverage patch over a frozen v3 bucket.

Input is the v3 bucket, the surface, and the first-sense gloss.
A row is inspected only when that bucket is SECONDARY.
Patch A may move SECONDARY to REJECT. Patch B may move SECONDARY to HIGH.
Existing HIGH and REJECT decisions are returned unchanged.
"""

from __future__ import annotations

import ast
import re
import unicodedata
from pathlib import Path

from hyperlexical.unbind_screen_v3 import NUMBERS, PARTICLES, STOP, stems

RULE_VERSION = "RUNE.UNBIND_SCREEN.v4"
PATCH_A = (
    "multi_token_person_name",
    "organization_from_gloss",
    "species_or_common_name_referent",
    "medical_technical_expression",
    "productive_number",
)
PATCH_B = (
    "nonliteral_semantic_shift",
    "conventionalized_idiom",
    "noncompositional_phrasal_binding",
    "fixed_lexicalized_expression",
)
_CANONICAL = {
    "HIGH_VALUE": "HIGH",
    "HIGH": "HIGH",
    "SECONDARY": "SECONDARY",
    "REJECT": "REJECT",
    "QUARANTINE": "QUARANTINE",
}
_HYPHEN = re.compile(r"(?<=\w)[\u2010\u2011\u2012\u2013\u2014-](?=\w)")
_PUNCT = re.compile(r"[^\w\s']+", re.UNICODE)
_WORD = re.compile(r"[A-Za-z]+")
_DELIMITERS = frozenset({
    "with", "that", "which", "used", "yielding", "having", "resulting", "who", "whose",
})
_MULTIPLIERS = frozenset({"times", "fold"})
_CLINICAL = frozenset({
    "impairment", "disease", "disorder", "syndrome", "inflammation", "symptom",
    "lesion", "pathology", "hemorrhage", "haemorrhage", "infection", "paralysis",
    "fracture", "tumor", "tumour", "carcinoma", "edema", "oedema", "surgery",
    "surgical", "clinical",
})
_COMPARATIVES = frozenset({
    "better", "worse", "greater", "lesser", "more", "less", "higher", "lower",
    "bigger", "smaller", "older", "younger", "sooner", "later", "richer", "poorer",
    "well",
})
_INTENSIFIERS = frozenset({
    "bone", "brand", "stone", "rock", "pitch", "crystal", "soaking", "dripping",
    "stark", "dirt", "stock", "wide",
})
_LIGHT_VERBS = frozenset({"give", "take", "have", "make", "get"})
_DETERMINERS = frozenset({"a", "an", "the"})
_LIFE = frozenset({"noun.animal", "noun.plant"})

SUCCESS_CRITERIA = {
    "schema": "hyperlex.unbind_screen_v4_success_criteria.v1",
    "high_precision_floor": 1.0,
    "reject_precision_floor": 1.0,
    "false_high_allowed": 0,
    "false_reject_allowed": 0,
    "false_secondary_rate_must_be_strictly_below": "13/29",
    "gate_b_violations_allowed": 0,
    "gate_e_violations_allowed": 0,
    "hand_corrections_allowed": 0,
    "sample_reuse_allowed": False,
    "perfect_accuracy_required": False,
    "question": "reduce_secondary_fallthrough_without_false_high_or_false_reject",
}


class ScreenV4Error(ValueError):
    pass


class EmptyLexicon:
    def noun_lex(self, lemma: str) -> str | None:
        return None

    def has_adjective(self, lemma: str) -> bool:
        return False


class WordNetLexicon:
    """First-sense lex-file names. Used as gloss evidence, not as a phrase list."""

    def __init__(self, root: str | Path):
        base = Path(root)
        self._lexnames = _lexnames(base / "lexnames")
        noun_offset = _offset_lexnum(base / "data.noun")
        self._noun = {
            lemma: self._lexnames.get(noun_offset[offset])
            for lemma, offset in _first_offsets(base / "index.noun").items()
            if offset in noun_offset
        }
        self._adj = set(_first_offsets(base / "index.adj"))

    def noun_lex(self, lemma: str) -> str | None:
        return self._noun.get(lemma.casefold())

    def has_adjective(self, lemma: str) -> bool:
        return lemma.casefold() in self._adj


def normalize_lexical(surface: str) -> str:
    """Fold hyphenation and punctuation. Apostrophes stay lexical."""
    text = unicodedata.normalize("NFKC", surface).casefold()
    text = text.replace("\u2019", "'").replace("`", "'")
    text = _HYPHEN.sub(" ", text)
    text = _PUNCT.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def canonical_bucket(raw: str) -> str:
    bucket = _CANONICAL.get(str(raw or ""))
    if bucket is None:
        raise ScreenV4Error(f"bucket {raw!r} is not a screen bucket")
    return bucket


def apply_v4(v3_bucket: str, surface: str, gloss: str, source_pos: str, lexicon) -> dict:
    """Return the v4 bucket. HIGH and REJECT are not inspected."""
    bucket = canonical_bucket(v3_bucket)
    normalized = normalize_lexical(surface)
    if bucket != "SECONDARY":
        return _decision(bucket, bucket, None, [], normalized, inspected=False)
    tokens = normalized.split() if normalized else []
    gloss_text = gloss or ""
    gstem = set(stems(gloss_text))
    patch_a = _patch_a(tokens, source_pos, gloss_text, lexicon)
    if patch_a:
        return _decision("SECONDARY", "REJECT", patch_a[0], patch_a[1:], normalized, inspected=True)
    patch_b = _patch_b(tokens, source_pos, gloss_text, gstem)
    if patch_b:
        return _decision("SECONDARY", "HIGH", patch_b[0], patch_b[1:], normalized, inspected=True)
    return _decision("SECONDARY", "SECONDARY", None, [], normalized, inspected=True)


def assess(rows: list[dict], *, phrase_specific_rule_fired: bool, expected_rows: int = 113) -> dict:
    """Mechanical GATE_A through GATE_E report. This is not a precision score."""
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
        v3 = canonical_bucket(str(row["v3_bucket"]))
        v4 = canonical_bucket(str(row["v4_bucket"]))
        operator = canonical_bucket(str(row["operator_bucket"]))
        primary = row.get("primary_evidence")
        supporting = list(row.get("supporting_evidence") or [])
        if v3 == "HIGH":
            held["high"] += 1
            if v4 != "HIGH":
                failures.append("HIGH row changed bucket")
            if operator == "HIGH" and v4 != "HIGH":
                failures.append("v3-correct HIGH is no longer operator-correct")
        elif v3 == "REJECT":
            held["reject"] += 1
            if v4 != "REJECT":
                failures.append("REJECT row changed bucket")
            if operator == "REJECT" and v4 != "REJECT":
                failures.append("v3-correct REJECT is no longer operator-correct")
        elif v3 == "SECONDARY":
            if v4 == "SECONDARY":
                moves["secondary_unchanged"] += 1
                if primary is not None or supporting:
                    failures.append("unchanged SECONDARY carries transition evidence")
            elif v4 == "HIGH":
                moves["secondary_to_high"] += 1
                _require_transition(primary, supporting, PATCH_B, failures)
            elif v4 == "REJECT":
                moves["secondary_to_reject"] += 1
                _require_transition(primary, supporting, PATCH_A, failures)
            else:
                failures.append("SECONDARY moved outside HIGH and REJECT")
        else:
            failures.append("v3 bucket is outside HIGH, REJECT, and SECONDARY")
        if v3 != v4 and operator != v4:
            conflicts += 1
        if v3 != v4 and primary is None:
            failures.append("changed row has no primary evidence")
    if phrase_specific_rule_fired:
        failures.append("phrase-specific rule fired")
    verified = not failures
    return {
        "schema": "hyperlex.unbind_screen_v4_gate_report.v1",
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
        "gate_b_violations": sum(1 for item in failures if "operator-correct" in item or "changed bucket" in item),
        "gate_e_violations": sum(
            1 for item in failures
            if "changed bucket" in item or "outside HIGH and REJECT" in item or "no primary" in item
            or "unchanged SECONDARY" in item or "moved outside" in item
        ),
        "assertions": {
            "A_historical_replay": len(rows) == expected_rows and len(set(surfaces)) == len(surfaces),
            "B_outer_bucket_preservation": not any("operator-correct" in item or "changed bucket" in item for item in failures),
            "C_patch_a_targeting": not any(item.startswith("SECONDARY to REJECT") for item in failures),
            "D_patch_b_targeting": not any(item.startswith("SECONDARY to HIGH") for item in failures),
            "E_no_other_movement": not any(
                "changed bucket" in item or "outside HIGH" in item or "moved outside" in item
                for item in failures
            ),
            "no_phrase_specific_rule": not phrase_specific_rule_fired,
        },
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
    )


def rule_surface_violations(source: str, forbidden: list[str] | tuple[str, ...]) -> list[str]:
    """Return phrase-rule violations in scorer source. The probe list is not a rule."""
    found = [phrase for phrase in forbidden if phrase and phrase in source]
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            if not any(isinstance(op, (ast.Eq, ast.NotEq)) for op in node.ops):
                continue
            candidates = [node.left, *node.comparators]
        elif isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            candidates = list(node.elts)
        elif isinstance(node, ast.Dict):
            candidates = [item for item in (*node.keys, *node.values) if item is not None]
        else:
            continue
        for item in candidates:
            if (
                isinstance(item, ast.Constant)
                and isinstance(item.value, str)
                and len(item.value.split()) >= 2
            ):
                found.append(item.value)
    found.extend(re.findall(r"\b[0-9a-f]{64}\b", source))
    return found


def _decision(v3, v4, primary, supporting, normalized, *, inspected: bool) -> dict:
    return {
        "rule": RULE_VERSION,
        "v3_bucket": v3,
        "v4_bucket": v4,
        "primary_evidence": primary,
        "supporting_evidence": list(supporting),
        "normalized": normalized,
        "inspected": inspected,
    }


def _require_transition(primary, supporting, allowed: tuple[str, ...], failures: list[str]) -> None:
    label = "SECONDARY to HIGH" if allowed is PATCH_B else "SECONDARY to REJECT"
    if primary not in allowed:
        failures.append(f"{label} lacks patch evidence")
        return
    if supporting.count(primary) or primary in supporting:
        failures.append(f"{label} repeats its primary evidence")
    if len([primary]) != 1:
        failures.append(f"{label} lacks one primary evidence")
    extra = [item for item in supporting if item not in allowed]
    if extra:
        failures.append(f"{label} supporting evidence is outside the patch")


def _patch_a(tokens: list[str], pos: str, gloss: str, lexicon) -> list[str]:
    nouns = _span_nouns(gloss, lexicon)
    matched = []
    if _person(tokens, pos, nouns):
        matched.append("multi_token_person_name")
    if _organization(tokens, pos, nouns):
        matched.append("organization_from_gloss")
    if _species(tokens, pos, nouns):
        matched.append("species_or_common_name_referent")
    if _medical(tokens, pos, gloss, lexicon):
        matched.append("medical_technical_expression")
    if _productive_number(tokens):
        matched.append("productive_number")
    return matched


def _patch_b(tokens: list[str], pos: str, gloss: str, gstem: set[str]) -> list[str]:
    matched = []
    if _nonliteral(tokens, pos, gstem):
        matched.append("nonliteral_semantic_shift")
    if _conventionalized(tokens, pos, gstem):
        matched.append("conventionalized_idiom")
    if _phrasal(tokens, pos, gloss, gstem):
        matched.append("noncompositional_phrasal_binding")
    if _fixed(tokens, pos, gstem):
        matched.append("fixed_lexicalized_expression")
    return matched


def _person(tokens: list[str], pos: str, nouns: list[tuple[str, str]]) -> bool:
    if pos != "noun" or not _name_shape(tokens) or not nouns:
        return False
    head, lex = nouns[0]
    return lex == "noun.person" and head not in tokens


def _organization(tokens: list[str], pos: str, nouns: list[tuple[str, str]]) -> bool:
    if pos != "noun" or not nouns:
        return False
    head, lex = nouns[0]
    return lex == "noun.group" and head not in tokens


def _species(tokens: list[str], pos: str, nouns: list[tuple[str, str]]) -> bool:
    if pos != "noun":
        return False
    return any(lex in _LIFE and lemma not in tokens for lemma, lex in nouns)


def _medical(tokens: list[str], pos: str, gloss: str, lexicon) -> bool:
    if pos != "noun":
        return False
    words = {tok.lower() for tok in _WORD.findall(gloss or "")}
    if words.isdisjoint(_CLINICAL):
        return False
    for lemma, lex in _all_nouns(gloss, lexicon):
        if lex == "noun.body" and lemma not in tokens:
            return True
    return False


def _productive_number(tokens: list[str]) -> bool:
    if len(tokens) < 2:
        return False
    body = list(tokens)
    if body[0] in {"a", "an"}:
        body = body[1:]
    if body and body[-1] in _MULTIPLIERS:
        body = body[:-1]
    if not body:
        return False
    return all(tok in NUMBERS or tok == "and" for tok in body) and any(tok in NUMBERS for tok in body)


def _name_shape(tokens: list[str]) -> bool:
    if len(tokens) < 2:
        return False
    return all(
        re.fullmatch(r"[a-z]+", tok) and tok not in STOP and tok not in PARTICLES
        for tok in tokens
    )


def _span_nouns(gloss: str, lexicon) -> list[tuple[str, str]]:
    found = []
    for low in _gloss_words(gloss):
        if low in _DELIMITERS and found:
            break
        item = _noun(low, lexicon)
        if item is not None:
            found.append(item)
    return found


def _all_nouns(gloss: str, lexicon) -> list[tuple[str, str]]:
    return [item for low in _gloss_words(gloss) if (item := _noun(low, lexicon)) is not None]


def _gloss_words(gloss: str) -> list[str]:
    return [tok.lower() for tok in _WORD.findall(gloss or "") if tok.lower() not in STOP]


def _noun(low: str, lexicon) -> tuple[str, str] | None:
    if lexicon.has_adjective(low):
        return None
    lex = lexicon.noun_lex(low)
    if not lex:
        return None
    return low, lex


def _content(tokens: list[str]) -> list[str]:
    return [tok for tok in tokens if len(tok) >= 3 and tok not in STOP]


def _absent(token: str, gstem: set[str]) -> bool:
    return len(token) >= 3 and token[:4] not in gstem


def _nonliteral(tokens: list[str], pos: str, gstem: set[str]) -> bool:
    return any((
        _verb_the(tokens, pos, gstem),
        _verb_determiner(tokens, pos, gstem),
        _verb_pivot_noun(tokens, pos, gstem),
        _in_the_head(tokens, pos, gstem),
    ))


def _conventionalized(tokens: list[str], pos: str, gstem: set[str]) -> bool:
    return any((
        _like_vehicle(tokens, pos, gstem),
        _as_frame(tokens, pos, gstem),
        _for_all(tokens, pos, gstem),
        _light_verb(tokens, pos, gstem),
    ))


def _verb_the(tokens: list[str], pos: str, gstem: set[str]) -> bool:
    if pos != "verb" or len(tokens) < 3 or tokens[1] != "the":
        return False
    content = _content(tokens)
    return bool(content) and all(_absent(tok, gstem) for tok in content)


def _verb_determiner(tokens: list[str], pos: str, gstem: set[str]) -> bool:
    if pos != "verb" or len(tokens) != 3 or tokens[1] not in {"a", "an"}:
        return False
    content = _content(tokens)
    return bool(content) and all(_absent(tok, gstem) for tok in content)


def _verb_pivot_noun(tokens: list[str], pos: str, gstem: set[str]) -> bool:
    if pos != "verb" or len(tokens) != 4:
        return False
    if tokens[1] not in {"on", "in"} or tokens[2] not in {"a", "an"}:
        return False
    return _absent(tokens[3], gstem)


def _in_the_head(tokens: list[str], pos: str, gstem: set[str]) -> bool:
    if pos not in {"adj", "adv", "noun"} or len(tokens) != 4:
        return False
    if tokens[0] != "in" or tokens[1] != "the":
        return False
    content = _content(tokens)
    present = [tok for tok in content if tok[:4] in gstem]
    return bool(present) and _absent(tokens[-1], gstem)


def _like_vehicle(tokens: list[str], pos: str, gstem: set[str]) -> bool:
    if pos not in {"adj", "adv"} or len(tokens) != 3:
        return False
    if tokens[0] != "like" or tokens[1] not in {"a", "an"}:
        return False
    return _absent(tokens[2], gstem)


def _as_frame(tokens: list[str], pos: str, gstem: set[str]) -> bool:
    if pos not in {"adj", "adv"} or len(tokens) != 3 or tokens[1] != "as":
        return False
    return _absent(tokens[2], gstem)


def _for_all(tokens: list[str], pos: str, gstem: set[str]) -> bool:
    if pos != "adv" or len(tokens) < 4 or tokens[:2] != ["for", "all"]:
        return False
    content = _content(tokens)
    present = [tok for tok in content if tok[:4] in gstem]
    return bool(present) and _absent(tokens[-1], gstem)


def _light_verb(tokens: list[str], pos: str, gstem: set[str]) -> bool:
    if pos != "verb" or not tokens or tokens[0] not in _LIGHT_VERBS:
        return False
    if not any(tok in _DETERMINERS for tok in tokens) or not gstem:
        return False
    surface = {tok[:4] for tok in _content(tokens)}
    if not gstem <= surface:
        return False
    return _absent(tokens[0], gstem) or len(tokens[0]) < 3


def _phrasal(tokens: list[str], pos: str, gloss: str, gstem: set[str]) -> bool:
    if pos not in {"verb", "adj"} or not tokens or tokens[-1] not in PARTICLES:
        return False
    if tokens[0] in _COMPARATIVES:
        return False
    gloss_words = {tok.lower() for tok in _WORD.findall(gloss or "")}
    if tokens[-1] in gloss_words:
        return False
    return _absent(tokens[0], gstem) or len(tokens[0]) < 3


def _fixed(tokens: list[str], pos: str, gstem: set[str]) -> bool:
    return _intensifier(tokens, pos, gstem) or _for_result(tokens, pos, gstem)


def _intensifier(tokens: list[str], pos: str, gstem: set[str]) -> bool:
    if pos != "adj" or len(tokens) != 2 or tokens[0] not in _INTENSIFIERS:
        return False
    return _absent(tokens[1], gstem)


def _for_result(tokens: list[str], pos: str, gstem: set[str]) -> bool:
    if pos not in {"adj", "verb"} or not (2 <= len(tokens) <= 4) or "for" not in tokens:
        return False
    content = _content(tokens)
    return bool(content) and all(_absent(tok, gstem) for tok in content)


def _lexnames(path: Path) -> dict[int, str]:
    names = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        number, name, *_rest = line.split()
        names[int(number)] = name
    return names


def _offset_lexnum(path: Path) -> dict[str, int]:
    found = {}
    for line in path.open(encoding="utf-8", errors="replace"):
        if not line or line[0] == " ":
            continue
        offset, lexnum, *_rest = line.split(" ", 2)
        found[offset] = int(lexnum)
    return found


def _first_offsets(path: Path) -> dict[str, str]:
    found = {}
    for line in path.open(encoding="utf-8", errors="replace"):
        if not line or line[0] == " ":
            continue
        parts = line.split()
        synset_cnt = int(parts[2])
        pointer_cnt = int(parts[3])
        rest = parts[4 + pointer_cnt:]
        offsets = rest[2:2 + synset_cnt]
        if not offsets:
            continue
        found[parts[0].casefold()] = offsets[0]
    return found
