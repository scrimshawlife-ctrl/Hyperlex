"""Spec 007 data/recipe PR #4: soft INFERRED unbind sample weight.

Default 1.0 is identity. Weight <1 scales CE + morph-margin for
class != OBSERVED only. Does not drop rows. Morph4 hard
HYPERLEX_UNBIND_INFERRED_CAP=1000 rejected (0.229; morph_negs 305→187).
"""

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.export import export_dataset
from hyperlexical.unbind_recipe import (
    UNBIND_INFERRED_WEIGHT_DEFAULT,
    UNBIND_INFERRED_WEIGHT_MAX,
    resolve_unbind_inferred_weight,
    shape_unbind_train,
    unbind_row_sample_weight,
)


def _unbind_row(text, fillers, *, cls="OBSERVED", split="train"):
    fills = list(fillers)
    return {
        "text": text,
        "split": split,
        "lineage": "brainrot-aura",
        "typology": ["compression"],
        "stage": "circulating",
        "roles": [f"pos_{i}" for i in range(len(fills))],
        "fillers": fills,
        "role_scheme": "positional",
        "task": "unbind",
        "provenance": "test:unbind",
        "class": cls,
        "license": "MIT-examples",
    }


def test_resolve_inferred_weight_default_identity(monkeypatch):
    monkeypatch.delenv("HYPERLEX_UNBIND_INFERRED_WEIGHT", raising=False)
    assert UNBIND_INFERRED_WEIGHT_DEFAULT == 1.0
    assert UNBIND_INFERRED_WEIGHT_MAX == 2.0
    assert resolve_unbind_inferred_weight() == 1.0
    assert resolve_unbind_inferred_weight("") == 1.0
    assert resolve_unbind_inferred_weight("  ") == 1.0
    monkeypatch.setenv("HYPERLEX_UNBIND_INFERRED_WEIGHT", "0.5")
    assert resolve_unbind_inferred_weight() == pytest.approx(0.5)
    assert resolve_unbind_inferred_weight(0.4) == pytest.approx(0.4)
    assert resolve_unbind_inferred_weight(2) == 2.0


def test_resolve_inferred_weight_reject_invalid(monkeypatch):
    monkeypatch.setenv("HYPERLEX_UNBIND_INFERRED_WEIGHT", "0")
    with pytest.raises(ValueError, match=r"finite number in \(0, 2\]"):
        resolve_unbind_inferred_weight()
    monkeypatch.setenv("HYPERLEX_UNBIND_INFERRED_WEIGHT", "-0.1")
    with pytest.raises(ValueError, match=r"finite number in \(0, 2\]"):
        resolve_unbind_inferred_weight()
    monkeypatch.setenv("HYPERLEX_UNBIND_INFERRED_WEIGHT", "2.1")
    with pytest.raises(ValueError, match=r"finite number in \(0, 2\]"):
        resolve_unbind_inferred_weight()
    monkeypatch.setenv("HYPERLEX_UNBIND_INFERRED_WEIGHT", "nope")
    with pytest.raises(ValueError, match=r"finite number in \(0, 2\]"):
        resolve_unbind_inferred_weight()
    monkeypatch.setenv("HYPERLEX_UNBIND_INFERRED_WEIGHT", "nan")
    with pytest.raises(ValueError, match=r"finite number in \(0, 2\]"):
        resolve_unbind_inferred_weight()
    monkeypatch.setenv("HYPERLEX_UNBIND_INFERRED_WEIGHT", "inf")
    with pytest.raises(ValueError, match=r"finite number in \(0, 2\]"):
        resolve_unbind_inferred_weight()


def test_sample_weight_default_identity_for_all_classes():
    w = resolve_unbind_inferred_weight(None)
    assert w == 1.0
    obs = _unbind_row("obs", ["aped"], cls="OBSERVED")
    inf = _unbind_row("inf", ["aura"], cls="INFERRED")
    spec = _unbind_row("spec", ["rizz"], cls="SPECULATIVE")
    missing = {"text": "none", "class": None, "fillers": ["yap"]}
    assert unbind_row_sample_weight(obs, w) == 1.0
    assert unbind_row_sample_weight(inf, w) == 1.0
    assert unbind_row_sample_weight(spec, w) == 1.0
    assert unbind_row_sample_weight(missing, w) == 1.0


def test_sample_weight_scales_only_non_observed():
    w = 0.5
    obs = _unbind_row("obs", ["aped"], cls="OBSERVED")
    inf = _unbind_row("inf", ["aura"], cls="INFERRED")
    spec = _unbind_row("spec", ["rizz"], cls="SPECULATIVE")
    missing = {"text": "none", "fillers": ["yap"]}
    assert unbind_row_sample_weight(obs, w) == 1.0
    assert unbind_row_sample_weight(inf, w) == pytest.approx(0.5)
    assert unbind_row_sample_weight(spec, w) == pytest.approx(0.5)
    assert unbind_row_sample_weight(missing, w) == pytest.approx(0.5)
    # CE + morph-margin for the row: OBSERVED stays full, INFERRED scales.
    ce_plus_margin = 4.0
    assert ce_plus_margin * unbind_row_sample_weight(obs, w) == pytest.approx(4.0)
    assert ce_plus_margin * unbind_row_sample_weight(inf, w) == pytest.approx(2.0)


def test_inferred_weight_does_not_drop_train_rows(monkeypatch):
    monkeypatch.setenv("HYPERLEX_UNBIND_INFERRED_WEIGHT", "0.4")
    monkeypatch.delenv("HYPERLEX_UNBIND_INFERRED_CAP", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_OBSERVED_UPSAMPLE", raising=False)
    rows = [
        _unbind_row("obs a", ["aped"], cls="OBSERVED"),
        _unbind_row("inf a", ["aura"], cls="INFERRED"),
        _unbind_row("inf b", ["rizz"], cls="INFERRED"),
    ]
    shaped, stats = shape_unbind_train(rows)
    assert [r["text"] for r in shaped] == [r["text"] for r in rows]
    assert stats["n_unbind_observed"] == 1
    assert stats["n_unbind_inferred"] == 2
    assert stats["unbind_inferred_cap"] == 0
    assert unbind_row_sample_weight(shaped[0], resolve_unbind_inferred_weight()) == 1.0
    assert unbind_row_sample_weight(shaped[1], resolve_unbind_inferred_weight()) == pytest.approx(0.4)
    assert unbind_row_sample_weight(shaped[2], resolve_unbind_inferred_weight()) == pytest.approx(0.4)


def test_export_sot_unchanged_when_inferred_weight_set(monkeypatch):
    monkeypatch.delenv("HYPERLEX_UNBIND_INFERRED_WEIGHT", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_INFERRED_CAP", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_HARD_ATOMS_PATH", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_HARD_UPSAMPLE", raising=False)
    baseline = export_dataset(ROOT)
    monkeypatch.setenv("HYPERLEX_UNBIND_INFERRED_WEIGHT", "0.5")
    weighted = export_dataset(ROOT)
    assert weighted["counts"]["unbind_inferred_weight"] == pytest.approx(0.5)
    assert baseline["counts"]["unbind_inferred_weight"] == pytest.approx(1.0)
    assert [r["text"] for r in weighted["rows"]] == [r["text"] for r in baseline["rows"]]
    assert [r.get("class") for r in weighted["rows"]] == [r.get("class") for r in baseline["rows"]]
    unbind = [r for r in weighted["rows"] if r["task"] == "unbind"]
    assert all("hard_neg_fillers" not in r for r in unbind)
    assert weighted["counts"]["n_unbind_observed"] == baseline["counts"]["n_unbind_observed"]
    assert weighted["counts"]["n_unbind_inferred"] == baseline["counts"]["n_unbind_inferred"]
    assert weighted["counts"]["name_gate"] is False
