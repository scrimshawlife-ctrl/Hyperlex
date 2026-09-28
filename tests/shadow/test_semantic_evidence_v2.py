"""The successor evidence function is deterministic and does not rerun WSD."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from hyperlexical.semantic_evidence_v2 import (
    BASELINE_COMPOSITION,
    BASELINE_FAMILY,
    FEATURE_NAMES,
    MAX_REPRESENTATION_FAMILIES,
    MEASUREMENT_DISPOSITION,
    OUTPUT_LABELS,
    REPRESENTATION_FAMILIES,
    RULE,
    STATE,
    TRAINING_AUTHORIZED,
    baseline_residual,
    constituent_text,
    evidence_record,
    parent_text,
    template_sha256,
    weighted_mean,
)


def _vectors():
    whole = (1.0, 0.0)
    constituents = ((1.0, 0.0), (0.0, 1.0))
    gloss_whole = (0.6, 0.8)
    gloss_composed = (0.8, 0.6)
    lemma_whole = (1.0, 1.0)
    lemma_composed = (1.0, 0.0)
    return whole, constituents, gloss_whole, gloss_composed, lemma_whole, lemma_composed


def _ready():
    whole, constituents, gloss_whole, gloss_composed, lemma_whole, lemma_composed = _vectors()
    return evidence_record(
        whole=whole,
        constituents=constituents,
        gloss_whole=gloss_whole,
        gloss_composed=gloss_composed,
        lemma_whole=lemma_whole,
        lemma_composed=lemma_composed,
        token_count=2,
        resolved=True,
    )


def test_encoding_and_feature_generation_are_deterministic():
    assert parent_text("red herring", "noun", "a clue meant to mislead") == parent_text(
        "red herring", "noun", "a clue meant to mislead"
    )
    assert constituent_text("red", "a color") == "surface: red\ndefinition: a color\n"
    assert template_sha256() == hashlib.sha256(
        (parent_text("{surface}", "{pos}", "{gloss}") + constituent_text("{surface}", "{gloss}")).encode("utf-8")
    ).hexdigest()
    first = _ready()
    second = _ready()
    assert first == second
    assert [feature["name"] for feature in first["features"]] == list(FEATURE_NAMES)


def test_missing_constituent_structure_is_unknown():
    record = evidence_record(
        whole=(1.0, 0.0),
        constituents=((1.0, 0.0),),
        gloss_whole=(1.0, 0.0),
        gloss_composed=(1.0, 0.0),
        lemma_whole=(1.0, 0.0),
        lemma_composed=(1.0, 0.0),
        token_count=2,
        resolved=True,
    )
    assert record["evidence_status"] == "UNKNOWN"
    assert record["features"] is None
    assert record["output"] == "UNKNOWN"
    unresolved = _ready()
    unresolved = evidence_record(
        whole=(1.0, 0.0),
        constituents=((1.0, 0.0), (0.0, 1.0)),
        gloss_whole=(1.0, 0.0),
        gloss_composed=(1.0, 0.0),
        lemma_whole=(1.0, 0.0),
        lemma_composed=(1.0, 0.0),
        token_count=2,
        resolved=False,
    )
    assert unresolved["evidence_status"] == "UNKNOWN"


def test_baseline_residual_matches_the_historical_scalar():
    whole, constituents, *_rest = _vectors()
    record = _ready()
    residual = next(feature["value"] for feature in record["features"] if feature["name"] == "whole_vs_constituent_mean_residual")
    assert residual == baseline_residual(whole, constituents)
    assert BASELINE_FAMILY == "minilm_baseline"
    assert BASELINE_COMPOSITION == "normalized_mean_v1"
    weighted = weighted_mean(constituents, (1, 3))
    assert len(weighted) == 2


def test_feature_function_does_not_import_wsd_or_touch_training():
    source = Path(__import__("hyperlexical.semantic_evidence_v2", fromlist=["__file__"]).__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    banned = ("wordnet", "glossbert", "nltk", "sentence_transformers", "residual_threshold")
    assert not any(any(token in name for token in banned) for name in imported)
    assert _ready()["output"] == "UNKNOWN"
    assert OUTPUT_LABELS == ("YES", "UNKNOWN")
    assert "NO" not in OUTPUT_LABELS
    assert TRAINING_AUTHORIZED is False
    assert STATE == "SEMANTIC_EVIDENCE_V2_SPEC_DRAFTED"
    assert MEASUREMENT_DISPOSITION == "RETAIN_FOR_V2_ONLY"
    assert RULE == "RUNE.SEMANTIC_COMPOSITIONALITY_EVIDENCE.v2"
    assert len(REPRESENTATION_FAMILIES) == MAX_REPRESENTATION_FAMILIES


def test_evidence_record_matches_its_schema():
    schema_dir = Path(__file__).resolve().parents[2] / "specs/007-hyperlexical-model/schemas/hyperlex/semantic-evidence-v2"
    schemas = {path.name: json_load(path) for path in schema_dir.glob("*.schema.json")}
    registry = Registry()
    for schema in schemas.values():
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    validator = Draft202012Validator(schemas["evidence-record.schema.json"], registry=registry)
    assert validator.is_valid(_ready())
    unknown = evidence_record(
        whole=None,
        constituents=None,
        gloss_whole=None,
        gloss_composed=None,
        lemma_whole=None,
        lemma_composed=None,
        token_count=0,
        resolved=False,
    )
    assert validator.is_valid(unknown)
    ready = _ready()
    ready["output"] = "YES"
    assert not validator.is_valid(ready)


def json_load(path: Path):
    import json
    return json.loads(path.read_text(encoding="utf-8"))
