"""SELECT-006 source design v2 is a preregistration, not a harvest."""

import json
from pathlib import Path

import pytest

from hyperlexical.layout import FAMILIES
from hyperlexical.select_006_efficiency_preservation import EPSILON
from hyperlexical.select_006_reserve_acquisition import COMPUTABLE_HEAD_FAMILIES
from hyperlexical.select_006_reserve_source_design_v2 import (
    NEAR_MISS_LABELS,
    SOURCE_FAMILY,
    SPENT_RECIPES,
    TARGET_FAMILIES,
    blind_surface_errors,
    definition_prose,
    design_receipt,
    named_target_family,
    review_surface_row,
    sense_label_arguments,
    source_design,
)

REPO = Path(__file__).resolve().parents[2]
LINE = "# {{lb|en|slang|video games}} A player who wins every match."


def test_target_families_are_the_scoring_heads():
    design = source_design()
    assert list(TARGET_FAMILIES) == [name for name in FAMILIES if name in COMPUTABLE_HEAD_FAMILIES]
    assert set(TARGET_FAMILIES) == set(COMPUTABLE_HEAD_FAMILIES)
    assert design["target_families"] == list(TARGET_FAMILIES)
    assert "brainrot-aura" in design["legacy_heads_not_targets"]
    assert EPSILON == 0
    assert design["epsilon_unchanged"] == 0
    assert design["execution_loader_status"] == "NOT_YET_IMPLEMENTED"
    assert design["training_launch_authorized"] is False
    assert design["training_started"] is False


def test_recipe_is_not_the_spent_gloss_or_unbind_harvest():
    design = source_design()
    assert design["family"]["family_id"] == SOURCE_FAMILY
    assert design["family"]["family_id"] not in SPENT_RECIPES
    assert design["fetch_authorized"] is False
    assert design["unbind_clean_acquisition_authorized"] is False
    assert "unbind_clean" not in design["family"]["slices"]
    assert design["spent_surface"]["redraw_authorized"] is False
    assert design["spent_surface"]["relabel_authorized"] is False
    assert design["spent_surface"]["reuse_authorized"] is False
    assert design["spent_surface"]["decisions"]["UNRESOLVED"] == 10
    assert design["spent_surface"]["routed_slices"]["unbind_clean"] == 22
    assert design["spent_surface"]["observed"] == 0
    assert design["family"]["wordnet_admitted"] is False
    admitted = [row["family_id"] for row in design["evaluated_sources"] if row["admitted"]]
    assert admitted == [SOURCE_FAMILY]


def test_sense_label_names_one_target_and_near_misses_do_not():
    assert sense_label_arguments(LINE) == ["slang", "video games"]
    assert named_target_family(sense_label_arguments(LINE)) == "gaming-meta"
    assert named_target_family(["Video-Games"]) == "gaming-meta"
    assert named_target_family(["cryptocurrency"]) == "crypto-degen"
    assert named_target_family(["artificial intelligence"]) == "ai-native"
    assert named_target_family(["gambling", "cryptocurrency"]) is None
    for label in NEAR_MISS_LABELS:
        assert named_target_family([label]) is None
    assert "video games" not in definition_prose(LINE)
    assert definition_prose(LINE) == "A player who wins every match"


def test_review_surface_keeps_labels_and_hides_the_family():
    row = review_surface_row(
        {
            "candidate_id": "s006v2-example",
            "exact_definition_prose": definition_prose(LINE),
            "headword": "example headword",
            "page_url": "https://en.wiktionary.org/wiki/Example",
            "part_of_speech": "Noun",
            "revision_id": "1",
            "sense_label_arguments": sense_label_arguments(LINE),
            "source_lemma_tokens": ["example", "headword"],
        }
    )
    assert row["sense_label_arguments"] == ["slang", "video games"]
    assert "semantic_family" not in row
    assert blind_surface_errors([row]) == []
    leaked = dict(row)
    leaked["semantic_family"] = "gaming-meta"
    assert blind_surface_errors([leaked])


def test_receipt_records_no_fetch_and_is_deterministic():
    first = design_receipt()
    second = design_receipt()
    assert first == second
    assert first["network_requests"] == 0
    assert first["rows_fetched"] == 0
    assert len(first["record_sha256"]) == 64
    assert first["next_legal_transition"] == "SELECT_006_RESERVE_ACQUISITION_V2"


def test_module_has_no_fetch_client():
    text = (REPO / "scripts/shadow/hyperlexical/select_006_reserve_source_design_v2.py").read_text()
    for banned in ("urllib", "import requests", "httpx", "urlopen", "import firecrawl", "Popen"):
        assert banned not in text
    assert "does not fetch" in text


def test_supporting_artifacts_bind_the_design_and_do_not_rewrite_it(tmp_path):
    from hyperlexical.select_006_reserve_source_design_v2 import (
        freeze_design,
        sha256_file,
        write_supporting_artifacts,
    )

    design_path = tmp_path / "SOURCE_DESIGN_V2.json"
    design = freeze_design(str(design_path), repository_commit="a" * 40)
    before = design_path.read_bytes()
    hashes = write_supporting_artifacts(
        str(tmp_path),
        design,
        design_file=str(design_path),
        repository_commit="b" * 40,
    )
    assert design_path.read_bytes() == before
    assert set(hashes) == {
        "ARTIFACT_MANIFEST.json",
        "FUTURE_ACQUISITION_CONTRACT.json",
        "HEAD_MAPPING_WITNESS.json",
        "SOURCE_RIGHTS_PROVENANCE_POLICY.json",
        "SPEC_RECEIPT.json",
    }
    witness = json.loads((tmp_path / "HEAD_MAPPING_WITNESS.json").read_text())
    assert witness["target_families"] == list(TARGET_FAMILIES)
    assert witness["head_index"]["gaming-meta"] == FAMILIES.index("gaming-meta")
    policy = json.loads((tmp_path / "SOURCE_RIGHTS_PROVENANCE_POLICY.json").read_text())
    assert policy["rights"] == "CC-BY-SA"
    assert policy["generated_oldid_trusted"] is False
    contract = json.loads((tmp_path / "FUTURE_ACQUISITION_CONTRACT.json").read_text())
    assert contract["executes_in_this_pass"] is False
    assert contract["acquisition_floors"]["head_mapped_non_none"] == 1
    assert contract["spent_surface"]["reuse_authorized"] is False
    manifest = json.loads((tmp_path / "ARTIFACT_MANIFEST.json").read_text())
    pinned = {item["name"]: item["sha256"] for item in manifest["artifacts"]}
    assert pinned["SOURCE_DESIGN_V2.json"] == sha256_file(design_path)
    for name, digest in pinned.items():
        if name == "SOURCE_DESIGN_V2.json":
            continue
        assert sha256_file(tmp_path / name) == digest
    receipt = json.loads((tmp_path / "SPEC_RECEIPT.json").read_text())
    assert receipt["rows_fetched"] == 0
    assert receipt["network_requests"] == 0
    assert receipt["next_legal_transition"] == "SELECT_006_RESERVE_ACQUISITION_V2"
    assert receipt["artifact_sha256"]["ARTIFACT_MANIFEST.json"] == sha256_file(tmp_path / "ARTIFACT_MANIFEST.json")


def test_companion_seal_fails_closed():
    import hyperlexical.select_006_reserve_source_design_v2 as module

    design = module.design_receipt()
    module.require_sealable(design)
    broken = dict(design)
    broken["target_families"] = []
    broken["record_sha256"] = module.sha256_text(
        module.canonical_json({key: value for key, value in broken.items() if key != "record_sha256"})
    )
    with pytest.raises(SystemExit, match="NO_HEAD_MAPPED_TARGET_FAMILIES"):
        module.require_sealable(broken)
    unobserved = dict(design)
    family = dict(unobserved["family"])
    family["observed_rule"] = "unspecified"
    unobserved["family"] = family
    unobserved["record_sha256"] = module.sha256_text(
        module.canonical_json({key: value for key, value in unobserved.items() if key != "record_sha256"})
    )
    with pytest.raises(SystemExit, match="OBSERVED_RULE_UNDERSPECIFIED"):
        module.require_sealable(unobserved)


def test_wordnet_and_fetch_fail_closed(monkeypatch):
    import hyperlexical.select_006_reserve_source_design_v2 as module

    original = module._family

    def admit_wordnet():
        row = original()
        row["wordnet_admitted"] = True
        return row

    monkeypatch.setattr(module, "_family", admit_wordnet)
    with pytest.raises(SystemExit, match="CC-BY-SA"):
        module.source_design()
