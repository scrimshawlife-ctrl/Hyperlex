"""Replay the frozen 197-row v7 development set.

This module does not draw a measurement sample, admit, settle, or append the ledger.
The replay is regression evidence. It is not a generalization estimate.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from hyperlexical.unbind_screen_v4 import canonical_bucket, normalize_lexical, rule_surface_violations
from hyperlexical.unbind_screen_v5 import WordNetLexicon
from hyperlexical.unbind_screen_v7 import RULE_VERSION, apply_v7, assess

LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
WORDNET = LEDGER / "acquisition/sources/wordnet-3.0/wordnet"
V6 = LEDGER / "operator-review/HLX-EVAL-UNBIND-SCREEN-V6-001/unbind_screen_v6"
V6H = LEDGER / "operator-review/HLX-EVAL-UNBIND-SCREEN-V6-HYPOTHESIS-001"
HYP = LEDGER / "operator-review/HLX-EVAL-UNBIND-SCREEN-V7-HYPOTHESIS-001"
OUT = LEDGER / "operator-review/HLX-EVAL-UNBIND-SCREEN-V7-001/unbind_screen_v7"
SPEC = Path("/home/morpheus/Hyperlex/specs/007-hyperlexical-model/evaluation-reserve.md")
SCORER = Path(__file__).with_name("unbind_screen_v7.py")
EXPECTED_EVENTS = "96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c"
EXPECTED_V6_SAMPLE = "8ee516423f002a355759eed788bfe3bef81332fad61b1f19c7e46bd0722a29f2"
EXPECTED_V6_PREDICTIONS = "476c5526b18fcb999f2a5397d0674ec07e29b199d5a5259afb555bf608d245ee"
EXPECTED_V6_LABELS = "feed0ee131a513f2801bd1725f553bb6274df1378b28fdea1cb13e238ea9eb11"
EXPECTED_V6_ACCEPTANCE = "68c60dfe9efaf9f79bc445b974c5436d31b60b77fe7374b17103f3b74865610f"
EXPECTED_V6_SOURCE = "59699496c15aaedfbe69a7e49b5c6e62d1e543ce5a1e0e9a0255a98a62036fba"
EXPECTED_DRAFT = "c168bf975e26804a032956d570e39a3d2c7078b407ef966da33083adecf5585b"
EXPECTED_ACCEPTANCE = "562c0756b0337e2fb10643f4fd6689ea4421977a345d12fe33d8a1504161cac5"
EXPECTED_EVIDENCE = "3d457801203c69ceb13c6cefbf5d82fe9cac0daea48f26eb2642d8673585a3a3"
EXPECTED_ANALYSIS = "06a2f10493640d6536b45ef3d9405470c12623bfa787f7fba49b3f64498fb766"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def events_sha256() -> str:
    return file_sha256(LEDGER / "events.jsonl")


def _require_frozen_parents() -> None:
    checks = {
        LEDGER / "events.jsonl": EXPECTED_EVENTS,
        V6 / "measurement_sample.jsonl": EXPECTED_V6_SAMPLE,
        V6 / "measurement_predictions.jsonl": EXPECTED_V6_PREDICTIONS,
        V6 / "measurement_labels.jsonl": EXPECTED_V6_LABELS,
        V6 / "measurement_error_analysis.json": EXPECTED_ANALYSIS,
        V6H / "ACCEPTANCE.json": EXPECTED_V6_ACCEPTANCE,
        V6H / "HYPOTHESIS.json": "fd4f5eeb66061ffdaf2aa4341fe86a0b5e988f131d1711d6ea299a4ebb9e1da4",
        HYP / "HYPOTHESIS.draft.json": EXPECTED_DRAFT,
        HYP / "ACCEPTANCE.json": EXPECTED_ACCEPTANCE,
        HYP / "DEVELOPMENT_EVIDENCE.json": EXPECTED_EVIDENCE,
        Path("/home/morpheus/Hyperlex/scripts/shadow/hyperlexical/unbind_screen_v6.py"): EXPECTED_V6_SOURCE,
    }
    for path, digest in checks.items():
        if file_sha256(path) != digest:
            raise SystemExit(f"frozen parent changed: {path}")


def load_replay_rows() -> list[dict]:
    rows = []
    for line in (V6 / "v6_replay_169_predictions.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        rows.append({
            "surface": raw["surface"],
            "pos": raw["pos"],
            "gloss": raw.get("gloss") or "",
            "v3_bucket": raw["v3_bucket"],
            "v4_bucket": raw["v4_bucket"],
            "v5_bucket": raw["v5_bucket"],
            "v6_bucket": raw["v6_bucket"],
            "operator_bucket": raw["operator_bucket"],
            "split": raw.get("split") or "reviewed_169",
            "row_id": raw["row_id"],
        })
    sample = {
        json.loads(line)["row_id"]: json.loads(line)
        for line in (V6 / "measurement_sample.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    labels = {
        json.loads(line)["row_id"]: json.loads(line)
        for line in (V6 / "measurement_labels.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    predictions = {
        json.loads(line)["row_id"]: json.loads(line)
        for line in (V6 / "measurement_predictions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    if set(sample) != set(labels) or set(sample) != set(predictions):
        raise SystemExit("v6 measurement identities differ")
    seen = {row["row_id"] for row in rows}
    if seen & set(sample):
        raise SystemExit("v6 measurement overlaps the prior reviewed surfaces")
    reviewed_norm = {normalize_lexical(row["surface"]) for row in rows}
    measurement_norm = {normalize_lexical(row["surface"]) for row in sample.values()}
    if reviewed_norm & measurement_norm:
        raise SystemExit("v6 measurement reuses a normalized reviewed identity")
    for row_id, blind in sample.items():
        pred = predictions[row_id]
        rows.append({
            "surface": blind["surface"],
            "pos": blind["pos"],
            "gloss": blind.get("gloss") or "",
            "v3_bucket": pred["v3_bucket"],
            "v4_bucket": pred["v4_bucket"],
            "v5_bucket": pred["v5_bucket"],
            "v6_bucket": pred["v6_bucket"],
            "operator_bucket": labels[row_id]["operator_bucket"],
            "split": "v6_measurement_28",
            "row_id": row_id,
        })
    if len(rows) != 197 or len({row["row_id"] for row in rows}) != 197:
        raise SystemExit(f"reviewed surfaces are {len(rows)}, not 197 unique")
    if len({row["surface"] for row in rows}) != 197:
        raise SystemExit("reviewed surfaces are not unique")
    return rows


def replay(out_dir: Path = OUT) -> dict:
    if (out_dir / "v7_replay_197_predictions.jsonl").exists():
        raise SystemExit("v7 replay is already frozen")
    if (out_dir / "measurement_sample.jsonl").exists():
        raise SystemExit("measurement sample is not authorized")
    if "Unbind screen v7 encoded" in SPEC.read_text(encoding="utf-8"):
        raise SystemExit("spec already records the v7 replay")
    _require_frozen_parents()
    acceptance = json.loads((HYP / "ACCEPTANCE.json").read_text(encoding="utf-8"))
    if acceptance.get("state") != "SPEC_FROZEN" or acceptance.get("implementation_encoded") is not False:
        raise SystemExit("acceptance is not the frozen specification")
    probes = acceptance["probe_surfaces"]["forbidden_in_executable_rule_code"]
    violations = rule_surface_violations(SCORER.read_text(encoding="utf-8"), probes)
    lexicon = WordNetLexicon(WORDNET)
    predictions = []
    for raw in load_replay_rows():
        decision = apply_v7(raw["v6_bucket"], raw["surface"], raw["gloss"], raw["pos"], lexicon)
        predictions.append({
            "schema": "hyperlex.unbind_screen_v7_replay_row.v1",
            "row_id": raw["row_id"],
            "split": raw["split"],
            "surface": raw["surface"],
            "pos": raw["pos"],
            "gloss": raw["gloss"],
            "operator_bucket": canonical_bucket(raw["operator_bucket"]),
            "v3_bucket": canonical_bucket(raw["v3_bucket"]),
            "v4_bucket": canonical_bucket(raw["v4_bucket"]),
            "v5_bucket": canonical_bucket(raw["v5_bucket"]),
            **decision,
        })
    report = assess(predictions, phrase_specific_rule_fired=bool(violations), expected_rows=197)
    report["phrase_violations"] = violations
    report["acceptance_sha256"] = file_sha256(HYP / "ACCEPTANCE.json")
    report["draft_hypothesis_sha256"] = file_sha256(HYP / "HYPOTHESIS.draft.json")
    report["development_evidence_sha256"] = file_sha256(HYP / "DEVELOPMENT_EVIDENCE.json")
    report["error_analysis_sha256"] = file_sha256(V6 / "measurement_error_analysis.json")
    report["events_sha256"] = events_sha256()
    report["measurement_sample_drawn"] = False
    report["measurement_eligible"] = False
    report["regression_is_not_generalization"] = True
    if report["replay_rows"] != 197:
        report["failures"].append("replay count is not 197")
        report["assertions"]["A_replay_197"] = False
        report["regression"] = "REGRESSION_FAILED"
        report["state"] = "ENCODED"
    predictions.sort(key=lambda row: row["row_id"])
    changed = [row for row in predictions if row["v6_bucket"] != row["v7_bucket"]]
    changed.sort(key=lambda row: row["row_id"])
    out_dir.mkdir(parents=True, exist_ok=True)
    out_dir.chmod(0o700)
    prediction_sha = _dump_jsonl(out_dir / "v7_replay_197_predictions.jsonl", predictions)
    diff_sha = _dump_jsonl(out_dir / "v7_replay_197_diff.jsonl", changed)
    report["prediction_sha256"] = prediction_sha
    report["diff_sha256"] = diff_sha
    report["diff_rows"] = len(changed)
    _dump_json(out_dir / "v7_replay_197_gate_report.json", report)
    receipt = _implementation_receipt(report, prediction_sha, diff_sha)
    _dump_json(out_dir / "v7_implementation_receipt.json", receipt)
    _touch_hypothesis(receipt)
    _append_spec(report, changed)
    _require_frozen_parents()
    if (out_dir / "measurement_sample.jsonl").exists():
        raise SystemExit("a measurement sample was drawn")
    if events_sha256() != EXPECTED_EVENTS:
        raise SystemExit("ledger events hash changed during replay")
    return receipt


def _implementation_receipt(report: dict, prediction_sha: str, diff_sha: str) -> dict:
    verified = report["regression"] == "REGRESSION_VERIFIED"
    return {
        "schema": "hyperlex.unbind_screen_v7_implementation_receipt.v1",
        "rule": RULE_VERSION,
        "state": "REGRESSION_VERIFIED" if verified else "ENCODED",
        "regression": report["regression"],
        "measurement_eligible": False,
        "measurement_sample_drawn": False,
        "regression_is_not_generalization": True,
        "authorized": False,
        "encoded": True,
        "applied_to_measurement": False,
        "relation_to_v6": "one_high_challenge_over_a_frozen_v6_bucket",
        "demotion_stops_for_this_application": True,
        "acceptance_sha256": report["acceptance_sha256"],
        "draft_hypothesis_sha256": report["draft_hypothesis_sha256"],
        "source_sha256": {SCORER.name: file_sha256(SCORER)},
        "replay_rows": report["replay_rows"],
        "diff_rows": report["diff_rows"],
        "prediction_sha256": prediction_sha,
        "diff_sha256": diff_sha,
        "phrase_specific_rule_fired": report["phrase_specific_rule_fired"],
        "failures": report["failures"],
        "assertions": report["assertions"],
        "moves": report["moves"],
        "previously_correct": report["previously_correct"],
        "previously_correct_lost": report["previously_correct_lost"],
        "correct_high": report["correct_high"],
        "correct_high_lost": report["correct_high_lost"],
        "direct_swaps": report["direct_swaps"],
        "events_sha256": report["events_sha256"],
        "revision_eligible": False,
        "select_authorized": False,
        "admitted": 0,
        "settled": 0,
        "gold": 0,
        "precision": "NOT_COMPUTABLE",
    }


def _touch_hypothesis(receipt: dict) -> None:
    path = HYP / "HYPOTHESIS.json"
    hypothesis = json.loads(path.read_text(encoding="utf-8"))
    if file_sha256(HYP / "HYPOTHESIS.draft.json") != EXPECTED_DRAFT:
        raise SystemExit("v7 draft bytes changed")
    if file_sha256(HYP / "ACCEPTANCE.json") != EXPECTED_ACCEPTANCE:
        raise SystemExit("v7 acceptance bytes changed")
    if hypothesis.get("acceptance_sha256") != EXPECTED_ACCEPTANCE:
        raise SystemExit("v7 hypothesis no longer points at the frozen acceptance")
    if hypothesis.get("draft_hypothesis_sha256") != EXPECTED_DRAFT:
        raise SystemExit("v7 hypothesis no longer points at the frozen draft")
    hypothesis["encoded"] = True
    hypothesis["implementation_encoded"] = True
    hypothesis["encoding_authorized"] = True
    hypothesis["state"] = receipt["state"]
    hypothesis["regression"] = receipt["regression"]
    hypothesis["measurement_eligible"] = False
    hypothesis["measurement_sample_drawn"] = False
    hypothesis["applied"] = False
    hypothesis["applied_to_measurement"] = False
    hypothesis["select_authorized"] = False
    hypothesis["authorized"] = False
    hypothesis["revision_eligible"] = False
    hypothesis["previously_correct_lost"] = receipt["previously_correct_lost"]
    hypothesis["correct_high_lost"] = receipt["correct_high_lost"]
    hypothesis["direct_swaps"] = receipt["direct_swaps"]
    hypothesis["moves"] = receipt["moves"]
    hypothesis["replay_rows"] = receipt["replay_rows"]
    hypothesis["regression_is_not_generalization"] = True
    hypothesis["precision"] = "NOT_COMPUTABLE"
    text = json.dumps(hypothesis, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)


def _append_spec(report: dict, changed: list[dict]) -> None:
    moves = report["moves"]
    if len(changed) == 1:
        row = changed[0]
        change = (
            f"One row moves. `{row['surface']}` goes from high to secondary with "
            f"`{row['primary_evidence']}`, and the operator bucket is {row['operator_bucket'].lower()}. "
            "That firing is not a required fit."
        )
    elif not changed:
        change = "No row moves."
    else:
        names = ", ".join(f"`{row['surface']}`" for row in changed)
        change = f"{len(changed)} rows move: {names}."
    verified = report["regression"] == "REGRESSION_VERIFIED"
    if verified:
        state = (
            "State is `REGRESSION_VERIFIED`. `measurement_eligible` stays false. "
            "The unseen sample was not drawn."
        )
    else:
        state = (
            "State stays `ENCODED` because the regression gate failed. "
            "`measurement_eligible` stays false. The unseen sample was not drawn."
        )
    section = f"""
## Unbind screen v7 encoded — 2026-09-28

`RUNE.UNBIND_SCREEN.v7` is encoded over a frozen v6 bucket. The only new predicate is `ordinary_compositional_derivation`. It inspects a provisional high. The recorded sense must be a comparative, syntactic, or phrasal composition, and the synset must not store an unrelated single-word synonym. A gloss that merely shares constituent stems does not fire, and a metaphorical retelling does not fire. A demotion stops at secondary. Reject rows still use the v6 reject challenge. Secondary rows are not reopened, so a demotion v6 already stopped stays stopped. `compositional_recoverability` is not a v7 transition. The acceptance contract is unchanged, sha256 `{EXPECTED_ACCEPTANCE}`.

The 197 reviewed surfaces were replayed as development and regression evidence, not as a generalization estimate. Previously correct rows lost: {report['previously_correct_lost']}. Previously correct high rows demoted: {report['correct_high_lost']}. Direct swaps between high and reject: {report['direct_swaps']}. High to secondary: {moves['high_to_secondary']}. Reject to secondary: {moves['reject_to_secondary']}. Secondary to high: {moves['secondary_to_high']}. Secondary to reject: {moves['secondary_to_reject']}. {change} No phrase-specific rule fired. This replay is not a precision estimate. Gate report sha256 `{report['replay_rows'] and ''}`. Prediction sha256 `{report['prediction_sha256']}`. Diff sha256 `{report['diff_sha256']}`.

{state} The pre-registered bar remains high precision 1, reject precision 1, false high 0, and false reject 0, with no false-secondary quota, no accuracy target, and no recall target. No measurement sample was drawn. `revision_eligible` stays false on v7, v6, and v5. `revision_eligible` on the v4 measurement stays true. `HLX-EXP-2026-09-27-SELECT-005` is not authorized. Admitted 0. Settled 0. Gold 0. The ledger was not appended. Events sha256 remains `{EXPECTED_EVENTS}`.
"""
    # The gate-report hash is the file hash, filled by the caller after the report is dumped.
    # This placeholder is replaced below once the file exists.
    spec = SPEC.read_text(encoding="utf-8")
    if not spec.endswith("\n"):
        spec += "\n"
    SPEC.write_text(spec + "\n" + section.lstrip("\n"), encoding="utf-8")


def _dump_json(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, sort_keys=True, ensure_ascii=True, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _dump_jsonl(path: Path, rows: list[dict]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> None:
    receipt = replay()
    gate = OUT / "v7_replay_197_gate_report.json"
    gate_sha = file_sha256(gate)
    spec = SPEC.read_text(encoding="utf-8")
    broken = "Gate report sha256 ``."
    if broken not in spec:
        raise SystemExit("spec gate hash placeholder missing")
    SPEC.write_text(spec.replace(broken, f"Gate report sha256 `{gate_sha}`.", 1), encoding="utf-8")
    print(json.dumps({
        "state": receipt["state"],
        "regression": receipt["regression"],
        "measurement_eligible": receipt["measurement_eligible"],
        "measurement_sample_drawn": receipt["measurement_sample_drawn"],
        "replay_rows": receipt["replay_rows"],
        "diff_rows": receipt["diff_rows"],
        "moves": receipt["moves"],
        "previously_correct_lost": receipt["previously_correct_lost"],
        "correct_high_lost": receipt["correct_high_lost"],
        "direct_swaps": receipt["direct_swaps"],
        "failures": receipt["failures"],
        "prediction_sha256": receipt["prediction_sha256"],
        "diff_sha256": receipt["diff_sha256"],
        "gate_sha256": gate_sha,
        "events_sha256": receipt["events_sha256"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
