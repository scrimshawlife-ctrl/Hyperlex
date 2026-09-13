"""Synthetic controls only; no Spark residuals become training fixtures.

Provenance: Notion Sprint 001 Hub NOT_COMPUTABLE + Loop 805 Slice N/A
+ Hash: versioned with repository patch.
"""
import json

import pytest
from scripts.shadow.hyperlexical.extraction_baseline import evaluate, extract, main


def row(text="same same", scheme="positional"):
    spans = extract(text, scheme)
    return {"text": text, "role_scheme": scheme, "task": "unbind",
            "fillers": [s["filler"] for s in spans],
            "roles": [s["role"] for s in spans]}


@pytest.mark.parametrize("scheme,text", [
    ("positional", "  same\tsame!  same\n"),
    ("type_slot", "TOKEN:Case SLOT:word. MARKER:: TOKEN:Case"),
    ("positional", "éclair 👋 mixed-case URL:https://example.invalid"),
])
def test_offsets_preserve_occurrences(scheme, text):
    spans = extract(text, scheme)
    assert len({s["start"] for s in spans}) == len(spans)
    assert [s["occurrence"] for s in spans] == list(range(len(spans)))
    assert all(text[s["start"]:s["end"]] == s["filler"] for s in spans)


@pytest.mark.parametrize("text,scheme", [("", "positional"), (None, "positional"),
    ("x", "unknown"), ("TOKEN:", "type_slot"), ("WRONG:x", "type_slot"),
    ("TOKEN:x bare", "type_slot"), ("token:x", "type_slot"), ("x", [])])
def test_bad_grammar_rejected(text, scheme):
    with pytest.raises(ValueError):
        extract(text, scheme)


def test_gold_is_not_prediction_input():
    r = row()
    assert evaluate([r], population="evaluation_set")["n_filler_exact"] == 1
    r["fillers"] = ["different", "gold"]
    result = evaluate([r], population="evaluation_set")
    assert result["n_filler_exact"] == 0
    assert not result["uses_gold_for_prediction"]


def test_role_mismatch_is_not_structure_success():
    r = row()
    r["roles"].reverse()
    result = evaluate([r], population="evaluation_set")
    assert result["n_filler_exact"] == 1
    assert result["n_structure_exact"] == 0


def test_rejected_rows_stay_in_denominator():
    result = evaluate([row(), {}], population="evaluation_set")
    assert result["n_rejected"] == 1
    assert result["filler_exact_all_input"] == 0.5


def residual():
    r = row()
    r["gold"] = r.pop("fillers")
    r.update(pred=["same", "other"], slot_tp=1, slot_n_gold=2,
             token_tp=1, token_n_gold=2, token_n_pred=2)
    return r


def test_residual_counter_control():
    r = residual()
    result = evaluate([r], population="residual_only")
    assert result["prior_one_wrong_slot_rows"] == 1
    assert result["n_structure_exact"] == 1
    assert result["full_validation_accuracy"] == "NOT_COMPUTABLE"
    r["slot_tp"] = 2
    assert evaluate([r], population="residual_only")["n_rejected"] == 1


@pytest.mark.parametrize("bad", [None, {}, [], {"text":"x"}])
def test_bad_rows_are_accounted_for(bad):
    assert evaluate([bad], population="evaluation_set")["n_rejected"] == 1


def test_cli_read_only_and_private_diagnostics(tmp_path, capsys):
    p = tmp_path / "input.jsonl"
    payload = json.dumps(residual()) + "\n"
    p.write_text(payload, encoding="utf-8")
    assert main(["--input", str(p), "--population", "residual_only"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["input_sha256"]
    assert not result["name_gate"]
    assert p.read_text(encoding="utf-8") == payload
    p.write_text('private malformed content', encoding="utf-8")
    assert main(["--input", str(p), "--population", "residual_only"]) == 2
    assert "private" not in capsys.readouterr().out


def test_duplicate_reporting_and_empty_fail_closed():
    assert evaluate([row(), row()], population="evaluation_set")["duplicate_text_scheme_rows"] == 1
    with pytest.raises(ValueError):
        evaluate([], population="evaluation_set")
    with pytest.raises(ValueError):
        evaluate([row()], population="unknown")
