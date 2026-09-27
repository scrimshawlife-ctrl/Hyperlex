"""Admission contract: one train_schedule variable, active reserve only."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from admission_fixtures import arm_controlled, classify_row, sha256_bytes  # noqa: E402
from hyperlexical.admission import (  # noqa: E402
    AdmissionError,
    admit_training_run,
    schedule_bundle,
)
from hyperlexical.holdout_guard import normalized_text_sha256  # noqa: E402
from hyperlexical.identity_ledger import IdentityLedger, derived_state  # noqa: E402
from hyperlexical.loop import _EARLY_STOP_OFF, _EARLY_STOP_ON  # noqa: E402
from hyperlexical.selection_surface import row_id  # noqa: E402

EXPERIMENT = "HLX-EXP-TEST"
OTHER = "HLX-EXP-OTHER"
SELECT = "classify_macro_f1_nonnone"
CONTROL_SCHEDULE = {
    "HYPERLEX_TRAIN_EPOCHS": "40",
    "HYPERLEX_EARLY_STOP": "0",
}
CANDIDATE_SCHEDULE = {
    "HYPERLEX_TRAIN_EPOCHS": "12",
    "HYPERLEX_EARLY_STOP": "1",
    "HYPERLEX_EARLY_STOP_PATIENCE": "4",
    "HYPERLEX_EARLY_STOP_MIN_EPOCHS": "4",
}


def _admit():
    return admit_training_run(
        trunk=Path(__import__("os").environ["HYPERLEX_TRUNK_DIR"]),
        out_dir=Path(__import__("os").environ["HYPERLEX_TRAIN_OUT"]),
    )


def _write_envs(tmp_path: Path, baseline: dict, candidate: dict) -> None:
    (tmp_path / "baseline-env.json").write_text(
        json.dumps(baseline, sort_keys=True), encoding="utf-8"
    )
    (tmp_path / "candidate-env.json").write_text(
        json.dumps(candidate, sort_keys=True), encoding="utf-8"
    )


def _arm_schedule(
    monkeypatch,
    tmp_path: Path,
    *,
    declared: str | None,
    baseline_extra: dict | None = None,
    candidate_extra: dict | None = None,
    metric: str = SELECT,
    baseline_metric: str | None = None,
    train_text: str = "train row",
):
    armed = arm_controlled(monkeypatch, tmp_path, [classify_row(train_text)])
    baseline = {
        "HYPERLEX_FILLER_FILTER": "off",
        "HLX_SELECT_METRIC": metric if baseline_metric is None else baseline_metric,
    }
    candidate = {
        "HYPERLEX_FILLER_FILTER": "off",
        "HLX_SELECT_METRIC": metric,
        "HLX_EXPERIMENT_ID": EXPERIMENT,
        "HYPERLEX_TRAIN_OUT": str(armed["out"]),
    }
    baseline.update(CONTROL_SCHEDULE)
    candidate.update(CANDIDATE_SCHEDULE)
    if baseline_extra:
        baseline.update(baseline_extra)
    if candidate_extra:
        candidate.update(candidate_extra)
    if declared is not None:
        baseline["HLX_SCIENTIFIC_VARIABLE"] = declared
        candidate["HLX_SCIENTIFIC_VARIABLE"] = declared
        monkeypatch.setenv("HLX_SCIENTIFIC_VARIABLE", declared)
    else:
        monkeypatch.delenv("HLX_SCIENTIFIC_VARIABLE", raising=False)
    _write_envs(tmp_path, baseline, candidate)
    monkeypatch.setenv("HLX_SELECT_METRIC", metric)
    for key, value in candidate.items():
        if key in {
            "HLX_EXPERIMENT_ID",
            "HYPERLEX_TRAIN_OUT",
            "HLX_SCIENTIFIC_VARIABLE",
            "HLX_SELECT_METRIC",
        }:
            continue
        monkeypatch.setenv(key, value)
    return armed


def _ledger_bytes(directory: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted(directory.iterdir())}


def _bind(root: Path, ledger: IdentityLedger, experiment_id: str) -> Path:
    ledger_dir = root / "ledger"
    if ledger_dir.exists():
        raise AssertionError("ledger directory already exists")
    ledger.save(ledger_dir)
    events_sha = sha256_bytes((ledger_dir / "events.jsonl").read_bytes())
    active = ledger.active_reserve_records(experiment_id)
    binding = {
        "schema": "hyperlex.reserve_binding.v1",
        "experiment_id": experiment_id,
        "ledger_events_sha256": events_sha,
        "counts": ledger.active_reserve_counts(experiment_id),
        "identities": len(active),
        "lifecycle": "EVAL_RESERVE",
    }
    path = root / "reserve-binding.json"
    path.write_text(json.dumps(binding, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _observe_reserve(ledger: IdentityLedger, text: str, label: dict, experiment_id: str) -> str:
    digest = normalized_text_sha256(text)
    ledger.observe(
        digest,
        source_artifact="fixture",
        row_ids=[row_id({"text": text, "task": label["task"], "split": "val"})],
        labels=[label],
        provenance="fixture",
        experiment_id=experiment_id,
    )
    ledger.transition(digest, "EVAL_RESERVE", source_artifact="fixture", provenance="fixture")
    return digest


def _fresh_reserve(experiment_id: str) -> IdentityLedger:
    ledger = IdentityLedger()
    _observe_reserve(
        ledger,
        "reserve classify surface",
        {"task": "classify", "class": "OBSERVED", "lineage": "gaming-meta", "split": "val"},
        experiment_id,
    )
    _observe_reserve(
        ledger,
        "reserve unbind surface",
        {
            "task": "unbind",
            "class": "INFERRED",
            "lineage": "none",
            "split": "val",
            "unbind_clean": True,
        },
        experiment_id,
    )
    return ledger


def _spend(ledger: IdentityLedger, digest: str) -> None:
    ledger.transition(digest, "EVAL_BOUND", source_artifact="fixture", provenance="bind")
    ledger.transition(digest, "EVAL_SPENT", source_artifact="fixture", provenance="spend")


def test_schedule_tokens_match_the_trainer():
    from hyperlexical.admission import _SCHEDULE_OFF, _SCHEDULE_ON

    assert _SCHEDULE_OFF == _EARLY_STOP_OFF
    assert _SCHEDULE_ON == _EARLY_STOP_ON


def test_select005_schedule_bundle_is_one_variable(monkeypatch, tmp_path):
    armed = _arm_schedule(monkeypatch, tmp_path, declared="train_schedule")
    before = _ledger_bytes(armed["reserve"]["ledger"])
    base = json.loads((tmp_path / "baseline-env.json").read_text(encoding="utf-8"))
    cand = json.loads((tmp_path / "candidate-env.json").read_text(encoding="utf-8"))
    assert schedule_bundle(base) != schedule_bundle(cand)
    result = _admit()
    assert result.admission_result == "ADMISSION_PASS"
    assert result.status == "PREREGISTERED"
    assert result.receipt["optimizer_loaded"] is False
    assert result.receipt["epochs"] == 0
    assert result.receipt["gradient_steps"] == 0
    assert _ledger_bytes(armed["reserve"]["ledger"]) == before
    assert not armed["out"].exists()


def test_extra_scientific_difference_is_a_second_variable(monkeypatch, tmp_path):
    _arm_schedule(
        monkeypatch,
        tmp_path,
        declared="train_schedule",
        candidate_extra={"HYPERLEX_TRAIN_LR": "1e-4"},
    )
    with pytest.raises(AdmissionError, match="scientific variable count is 2") as exc:
        _admit()
    assert exc.value.receipt["failed_gate"] == "single_variable"
    message = str(exc.value)
    assert "train_schedule" in message
    assert "HYPERLEX_TRAIN_LR" in message


def test_selection_metric_difference_is_not_inside_train_schedule(monkeypatch, tmp_path):
    _arm_schedule(
        monkeypatch,
        tmp_path,
        declared="train_schedule",
        baseline_metric="unbind_exact",
    )
    with pytest.raises(AdmissionError, match="not part of train_schedule") as exc:
        _admit()
    assert exc.value.receipt["failed_gate"] == "single_variable"


def test_undeclared_schedule_difference_refuses_admission(monkeypatch, tmp_path):
    _arm_schedule(monkeypatch, tmp_path, declared=None)
    with pytest.raises(AdmissionError, match="undeclared schedule difference") as exc:
        _admit()
    assert exc.value.receipt["failed_gate"] == "single_variable"


def test_declared_select_metric_mode_still_passes(monkeypatch, tmp_path):
    armed = arm_controlled(monkeypatch, tmp_path, [classify_row("train row")])
    baseline = {"HYPERLEX_FILLER_FILTER": "off", "HLX_SCIENTIFIC_VARIABLE": "HLX_SELECT_METRIC"}
    candidate = {
        "HYPERLEX_FILLER_FILTER": "off",
        "HLX_SCIENTIFIC_VARIABLE": "HLX_SELECT_METRIC",
        "HLX_SELECT_METRIC": SELECT,
        "HLX_EXPERIMENT_ID": EXPERIMENT,
        "HYPERLEX_TRAIN_OUT": str(armed["out"]),
    }
    _write_envs(tmp_path, baseline, candidate)
    monkeypatch.setenv("HLX_SCIENTIFIC_VARIABLE", "HLX_SELECT_METRIC")
    result = _admit()
    assert result.admission_result == "ADMISSION_PASS"
    assert result.receipt["optimizer_loaded"] is False


def test_implicit_select_metric_mode_still_passes(monkeypatch, tmp_path):
    arm_controlled(monkeypatch, tmp_path, [classify_row("train row")])
    monkeypatch.delenv("HLX_SCIENTIFIC_VARIABLE", raising=False)
    result = _admit()
    assert result.admission_result == "ADMISSION_PASS"
    assert result.status == "PREREGISTERED"


def test_spent_only_ledger_has_zero_active_counts_and_keeps_the_flag(monkeypatch, tmp_path):
    ledger = _fresh_reserve(EXPERIMENT)
    for record in list(ledger.identities.values()):
        assert record["evaluation_reserved"] is True
        _spend(ledger, record["normalized_text_sha256"])
        assert record["evaluation_reserved"] is True
        assert derived_state(record) == "EVAL_SPENT"
    assert ledger.active_reserve_counts(EXPERIMENT) == {
        "classify": 0,
        "classify_observed": 0,
        "classify_non_none": 0,
        "unbind_clean": 0,
    }
    root = tmp_path / "spent"
    root.mkdir()
    binding = _bind(root, ledger, EXPERIMENT)
    arm_controlled(monkeypatch, tmp_path, [classify_row("train row")])
    monkeypatch.setenv("HLX_EVAL_RESERVE_LEDGER", str(root / "ledger"))
    monkeypatch.setenv("HLX_RESERVE_BINDING", str(binding))
    before = _ledger_bytes(root / "ledger")
    with pytest.raises(AdmissionError, match="missing active reserve") as exc:
        _admit()
    assert exc.value.receipt["failed_gate"] == "holdout_reserve"
    assert _ledger_bytes(root / "ledger") == before
    reloaded = IdentityLedger.load(root / "ledger")
    assert all(record["evaluation_reserved"] is True for record in reloaded.identities.values())
    assert reloaded.active_reserve_counts(EXPERIMENT)["classify"] == 0


def test_mixed_ledger_counts_only_active_identities(monkeypatch, tmp_path):
    ledger = _fresh_reserve(EXPERIMENT)
    spent = _observe_reserve(
        ledger,
        "already spent surface",
        {"task": "classify", "class": "OBSERVED", "lineage": "gaming-meta", "split": "val"},
        EXPERIMENT,
    )
    _spend(ledger, spent)
    assert ledger.identity(spent)["evaluation_reserved"] is True
    active_hashes = {record["normalized_text_sha256"] for record in ledger.active_reserve_records(EXPERIMENT)}
    assert spent not in active_hashes
    assert len(active_hashes) == 2
    counts = ledger.active_reserve_counts(EXPERIMENT)
    assert counts["classify"] == 1
    assert counts["unbind_clean"] == 1
    root = tmp_path / "mixed"
    root.mkdir()
    binding = _bind(root, ledger, EXPERIMENT)
    armed = _arm_schedule(monkeypatch, tmp_path, declared="train_schedule")
    monkeypatch.setenv("HLX_EVAL_RESERVE_LEDGER", str(root / "ledger"))
    monkeypatch.setenv("HLX_RESERVE_BINDING", str(binding))
    before = _ledger_bytes(root / "ledger")
    result = _admit()
    assert result.admission_result == "ADMISSION_PASS"
    assert result.receipt["reserve_counts"]["classify"] == 1
    assert _ledger_bytes(root / "ledger") == before
    assert not armed["out"].exists()


def test_wrong_experiment_active_reserve_refuses(monkeypatch, tmp_path):
    ledger = _fresh_reserve(OTHER)
    assert ledger.active_reserve_counts(EXPERIMENT) == {
        "classify": 0,
        "classify_observed": 0,
        "classify_non_none": 0,
        "unbind_clean": 0,
    }
    assert ledger.active_reserve_counts(OTHER)["classify"] == 1
    root = tmp_path / "foreign"
    root.mkdir()
    # Binding names the current experiment. The identities do not.
    binding = _bind(root, ledger, EXPERIMENT)
    arm_controlled(monkeypatch, tmp_path, [classify_row("train row")])
    monkeypatch.setenv("HLX_EVAL_RESERVE_LEDGER", str(root / "ledger"))
    monkeypatch.setenv("HLX_RESERVE_BINDING", str(binding))
    with pytest.raises(AdmissionError, match="bound to another experiment") as exc:
        _admit()
    assert exc.value.receipt["failed_gate"] == "holdout_reserve"


def test_active_reserve_overlap_still_fails(monkeypatch, tmp_path):
    arm_controlled(monkeypatch, tmp_path, [classify_row("reserve classify surface")])
    with pytest.raises(AdmissionError, match="overlaps the sealed reserve") as exc:
        _admit()
    assert exc.value.receipt["failed_gate"] == "train_reserve_disjointness"


def test_spent_identity_cannot_be_reallocated_or_reused():
    ledger = IdentityLedger()
    digest = _observe_reserve(
        ledger,
        "spent surface",
        {"task": "classify", "class": "OBSERVED", "lineage": "gaming-meta", "split": "val"},
        EXPERIMENT,
    )
    _spend(ledger, digest)
    record = ledger.identity(digest)
    assert record is not None
    assert record["evaluation_reserved"] is True
    assert derived_state(record) == "EVAL_SPENT"
    with pytest.raises(SystemExit, match="monotonic"):
        ledger.transition(digest, "EVAL_RESERVE", source_artifact="fixture", provenance="reuse")
    report = ledger.admit(
        [
            {
                "text": "spent surface",
                "task": "classify",
                "split": "val",
                "class": "OBSERVED",
                "lineage": "gaming-meta",
            }
        ],
        batch_id="reuse-attempt",
        source_artifact="fixture",
        targets={"classify": 1, "classify_observed": 1, "classify_non_none": 1, "unbind_clean": 1},
    )
    assert report["rejected_existing_identities"]["EVAL_SPENT"] == 1
    assert report["unique_admitted_to_eval_reserve"] == 0
    assert ledger.identity(digest)["evaluation_reserved"] is True
    assert derived_state(ledger.identity(digest)) == "EVAL_SPENT"
