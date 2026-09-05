import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class HyperlexInstallAudit(unittest.TestCase):
    def test_real_install_reinstall_and_explicit_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            profile = home / "profile"
            env = dict(os.environ, HOME=str(home), HERMES_HOME=str(profile))
            dest = profile / "skills/hyperlex"
            for args in ([], ["--skip-smoke"]):
                result = subprocess.run(
                    ["bash", str(ROOT / "install.sh"), *args],
                    cwd=tmp,
                    env=env,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                receipt = json.loads((dest / ".install-provenance.json").read_text())
                self.assertEqual(
                    receipt["status"], "UNVERIFIED" if args else "VALIDATED"
                )
                if args:
                    self.assertIn("UNVERIFIED", result.stdout)
                    self.assertEqual((dest / "out/keep").read_text(), "operator output")
                else:
                    (dest / "out").mkdir(exist_ok=True)
                    (dest / "out/keep").write_text("operator output")
            self.assertFalse((home / ".hermes").exists())

    def test_smoke_failure_not_just_check_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            shutil.copytree(
                ROOT,
                source,
                ignore=shutil.ignore_patterns(".git", "out", "__pycache__", ".venv"),
            )
            cli = source / "scripts/hyperlex.py"
            text = cli.read_text()
            signature = "def cmd_smoke(_args: argparse.Namespace) -> int:\n"
            self.assertIn(signature, text)
            cli.write_text(
                text.replace(
                    signature,
                    signature + "    return 42  # injected smoke-only failure\n",
                    1,
                )
            )
            home = Path(tmp) / "home"
            home.mkdir()
            dest = home / "profile/skills/hyperlex"
            dest.mkdir(parents=True)
            (dest / "SKILL.md").write_text("previous install")
            env = dict(os.environ, HOME=str(home), HERMES_HOME=str(home / "profile"))
            result = subprocess.run(
                ["bash", str(source / "install.sh")],
                cwd=tmp,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("42", result.stderr)
            self.assertEqual((dest / "SKILL.md").read_text(), "previous install")


if __name__ == "__main__":
    unittest.main()
