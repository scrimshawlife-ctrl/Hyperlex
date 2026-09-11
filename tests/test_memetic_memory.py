"""Tests for Moltbook-assimilated memetic memory features."""

from hyperlex.analysis import (
    classify_compression_type,
    compute_context_friction,
    detect_memetic_memory_patterns,
)


def test_classify_compression_load_bearing():
    text = "We need provenance and episodic consolidation like ECHO for reliable memory."
    result = classify_compression_type(text)
    assert result["compression_type"] == "load_bearing"
    assert result["score"] > 0.5


def test_classify_compression_decorative():
    text = "This is a pivotal landscape tapestry of the realm."
    result = classify_compression_type(text)
    assert result["compression_type"] in ("decorative", "mixed")


def test_context_friction_detects_loss():
    text = "Sliding windows cause context to fall off the conveyor belt. Re-entry costs 7000+ tokens."
    result = compute_context_friction(text)
    assert result["friction_score"] > 0.3
    assert "conveyor belt" in str(result["loss_patterns"]) or "sliding window" in str(result)


def test_detect_memetic_memory_patterns():
    text = "KDR helps with multi-agent context loss. Tiered memory: scratchpad + episodic + rubric. Provenance required."
    result = detect_memetic_memory_patterns(text)
    assert "scratchpad" in result["memory_tiers"]
    assert "episodic" in result["memory_tiers"]
    assert result["provenance_required"] is True
    assert result["context_loss_technique"] == "KDR"


def test_full_detect_with_memory_fields():
    from hyperlex import detect_memetic_patterns
    res = detect_memetic_patterns(
        "agent memory provenance KDR tiered context loss",
        ingest_source="moltbook"
    )
    analysis = res["analysis"]
    assert "memetic_memory" in analysis
    assert "compression" in analysis
    assert "context_friction" in analysis
    assert analysis["memetic_memory"]["provenance_required"] is True


def test_compute_memetic_efficiency_score():
    from hyperlex.analysis import compute_memetic_efficiency_score, detect_memetic_memory_patterns
    text = "KDR episodic rubric ghost in the cache provenance ECHO"
    eff = compute_memetic_efficiency_score(text)
    assert "efficiency_score" in eff
    assert 0 <= eff["efficiency_score"] <= 1
    assert "components" in eff
    # higher on good signals
    assert eff["efficiency_score"] > 0.4

def test_synthesis_includes_memetic_efficiency():
    from hyperlex import detect_memetic_patterns
    from hyperlex.synthesis import mock_integrate_with_external_signal
    res = detect_memetic_patterns("memory ledge concurrent writes KDR", ingest_source="moltbook")
    sig = mock_integrate_with_external_signal(res)
    assert "memetic_efficiency" in sig
    assert "memory_tiers" in sig
    assert sig["actionable"] in ("MONITOR", "IGNORE")

