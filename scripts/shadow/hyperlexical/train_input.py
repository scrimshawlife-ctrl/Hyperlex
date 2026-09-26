"""Training-input contract. Live rebuild versus an exact pinned export.

RUNE.TRAIN_INPUT_BIND(x) =
    experiment_id_present
    AND export_path_present
    AND expected_export_digest_present
    AND export_file_exists
    AND actual_export_digest == expected_export_digest
    AND trainer_source == PINNED_EXPORT

A controlled experiment (``HLX_EXPERIMENT_ID`` set) that fails any term
stops before training and does not call ``export_dataset``. Outside a
controlled experiment, an absent pin keeps ``LIVE_BUILD``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any, Callable

LIVE_BUILD = "LIVE_BUILD"
PINNED_EXPORT = "PINNED_EXPORT"

PATH_ENV = "HLX_TRAIN_EXPORT_PATH"
SHA_ENV = "HLX_TRAIN_EXPORT_SHA256"
ROWS_ENV = "HLX_TRAIN_EXPORT_ROWS"
EXPERIMENT_ID_ENV = "HLX_EXPERIMENT_ID"


class TrainInputAdmissionError(SystemExit):
    """Fail closed before training. ``SystemExit`` so the CLI does not swallow it."""


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


def pinned_request() -> tuple[str, str, int | None]:
    """Return ``(path, expected_sha256, expected_rows)``. Rows are optional."""
    path = _env(PATH_ENV)
    digest = _env(SHA_ENV)
    raw_rows = _env(ROWS_ENV)
    expected_rows: int | None = None
    if raw_rows:
        if not raw_rows.isdigit():
            raise TrainInputAdmissionError(
                f"ADMISSION FAIL: {ROWS_ENV} must be a non-negative integer"
            )
        expected_rows = int(raw_rows)
    return path, digest, expected_rows


def peek_train_input_mode() -> str:
    """Env-only admission. Does not read an export or call ``export_dataset``.

    Incomplete pins fail closed. A controlled experiment with no pin fails
    closed. Neither case falls through to ``LIVE_BUILD``.
    """
    experiment_id = _env(EXPERIMENT_ID_ENV)
    path, digest, _expected_rows = pinned_request()
    if experiment_id and (not path or not digest):
        raise TrainInputAdmissionError(
            "ADMISSION FAIL: experiment id present but no pinned export"
        )
    if path or digest:
        if not path or not digest:
            raise TrainInputAdmissionError(
                "ADMISSION FAIL: pinned export requires "
                f"{PATH_ENV} and {SHA_ENV}"
            )
        return PINNED_EXPORT
    return LIVE_BUILD


def _digest_matches(actual: str, expected: str) -> bool:
    if len(actual) != len(expected):
        return False
    return hmac.compare_digest(actual, expected)


def _load_pinned(path: Path, expected: str, expected_rows: int | None) -> dict[str, Any]:
    if not path.is_file():
        raise TrainInputAdmissionError(f"ADMISSION FAIL: pinned export missing: {path}")
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if not _digest_matches(actual, expected):
        raise TrainInputAdmissionError(
            "ADMISSION FAIL: pinned export digest mismatch: "
            f"expected {expected} actual {actual}"
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TrainInputAdmissionError(
            "ADMISSION FAIL: pinned export is not UTF-8 JSONL"
        ) from exc
    rows: list[Any] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise TrainInputAdmissionError(
                "ADMISSION FAIL: pinned export is not JSONL"
            ) from exc
    if expected_rows is not None and len(rows) != expected_rows:
        raise TrainInputAdmissionError(
            "ADMISSION FAIL: pinned export row count mismatch: "
            f"expected {expected_rows} actual {len(rows)}"
        )
    return {
        "rows": rows,
        "sha256": actual,
        "counts": {"n": len(rows), "live_included": 0},
        "payload": text,
        "train_input": {
            "mode": PINNED_EXPORT,
            "path": str(path.resolve()),
            "sha256_expected": expected,
            "sha256_actual": actual,
            "rows": len(rows),
            "live_export_generation_enabled": False,
        },
    }


def _tag_live(bundle: dict[str, Any]) -> dict[str, Any]:
    rows = bundle.get("rows") or []
    digest = bundle.get("sha256")
    bundle["train_input"] = {
        "mode": LIVE_BUILD,
        "path": None,
        "sha256_expected": None,
        "sha256_actual": digest,
        "rows": len(rows),
        "live_export_generation_enabled": True,
    }
    return bundle


def load_training_bundle(
    root: Path,
    *,
    include_live: bool,
    live_store: Path | None,
    export_dataset: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    """Return the bundle ``run_loop`` trains on.

    ``PINNED_EXPORT`` reads the sealed file and does not call ``export_dataset``.
    ``LIVE_BUILD`` is the existing generator, including ``include_live``.
    """
    mode = peek_train_input_mode()
    if mode == PINNED_EXPORT:
        path, digest, expected_rows = pinned_request()
        return _load_pinned(Path(path), digest, expected_rows)
    bundle = export_dataset(root, include_live=include_live, live_store=live_store)
    return _tag_live(bundle)


def train_input_receipt(bundle: dict[str, Any]) -> dict[str, Any]:
    """Fields copied onto the train receipt. Digest is the artifact actually loaded."""
    info = bundle.get("train_input") or {}
    mode = info.get("mode") or LIVE_BUILD
    actual = info.get("sha256_actual")
    if actual is None:
        actual = bundle.get("sha256")
    rows = info.get("rows")
    if rows is None:
        rows = len(bundle.get("rows") or [])
    generated = info.get("live_export_generation_enabled")
    if generated is None:
        generated = mode == LIVE_BUILD
    return {
        "data_sha256": actual if mode == PINNED_EXPORT else bundle.get("sha256", actual),
        "training_input_mode": mode,
        "training_export_path": info.get("path"),
        "training_export_sha256_expected": info.get("sha256_expected"),
        "training_export_sha256_actual": actual,
        "training_export_rows": rows,
        "live_export_generation_enabled": bool(generated),
    }
