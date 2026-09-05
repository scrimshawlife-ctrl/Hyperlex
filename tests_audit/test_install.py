import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = "hyperlex"


class InstallAudit(unittest.TestCase):
    def test_failed_check_preserves_previous_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            profile = home / "profile"
            dest = profile / "skills" / SKILL
            dest.mkdir(parents=True)
            (dest / "SKILL.md").write_text("previous package")
            (dest / "out/wizard-sessions").mkdir(parents=True)
            sentinel = dest / "out/wizard-sessions/keep.json"
            sentinel.write_text("previous session")
            source = Path(tmp) / "source"
            shutil.copytree(
                ROOT,
                source,
                ignore=shutil.ignore_patterns(
                    ".git", "skills", "out", "__pycache__", ".venv"
                ),
            )
            (source / "scripts/hyperlex.py").write_text("import sys\nsys.exit(42)\n")
            env = dict(os.environ, HOME=str(home), HERMES_HOME=str(profile))
            result = subprocess.run(
                check=False,
                args=["bash", str(source / "install.sh")],
                cwd=tmp,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual((dest / "SKILL.md").read_text(), "previous package")
            self.assertEqual(sentinel.read_text(), "previous session")
            self.assertFalse((home / ".hermes").exists())

    def test_profile_skills_symlink_cannot_redirect_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            profile = home / "profile-a"
            foreign = home / "profile-b/skills"
            profile.mkdir(parents=True)
            foreign.mkdir(parents=True)
            (profile / "skills").symlink_to(foreign, target_is_directory=True)
            env = dict(os.environ, HOME=str(home), HERMES_HOME=str(profile))
            result = subprocess.run(
                ["bash", str(ROOT / "install.sh")],
                cwd=tmp,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(list(foreign.iterdir()), [])
            self.assertTrue((profile / "skills").is_symlink())


if __name__ == "__main__":
    unittest.main()
