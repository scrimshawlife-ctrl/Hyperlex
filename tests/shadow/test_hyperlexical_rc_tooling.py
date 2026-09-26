import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPARK = ROOT / "scripts" / "spark" / "soft_ceiling"
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))
sys.path.insert(0, str(SPARK))

import launch_train  # noqa: E402
from score_holdout import copy_baseline, macro_f1  # noqa: E402


def test_rc1_env_is_cold_strict_release():
    env = json.loads((SPARK / "rc1-train-env.json").read_text())
    assert "HYPERLEX_INIT_FROM" not in env and "HYPERLEX_INIT_EXPAND_VOCAB" not in env
    assert env["HYPERLEX_FILLER_FILTER"] == "strict"
    assert env["HYPERLEX_RELEASE_SET"] == "1"
    assert env["HYPERLEX_ALLOW_TRAIN"] == "1"
    assert env["HYPERLEX_TRAIN_OUT"].endswith("seed-rc1")
    assert env["HYPERLEX_EXPORT_DIR"].startswith(env["HYPERLEX_TRAIN_OUT"])
    base = json.loads((SPARK / "morph78-train-env.json").read_text())
    same = {k for k in base if k in env and base[k] == env[k]}
    assert {"HYPERLEX_TRAIN_EPOCHS", "HYPERLEX_UNBIND_OBSERVED_UPSAMPLE", "HYPERLEX_LAST_TRAINABLE", "HYPERLEX_TASK_ROUTING"} <= same


def test_launch_cmd_shape():
    env = {"HYPERLEX_ALLOW_TRAIN": "1", "HYPERLEX_TRAIN_OUT": "/x", "HYPERLEX_CUDA_MEM_FRACTION": "0.3"}
    cmd = launch_train.build_cmd(env, "hlx-train-rc1-1", pathlib.Path("/home/morpheus/Hyperlex"))
    i = cmd.index("lmsysorg/sglang:dev-qwen38-27b-dflash2")
    assert cmd[i + 1 :] == ["python", "/home/morpheus/Hyperlex/scripts/spark/guard.py", "0.3", "hyperlexical.train", "--offline", "--run", "--include-live"]
    assert "HYPERLEX_ALLOW_TRAIN=1" in cmd and "HF_HUB_OFFLINE=1" in cmd


def test_score_helpers():
    assert macro_f1([0, 1, 1], [0, 1, 0]) == (2 / 3 + 2 / 3) / 2
    rows = [
        {"text": "no cap", "fillers": ["no", "cap"]},
        {"text": "TOKEN:rizz SLOT:up", "fillers": ["rizz", "up"]},
        {"text": "bet", "fillers": ["that"]},
    ]
    assert copy_baseline(rows) == 2 / 3
    assert copy_baseline([]) is None

def test_rc2_env_is_cold_strict_release_with_holdout_guard():
    env = json.loads((SPARK / "rc2-train-env.json").read_text())
    assert env["HYPERLEX_ALLOW_TRAIN"] == "1"
    assert env["HYPERLEX_FILLER_FILTER"] == "strict"
    assert env["HYPERLEX_RELEASE_SET"] == "1"
    assert "HYPERLEX_INIT_FROM" not in env
    assert env["HYPERLEX_TRAIN_OUT"].endswith("seed-rc2")
    assert "holdout-manifest-rc2.json" in env["HLX_HOLDOUT_MANIFESTS"]
    assert env["HLX_FORCE_TRAIN_DISJOINT"] == "1"
    assert env.get("HLX_ALLOW_NO_HOLDOUT") in (None, "", "0")
