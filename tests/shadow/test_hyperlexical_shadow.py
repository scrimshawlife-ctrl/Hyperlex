import ast
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.infer import main as infer_main
from hyperlexical.packet import (
    PacketError,
    attach_or_omit,
    build_packet,
    validate_packet,
)

SHADOW = ROOT / "scripts" / "shadow" / "hyperlexical"
SCHEMA = ROOT / "specs" / "007-hyperlexical-model" / "schemas" / "hyperlexical_inference.v0.1.schema.json"
CONTRACTS = ROOT / "specs" / "007-hyperlexical-model" / "contracts"
TORCH_ALLOWED = {
    "classification_v2_runtime.py",
    "classify_error_audit.py",
    "eval_forward.py",
    "loop.py",
    "model_based_wsd_candidate_v1_replay.py",
    "save_pretrained.py",
    "select_005_reserve_eval.py",
    "select_006_reserve_eval.py",
    "select_007_reserve_eval.py",
    "semantic_compositionality_residual_replay.py",
    "training_reviewed_loop.py",
    "zero_init_loader.py",
}
NETWORK_ALLOWED = {"classification_v2_acquire_run.py"}


def test_e0_rizz_packet():
    pkt = build_packet("rizz")
    assert pkt["brier"] is None
    assert pkt["forecast_eligible"] is False
    assert pkt["auto_fire"] is False
    assert "semantic" not in pkt["routes_claimed"]
    assert pkt["model_id"] == "stub"
    assert pkt["embed_mode"] == "STATIC_HASH_EMBEDDING"
    assert pkt["surface"] == "rizz"
    assert pkt["unbind_ok"] is False


def test_e4_restricted_drops_surface():
    pkt = build_packet("__RESTRICTED_FIXTURE__ payload", restricted=True)
    assert pkt["restricted_intent_suspected"] is True
    assert pkt["surface"] is None
    assert isinstance(pkt["payload_ref"], str) and len(pkt["payload_ref"]) == 64


def test_e6_dialect_no_refusal():
    pkt = build_packet("no cap fr")
    assert pkt["surface"] == "no cap fr"
    blob = json.dumps(pkt).lower()
    assert "i cannot analyze" not in blob
    assert "as an ai" not in blob


def test_forbid_symbolic():
    pkt = build_packet("rizz")
    pkt["symbolic"] = True
    with pytest.raises(PacketError):
        validate_packet(pkt)


def test_forbid_semantic_route():
    pkt = build_packet("rizz")
    pkt["routes_claimed"] = ["semantic"]
    with pytest.raises(PacketError):
        validate_packet(pkt)


def test_model_embedding_requires_hashes():
    pkt = build_packet("rizz")
    pkt["embed_mode"] = "MODEL_EMBEDDING"
    pkt["input_hash"] = None
    with pytest.raises(PacketError):
        validate_packet(pkt)


def test_omit_on_empty():
    assert attach_or_omit(None) is None
    bad = build_packet("rizz")
    bad["brier"] = 0.2
    assert attach_or_omit(bad) is None
    ok = attach_or_omit(build_packet("rizz"))
    assert ok["analysis"]["hyperlexical"]["schema"].startswith("hyperlex.hyperlexical")


def test_cli_offline_rizz(tmp_path):
    out = tmp_path / "pkt.json"
    rc = infer_main(["--text", "rizz", "--offline", "--out", str(out)])
    assert rc == 0
    pkt = json.loads(out.read_text())
    assert pkt["surface"] == "rizz"
    assert pkt["brier"] is None


_BANNED_PACKAGE_ROOTS = frozenset({"hyperlex", "abraxas"})


def _import_roots(src: str) -> set[str]:
    """Top-level module names of import statements. ``hyperlexical`` is not ``hyperlex``."""
    roots: set[str] = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_no_hyperlex_or_abraxas_imports():
    for path in SHADOW.glob("*.py"):
        roots = _import_roots(path.read_text())
        banned = roots & _BANNED_PACKAGE_ROOTS
        assert not banned, f"{path.name} imports {sorted(banned)}"
        if path.name not in TORCH_ALLOWED:
            assert "torch" not in roots, path.name


def test_import_boundary_permits_hyperlexical_and_rejects_hyperlex_and_abraxas():
    hyperlexical = "from hyperlexical.holdout_eligibility import census\n"
    assert _import_roots(hyperlexical) == {"hyperlexical"}
    mentioned = (
        'note = "from hyperlex import hidden"\n'
        "# import abraxas\n"
        "from hyperlexical.packet import build_packet\n"
    )
    assert _import_roots(mentioned) == {"hyperlexical"}
    rejected = (
        "import hyperlex\n",
        "import hyperlex.analysis\n",
        "from hyperlex import detect_memetic_patterns\n",
        "from hyperlex.analysis.mutation import predict_mutations\n",
        "import abraxas\n",
        "from abraxas.compat import foo\n",
    )
    for src in rejected:
        assert _import_roots(src) & _BANNED_PACKAGE_ROOTS, src


def test_no_network_calls_in_source():
    forbidden_mods = {"requests", "urllib", "http.client", "socket", "huggingface_hub"}
    for path in SHADOW.glob("*.py"):
        if path.name in NETWORK_ALLOWED:
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden_mods, path.name
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden_mods, path.name


def test_contracts_and_schema_exist():
    assert SCHEMA.is_file()
    assert (CONTRACTS / "example.ok.json").is_file()
    assert (CONTRACTS / "example.restricted.json").is_file()
    assert (CONTRACTS / "example.e6-dialect.json").is_file()


def test_jsonschema_if_installed():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text())
    Validator = jsonschema.Draft202012Validator
    Validator.check_schema(schema)
    v = Validator(schema)
    v.validate(build_packet("rizz"))
    v.validate(build_packet("__RESTRICTED_FIXTURE__", restricted=True))
    v.validate(json.loads((CONTRACTS / "example.ok.json").read_text()))
    v.validate(json.loads((CONTRACTS / "example.restricted.json").read_text()))
    v.validate(json.loads((CONTRACTS / "example.e6-dialect.json").read_text()))
