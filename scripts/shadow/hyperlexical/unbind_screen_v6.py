"""Challengeable outer buckets over a frozen v5 decision.

A frozen v5 bucket is provisional. High may fall to secondary when the gloss
is recoverable from ordinary constituent senses and ordinary syntax. Reject
may fall to secondary when the surface is a lexical state or relation rather
than a designation. A demotion stops for that application. A provisional
secondary row may still move by the two v5 evidences. High and reject do not
swap.
"""

from __future__ import annotations

import re

from hyperlexical.unbind_screen_v4 import canonical_bucket, normalize_lexical
from hyperlexical.unbind_screen_v5 import (
    HIGH_EVIDENCE,
    REJECT_EVIDENCE,
    Entry,
    _body_clash,
    _content,
    _exocentric_category,
    _exocentric_life,
    _initialism,
    _ordinary,
    _ordinary_synonym,
    _orthographic,
    _related,
    _single_words,
    _stem,
    _stems,
    _verb_shift,
    _LIFE,
)

RULE_VERSION = "RUNE.UNBIND_SCREEN.v6"
COMPOSITIONAL_EVIDENCE = "compositional_recoverability"
NONREFERENTIAL_EVIDENCE = "nonreferential_lexical_use"
_RELATIONAL = re.compile(r"^(of or relating to|relating to|related to)\b", re.IGNORECASE)


def apply_v6(v5_bucket: str, surface: str, gloss: str, source_pos: str, lexicon) -> dict:
    """Return the v6 bucket. A demoted row is not reconsidered."""
    del source_pos
    bucket = canonical_bucket(v5_bucket)
    normalized = normalize_lexical(surface)
    if bucket == "HIGH":
        if _compositional(surface or "", gloss or "", lexicon):
            return _decision(bucket, "SECONDARY", COMPOSITIONAL_EVIDENCE, normalized, inspected=True)
        return _decision(bucket, "HIGH", None, normalized, inspected=True)
    if bucket == "REJECT":
        if _nonreferential(surface or "", gloss or "", lexicon):
            return _decision(bucket, "SECONDARY", NONREFERENTIAL_EVIDENCE, normalized, inspected=True)
        return _decision(bucket, "REJECT", None, normalized, inspected=True)
    if bucket != "SECONDARY":
        raise ValueError(f"provisional bucket {bucket} is outside HIGH, REJECT, and SECONDARY")
    evidence = _secondary_evidence(surface or "", gloss or "", lexicon)
    if evidence == REJECT_EVIDENCE:
        return _decision(bucket, "REJECT", evidence, normalized, inspected=True)
    if evidence == HIGH_EVIDENCE:
        return _decision(bucket, "HIGH", evidence, normalized, inspected=True)
    return _decision(bucket, "SECONDARY", None, normalized, inspected=True)


def assess(rows: list[dict], *, phrase_specific_rule_fired: bool, expected_rows: int = 169) -> dict:
    """Replay gate. Previously correct rows must stay correct. Buckets may move."""
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
    direct_swaps = 0
    for row in rows:
        prior = canonical_bucket(str(row["v5_bucket"]))
        nxt = canonical_bucket(str(row["v6_bucket"]))
        operator = canonical_bucket(str(row["operator_bucket"]))
        primary = row.get("primary_evidence")
        supporting = list(row.get("supporting_evidence") or [])
        if prior == operator:
            previously_correct += 1
            if nxt != operator:
                previously_correct_lost += 1
                failures.append("previously correct row is no longer correct")
        if prior == nxt:
            moves["unchanged"] += 1
            if primary is not None or supporting:
                failures.append("unchanged row carries transition evidence")
        elif prior == "HIGH" and nxt == "SECONDARY":
            moves["high_to_secondary"] += 1
            if primary != COMPOSITIONAL_EVIDENCE or supporting:
                failures.append("HIGH to SECONDARY lacks compositional_recoverability")
            if nxt != operator:
                failures.append("outer reversal does not land on the operator bucket")
        elif prior == "REJECT" and nxt == "SECONDARY":
            moves["reject_to_secondary"] += 1
            if primary != NONREFERENTIAL_EVIDENCE or supporting:
                failures.append("REJECT to SECONDARY lacks nonreferential_lexical_use")
            if nxt != operator:
                failures.append("outer reversal does not land on the operator bucket")
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
            failures.append("row moved outside the four legal transitions")
        if prior != nxt and primary is None:
            failures.append("changed row has no primary evidence")
    if phrase_specific_rule_fired:
        failures.append("phrase-specific rule fired")
    assertions = {
        "replay_count": len(rows) == expected_rows,
        "previously_correct_remain_correct": previously_correct_lost == 0,
        "high_to_secondary_evidence": "HIGH to SECONDARY lacks compositional_recoverability" not in failures,
        "reject_to_secondary_evidence": "REJECT to SECONDARY lacks nonreferential_lexical_use" not in failures,
        "secondary_to_high_evidence": "SECONDARY to HIGH lacks lexicalized_noncompositional" not in failures,
        "secondary_to_reject_evidence": "SECONDARY to REJECT lacks referential_terminological_dominance" not in failures,
        "no_direct_outer_swap": direct_swaps == 0,
        "no_phrase_specific_rules": not phrase_specific_rule_fired,
    }
    verified = not failures and all(assertions.values())
    return {
        "schema": "hyperlex.unbind_screen_v6_gate_report.v1",
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
        "direct_swaps": direct_swaps,
        "moves": moves,
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
        and report.get("previously_correct_lost") == 0
        and report.get("direct_swaps") == 0
        and all((report.get("assertions") or {}).values())
    )


def _decision(prior, nxt, primary, normalized, *, inspected: bool) -> dict:
    return {
        "rule": RULE_VERSION,
        "v5_bucket": prior,
        "v6_bucket": nxt,
        "primary_evidence": primary,
        "supporting_evidence": [],
        "normalized": normalized,
        "inspected": inspected,
    }


def _secondary_evidence(surface: str, gloss: str, lexicon) -> str | None:
    """The frozen v5 secondary tests. Not applied to a row demoted in this pass."""
    from hyperlexical.unbind_screen_v5 import _inspect

    return _inspect(surface, gloss, lexicon)


def _compositional(surface: str, gloss: str, lexicon) -> bool:
    """Recoverable from ordinary senses and ordinary syntax, without an idiomatic mapping."""
    found = lexicon.entry(surface)
    if found is None:
        return False
    content = _content(surface)
    stems = {item for item in (_stem(token) for token in content) if item}
    if _idiomatic_mapping(found, content, stems):
        return False
    ordinary, missing, senses = _ordinary(content, lexicon)
    if missing or _orthographic(content) or _body_clash(found, gloss, content, senses):
        return False
    if _verb_shift(found, content, senses):
        return False
    gloss_stems = _stems(gloss)
    if not gloss_stems or not gloss_stems <= ordinary:
        return False
    return _contributors(content, gloss_stems, lexicon) >= 2


def _nonreferential(surface: str, gloss: str, lexicon) -> bool:
    """A pertainym used as a state or relation, not as a designation."""
    found = lexicon.entry(surface)
    if found is None or found.lex != "adj.pert":
        return False
    content = _content(surface)
    stems = {item for item in (_stem(token) for token in content) if item}
    if _hard_designation(found, stems, content):
        return False
    text = (gloss or "").strip()
    if not text or _RELATIONAL.match(text):
        return False
    ordinary, missing, _senses = _ordinary(content, lexicon)
    if missing:
        return False
    gloss_stems = _stems(text)
    sense_stems = ordinary - stems
    return bool(gloss_stems & sense_stems)


def _hard_designation(found: Entry, stems: set[str], content: list[str]) -> bool:
    if any(char.isupper() for char in found.lemma):
        return True
    if found.lex in _LIFE and _exocentric_life(found.hypernyms, stems):
        return True
    if _exocentric_category(found.hypernyms, stems) and not _ordinary_synonym(found.lemmas, content):
        return True
    return False


def _idiomatic_mapping(found: Entry, content: list[str], stems: set[str]) -> bool:
    for lemma in _single_words(found.lemmas):
        if _initialism(lemma):
            continue
        if not _related(lemma, content, stems):
            return True
    return False


def _contributors(content: list[str], gloss_stems: set[str], lexicon) -> int:
    count = 0
    for token in content:
        if len(token) < 3:
            continue
        token_stems = set()
        for sense in lexicon.senses(token):
            token_stems |= _stems(sense.gloss)
        stemmed = _stem(token)
        if stemmed:
            token_stems.add(stemmed)
        if gloss_stems & token_stems:
            count += 1
    return count
