from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.align import atom_token_index, char_span, pool_indices, whitespace_offsets
from hyperlexical.save_pretrained import composed_config, write_skeleton


def test_atom_span_locked_in():
    text = "locked in for the dub"
    assert char_span(text, "locked in") == (0, 9)
    offs = whitespace_offsets(text)
    assert atom_token_index(text, "locked in", offs) == [0, 1]


def test_pool_fallback():
    assert pool_indices(5, []) == [1]
    assert pool_indices(5, [2, 3]) == [2, 3]


def test_skeleton_writes_config(tmp_path):
    out = write_skeleton(tmp_path / "pkg", maps={"role_vocab": ["<unk>", "pos_0"], "filler_vocab": ["<unk>", "a"], "families": []})
    cfg = json.loads((out / "config.json").read_text())
    assert cfg["base_model"] == "answerdotai/ModernBERT-base"
    assert cfg["pipeline_tag"] == "text-classification"
    assert cfg["e2_pass"] is False
    assert cfg["brier"] is None
    assert composed_config()["name_gate"] is False
