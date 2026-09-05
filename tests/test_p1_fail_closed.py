"""ADVERSARY P1 fail-closed gates: install/init, settle, X-base, cloud-write, SoT, receipt."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from hyperlex.guards import (
    SETTLE_CONFIRM_PHRASE,
    CloudWriteError,
    SettleGateError,
    UrlGateError,
    require_cloud_write,
    require_http_url,
    require_scored_settle_gate,
    validate_x_api_base,
)
from hyperlex.calibration.settlement import settle
from hyperlex.calibration.score_log import settle_and_log
from hyperlex.intake.x_search import fetch_x_api
from hyperlex.receipt import emit_receipt, verify_receipt
from hyperlex.init_skill import run_init, skill_targets
from hyperlex.claude_sot import resolve_claude_sot_cleared, claude_packaging_claimed

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "install.sh"
SCRIPT = ROOT / "scripts" / "hyperlex.py"


def _fc(fid: str = "p1") -> dict:
    return {
        "forecast_id": fid,
        "receipt_ref": {"integrity": "abc"},
        "signal_key": "lineage.confidence",
        "probability": 0.5,
        "target_event": "t",
        "target_schema": "lineage.family_confirmed",
        "created_at": "2026-08-05T00:00:00+00:00",
        "mapping_version": "v1",
    }


def _load_tx():
    spec = importlib.util.spec_from_file_location(
        "install_transaction_p1", ROOT / "scripts/install_transaction.py"
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# P1-1 init + install helpers
# ---------------------------------------------------------------------------

def test_init_dry_run_writes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("HYPERLEX_HOME", str(home / ".hyperlex"))
    out = run_init(["claude"], dry_run=True)
    assert out["ok"] is True
    assert out["dry_run"] is True
    assert not (home / ".claude").exists()
    dest = skill_targets()["claude"] / "SKILL.md"
    assert not dest.exists()


def test_init_refuses_symlink_dest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    dest = home / ".claude" / "skills" / "hyperlex"
    dest.parent.mkdir(parents=True)
    dest.symlink_to(tmp_path / "elsewhere")
    with pytest.raises(ValueError, match="symlink"):
        run_init(["claude"], dry_run=False)


def test_init_backup_and_skip_smoke_unverified(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("HYPERLEX_HOME", str(home / ".hyperlex"))
    dest = home / ".claude" / "skills" / "hyperlex"
    dest.mkdir(parents=True)
    (dest / "SKILL.md").write_text("old skill", encoding="utf-8")
    out = run_init(["claude"], dry_run=False, skip_smoke=True)
    assert out["written"][0]["status"] == "UNVERIFIED"
    assert (dest / "SKILL.md").read_text(encoding="utf-8") != "old skill"
    assert "backup" in out["written"][0]
    backup = Path(out["written"][0]["backup"])
    assert (backup / "SKILL.md").read_text(encoding="utf-8") == "old skill"


def test_init_smoke_validated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("HYPERLEX_HOME", str(home / ".hyperlex"))
    out = run_init(["claude"], dry_run=False, skip_smoke=False)
    assert out["written"][0]["status"] == "VALIDATED"
    path = Path(out["written"][0]["path"])
    assert path.is_file()
    assert "<!-- hyperlex-init -->" in path.read_text(encoding="utf-8")


def test_install_sh_has_no_raw_helper_copy() -> None:
    text = INSTALL.read_text(encoding="utf-8")
    assert "copy_claude_helpers" not in text
    assert "cp -f" not in text
    assert "install_claude_helpers" in text
    assert "hyperlex-helper" in text
    assert "scripts/install_transaction.py" in text


def test_helper_kind_refuses_symlink_and_backs_up(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tx = _load_tx()
    home = tmp_path / "home"
    profile = tmp_path / "profile"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("HERMES_HOME", str(profile))
    src = tmp_path / "helper"
    src.mkdir()
    (src / "SKILL.md").write_text("# helper\n", encoding="utf-8")
    dest = tmp_path / "dest"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.symlink_to(tmp_path / "other")
    with pytest.raises(ValueError, match="symlink"):
        tx.install(src, dest, "hyperlex-helper", skip_checks=True)


def test_helper_kind_install_and_unverified(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tx = _load_tx()
    home = tmp_path / "home"
    profile = tmp_path / "profile"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("HERMES_HOME", str(profile))
    src = tmp_path / "helper"
    src.mkdir()
    (src / "SKILL.md").write_text("# helper\n", encoding="utf-8")
    dest = tmp_path / "skills" / "hyperlex-demo"
    dest.mkdir(parents=True)
    (dest / "SKILL.md").write_text("old", encoding="utf-8")
    tx.install(src, dest, "hyperlex-helper", skip_checks=True)
    assert (dest / "SKILL.md").read_text(encoding="utf-8") == "# helper\n"
    receipt = json.loads((dest / ".install-provenance.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "UNVERIFIED"


def test_install_sh_claude_dry_run_no_writes(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    env = os.environ.copy()
    env.update({"HOME": str(home), "HERMES_HOME": str(home / "profile"), "HYPERLEX_OFFLINE": "1"})
    result = subprocess.run(
        ["bash", str(INSTALL), "--claude", "--dry-run"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "hyperlex-demo" in result.stdout
    assert "transactional-install Claude helper" in result.stdout
    assert not (home / ".claude").exists()


def test_hermes_install_dry_run_still_ok(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    env = os.environ.copy()
    env.update({"HOME": str(home), "HERMES_HOME": str(home / "profile")})
    result = subprocess.run(
        ["bash", str(INSTALL), "--dry-run"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "would staged-validate then activate Hyperlex" in result.stdout
    assert not (home / "profile" / "skills").exists()


# ---------------------------------------------------------------------------
# P1-2 settle
# ---------------------------------------------------------------------------

def test_settle_refuses_missing_token_non_tty() -> None:
    with pytest.raises(SettleGateError):
        settle(_fc(), outcome_value=1.0, settlement_decision="TRUE", authority_ref="op")


def test_settle_refuses_empty_authority_ref() -> None:
    with pytest.raises(SettleGateError, match="authority.ref"):
        settle(_fc(), outcome_value=1.0, settlement_decision="TRUE", settle_token="tok")


def test_settle_refuses_advisory_kind() -> None:
    with pytest.raises(SettleGateError, match="advisory"):
        settle(
            _fc(),
            outcome_value=1.0,
            settlement_decision="TRUE",
            authority_kind="advisory",
            authority_ref="op",
            settle_token="tok",
        )


def test_settle_refuses_piped_yes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HYPERLEX_SETTLE_TOKEN", raising=False)
    fake_in = io.StringIO("yes\n")
    fake_in.isatty = lambda: False  # type: ignore[method-assign]
    with pytest.raises(SettleGateError, match="non-TTY"):
        require_scored_settle_gate(
            settlement_decision="TRUE",
            authority_kind="operator",
            authority_ref="op",
            settle_token=None,
            stdin=fake_in,
            stdout=io.StringIO(),
        )


def test_settle_tty_confirm_accepts_phrase() -> None:
    fake_in = io.StringIO(SETTLE_CONFIRM_PHRASE + "\n")
    fake_in.isatty = lambda: True  # type: ignore[method-assign]
    require_scored_settle_gate(
        settlement_decision="TRUE",
        authority_kind="operator",
        authority_ref="op",
        settle_token=None,
        stdin=fake_in,
        stdout=io.StringIO(),
    )


def test_settle_and_log_refuses_without_append(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HYPERLEX_SETTLE_TOKEN", raising=False)
    log = tmp_path / "score_log.jsonl"
    log.write_text("", encoding="utf-8")
    with pytest.raises(SettleGateError):
        settle_and_log(
            _fc("nolog"),
            outcome_value=1.0,
            settlement_decision="TRUE",
            authority_ref="op",
            path=log,
        )
    assert log.read_text(encoding="utf-8").strip() == ""


def test_settle_does_not_store_token() -> None:
    st = settle(
        _fc("tok"),
        outcome_value=1.0,
        settlement_decision="TRUE",
        authority_ref="op",
        settle_token="super-secret-token",
    )
    blob = json.dumps(st)
    assert "super-secret-token" not in blob


def test_void_settle_skips_gate() -> None:
    st = settle(_fc("void"), outcome_value=0.0, settlement_decision="VOID")
    assert st["settlement_decision"] == "VOID"


# ---------------------------------------------------------------------------
# P1-3 X API base
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "url",
    [
        "http://api.twitter.com/2",
        "https://user:pass@api.twitter.com/2",
        "https://api.twitter.com:8443/2",
        "https://evil.example/2",
    ],
)
def test_x_api_base_refused(url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HYPERLEX_X_API_BASE_ALLOW_CUSTOM", raising=False)
    with pytest.raises(UrlGateError):
        validate_x_api_base(url)


def test_x_api_base_allowlisted() -> None:
    assert validate_x_api_base("https://api.twitter.com/2") == "https://api.twitter.com/2"
    assert validate_x_api_base("https://api.x.com/2") == "https://api.x.com/2"


def test_fetch_x_api_refuses_before_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYPERLEX_X_API_BASE", "https://evil.example/2")
    monkeypatch.setenv("HYPERLEX_X_BEARER_TOKEN", "secret-bearer")
    monkeypatch.delenv("HYPERLEX_X_API_BASE_ALLOW_CUSTOM", raising=False)
    monkeypatch.delenv("HYPERLEX_OFFLINE", raising=False)

    def boom(*_a, **_k):
        raise AssertionError("request must not fire on refuse")

    monkeypatch.setattr("hyperlex.intake.x_search.requests", type("R", (), {"get": staticmethod(boom)}))
    signal, meta = fetch_x_api("rizz")
    assert "X_API_BASE_REFUSED" in signal
    assert meta["reason"] == "x_api_base_refused"
    assert "secret-bearer" not in signal
    assert "secret-bearer" not in json.dumps(meta)


def test_x_api_custom_override_warns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYPERLEX_X_API_BASE", "https://proxy.example/2")
    monkeypatch.setenv("HYPERLEX_X_API_BASE_ALLOW_CUSTOM", "1")
    monkeypatch.setenv("HYPERLEX_OFFLINE", "1")
    signal, meta = fetch_x_api("rizz")
    assert meta.get("custom_base") is True
    assert "X_OFFLINE" in signal


# ---------------------------------------------------------------------------
# P1-4 cloud write
# ---------------------------------------------------------------------------

def test_cloud_write_refused_without_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HYPERLEX_CLOUD_WRITE", raising=False)
    with pytest.raises(CloudWriteError):
        require_cloud_write()


def test_cloud_write_env_permits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYPERLEX_CLOUD_WRITE", "1")
    require_cloud_write()


def test_cloud_write_env_keys_alone_not_enough(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HYPERLEX_CLOUD_WRITE", raising=False)
    monkeypatch.setenv("CHROMA_API_KEY", "ck")
    monkeypatch.setenv("HYPERLEX_CHROMA_API_KEY", "ck")
    with pytest.raises(CloudWriteError):
        require_cloud_write()


def test_force_cloud_transfer_gated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("HYPERLEX_CLOUD_WRITE", raising=False)
    from hyperlex.vectordb.transfer import open_vector_store

    with pytest.raises(CloudWriteError):
        open_vector_store(backend="chroma", force_cloud=True)


def test_autoindex_cloud_store_gated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HYPERLEX_CLOUD_WRITE", raising=False)
    from hyperlex.vectordb.autoindex import index_texts

    class Cloudish:
        force_cloud = True
        _cloud = True

        def close(self) -> None:
            return None

    out = index_texts(
        [{"id": "t1", "kind": "term", "text": "rizz"}],
        store=Cloudish(),
    )
    assert out["ok"] is False
    assert "cloud vector write refused" in str(out.get("error") or "")


# ---------------------------------------------------------------------------
# P1-5 doctor SoT
# ---------------------------------------------------------------------------

def test_claude_sot_pin_matches_this_tree() -> None:
    cleared, reason = resolve_claude_sot_cleared(ROOT)
    assert cleared is True, reason
    assert "pinned" in reason


def test_claude_sot_missing_pin(tmp_path: Path) -> None:
    cleared, reason = resolve_claude_sot_cleared(tmp_path)
    assert cleared is False
    assert "no local pin" in reason


def test_doctor_emits_claude_sot_cleared() -> None:
    env = os.environ.copy()
    env["HYPERLEX_OFFLINE"] = "1"
    env["HYPERLEX_NO_RATE_LIMIT"] = "1"
    env["PYTHONPATH"] = str(ROOT / "src")
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "doctor"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    body = json.loads(r.stdout)
    assert "CLAUDE_SOT_CLEARED" in body
    assert body["CLAUDE_SOT_CLEARED"] is True
    names = {c["name"] for c in body["checks"]}
    assert "claude_sot_cleared" in names
    sot = next(c for c in body["checks"] if c["name"] == "claude_sot_cleared")
    assert sot["message"].startswith("CLAUDE_SOT_CLEARED=")


def test_claude_sot_missing_pin_object_is_uncleared(tmp_path: Path) -> None:
    """Shallow / unrelated clones cannot prove descent without a live fetch."""
    import shutil

    repo = tmp_path / "repo"
    repo.mkdir()
    pin_src = ROOT / "references" / "claude-sot-cleared.json"
    dest_dir = repo / "references"
    dest_dir.mkdir()
    shutil.copy(pin_src, dest_dir / "claude-sot-cleared.json")
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "p1@test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "p1"], cwd=repo, check=True)
    subprocess.run(["git", "add", "references/claude-sot-cleared.json"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "pin only"], cwd=repo, check=True, capture_output=True)
    cleared, reason = resolve_claude_sot_cleared(repo)
    assert cleared is False
    assert "not in local git objects" in reason


def test_doctor_fails_when_claimed_and_uncleared(tmp_path: Path) -> None:
    home = tmp_path / "home"
    skill = home / ".claude" / "skills" / "hyperlex"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# x\n", encoding="utf-8")
    (skill / "scripts").mkdir()
    (skill / "scripts" / "hyperlex.py").write_text("# stub\n", encoding="utf-8")
    assert claude_packaging_claimed(home=home) is True
    empty = tmp_path / "empty-root"
    empty.mkdir()
    cleared, reason = resolve_claude_sot_cleared(empty)
    assert cleared is False
    assert "no local pin" in reason
    from hyperlex.claude_sot import doctor_sot_should_fail

    assert doctor_sot_should_fail(cleared=False, claimed=True) is True
    assert doctor_sot_should_fail(cleared=True, claimed=True) is False
    assert doctor_sot_should_fail(cleared=False, claimed=False) is False


# ---------------------------------------------------------------------------
# P1-6 receipt sha256
# ---------------------------------------------------------------------------

def test_emit_receipt_full_sha256_and_validate_default(tmp_path: Path) -> None:
    from hyperlex import detect_memetic_patterns

    result = detect_memetic_patterns(query="rizz", ingest_source="mock", validate=False)
    path = emit_receipt(result, out_dir=tmp_path, append_ledger=False)
    payload = json.loads(path.read_text(encoding="utf-8"))
    integ = payload["receipt"]["integrity"]
    assert len(integ) == 64
    assert all(c in "0123456789abcdef" for c in integ)
    assert "schema_validation" in payload["receipt"]
    ok, msg = verify_receipt(payload)
    assert ok, msg


def test_legacy_short_digest_refused_without_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HYPERLEX_RECEIPT_LEGACY_INTEGRITY", raising=False)
    from hyperlex import detect_memetic_patterns

    result = detect_memetic_patterns(query="rizz", ingest_source="mock", validate=False)
    path = emit_receipt(result, out_dir=tmp_path, append_ledger=False, validate=False)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["receipt"]["integrity"] = payload["receipt"]["integrity"][:12]
    ok, msg = verify_receipt(payload)
    assert ok is False
    assert "mismatch" in msg


def test_legacy_short_digest_ok_with_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYPERLEX_RECEIPT_LEGACY_INTEGRITY", "1")
    from hyperlex import detect_memetic_patterns

    result = detect_memetic_patterns(query="rizz", ingest_source="mock", validate=False)
    path = emit_receipt(result, out_dir=tmp_path, append_ledger=False, validate=False)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["receipt"]["integrity"] = payload["receipt"]["integrity"][:12]
    ok, msg = verify_receipt(payload)
    assert ok is True
    assert "legacy" in msg


def test_http_scheme_allowlist() -> None:
    require_http_url("https://api.openai.com/v1", name="HYPERLEX_LLM_BASE_URL")
    require_http_url("http://localhost:8080/v1", name="HYPERLEX_LLM_BASE_URL")
    with pytest.raises(UrlGateError):
        require_http_url("file:///etc/passwd", name="HYPERLEX_LLM_BASE_URL")
