"""SELECT-006 admission-only. Launch is armed only for this overlay. No training."""

from __future__ import annotations

import hashlib
import io
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path("/home/morpheus/Hyperlex")
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.select_006_admission import (  # noqa: E402
    BEST_SHA256,
    BEST_WEIGHTS,
    COMBINED_WITNESS_SHA256,
    EXPERIMENT_ID,
    LEDGER,
    LEDGER_EVENTS_SHA256,
    LEDGER_PROJECTION_SHA256,
    RESERVE_MANIFEST_SHA256,
    SPEC,
    THRESHOLD,
    VERIFIED,
    WARM_START_SHA256,
)
from hyperlexical.select_006_efficiency_preservation import (  # noqa: E402
    TRUNK_DIR,
    TRUNK_SHA256,
    WARM_START_DIR,
)

OUT = Path("/home/morpheus/hlx-private/exp-20260929-select-006/admission-only-001")
TRAIN_OUT = Path("/tmp/select006-admission-only-out-41af")
BINDING = Path(
    "/home/morpheus/hlx-private/exp-20260929-select-006/zero-init-loader-001/RESERVE_BINDING_FOR_INIT_DRY_RUN.json"
)
MANIFEST = Path(
    "/home/morpheus/hlx-private/exp-20260929-select-006/reserve-acquisition-002/RESERVE_MANIFEST.json"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fail(code: str, detail: str) -> None:
    raise SystemExit(f"{code}: {detail}")


def _pins() -> dict[str, str]:
    return {
        "best_sha256": _sha256(Path(BEST_WEIGHTS)),
        "ledger_events_sha256": _sha256(LEDGER / "events.jsonl"),
        "ledger_projection_sha256": _sha256(LEDGER / "ledger.json"),
        "reserve_manifest_sha256": _sha256(MANIFEST),
        "warm_start_sha256": _sha256(Path(WARM_START_DIR) / "model.safetensors"),
    }


def _arm() -> None:
    os.environ["HLX_EXPERIMENT_ID"] = EXPERIMENT_ID
    os.environ["HLX_SCHEDULE_ARM"] = "candidate"
    os.environ["HLX_BASELINE_ENV"] = str(SPEC / "BASELINE_ENV.json")
    os.environ["HLX_CANDIDATE_ENV"] = str(SPEC / "CANDIDATE_ENV.json")
    for name in ("BASELINE_ENV.json", "CANDIDATE_ENV.json"):
        payload = json.loads((SPEC / name).read_text(encoding="utf-8"))
        for key, value in payload.items():
            os.environ[key] = str(value)
    os.environ["HYPERLEX_ALLOW_TRAIN"] = "1"
    os.environ["HLX_ADMISSION_ONLY"] = "1"
    os.environ["HLX_THRESHOLD_AUTHORIZATION"] = str(THRESHOLD)
    os.environ["HLX_EVAL_RESERVE_LEDGER"] = str(LEDGER)
    os.environ["HLX_RESERVE_BINDING"] = str(BINDING)
    os.environ["HLX_BEST_SHA256"] = BEST_SHA256
    os.environ["HLX_BEST_WEIGHTS"] = BEST_WEIGHTS
    os.environ["HLX_TRUNK_SHA256"] = TRUNK_SHA256
    os.environ["HYPERLEX_TRUNK_DIR"] = str(TRUNK_DIR)
    os.environ["HYPERLEX_TRAIN_OUT"] = str(TRAIN_OUT)
    os.environ.pop("HLX_HOLDOUT_MANIFESTS", None)
    os.environ.pop("HLX_ALLOW_NO_HOLDOUT", None)
    os.environ.pop("HYPERLEX_INCLUDE_LIVE", None)


def main() -> None:
    if TRAIN_OUT.exists():
        _fail("ADMISSION_ONLY_GUARD_FAILURE", "training output directory already exists")
    if os.environ.get("HYPERLEX_ALLOW_TRAIN") == "1" and os.environ.get("HLX_ADMISSION_ONLY") != "1":
        _fail("ADMISSION_ONLY_GUARD_FAILURE", "launch armed without the admission-only overlay")
    before = _pins()
    expected = {
        "best_sha256": BEST_SHA256,
        "ledger_events_sha256": LEDGER_EVENTS_SHA256,
        "ledger_projection_sha256": LEDGER_PROJECTION_SHA256,
        "reserve_manifest_sha256": RESERVE_MANIFEST_SHA256,
        "warm_start_sha256": WARM_START_SHA256,
    }
    for key, value in expected.items():
        if before[key] != value:
            _fail("ADMISSION_PIN_MISMATCH", key)
    _arm()
    if os.environ.get("HYPERLEX_ALLOW_TRAIN") != "1" or os.environ.get("HLX_ADMISSION_ONLY") != "1":
        _fail("ADMISSION_ONLY_GUARD_FAILURE", "admission-only environment was not armed")
    from hyperlexical.train import main as train_main

    buffer = io.StringIO()
    try:
        with redirect_stdout(buffer):
            code = train_main(["--run"])
    except SystemExit as exc:
        receipt = getattr(exc, "receipt", None)
        if receipt is not None:
            print(json.dumps(receipt, indent=2, sort_keys=True))
        raise
    if code != 0:
        _fail("ADMISSION_FAILURE", f"trainer exited {code}")
    if TRAIN_OUT.exists():
        _fail("ADMISSION_ONLY_GUARD_FAILURE", "training output directory was created")
    receipt = json.loads(buffer.getvalue())
    if receipt.get("admission_result") != "ADMISSION_PASS" or receipt.get("status") != "TRAINING_READY":
        _fail("ADMISSION_FAILURE", "admission did not reach TRAINING_READY")
    if receipt.get("ready_to_train") is not True:
        _fail("ADMISSION_FAILURE", "ready_to_train")
    if receipt.get("training_launch_authorized") is not False or receipt.get("training_started") is not False:
        _fail("ADMISSION_ONLY_GUARD_FAILURE", "launch or training was persisted")
    if receipt.get("optimizer_loaded") is not False or receipt.get("epochs") != 0 or receipt.get("gradient_steps") != 0:
        _fail("ADMISSION_ONLY_GUARD_FAILURE", "optimizer or steps")
    if receipt.get("execution_loader_status") != VERIFIED:
        _fail("ADMISSION_LOADER_NOT_VERIFIED", "execution loader")
    if receipt.get("expanded_loader_witness_sha256") != COMBINED_WITNESS_SHA256:
        _fail("ADMISSION_ZERO_INIT_WITNESS_MISMATCH", "combined witness")
    after = _pins()
    if after != before:
        _fail("ADMISSION_RESERVE_FAILURE", "pinned artifact changed during admission")
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "ADMISSION_RECEIPT.json"
    target.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "admission_reason": receipt.get("admission_reason"),
        "admission_result": receipt.get("admission_result"),
        "execution_loader_status": receipt.get("execution_loader_status"),
        "ready_to_train": receipt.get("ready_to_train"),
        "receipt_sha256": _sha256(target),
        "status": receipt.get("status"),
        "training_launch_authorized": receipt.get("training_launch_authorized"),
        "training_started": receipt.get("training_started"),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
