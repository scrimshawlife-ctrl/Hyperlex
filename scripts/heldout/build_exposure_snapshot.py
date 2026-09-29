"""Monotonic exposure snapshot builder.

The historical box hash list and Vernacular string list are a lower bound.
A successor may add hashes or strings. It may not drop any. Notion titles,
WordNet, and Wiktionary are not box-hash sources. This module does not fetch,
does not execute hs_run, and does not harvest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

BUILDER_VERSION = "exposure_snapshot_builder_v1"
TRANSITION = "EXPOSURE_SNAPSHOT_RECONSTRUCTION_AUTHORIZATION"
RECONSTRUCTED = "EXPOSURE_SNAPSHOT_RECONSTRUCTED"
MONOTONICITY_FAILURE = "EXPOSURE_MONOTONICITY_FAILURE"
PLANNED = "EXPOSURE_SNAPSHOT_PLANNED"
SCHEMA = "hyperlex.exposure_snapshot_reconstruction.v1"
BASELINE_SNAPSHOT_ID = "20260925T211351Z"
SNAPSHOT_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
REFUSED_BOX_FAMILIES = frozenset({"notion", "wiktionary", "wordnet"})
ABSENT_BY_DEFAULT = (
    "discovery_lane_export",
    "jev_spike_export",
    "notion_not_a_box_hash_source",
    "obsidian_export",
    "vernacular_sqlite",
)
HASH_NORMALIZATION = (
    "precomputed sha256 of normalize_group_text; lines are united and not recomputed"
)
VERN_NORMALIZATION = (
    "historical JSON string lines are carried byte-for-byte; new strings use json.dumps ensure_ascii"
)


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_box_hash_text(text: str, *, label: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        if HASH_RE.fullmatch(line) is None:
            raise SystemExit(f"REFUSE: {label} line {line_number} is not a lowercase sha256")
        if line in seen:
            continue
        seen.add(line)
        found.append(line)
    if not found:
        raise SystemExit(f"REFUSE: {label} has no hashes")
    return found


def parse_vern_text(text: str, *, label: str) -> list[tuple[str, str]]:
    """Return ``(decoded string, original line)`` pairs. Duplicate strings keep the first line."""
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for line_number, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"REFUSE: {label} line {line_number} is not JSON") from exc
        if not isinstance(value, str):
            raise SystemExit(f"REFUSE: {label} line {line_number} is not a JSON string")
        if value in seen:
            continue
        seen.add(value)
        found.append((value, raw))
    if not found:
        raise SystemExit(f"REFUSE: {label} has no strings")
    return found


def _source_record(
    *,
    family: str,
    artifact: str,
    source_sha256: str,
    entry_count: int,
    added_count: int,
    normalization: str,
) -> dict[str, Any]:
    return {
        "added_count": added_count,
        "artifact": artifact,
        "builder_version": BUILDER_VERSION,
        "entry_count": entry_count,
        "family": family,
        "normalization": normalization,
        "source_sha256": source_sha256,
    }


def assess_monotonicity(
    previous_box: set[str],
    new_box: set[str],
    previous_vern: set[str],
    new_vern: set[str],
) -> dict[str, Any]:
    box_missing = len(previous_box - new_box)
    vern_missing = len(previous_vern - new_vern)
    return {
        "box_missing": box_missing,
        "ok": box_missing == 0 and vern_missing == 0,
        "vern_missing": vern_missing,
    }


def plan_reconstruction(
    *,
    baseline_box_text: str,
    baseline_vern_text: str,
    baseline_snapshot_id: str,
    baseline_box_sha256: str,
    baseline_vern_sha256: str,
    box_increments: Sequence[Mapping[str, Any]] = (),
    vern_increments: Sequence[Mapping[str, Any]] = (),
    absent_families: Sequence[str] = ABSENT_BY_DEFAULT,
) -> dict[str, Any]:
    """Unite sources. Do not write. Missing historical rows fail closed."""
    if SNAPSHOT_ID_RE.fullmatch(baseline_snapshot_id) is None:
        raise SystemExit("REFUSE: baseline snapshot id is not YYYYMMDDTHHMMSSZ")
    baseline_hashes = parse_box_hash_text(baseline_box_text, label="baseline box")
    baseline_vern = parse_vern_text(baseline_vern_text, label="baseline vern")
    box_set = set(baseline_hashes)
    vern_lines = {value: line for value, line in baseline_vern}
    vern_order = [value for value, _line in baseline_vern]
    sources = [
        _source_record(
            family="historical_box_snapshot",
            artifact=f"box-jev-hashes-{baseline_snapshot_id}.txt",
            source_sha256=baseline_box_sha256,
            entry_count=len(baseline_hashes),
            added_count=len(baseline_hashes),
            normalization=HASH_NORMALIZATION,
        ),
        _source_record(
            family="historical_vern_snapshot",
            artifact=f"vern-texts-{baseline_snapshot_id}.jsonl",
            source_sha256=baseline_vern_sha256,
            entry_count=len(baseline_vern),
            added_count=len(baseline_vern),
            normalization=VERN_NORMALIZATION,
        ),
    ]
    for item in box_increments:
        family = str(item.get("family") or "")
        if family in REFUSED_BOX_FAMILIES:
            raise SystemExit(f"REFUSE: {family} is not a box-hash source")
        hashes = parse_box_hash_text(str(item.get("text") or ""), label=family or "box increment")
        added = [digest for digest in hashes if digest not in box_set]
        box_set.update(added)
        sources.append(
            _source_record(
                family=family,
                artifact=str(item.get("artifact") or ""),
                source_sha256=str(item.get("source_sha256") or ""),
                entry_count=len(hashes),
                added_count=len(added),
                normalization=HASH_NORMALIZATION,
            )
        )
    new_vern_values: list[str] = []
    for item in vern_increments:
        family = str(item.get("family") or "")
        if family in REFUSED_BOX_FAMILIES:
            raise SystemExit(f"REFUSE: {family} is not an exposure-snapshot source")
        parsed = parse_vern_text(str(item.get("text") or ""), label=family or "vern increment")
        added_values = [value for value, _line in parsed if value not in vern_lines]
        for value, _line in parsed:
            if value not in vern_lines:
                vern_lines[value] = json.dumps(value, ensure_ascii=True)
                new_vern_values.append(value)
        sources.append(
            _source_record(
                family=family,
                artifact=str(item.get("artifact") or ""),
                source_sha256=str(item.get("source_sha256") or ""),
                entry_count=len(parsed),
                added_count=len(added_values),
                normalization=VERN_NORMALIZATION,
            )
        )
    box_text = "".join(digest + "\n" for digest in sorted(box_set))
    vern_text = "".join(vern_lines[value] + "\n" for value in vern_order + new_vern_values)
    previous_vern = {value for value, _line in baseline_vern}
    assessment = assess_monotonicity(set(baseline_hashes), box_set, previous_vern, set(vern_lines))
    return {
        "absent_families": sorted(set(absent_families)),
        "baseline_snapshot_id": baseline_snapshot_id,
        "box_added": len(box_set) - len(baseline_hashes),
        "box_count": len(box_set),
        "box_sha256": sha256_text(box_text),
        "box_text": box_text,
        "builder_version": BUILDER_VERSION,
        "monotonicity": assessment,
        "network_requests": 0,
        "sources": sources,
        "transition": TRANSITION,
        "vern_added": len(vern_lines) - len(previous_vern),
        "vern_bytes_carried_forward": vern_text == baseline_vern_text,
        "vern_count": len(vern_lines),
        "vern_sha256": sha256_text(vern_text),
        "vern_text": vern_text,
    }


def snapshot_paths(out_dir: Path, snapshot_id: str) -> tuple[Path, Path]:
    if SNAPSHOT_ID_RE.fullmatch(snapshot_id) is None:
        raise SystemExit("REFUSE: snapshot id is not YYYYMMDDTHHMMSSZ")
    return (
        out_dir / f"vern-texts-{snapshot_id}.jsonl",
        out_dir / f"box-jev-hashes-{snapshot_id}.txt",
    )


def publish_pair(out_dir: Path, snapshot_id: str, box_text: str, vern_text: str) -> tuple[Path, Path]:
    """Write both files or neither. Existing names are left untouched."""
    vern_path, box_path = snapshot_paths(out_dir, snapshot_id)
    if vern_path.exists() or box_path.exists():
        raise SystemExit("REFUSE: snapshot id is already published")
    partial = out_dir / f".partial-{snapshot_id}"
    partial.mkdir(mode=0o700)
    temporary_vern = partial / vern_path.name
    temporary_box = partial / box_path.name
    try:
        temporary_vern.write_text(vern_text, encoding="utf-8")
        temporary_box.write_text(box_text, encoding="utf-8")
        os.replace(temporary_vern, vern_path)
        try:
            os.replace(temporary_box, box_path)
        except Exception:
            vern_path.unlink(missing_ok=True)
            raise
    finally:
        temporary_box.unlink(missing_ok=True)
        temporary_vern.unlink(missing_ok=True)
        partial.rmdir()
    os.chmod(vern_path, stat.S_IRUSR | stat.S_IWUSR)
    os.chmod(box_path, stat.S_IRUSR | stat.S_IWUSR)
    return vern_path, box_path


def freshness_record(
    *,
    vern_path: Path,
    box_path: Path,
    snapshot_id: str,
    compared_at_unix: str,
) -> dict[str, Any]:
    from hyperlexical.select_005_harvest import exposure_fence

    rows = []
    for kind, path in (("vern", vern_path), ("boxhash", box_path)):
        rows.append(
            {
                "kind": kind,
                "mtime_unix": format(path.stat().st_mtime, ".6f"),
                "path": path.name,
                "sha256": sha256_file(path),
                "snapshot_id": snapshot_id,
            }
        )
    return exposure_fence(rows, compared_at_unix=compared_at_unix)


def build_receipt(
    plan: Mapping[str, Any],
    *,
    snapshot_id: str | None,
    published: bool,
    fence: Mapping[str, Any] | None,
    harvest_run: bool = False,
) -> dict[str, Any]:
    if harvest_run:
        raise SystemExit("REFUSE: reconstruction does not harvest")
    monotonicity = dict(plan["monotonicity"])
    if published and not monotonicity["ok"]:
        raise SystemExit("REFUSE: a failed monotonicity check cannot be published")
    if not monotonicity["ok"]:
        state = MONOTONICITY_FAILURE
    elif published:
        state = RECONSTRUCTED
    else:
        state = PLANNED
    record: dict[str, Any] = {
        "absent_families": list(plan["absent_families"]),
        "baseline_snapshot_id": plan["baseline_snapshot_id"],
        "box_added": plan["box_added"],
        "box_count": plan["box_count"],
        "builder_version": BUILDER_VERSION,
        "freshness": None if fence is None else {key: fence[key] for key in ("state", "worst_age_hours", "limit_hours")},
        "harvest_run": False,
        "monotonicity": monotonicity,
        "network_requests": 0,
        "previous_pair_overwritten": False,
        "published": published,
        "schema": SCHEMA,
        "snapshot_id": snapshot_id,
        "successor_box_sha256": plan["box_sha256"],
        "successor_vern_sha256": plan["vern_sha256"],
        "sources": list(plan["sources"]),
        "state": state,
        "training_authorized": False,
        "transition": TRANSITION,
        "vern_added": plan["vern_added"],
        "vern_bytes_carried_forward": plan["vern_bytes_carried_forward"],
        "vern_count": plan["vern_count"],
    }
    if fence is not None:
        file_box = next(row["sha256"] for row in fence["snapshots"] if row["kind"] == "boxhash")
        file_vern = next(row["sha256"] for row in fence["snapshots"] if row["kind"] == "vern")
        if file_box != plan["box_sha256"] or file_vern != plan["vern_sha256"]:
            raise SystemExit("REFUSE: published bytes differ from the planned pair")
    body = {key: value for key, value in record.items() if key != "record_sha256"}
    record["record_sha256"] = sha256_text(canonical_json(body))
    return record


def utc_snapshot_id(moment: datetime | None = None) -> str:
    current = moment or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise SystemExit("REFUSE: snapshot clock is naive")
    return current.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _increment(spec: str) -> tuple[str, Path]:
    family, separator, raw_path = spec.partition(":")
    if not separator or not family or not raw_path:
        raise SystemExit("REFUSE: increment must be family:path")
    return family, Path(raw_path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build one monotonic exposure snapshot pair")
    parser.add_argument("--baseline-id", default=BASELINE_SNAPSHOT_ID)
    parser.add_argument("--baseline-box", type=Path, required=True)
    parser.add_argument("--baseline-vern", type=Path, required=True)
    parser.add_argument("--box-increment", action="append")
    parser.add_argument("--vern-increment", action="append")
    parser.add_argument("--absent", action="append")
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--snapshot-id")
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args(argv)
    box_text = args.baseline_box.read_text(encoding="utf-8")
    vern_text = args.baseline_vern.read_text(encoding="utf-8")
    increments = []
    for spec in args.box_increment or []:
        family, path = _increment(spec)
        increments.append(
            {
                "artifact": str(path),
                "family": family,
                "source_sha256": sha256_file(path),
                "text": path.read_text(encoding="utf-8"),
            }
        )
    vern_increments = []
    for spec in args.vern_increment or []:
        family, path = _increment(spec)
        vern_increments.append(
            {
                "artifact": str(path),
                "family": family,
                "source_sha256": sha256_file(path),
                "text": path.read_text(encoding="utf-8"),
            }
        )
    plan = plan_reconstruction(
        baseline_box_text=box_text,
        baseline_vern_text=vern_text,
        baseline_snapshot_id=args.baseline_id,
        baseline_box_sha256=sha256_file(args.baseline_box),
        baseline_vern_sha256=sha256_file(args.baseline_vern),
        box_increments=increments,
        vern_increments=vern_increments,
        absent_families=args.absent if args.absent is not None else ABSENT_BY_DEFAULT,
    )
    published = False
    fence = None
    snapshot_id = args.snapshot_id
    if plan["monotonicity"]["ok"] and args.publish:
        if args.out_dir is None:
            raise SystemExit("REFUSE: publish requires --out-dir")
        snapshot_id = snapshot_id or utc_snapshot_id()
        if snapshot_id == args.baseline_id:
            raise SystemExit("REFUSE: successor snapshot id collides with the baseline")
        vern_path, box_path = publish_pair(args.out_dir, snapshot_id, plan["box_text"], plan["vern_text"])
        published = True
        fence = freshness_record(
            vern_path=vern_path,
            box_path=box_path,
            snapshot_id=snapshot_id,
            compared_at_unix=format(time.time(), ".6f"),
        )
        if fence["state"] != "EXPOSURE_SNAPSHOT_FRESH":
            raise SystemExit("REFUSE: published pair is not inside the 6 hour fence")
    elif not plan["monotonicity"]["ok"] and args.publish:
        published = False
    receipt = build_receipt(plan, snapshot_id=snapshot_id, published=published, fence=fence)
    rendered = canonical_json(receipt)
    if args.receipt is not None:
        args.receipt.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        args.receipt.write_text(rendered, encoding="utf-8")
        os.chmod(args.receipt, stat.S_IRUSR | stat.S_IWUSR)
    print(rendered, end="")
    return 0 if plan["monotonicity"]["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
