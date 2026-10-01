"""CPU tests for V6 architecture-reset bake-off contracts."""

from __future__ import annotations

from hyperlexical.classification_v6_architecture_reset_bakeoff import (
    ADVANCEMENT_GATE,
    LABEL_DESCRIPTIONS,
    TRACKS,
    axis_floors_pass,
    bakeoff_contract,
    diagnose_exhaustion,
    frozen_label_descriptions,
    select_reset_candidate,
)
from hyperlexical.classification_v6_label_migration import (
    DOMAIN_VOCAB,
    FUNCTION_VOCAB,
    MEDIATION_VOCAB,
)


def test_frozen_label_descriptions_cover_vocab():
    defs = frozen_label_descriptions()
    for lab in DOMAIN_VOCAB + FUNCTION_VOCAB + MEDIATION_VOCAB:
        assert lab in defs
        assert "DOMAIN" in defs[lab] or "FUNCTION" in defs[lab] or "MEDIATION" in defs[lab]
    assert LABEL_DESCRIPTIONS["domain.technology.ai_discourse"].lower().find("technology") >= 0


def test_contract_forbids_abc_and_qual():
    c = bakeoff_contract()
    assert c["PHASE_RULE"] == "CONTINUE_V6_ARCHITECTURE_BAKEOFF"
    assert c["tracks"] == list(TRACKS)
    assert "incremental_ABC_tuning" in c["forbidden"]
    assert c["qual_policy"]["inspected"] is False
    assert c["advancement_gate"]["floors_locked"] is True
    assert c["advancement_gate"]["min_rep_system_macro_f1"] == 0.20
    assert c["advancement_gate"]["min_axis_macro_f1"] == 0.10


def test_selection_requires_axis_floor_and_exhaustion():
    weak = {
        "D_LABEL_DESCRIPTION_NLI__CONTROL": {
            "DEV": {
                "system": {"macro_f1": 0.03},
                "domain": {"macro_f1": 0.02},
                "function": {"macro_f1": 0.01},
                "mediation": {"macro_f1": 0.0},
            },
            "REP": {
                "system": {"macro_f1": 0.025},
                "domain": {"macro_f1": 0.02, "n_positive_labels": 100},
                "function": {"macro_f1": 0.01, "n_positive_labels": 40},
                "mediation": {"macro_f1": 0.0, "n_positive_labels": 10},
                "hierarchy": {"hierarchy_violation_rate": 0.0},
            },
        }
    }
    sel = select_reset_candidate(weak)
    assert sel["advance"] is False
    assert sel["selected"] is None
    assert sel["BAKEOFF_STATE"] == "V6_ARCHITECTURE_BAKEOFF_EXHAUSTED"
    assert sel["NEXT_ACTION"] == "REASSESS_V6_TASK_SIGNAL_AND_PRETRAINED_REPRESENTATION"
    assert ADVANCEMENT_GATE["min_axis_macro_f1"] == 0.10
    ax = axis_floors_pass(weak["D_LABEL_DESCRIPTION_NLI__CONTROL"]["REP"])
    assert ax["ok"] is False

    strong = {
        "D_LABEL_DESCRIPTION_NLI__EXTERNAL": {
            "DEV": {
                "system": {"macro_f1": 0.35},
                "domain": {"macro_f1": 0.30},
                "function": {"macro_f1": 0.25},
                "mediation": {"macro_f1": 0.20},
            },
            "REP": {
                "system": {"macro_f1": 0.28},
                "domain": {"macro_f1": 0.22, "n_positive_labels": 100},
                "function": {"macro_f1": 0.18, "n_positive_labels": 40},
                "mediation": {"macro_f1": 0.15, "n_positive_labels": 10},
                "hierarchy": {"hierarchy_violation_rate": 0.0},
            },
        }
    }
    sel2 = select_reset_candidate(strong)
    assert sel2["advance"] is True
    assert sel2["selected"] == "D_LABEL_DESCRIPTION_NLI__EXTERNAL"
    assert sel2["NEXT_ACTION"] == "HARDEN_V6_SELECTED_ARCHITECTURE_AND_PREPARE_QUALIFICATION"


def test_diagnose_zero_shot_stronger():
    results = {
        "D_LABEL_DESCRIPTION_NLI__CONTROL": {
            "REP": {
                "system": {"macro_f1": 0.03},
                "domain": {"macro_f1": 0.02},
                "function": {"macro_f1": 0.01},
                "mediation": {"macro_f1": 0.0},
                "hierarchy": {"hierarchy_violation_rate": 0.0},
            }
        }
    }
    zs = {"REP": {"system": {"macro_f1": 0.12}}}
    d = diagnose_exhaustion(results=results, zero_shot=zs, abc_best_rep=0.024)
    assert d["zero_shot_stronger_than_trained"] is True
    assert (
        d["primary_failure_diagnosis"]
        == "LABEL_SEMANTICS_PRIOR_STRONGER_THAN_CURRENT_TRAINED_REPRESENTATION"
    )
