"""Clean-unbind admission. Contamination hash and the clean predicate stay distinct."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.clean_unbind import (  # noqa: E402
    admit_clean_unbind,
    dual_scheme_rows,
    gate_rows,
    read_wordnet_index,
    schema_example,
    select_diverse,
    structural_reason,
)
from hyperlexical.holdout_guard import normalized_text_sha256  # noqa: E402
from hyperlexical.identity_ledger import IdentityLedger  # noqa: E402
from hyperlexical.unbind_settlement import (  # noqa: E402
    append_events,
    event_from_decision,
    load_events,
)

LICENSE = "Example rights grant for unit fixtures"
OPERATOR = "unit-operator"
WHEN = "2026-09-26T00:00:00Z"


def _rows(tokens, **kwargs):
    return dual_scheme_rows(
        tokens,
        license=kwargs.pop("license", LICENSE),
        provenance=kwargs.pop("provenance", "source:unit"),
        target_origin=kwargs.pop("target_origin", "source_lemma_tokens"),
        **kwargs,
    )


def _accept(row, decision="ACCEPT", previous=""):
    from hyperlexical.clean_unbind import target_sha256

    return event_from_decision(
        normalized_text_sha256=normalized_text_sha256(row["text"]),
        decision=decision,
        target_sha256=target_sha256(row["fillers"]),
        target_provenance=row["target_origin"],
        operator=OPERATOR,
        settled_at=WHEN,
        decision_basis="source_lemma_token_identity",
        previous_target_sha256=previous,
    )


def _settled(rows, **overrides):
    events = []
    for row in rows:
        cloned = dict(row)
        if "decision" in overrides:
            decision = overrides["decision"]
        else:
            decision = "ACCEPT"
        events.append(_accept(cloned, decision=decision))
    return {event["normalized_text_sha256"]: event for event in events}


def _train(text):
    return {"text": text, "split": "train", "task": "unbind", "role_scheme": "positional"}


def _classify(text):
    return {
        "text": text,
        "task": "classify",
        "class": "OBSERVED",
        "lineage": "gaming-meta",
        "split": "eval",
        "fillers": [],
        "roles": [],
        "role_scheme": None,
    }


def test_schema_example_uses_placeholders_only():
    example = schema_example()
    blob = json.dumps(example)
    assert "EXAMPLE_TOKEN_A" in blob
    assert example["positional"]["task"] == "unbind"
    assert example["scorer"]["this_module_scores"] is False
    assert example["scorer"]["clean_slice"] == "soft_ceiling.clean_surface"


def test_novel_clean_unbind_is_admitted_and_dirty_is_not():
    novel = _rows(["qxalpha", "qxbeta"])
    dirty = _rows(["qxdirty", "qxphrase"])
    ledger = IdentityLedger()
    report = admit_clean_unbind(
        ledger,
        novel + dirty,
        batch_id="unit-clean",
        source_artifact="unit",
        train_rows=[_train(row["text"]) for row in dirty],
        settlements=_settled(novel + dirty),
    )
    assert report["unique_admitted_to_eval_reserve"] == 2
    assert report["reserve_counts_after"]["unbind_clean"] == 2
    assert report["rejection_counts"]["not_clean"] == 2
    assert report["unique_routed_to_train_candidate"] == 0
    for row in dirty:
        assert ledger.identity(normalized_text_sha256(row["text"])) is None


def test_missing_target_model_target_and_unresolved_rights_are_rejected():
    missing = _rows(["qxmiss", "qxtarget"])[0]
    missing["fillers"] = []
    modeled = _rows(["qxmodel", "qxtarget"], target_origin="model")
    unresolved = _rows(["qxrights", "qxtarget"], license="RIGHTS_UNRESOLVED")
    ledger = IdentityLedger()
    _admissible, rejections, _account = gate_rows(
        [missing, modeled[0], unresolved[0]],
        train_rows=[],
        ledger=ledger,
        settlements={},
    )
    reasons = {item["reason"] for item in rejections}
    assert "missing_target" in reasons
    assert "model_derived_target" in reasons
    assert "rights_unresolved" in reasons
    assert ledger.reserve_counts()["unbind_clean"] == 0


def test_blocked_ledger_states_reject_the_same_surface():
    surface = ["qxblock", "qxsurface"]
    rows = _rows(surface)
    positional = rows[0]
    digest = normalized_text_sha256(positional["text"])
    reasons = []
    for flag, reason in (
        ("training_consumed", "TRAIN_CONSUMED"),
        ("evaluation_spent", "EVAL_SPENT"),
        ("evaluation_abandoned", "EVAL_ABANDONED"),
    ):
        ledger = IdentityLedger()
        ledger.observe_row(positional, source_artifact="pin", provenance="pin", catalogued=True)
        ledger.mark_historical(digest, flag, source_artifact="pin", provenance=flag)
        _kept, rejections, _account = gate_rows(
            [positional],
            train_rows=[],
            ledger=ledger,
            settlements=_settled([positional]),
        )
        assert rejections[0]["reason"] == reason
        reasons.append(reason)
        assert ledger.reserve_counts()["unbind_clean"] == 0
    reserved = IdentityLedger()
    reserved.admit(
        [_classify(positional["text"])],
        batch_id="unit-reserve",
        source_artifact="unit",
        targets={"classify": 5, "classify_observed": 5, "classify_non_none": 5, "unbind_clean": 5},
    )
    assert reserved.reserve_counts()["classify"] == 1
    _kept, rejections, _account = gate_rows(
        [positional],
        train_rows=[],
        ledger=reserved,
        settlements=_settled([positional]),
    )
    assert rejections[0]["reason"] == "EVAL_RESERVE"
    assert reserved.reserve_counts()["classify"] == 1
    assert reserved.reserve_counts()["unbind_clean"] == 0
    assert reasons == ["TRAIN_CONSUMED", "EVAL_SPENT", "EVAL_ABANDONED"]


def test_two_surfaces_one_target_stay_distinct_and_classify_reserve_holds():
    pair = _rows(["qxshared", "qxtarget"], source_pos="noun")
    assert normalized_text_sha256(pair[0]["text"]) != normalized_text_sha256(pair[1]["text"])
    from hyperlexical.clean_unbind import target_sha256

    assert target_sha256(pair[0]["fillers"]) == target_sha256(pair[1]["fillers"])
    ledger = IdentityLedger()
    ledger.admit(
        [_classify("qxclassify qxonly")],
        batch_id="unit-classify",
        source_artifact="unit",
        targets={"classify": 5, "classify_observed": 5, "classify_non_none": 5, "unbind_clean": 5},
    )
    before = ledger.reserve_counts()
    report = admit_clean_unbind(
        ledger,
        pair,
        batch_id="unit-pair",
        source_artifact="unit",
        train_rows=[],
        settlements=_settled(pair),
    )
    after = ledger.reserve_counts()
    assert after["classify"] == before["classify"] == 1
    assert after["classify_observed"] == before["classify_observed"]
    assert after["classify_non_none"] == before["classify_non_none"]
    assert after["unbind_clean"] == 2
    assert report["diversity"]["unique_targets"] == 1
    assert report["diversity"]["max_surfaces_per_target"] == 2
    assert report["diversity"]["role_scheme"] == {"positional": 1, "type_slot": 1}


def test_settlement_correction_appends_and_reject_does_not_admit(tmp_path):
    row = _rows(["qxsettle", "qxatom"])[0]
    first = _accept(row, decision="ACCEPT")
    log = tmp_path / "events.jsonl"
    append_events(log, [first])
    corrected = event_from_decision(
        normalized_text_sha256=first["normalized_text_sha256"],
        decision="CORRECT_TARGET",
        target_sha256="b" * 64,
        previous_target_sha256=first["target_sha256"],
        target_provenance="operator_authored",
        operator=OPERATOR,
        settled_at=WHEN,
        decision_basis="operator_correction",
    )
    append_events(log, [corrected])
    body = log.read_text(encoding="utf-8").splitlines()
    assert len(body) == 2
    assert json.loads(body[0])["decision"] == "ACCEPT"
    assert json.loads(body[1])["decision"] == "CORRECT_TARGET"
    assert load_events(log)[0] == json.loads(body[0])
    rejected = _rows(["qxno", "qxadmit"])
    ledger = IdentityLedger()
    report = admit_clean_unbind(
        ledger,
        rejected,
        batch_id="unit-reject",
        source_artifact="unit",
        train_rows=[],
        settlements=_settled(rejected, decision="REJECT"),
    )
    assert report["unique_admitted_to_eval_reserve"] == 0
    assert report["rejection_counts"]["settlement_reject"] == 2
    assert structural_reason(rejected[0]) is None


def test_diverse_selection_is_not_one_token_length():
    short = []
    for index in range(4):
        short.extend(_rows([f"qxshort{index}", "qxbeta"], source_pos="noun"))
    long = _rows(["qxone", "qxtwo", "qxthree", "qxfour", "qxfive", "qxsix"], source_pos="noun")
    picked = select_diverse(short + long, limit=4)
    lengths = {len(row["fillers"]) for row in picked}
    assert 6 in lengths
    assert 2 in lengths


def test_wordnet_index_reader_keeps_lemma_text_out_of_provenance(tmp_path):
    (tmp_path / "index.noun").write_text(
        "  copyright line\nqxunit_qxlemma n 1 1 @ 1 0 00000001\nqxonly n 1 1 @ 1 0 00000002\n",
        encoding="utf-8",
    )
    for name in ("index.verb", "index.adj", "index.adv"):
        (tmp_path / name).write_text("  copyright\n", encoding="utf-8")
    atoms = read_wordnet_index(tmp_path)
    assert len(atoms) == 1
    assert atoms[0]["tokens"] == ["qxunit", "qxlemma"]
    assert "qxunit_qxlemma" not in atoms[0]["lemma_sha256"]


def test_cli_train_export_marks_clean_surface_only(tmp_path):
    from hyperlexical.identity_ledger import main

    ledger_dir = tmp_path / "ledger"
    ledger = IdentityLedger()
    ledger.save(ledger_dir)
    rows_path = tmp_path / "rows.jsonl"
    train_path = tmp_path / "train.jsonl"
    novel = _rows(["qxcli", "qxnovel"])[0]
    dirty = _rows(["qxcli", "qxdirty"])[0]
    rows_path.write_text(json.dumps(novel) + "\n" + json.dumps(dirty) + "\n", encoding="utf-8")
    train_path.write_text(json.dumps(_train(dirty["text"])) + "\n", encoding="utf-8")
    assert (
        main(
            [
                "admit",
                "--ledger",
                str(ledger_dir),
                "--rows",
                str(rows_path),
                "--batch-id",
                "unit-cli",
                "--source",
                "unit",
                "--train-export",
                str(train_path),
            ]
        )
        == 0
    )
    loaded = IdentityLedger.load(ledger_dir)
    assert loaded.reserve_counts()["unbind_clean"] == 1
    dirty_record = loaded.identity(normalized_text_sha256(dirty["text"]))
    assert dirty_record is not None
    assert all(label.get("unbind_clean") is not True for label in dirty_record["labels"])
