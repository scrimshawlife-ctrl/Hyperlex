import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.export import AI_NATIVE_TYPOLOGY, ai_native_typology

SNIPPET = (
    "import sys; sys.path.insert(0, %r);"
    "from hyperlexical.export import ai_native_typology;"
    "print(ai_native_typology(['status', 'compression']))"
) % str(ROOT / "scripts" / "shadow")


def test_ai_native_typology_dedupes_in_order():
    assert ai_native_typology(["status", "compression"]) == ["status", *AI_NATIVE_TYPOLOGY]


def test_ai_native_typology_independent_of_hash_seed():
    outs = {
        subprocess.run(
            [sys.executable, "-c", SNIPPET],
            env={"PYTHONHASHSEED": seed},
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        for seed in ("1", "2", "3")
    }
    assert len(outs) == 1
