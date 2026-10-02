"""Tests for HYPERLEX_INSTRUMENT_V1 packaging and Abraxas authority boundary."""

from __future__ import annotations

import json
import threading
import time
from http.client import HTTPConnection

import pytest

from hyperlex.compat.abraxas import (
    AuthorityBoundaryError,
    assert_not_authoritative,
    promote_to_canonical_state,
    to_abraxas_evidence,
)
from hyperlex.instrument import (
    CLASSIFIER_RELEASE,
    CONTRACT_VERSION,
    INSTRUMENT_VERSION,
    OPERATION_MODE,
    InstrumentClient,
    InstrumentHttpClient,
    cold_load_manifest,
    get_capabilities,
    health,
    observe,
    validate_observation,
)
from hyperlex.instrument.api import make_server
from hyperlex.instrument.constants import RESEARCH_ONLY_CONCEPTS


def test_cold_load_and_manifest_integrity():
    m = cold_load_manifest()
    assert m["instrument_version"] == INSTRUMENT_VERSION
    assert m["contract_version"] == CONTRACT_VERSION
    assert m["operation_mode"] == OPERATION_MODE
    assert m["classifier_release"] == CLASSIFIER_RELEASE
    assert m["authority_boundary"]["HYPERLEX_OUTPUT_EQ_SEMANTIC_TRUTH"] is False
    assert m["schema_sha256"]
    assert m["manifest_sha256"]
    assert len(m["manifest_sha256"]) == 64
    # Self-check: rebuild digest excluding field
    body = {k: v for k, v in m.items() if k != "manifest_sha256"}
    import hashlib

    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert digest == m["manifest_sha256"]


def test_capabilities_discovery():
    caps = get_capabilities()
    c = caps["capabilities"]
    assert c["evidence_signal"]["status"] == "supported"
    assert c["representation"]["status"] == "supported"
    assert c["domain_candidates"]["status"] == "advisory"
    assert c["mediation_candidates"]["status"] == "advisory"
    assert c["function_candidates"]["status"] == "experimental_or_advisory"
    assert c["memetic_form"]["status"] == "research_only"
    assert c["final_classification"]["status"] == "unsupported"
    assert c["distribution_distance"]["status"] == "unavailable"
    assert caps["authority"]["HYPERLEX_OUTPUT_EQ_SEMANTIC_TRUTH"] is False
    assert "classify" in caps["forbidden_operations"]


def test_observe_structure_and_determinism():
    a = observe("crypto nft airdrop on reddit")
    b = observe("crypto nft airdrop on reddit")
    assert a["observation_id"] == b["observation_id"]
    assert a["input_hash"] == b["input_hash"]
    assert a["schema"] == "hyperlex.instrument.v1"
    assert a["authority"]["semantic_truth"] is False
    assert a["authority"]["kind"] == "advisory"
    assert a["final_classification"] is None
    assert "domain_labels" not in a
    assert validate_observation(a)["ok"] is True
    assert a["representation"]["embed_mode"] == "STATIC_HASH_EMBEDDING"
    assert a["provenance"]["instrument_version"] == INSTRUMENT_VERSION
    assert a["provenance"]["manifest_sha256"]
    assert a["provenance"]["settlement_receipt"]


def test_none_abstention_is_valid():
    obs = observe("the")
    assert obs["evidence"]["abstain"] is True
    assert obs["evidence"]["present"] is False
    assert obs["candidates"] == []
    assert validate_observation(obs)["ok"] is True

    empty = observe("   ")
    assert empty["evidence"]["abstain"] is True
    assert empty["candidates"] == []


def test_candidates_are_advisory_only_and_no_memetic_form():
    obs = observe("bitcoin defi gambling odds poker meme format")
    assert obs["evidence"]["present"] is True
    assert obs["candidates"]
    for c in obs["candidates"]:
        assert c["advisory"] is True
        assert c["concept_id"] not in RESEARCH_ONLY_CONCEPTS
    # DOMAIN/MEDIATION axes may appear only as advisory candidates
    axes = {c["axis"] for c in obs["candidates"]}
    assert axes <= {"domain", "mediation", "function"}


def test_unavailable_diagnostics_not_fabricated():
    obs = observe("software programming algorithm")
    d = obs["diagnostics"]
    assert d["distribution_distance"] is None
    assert d["representation_drift"] is None
    assert "distribution_distance" in d["unavailable"]
    assert "representation_drift" in d["unavailable"]


def test_health():
    h = health()
    assert h["ok"] is True
    assert h["HYPERLEX_OUTPUT_EQ_SEMANTIC_TRUTH"] is False


def test_sdk_inprocess():
    client = InstrumentClient()
    obs = client.observe("nba tournament championship")
    assert obs["schema"] == CONTRACT_VERSION
    assert client.manifest()["manifest_sha256"]
    assert client.capabilities()["primary_operation"] == "observe"


def test_api_sdk_parity():
    httpd = make_server("127.0.0.1", 18741)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        # wait for bind
        for _ in range(50):
            try:
                conn = HTTPConnection("127.0.0.1", 18741, timeout=1)
                conn.request("GET", "/v1/health")
                assert conn.getresponse().status == 200
                conn.close()
                break
            except OSError:
                time.sleep(0.05)
        else:
            pytest.fail("server did not start")

        http = InstrumentHttpClient("http://127.0.0.1:18741")
        local = InstrumentClient()
        text = "chatgpt llm prompt inference"
        a = local.observe(text)
        b = http.observe(text)
        assert a["observation_id"] == b["observation_id"]
        assert a["candidates"] == b["candidates"]
        assert http.health()["ok"] is True
        assert http.manifest()["manifest_sha256"] == local.manifest()["manifest_sha256"]
    finally:
        httpd.shutdown()


def test_abraxas_adapter_mapping_and_authority_boundary():
    obs = observe("ethereum blockchain defi")
    ev = to_abraxas_evidence(obs, role="SHADOW_SIGNAL")
    assert ev["source"] == "hyperlex"
    assert ev["authority"] == "advisory"
    assert ev["semantic_truth"] is False
    assert ev["kind"] == "SHADOW_SIGNAL"
    assert ev["valid_for_forecast"] is False
    assert ev["influence_policy"] == "NONE"
    assert ev["instrument_version"] == INSTRUMENT_VERSION
    assert ev["ontology_version"]
    assert_not_authoritative(ev)

    with pytest.raises(AuthorityBoundaryError):
        promote_to_canonical_state(ev)

    with pytest.raises(AuthorityBoundaryError):
        to_abraxas_evidence(obs, role="CANONICAL_STATE")

    bad = dict(ev, semantic_truth=True)
    with pytest.raises(AuthorityBoundaryError):
        assert_not_authoritative(bad)

    # Non-advisory candidate must not cross the boundary
    poisoned = dict(obs)
    poisoned["candidates"] = [
        {
            "concept_id": "domain.crypto",
            "score": 0.9,
            "axis": "domain",
            "advisory": False,
            "status": "advisory",
        }
    ]
    with pytest.raises(AuthorityBoundaryError):
        to_abraxas_evidence(poisoned)
