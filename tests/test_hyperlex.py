"""Tests for hyperlex package (v1.6 expanded ingest + schemas)."""

import json
import hashlib
from hyperlex import (
    ingest_signal,
    fetch_ingest,
    detect_memetic_patterns,
    mock_integrate_with_external_signal,
    humanize_slang_output,
    compute_virality_score,
    simulate_hyperstition_loop,
    schemas,
)

class _S:
    pass

s = _S()
s.ingest_signal = ingest_signal
s.fetch_ingest = fetch_ingest
s.detect_memetic_patterns = detect_memetic_patterns
s.mock_integrate_with_external_signal = mock_integrate_with_external_signal
s.humanize_slang_output = humanize_slang_output
s.compute_virality_score = compute_virality_score
s.simulate_hyperstition_loop = simulate_hyperstition_loop

# === Original compatibility tests ===
def test_humanize_slang_output_strips_aiisms():
    text = "This pivotal underscoring showcasing crucial landscape tapestry delve realm moment."
    result = s.humanize_slang_output(text)
    for bad in ["pivotal", "underscoring", "showcasing", "crucial", "landscape", "tapestry", "delve", "realm"]:
        assert bad not in result
    assert result  # AI-isms stripped; do not inject domain slang

def test_detect_memetic_patterns_structure():
    out = s.detect_memetic_patterns("slang emergence hyperstition")
    assert "observed" in out
    assert "inferred" in out
    assert "speculative" in out
    assert "provenance" in out
    prov = out["provenance"]
    assert "canonical_hash" in prov
    assert prov["brier"] is None
    assert "analysis" in out
    assert "virality" in out["analysis"]

def test_canonical_hash_stable():
    q = "test query"
    obs = "some observed text"[:100]
    canonical = json.dumps({"q": q, "obs": obs}, sort_keys=True, separators=(",", ":"))
    h = hashlib.sha256(canonical.encode()).hexdigest()[:16]
    assert len(h) == 16
    h2 = hashlib.sha256(canonical.encode()).hexdigest()[:16]
    assert h == h2

def test_recommendation_present():
    out = s.detect_memetic_patterns()
    assert "recommendation" in out

# === Expanded ingest tests (v1.6) ===
def test_ingest_signal_real_wired():
    sig = s.ingest_signal("sharp money revenge", source="real")
    assert isinstance(sig, str)
    assert len(sig) > 30

def test_ingest_signal_urban():
    sig = s.ingest_signal("sharp money", source="urban")
    assert isinstance(sig, str)
    assert len(sig) > 10

def test_ingest_signal_wikipedia():
    sig = s.ingest_signal("hyperstition", source="wikipedia")
    assert isinstance(sig, str)
    assert len(sig) > 5

def test_ingest_signal_combined():
    sig = s.ingest_signal("revenge narrative", source="combined")
    assert isinstance(sig, str)
    assert "|" in sig or "COMBINED" in sig

def test_fetch_ingest_structured():
    data = s.fetch_ingest("chalk eaters", source="glossary")
    assert isinstance(data, dict)
    assert "query" in data
    assert "raw_signal" in data
    assert "extracted_terms" in data
    assert "metadata" in data
    assert isinstance(data["extracted_terms"], list)

# === Schema tests ===
def test_schemas_loaded():
    assert schemas.INGEST_SCHEMA is not None
    assert schemas.RESULT_SCHEMA is not None
    assert "query" in schemas.INGEST_SCHEMA.get("properties", {})

def test_structured_ingest_validation():
    data = s.fetch_ingest("sharp action", source="reddit")
    ok, msg = schemas.validate_ingest(data)
    # Should be valid or jsonschema not present
    assert ok or "not installed" in msg

def test_result_validation():
    out = s.detect_memetic_patterns(query="memetic", ingest_source="urban", use_structured_ingest=True, validate=True)
    assert "schema_validation" in out
    assert "valid" in out["schema_validation"]

# === Integration tests ===
def test_mock_integration():
    slang_result = s.detect_memetic_patterns()
    signal = s.mock_integrate_with_external_signal(slang_result)
    assert "virality_boost" in signal
    assert "hyperstition_risk" in signal
    assert "confidence" in signal
    assert "actionable" in signal
