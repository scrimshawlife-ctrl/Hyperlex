"""Synthetic proposed-contract controls; no corpus or checkpoint evidence.

Provenance: Notion Sprint 001 Hub NOT_COMPUTABLE + Loop 805 Slice N/A
+ Hash: b3eee725054c1ed1dae16fad3464af005edad0cc (base).
"""
import copy
import hashlib
import json

import pytest
from scripts.shadow.hyperlexical.training_contracts import digest, main, validate


def seal(b):
    for k, v in [("source_sha256", b["sources"]), ("annotation_sha256", b["annotations"]),
                 ("split_sha256", b["split"])]:
        b["run"][k] = digest(v)
    return b


def fixture():
    b = {
        "sources": [{"version": "source.v1", "source_id": "s1", "raw_text": "same same",
                     "text_sha256": hashlib.sha256(b"same same").hexdigest(),
                     "source_kind": "synthetic", "rights_status": "approved",
                     "rights_reference": "synthetic test", "provenance_reference": "synthetic control"}],
        "annotations": [{"version": "annotation.v1", "example_id": "e1", "source_id": "s1",
                         "group_ids": ["g1"], "offset_unit": "unicode_codepoint", "ontology_version": "proposal-v1",
                         "spans": [{"occurrence_id": "o1", "start": 0, "end": 4, "text": "same", "role": "pos_0"},
                                   {"occurrence_id": "o2", "start": 5, "end": 9, "text": "same", "role": "pos_1"}],
                         "labels": {"family": {"status": "unreviewed", "values": [], "loss_mask": False,
                                               "method": "not annotated", "reviewer": None}}}],
        "split": {"version": "split.v1", "split_id": "split1", "assignments": [{"example_id": "e1", "partition": "dev"}]},
        "run": {"version": "run.v1", "run_id": "r1", "code_commit": "a" * 40, "code_patch_sha256": "b" * 64,
                "source_sha256": "c" * 64, "annotation_sha256": "c" * 64, "split_sha256": "c" * 64,
                "checkpoint_sha256": "d" * 64, "trunk_revision": "fixture-only", "tokenizer_revision": "fixture-only",
                "seed": 1, "environment": {"python": "fixture"},
                "recipe": {"sampler": "seeded", "optimizer": "test", "learning_rate": 0.001, "batch_size": 1, "epochs": 1},
                "name_gate": False, "brier": None},
        "evaluation": {"version": "evaluation.v1", "protocol_id": "p1", "run_id": "r1", "population": "dev",
                       "example_ids": ["e1"], "task": "surface_extraction", "decoder_access": "text",
                       "n_evaluated": 1, "n_exact": 1, "exact": 1.0, "name_gate": False, "brier": None},
    }
    return seal(b)


def test_positive_and_no_mutation():
    b = fixture()
    prior = copy.deepcopy(b)
    assert validate(b)["status"] == "CONTRACT_VALID"
    assert b == prior


@pytest.mark.parametrize("path,value", [
    (("sources", 0, "text_sha256"), "0" * 64),
    (("sources", 0, "rights_status"), "unreviewed"),
    (("sources", 0, "unexpected"), True),
    (("annotations", 0, "source_id"), "missing"),
    (("annotations", 0, "spans", 0, "start"), 1),
    (("annotations", 0, "spans", 0, "end"), 100),
    (("annotations", 0, "spans", 0, "start"), True),
    (("annotations", 0, "spans", 0, "start"), 0.0),
    (("annotations", 0, "spans", 1, "occurrence_id"), "o1"),
    (("annotations", 0, "labels", "family", "loss_mask"), True),
    (("annotations", 0, "labels", "family", "status"), "reviewed"),
    (("split", "assignments", 0, "example_id"), "missing"),
    (("run", "name_gate"), True),
    (("run", "recipe", "learning_rate"), 0),
    (("evaluation", "n_exact"), 2),
    (("evaluation", "exact"), 0.5),
    (("evaluation", "run_id"), "other"),
    (("evaluation", "example_ids"), ["missing"]),
    (("evaluation", "decoder_access"), "representation_only"),
    (("evaluation", "population"), "test"),
])
def test_rejects_invalid_contracts(path, value):
    b = fixture()
    target = b
    for k in path[:-1]:
        target = target[k]
    target[path[-1]] = value
    with pytest.raises(ValueError):
        validate(seal(b))


@pytest.mark.parametrize("field", ["source_sha256", "annotation_sha256", "split_sha256"])
def test_run_hash_mismatch(field):
    b = fixture()
    b["run"][field] = "0" * 64
    with pytest.raises(ValueError, match="run content hash"):
        validate(b)


@pytest.mark.parametrize("collection", ["sources", "annotations"])
def test_duplicate_ids(collection):
    b = fixture()
    b[collection].append(copy.deepcopy(b[collection][0]))
    with pytest.raises(ValueError, match="duplicate"):
        validate(seal(b))


@pytest.mark.parametrize("kind", ["source", "declared", "normalized"])
def test_group_overlap(kind):
    b = fixture()
    a = copy.deepcopy(b["annotations"][0])
    a["example_id"] = "e2"
    if kind != "source":
        s = copy.deepcopy(b["sources"][0])
        s["source_id"] = "s2"
        a["source_id"] = "s2"
        b["sources"].append(s)
    if kind == "declared":
        s["raw_text"] = "some same"
        s["text_sha256"] = hashlib.sha256(s["raw_text"].encode()).hexdigest()
        a["spans"][0]["text"] = "some"
    else:
        a["group_ids"] = ["g2"]
    b["annotations"].append(a)
    b["split"]["assignments"].append({"example_id": "e2", "partition": "train"})
    with pytest.raises(ValueError, match="group crosses"):
        validate(seal(b))


def test_cli_private_failure_and_duplicate_json(tmp_path, capsys):
    p = tmp_path / "bundle.json"
    payload = json.dumps(fixture())
    p.write_text(payload, encoding="utf-8")
    assert main(["--bundle", str(p)]) == 0
    assert "CONTRACT_VALID" in capsys.readouterr().out
    assert p.read_text(encoding="utf-8") == payload
    p.write_text('{"private":"secret", "private":"duplicate"}', encoding="utf-8")
    assert main(["--bundle", str(p)]) == 2
    out = capsys.readouterr().out
    assert "CONTRACT_INVALID" in out and "secret" not in out


def test_nonfinite_and_ordered_digest():
    with pytest.raises(ValueError):
        digest(float("nan"))
    assert digest({"b": 2, "a": 1}) == digest({"a": 1, "b": 2})
    assert digest([1, 2]) != digest([2, 1])


def test_bound_access_and_residual_declarations():
    b = fixture()
    b["evaluation"].update(task="bound_recovery", decoder_access="representation_only", population="residual_only")
    assert validate(b)["runtime_proof"] == "NOT_COMPUTABLE"
