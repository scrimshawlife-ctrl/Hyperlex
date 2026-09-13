"""Offline structural baseline, not a trained model or a promotion gate.

Provenance: Notion Sprint 001 Hub NOT_COMPUTABLE + Loop 805 Slice N/A
+ Hash: see caller's code revision and the emitted input_sha256.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

TYPE_ROLES = frozenset({"TOKEN", "SLOT", "MARKER"})


def extract(text: str, role_scheme: str) -> list[dict]:
    """Predict occurrences from text and declared grammar only; no gold input.

    Positional grammar uses whitespace-delimited surface atoms. Type-slot
    grammar requires ROLE:atom on every whitespace-delimited token. Roles
    are explicit input syntax, not semantic roles inferred by a model.
    Offsets are Python Unicode character offsets into the original text.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("nonempty text required")
    if not isinstance(role_scheme, str) or role_scheme not in {"positional", "type_slot"}:
        raise ValueError("unsupported role_scheme")
    result = []
    for i, match in enumerate(re.finditer(r"\S+", text)):
        atom = match.group()
        start = match.start()
        role = f"pos_{i}"
        if role_scheme == "type_slot":
            role, sep, atom = atom.partition(":")
            if not sep or role not in TYPE_ROLES or not atom:
                raise ValueError("malformed type-slot syntax")
            start += len(role) + 1
        result.append({"occurrence": i, "start": start, "end": match.end(),
                       "filler": atom, "role": role})
    return result


def _strings(value, field: str) -> list[str]:
    if not isinstance(value, list) or not value or any(
        not isinstance(v, str) or not v for v in value
    ):
        raise ValueError(f"{field} must be a nonempty string list")
    return value


def _counter_matches(row: dict, gold: list[str], pred: list[str]) -> None:
    expected = {
        "slot_tp": sum(a == b for a, b in zip(gold, pred)),
        "slot_n_gold": len(gold), "token_n_gold": len(gold),
        "token_n_pred": len(pred),
        "token_tp": sum((Counter(gold) & Counter(pred)).values()),
    }
    for key, value in expected.items():
        if type(row.get(key)) is not int or row[key] != value:
            raise ValueError(f"inconsistent {key}")


def evaluate(rows: list[dict], *, population: str) -> dict:
    """Audit residual JSONL or unbind dataset JSONL without altering either.

    Rejections are included as failures in the all-input denominator.
    Residual-only results cannot represent full validation accuracy.
    """
    if not isinstance(population, str) or population not in {"residual_only", "evaluation_set"}:
        raise ValueError("explicit population required")
    if not rows:
        raise ValueError("empty input")
    hits = structure_hits = accepted = one_wrong = 0
    rejected = Counter()
    scheme = Counter()
    lengths = Counter()
    duplicate_keys = set()
    duplicates = 0
    for row in rows:
        try:
            if not isinstance(row, dict):
                raise TypeError("row must be an object")
            # The predictor deliberately receives only text and scheme.
            spans = extract(row.get("text"), row.get("role_scheme"))
            field = "gold" if population == "residual_only" else "fillers"
            gold = _strings(row.get(field), field)
            roles = _strings(row.get("roles"), "roles")
            if len(roles) != len(gold):
                raise ValueError("role/filler length mismatch")
            if population == "evaluation_set" and row.get("task") != "unbind":
                raise ValueError("evaluation_set requires task=unbind")
            if population == "residual_only":
                prior = _strings(row.get("pred"), "pred")
                _counter_matches(row, gold, prior)
                if prior == gold:
                    raise ValueError("residual input contains exact hit")
                one_wrong += int(len(gold) == len(prior) and
                                 sum(a != b for a, b in zip(gold, prior)) == 1)
            key = (row["text"], row["role_scheme"])
            duplicates += int(key in duplicate_keys)
            duplicate_keys.add(key)
            accepted += 1
            scheme[row["role_scheme"]] += 1
            lengths[len(gold)] += 1
            predicted = [s["filler"] for s in spans]
            hits += int(predicted == gold)
            structure_hits += int(predicted == gold and [s["role"] for s in spans] == roles)
        except (TypeError, ValueError) as exc:
            rejected[str(exc)] += 1
    return {
        "schema": "hyperlex.extraction_baseline.v0.1",
        "baseline": "whitespace_or_explicit_role_grammar",
        "uses_gold_for_prediction": False, "population": population,
        "n_input": len(rows), "n_accepted": accepted,
        "n_rejected": sum(rejected.values()), "rejections": dict(rejected),
        "duplicate_text_scheme_rows": duplicates,
        "n_filler_exact": hits, "n_structure_exact": structure_hits,
        "filler_exact_all_input": hits / len(rows),
        "structure_exact_all_input": structure_hits / len(rows),
        "by_scheme_accepted": dict(scheme), "by_length_accepted": dict(lengths),
        "prior_one_wrong_slot_rows": one_wrong if population == "residual_only" else None,
        "full_validation_accuracy": "NOT_COMPUTABLE",
        "learned_model_improvement": "NOT_COMPUTABLE",
        "name_gate": False, "brier": None, "forecast_eligible": False,
        "note": "Structural grammar baseline only; no semantic extraction or model promotion proof.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--population", required=True,
                        choices=("residual_only", "evaluation_set"))
    args = parser.parse_args(argv)
    try:
        payload = args.input.read_bytes()
        rows = [json.loads(line) for line in payload.decode("utf-8-sig").splitlines()
                if line.strip()]
        report = evaluate(rows, population=args.population)
        report["input_sha256"] = hashlib.sha256(payload).hexdigest()
    except (OSError, UnicodeError, ValueError):
        # Do not disclose raw rows or private paths in diagnostics.
        print(json.dumps({"error": "unreadable, empty or malformed input", "name_gate": False}))
        return 2
    print(json.dumps(report, sort_keys=True, indent=2))
    return 2 if report["n_rejected"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
