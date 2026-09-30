"""Forward ontology vocabulary switch tests."""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))


def test_historical_vocab_default():
    os.environ.pop("HLX_V2_FORWARD_ONTOLOGY", None)
    import hyperlexical.classification_v2 as v2

    importlib.reload(v2)
    assert len(v2.ACTIVE_FAMILY_VOCABULARY) == 19
    assert "approval-disapproval" in v2.ACTIVE_FAMILY_VOCABULARY
    assert "social-evaluation" not in v2.ACTIVE_FAMILY_VOCABULARY
    assert v2.FORWARD_ONTOLOGY is False


def test_forward_vocab_env():
    os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
    import hyperlexical.classification_v2 as v2

    importlib.reload(v2)
    try:
        assert v2.FORWARD_ONTOLOGY is True
        assert len(v2.ACTIVE_FAMILY_VOCABULARY) == 18
        assert "social-evaluation" in v2.ACTIVE_FAMILY_VOCABULARY
        assert "approval-disapproval" not in v2.ACTIVE_FAMILY_VOCABULARY
        assert "social-status" not in v2.ACTIVE_FAMILY_VOCABULARY
        assert "social-evaluation" not in v2.EXACT_COPY_FAMILIES
        assert len(v2.HISTORICAL_ACTIVE_FAMILY_VOCABULARY) == 19
    finally:
        os.environ.pop("HLX_V2_FORWARD_ONTOLOGY", None)
        importlib.reload(v2)
