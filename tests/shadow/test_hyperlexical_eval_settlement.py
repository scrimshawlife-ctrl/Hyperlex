"""Evaluation settlement keeps family, attest, and the production head apart."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.eval_settlement import (  # noqa: E402
    ACTIVE_FAMILIES,
    CANDIDATE_FAMILIES,
    SHEET_COLUMNS,
    SURFACES,
    family_flags,
    parse_sheet,
    receipt_sha_matches,
    settlement_allows_reserve,
    settle,
)
from hyperlexical.holdout_guard import normalized_text_sha256  # noqa: E402
from hyperlexical.identity_ledger import main  # noqa: E402
from hyperlexical.layout import FAMILIES as PRODUCTION_FAMILIES  # noqa: E402
from hyperlexical.weak_tag_family import FAMILIES as WEAK_FAMILIES  # noqa: E402

STAMP = {
    "operator": "operator",
    "settled_at": "2026-09-26T16:00:00Z",
    "provenance": "unit",
    "batch_id": "unit-batch",
}


def _stream(
    text="phrase alpha",
    *,
    key="hs-1",
    hint="gaming-meta",
    source="wiktionary_category",
    label="gaming-meta",
    label_source="INFERRED",
):
    return {
        "row_key": key,
        "text": text,
        "family_hint_not_a_label": hint,
        "source_type": source,
        "label": label,
        "label_source": label_source,
        "normtext_sha256": normalized_text_sha256(text),
    }


def _decision(stream, **overrides):
    payload = {
        "row_id": stream["row_key"],
        "text_hash": normalized_text_sha256(stream["text"]),
        "decision": "ACCEPT",
        "semantic_family": "gaming-meta",
        "attest": "INFERRED",
        "register": None,
        "function": None,
        "source_hint": stream["family_hint_not_a_label"],
        "proposed_family": "gaming-meta",
        "lane": "A",
    }
    payload.update(overrides)
    return payload


def _apply(stream, decision):
    streams = stream if isinstance(stream, list) else [stream]
    decisions = decision if isinstance(decision, list) else [decision]
    return settle(streams, decisions, **STAMP)


def _sheet(path: Path, stream, *, lane="A", decision="", family="", attest="", register="", function="", proposed=None):
    hint = stream["family_hint_not_a_label"]
    hint_cell = "NO_HINT" if hint in (None, "") else hint
    label = "UNLABELLED" if stream["label"] is None else str(stream["label"])
    rights = "CC-BY-SA" if stream["source_type"] in ("wiktionary_category", "wikipedia_prose") else "RIGHTS_UNRESOLVED"
    if proposed is None:
        proposed = family or ("" if hint in (None, "") else str(hint))
    row = [
        lane,
        stream["row_key"],
        stream["text"],
        hint_cell,
        "stream.family_hint_not_a_label",
        label,
        stream["label_source"],
        rights,
        proposed,
        "",
        family,
        attest,
        register,
        function,
        decision,
    ]
    path.write_text("\t".join(SHEET_COLUMNS) + "\n" + "\t".join(row) + "\n", encoding="utf-8")


def test_evaluation_only_families_are_accepted():
    for family, hint, proposed in (
        ("workplace-career", "workplace-corp", "workplace-career"),
        ("technology-ai", "ai-native", "technology-ai"),
        ("identity-affiliation", "kinship-address", "identity-affiliation"),
        ("politics-civic", "political-status", "politics-civic"),
    ):
        stream = _stream(f"phrase {family}", hint=hint, label=None, label_source="UNLABELLED")
        record = _apply(
            stream,
            _decision(
                stream,
                semantic_family=family,
                proposed_family=proposed,
                lane="B",
                decision="ACCEPT FAMILY",
            ),
        )["records"][0]
        assert record["semantic_family"] == family
        assert record["source_hint"] == hint
        assert record["attest"] == "INFERRED"
        assert "label_source" not in record


def test_production_family_is_accepted_on_the_evaluation_surface():
    stream = _stream("phrase gaming")
    record = _apply(stream, _decision(stream, semantic_family="gaming-meta"))["records"][0]
    assert record["semantic_family"] == "gaming-meta"
    assert record["source_hint"] == "gaming-meta"
    assert family_flags("gaming-meta")["production.enabled"] is False


def test_source_hint_is_preserved_and_not_copied():
    stream = _stream("phrase career", hint="workplace-corp", label=None, label_source="UNLABELLED")
    record = _apply(
        stream,
        _decision(
            stream,
            semantic_family="workplace-career",
            proposed_family="workplace-career",
            lane="B",
        ),
    )["records"][0]
    assert record["source_hint"] == "workplace-corp"
    assert record["semantic_family"] == "workplace-career"
    stream = _stream("phrase blank hint", hint="workplace-corp", label=None, label_source="UNLABELLED")
    with pytest.raises(SystemExit, match="ACCEPT requires an explicit semantic_family"):
        _apply(stream, _decision(stream, semantic_family="", proposed_family="workplace-career", lane="B"))


def test_accept_inferred_remains_inferred():
    stream = _stream("phrase inferred")
    record = _apply(stream, _decision(stream, decision="ACCEPT", attest="INFERRED"))["records"][0]
    assert record["decision"] == "ACCEPT"
    assert record["attest"] == "INFERRED"
    assert record["semantic_family"] == "gaming-meta"


def test_accept_observed_records_operator_observed():
    stream = _stream("phrase observed", label_source="INFERRED")
    record = _apply(stream, _decision(stream, decision="ACCEPT", attest="OBSERVED"))["records"][0]
    assert record["attest"] == "OBSERVED"
    assert "label_source" not in record


def test_reclassify_requires_an_explicit_different_family():
    stream = _stream("phrase move", hint="brainrot-aura", label=None, label_source="UNLABELLED")
    with pytest.raises(SystemExit, match="RECLASSIFY requires an explicit family"):
        _apply(
            stream,
            _decision(stream, decision="RECLASSIFY", semantic_family="", proposed_family="", lane="C"),
        )
    with pytest.raises(SystemExit, match="must differ"):
        _apply(
            stream,
            _decision(
                stream,
                decision="RECLASSIFY",
                semantic_family="gaming-meta",
                proposed_family="gaming-meta",
                attest="INFERRED",
            ),
        )
    record = _apply(
        stream,
        _decision(
            stream,
            decision="CHOOSE DIFFERENT FAMILY",
            semantic_family="internet-slang",
            proposed_family="",
            attest="OBSERVED",
            lane="C",
        ),
    )["records"][0]
    assert record["decision"] == "RECLASSIFY"
    assert record["semantic_family"] == "internet-slang"
    assert record["source_hint"] == "brainrot-aura"
    assert record["attest"] == "OBSERVED"


def test_none_produces_semantic_family_none():
    stream = _stream("phrase none", hint="none", label="none")
    record = _apply(
        stream,
        _decision(stream, decision="NONE", semantic_family="", proposed_family="none", attest="INFERRED"),
    )["records"][0]
    assert record["semantic_family"] == "none"
    assert record["decision"] == "NONE"
    assert record["attest"] == "INFERRED"
    with pytest.raises(SystemExit, match="reject is a production attest token"):
        _apply(stream, _decision(stream, decision="reject"))


def test_unresolved_remains_unsettled_and_outside_reserve():
    stream = _stream("phrase open")
    result = _apply(
        stream,
        _decision(stream, decision="UNRESOLVED", semantic_family="", attest="", proposed_family="gaming-meta"),
    )
    record = result["records"][0]
    assert record["semantic_family"] is None
    assert record["attest"] is None
    assert result["receipt"]["settled_row_count"] == 0
    assert result["receipt"]["unresolved_row_count"] == 1
    assert settlement_allows_reserve(record) is False
    with pytest.raises(SystemExit, match="UNRESOLVED requires null"):
        _apply(stream, _decision(stream, decision="UNRESOLVED", semantic_family="gaming-meta", attest=""))


def test_rights_unresolved_settlement_cannot_enter_reserve():
    stream = _stream(
        "phrase reddit",
        hint="betting-sharp",
        source="reddit_title",
        label=None,
        label_source="UNLABELLED",
    )
    record = _apply(
        stream,
        _decision(
            stream,
            lane="D",
            semantic_family="betting-sharp",
            proposed_family="betting-sharp",
            attest="INFERRED",
        ),
    )["records"][0]
    assert record["rights"] == "RIGHTS_UNRESOLVED"
    assert record["semantic_family"] == "betting-sharp"
    assert settlement_allows_reserve(record) is False
    cleared = _apply(_stream("phrase clear"), _decision(_stream("phrase clear"), attest="OBSERVED"))["records"][0]
    assert settlement_allows_reserve(cleared) is True


def test_inactive_candidate_is_rejected_until_separately_activated():
    stream = _stream("phrase candidate", hint="none", label="none")
    with pytest.raises(SystemExit, match="candidate family is inactive"):
        _apply(stream, _decision(stream, semantic_family="sexual-romantic", proposed_family="sexual-romantic"))
    record = settle(
        [stream],
        [_decision(stream, semantic_family="sexual-romantic", proposed_family="sexual-romantic")],
        activated={"sexual-romantic"},
        **STAMP,
    )["records"][0]
    assert record["semantic_family"] == "sexual-romantic"
    assert family_flags("sexual-romantic")["taxonomy.active"] is False
    assert family_flags("sexual-romantic", activated={"sexual-romantic"}) == {
        "taxonomy.active": True,
        "evaluation.enabled": False,
        "production.enabled": False,
    }
    with pytest.raises(SystemExit, match="activation refused"):
        settle(
            [stream],
            [_decision(stream, semantic_family="brainrot-aura", proposed_family="")],
            activated={"brainrot-aura"},
            **STAMP,
        )


def test_invalid_family_and_attest_are_rejected():
    stream = _stream("phrase bad")
    with pytest.raises(SystemExit, match="not in the evaluation taxonomy"):
        _apply(
            stream,
            _decision(stream, semantic_family="workplace-corp", proposed_family="workplace-corp"),
        )
    with pytest.raises(SystemExit, match="invalid attest"):
        _apply(stream, _decision(stream, attest="UNLABELLED"))


def test_row_id_and_hash_mismatch_are_rejected():
    stream = _stream("phrase identity")
    with pytest.raises(SystemExit, match="not in the held-out stream"):
        _apply(stream, _decision(stream, row_id="hs-missing"))
    with pytest.raises(SystemExit, match="text_hash does not match"):
        _apply(stream, _decision(stream, text_hash="0" * 64))


def test_duplicate_settlement_is_rejected_and_log_is_append_only(tmp_path):
    stream = _stream("phrase once")
    decision = _decision(stream)
    with pytest.raises(SystemExit, match="duplicate settlement"):
        _apply(stream, [decision, decision])
    from hyperlexical.eval_settlement import commit_settlement

    first = _apply(stream, decision)
    log = tmp_path / "events.jsonl"
    receipt = tmp_path / "receipt.json"
    commit_settlement(first["records"], first["receipt"], log_path=log, receipt_path=receipt)
    before = log.read_bytes()
    with pytest.raises(SystemExit, match="duplicate settlement"):
        commit_settlement(
            first["records"],
            first["receipt"],
            log_path=log,
            receipt_path=tmp_path / "other.json",
        )
    assert log.read_bytes() == before
    assert receipt_sha_matches(json.loads(receipt.read_text(encoding="utf-8")))
    assert "phrase once" not in receipt.read_text(encoding="utf-8")


def test_legacy_production_attest_apply_behavior_is_unchanged():
    assert PRODUCTION_FAMILIES == (
        "betting-sharp",
        "crypto-degen",
        "ai-native",
        "brainrot-aura",
        "kinship-address",
        "political-status",
        "gaming-meta",
        "workplace-corp",
        "none",
    )
    assert tuple(WEAK_FAMILIES) == PRODUCTION_FAMILIES[:-1]
    legacy_valid = set(PRODUCTION_FAMILIES) | {"reject"}
    assert "workplace-career" not in legacy_valid
    assert "technology-ai" not in legacy_valid

    def legacy_outcome(value: str) -> str:
        if value not in legacy_valid:
            return "invalid"
        if value == "reject":
            return "attest_reject"
        return "label_source=OBSERVED"

    assert legacy_outcome("gaming-meta") == "label_source=OBSERVED"
    assert legacy_outcome("reject") == "attest_reject"
    assert legacy_outcome("workplace-career") == "invalid"
    module = (ROOT / "scripts" / "shadow" / "hyperlexical" / "eval_settlement.py").read_text(encoding="utf-8")
    assert "import layout" not in module
    assert ".admit(" not in module
    private = Path.home() / "hlx-private" / "heldout-stream" / "bin" / "hs_run.py"
    if private.is_file():
        source = private.read_text(encoding="utf-8")
        start = source.index("def cmd_attest_apply")
        end = source.index("\ndef main()")
        body = source[start:end]
        assert 'valid = set(FAMILIES) | {"none", "reject"}' in body
        assert 'r["label_source"] = "OBSERVED"' in source
        assert "workplace-career" not in body


def test_blank_sheet_settles_nothing_and_does_not_fill_decisions(tmp_path):
    stream = _stream("phrase blank")
    sheet = tmp_path / "lane-A.tsv"
    _sheet(sheet, stream, decision="", family="", attest="")
    before = sheet.read_bytes()
    parsed = parse_sheet(sheet, {stream["row_key"]: stream}, **{k: STAMP[k] for k in ("operator", "provenance", "settled_at")})
    assert parsed["records"] == []
    assert parsed["unset_row_count"] == 1
    assert sheet.read_bytes() == before


def test_three_taxonomy_flags_stay_distinct():
    assert len(ACTIVE_FAMILIES) == 18
    for name in ACTIVE_FAMILIES:
        assert family_flags(name) == {
            "taxonomy.active": True,
            "evaluation.enabled": False,
            "production.enabled": False,
        }
    for name in CANDIDATE_FAMILIES:
        assert family_flags(name)["taxonomy.active"] is False
        assert family_flags(name)["evaluation.enabled"] is False
    assert set(SURFACES) == {"A", "B", "C", "D", "HELD_OUTSIDE_LANES"}


def test_cli_blank_sheet_writes_zero_receipt_without_a_ledger(tmp_path):
    stream = _stream("phrase cli")
    rows = tmp_path / "rows.jsonl"
    rows.write_text(json.dumps(stream) + "\n", encoding="utf-8")
    sheet = tmp_path / "holding.tsv"
    _sheet(sheet, stream, lane="HELD_OUTSIDE_LANES", proposed="gaming-meta")
    receipt = tmp_path / "receipt.json"
    log = tmp_path / "events.jsonl"
    code = main(
        [
            "settlement-apply",
            "--stream-rows",
            str(rows),
            "--sheet",
            str(sheet),
            "--operator",
            "tool-ready",
            "--provenance",
            "blank-sheet validation",
            "--batch-id",
            "unit-cli",
            "--receipt",
            str(receipt),
            "--settlement-log",
            str(log),
            "--settled-at",
            "2026-09-26T16:00:00Z",
            "--stream-run-id",
            "hs-unit",
        ]
    )
    assert code == 0
    body = json.loads(receipt.read_text(encoding="utf-8"))
    assert body["settled_row_count"] == 0
    assert body["reserve_added"] == 0
    assert body["vendor_calls"] == 0
    assert body["ledger_mutated"] is False
    assert body["evaluation_enabled"] is False
    assert body["stream_run_id"] == "hs-unit"
    assert body["settled_at"] == "2026-09-26T16:00:00Z"
    assert body["input_sheets"][0]["identity"] == "holding.tsv"
    assert len(body["input_sheets"][0]["sha256"]) == 64
    assert body["unset_row_count"] == 1
    assert body["unresolved_row_count"] == 0
    assert log.read_text(encoding="utf-8") == ""
    assert not (tmp_path / "ledger.json").exists()
    assert "phrase cli" not in receipt.read_text(encoding="utf-8")


def test_private_lane_sheets_parse_without_rewriting():
    root = Path.home() / "hlx-private" / "heldout-stream"
    stream_path = root / "store" / "rows.jsonl"
    attest = root / "attest"
    names = {
        "A": "lane-A-confirm-20260926.tsv",
        "B": "lane-B-proposed-family-20260926.tsv",
        "C": "lane-C-disambiguate-20260926.tsv",
        "D": "lane-D-rights-blocked-20260926.tsv",
        "HELD_OUTSIDE_LANES": "holding-hint-only-outside-lanes-20260926.tsv",
    }
    if not stream_path.is_file() or not all((attest / name).is_file() for name in names.values()):
        pytest.skip("private lane sheets are host-local")
    from hyperlexical.eval_settlement import load_stream

    stream = load_stream(stream_path)
    expected = {"A": 204, "B": 65, "C": 21, "D": 16, "HELD_OUTSIDE_LANES": 33}
    for lane, name in names.items():
        path = attest / name
        before = path.read_bytes()
        parsed = parse_sheet(
            path,
            stream,
            operator="tool-ready",
            provenance="blank-sheet validation",
            settled_at="2026-09-26T16:00:00Z",
        )
        assert parsed["unset_row_count"] + len(parsed["records"]) == expected[lane]
        assert parsed["lane_rows"] == {lane: expected[lane]}
        assert path.read_bytes() == before
