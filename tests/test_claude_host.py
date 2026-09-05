"""Claude Code packaging: install dry-run + doctor host detection.

Offline only. Does not call Anthropic. Hermes dry-run must stay intact.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "hyperlex.py"
INSTALL = ROOT / "install.sh"


def _run(args: list[str], *, env: dict[str, str] | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged["HYPERLEX_OFFLINE"] = "1"
    merged["HYPERLEX_NO_RATE_LIMIT"] = "1"
    if env:
        merged.update(env)
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        cwd=str(cwd or ROOT),
        env=merged,
    )


def test_hermes_dry_run_unchanged(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    env = {
        "HOME": str(home),
        "HERMES_HOME": str(home / "profile"),
    }
    result = _run(["bash", str(INSTALL), "--dry-run"], env=env)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "would staged-validate then activate Hyperlex" in result.stdout
    assert "Claude personal skill" not in result.stdout
    assert "Claude plugin dir" not in result.stdout
    assert not (home / ".claude").exists()
    assert not (home / "profile" / "skills").exists()


def test_claude_dry_run_lists_personal_path(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    env = {
        "HOME": str(home),
        "HERMES_HOME": str(home / "profile"),
    }
    result = _run(["bash", str(INSTALL), "--claude", "--dry-run"], env=env)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "would staged-validate then activate Hyperlex" in result.stdout
    assert "Claude personal skill" in result.stdout
    assert str(home / ".claude" / "skills" / "hyperlex") in result.stdout
    assert "hyperlex-demo" in result.stdout
    assert "hyperlex-settle" in result.stdout
    assert not (home / ".claude").exists()


def test_claude_plugin_dry_run_lists_plugin_path(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    env = {
        "HOME": str(home),
        "HERMES_HOME": str(home / "profile"),
    }
    result = _run(["bash", str(INSTALL), "--claude-plugin", "--dry-run"], env=env)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "Claude plugin dir" in result.stdout
    assert str(home / ".claude" / "plugins" / "hyperlex") in result.stdout
    assert not (home / ".claude").exists()


def test_install_claude_skip_smoke_writes_personal_and_keeps_hermes(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    profile = home / "profile"
    env = {
        "HOME": str(home),
        "HERMES_HOME": str(profile),
    }
    result = _run(["bash", str(INSTALL), "--claude", "--skip-smoke"], env=env)
    assert result.returncode == 0, result.stderr + result.stdout
    hermes = profile / "skills" / "hyperlex"
    claude = home / ".claude" / "skills" / "hyperlex"
    assert (hermes / "SKILL.md").is_file()
    assert (hermes / "scripts" / "hyperlex.py").is_file()
    assert (claude / "SKILL.md").is_file()
    assert (claude / "scripts" / "hyperlex.py").is_file()
    assert (claude / "scripts" / "claude_hlx.sh").is_file()
    assert (home / ".claude" / "skills" / "hyperlex-demo" / "SKILL.md").is_file()
    assert (home / ".claude" / "skills" / "hyperlex-settle" / "SKILL.md").is_file()
    assert not (home / ".hermes").exists()


def test_doctor_reports_claude_missing(tmp_path: Path) -> None:
    home = tmp_path / "empty-home"
    home.mkdir()
    env = {
        "HOME": str(home),
        "HYPERLEX_SKILL_DIR": "",
        "CLAUDE_SKILL_DIR": "",
        "HERMES_SKILL_DIR": "",
    }
    # Drop leftover skill-dir hints from the parent environment.
    result = _run([sys.executable, str(SCRIPT), "doctor"], env=env)
    assert result.returncode == 0, result.stderr + result.stdout
    body = json.loads(result.stdout)
    assert body["ok"] is True
    assert body["n_failed"] == 0
    claude = next(c for c in body["checks"] if c["name"] == "claude_host")
    assert claude["ok"] is True
    assert claude["message"].startswith("CLAUDE_MISSING")


def test_doctor_reports_claude_ok(tmp_path: Path) -> None:
    home = tmp_path / "home"
    skill = home / ".claude" / "skills" / "hyperlex"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# hyperlex\n", encoding="utf-8")
    (skill / "scripts").mkdir()
    (skill / "scripts" / "hyperlex.py").write_text("# stub\n", encoding="utf-8")
    env = {
        "HOME": str(home),
        "HYPERLEX_SKILL_DIR": "",
        "CLAUDE_SKILL_DIR": "",
        "HERMES_SKILL_DIR": "",
    }
    result = _run([sys.executable, str(SCRIPT), "doctor"], env=env)
    assert result.returncode == 0, result.stderr + result.stdout
    body = json.loads(result.stdout)
    assert body["ok"] is True
    claude = next(c for c in body["checks"] if c["name"] == "claude_host")
    assert claude["ok"] is True
    assert claude["message"].startswith("CLAUDE_OK")
    assert "personal=" in claude["message"]


def test_claude_hlx_wrapper_check() -> None:
    result = _run(["bash", str(ROOT / "scripts" / "claude_hlx.sh"), "check"])
    assert result.returncode == 0, result.stderr + result.stdout
    body = json.loads(result.stdout)
    assert body["ok"] is True


def test_plugin_manifest_matches_version() -> None:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "hyperlex"
    assert manifest["version"] == version
    assert "Applied Alchemy Labs" in manifest["author"]["name"]
    assert "github.com/scrimshawlife-ctrl/Hyperlex" in manifest["homepage"]


def test_helper_skills_are_short_and_fail_closed() -> None:
    helpers = (
        "hyperlex-demo",
        "hyperlex-wizard",
        "hyperlex-scan",
        "hyperlex-analyze",
        "hyperlex-pending",
        "hyperlex-settle",
    )
    for name in helpers:
        skill = ROOT / ".claude" / "skills" / name / "SKILL.md"
        command = ROOT / "commands" / f"{name}.md"
        body = skill.read_text(encoding="utf-8")
        assert skill.is_file()
        assert command.is_file()
        assert "Never invent" in body or "Do not invent" in body or "do not invent" in body.lower()
        assert "$HLX" in body
        assert len(body.splitlines()) < 50
