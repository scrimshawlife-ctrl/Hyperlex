"""Synthetic preparation controls; no real rights or training claims."""
import copy
import hashlib
import json
import zipfile

import pytest
from test_training_adapter import dataset

from scripts.shadow.hyperlexical.training_adapter import (
    align_occurrences,
    prepare_reviewed,
)
from scripts.shadow.hyperlexical.training_contracts import digest
from scripts.shadow.hyperlexical.training_prepare import (
    export_package,
    main,
    prepare,
    verify_package,
)


def encoded(value):
    return json.dumps(value).encode()


def reviewed_inputs():
    d = dataset()
    a = d["annotations"][0]
    row = {"text": d["sources"][0]["raw_text"]}
    metadata = {digest(row): {"source": d["sources"][0], "annotation": a, "partition": "dev"}}
    # Intake assigns its own declared split id.
    d["split"]["split_id"] = "intake-review-v1"
    tokenization = {"dataset_sha256": digest(d), "tokenizer_revision": "synthetic-offsets-v1",
                    "offset_unit": "unicode_codepoint", "examples": {"e1": [[0, 0], [0, 4], [5, 9], [0, 0]]}}
    return encoded(row), encoded(metadata), tokenization


def test_repeated_occurrences_have_distinct_tokens_and_both_heads():
    payload, metadata, tokenization = reviewed_inputs()
    result = prepare(payload, metadata, ontology="proposal-v1", tokenization=tokenization)
    plan = result["plan"]
    assert [s["token_indices"] for s in plan["rows"][0]["aligned_occurrences"]] == [[1], [2]]
    assert plan["selected_example_ids"]["structure"]["val"] == ["e1"]
    assert plan["selected_example_ids"]["family"]["val"] == ["e1"]
    assert plan["legacy_routing_diagnostic"]["combined_unbind_suppressed"] == 1
    assert result["report"]["training_ready"] is False
    assert plan["train_only_vocabularies"]["fillers"] == ["<unk>"]
    assert plan["rows"][0]["target_known"]["fillers"] == [False, False]
    assert plan["rows"][0]["fillers"] == ["same", "same"]
    assert result == prepare(payload, metadata, ontology="proposal-v1", tokenization=tokenization)


@pytest.mark.parametrize("offsets", [[], [[0, 4]], [[0, 9]], [[0, 3], [5, 9]],
                                    [[True, 4], [5, 9]], [[0.0, 4], [5, 9]],
                                    [[0, 4], [3, 9]], [[5, 9], [0, 4]], [[0, 99]], [[0]], None])
def test_bad_truncated_or_spilling_offsets_rejected(offsets):
    d = dataset()
    with pytest.raises((TypeError, ValueError)):
        align_occurrences("same same", d["annotations"][0]["spans"], offsets)


def test_unicode_and_multiword_whitespace():
    spans = [{"occurrence_id": "o", "start": 2, "end": 9, "text": "hi moon", "role": "pos_0"}]
    assert align_occurrences("🌙 hi moon", spans, [[0, 1], [2, 4], [5, 9]])[0]["token_indices"] == [1, 2]


@pytest.mark.parametrize("kind", ["hash", "unit", "extra", "missing", "revision"])
def test_tokenization_binding_rejected(kind):
    payload, metadata, tokens = reviewed_inputs()
    if kind == "hash":
        tokens["dataset_sha256"] = "0" * 64
    elif kind == "unit":
        tokens["offset_unit"] = "bytes"
    elif kind == "extra":
        tokens["examples"]["invented"] = []
    elif kind == "missing":
        tokens["examples"] = {}
    else:
        tokens["tokenizer_revision"] = " "
    with pytest.raises(ValueError):
        prepare(payload, metadata, ontology="proposal-v1", tokenization=tokens)


def test_missing_offsets_preserve_family_and_block_structure():
    payload, metadata, _ = reviewed_inputs()
    plan = prepare(payload, metadata, ontology="proposal-v1")["plan"]
    assert plan["selected_example_ids"]["family"]["val"] == ["e1"]
    assert plan["selected_example_ids"]["structure"]["val"] == []
    assert plan["alignment_blocked"] == [{"example_id": "e1", "reason": "MISSING_TOKENIZATION"}]


def test_no_automatic_observed_approval_and_exact_accounting():
    result = prepare(b'{"text":"private", "class":"OBSERVED"}\n{bad}\n', ontology="proposal-v1")
    assert result["report"]["n_records"] == 2
    assert result["report"]["n_quarantined"] == 2
    assert result["dataset"] is result["plan"] is None
    assert len(result["review_queue"]) == 2
    assert "private" not in json.dumps(result["report"])


def test_valid_three_partition_plan_no_mutation_or_test_consumption():
    d = dataset()
    for a in d["annotations"]:
        a["labels"]["structure"]["loss_mask"] = False
    for partition in ("train", "test"):
        source = copy.deepcopy(d["sources"][0])
        source.update(source_id=partition, raw_text=partition)
        source["text_sha256"] = hashlib.sha256(partition.encode()).hexdigest()
        ann = copy.deepcopy(d["annotations"][0])
        ann.update(source_id=partition, example_id=partition, group_ids=[partition], spans=[])
        d["sources"].append(source)
        d["annotations"].append(ann)
        d["split"]["assignments"].append({"example_id": partition, "partition": partition})
    before = copy.deepcopy(d)
    plan = prepare_reviewed(d, expected_ontology="proposal-v1")
    assert plan["status"] == "PREPARED_NOT_RUNNABLE"
    assert plan["selected_example_ids"]["family"] == {"train": ["train"], "val": ["e1"]}
    assert plan["row_outcomes"] == {"selected": 2, "reserved_test": 1}
    assert d == before


def test_export_hashes_no_overwrite_and_cli_privacy(tmp_path, capsys):
    payload, metadata, tokens = reviewed_inputs()
    result = prepare(payload, metadata, ontology="proposal-v1", tokenization=tokens)
    out = tmp_path / "prepared"
    export_package(out, result, payload, metadata, encoded(tokens))
    receipt = json.loads((out / "receipt.json").read_text())
    assert verify_package(out)["status"] == "PACKAGE_VERIFIED"
    for name, expected in receipt["files_sha256"].items():
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == expected
    with pytest.raises(FileExistsError):
        export_package(out, result, payload)
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("rows.jsonl", payload)
    assert main(["--input", str(archive), "--zip-member", "rows.jsonl", "--ontology", "proposal-v1"]) == 3
    printed = json.loads(capsys.readouterr().out)
    assert printed["n_quarantined"] == 1
    assert "same same" not in json.dumps(printed)
    assert main(["--input", str(archive), "--zip-member", "absent", "--ontology", "proposal-v1"]) == 2


def test_cli_successful_adaptation_and_duplicate_json_rejection(tmp_path, capsys):
    payload, metadata, tokens = reviewed_inputs()
    src, meta, tok = [tmp_path / n for n in ("input.jsonl", "meta.json", "tokens.json")]
    src.write_bytes(payload)
    meta.write_bytes(metadata)
    tok.write_bytes(encoded(tokens))
    args = ["--input", str(src), "--metadata", str(meta), "--tokenization", str(tok), "--ontology", "proposal-v1"]
    assert main(args) == 3  # dev-only synthetic dataset is honestly blocked
    assert json.loads(capsys.readouterr().out)["n_adapted"] == 1
    tok.write_text('{"private":1,"private":2}')
    assert main(args) == 2
    assert "private" not in capsys.readouterr().out


@pytest.mark.parametrize("kind", ["bytes", "receipt", "extra", "traversal", "forged_artifact", "forged_claim"])
def test_verify_package_negative_controls(tmp_path, kind):
    payload, metadata, tokens = reviewed_inputs()
    result = prepare(payload, metadata, ontology="proposal-v1", tokenization=tokens)
    out = tmp_path / "prepared"
    export_package(out, result, payload, metadata, encoded(tokens))
    assert verify_package(out)["status"] == "PACKAGE_VERIFIED"
    receipt = json.loads((out / "receipt.json").read_text())
    if kind == "bytes":
        (out / "original.jsonl").write_bytes(b'changed')
    elif kind == "receipt":
        receipt["n_records"] += 1
    elif kind == "extra":
        (out / "extra.json").write_text('{}')
    elif kind == "traversal":
        receipt["files_sha256"]["../escape"] = "0" * 64
    elif kind == "forged_claim":
        receipt["rights_independently_verified"] = True
    else:
        (out / "plan.json").write_text('{}')
        receipt["files_sha256"]["plan.json"] = hashlib.sha256(b'{}').hexdigest()
    (out / "receipt.json").write_text(json.dumps(receipt))
    with pytest.raises(ValueError):
        verify_package(out)


def test_training_vocab_excludes_heldout_and_reserved_target():
    d = dataset()
    source = copy.deepcopy(d["sources"][0])
    source.update(source_id="train", raw_text="blue moon", text_sha256=hashlib.sha256(b'blue moon').hexdigest())
    ann = copy.deepcopy(d["annotations"][0])
    ann.update(source_id="train", example_id="train", group_ids=["train"])
    for span, text in zip(ann["spans"], ["blue", "moon"], strict=True):
        span["text"] = text
    d["sources"].append(source)
    d["annotations"].append(ann)
    d["split"]["assignments"].append({"example_id": "train", "partition": "train"})
    tokens = {"dataset_sha256": digest(d), "tokenizer_revision": "synthetic-v1", "offset_unit": "unicode_codepoint",
              "examples": {eid: [[0, 4], [5, 9]] for eid in ["e1", "train"]}}
    plan = prepare_reviewed(d, expected_ontology="proposal-v1", tokenization=tokens)
    assert plan["train_only_vocabularies"]["fillers"] == ["<unk>", "blue", "moon"]
    assert plan["rows"][1]["target_ids"]["fillers"] == [1, 2]
    assert plan["rows"][0]["target_known"]["fillers"] == [False, False]
    ann["spans"][0]["role"] = "<unk>"
    tokens["dataset_sha256"] = digest(d)
    with pytest.raises(ValueError, match="reserved unknown"):
        prepare_reviewed(d, expected_ontology="proposal-v1", tokenization=tokens)


@pytest.mark.parametrize("field,value", [("container_sha256", "0" * 64), ("zip_member", "absent"), ("invented", True)])
def test_cli_archive_identity_is_recomputed(tmp_path, capsys, field, value):
    src, out = tmp_path / "source.zip", tmp_path / "out"
    with zipfile.ZipFile(src, "w") as archive:
        archive.writestr("rows.jsonl", '{"text":"private"}')
    assert main(["--input", str(src), "--zip-member", "rows.jsonl", "--ontology", "test-v1", "--out-dir", str(out)]) == 3
    capsys.readouterr()
    assert verify_package(out)["status"] == "PACKAGE_VERIFIED"
    assert (out / "container.zip").read_bytes() == src.read_bytes()
    receipt = json.loads((out / "receipt.json").read_text())
    receipt[field] = value
    (out / "receipt.json").write_text(json.dumps(receipt))
    with pytest.raises(ValueError):
        verify_package(out)
