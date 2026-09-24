import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical import provenance as prov


def _repo(tmp_path, head, refs=None, packed=None):
    git = tmp_path / ".git"
    (git / "refs" / "heads").mkdir(parents=True)
    (git / "HEAD").write_text(head)
    for name, sha in (refs or {}).items():
        (git / "refs" / "heads" / name).write_text(sha + "\n")
    if packed:
        (git / "packed-refs").write_text(packed)
    return tmp_path


def test_commit_from_loose_ref(tmp_path):
    root = _repo(tmp_path, "ref: refs/heads/main\n", {"main": "a" * 40})
    assert prov.code_commit(root) == "a" * 40


def test_commit_from_packed_ref(tmp_path):
    root = _repo(tmp_path, "ref: refs/heads/main\n", packed=f"# pack\n{'b' * 40} refs/heads/main\n")
    assert prov.code_commit(root) == "b" * 40


def test_detached_head_and_no_git(tmp_path):
    root = _repo(tmp_path, "c" * 40 + "\n")
    assert prov.code_commit(root) == "c" * 40
    assert prov.code_commit(tmp_path / "missing") is None


def test_tree_hash_changes_on_edit(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "a.py").write_text("x = 1\n")
    before = prov.code_tree_sha256(pkg)
    (pkg / "a.py").write_text("x = 2\n")
    assert prov.code_tree_sha256(pkg) != before


def test_env_snapshot_only_hyperlex():
    snap = prov.env_snapshot({"HYPERLEX_A": "1", "HOME": "/x", "HYPERLEX_B": "2"})
    assert snap == {"HYPERLEX_A": "1", "HYPERLEX_B": "2"}


def test_repo_provenance_shape():
    out = prov.provenance(ROOT)
    assert set(out) == {"code_commit", "code_tree_sha256", "hyperlex_env"}
    assert len(out["code_tree_sha256"]) == 64


def test_worktree_commondir_and_missing_gitdir(tmp_path):
    main = tmp_path / "main" / ".git"
    (main / "refs" / "heads").mkdir(parents=True)
    (main / "refs" / "heads" / "feat").write_text("d" * 40 + "\n")
    wt_git = main / "worktrees" / "wt"
    wt_git.mkdir(parents=True)
    (wt_git / "HEAD").write_text("ref: refs/heads/feat\n")
    (wt_git / "commondir").write_text("../..\n")
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / ".git").write_text(f"gitdir: {wt_git}\n")
    assert prov.code_commit(wt) == "d" * 40
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / ".git").write_text("gitdir: /nonexistent/path\n")
    assert prov.code_commit(broken) is None
