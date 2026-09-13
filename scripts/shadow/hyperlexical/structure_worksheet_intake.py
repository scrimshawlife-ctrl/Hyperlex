"""Fail-closed intake: human-filled structure worksheet -> patched metadata.

Never invents spans, rights, or confirm flags. Unconfirmed rows stay pending.
Writes a NEW out directory only. Callers prepare/verify separately and must not
overwrite BEST.
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from .training_contracts import digest


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            raise ValueError(f"{path}:{line_no}: row must be an object")
        rows.append(obj)
    return rows


def validate_spans(text: str, spans: list[dict]) -> list[str]:
    errors: list[str] = []
    if not isinstance(spans, list) or not spans:
        return ["empty spans"]
    seen_ids: set[str] = set()
    seen_coords: set[tuple[int, int]] = set()
    for i, span in enumerate(spans):
        if not isinstance(span, dict):
            errors.append(f"span[{i}] not an object")
            continue
        for req in ("start", "end", "text", "role"):
            if req not in span:
                errors.append(f"span[{i}] missing {req}")
        if any(e.startswith(f"span[{i}]") for e in errors):
            continue
        start, end = span["start"], span["end"]
        if not isinstance(start, int) or not isinstance(end, int):
            errors.append(f"span[{i}] start/end must be ints")
            continue
        if start < 0 or end <= start or end > len(text):
            errors.append(f"span[{i}] bounds invalid for text len={len(text)}")
            continue
        piece = text[start:end]
        if piece != span["text"]:
            errors.append(f"span[{i}] text mismatch: {span['text']!r} != {piece!r}")
        if not isinstance(span["role"], str) or not span["role"].strip():
            errors.append(f"span[{i}] role empty")
        oid = span.get("occurrence_id") or span.get("span_id") or f"sp{i}"
        if not isinstance(oid, str) or not oid.strip():
            errors.append(f"span[{i}] occurrence_id empty")
        elif oid in seen_ids:
            errors.append(f"span[{i}] duplicate occurrence_id")
        else:
            seen_ids.add(oid)
        coord = (start, end)
        if coord in seen_coords:
            errors.append(f"span[{i}] duplicate coordinates")
        else:
            seen_coords.add(coord)
    return errors


def normalize_span(span: dict, index: int) -> dict:
    return {
        "occurrence_id": span.get("occurrence_id") or span.get("span_id") or f"sp{index}",
        "start": span["start"],
        "end": span["end"],
        "text": span["text"],
        "role": span["role"],
    }


def source_raw_text(source: dict) -> str | None:
    if not isinstance(source, dict):
        return None
    for key in ("raw_text", "text"):
        value = source.get(key)
        if isinstance(value, str):
            return value
    return None


def set_loss_mask(label: dict, value: bool) -> None:
    """Set the prepared-package structure loss mask field."""
    label["loss_mask"] = value


def promote_structure_row(
    *,
    worksheet_row: dict,
    metadata_entry: dict,
) -> tuple[dict | None, dict]:
    """Return (patched_entry_or_None, audit). Never invents confirmations."""
    audit: dict[str, Any] = {
        "canonical_row_sha256": worksheet_row.get("canonical_row_sha256"),
        "text": worksheet_row.get("text"),
        "status": None,
        "errors": [],
    }
    text = worksheet_row.get("text")
    if not isinstance(text, str) or not text.strip():
        audit["status"] = "REJECTED"
        audit["errors"].append("missing text")
        return None, audit

    structure = worksheet_row.get("structure") or {}
    spans = structure.get("spans") or []
    confirm_labels = worksheet_row.get("confirm_labels") is True
    confirm_rights = worksheet_row.get("confirm_rights") is True

    if not spans and not confirm_labels:
        audit["status"] = "PENDING"
        return None, audit

    if not confirm_labels or not confirm_rights:
        audit["status"] = "PENDING_CONFIRM"
        audit["errors"].append("confirm_labels and confirm_rights must both be true")
        return None, audit

    if structure.get("status") != "reviewed":
        audit["status"] = "REJECTED"
        audit["errors"].append("structure.status must be reviewed")
        return None, audit

    if structure.get("loss_mask") is not True:
        audit["status"] = "REJECTED"
        audit["errors"].append("structure.loss_mask must be true")
        return None, audit

    reviewer = structure.get("reviewer")
    if not isinstance(reviewer, str) or not reviewer.strip():
        audit["status"] = "REJECTED"
        audit["errors"].append("structure.reviewer required")
        return None, audit

    span_errors = validate_spans(text, spans)
    if span_errors:
        audit["status"] = "REJECTED"
        audit["errors"].extend(span_errors)
        return None, audit

    values = structure.get("values") or []
    role_set = {s["role"] for s in spans}
    if not isinstance(values, list) or not values:
        values = sorted(role_set)
    if set(values) != role_set:
        audit["status"] = "REJECTED"
        audit["errors"].append("structure.values must match span roles exactly")
        return None, audit

    if not isinstance(metadata_entry, dict) or set(metadata_entry) != {
        "source",
        "annotation",
        "partition",
    }:
        audit["status"] = "REJECTED"
        audit["errors"].append("metadata entry must be {source,annotation,partition}")
        return None, audit

    if source_raw_text(metadata_entry["source"]) != text:
        audit["status"] = "REJECTED"
        audit["errors"].append("metadata source text mismatch")
        return None, audit

    patched = json.loads(json.dumps(metadata_entry))
    ann = patched["annotation"]
    if not isinstance(ann, dict):
        audit["status"] = "REJECTED"
        audit["errors"].append("annotation missing")
        return None, audit

    labels = ann.setdefault("labels", {})
    structure_label = labels.setdefault("structure", {})
    structure_label["status"] = "reviewed"
    set_loss_mask(structure_label, True)
    structure_label["reviewer"] = reviewer.strip()
    structure_label["method"] = structure.get("method") or "human-structure"
    structure_label["values"] = list(values)
    ann["spans"] = [normalize_span(s, i) for i, s in enumerate(spans)]
    if "offset_unit" in ann:
        ann["offset_unit"] = structure.get("offset_unit") or ann.get("offset_unit") or "unicode_codepoint"

    audit["status"] = "PROMOTED"
    audit["n_spans"] = len(ann["spans"])
    return patched, audit


def run_intake(
    *,
    worksheet_path: Path,
    original_path: Path,
    metadata_path: Path,
    out_dir: Path,
) -> dict:
    worksheet = load_jsonl(worksheet_path)
    originals = load_jsonl(original_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object keyed by digest")

    by_digest = {digest(row): row for row in originals}
    out_metadata = json.loads(json.dumps(metadata))
    audits: list[dict] = []
    promoted_keys: list[str] = []

    for row in worksheet:
        key = row.get("canonical_row_sha256")
        if key not in metadata or key not in by_digest:
            audits.append(
                {
                    "canonical_row_sha256": key,
                    "text": row.get("text"),
                    "status": "REJECTED",
                    "errors": ["UNKNOWN_DIGEST"],
                }
            )
            continue
        patched, audit = promote_structure_row(
            worksheet_row=row,
            metadata_entry=metadata[key],
        )
        audits.append(audit)
        if patched is not None and audit["status"] == "PROMOTED":
            out_metadata[key] = patched
            promoted_keys.append(key)

    counts = Counter(a["status"] for a in audits)
    report = {
        "version": "structure_worksheet_intake.v1",
        "worksheet": str(worksheet_path),
        "n_worksheet": len(worksheet),
        "n_promoted": len(promoted_keys),
        "counts": dict(counts),
        "promoted_digests": promoted_keys,
        "audits": audits,
        "training_ready": False,
        "name_gate": False,
        "best_overwrite": False,
        "note": (
            "Fail-closed intake. Metadata patched only for rows with "
            "confirm_labels=true, confirm_rights=true, and validated spans. "
            "Prepare/verify/train must use a NEW directory; never overwrite BEST."
        ),
    }

    if out_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing out_dir: {out_dir}")
    out_dir.mkdir(parents=True)
    (out_dir / "metadata.json").write_text(
        json.dumps(out_metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    promoted_set = set(promoted_keys)
    filtered = [row for row in originals if digest(row) in promoted_set]
    (out_dir / "original_structure_promoted.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in filtered),
        encoding="utf-8",
    )
    shutil.copy2(original_path, out_dir / "original_full.jsonl")
    (out_dir / "INTAKE_REPORT.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "README.md").write_text(
        "\n".join(
            [
                "# Structure worksheet intake output",
                "",
                f"- promoted: {len(promoted_keys)} / {len(worksheet)}",
                "- next: prepare/verify into a **new** prepare dir",
                "- never overwrite BEST / morph19",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worksheet", type=Path, required=True)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    report = run_intake(
        worksheet_path=args.worksheet,
        original_path=args.original,
        metadata_path=args.metadata,
        out_dir=args.out_dir,
    )
    print(
        json.dumps(
            {
                "status": "INTAKE_DONE",
                "n_promoted": report["n_promoted"],
                "counts": report["counts"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
