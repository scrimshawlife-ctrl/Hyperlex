"""The v2 surface draw is one label-blind walk with fixed quotas."""

from __future__ import annotations

import inspect
from pathlib import Path

from hyperlexical.residual_threshold_v2_surface_draw import (
    MANIFEST_FIELDS,
    SAMPLING_RULE_ID,
    _identity_fences,
    allocate_surfaces,
    build_universe,
    manifest_row,
)


def _item(digest: str, pos: str, synset: str, surface: str) -> dict:
    return {
        "frozen_gloss": f"gloss {surface}",
        "normalized_text_sha256": digest,
        "operator_bucket": "HIGH",
        "pos": pos,
        "pwn30_synset": synset,
        "surface": surface,
    }


def _cells() -> dict[tuple[str, int], list[dict]]:
    return {
        ("noun", 2): [
            _item("n2", "noun", "noun:2", "noun two"),
            _item("n0", "noun", "noun:0", "noun zero"),
            _item("n1", "noun", "noun:1", "noun one"),
        ],
        ("adj", 2): [
            _item("a1", "adj", "adj:1", "adj one"),
            _item("a0", "adj", "adj:0", "adj zero"),
        ],
        ("adj", 3): [
            _item("a3", "adj", "adj:3", "adj three"),
        ],
    }


def test_frozen_walk_fills_calibration_before_continuing() -> None:
    allocated = allocate_surfaces(_cells(), 3, 3)
    assert allocated["filled"] is True
    assert allocated["shortage"] is None
    calibration = allocated["calibration"]
    measurement = allocated["measurement"]
    assert [row["row_id"] for row in calibration] == ["a0", "a3", "n0"]
    assert [row["row_id"] for row in measurement] == ["a1", "n1", "n2"]
    assert [row["global_draw_order"] for row in calibration] == [1, 2, 3]
    assert [row["global_draw_order"] for row in measurement] == [4, 5, 6]
    assert [row["surface_role"] for row in calibration] == ["CALIBRATION_V2"] * 3
    assert [row["surface_role"] for row in measurement] == ["MEASUREMENT_V2"] * 3
    assert calibration[0]["within_stratum_order"] == 1
    assert measurement[0]["within_stratum_order"] == 2
    assert calibration[0]["stratum_id"] == "adj:2"
    assert {row["allocation_rule_id"] for row in calibration + measurement} == {SAMPLING_RULE_ID}


def test_same_cell_is_not_alternating_when_the_walk_returns() -> None:
    cells = {
        ("adj", 2): [_item(f"a{i}", "adj", f"adj:{i}", f"adj {i}") for i in range(4)],
        ("noun", 2): [_item(f"n{i}", "noun", f"noun:{i}", f"noun {i}") for i in range(4)],
    }
    allocated = allocate_surfaces(cells, 3, 3)
    assert [row["row_id"] for row in allocated["calibration"]] == ["a0", "n0", "a1"]
    assert [row["row_id"] for row in allocated["measurement"]] == ["n1", "a2", "n2"]


def test_two_reconstructions_match_and_unsorted_input_is_ordered() -> None:
    first = allocate_surfaces(_cells(), 3, 3)
    second = allocate_surfaces(_cells(), 3, 3)
    assert first == second
    assert first["calibration"][0]["row_id"] == "a0"


def test_unfilled_quota_does_not_shrink_or_emit_partial_manifests() -> None:
    allocated = allocate_surfaces(_cells(), 4, 4)
    assert allocated["filled"] is False
    assert allocated["calibration"] == []
    assert allocated["measurement"] == []
    shortage = allocated["shortage"]
    assert shortage["calibration_quota"] == 4
    assert shortage["measurement_quota"] == 4
    assert shortage["calibration_rows_emitted"] == 4
    assert shortage["measurement_rows_emitted"] == 2
    exhausted = [cell for cell in shortage["cells"] if cell["exhausted"]]
    assert len(exhausted) == 3


def test_manifest_rows_omit_labels() -> None:
    allocated = allocate_surfaces(_cells(), 2, 2)
    for row in allocated["calibration"] + allocated["measurement"]:
        assert set(row) == set(MANIFEST_FIELDS)
        assert "operator_bucket" not in row
        assert row["row_id"] == row["normalized_text_sha256"]
        assert row["source_identity"] == "wordnet-3.0"


def test_draw_module_does_not_score_or_sample_at_random() -> None:
    path = Path(inspect.getsourcefile(allocate_surfaces))
    text = path.read_text(encoding="utf-8")
    allocator = "\n".join(
        inspect.getsource(function)
        for function in (allocate_surfaces, manifest_row, build_universe, _identity_fences)
    )
    assert "operator_bucket" not in allocator
    assert "select_threshold(" not in text
    assert "random" not in text
    assert "torch" not in text
    assert "GlossBERT" not in text
    assert "SentenceTransformer" not in text
    assert "0.672078" not in text
    assert "0.4040327275" not in text
    assert "CALIBRATION_LABELS" not in allocator
    assert "CALIBRATION_SCORES" not in allocator
