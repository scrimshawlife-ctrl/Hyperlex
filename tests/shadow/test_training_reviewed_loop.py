"""Reviewed trainer controls. No private rights or BEST overwrite claims."""
from __future__ import annotations

import copy
import hashlib
import tempfile
from pathlib import Path

import pytest

from scripts.shadow.hyperlexical import loop
from scripts.shadow.hyperlexical.training_adapter import prepare_reviewed
from scripts.shadow.hyperlexical.training_contracts import digest
from scripts.shadow.hyperlexical.training_reviewed_loop import (
    assert_consumption_matches_selection,
    assert_pinned_token_indices,
    assert_plan_eligible,
    collate_reviewed_batch,
    compare_uninterrupted_vs_resumed,
    gold_span_diagnostics,
    run_reviewed_train,
    select_split_rows,
    selected_train_example_ids,
    structure_exact_match,
)
from test_training_contracts import fixture


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def eligible_plan():
    base = fixture()
    src0, ann0 = base["sources"][0], base["annotations"][0]
    ontology = ann0["ontology_version"]
    parts = [
        ("train", "alpha beta", [(0, 5, "alpha", "pos_0"), (6, 10, "beta", "pos_1")]),
        ("dev", "gamma delta", [(0, 5, "gamma", "pos_0"), (6, 11, "delta", "pos_1")]),
        ("test", "epsilon zeta", [(0, 7, "epsilon", "pos_0"), (8, 12, "zeta", "pos_1")]),
    ]
    sources, annotations, assignments = [], [], []
    for i, (partition, text, spans) in enumerate(parts):
        source_id, example_id = f"s{i}", f"e{i}"
        source = copy.deepcopy(src0)
        source.update(source_id=source_id, raw_text=text, text_sha256=_sha(text))
        sources.append(source)
        family = copy.deepcopy(ann0["labels"]["family"])
        family.update(status="reviewed", values=["none"], loss_mask=True, reviewer="synthetic")
        structure = copy.deepcopy(family)
        structure["values"] = [role for *_, role in spans]
        ann_spans = []
        for j, (start, end, span_text, role) in enumerate(spans):
            ann_spans.append(
                {
                    **{
                        k: v
                        for k, v in ann0["spans"][0].items()
                        if k not in ("occurrence_id", "start", "end", "text", "role")
                    },
                    "occurrence_id": f"o{i}{j}",
                    "start": start,
                    "end": end,
                    "text": span_text,
                    "role": role,
                }
            )
        annotation = copy.deepcopy(ann0)
        annotation.update(
            source_id=source_id,
            example_id=example_id,
            group_ids=[f"g{i}"],
            spans=ann_spans,
            labels={"family": family, "structure": structure},
        )
        annotations.append(annotation)
        assignments.append({"example_id": example_id, "partition": partition})
    dataset = {
        "sources": sources,
        "annotations": annotations,
        "split": {**base["split"], "assignments": assignments},
    }
    tokenization = {
        "dataset_sha256": digest(dataset),
        "tokenizer_revision": "synthetic-reviewed-trainer-v1",
        "offset_unit": "unicode_codepoint",
        "examples": {
            f"e{i}": [[0, 0]] + [[start, end] for start, end, _, _ in parts[i][2]] + [[0, 0]]
            for i in range(3)
        },
    }
    plan = prepare_reviewed(dataset, expected_ontology=ontology, tokenization=tokenization)
    assert plan["status"] == "PREPARED_NOT_RUNNABLE"
    assert plan["blockers"] == []
    return plan


def test_legacy_loop_still_rejects_reviewed_scheme(monkeypatch, tmp_path):
    plan = eligible_plan()
    monkeypatch.setattr(loop, "export_dataset", lambda *a, **k: {"rows": plan["rows"]})

    def forbidden(*a, **k):
        pytest.fail("reviewed rows must not reach writes or model loading")

    monkeypatch.setattr(loop, "write_export", forbidden)
    monkeypatch.setattr(loop, "_require_local_model", forbidden)
    with pytest.raises(ValueError, match="occurrence-aware"):
        loop.run_loop(tmp_path, tmp_path)


def test_occurrence_ids_and_pinned_indices_survive_collate():
    plan = eligible_plan()
    rows = select_split_rows(plan, "train")
    batch = collate_reviewed_batch(
        rows, families=plan["families"], vocabularies=plan["train_only_vocabularies"]
    )
    assert batch["occurrence_ids"] == [["o00", "o01"]]
    assert batch["token_indices"] == [[[1], [2]]]
    assert batch["filler_known"] == [[True, True]]
    assert all(tid > 0 for tid in batch["filler_target_ids"][0])


def test_unknown_ids_do_not_false_exact_match():
    assert structure_exact_match([0, 0], [0, 0], [False, False]) is False
    assert structure_exact_match([1, 2], [1, 2], [True, True]) is True
    assert structure_exact_match([1, 2], [1, 9], [True, True]) is False


def test_gold_span_diagnostic_is_not_bound_recovery():
    gold = [{"occurrence_id": "o1", "start": 0, "end": 4, "text": "same"}]
    pred = [{"occurrence_id": "o1", "start": 0, "end": 4, "text": "same"}]
    diag = gold_span_diagnostics(gold, pred)
    assert diag["kind"] == "gold_span_diagnostic"
    assert diag["not"] == "bound_vector_recovery"
    assert diag["n_span_exact"] == 1


def test_rejects_train_eval_fallback_and_blocked_plan(tmp_path):
    plan = eligible_plan()
    blocked = copy.deepcopy(plan)
    blocked["blockers"] = ["SYNTHETIC_BLOCK"]
    with pytest.raises(ValueError, match="blocked"):
        assert_plan_eligible(blocked)
    train_only = copy.deepcopy(plan)
    train_only["rows"] = [row for row in plan["rows"] if row["split"] == "train"]
    with pytest.raises(ValueError, match="train-set evaluation fallback"):
        run_reviewed_train(train_only, out_dir=tmp_path / "no-eval", seed=1, max_steps=1)
    with pytest.raises(ValueError, match="forbidden"):
        run_reviewed_train(plan, out_dir=tmp_path / "train-eval", seed=1, max_steps=1, eval_split="train")


def test_uninterrupted_vs_resumed_weights_equal():
    plan = eligible_plan()
    with tempfile.TemporaryDirectory() as tmp:
        result = compare_uninterrupted_vs_resumed(
            plan,
            out_root=tmp,
            seed=11,
            max_steps=6,
            interrupt_at=3,
            batch_size=1,
            scheduler_step_size=10,
        )
        assert result["weights_equal"] is True
        assert result["full_metrics"]["train_eval_fallback"] is False
        assert Path(result["uninterrupted_checkpoint"]).is_file()
        assert Path(result["resumed_checkpoint"]).is_file()


def test_consumption_receipt_and_no_name_gate(tmp_path):
    plan = eligible_plan()
    out = run_reviewed_train(plan, out_dir=tmp_path / "run", seed=3, max_steps=4, batch_size=1)
    receipt = out["receipt"]
    assert receipt["status"] == "RAN_REVIEWED_TRAINER"
    assert receipt["name_gate"] is False
    assert receipt["training_ready_claim"] is False
    assert receipt["legacy_loop_guard_preserved"] is True
    assert receipt["train_eval_fallback"] is False
    assert receipt["dataset_sha256"] == plan["dataset_sha256"]
    assert receipt["rows_sha256"] == plan["rows_sha256"]
    assert receipt["n_train_rows_available"] == 1
    assert receipt["n_eval_rows"] == 1


def test_pinned_indices_required_no_first_occurrence_fallback():
    plan = eligible_plan()
    row = copy.deepcopy(select_split_rows(plan, "train")[0])
    assert_pinned_token_indices(row)
    row["aligned_occurrences"][0]["token_indices"] = []
    with pytest.raises(ValueError, match="pinned token_indices"):
        assert_pinned_token_indices(row)
    del row["aligned_occurrences"]
    with pytest.raises(ValueError, match="aligned_occurrences"):
        assert_pinned_token_indices(row)


def test_selected_example_ids_match_actual_consumption(tmp_path):
    plan = eligible_plan()
    selected = selected_train_example_ids(plan)
    out = run_reviewed_train(plan, out_dir=tmp_path / "consume", seed=5, max_steps=5, batch_size=1)
    receipt = out["receipt"]
    assert receipt["selected_train_example_ids"] == selected
    assert set(receipt["consumed_example_ids"]) <= set(selected)
    assert receipt["consumption_audit"]["all_consumed_in_selected"] is True
    # Injecting an alien id must fail the audit helper.
    with pytest.raises(ValueError, match="not in selected"):
        assert_consumption_matches_selection(selected, receipt["consumed_example_ids"] + ["alien"])


def test_receipt_records_identities_and_refuses_best_overwrite(tmp_path):
    plan = eligible_plan()
    out = run_reviewed_train(plan, out_dir=tmp_path / "ident", seed=9, max_steps=3, batch_size=1)
    receipt = out["receipt"]
    identity = receipt["runtime_identity"]
    assert identity["recipe"]["seed"] == 9
    assert identity["recipe"]["max_steps"] == 3
    assert receipt["tokenizer_revision"] == plan["tokenizer_revision"]
    assert receipt["dataset_sha256"] == plan["dataset_sha256"]
    assert receipt["best_overwrite"] is False
    assert receipt["split_protocol"]["selected_example_ids"] == plan["selected_example_ids"]
