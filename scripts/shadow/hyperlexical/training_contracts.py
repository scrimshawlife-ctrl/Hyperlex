"""Opt-in local proposed contracts; no training or corpus mutation.

Provenance: Notion Sprint 001 Hub NOT_COMPUTABLE + Loop 805 Slice N/A
+ Hash: b3eee725054c1ed1dae16fad3464af005edad0cc (base).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA = Path(__file__).resolve().parents[3] / "contracts/training/v1.schema.json"


def digest(value) -> str:
    """v1 digest: sorted keys, compact ASCII JSON, finite numbers, list order retained."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def _unique(records: list[dict], field: str) -> dict:
    result = {r[field]: r for r in records}
    if len(result) != len(records):
        raise ValueError(f"duplicate {field}")
    return result


def validate_dataset(bundle: dict) -> dict:
    """Validate sources/annotations/split without inventing a training run."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    schema = {"$defs": schema["$defs"], "type": "object", "additionalProperties": False,
              "required": ["sources", "annotations", "split"],
              "properties": {key: schema["$defs"]["bundle"]["properties"][key]
                             for key in ("sources", "annotations", "split")}}
    Draft202012Validator.check_schema(schema)
    if not Draft202012Validator(schema).is_valid(bundle):
        raise ValueError("schema violation")
    digest(bundle)  # Reject non-finite values even in otherwise numeric fields.
    sources = _unique(bundle["sources"], "source_id")
    annotations = _unique(bundle["annotations"], "example_id")
    assignments = _unique(bundle["split"]["assignments"], "example_id")
    if set(assignments) != set(annotations):
        raise ValueError("split coverage mismatch")
    for source in sources.values():
        if hashlib.sha256(source["raw_text"].encode("utf-8")).hexdigest() != source["text_sha256"]:
            raise ValueError("source text hash mismatch")
    groups = {}
    for eid, ann in annotations.items():
        if ann["source_id"] not in sources:
            raise ValueError("unknown source")
        source = sources[ann["source_id"]]
        if source["rights_status"] != "approved":
            raise ValueError("unapproved source used by annotation")
        _unique(ann["spans"], "occurrence_id")
        coordinates = set()
        for span in ann["spans"]:
            start, end = span["start"], span["end"]
            if type(start) is not int or type(end) is not int:
                raise ValueError("span offsets must be integer encodings")
            if start >= end or end > len(source["raw_text"]) or source["raw_text"][start:end] != span["text"]:
                raise ValueError("invalid occurrence span")
            if (start, end) in coordinates:
                raise ValueError("duplicate occurrence coordinates")
            coordinates.add((start, end))
        for head, label in ann["labels"].items():
            if label["status"] in {"unreviewed", "disputed"} and label["loss_mask"]:
                raise ValueError("unreviewed/disputed label activates loss")
            if label["loss_mask"] and not label["values"]:
                raise ValueError("active loss has no label")
            if label["status"] == "reviewed" and not (label["reviewer"] or "").strip():
                raise ValueError("reviewed label has no reviewer")
            if head == "structure" and label["loss_mask"] and not ann["spans"]:
                raise ValueError("active structure has no spans")
        partition = assignments[eid]["partition"]
        # Source IDs and normalized exact-text groups are automatic safeguards.
        keys = [("source", ann["source_id"]),
                ("text", " ".join(source["raw_text"].casefold().split()))]
        keys += [("declared", g) for g in ann["group_ids"]]
        for key in keys:
            if key in groups and groups[key] != partition:
                raise ValueError("group crosses partitions")
            groups[key] = partition
    return {"sources": len(sources), "annotations": len(annotations)}


def validate(bundle: dict) -> dict:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    if not Draft202012Validator(schema).is_valid(bundle):
        raise ValueError("schema violation")
    digest(bundle)
    counts = validate_dataset({key: bundle[key] for key in ("sources", "annotations", "split")})
    annotations = {a["example_id"]: a for a in bundle["annotations"]}
    assignments = {a["example_id"]: a for a in bundle["split"]["assignments"]}
    run = bundle["run"]
    for field, content in [("source_sha256", bundle["sources"]),
                           ("annotation_sha256", bundle["annotations"]),
                           ("split_sha256", bundle["split"])]:
        if run[field] != digest(content):
            raise ValueError("run content hash mismatch")
    evaluation = bundle["evaluation"]
    if evaluation["run_id"] != run["run_id"]:
        raise ValueError("evaluation run mismatch")
    ids = set(evaluation["example_ids"])
    if not ids <= set(annotations) or len(ids) != evaluation["n_evaluated"]:
        raise ValueError("evaluation example coverage mismatch")
    parts = {assignments[eid]["partition"] for eid in ids}
    if evaluation["population"] == "residual_only":
        if parts != {"dev"}:
            raise ValueError("residual review must use development examples")
    else:
        expected = {eid for eid, a in assignments.items() if a["partition"] == evaluation["population"]}
        if ids != expected:
            raise ValueError("incomplete evaluation partition")
    access = {"surface_extraction": "text", "bound_recovery": "representation_only",
              "oracle_span_diagnostic": "gold_spans"}
    if evaluation["decoder_access"] != access[evaluation["task"]]:
        raise ValueError("task/access mismatch")
    if evaluation["n_exact"] > evaluation["n_evaluated"] or not math.isclose(
        evaluation["exact"], evaluation["n_exact"] / evaluation["n_evaluated"], abs_tol=1e-12, rel_tol=0
    ):
        raise ValueError("evaluation counts mismatch")
    return {"status": "CONTRACT_VALID", "bundle_sha256": digest(bundle),
            **counts,
            "runtime_proof": "NOT_COMPUTABLE", "name_gate": False,
            "note": "Declared contracts only; no proof of rights, annotations, checkpoint bytes or decoder isolation."}


def _strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON property")
        result[key] = value
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        bundle = json.loads(args.bundle.read_text(encoding="utf-8-sig"), object_pairs_hook=_strict_object)
        report = validate(bundle)
    except (OSError, ValueError, UnicodeError):
        print(json.dumps({"status": "CONTRACT_INVALID", "name_gate": False}))
        return 2
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
