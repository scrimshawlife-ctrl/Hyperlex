from pathlib import Path

from hyperlex.init_skill import TARGETS, run_init, run_uninstall, skill_template


def test_template_has_marker_and_cli():
    body = skill_template()
    assert "<!-- hyperlex-init -->" in body
    assert "hyperlex mutation trace" in body
    assert "hyperlex pipeline" in body


def test_init_dry_run_lists_default_hosts():
    out = run_init(["hermes", "grok"], dry_run=True)
    assert out["ok"] is True
    assert len(out["written"]) == 2
    assert all(row["path"].endswith("SKILL.md") for row in out["written"])


def test_targets_are_under_home():
    home = str(Path.home())
    for dest in TARGETS.values():
        assert str(dest).startswith(home)
