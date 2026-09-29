"""One Classification v2 training run. Does not move BEST and does not open a SELECT id."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
EXPORT = Path(
    "/home/morpheus/hlx-private/classification-v2-acquire-20260929/civilian.v0.1.jsonl"
)
EXPORT_SHA = "aa21415adab0c6ea488c7bdc3ea5495d20126017a094a5df33406f30eccd7e3e"
EXPORT_ROWS = 9263
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
INIT_FROM = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004"
)
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
OUT = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-classification-v2"
)
PRIVATE = Path("/home/morpheus/hlx-private/classification-v2-train-20260929")
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
BEST_LINK = Path("/home/morpheus/.hyperlex/models/BEST")

sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sudo_sha256(path: Path) -> str:
    completed = subprocess.run(
        ["sudo", "-n", "sha256sum", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.split()[0]


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def write_private(path: Path, payload: dict) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def preflight() -> dict:
    if sha256_file(EXPORT) != EXPORT_SHA:
        fail("export digest mismatch")
    rows = []
    with EXPORT.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    if len(rows) != EXPORT_ROWS:
        fail(f"export row count {len(rows)} != {EXPORT_ROWS}")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if not BEST_LINK.is_symlink() or BEST_LINK.resolve() != INIT_FROM.resolve():
        fail("BEST symlink is not the production checkpoint")
    if OUT.exists():
        fail(f"output already exists: {OUT}")
    if OUT.resolve() == INIT_FROM.resolve() or OUT.resolve() == BEST_LINK.resolve():
        fail("output resolves to BEST")
    if not (TRUNK / "config.json").is_file():
        fail("trunk config missing")
    if not (INIT_FROM / "model.safetensors").is_file():
        fail("warm start weights missing")
    from hyperlexical.holdout_guard import normalized_text_sha256
    from hyperlexical.identity_ledger import (
        IdentityLedger,
        assert_training_disjoint_from_reserve,
        derived_state,
    )

    ledger = IdentityLedger.load(LEDGER)
    assert_training_disjoint_from_reserve(rows, ledger)
    fresh = [row for row in rows if isinstance(row.get("provenance"), dict) and row["provenance"].get("evidence_seal")]
    if len(fresh) != 113:
        fail(f"fresh evidence rows {len(fresh)} != 113")
    reserve_states = {"EVAL_RESERVE", "EVAL_SPENT", "EVAL_ABANDONED", "EVAL_BOUND"}
    for row in fresh:
        digest = normalized_text_sha256(str(row.get("text") or ""))
        record = ledger.identity(digest)
        if record is None or derived_state(record) != "TRAIN_CONSUMED":
            fail("fresh row is not TRAIN_CONSUMED")
        if derived_state(record) in reserve_states:
            fail("fresh row is reserved")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if dirty:
        fail("trainer tree is dirty")
    return {
        "best_sha256": BEST_SHA,
        "best_unchanged": True,
        "export_rows": EXPORT_ROWS,
        "export_sha256": EXPORT_SHA,
        "fresh_observed_rows": len(fresh),
        "git_head": head,
        "init_expand_vocab": True,
        "init_from": str(INIT_FROM),
        "jev": "OFF",
        "moves_best": False,
        "output": str(OUT),
        "schedule": "select-006-candidate",
        "trainer_commit": head,
    }


def docker_env() -> dict[str, str]:
    return {
        "HF_HUB_OFFLINE": "1",
        "HLX_ALLOW_NO_HOLDOUT": "1",
        "HLX_TRAIN_EXPORT_PATH": str(EXPORT),
        "HLX_TRAIN_EXPORT_ROWS": str(EXPORT_ROWS),
        "HLX_TRAIN_EXPORT_SHA256": EXPORT_SHA,
        "HOME": "/home/morpheus",
        "HYPERLEX_ALLOW_TRAIN": "1",
        "HYPERLEX_CLASSIFICATION": "v2",
        "HYPERLEX_EXPORT_DIR": str(PRIVATE / "export"),
        "HYPERLEX_FILLER_FILTER": "strict",
        "HYPERLEX_INIT_EXPAND_VOCAB": "1",
        "HYPERLEX_INIT_FROM": str(INIT_FROM),
        "HYPERLEX_LAST_TRAINABLE": "2",
        "HYPERLEX_TRAIN_BATCH": "8",
        "HYPERLEX_TRAIN_LR": "2e-5",
        "HYPERLEX_TRAIN_OUT": str(OUT),
        "HYPERLEX_TRUNK_DIR": str(TRUNK),
        "HYPERLEX_UNBIND_CURRICULUM": "0",
        "HYPERLEX_UNBIND_EVERY_N": "1",
        "HYPERLEX_UNBIND_LOSS_WEIGHT": "1.0",
        "HYPERLEX_UNBIND_PRIMARY": "mixed",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": "/home/morpheus/Hyperlex/scripts/shadow",
        "PYTHONUNBUFFERED": "1",
        "TRANSFORMERS_OFFLINE": "1",
    }


def main() -> int:
    pins = preflight()
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(PRIVATE, 0o700)
    write_private(PRIVATE / "LAUNCH.json", {"schema": "hyperlex.classification.v2.launch.v1", **pins, "env": docker_env()})
    command = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "--name",
        "hlx-classification-v2-train",
        "-v",
        "/home/morpheus/Hyperlex:/home/morpheus/Hyperlex",
        "-v",
        "/home/morpheus/hlx-private:/home/morpheus/hlx-private",
        "-v",
        "/home/morpheus/.hyperlex:/home/morpheus/.hyperlex",
        "-w",
        "/home/morpheus/Hyperlex",
        "-e",
        "HOME=/home/morpheus",
        "-e",
        "HF_HUB_OFFLINE=1",
        "-e",
        "PYTHONDONTWRITEBYTECODE=1",
        "-e",
        "PYTHONPATH=/home/morpheus/Hyperlex/scripts/shadow",
        "-e",
        "PYTHONUNBUFFERED=1",
        "-e",
        "TRANSFORMERS_OFFLINE=1",
    ]
    for key, value in sorted(docker_env().items()):
        if key in {"HOME", "HF_HUB_OFFLINE", "PYTHONDONTWRITEBYTECODE", "PYTHONPATH", "PYTHONUNBUFFERED", "TRANSFORMERS_OFFLINE"}:
            continue
        command.extend(["-e", f"{key}={value}"])
    command.extend([IMAGE, "python", "-u", "-m", "hyperlexical.train", "--run"])
    log_path = PRIVATE / "train.log"
    print(json.dumps({"launching": str(OUT), "log": str(log_path)}, sort_keys=True), flush=True)
    with log_path.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, check=False)
    write_private(PRIVATE / "EXIT.json", {"code": completed.returncode})
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed during training")
    if completed.returncode != 0:
        fail(f"trainer exit {completed.returncode}")
    print(json.dumps({"trainer_exit": 0, "output": str(OUT)}, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
