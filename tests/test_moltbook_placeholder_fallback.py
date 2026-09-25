"""Moltbook adapters must not invent a filler when the detector returns none."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(filename: str):
    path = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _analysis(technique):
    return {
        "analysis": {
            "memetic_memory": {
                "memory_tiers": ["episodic"],
                "context_loss_technique": technique,
                "provenance_required": False,
            },
            "compression": {"compression_type": "mixed"},
            "virality": {},
        },
        "memetic_efficiency": {"efficiency_score": 0.2},
    }


def test_moltbook_to_hyperlexical_emits_no_general_fallback(monkeypatch):
    mod = _load("moltbook_to_hyperlexical.py")
    monkeypatch.setattr(mod, "detect_memetic_patterns", lambda *a, **k: _analysis(None))
    row = mod.moltbook_post_to_row(
        {"title": "Good morning", "body": "The coffee is ready.", "post_id": "synthetic"}
    )
    assert row["fillers"] == []
    assert "general" not in row["fillers"]
    assert "KDR" not in row["fillers"]


def test_moltbook_to_hyperlexical_keeps_detector_technique(monkeypatch):
    mod = _load("moltbook_to_hyperlexical.py")
    monkeypatch.setattr(mod, "detect_memetic_patterns", lambda *a, **k: _analysis("KDR"))
    row = mod.moltbook_post_to_row(
        {"title": "Note", "body": "A technique was detected.", "post_id": "synthetic"}
    )
    assert row["fillers"] == ["KDR"]


def test_high_signal_emits_no_label_when_detector_finds_none(monkeypatch):
    mod = _load("create_high_signal_subset.py")
    monkeypatch.setattr(mod, "detect_memetic_patterns", lambda *a, **k: _analysis(None))
    out = mod.classify_row("Good morning, the coffee is ready.", None)
    assert out["fillers"] == []
    assert "general" not in out["fillers"]
    assert "KDR" not in out["fillers"]


def test_high_signal_keeps_detector_technique(monkeypatch):
    mod = _load("create_high_signal_subset.py")
    monkeypatch.setattr(mod, "detect_memetic_patterns", lambda *a, **k: _analysis("sliding_window"))
    out = mod.classify_row("A technique was detected.", None)
    assert out["fillers"] == ["sliding_window"]


def test_high_signal_does_not_stamp_kdr_when_detector_returns_nothing(monkeypatch):
    """Old fallback stamped KDR onto texts that merely contained rented/ghost."""
    mod = _load("create_high_signal_subset.py")

    def _down(*_args, **_kwargs):
        raise RuntimeError("detector unavailable")

    monkeypatch.setattr(mod, "detect_memetic_patterns", _down)
    out = mod.classify_row(
        "a ghost of rented memory",
        {"efficiency": 0.4, "tiers": ["episodic"], "provenance_required": False},
    )
    assert out["fillers"] == []
    assert "KDR" not in out["fillers"]
    assert "general" not in out["fillers"]
