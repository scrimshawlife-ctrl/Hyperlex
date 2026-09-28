"""One high challenge over a frozen v6 bucket.

A provisional high may fall to secondary when ordinary compositional derivation
fires. That demotion stops. Reject and secondary buckets stay at the v6
decision: those transitions were already applied, and a stopped demotion is
not reopened. The v6 high-challenge evidence is not a v7 transition.
"""

from __future__ import annotations

import re

from hyperlexical.unbind_screen_v4 import canonical_bucket, normalize_lexical
from hyperlexical.unbind_screen_v5 import (
    HIGH_EVIDENCE,
    REJECT_EVIDENCE,
    _FUNCTION,
    _WORD,
    _content,
    _initialism,
    _related,
    _single_words,
    _stem,
)
from hyperlexical.unbind_screen_v6 import NONREFERENTIAL_EVIDENCE, apply_v6

RULE_VERSION = "RUNE.UNBIND_SCREEN.v7"
ORDINARY_EVIDENCE = "ordinary_compositional_derivation"
_COMPARATIVE_GLOSS = re.compile(r"^used to form the comparative\b", re.IGNORECASE)
_DEGREE_SENSE = re.compile(r"^(?:of less|of more|of greater|of smaller)\b", re.IGNORECASE)
_METAPHOR = re.compile(r"\bmetaphors?\b|\bmetaphorical(?:ly)?\b", re.IGNORECASE)
_PARTICLE = frozenset({
    "out", "off", "up", "down", "away", "back", "over", "through", "along",
})


def apply_v7(v6_bucket: str, surface: str, gloss: str, source_pos: str, lexicon) -> dict:
    """Return the v7 bucket. Only a provisional high is eligible for the new predicate."""
    bucket = canonical_bucket(v6_bucket)
    normalized = normalize_lexical(surface)
    if bucket == "HIGH":
        if ordinary_compositional_derivation(surface or "", gloss or "", lexicon):
            return _decision(bucket, "SECONDARY", ORDINARY_EVIDENCE, normalized, inspected=True)
        return _decision(bucket, "HIGH", None, normalized, inspected=True)
    if bucket == "REJECT":
        inherited = apply_v6(bucket, surface, gloss, source_pos, lexicon)
        return _decision(
            bucket,
            inherited["v6_bucket"],
            inherited["primary_evidence"],
            normalized,
            inspected=bool(inherited["inspected"]),
        )
    if bucket != "SECONDARY":
        raise ValueError(f"provisional bucket {bucket} is outside HIGH, REJECT, and SECONDARY")
    # v6 already ran the secondary transitions. Running them again would reopen
    # a demotion that v6 stopped, so the frozen secondary decision stands.
    return _decision(bucket, "SECONDARY", None, normalized, inspected=False)


def ordinary_compositional_derivation(surface: str, gloss: str, lexicon) -> bool:
    """True when the recorded sense is ordinary composition, not a stored binding.

    Stem overlap with a constituent gloss is not enough, and a metaphorical
    retelling of the gloss is not enough. The lexical record has to present a
    comparative, syntactic, or phrasal composition with no unrelated synonym.
    """
    found = lexicon.entry(surface)
    if found is None or _stored_binding(found, surface) or _METAPHOR.search(gloss or ""):
        return False
    return (
        _comparative(found, surface, gloss, lexicon)
        or _syntactic(surface, gloss, lexicon)
        or _phrasal(surface, gloss, lexicon)
    )


def assess(rows: list[dict], *, phrase_specific_rule_fired: bool, expected_rows: int = 197) -> dict:
    """Regression gate. Previously correct rows must stay correct. Buckets may move."""
    failures: list[str] = []
    surfaces = [str(row["surface"]) for row in rows]
    if len(rows) != expected_rows:
        failures.append(f"replay rows {len(rows)} != {expected_rows}")
    if len(set(surfaces)) != len(surfaces):
        failures.append("replay surface is duplicated")
    moves = {
        "high_to_secondary": 0,
        "reject_to_secondary": 0,
        "secondary_to_high": 0,
        "secondary_to_reject": 0,
        "unchanged": 0,
    }
    previously_correct = 0
    previously_correct_lost = 0
    correct_high = 0
    correct_high_lost = 0
    direct_swaps = 0
    for row in rows:
        prior = canonical_bucket(str(row["v6_bucket"]))
        nxt = canonical_bucket(str(row["v7_bucket"]))
        operator = canonical_bucket(str(row["operator_bucket"]))
        primary = row.get("primary_evidence")
        supporting = list(row.get("supporting_evidence") or [])
        if prior == operator:
            previously_correct += 1
            if nxt != operator:
                previously_correct_lost += 1
                failures.append("previously correct row is no longer correct")
        if prior == "HIGH" and operator == "HIGH":
            correct_high += 1
            if nxt != "HIGH":
                correct_high_lost += 1
                failures.append("previously correct HIGH was demoted")
        if prior == nxt:
            moves["unchanged"] += 1
            if primary is not None or supporting:
                failures.append("unchanged row carries transition evidence")
        elif prior == "HIGH" and nxt == "SECONDARY":
            moves["high_to_secondary"] += 1
            if primary != ORDINARY_EVIDENCE or supporting:
                failures.append("HIGH to SECONDARY lacks ordinary_compositional_derivation")
        elif prior == "REJECT" and nxt == "SECONDARY":
            moves["reject_to_secondary"] += 1
            if primary != NONREFERENTIAL_EVIDENCE or supporting:
                failures.append("REJECT to SECONDARY lacks nonreferential_lexical_use")
        elif prior == "SECONDARY" and nxt == "HIGH":
            moves["secondary_to_high"] += 1
            if primary != HIGH_EVIDENCE or supporting:
                failures.append("SECONDARY to HIGH lacks lexicalized_noncompositional")
        elif prior == "SECONDARY" and nxt == "REJECT":
            moves["secondary_to_reject"] += 1
            if primary != REJECT_EVIDENCE or supporting:
                failures.append("SECONDARY to REJECT lacks referential_terminological_dominance")
        elif {prior, nxt} == {"HIGH", "REJECT"}:
            direct_swaps += 1
            failures.append("HIGH and REJECT swapped directly")
        else:
            failures.append("row moved outside the legal transitions")
        if prior != nxt and primary is None:
            failures.append("changed row has no primary evidence")
    if phrase_specific_rule_fired:
        failures.append("phrase-specific rule fired")
    assertions = {
        "A_replay_197": len(rows) == expected_rows and len(set(surfaces)) == len(surfaces),
        "B_previously_correct_remain_correct": previously_correct_lost == 0,
        "C_high_demotion_evidence": "HIGH to SECONDARY lacks ordinary_compositional_derivation" not in failures,
        "D_correct_high_stays_high": correct_high_lost == 0,
        "E_v6_transitions_unchanged": (
            "REJECT to SECONDARY lacks nonreferential_lexical_use" not in failures
            and "SECONDARY to HIGH lacks lexicalized_noncompositional" not in failures
            and "SECONDARY to REJECT lacks referential_terminological_dominance" not in failures
            and moves["secondary_to_high"] == 0
            and moves["secondary_to_reject"] == 0
            and moves["reject_to_secondary"] == 0
        ),
        "F_no_direct_outer_swap": direct_swaps == 0,
        "G_no_phrase_rules": not phrase_specific_rule_fired,
        "H_demotion_stops": moves["high_to_secondary"] == 0 or "HIGH to SECONDARY lacks ordinary_compositional_derivation" not in failures,
        "I_measurement_not_drawn": True,
    }
    verified = not failures and all(assertions.values())
    return {
        "schema": "hyperlex.unbind_screen_v7_gate_report.v1",
        "rule": RULE_VERSION,
        "regression": "REGRESSION_VERIFIED" if verified else "REGRESSION_FAILED",
        "state": "REGRESSION_VERIFIED" if verified else "ENCODED",
        "failures": failures,
        "assertions": assertions,
        "expected_rows": expected_rows,
        "replay_rows": len(rows),
        "unique_surfaces": len(set(surfaces)),
        "previously_correct": previously_correct,
        "previously_correct_lost": previously_correct_lost,
        "correct_high": correct_high,
        "correct_high_lost": correct_high_lost,
        "direct_swaps": direct_swaps,
        "moves": moves,
        "phrase_specific_rule_fired": bool(phrase_specific_rule_fired),
        "measurement_eligible": False,
        "measurement_sample_drawn": False,
        "regression_is_not_generalization": True,
        "select_authorized": False,
        "revision_eligible": False,
    }


def _decision(prior, nxt, primary, normalized, *, inspected: bool) -> dict:
    return {
        "rule": RULE_VERSION,
        "v6_bucket": prior,
        "v7_bucket": nxt,
        "primary_evidence": primary,
        "supporting_evidence": [],
        "normalized": normalized,
        "inspected": inspected,
    }


def _stored_binding(found, surface: str) -> bool:
    """An unrelated single-word synonym is a stored conventionalized binding."""
    content = _content(surface)
    stems = {item for item in (_stem(token) for token in content) if item}
    for lemma in _single_words(found.lemmas):
        if _initialism(lemma):
            continue
        if not _related(lemma, content, stems):
            return True
    return False


def _comparative(found, surface: str, gloss: str, lexicon) -> bool:
    """A periphrastic comparative whose record is the degree construction itself."""
    if found.lex != "adv.all" or not _COMPARATIVE_GLOSS.match((gloss or "").strip()):
        return False
    return any(_degree_adjective(token, lexicon) for token in _content(surface))


def _degree_adjective(token: str, lexicon) -> bool:
    if len(token) < 5 or not token.endswith("er"):
        return False
    for sense in lexicon.senses(token):
        if sense.pos != "adj" and sense.lex != "adj.all":
            continue
        if _DEGREE_SENSE.match((sense.gloss or "").strip()):
            return True
    return False


def _syntactic(surface: str, gloss: str, lexicon) -> bool:
    """The gloss is the recorded senses of two open-class constituents, in order."""
    heads = [token for token in _content(surface) if token not in _PARTICLE]
    if len(heads) < 2:
        return False
    return _gloss_is_sense_sum(heads, gloss, lexicon)


def _phrasal(surface: str, gloss: str, lexicon) -> bool:
    """The gloss is a verb sense plus one particle sense, with nothing left over."""
    content = _content(surface)
    particles = [token for token in content if token in _PARTICLE]
    heads = [token for token in content if token not in _PARTICLE]
    if len(particles) != 1 or len(heads) != 1:
        return False
    if not any(sense.pos == "verb" for sense in lexicon.senses(heads[0])):
        return False
    return _gloss_is_sense_sum([heads[0], particles[0]], gloss, lexicon)


def _gloss_is_sense_sum(tokens: list[str], gloss: str, lexicon) -> bool:
    target = _open_words(gloss)
    if len(target) < 2:
        return False
    choices: list[tuple[tuple[str, ...], ...]] = []
    for token in tokens:
        glosses = tuple(_open_words(sense.gloss) for sense in lexicon.senses(token) if _open_words(sense.gloss))
        if not glosses:
            return False
        choices.append(glosses)
    return _any_concatenation(choices, target)


def _any_concatenation(choices: list[tuple[tuple[str, ...], ...]], target: list[str]) -> bool:
    def walk(index: int, built: list[str]) -> bool:
        if index == len(choices):
            return built == target and all(built)
        for gloss in choices[index]:
            if walk(index + 1, built + list(gloss)):
                return True
        return False

    return walk(0, [])


def _open_words(text: str) -> list[str]:
    return [
        word.casefold()
        for word in _WORD.findall(text or "")
        if word.casefold() not in _FUNCTION and len(word) >= 3
    ]
