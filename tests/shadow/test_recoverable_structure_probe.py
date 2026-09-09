import ast
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from recoverable_structure.fit import Abort, run_probe
from recoverable_structure.fixtures import snapshot
from recoverable_structure.receipt import ReceiptError, validate_receipt
from recoverable_structure.schemes import UnknownScheme, validate_schemes
from recoverable_structure import cli

SHADOW = ROOT / "scripts" / "shadow" / "recoverable_structure"


def test_t2_whitelist_and_abort():
    assert validate_schemes(["positional", "type_slot"]) == ["positional", "type_slot"]
    with pytest.raises(UnknownScheme):
        validate_schemes(["positional", "wickel"])


def test_t6_t7_t8_tpr_receipt():
    snap = snapshot("tpr", n=48, length=4, dim=12, seed=7)
    out = run_probe(snap, schemes=("positional", "type_slot"))
    rec = out["receipt"]
    validate_receipt(rec)
    assert rec["brier"] is None
    assert rec["forecast_eligible"] is False
    assert rec["auto_fire"] is False
    assert "symbolic" not in rec
    pos = next(b for b in rec["schemes"] if b["scheme"] == "positional")
    assert pos["test_mse"] < 1e-6
    assert "Brier: null" in out["card"]
    assert "Two-scheme cap" in out["card"]


def test_t12_polarity_tpr_vs_atomic():
    tpr = run_probe(snapshot("tpr", n=48, seed=7), schemes=("positional",))
    atom = run_probe(snapshot("atomic_pair", n=48, seed=7), schemes=("positional",))
    assert tpr["receipt"]["schemes"][0]["test_mse"] < atom["receipt"]["schemes"][0]["test_mse"]


def test_t5_t12_third_scheme_aborts():
    with pytest.raises(Abort):
        run_probe(snapshot("tpr", n=16, seed=3), schemes=("positional", "wickel"))


def test_receipt_rejects_symbolic():
    rec = dict(run_probe(snapshot("tpr", n=16, seed=1), schemes=("positional",))["receipt"])
    rec["symbolic"] = True
    with pytest.raises(ReceiptError):
        validate_receipt(rec)


def test_t11_cli_human(tmp_path):
    out = tmp_path / "card.txt"
    rc = cli.main(["--fixture", "tpr", "--human", "--out", str(out), "--schemes", "positional"])
    assert rc == 0
    text = out.read_text()
    assert "Brier: null" in text
    assert "SHADOW" in text


def test_cli_rejects_third_scheme():
    assert cli.main(["--schemes", "positional,wickel"]) == 2


def test_no_hyperlex_or_abraxas_imports():
    banned = ("import hyperlex", "from hyperlex", "import abraxas", "from abraxas")
    for path in SHADOW.glob("*.py"):
        src = path.read_text()
        for token in banned:
            assert token not in src


def test_no_network_calls_in_source():
    forbidden_mods = {"requests", "urllib", "http.client", "socket"}
    for path in SHADOW.glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden_mods
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden_mods
