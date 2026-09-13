"""Opt-in reviewed sidecar conversion; preserves original bytes, never approves data.

Provenance: Notion Sprint 001 Hub NOT_COMPUTABLE + Loop 805 Slice N/A
+ Hash: see emitted input_sha256 and metadata_sha256.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from .training_contracts import _strict_object, digest, validate_dataset


def parse_json(text: str):
    value = json.loads(text, object_pairs_hook=_strict_object)
    digest(value)  # No NaN/Infinity; preserves original bytes separately.
    return value


def convert(payload: bytes, metadata_payload: bytes | None = None) -> dict:
    """Each metadata entry is keyed by the canonical JSON digest of a legacy row.

    It supplies source/annotation/partition explicitly. Source text must equal
    legacy text; arbitrary source remapping is outside this version.
    """
    text = payload.decode("utf-8-sig")
    metadata = {} if metadata_payload is None else parse_json(metadata_payload.decode("utf-8-sig"))
    if not isinstance(metadata, dict):
        raise TypeError("metadata must be a digest-keyed object")
    for key in metadata:
        if len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
            raise ValueError("invalid metadata key")
    candidates = []
    quarantine = []
    used = set()
    seen = set()
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        record = {"line": number, "record_sha256": hashlib.sha256(line.encode()).hexdigest()}
        try:
            original = parse_json(line)
            if not isinstance(original, dict):
                raise TypeError("NOT_AN_OBJECT")
            key = digest(original)
            record["canonical_row_sha256"] = key
            if key in seen:
                raise ValueError("DUPLICATE_ROW")
            seen.add(key)
            if key not in metadata:
                raise ValueError("MISSING_REVIEW_METADATA")
            used.add(key)
            entry = metadata[key]
            if not isinstance(entry, dict) or set(entry) != {"source", "annotation", "partition"}:
                raise ValueError("INVALID_METADATA")
            if "gold" in original and "pred" in original and entry["partition"] != "dev":
                raise ValueError("RESIDUAL_PARTITION")
            if not isinstance(entry["source"], dict) or entry["source"].get("raw_text") != original.get("text"):
                raise ValueError("SOURCE_TEXT_MISMATCH")
            ann = entry["annotation"]
            if not isinstance(ann, dict):
                raise TypeError("INVALID_METADATA")
            assignment = {"example_id": ann.get("example_id"), "partition": entry["partition"]}
            candidate = {"sources": [entry["source"]], "annotations": [ann],
                         "split": {"version": "split.v1", "split_id": "intake-review-v1", "assignments": [assignment]}}
            try:
                validate_dataset(candidate)
            except ValueError as exc:
                raise ValueError("INVALID_CONTRACT_METADATA") from exc
            candidates.append({**record, "source": entry["source"], "annotation": ann, "assignment": assignment})
        except (TypeError, ValueError, UnicodeError) as exc:
            safe = {"NOT_AN_OBJECT", "DUPLICATE_ROW", "MISSING_REVIEW_METADATA", "INVALID_METADATA",
                    "SOURCE_TEXT_MISMATCH", "INVALID_CONTRACT_METADATA", "RESIDUAL_PARTITION"}
            quarantine.append({**record, "reason": str(exc) if str(exc) in safe else "MALFORMED_JSON"})
    if not candidates and not quarantine:
        raise ValueError("empty input")
    # Conflicts between accepted candidates fail the batch closed, rather than
    # retaining whichever source happened to occur first.
    dataset = None
    if candidates:
        source_map = {}
        conflict = False
        for c in candidates:
            sid = c["source"]["source_id"]
            if sid in source_map and source_map[sid] != c["source"]:
                conflict = True
            source_map[sid] = c["source"]
        dataset = {"sources": list(source_map.values()), "annotations": [c["annotation"] for c in candidates],
                   "split": {"version": "split.v1", "split_id": "intake-review-v1",
                             "assignments": [c["assignment"] for c in candidates]}}
        try:
            if conflict:
                raise ValueError("source conflict")
            validate_dataset(dataset)
        except ValueError:
            quarantine.extend({"line": c["line"], "record_sha256": c["record_sha256"],
                               "canonical_row_sha256": c["canonical_row_sha256"],
                               "reason": "BATCH_CONTRACT_CONFLICT"} for c in candidates)
            candidates, dataset = [], None
    quarantine.sort(key=lambda r: r["line"])
    report = {"version": "training_intake.v1", "input_sha256": hashlib.sha256(payload).hexdigest(),
              "metadata_sha256": hashlib.sha256(metadata_payload).hexdigest() if metadata_payload is not None else None,
              "n_records": len(candidates) + len(quarantine), "n_candidates": len(candidates),
              "n_quarantined": len(quarantine), "unused_metadata_entries": len(set(metadata) - used),
              "reasons": dict(Counter(q["reason"] for q in quarantine)), "name_gate": False,
              "training_ready": False, "run_evidence": "NOT_COMPUTABLE",
              "provenance": "Notion Sprint 001 Hub NOT_COMPUTABLE + Loop 805 Slice N/A + Hash: input_sha256",
              "note": "Review candidates only; no label/rights approval or trainer activation."}
    return {"report": report, "candidates": candidates, "quarantine": quarantine, "dataset": dataset}


def export_new(directory: Path, result: dict, payload: bytes, metadata: bytes | None) -> None:
    """Never overwrite. A receipt is written last; absent receipt means incomplete."""
    directory.mkdir(exist_ok=False)  # Parent must already exist; no broad directory creation.
    with (directory / "original.jsonl").open("xb") as f:
        f.write(payload)
    if metadata is not None:
        with (directory / "metadata.json").open("xb") as f:
            f.write(metadata)
    for name in ("candidates", "quarantine", "dataset"):
        with (directory / f"{name}.json").open("x", encoding="utf-8") as f:
            json.dump(result[name], f, indent=2, sort_keys=True, allow_nan=False)
            f.write("\n")
    with (directory / "receipt.json").open("x", encoding="utf-8") as f:
        json.dump({**result["report"], "export_complete": True}, f, indent=2, sort_keys=True)
        f.write("\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        payload = args.input.read_bytes()
        metadata = args.metadata.read_bytes() if args.metadata else None
        result = convert(payload, metadata)
        if args.out_dir:
            export_new(args.out_dir, result, payload, metadata)
    except (OSError, TypeError, ValueError, UnicodeError):
        print(json.dumps({"status": "INTAKE_FAILED", "name_gate": False,
                          "note": "Input/metadata/output error. Any directory without receipt.json is incomplete."}))
        return 2
    print(json.dumps(result["report"], indent=2, sort_keys=True))
    return 2 if result["report"]["n_quarantined"] or result["report"]["unused_metadata_entries"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
