"""Spec 007 data/recipe shape PR #2: scheme-split unbind curriculum.

Morph1 OBSERVED val dump (seed-morph1, not SoT gold): unbind_exact 0.321
(115/358); positional 185 / 135 fail; type_slot 173 / 108 fail. Curriculum
order is positional → type_slot → joint because positional_head_filler_miss
dominates. INFERRED cap and status-vocab denylist stay default-off.
"""

from pathlib import Path
import json
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.export import export_dataset
from hyperlexical.loop import prepare_unbind_splits
from hyperlexical.unbind_curriculum import (
    MORPH1_STATUS_VOCAB_DISTRACTORS,
    MORPH1_VAL_HIT,
    MORPH1_VAL_N,
    MORPH1_VAL_POSITIONAL_FAIL,
    MORPH1_VAL_POSITIONAL_N,
    MORPH1_VAL_TYPE_SLOT_FAIL,
    MORPH1_VAL_TYPE_SLOT_N,
    MORPH1_VAL_UNBIND_EXACT,
    PHASE_JOINT,
    PHASE_POSITIONAL,
    PHASE_TYPE_SLOT,
    UNBIND_CURRICULUM_DEFAULT,
    UNBIND_CURRICULUM_POS_EPOCHS_DEFAULT,
    UNBIND_CURRICULUM_TYPE_EPOCHS_DEFAULT,
    filter_rows_for_phase,
    phase_name_for_epoch,
    plan_unbind_curriculum,
    resolve_curriculum_schedule,
    resolve_unbind_curriculum,
    resolve_unbind_curriculum_pos_epochs,
    resolve_unbind_curriculum_type_epochs,
    select_unbind_for_epoch,
)
from hyperlexical.unbind_recipe import (
    UNBIND_INFERRED_CAP_DEFAULT,
    distractor_fillers_for,
    hard_negatives_for,
    resolve_filler_denylist,
    resolve_unbind_inferred_cap,
    shape_unbind_train,
)


def _unbind_row(
    text,
    fillers,
    *,
    cls="OBSERVED",
    split="train",
    scheme="positional",
    roles=None,
    lineage="brainrot-aura",
):
    fills = list(fillers)
    if roles is not None:
        role_list = list(roles)
    elif scheme == "type_slot":
        role_list = ["TOKEN", "SLOT", "MARKER"][: len(fills)]
        while len(role_list) < len(fills):
            role_list.append("TOKEN")
    else:
        role_list = [f"pos_{i}" for i in range(len(fills))]
    return {
        "text": text,
        "split": split,
        "lineage": lineage,
        "typology": ["compression"],
        "stage": "circulating",
        "roles": role_list,
        "fillers": fills,
        "role_scheme": scheme,
        "task": "unbind",
        "provenance": "test:unbind",
        "class": cls,
        "license": "MIT-examples",
    }


def _mixed_rows():
    return [
        _unbind_row("pos obs", ["aped"], cls="OBSERVED", scheme="positional"),
        _unbind_row("pos inf", ["aura"], cls="INFERRED", scheme="positional"),
        _unbind_row("TOKEN:rizz SLOT:tax", ["rizz", "tax"], cls="OBSERVED", scheme="type_slot"),
        _unbind_row("TOKEN:yap", ["yap"], cls="INFERRED", scheme="type_slot"),
    ]


def test_curriculum_default_off_is_identity(monkeypatch):
    monkeypatch.delenv("HYPERLEX_UNBIND_CURRICULUM", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_CURRICULUM_POS_EPOCHS", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_CURRICULUM_TYPE_EPOCHS", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_OBSERVED_UPSAMPLE", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_INFERRED_CAP", raising=False)
    assert UNBIND_CURRICULUM_DEFAULT == 0
    assert resolve_unbind_curriculum() is False
    assert resolve_unbind_curriculum("") is False
    sched = resolve_curriculum_schedule()
    assert sched == {"enabled": False, "pos_epochs": 0, "type_epochs": 0}
    rows = _mixed_rows()
    shaped, _stats = shape_unbind_train(rows)
    for ep in range(4):
        selected, meta = select_unbind_for_epoch(shaped, ep, sched)
        assert [r["text"] for r in selected] == [r["text"] for r in shaped]
        assert meta["phase"] == PHASE_JOINT
        assert meta["n_rows"] == len(shaped)
        assert meta["fallback_full_mix"] is False
    plan = plan_unbind_curriculum(shaped, 3, sched)
    assert plan["enabled"] is False
    assert plan["phases"] == [
        {
            "name": PHASE_JOINT,
            "start_epoch": 0,
            "end_epoch": 3,
            "n_rows": len(shaped),
            "fallback_full_mix": False,
        }
    ]


def test_resolve_curriculum_0_1_only(monkeypatch):
    monkeypatch.setenv("HYPERLEX_UNBIND_CURRICULUM", "1")
    assert resolve_unbind_curriculum() is True
    assert resolve_unbind_curriculum(0) is False
    assert resolve_unbind_curriculum(1) is True
    monkeypatch.setenv("HYPERLEX_UNBIND_CURRICULUM", "true")
    with pytest.raises(ValueError, match="0 or 1"):
        resolve_unbind_curriculum()
    monkeypatch.setenv("HYPERLEX_UNBIND_CURRICULUM", "2")
    with pytest.raises(ValueError, match="0 or 1"):
        resolve_unbind_curriculum()


def test_resolve_phase_epoch_lengths(monkeypatch):
    monkeypatch.delenv("HYPERLEX_UNBIND_CURRICULUM_POS_EPOCHS", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_CURRICULUM_TYPE_EPOCHS", raising=False)
    assert resolve_unbind_curriculum_pos_epochs() == 1
    assert resolve_unbind_curriculum_type_epochs() == 1
    monkeypatch.setenv("HYPERLEX_UNBIND_CURRICULUM_POS_EPOCHS", "2")
    monkeypatch.setenv("HYPERLEX_UNBIND_CURRICULUM_TYPE_EPOCHS", "0")
    assert resolve_unbind_curriculum_pos_epochs() == 2
    assert resolve_unbind_curriculum_type_epochs() == 0
    monkeypatch.setenv("HYPERLEX_UNBIND_CURRICULUM_POS_EPOCHS", "-1")
    with pytest.raises(ValueError, match="int >= 0"):
        resolve_unbind_curriculum_pos_epochs()
    monkeypatch.setenv("HYPERLEX_UNBIND_CURRICULUM_TYPE_EPOCHS", "nope")
    with pytest.raises(ValueError, match="int >= 0"):
        resolve_unbind_curriculum_type_epochs()


def test_phase_selection_positional_then_type_slot_then_joint(monkeypatch):
    monkeypatch.setenv("HYPERLEX_UNBIND_CURRICULUM", "1")
    monkeypatch.setenv("HYPERLEX_UNBIND_CURRICULUM_POS_EPOCHS", "1")
    monkeypatch.setenv("HYPERLEX_UNBIND_CURRICULUM_TYPE_EPOCHS", "1")
    sched = resolve_curriculum_schedule()
    rows = _mixed_rows()
    assert phase_name_for_epoch(0, sched) == PHASE_POSITIONAL
    assert phase_name_for_epoch(1, sched) == PHASE_TYPE_SLOT
    assert phase_name_for_epoch(2, sched) == PHASE_JOINT
    pos, pos_meta = select_unbind_for_epoch(rows, 0, sched)
    typ, typ_meta = select_unbind_for_epoch(rows, 1, sched)
    joint, joint_meta = select_unbind_for_epoch(rows, 2, sched)
    assert [r["role_scheme"] for r in pos] == ["positional", "positional"]
    assert [r["text"] for r in pos] == ["pos obs", "pos inf"]
    assert pos_meta == {"phase": PHASE_POSITIONAL, "n_rows": 2, "fallback_full_mix": False}
    assert [r["role_scheme"] for r in typ] == ["type_slot", "type_slot"]
    assert all("TOKEN:" in r["text"] or r["role_scheme"] == "type_slot" for r in typ)
    assert typ_meta["n_rows"] == 2
    assert [r["text"] for r in joint] == [r["text"] for r in rows]
    assert joint_meta["phase"] == PHASE_JOINT
    plan = plan_unbind_curriculum(rows, 4, sched)
    assert [p["name"] for p in plan["phases"]] == [
        PHASE_POSITIONAL,
        PHASE_TYPE_SLOT,
        PHASE_JOINT,
    ]
    assert plan["phases"][0]["start_epoch"] == 0
    assert plan["phases"][0]["end_epoch"] == 1
    assert plan["phases"][1]["start_epoch"] == 1
    assert plan["phases"][1]["end_epoch"] == 2
    assert plan["phases"][2]["start_epoch"] == 2
    assert plan["phases"][2]["end_epoch"] == 4
    assert plan["phases"][0]["n_rows"] == 2
    assert plan["phases"][1]["n_rows"] == 2
    assert plan["phases"][2]["n_rows"] == 4
    assert plan["n_unbind_positional"] == 2
    assert plan["n_unbind_type_slot"] == 2
    assert plan["n_unbind_joint"] == 4


def test_curriculum_composes_with_shape_unbind_train(monkeypatch):
    monkeypatch.setenv("HYPERLEX_UNBIND_CURRICULUM", "1")
    monkeypatch.setenv("HYPERLEX_UNBIND_CURRICULUM_POS_EPOCHS", "1")
    monkeypatch.setenv("HYPERLEX_UNBIND_CURRICULUM_TYPE_EPOCHS", "1")
    monkeypatch.setenv("HYPERLEX_UNBIND_OBSERVED_UPSAMPLE", "2")
    monkeypatch.delenv("HYPERLEX_UNBIND_INFERRED_CAP", raising=False)
    rows = _mixed_rows()
    shaped, stats = shape_unbind_train(rows)
    assert stats["unbind_observed_upsample"] == 2
    # OBSERVED copies first (pos obs + type_slot obs), then INFERRED.
    assert [r["text"] for r in shaped].count("pos obs") == 2
    assert [r["text"] for r in shaped].count("TOKEN:rizz SLOT:tax") == 2
    sched = resolve_curriculum_schedule()
    pos, _ = select_unbind_for_epoch(shaped, 0, sched)
    typ, _ = select_unbind_for_epoch(shaped, 1, sched)
    assert all(r["role_scheme"] != "type_slot" for r in pos)
    assert [r["text"] for r in pos].count("pos obs") == 2
    assert all(r["role_scheme"] == "type_slot" for r in typ)
    assert [r["text"] for r in typ].count("TOKEN:rizz SLOT:tax") == 2


def test_empty_type_slot_phase_falls_back_to_full_mix(monkeypatch):
    monkeypatch.setenv("HYPERLEX_UNBIND_CURRICULUM", "1")
    rows = [
        _unbind_row("only pos", ["aped"], scheme="positional"),
        _unbind_row("also pos", ["aura"], scheme="positional"),
    ]
    sched = {"enabled": True, "pos_epochs": 1, "type_epochs": 1}
    selected, meta = select_unbind_for_epoch(rows, 1, sched)
    assert meta["phase"] == PHASE_TYPE_SLOT
    assert meta["fallback_full_mix"] is True
    assert [r["text"] for r in selected] == ["only pos", "also pos"]
    plan = plan_unbind_curriculum(rows, 3, sched)
    type_phase = next(p for p in plan["phases"] if p["name"] == PHASE_TYPE_SLOT)
    assert type_phase["fallback_full_mix"] is True
    assert type_phase["n_rows"] == 2


def test_curriculum_does_not_touch_classify_or_val(monkeypatch):
    monkeypatch.setenv("HYPERLEX_UNBIND_CURRICULUM", "1")
    monkeypatch.setenv("HYPERLEX_UNBIND_OBSERVED_UPSAMPLE", "2")
    rows = [
        _unbind_row("train pos", ["aped"], split="train", scheme="positional"),
        _unbind_row("TOKEN:train", ["rizz"], split="train", scheme="type_slot"),
        _unbind_row("val pos", ["aura"], split="val", scheme="positional"),
        {
            "text": "classify me",
            "split": "train",
            "task": "classify",
            "class": "INFERRED",
            "lineage": "brainrot-aura",
            "fillers": [],
            "roles": [],
            "role_scheme": None,
        },
    ]
    train, val, _stats = prepare_unbind_splits(rows)
    assert [r["text"] for r in val] == ["val pos"]
    assert all(r["task"] == "unbind" for r in train)
    assert "classify me" not in [r["text"] for r in train]
    sched = resolve_curriculum_schedule()
    pos, _ = select_unbind_for_epoch(train, 0, sched)
    assert all(r.get("task") == "unbind" for r in pos)
    assert all(r["role_scheme"] == "positional" for r in pos)


def test_morph1_dump_justifies_positional_first_then_type_slot_then_joint():
    """OBSERVED Morph1 counts only. Does not mint SoT gold."""
    assert MORPH1_VAL_HIT / MORPH1_VAL_N == pytest.approx(MORPH1_VAL_UNBIND_EXACT, abs=0.001)
    assert MORPH1_VAL_POSITIONAL_N + MORPH1_VAL_TYPE_SLOT_N == MORPH1_VAL_N
    assert MORPH1_VAL_POSITIONAL_FAIL + MORPH1_VAL_TYPE_SLOT_FAIL == MORPH1_VAL_N - MORPH1_VAL_HIT
    assert MORPH1_VAL_POSITIONAL_FAIL / MORPH1_VAL_POSITIONAL_N > (
        MORPH1_VAL_TYPE_SLOT_FAIL / MORPH1_VAL_TYPE_SLOT_N
    )
    # Defaults stay 1/1 so a 2-epoch smoke still reaches type_slot.
    assert UNBIND_CURRICULUM_POS_EPOCHS_DEFAULT == 1
    assert UNBIND_CURRICULUM_TYPE_EPOCHS_DEFAULT == 1
    # Longer Spark card: more early positional, then type_slot, then joint.
    sched = {"enabled": True, "pos_epochs": 2, "type_epochs": 1}
    assert [phase_name_for_epoch(i, sched) for i in range(4)] == [
        PHASE_POSITIONAL,
        PHASE_POSITIONAL,
        PHASE_TYPE_SLOT,
        PHASE_JOINT,
    ]


def test_inferred_cap_stays_default_off(monkeypatch):
    """Morph1 INFERRED type_slot proper-noun noise is operator-opt-in, not default."""
    monkeypatch.delenv("HYPERLEX_UNBIND_INFERRED_CAP", raising=False)
    assert UNBIND_INFERRED_CAP_DEFAULT == 0
    assert resolve_unbind_inferred_cap() == 0


def test_residual_morph_bleed_pairs_only_when_both_exist():
    """Morph1 residual bleed. Missing sibling is not invented."""
    assert set(hard_negatives_for("looksmaxxed", {"looksmaxxed", "looksmaxxing"})) == {
        "looksmaxxing"
    }
    assert set(hard_negatives_for("looksmaxxing", {"looksmaxxed", "looksmaxxing"})) == {
        "looksmaxxed"
    }
    assert set(hard_negatives_for("rizz", {"rizz", "rizzless"})) == {"rizzless"}
    assert set(hard_negatives_for("rizzless", {"rizz", "rizzless"})) == {"rizz"}
    assert hard_negatives_for("rizz", {"rizz"}) == []
    assert hard_negatives_for("rizzless", {"rizzless"}) == []


def test_status_vocab_denylist_is_operator_opt_in(monkeypatch):
    """Morph1 bum/bolt/burn/mid bleed. Empty default. Distractors only."""
    monkeypatch.delenv("HYPERLEX_UNBIND_FILLER_DENYLIST", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_FILLER_DENYLIST_PATH", raising=False)
    assert resolve_filler_denylist() == {}
    assert MORPH1_STATUS_VOCAB_DISTRACTORS == ("bum", "bolt", "burn", "mid")
    deny = resolve_filler_denylist(
        {"brainrot-aura": list(MORPH1_STATUS_VOCAB_DISTRACTORS)}
    )
    assert deny["brainrot-aura"] == frozenset(MORPH1_STATUS_VOCAB_DISTRACTORS)
    known = {"aped", "aping", *MORPH1_STATUS_VOCAB_DISTRACTORS}
    negs = distractor_fillers_for(
        "aped", known, lineage="brainrot-aura", denylist=deny
    )
    assert negs == ["aping"]
    assert not set(MORPH1_STATUS_VOCAB_DISTRACTORS) & set(negs)


def test_filter_rejects_unknown_phase():
    with pytest.raises(ValueError, match="unknown unbind curriculum phase"):
        filter_rows_for_phase([], "semantic")


def test_filler_denylist_default_empty_identity(monkeypatch):
    monkeypatch.delenv("HYPERLEX_UNBIND_FILLER_DENYLIST", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_FILLER_DENYLIST_PATH", raising=False)
    assert resolve_filler_denylist() == {}
    assert resolve_filler_denylist("") == {}
    known = {"aped", "aping"}
    assert distractor_fillers_for("aped", known) == ["aping"]
    rows = [
        _unbind_row("they aped in", ["aped"]),
        _unbind_row("still aping", ["aping"]),
    ]
    shaped, stats = shape_unbind_train(rows)
    assert stats["unbind_filler_denylist_lineages"] == 0
    by_text = {r["text"]: r for r in shaped}
    assert "aping" in by_text["they aped in"]["hard_neg_fillers"]


def test_filler_denylist_filters_hard_neg_not_gold(monkeypatch, tmp_path):
    monkeypatch.delenv("HYPERLEX_UNBIND_FILLER_DENYLIST_PATH", raising=False)
    monkeypatch.setenv(
        "HYPERLEX_UNBIND_FILLER_DENYLIST",
        json.dumps({"brainrot-aura": ["aping"]}),
    )
    deny = resolve_filler_denylist()
    assert deny == {"brainrot-aura": frozenset({"aping"})}
    known = {"aped", "aping"}
    assert distractor_fillers_for(
        "aped", known, lineage="brainrot-aura", denylist=deny
    ) == []
    # other lineage unchanged; missing sibling is not invented
    assert distractor_fillers_for(
        "aped", known, lineage="gaming-meta", denylist=deny
    ) == ["aping"]
    assert "looksmaxxing" not in distractor_fillers_for(
        "aped", known, lineage="brainrot-aura", denylist={"brainrot-aura": ["looksmaxxing"]}
    )
    rows = [
        _unbind_row("they aped in", ["aped"], lineage="brainrot-aura"),
        _unbind_row("still aping", ["aping"], lineage="brainrot-aura"),
    ]
    shaped, stats = shape_unbind_train(rows)
    assert stats["unbind_filler_denylist_lineages"] == 1
    by_text = {r["text"]: r for r in shaped}
    assert by_text["they aped in"]["fillers"] == ["aped"]
    assert "aping" not in by_text["they aped in"]["hard_neg_fillers"]
    assert by_text["still aping"]["fillers"] == ["aping"]

    path = tmp_path / "deny.json"
    path.write_text(json.dumps({"gaming-meta": ["aped"]}), encoding="utf-8")
    monkeypatch.delenv("HYPERLEX_UNBIND_FILLER_DENYLIST", raising=False)
    monkeypatch.setenv("HYPERLEX_UNBIND_FILLER_DENYLIST_PATH", str(path))
    from_path = resolve_filler_denylist()
    assert from_path == {"gaming-meta": frozenset({"aped"})}


def test_filler_denylist_fail_closed(monkeypatch, tmp_path):
    monkeypatch.setenv("HYPERLEX_UNBIND_FILLER_DENYLIST", "not-json")
    with pytest.raises(ValueError, match="JSON object"):
        resolve_filler_denylist()
    monkeypatch.setenv("HYPERLEX_UNBIND_FILLER_DENYLIST", json.dumps(["aped"]))
    with pytest.raises(ValueError, match="JSON object"):
        resolve_filler_denylist()
    monkeypatch.setenv("HYPERLEX_UNBIND_FILLER_DENYLIST", json.dumps({"brainrot-aura": "aping"}))
    with pytest.raises(ValueError, match="list of surfaces"):
        resolve_filler_denylist()
    monkeypatch.delenv("HYPERLEX_UNBIND_FILLER_DENYLIST", raising=False)
    monkeypatch.setenv("HYPERLEX_UNBIND_FILLER_DENYLIST_PATH", str(tmp_path / "missing.json"))
    with pytest.raises(ValueError, match="is not a file"):
        resolve_filler_denylist()


def test_export_counts_curriculum_default_off(monkeypatch):
    monkeypatch.delenv("HYPERLEX_UNBIND_CURRICULUM", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_FILLER_DENYLIST", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_FILLER_DENYLIST_PATH", raising=False)
    bundle = export_dataset(ROOT)
    c = bundle["counts"]
    assert c["unbind_curriculum"] == 0
    assert c["unbind_curriculum_pos_epochs"] == 0
    assert c["unbind_curriculum_type_epochs"] == 0
    assert c["unbind_filler_denylist_lineages"] == 0
    assert c["name_gate"] is False
    unbind = [r for r in bundle["rows"] if r["task"] == "unbind"]
    assert all("hard_neg_fillers" not in r for r in unbind)
    assert {r["role_scheme"] for r in unbind} <= {"positional", "type_slot", None}
