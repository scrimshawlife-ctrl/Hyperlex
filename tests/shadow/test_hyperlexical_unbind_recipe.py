"""Spec 007 data/recipe shape: morph hard-negs + OBSERVED upsample / INFERRED cap."""

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.export import export_dataset, lexical_split
from hyperlexical.loop import prepare_unbind_splits
from hyperlexical.unbind_recipe import (
    UNBIND_INFERRED_CAP_DEFAULT,
    UNBIND_OBSERVED_UPSAMPLE_DEFAULT,
    hard_negatives_for,
    morph_margin_loss,
    morph_pairs_for_rows,
    resolve_unbind_inferred_cap,
    resolve_unbind_observed_upsample,
    shape_unbind_train,
)


def _unbind_row(text, fillers, *, cls="OBSERVED", split="train", roles=None):
    fills = list(fillers)
    return {
        "text": text,
        "split": split,
        "lineage": "brainrot-aura",
        "typology": ["compression"],
        "stage": "circulating",
        "roles": list(roles) if roles is not None else [f"pos_{i}" for i in range(len(fills))],
        "fillers": fills,
        "role_scheme": "positional",
        "task": "unbind",
        "provenance": "test:unbind",
        "class": cls,
        "license": "MIT-examples",
    }


def test_resolve_upsample_and_cap_defaults(monkeypatch):
    monkeypatch.delenv("HYPERLEX_UNBIND_OBSERVED_UPSAMPLE", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_INFERRED_CAP", raising=False)
    assert UNBIND_OBSERVED_UPSAMPLE_DEFAULT == 1
    assert UNBIND_INFERRED_CAP_DEFAULT == 0
    assert resolve_unbind_observed_upsample() == 1
    assert resolve_unbind_observed_upsample("") == 1
    assert resolve_unbind_inferred_cap() == 0
    assert resolve_unbind_inferred_cap("") == 0
    monkeypatch.setenv("HYPERLEX_UNBIND_OBSERVED_UPSAMPLE", "3")
    monkeypatch.setenv("HYPERLEX_UNBIND_INFERRED_CAP", "12")
    assert resolve_unbind_observed_upsample() == 3
    assert resolve_unbind_inferred_cap() == 12
    assert resolve_unbind_observed_upsample(2) == 2
    assert resolve_unbind_inferred_cap(4) == 4


def test_resolve_upsample_and_cap_reject_invalid(monkeypatch):
    monkeypatch.setenv("HYPERLEX_UNBIND_OBSERVED_UPSAMPLE", "0")
    with pytest.raises(ValueError, match="positive int"):
        resolve_unbind_observed_upsample()
    monkeypatch.setenv("HYPERLEX_UNBIND_OBSERVED_UPSAMPLE", "nope")
    with pytest.raises(ValueError, match="positive int"):
        resolve_unbind_observed_upsample()
    monkeypatch.setenv("HYPERLEX_UNBIND_INFERRED_CAP", "-1")
    with pytest.raises(ValueError, match="int >= 0"):
        resolve_unbind_inferred_cap()
    monkeypatch.setenv("HYPERLEX_UNBIND_INFERRED_CAP", "nope")
    with pytest.raises(ValueError, match="int >= 0"):
        resolve_unbind_inferred_cap()


def test_explicit_morph_pairs_seeded_from_failures():
    known = {"aped", "aping", "looksmaxxing", "looksmaxxed", "fanum", "aura", "rizz"}
    assert set(hard_negatives_for("aped", known)) == {"aping"}
    assert set(hard_negatives_for("aping", known)) == {"aped"}
    assert "looksmaxxed" in hard_negatives_for("looksmaxxing", known)
    assert "looksmaxxing" in hard_negatives_for("looksmaxxed", known)
    assert hard_negatives_for("rizz", known) == []
    assert hard_negatives_for("fanum", known) == []
    assert hard_negatives_for("aura", known) == []


def test_morph3_cluster_pairs_when_both_exist():
    """Morph3 residual near-morphs. Pair only if both fillers already exist."""
    rizz_known = {"rizz", "rizzed", "rizzless", "rizzing"}
    assert set(hard_negatives_for("rizz", rizz_known)) == {"rizzed", "rizzless", "rizzing"}
    assert set(hard_negatives_for("rizzed", rizz_known)) == {"rizz", "rizzless", "rizzing"}
    assert set(hard_negatives_for("rizzless", rizz_known)) == {"rizz", "rizzed", "rizzing"}

    quiet_known = {"quiet quit", "quiet quitter", "quiet quitting"}
    assert set(hard_negatives_for("quiet quitter", quiet_known)) == {
        "quiet quit",
        "quiet quitting",
    }
    assert set(hard_negatives_for("quiet quitting", quiet_known)) == {
        "quiet quit",
        "quiet quitter",
    }

    mew_known = {"mew", "mewing", "mewed"}
    assert set(hard_negatives_for("mewing", mew_known)) == {"mew", "mewed"}
    assert set(hard_negatives_for("mewed", mew_known)) == {"mew", "mewing"}

    crash_known = {"crash", "crashed", "crashout"}
    assert set(hard_negatives_for("crash", crash_known)) == {"crashed", "crashout"}
    assert set(hard_negatives_for("crashout", crash_known)) == {"crash", "crashed"}

    fanum_known = {"fanum", "fanum tax", "fanumtax", "fanum taxed", "taxed"}
    assert "taxed" in hard_negatives_for("fanum", fanum_known)
    assert "taxed" in hard_negatives_for("fanumtax", fanum_known)
    assert "fanumtax" in hard_negatives_for("fanum taxed", fanum_known)
    assert "looksmaxxing" in hard_negatives_for(
        "looksmaxxed", {"looksmaxxed", "looksmaxxing"}
    )


def test_morph3_does_not_invent_atoms():
    assert hard_negatives_for("rizzed", {"rizzed"}) == []
    assert hard_negatives_for("rizzless", {"rizzless"}) == []
    assert hard_negatives_for("quiet quitter", {"quiet quitter"}) == []
    assert hard_negatives_for("mewing", {"mewing"}) == []
    assert hard_negatives_for("crashout", {"crashout"}) == []
    assert hard_negatives_for("fanum taxed", {"fanum taxed"}) == []
    assert "rizzing" not in hard_negatives_for("rizz", {"rizz", "aped"})
    assert "quiet quitting" not in hard_negatives_for(
        "quiet quitter", {"quiet quitter", "rizz"}
    )


def test_taxed_pairs_only_when_gold_is_fanum_lineage():
    """tax/taxed alone are too broad. Pair with fanum* only from fanum gold."""
    mixed = {"fanum", "fanum tax", "fanumtax", "fanum taxed", "tax", "taxed", "rizz"}
    assert "taxed" in hard_negatives_for("fanum", mixed)
    assert "tax" in hard_negatives_for("fanum taxed", mixed)
    assert "fanumtax" in hard_negatives_for("fanum", mixed)
    fanum_from_taxed = set(hard_negatives_for("taxed", mixed))
    assert fanum_from_taxed.isdisjoint({"fanum", "fanum tax", "fanumtax", "fanum taxed"})
    assert "tax" in fanum_from_taxed
    fanum_from_tax = set(hard_negatives_for("tax", mixed))
    assert fanum_from_tax.isdisjoint({"fanum", "fanum tax", "fanumtax", "fanum taxed"})
    assert hard_negatives_for("taxed", {"taxed", "fanum"}) == []
    assert hard_negatives_for("tax", {"tax", "fanumtax"}) == []


def test_mewing_does_not_pair_with_me():
    """jawline mewing↔me is stem bleed, not a near-morph."""
    assert hard_negatives_for("mewing", {"mewing", "me"}) == []
    assert "me" not in hard_negatives_for("mewing", {"mewing", "mew", "mewed", "me"})


def test_cooked_is_not_a_morph_of_vibe_coded():
    """vibe coded↔cooked is not inflection / productive slang. Skip."""
    known = {"vibe coded", "coded", "cooked", "cook", "vibe"}
    assert hard_negatives_for("vibe coded", known) == []
    assert "cooked" not in hard_negatives_for("coded", known)
    assert "cooked" not in hard_negatives_for("vibe", known)


def test_quiet_quitter_does_not_pair_standalone_quitting():
    """Standalone quitting is too broad, like taxed without fanum* gold."""
    assert hard_negatives_for("quiet quitter", {"quiet quitter", "quitting"}) == []
    assert hard_negatives_for("quitting", {"quiet quitting", "quitting"}) == []
    assert set(hard_negatives_for("quiet quitter", {"quiet quitter", "quiet quitting"})) == {
        "quiet quitting"
    }


def test_auto_same_stem_does_not_invent_atoms():
    known = {"aped"}
    assert hard_negatives_for("aped", known) == []
    known = {"farming", "farmed", "cook"}
    assert set(hard_negatives_for("farming", known)) == {"farmed"}
    assert set(hard_negatives_for("farmed", known)) == {"farming"}
    assert hard_negatives_for("cook", known) == []
    # sibling surface absent → do not invent
    assert "aping" not in hard_negatives_for("aped", {"aped", "rizz"})


def test_morph_pairs_only_from_existing_unbind_fillers():
    rows = [
        _unbind_row("they aped in", ["aped"]),
        _unbind_row("still aping", ["aping"]),
        _unbind_row("just rizz", ["rizz"]),
    ]
    pairs = morph_pairs_for_rows(rows)
    gold_neg = {(p["gold"], p["neg"]) for p in pairs}
    assert ("aped", "aping") in gold_neg
    assert ("aping", "aped") in gold_neg
    assert all(p["gold"] != p["neg"] for p in pairs)
    assert all(p["source"] in {"explicit", "auto"} for p in pairs)
    assert not any(p["gold"] == "rizz" or p["neg"] == "rizz" for p in pairs)
    assert not any(p["neg"] == "looksmaxxing" for p in pairs)


def test_morph3_pairs_from_rows_do_not_invent_atoms():
    rows = [
        _unbind_row("he rizzed", ["rizzed"]),
        _unbind_row("no rizz", ["rizz"]),
        _unbind_row("fanum taxed me", ["fanum taxed"]),
        _unbind_row("just taxed", ["taxed"]),
        _unbind_row("quiet quitter", ["quiet quitter"]),
    ]
    pairs = morph_pairs_for_rows(rows)
    gold_neg = {(p["gold"], p["neg"]) for p in pairs}
    assert ("rizzed", "rizz") in gold_neg
    assert ("rizz", "rizzed") in gold_neg
    assert ("fanum taxed", "taxed") in gold_neg
    assert ("taxed", "fanum taxed") not in gold_neg
    assert not any(p["gold"] == "quiet quitter" for p in pairs)
    assert not any(p["neg"] == "rizzless" for p in pairs)
    assert not any(p["neg"] == "mewing" for p in pairs)


def test_shape_defaults_are_identity(monkeypatch):
    monkeypatch.delenv("HYPERLEX_UNBIND_OBSERVED_UPSAMPLE", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_INFERRED_CAP", raising=False)
    rows = [
        _unbind_row("obs a", ["aped"], cls="OBSERVED"),
        _unbind_row("inf a", ["aura"], cls="INFERRED"),
        _unbind_row("inf b", ["rizz"], cls="INFERRED"),
    ]
    shaped, stats = shape_unbind_train(rows)
    assert stats["unbind_observed_upsample"] == 1
    assert stats["unbind_inferred_cap"] == 0
    assert stats["n_unbind_observed"] == 1
    assert stats["n_unbind_inferred"] == 2
    assert [r["text"] for r in shaped] == [r["text"] for r in rows]
    assert stats["n_unbind_morph_negatives"] == 0


def test_shape_upsample_observed_only(monkeypatch):
    monkeypatch.setenv("HYPERLEX_UNBIND_OBSERVED_UPSAMPLE", "2")
    monkeypatch.delenv("HYPERLEX_UNBIND_INFERRED_CAP", raising=False)
    rows = [
        _unbind_row("obs a", ["aura"], cls="OBSERVED"),
        _unbind_row("inf a", ["rizz"], cls="INFERRED"),
    ]
    shaped, stats = shape_unbind_train(rows)
    texts = [r["text"] for r in shaped]
    assert texts.count("obs a") == 2
    assert texts.count("inf a") == 1
    assert stats["n_unbind_observed"] == 1
    assert stats["unbind_observed_upsample"] == 2
    assert stats["n_unbind_inferred"] == 1
    assert all(r["class"] == "OBSERVED" for r in shaped if r["text"] == "obs a")


def test_shape_inferred_cap_stable_prefix(monkeypatch):
    monkeypatch.delenv("HYPERLEX_UNBIND_OBSERVED_UPSAMPLE", raising=False)
    monkeypatch.setenv("HYPERLEX_UNBIND_INFERRED_CAP", "1")
    rows = [
        _unbind_row("obs a", ["aura"], cls="OBSERVED"),
        _unbind_row("inf a", ["rizz"], cls="INFERRED"),
        _unbind_row("inf b", ["yap"], cls="INFERRED"),
    ]
    shaped, stats = shape_unbind_train(rows)
    texts = [r["text"] for r in shaped]
    assert "obs a" in texts
    assert texts.count("inf a") == 1
    assert "inf b" not in texts
    assert stats["n_unbind_inferred"] == 1
    assert stats["unbind_inferred_cap"] == 1


def test_shape_attaches_hard_neg_fillers_on_train_rows(monkeypatch):
    monkeypatch.delenv("HYPERLEX_UNBIND_OBSERVED_UPSAMPLE", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_INFERRED_CAP", raising=False)
    rows = [
        _unbind_row("they aped in", ["aped"], cls="OBSERVED"),
        _unbind_row("still aping", ["aping"], cls="INFERRED"),
    ]
    shaped, stats = shape_unbind_train(rows)
    by_text = {r["text"]: r for r in shaped}
    assert "aping" in by_text["they aped in"]["hard_neg_fillers"]
    assert "aped" in by_text["still aping"]["hard_neg_fillers"]
    assert stats["n_unbind_morph_negatives"] >= 2


def test_prepare_unbind_splits_does_not_touch_val(monkeypatch):
    monkeypatch.setenv("HYPERLEX_UNBIND_OBSERVED_UPSAMPLE", "3")
    monkeypatch.setenv("HYPERLEX_UNBIND_INFERRED_CAP", "1")
    rows = [
        _unbind_row("train obs", ["aped"], cls="OBSERVED", split="train"),
        _unbind_row("train inf a", ["rizz"], cls="INFERRED", split="train"),
        _unbind_row("train inf b", ["yap"], cls="INFERRED", split="train"),
        _unbind_row("val obs", ["aping"], cls="OBSERVED", split="val"),
        _unbind_row("val inf", ["aura"], cls="INFERRED", split="val"),
        {"text": "rizz", "split": "train", "task": "classify", "class": "INFERRED",
         "lineage": "brainrot-aura", "fillers": [], "roles": []},
    ]
    train, val, stats = prepare_unbind_splits(rows)
    assert [r["text"] for r in val] == ["val obs", "val inf"]
    assert all(r["split"] == "val" for r in val)
    assert [r["text"] for r in train].count("train obs") == 3
    assert "train inf b" not in [r["text"] for r in train]
    assert stats["n_unbind_observed"] == 1
    assert stats["unbind_observed_upsample"] == 3


def test_lexical_split_frozen_when_settle_adds_rows():
    held = ("rizz", "aura farming", "fanum tax", "looksmaxxing")
    before = {t: lexical_split(t) for t in held}
    assert lexical_split("brand new settled atom xyz") in {"train", "val", "test"}
    after = {t: lexical_split(t) for t in held}
    assert after == before
    for t in held:
        assert lexical_split(t) == before[t]


def test_morph_margin_loss_pushes_away_from_neg():
    assert morph_margin_loss(2.0, [0.0], margin=0.5) == 0.0
    assert morph_margin_loss(0.0, [1.0], margin=0.5) == pytest.approx(1.5)
    assert morph_margin_loss(1.0, [1.0, 2.0], margin=0.5) == pytest.approx(0.5 + 1.5)


def test_export_counts_unbind_class_and_recipe_defaults(monkeypatch):
    monkeypatch.delenv("HYPERLEX_UNBIND_OBSERVED_UPSAMPLE", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_INFERRED_CAP", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_INFERRED_WEIGHT", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_CURRICULUM", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_FILLER_DENYLIST", raising=False)
    monkeypatch.delenv("HYPERLEX_UNBIND_FILLER_DENYLIST_PATH", raising=False)
    bundle = export_dataset(ROOT)
    c = bundle["counts"]
    assert c["n_unbind_observed"] + c["n_unbind_inferred"] == c["unbind"]
    assert c["n_unbind_observed"] == sum(
        1 for r in bundle["rows"] if r["task"] == "unbind" and r["class"] == "OBSERVED"
    )
    assert c["n_unbind_inferred"] == sum(
        1 for r in bundle["rows"] if r["task"] == "unbind" and r["class"] == "INFERRED"
    )
    assert c["unbind_observed_upsample"] == 1
    assert c["unbind_inferred_cap"] == 0
    assert c["unbind_inferred_weight"] == 1.0
    assert c["unbind_morph_negatives"] >= 0
    assert c["unbind_curriculum"] == 0
    assert c["unbind_filler_denylist_lineages"] == 0
    assert c["name_gate"] is False
    # Export JSONL stays SoT-shaped: no invented OBSERVED copies / hard-neg keys.
    unbind = [r for r in bundle["rows"] if r["task"] == "unbind"]
    assert all("hard_neg_fillers" not in r for r in unbind)
