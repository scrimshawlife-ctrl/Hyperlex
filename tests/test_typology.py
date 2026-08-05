"""Memetic typology expansion tests."""

from __future__ import annotations

from hyperlex.analysis import memetics_protocol_check
from hyperlex import detect_memetic_patterns


def test_typology_tactical_edge() -> None:
    m = memetics_protocol_check("sharp steam revenge narrative")
    assert m["typology_primary"] == "tactical_edge"
    assert m["is_memetic"] is True
    assert m["provenance"] == "INFERRED"
    assert "sharp" in m["rules_hit"]["tactical_edge"]


def test_typology_risk_identity() -> None:
    m = memetics_protocol_check("hodl diamond hands rekt degen")
    assert m["typology_primary"] == "risk_identity"


def test_typology_platform_agency() -> None:
    m = memetics_protocol_check("agentic slop skill issue hallucinate")
    assert m["typology_primary"] == "platform_agency"


def test_typology_one_off_quiet() -> None:
    m = memetics_protocol_check("the weather is mild with clouds")
    assert m["typology"] == "one_off"
    assert m["is_memetic"] is False


def test_lineage_prior_boosts() -> None:
    m = memetics_protocol_check("quiet text only", lineage_family="crypto-degen")
    # prior alone may not exceed threshold without cues — still records hit
    assert "lineage:crypto-degen" in m.get("rules_hit", {}).get("risk_identity", [])


def test_analysis_attaches_typology_primary() -> None:
    r = detect_memetic_patterns("sharp steam revenge", ingest_source="mock")
    mem = r["analysis"]["memetics"]
    assert mem.get("typology_primary") == "tactical_edge"
    assert "typology_scores" in mem
