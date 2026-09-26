"""Fixtures for controlled-experiment admission tests. Not collected by pytest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from hyperlexical.holdout_guard import normalized_text_sha256
from hyperlexical.identity_ledger import IdentityLedger, derived_state
from hyperlexical.selection_surface import row_id


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def write_jsonl(path: Path, rows: list[dict]) -> str:
    payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    path.write_text(payload, encoding="utf-8")
    return sha256_bytes(path.read_bytes())


def classify_row(text: str, *, split: str = "train") -> dict:
    return {
        "text": text,
        "task": "classify",
        "split": split,
        "class": "OBSERVED",
        "lineage": "none",
        "role_scheme": "positional",
    }


def _label_row(text: str, label: dict) -> dict:
    return {
        "text": text,
        "task": label["task"],
        "split": label.get("split") or "val",
        "class": label.get("class") or "",
        "lineage": label.get("lineage") or "",
        "role_scheme": "positional",
    }


def seal_reserve(
    root: Path,
    *,
    experiment_id: str,
    extra: list[tuple[str, dict]] | None = None,
) -> dict:
    """Four-slice EVAL_RESERVE ledger plus a binding file. No training rows."""
    labels = [
        (
            "reserve classify surface",
            {
                "task": "classify",
                "class": "OBSERVED",
                "lineage": "gaming-meta",
                "split": "val",
            },
        ),
        (
            "reserve unbind surface",
            {
                "task": "unbind",
                "class": "INFERRED",
                "lineage": "none",
                "split": "val",
                "unbind_clean": True,
            },
        ),
    ]
    labels.extend(extra or [])
    ledger = IdentityLedger()
    for text, label in labels:
        row = _label_row(text, label)
        digest = normalized_text_sha256(text)
        ledger.observe(
            digest,
            source_artifact="fixture",
            row_ids=[row_id(row)],
            labels=[label],
            provenance="fixture",
            experiment_id=experiment_id,
        )
        ledger.transition(
            digest,
            "EVAL_RESERVE",
            source_artifact="fixture",
            provenance="fixture",
        )
    ledger_dir = root / "ledger"
    ledger.save(ledger_dir)
    events_sha = sha256_bytes((ledger_dir / "events.jsonl").read_bytes())
    reserved = [
        record
        for record in ledger.identities.values()
        if derived_state(record) == "EVAL_RESERVE"
    ]
    binding = {
        "schema": "hyperlex.reserve_binding.v1",
        "experiment_id": experiment_id,
        "ledger_events_sha256": events_sha,
        "counts": ledger.reserve_counts(),
        "identities": len(reserved),
        "lifecycle": "EVAL_RESERVE",
    }
    binding_path = root / "reserve-binding.json"
    binding_path.write_text(json.dumps(binding, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"ledger": ledger_dir, "binding": binding_path, "counts": binding["counts"]}


def write_weights(path: Path, payload: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return sha256_bytes(payload)


def arm_controlled(
    monkeypatch,
    tmp_path: Path,
    rows: list[dict],
    *,
    experiment_id: str = "HLX-EXP-TEST",
    extra_reserve: list[tuple[str, dict]] | None = None,
    candidate_extra: dict | None = None,
    best_sha: str | None = None,
    trunk_sha: str | None = None,
    create_output: bool = False,
) -> dict:
    """Launch environment for one controlled experiment. Output stays absent unless asked."""
    pinned = tmp_path / "pinned.jsonl"
    digest = write_jsonl(pinned, rows)
    reserve = seal_reserve(tmp_path, experiment_id=experiment_id, extra=extra_reserve)
    trunk = tmp_path / "trunk"
    trunk.mkdir()
    (trunk / "config.json").write_text("{}
", encoding="utf-8")
    actual_trunk = write_weights(trunk / "model.safetensors", b"trunk-weights")
    actual_best = write_weights(tmp_path / "best.safetensors", b"best-weights")
    out = tmp_path / "train-out"
    if create_output:
        out.mkdir()
    baseline = {"HYPERLEX_FILLER_FILTER": "off"}
    candidate = {
        "HYPERLEX_FILLER_FILTER": "off",
        "HLX_SELECT_METRIC": "classify_macro_f1_nonnone",
        "HLX_EXPERIMENT_ID": experiment_id,
        "HYPERLEX_TRAIN_OUT": str(out),
    }
    if candidate_extra:
        candidate.update(candidate_extra)
    baseline_path = tmp_path / "baseline-env.json"
    candidate_path = tmp_path / "candidate-env.json"
    baseline_path.write_text(json.dumps(baseline, sort_keys=True), encoding="utf-8")
    candidate_path.write_text(json.dumps(candidate, sort_keys=True), encoding="utf-8")
    monkeypatch.setenv("HLX_EXPERIMENT_ID", experiment_id)
    monkeypatch.setenv("HYPERLEX_ALLOW_TRAIN", "1")
    monkeypatch.setenv("HLX_TRAIN_EXPORT_PATH", str(pinned))
    monkeypatch.setenv("HLX_TRAIN_EXPORT_SHA256", digest)
    monkeypatch.setenv("HLX_TRAIN_EXPORT_ROWS", str(len(rows)))
    monkeypatch.setenv("HLX_EVAL_RESERVE_LEDGER", str(reserve["ledger"]))
    monkeypatch.setenv("HLX_RESERVE_BINDING", str(reserve["binding"]))
    monkeypatch.setenv("HLX_BASELINE_ENV", str(baseline_path))
    monkeypatch.setenv("HLX_CANDIDATE_ENV", str(candidate_path))
    monkeypatch.setenv("HLX_SELECT_METRIC", "classify_macro_f1_nonnone")
    monkeypatch.setenv("HYPERLEX_FILLER_FILTER", "off")
    monkeypatch.setenv("HLX_BEST_SHA256", best_sha if best_sha is not None else actual_best)
    monkeypatch.setenv("HLX_BEST_WEIGHTS", str(tmp_path / "best.safetensors"))
    monkeypatch.setenv("HLX_TRUNK_SHA256", trunk_sha if trunk_sha is not None else actual_trunk)
    monkeypatch.setenv("HYPERLEX_TRUNK_DIR", str(trunk))
    monkeypatch.setenv("HYPERLEX_TRAIN_OUT", str(out))
    monkeypatch.setenv("HYPERLEX_EXPORT_DIR", str(tmp_path / "export-out"))
    monkeypatch.delenv("HLX_HOLDOUT_MANIFESTS", raising=False)
    monkeypatch.delenv("HLX_ALLOW_NO_HOLDOUT", raising=False)
    return {
        "pinned": pinned,
        "digest": digest,
        "out": out,
        "trunk": trunk,
        "reserve": reserve,
        "rows": len(rows),
    }
