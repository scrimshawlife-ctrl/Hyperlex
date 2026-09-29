"""SELECT-005 completion: seal the control recipe, do not invent floors or a corpus."""

import ast
from pathlib import Path

import pytest

from hyperlexical.select_005_completion import (
    BEST_NAME,
    EXHAUSTED_STREAM_RUN,
    PREREGISTRATION_SEALED,
    THRESHOLDS_BLOCKED,
    TRANSITION,
    WARM_START_NAME,
    completion_report,
    decision_only_exclusion,
    exposure_snapshot_refusal,
    fresh_census,
    initialization_decision,
    label_blind_surface,
    sealed_preregistration,
    source_contract,
    threshold_authorization_proposal,
)
from hyperlexical.select_005_reserve import canonical_json

MODULE = Path(__file__).resolve().parents[2] / "scripts/shadow/hyperlexical/select_005_completion.py"


def test_initialization_is_morph65_not_the_current_best():
    decision = initialization_decision()
    assert decision["decision"] == "morph65_new_schedule"
    assert decision["rejected_alternative"] == "select004_best_new_schedule"
    assert decision["warm_start_name"] == WARM_START_NAME
    assert decision["best_name"] == BEST_NAME
    assert decision["best_not_moved"] is True
    assert decision["trainer_default_did_not_decide"] is True


def test_preregistration_seals_the_control_recipe_without_select_004_inheritance():
    sealed = sealed_preregistration()
    assert sealed["state"] == PREREGISTRATION_SEALED
    assert sealed["sealed"] is True
    assert sealed["unset_fields"] == []
    assert sealed["scientific_variable"] == "train_schedule"
    held = sealed["held_constant"]
    assert held["learning_rate"] == "2e-5"
    assert held["batch_size"] == 8
    assert held["gradient_accumulation"] == 1
    assert held["seed"] is None
    assert held["seed_policy"] == "HLX_SEED_UNSET_FROZEN"
    authority = sealed["held_constant_authority"]
    assert authority["inherited_from_select_004"] is False
    assert authority["trainer_default_did_not_decide"] is True
    assert authority["same_numeric_optimizer_values_as_select_004_candidate_env"] is True
    assert authority["select_004_scientific_variable_not_transferred"] == "HLX_SELECT_METRIC"
    assert sealed["initialization"]["decision"] == "morph65_new_schedule"
    assert sealed["training_authorized"] is False
    assert sealed["training_launch_authorized"] is False


def test_threshold_proposal_stays_unsealed():
    proposal = threshold_authorization_proposal()
    assert proposal["sealed"] is False
    assert proposal["state"] == THRESHOLDS_BLOCKED
    assert proposal["decision_thresholds"] == {}
    assert proposal["inherited_from_select_004"] is False
    assert proposal["comparison_baseline"] == "SELECT-005 control arm"
    assert proposal["not_seed_morph78"] is True
    assert all(item["numeric_threshold"] is None for item in proposal["metrics"])
    assert [item["metric"] for item in proposal["metrics"]] == [
        "classify_macro_f1_nonnone",
        "classification_accuracy",
        "observed_label_accuracy",
        "unbind_clean_exact",
    ]


def test_exhausted_stream_is_not_a_source_and_a_decision_only_row_has_no_slice():
    contract = source_contract()
    assert contract["exhausted_stream_is_a_source"] is False
    assert contract["wordnet"]["census_rights_token"] == "not CC-BY-SA"
    assert contract["wordnet"]["admitted_alone"] is False
    with pytest.raises(SystemExit, match="exhausted settlement universe"):
        fresh_census(
            [
                {
                    "decision": "ACCEPT",
                    "exhausted_universe": True,
                    "provenance": "old",
                    "rights": "CC-BY-SA",
                    "row_id": "old",
                    "source_run": EXHAUSTED_STREAM_RUN,
                    "text_hash": "ab" * 32,
                }
            ],
            {},
            set(),
        )
    event = {
        "decision": "ACCEPT",
        "provenance": "fresh",
        "rights": "CC-BY-SA",
        "row_id": "new",
        "source_run": "hs-new",
        "text_hash": "cd" * 32,
    }
    assert decision_only_exclusion(event) == "SLICE_LABELS_ABSENT"
    censused = fresh_census([event], {}, set())
    assert censused["failure"] == "RESERVE_QUOTA_UNFILLED"
    assert censused["reserve_row_count"] == 0
    assert censused["exhausted_universe_consulted"] is False
    assert censused["source_universe_count"] == 1


def test_stale_snapshot_refuses_and_the_empty_surface_is_label_blind():
    refusal = exposure_snapshot_refusal({"vern": 71.7, "boxhash": 71.7})
    assert refusal is not None
    assert "71.7h" in refusal
    assert exposure_snapshot_refusal({"vern": 1.0, "boxhash": 1.0}) is None
    assert exposure_snapshot_refusal({}) == "REFUSE: no box exposure snapshot"
    kept = label_blind_surface(
        [
            {
                "license": "CC BY-SA 3.0",
                "row_id": "hs-fresh-example",
                "source_type": "wiktionary_category",
                "source_url": "https://en.wiktionary.org/wiki/Example",
                "text_hash": "ef" * 32,
            }
        ]
    )
    assert kept == [
        {
            "license": "CC BY-SA 3.0",
            "row_id": "hs-fresh-example",
            "source_type": "wiktionary_category",
            "source_url": "https://en.wiktionary.org/wiki/Example",
            "text_hash": "ef" * 32,
        }
    ]
    with pytest.raises(SystemExit, match="label-blind surface carries task"):
        label_blind_surface(
            [
                {
                    "license": "CC-BY-SA",
                    "row_id": "labeled",
                    "source_type": "wikipedia_prose",
                    "source_url": "https://en.wikipedia.org/wiki/Example",
                    "task": "classify",
                    "text_hash": "11" * 32,
                }
            ]
        )
    with pytest.raises(SystemExit, match="not rights-cleared"):
        label_blind_surface(
            [
                {
                    "license": "MIT-examples",
                    "row_id": "mit",
                    "source_type": "mit_examples",
                    "source_url": "local",
                    "text_hash": "22" * 32,
                }
            ]
        )


def test_completion_report_is_stable_and_does_not_authorize_training():
    ages = {"boxhash": 71.7, "vern": 72.0}
    first = canonical_json(completion_report(ages))
    second = canonical_json(completion_report(ages))
    assert first == second
    report = completion_report(ages)
    assert report["transition"] == TRANSITION
    assert report["rows_acquired"] == 0
    assert report["settlements_appended"] == 0
    assert report["admission_receipt"] is None
    assert report["reserve_manifest_created"] is False
    assert report["preregistration_state"] == PREREGISTRATION_SEALED
    assert report["threshold_state"] == THRESHOLDS_BLOCKED
    assert report["training_authorized"] is False
    assert report["training_launch_authorized"] is False
    assert report["exhausted_universe_consulted"] is False
    assert report["label_blind_surface_count"] == 0
    assert report["isolation"] == "NOT_RUN_NO_ROWS"
    assert report["provenance"] == "NO_ADMITTED_ROWS"


def test_module_does_not_commit_or_touch_the_residual_lane():
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert not any("residual" in name for name in imported)
    assert "commit_settlement" not in source
    assert "persist_append" not in source
    assert "torch" not in imported
