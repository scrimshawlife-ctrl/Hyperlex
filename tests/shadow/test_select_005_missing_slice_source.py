"""The missing-slice source design is a preregistration, not a harvest."""

from pathlib import Path

import pytest

from hyperlexical.select_005_missing_slice_source import (
    MISSING_SLICES,
    SPENT_RECIPE,
    design_receipt,
    source_design,
)

REPO = Path(__file__).resolve().parents[2]


def test_design_covers_three_missing_slices_without_fetch():
    design = source_design()
    covered = set(design["families"]["A"]["slices"]) | set(design["families"]["B"]["slices"])
    assert set(MISSING_SLICES) <= covered
    assert design["families"]["A"]["slices"] == ["classify", "classify_observed", "classify_non_none"]
    assert design["families"]["B"]["slices"] == ["unbind_clean"]
    assert design["families"]["A"]["fetch_authorized"] is False
    assert design["families"]["B"]["fetch_authorized"] is False
    assert design["training_authorized"] is False
    assert design["spent_surface"]["redraw_authorized"] is False
    assert design["spent_surface"]["relabel_authorized"] is False
    assert design["spent_surface"]["decisions"]["UNRESOLVED"] == 888
    assert design["spent_surface"]["decisions"]["NONE"] == 40


def test_new_families_are_not_the_spent_recipe_or_wordnet():
    design = source_design()
    ids = {design["families"]["A"]["family_id"], design["families"]["B"]["family_id"]}
    assert ids.isdisjoint(SPENT_RECIPE)
    assert "wordnet" in design["families"]["B"]["refused_sources"]
    assert design["families"]["A"]["wordnet_admitted"] is False
    assert design["families"]["B"]["target_origin"] == "source_lemma_tokens"
    assert "operator_authored_fillers" in design["families"]["B"]["refused_sources"]
    assert design["families"]["A"]["routing"]["class"] == "OBSERVED"
    assert design["families"]["A"]["routing"]["unbind_clean"] is False
    assert design["families"]["B"]["routing"]["task"] == "unbind"
    assert design["families"]["B"]["routing"]["unbind_clean_derivation"] == "soft_ceiling.clean_surface"


def test_receipt_is_deterministic_and_records_no_fetch():
    first = design_receipt()
    second = design_receipt()
    assert first == second
    assert first["network_requests"] == 0
    assert first["rows_fetched"] == 0
    assert len(first["record_sha256"]) == 64


def test_module_has_no_fetch_client():
    text = (REPO / "scripts/shadow/hyperlexical/select_005_missing_slice_source.py").read_text()
    for banned in ("urllib", "import requests", "httpx", "urlopen", "import hs_run", "Popen"):
        assert banned not in text
    assert "does not fetch" in text


def test_wordnet_rights_fail_closed(monkeypatch):
    import hyperlexical.select_005_missing_slice_source as module

    original = module._family_b

    def bad():
        row = original()
        row["wordnet_admitted"] = True
        return row

    monkeypatch.setattr(module, "_family_b", bad)
    with pytest.raises(SystemExit, match="WordNet"):
        module.source_design()
