from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.layout import FAMILIES, HIDDEN, LAST_TRAINABLE, LAYERS, describe, label_maps


def test_layout_shapes():
    maps = label_maps(
        [
            {"roles": ["pos_0", "pos_1"], "fillers": ["a", "b"]},
            {"roles": ["TOKEN"], "fillers": ["c"]},
        ]
    )
    card = describe(maps)
    assert card["hidden"] == HIDDEN == 768
    assert card["layers"] == LAYERS == 22
    assert card["last_trainable"] == LAST_TRAINABLE == 2
    assert card["classify"]["out"] == len(FAMILIES) == 9
    assert card["unbind_role"]["reads"] == "last_hidden_state"
    assert card["unbind_filler"]["reads"] == "last_hidden_state"
    assert "refusal_head" in card["forbidden"]
    assert card["brier"] is None
    assert maps["role_vocab"][0] == "<unk>"
    assert "a" in maps["filler_vocab"]
