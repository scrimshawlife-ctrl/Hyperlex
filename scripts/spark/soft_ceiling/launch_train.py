#!/usr/bin/env python3
"""Launch one Spark train container from a recorded env JSON. Canonical.

Replaces the per-morph ``launch()`` in the archived launchers. Refuses if a
train container is already running, if ``HYPERLEX_ALLOW_TRAIN`` is not ``1``,
or if the output directory already holds a train receipt.

  python scripts/spark/soft_ceiling/launch_train.py --env ENV.json --tag rc1 [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

HOME = Path("/home/morpheus")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
MOUNTS = (".cache", "hlx", "Hyperlex", ".hyperlex")


def build_cmd(env: dict, name: str, repo: Path) -> list[str]:
    cmd = ["docker", "run", "-d", "--name", name, "--gpus", "all", "-w", str(repo)]
    for m in MOUNTS:
        cmd += ["-v", f"{HOME / m}:{HOME / m}"]
    base = {
        "HOME": str(HOME),
        "PYTHONPATH": "scripts/shadow",
        "PYTHONUNBUFFERED": "1",
        "TOKENIZERS_PARALLELISM": "false",
        "HF_HUB_OFFLINE": "1",
        "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
        "XDG_CACHE_HOME": str(HOME / ".cache"),
        "TRITON_CACHE_DIR": str(HOME / ".cache" / "triton"),
        "TORCHINDUCTOR_CACHE_DIR": str(HOME / ".cache" / "inductor"),
    }
    for k, v in {**base, **env}.items():
        cmd += ["-e", f"{k}={v}"]
    frac = str(env.get("HYPERLEX_CUDA_MEM_FRACTION", "0.3"))
    cmd += [IMAGE, "python", str(repo / "scripts" / "spark" / "guard.py"), frac, "hyperlexical.train", "--offline", "--run", "--include-live"]
    return cmd


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--env", required=True)
    p.add_argument("--tag", required=True)
    p.add_argument("--repo", default=str(HOME / "Hyperlex"))
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    env = json.loads(Path(args.env).read_text())
    if env.get("HYPERLEX_ALLOW_TRAIN") != "1":
        raise SystemExit("REFUSE: HYPERLEX_ALLOW_TRAIN must be 1 in the recorded env")
    out = Path(env["HYPERLEX_TRAIN_OUT"])
    if (out / "train-receipt.json").exists():
        raise SystemExit(f"REFUSE: {out} already has a train receipt")
    running = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True, check=True).stdout
    busy = [n for n in running.split() if n.startswith("hlx-")]
    if busy:
        raise SystemExit(f"REFUSE: GPU job running: {busy}")
    name = f"hlx-train-{args.tag}-{int(time.time())}"
    cmd = build_cmd(env, name, Path(args.repo))
    if args.dry_run:
        print(json.dumps({"name": name, "cmd": cmd}, indent=2))
        return 0
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run(cmd, check=True)
    (HOME / "hlx" / "last-train-container").write_text(name + "\n")
    print(json.dumps({"launched": name, "out": str(out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
