"""Replay the frozen 197-row set, then draw one unseen measurement sample.

The replay is regression evidence. The draw excludes those identities, freezes
the sample, and only then applies v7 once. It does not label, admit, settle,
or append the ledger.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from hyperlexical.holdout_guard import normalized_text_sha256
from hyperlexical.unbind_screen_v3 import gloss_for, screen
from hyperlexical.unbind_screen_v4 import WordNetLexicon as V4Lexicon
from hyperlexical.unbind_screen_v4 import apply_v4, canonical_bucket, normalize_lexical, rule_surface_violations
from hyperlexical.unbind_screen_v4_measure import _stratified_sample
from hyperlexical.unbind_screen_v5 import WordNetLexicon
from hyperlexical.unbind_screen_v5 import WordNetLexicon as V5Lexicon
from hyperlexical.unbind_screen_v5 import apply_v5
from hyperlexical.unbind_screen_v6 import apply_v6
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
EXPECTED_REPLAY = "24f266e16b80da602b011bf7cca13774ce9f76c0c52e81e600a1d9743d61d197"
EXPECTED_GATE = "78225b68c639694bb4c17342c87320ccb44faac557a9145ea117603da0d545ed"
LEAK_KEYS = frozenset({
    "predicted", "predicted_bucket", "bucket", "relation", "rule", "phase",
    "operator", "operator_bucket", "operator_reason", "forecast", "diagnostic",
    "v3", "v4", "v5", "v6", "v7", "primary_evidence", "supporting_evidence",
    "evidence", "v3_bucket", "v4_bucket", "v5_bucket", "v6_bucket", "v7_bucket",
    "ordinary_compositional_derivation",
})


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


def draw_measurement(out_dir: Path = OUT, per_cell: int = 2) -> dict:
    """Freeze one unseen sample, then apply v7 once."""
    if (out_dir / "measurement_sample.jsonl").exists():
        raise SystemExit("measurement sample is already frozen")
    if (out_dir / "measurement_predictions.jsonl").exists():
        raise SystemExit("measurement predictions already exist")
    if "Unbind screen v7 measurement frozen" in SPEC.read_text(encoding="utf-8"):
        raise SystemExit("spec already records the v7 measurement draw")
    _require_frozen_parents()
    if file_sha256(out_dir / "v7_replay_197_predictions.jsonl") != EXPECTED_REPLAY:
        raise SystemExit("v7 replay predictions changed")
    if file_sha256(out_dir / "v7_replay_197_gate_report.json") != EXPECTED_GATE:
        raise SystemExit("v7 gate report changed")
    report = json.loads((out_dir / "v7_replay_197_gate_report.json").read_text(encoding="utf-8"))
    if report.get("regression") != "REGRESSION_VERIFIED" or report.get("replay_rows") != 197:
        raise SystemExit("measurement draw refused: regression is not verified")
    if report.get("previously_correct_lost") != 0 or report.get("failures"):
        raise SystemExit("measurement draw refused: regression failures are present")
    acceptance = json.loads((HYP / "ACCEPTANCE.json").read_text(encoding="utf-8"))
    criteria = dict(acceptance["success_criteria"])
    if criteria.get("high_precision") != 1.0 or criteria.get("reject_precision") != 1.0:
        raise SystemExit("acceptance bar was amended")
    if criteria.get("false_high_allowed") != 0 or criteria.get("false_reject_allowed") != 0:
        raise SystemExit("acceptance bar was amended")
    if criteria.get("false_secondary_rate_required") is not False or criteria.get("accuracy_gain_required") is not False:
        raise SystemExit("acceptance bar gained a coverage or accuracy target")
    if criteria.get("recall_required") is not False:
        raise SystemExit("acceptance bar gained a recall target")
    if criteria.get("next_measurement_excludes_reviewed_surfaces") != 197:
        raise SystemExit("acceptance exclusion count changed")
    criteria_sha = _dump_json(out_dir / "measurement_criteria.json", criteria)
    if file_sha256(HYP / "ACCEPTANCE.json") != EXPECTED_ACCEPTANCE:
        raise SystemExit("copying criteria changed the acceptance")

    reviewed = [
        json.loads(line)
        for line in (out_dir / "v7_replay_197_predictions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(reviewed) != 197 or len({row["row_id"] for row in reviewed}) != 197:
        raise SystemExit("reviewed replay is not 197 unique rows")
    blocked_hash = {row["row_id"] for row in reviewed}
    blocked_norm = {normalize_lexical(row["surface"]) for row in reviewed}
    if len(blocked_norm) != 197:
        raise SystemExit("reviewed normalized identities are not unique")
    picked, strata = _stratified_sample(blocked_hash, blocked_norm, per_cell=per_cell)
    exhausted = [cell for cell in strata if cell["available"] < per_cell or cell["taken"] < per_cell]
    for cell in strata:
        if cell["taken"] > cell["available"] or cell["taken"] > per_cell:
            raise SystemExit("stratum draw exceeded the frozen policy")

    blinded = []
    sources = {}
    for row in picked:
        surface = str(row["text"])
        pos = str(row["source_pos"])
        tokens = [str(tok) for tok in row["fillers"]]
        if " ".join(tokens) != surface or len(tokens) < 1:
            raise SystemExit("sample tokens do not reconstruct the surface")
        _pos, gloss = gloss_for(surface, pos, WORDNET)
        row_id = normalized_text_sha256(surface)
        identity = normalize_lexical(surface)
        if row_id in blocked_hash or identity in blocked_norm:
            raise SystemExit(f"draw reused a reviewed identity: {surface}")
        blind = {
            "schema": "hyperlex.unbind_screen_review_row.v1",
            "evaluation_id": "HLX-EVAL-UNBIND-SCREEN-V7-001",
            "sample_id": "measurement-001",
            "row_id": row_id,
            "surface": surface,
            "pos": pos,
            "token_count": len(tokens),
            "gloss": gloss,
            "provenance": {
                "source": "wordnet-3.0",
                "source_pos": pos,
                "excluded_reviewed_surfaces": 197,
            },
        }
        leaked = LEAK_KEYS.intersection(blind)
        if leaked:
            raise SystemExit(f"blind row carries {sorted(leaked)}")
        blinded.append(blind)
        sources[row_id] = {"tokens": tokens, "pos": pos, "surface": surface, "gloss": gloss}
    identities = [normalize_lexical(row["surface"]) for row in blinded]
    if len(identities) != len(set(identities)):
        raise SystemExit("sample contains a duplicate normalized identity")
    if set(identities) & blocked_norm or {row["row_id"] for row in blinded} & blocked_hash:
        raise SystemExit("sample intersects the reviewed 197")
    if {row["surface"] for row in blinded} & {row["surface"] for row in reviewed}:
        raise SystemExit("sample reuses a reviewed surface")
    blinded.sort(key=lambda row: row["row_id"])
    sample_sha = _dump_jsonl(out_dir / "measurement_sample.jsonl", blinded)
    sample_text = (out_dir / "measurement_sample.jsonl").read_text(encoding="utf-8")
    if file_sha256(out_dir / "measurement_sample.jsonl") != sample_sha:
        raise SystemExit("sample hash did not stick")
    for forbidden in (
        "ordinary_compositional_derivation",
        "primary_evidence",
        "operator_bucket",
        "operator_reason",
        "v7_bucket",
        "v6_bucket",
        "v5_bucket",
        "v4_bucket",
        "v3_bucket",
    ):
        if forbidden in sample_text:
            raise SystemExit(f"blind sample contains {forbidden}")
    frozen_rows = [json.loads(line) for line in sample_text.splitlines() if line.strip()]
    if [row["row_id"] for row in frozen_rows] != [row["row_id"] for row in blinded]:
        raise SystemExit("frozen sample does not match the draw")

    v4_lexicon = V4Lexicon(WORDNET)
    v5_lexicon = V5Lexicon(WORDNET)
    predictions = []
    applications = 0
    for row in frozen_rows:
        source = sources[row["row_id"]]
        if source["surface"] != row["surface"] or source["gloss"] != row["gloss"]:
            raise SystemExit("apply input drifted from the frozen sample")
        if source["pos"] != row["pos"] or len(source["tokens"]) != row["token_count"]:
            raise SystemExit("apply input drifted from the frozen sample")
        surface = row["surface"]
        pos = row["pos"]
        tokens = source["tokens"]
        gloss = row["gloss"]
        v3_bucket, v3_rule, _phase = screen(surface, pos, tokens, gloss)
        v4_decision = apply_v4(v3_bucket, surface, gloss, pos, v4_lexicon)
        v5_decision = apply_v5(v4_decision["v4_bucket"], surface, gloss, pos, v5_lexicon)
        v6_decision = apply_v6(v5_decision["v5_bucket"], surface, gloss, pos, v5_lexicon)
        decision = apply_v7(v6_decision["v6_bucket"], surface, gloss, pos, v5_lexicon)
        applications += 1
        if decision["v6_bucket"] != v6_decision["v6_bucket"]:
            raise SystemExit("v7 did not keep the provisional v6 bucket")
        predictions.append({
            "schema": "hyperlex.unbind_screen_v7_measurement_prediction.v1",
            "evaluation_id": "HLX-EVAL-UNBIND-SCREEN-V7-001",
            "sample_id": "measurement-001",
            "row_id": row["row_id"],
            "v3_rule": v3_rule,
            "application_index": 1,
            "v3_bucket": canonical_bucket(v3_bucket),
            "v4_bucket": v4_decision["v4_bucket"],
            "v5_bucket": v5_decision["v5_bucket"],
            "provisional_v6_bucket": v6_decision["v6_bucket"],
            **decision,
        })
    if applications != len(frozen_rows):
        raise SystemExit("v7 application count does not match the sample")
    if file_sha256(out_dir / "measurement_sample.jsonl") != sample_sha:
        raise SystemExit("sample hash changed while v7 was applied")
    predictions.sort(key=lambda row: row["row_id"])
    if [row["row_id"] for row in predictions] != [row["row_id"] for row in frozen_rows]:
        raise SystemExit("predictions do not cover the frozen sample")
    prediction_sha = _dump_jsonl(out_dir / "measurement_predictions.jsonl", predictions)
    freeze = {
        "schema": "hyperlex.unbind_screen_v7_measurement_freeze.v1",
        "rule": RULE_VERSION,
        "state": "MEASUREMENT_ELIGIBLE",
        "sample_state": "MEASUREMENT_SAMPLE_FROZEN",
        "regression": "REGRESSION_VERIFIED",
        "measurement_eligible": True,
        "rows": len(frozen_rows),
        "per_cell": per_cell,
        "strata": "source_pos x token_count",
        "stratum_counts": strata,
        "exhausted_strata": exhausted,
        "order": "normalized_text_sha256",
        "excluded_reviewed_surfaces": 197,
        "normalized_overlap_with_reviewed_197": 0,
        "duplicate_normalized_identities": 0,
        "deduplicated_normalized_lexical_identity": True,
        "sample_sha256": sample_sha,
        "prediction_sha256": prediction_sha,
        "criteria_sha256": criteria_sha,
        "sample_frozen_before_apply": True,
        "v7_application_count": applications,
        "hand_corrections": 0,
        "operator_labels": None,
        "precision": "NOT_COMPUTABLE",
        "confusion": "NOT_COMPUTABLE",
        "inspected_before_freeze": False,
        "false_secondary_rate_required": False,
        "accuracy_gain_required": False,
        "recall_required": False,
        "admitted": 0,
        "settled": 0,
        "gold": 0,
        "select_authorized": False,
        "revision_eligible": False,
        "events_sha256": events_sha256(),
    }
    _dump_json(out_dir / "measurement_freeze.json", freeze)
    receipt = json.loads((out_dir / "v7_implementation_receipt.json").read_text(encoding="utf-8"))
    receipt["state"] = "MEASUREMENT_ELIGIBLE"
    receipt["applied_to_measurement"] = True
    receipt["measurement_eligible"] = True
    receipt["measurement_sample_drawn"] = True
    receipt["measurement_state"] = "MEASUREMENT_ELIGIBLE"
    receipt["sample_state"] = "MEASUREMENT_SAMPLE_FROZEN"
    receipt["measurement_rows"] = len(frozen_rows)
    receipt["measurement_sample_sha256"] = sample_sha
    receipt["measurement_prediction_sha256"] = prediction_sha
    receipt["criteria_sha256"] = criteria_sha
    receipt["v7_application_count"] = applications
    receipt["hand_corrections"] = 0
    receipt["precision"] = "NOT_COMPUTABLE"
    receipt["exhausted_strata"] = len(exhausted)
    receipt["events_sha256"] = events_sha256()
    _dump_json(out_dir / "v7_implementation_receipt.json", receipt)
    _mark_measured(freeze)
    _write_review_sheet(out_dir, frozen_rows, sample_sha)
    _append_measurement_spec(freeze, exhausted)
    _require_frozen_parents()
    if file_sha256(out_dir / "measurement_sample.jsonl") != sample_sha:
        raise SystemExit("sample hash drifted after the draw")
    if file_sha256(HYP / "ACCEPTANCE.json") != EXPECTED_ACCEPTANCE:
        raise SystemExit("acceptance bytes changed during the draw")
    if file_sha256(HYP / "HYPOTHESIS.draft.json") != EXPECTED_DRAFT:
        raise SystemExit("draft bytes changed during the draw")
    if events_sha256() != EXPECTED_EVENTS:
        raise SystemExit("ledger events hash changed during the draw")
    return freeze


def _mark_measured(freeze: dict) -> None:
    path = HYP / "HYPOTHESIS.json"
    hypothesis = json.loads(path.read_text(encoding="utf-8"))
    if hypothesis.get("acceptance_sha256") != EXPECTED_ACCEPTANCE:
        raise SystemExit("hypothesis no longer points at the frozen acceptance")
    if hypothesis.get("draft_hypothesis_sha256") != EXPECTED_DRAFT:
        raise SystemExit("hypothesis no longer points at the frozen draft")
    hypothesis["state"] = "MEASUREMENT_ELIGIBLE"
    hypothesis["measurement_state"] = "MEASUREMENT_ELIGIBLE"
    hypothesis["sample_state"] = "MEASUREMENT_SAMPLE_FROZEN"
    hypothesis["measurement_eligible"] = True
    hypothesis["measurement_sample_drawn"] = True
    hypothesis["applied"] = True
    hypothesis["applied_to_measurement"] = True
    hypothesis["precision"] = "NOT_COMPUTABLE"
    hypothesis["measurement_rows"] = freeze["rows"]
    hypothesis["measurement_sample_sha256"] = freeze["sample_sha256"]
    hypothesis["measurement_prediction_sha256"] = freeze["prediction_sha256"]
    hypothesis["hand_corrections"] = 0
    hypothesis["v7_application_count"] = freeze["v7_application_count"]
    hypothesis["operator_labels"] = None
    hypothesis["labeling_performed"] = False
    hypothesis["next_legal_transition"] = "OPERATOR_LABELS"
    hypothesis["select_authorized"] = False
    hypothesis["authorized"] = False
    hypothesis["revision_eligible"] = False
    hypothesis["admitted"] = 0
    hypothesis["settled"] = 0
    hypothesis["gold"] = 0
    text = json.dumps(hypothesis, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)


def _write_review_sheet(out_dir: Path, rows: list[dict], sample_sha: str) -> None:
    lines = [
        "# Unbind screen v7 blind review",
        "",
        "Prediction buckets and evidence codes are withheld.",
        f"Sample sha256 `{sample_sha}`.",
        "",
        "| row_id | surface | pos | token_count | gloss |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        gloss = row["gloss"].replace("|", "\\|")
        lines.append(
            f"| `{row['row_id']}` | {row['surface']} | {row['pos']} | {row['token_count']} | {gloss} |"
        )
    lines.append("")
    path = out_dir / "measurement_review.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    path.chmod(0o600)
    text = path.read_text(encoding="utf-8")
    for forbidden in ("ordinary_compositional_derivation", "primary_evidence", "v7_bucket", "operator_bucket"):
        if forbidden in text:
            raise SystemExit(f"review sheet contains {forbidden}")


def _append_measurement_spec(freeze: dict, exhausted: list[dict]) -> None:
    if exhausted:
        detail = "; ".join(
            f"{cell['source_pos']} x {cell['token_count']} available {cell['available']}, taken {cell['taken']}"
            for cell in exhausted
        )
        exhausted_sentence = f"Exhausted cells, where fewer than 2 rows remained: {detail}."
    else:
        exhausted_sentence = "No occupied cell was exhausted. Each occupied cell contributed 2 rows."
    section = f"""
## Unbind screen v7 measurement frozen — 2026-09-28

The 197-row regression stays `REGRESSION_VERIFIED`. One unseen measurement sample excludes those 197 normalized identities. Normalized overlap with the reviewed set is 0. Duplicate normalized identities inside the sample are 0. The draw is deterministic and stratified by source part of speech and token count, two rows from each occupied cell. Occupied cells produced {freeze['rows']} rows. {exhausted_sentence}

The sample was frozen before v7 was applied. Sample sha256 `{freeze['sample_sha256']}`. v7 was then applied once. Hand corrections are 0. Prediction sha256 `{freeze['prediction_sha256']}`. The blind rows carry surface, part of speech, token count, and gloss. They do not carry a bucket or an evidence code. Operator labels are absent. Precision is `NOT_COMPUTABLE`. State is `MEASUREMENT_ELIGIBLE`.

The acceptance bar is unchanged: high precision 1, reject precision 1, false high 0, and false reject 0. No false-secondary floor, no accuracy target, and no recall target were added. Criteria sha256 `{freeze['criteria_sha256']}`. `revision_eligible` stays false. `HLX-EXP-2026-09-27-SELECT-005` is not authorized. Admitted 0. Settled 0. Gold 0. The ledger was not appended. Events sha256 remains `{EXPECTED_EVENTS}`.
"""
    spec = SPEC.read_text(encoding="utf-8")
    if not spec.endswith("\n"):
        spec += "\n"
    SPEC.write_text(spec + "\n" + section.lstrip("\n"), encoding="utf-8")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Draw the unseen v7 measurement sample")
    parser.add_argument("command", choices=("draw",))
    args = parser.parse_args()
    if args.command != "draw":
        raise SystemExit("only the measurement draw is authorized")
    freeze = draw_measurement()
    print(json.dumps({
        "state": freeze["state"],
        "sample_state": freeze["sample_state"],
        "rows": freeze["rows"],
        "exhausted_strata": freeze["exhausted_strata"],
        "sample_sha256": freeze["sample_sha256"],
        "prediction_sha256": freeze["prediction_sha256"],
        "v7_application_count": freeze["v7_application_count"],
        "hand_corrections": freeze["hand_corrections"],
        "normalized_overlap_with_reviewed_197": freeze["normalized_overlap_with_reviewed_197"],
        "duplicate_normalized_identities": freeze["duplicate_normalized_identities"],
        "precision": freeze["precision"],
        "events_sha256": freeze["events_sha256"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
