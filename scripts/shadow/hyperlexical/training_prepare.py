"""Private, deterministic intake-to-adapter package. No training or promotion.

Provenance: Hyperlex Spec 007 WF-003; hashes emitted in each package.
"""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from .training_adapter import prepare_reviewed
from .training_contracts import digest
from .training_intake import convert, parse_json


def prepare(payload, metadata=None, *, ontology, tokenization=None):
    if not isinstance(ontology, str) or not ontology.strip():
        raise ValueError("explicit ontology required")
    intake = convert(payload, metadata)
    plan = None
    if intake["dataset"] is not None:
        plan = prepare_reviewed(intake["dataset"], expected_ontology=ontology, tokenization=tokenization)
    elif tokenization is not None:
        raise ValueError("tokenization without accepted dataset")
    blockers = []
    if intake["report"]["n_quarantined"]:
        blockers.append("QUARANTINED_INPUT")
    if intake["report"]["unused_metadata_entries"]:
        blockers.append("UNUSED_METADATA")
    if plan is None:
        blockers.append("NO_REVIEWED_DATASET")
    else:
        blockers.extend(plan["blockers"])
    review_queue = [{**q, "required_action": "Resolve source rights, per-head review, ontology and grouped split; do not infer approval from OBSERVED."}
                    for q in intake["quarantine"]]
    report = {**intake["report"], "version": "training_preparation.v1",
              "status": "DATA_BLOCKED" if blockers else "PREPARED_NOT_RUNNABLE",
              "blockers": blockers, "expected_ontology": ontology,
              "n_adapted": len(plan["rows"]) if plan else 0,
              "n_excluded": len(plan["excluded"]) if plan else 0,
              "plan_sha256": digest(plan), "review_queue_sha256": digest(review_queue),
              "note": "Local preparation only; legacy trainer remains blocked for reviewed occurrences."}
    assert report["n_records"] == report["n_quarantined"] + report["n_adapted"] + report["n_excluded"]
    return {"report": report, "dataset": intake["dataset"], "plan": plan,
            "quarantine": intake["quarantine"], "review_queue": review_queue}


def export_package(directory, result, payload, metadata=None, tokenization_payload=None):
    """Create only; receipt last. Hash every output file except the receipt itself."""
    directory.mkdir(exist_ok=False)
    artifacts = {"original.jsonl": payload}
    if metadata is not None:
        artifacts["metadata.json"] = metadata
    if tokenization_payload is not None:
        artifacts["tokenization.json"] = tokenization_payload
    for key in ("dataset", "plan", "quarantine", "review_queue"):
        artifacts[key + ".json"] = (json.dumps(result[key], indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    hashes = {}
    for name, data in artifacts.items():
        with (directory / name).open("xb") as stream:
            stream.write(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
    with (directory / "receipt.json").open("x", encoding="utf-8") as stream:
        json.dump({**result["report"], "files_sha256": hashes, "export_complete": True}, stream, indent=2, sort_keys=True)
        stream.write("\n")


def verify_package(directory):
    """Recompute preparation from retained bytes and verify every declared artifact."""
    receipt = parse_json((directory / "receipt.json").read_text(encoding="utf-8"))
    required = {"original.jsonl", "dataset.json", "plan.json", "quarantine.json", "review_queue.json"}
    allowed = required | {"metadata.json", "tokenization.json"}
    names = set(receipt["files_sha256"])
    if not required <= names <= allowed or receipt.get("export_complete") is not True:
        raise ValueError("invalid package manifest")
    if {p.name for p in directory.iterdir()} != names | {"receipt.json"}:
        raise ValueError("unexpected package files")
    for name in names:
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != receipt["files_sha256"][name]:
            raise ValueError("package hash mismatch")
    metadata = (directory / "metadata.json").read_bytes() if "metadata.json" in names else None
    tokens = parse_json((directory / "tokenization.json").read_text(encoding="utf-8-sig")) if "tokenization.json" in names else None
    result = prepare((directory / "original.jsonl").read_bytes(), metadata,
                     ontology=receipt["expected_ontology"], tokenization=tokens)
    if any(receipt.get(k) != v for k, v in result["report"].items()):
        raise ValueError("recomputed receipt mismatch")
    for key in ("dataset", "plan", "quarantine", "review_queue"):
        if parse_json((directory / (key + ".json")).read_text(encoding="utf-8")) != result[key]:
            raise ValueError("recomputed artifact mismatch")
    return {"status": "PACKAGE_VERIFIED", "n_records": receipt["n_records"],
            "n_quarantined": receipt["n_quarantined"], "training_ready": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--zip-member")
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--tokenization", type=Path)
    parser.add_argument("--ontology", required=True)
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        if not args.ontology.strip():
            raise ValueError("ontology required")
        original = args.input.read_bytes()
        payload = original
        if args.zip_member:
            # Read one explicit member in memory; never extract archive paths.
            import io
            with zipfile.ZipFile(io.BytesIO(original)) as archive:
                if archive.namelist().count(args.zip_member) != 1:
                    raise ValueError("ambiguous or missing member")
                payload = archive.read(args.zip_member)
        metadata = args.metadata.read_bytes() if args.metadata else None
        token_bytes = args.tokenization.read_bytes() if args.tokenization else None
        tokenization = parse_json(token_bytes.decode("utf-8-sig")) if token_bytes is not None else None
        result = prepare(payload, metadata, ontology=args.ontology, tokenization=tokenization)
        result["report"].update(container_sha256=hashlib.sha256(original).hexdigest(), zip_member=args.zip_member)
        if args.out_dir:
            export_package(args.out_dir, result, payload, metadata, token_bytes)
    except (OSError, ValueError, TypeError, KeyError, zipfile.BadZipFile):
        print(json.dumps({"status": "PREPARATION_FAILED", "training_ready": False,
                          "note": "Input, contract or output error. No receipt means incomplete output."}))
        return 2
    print(json.dumps(result["report"], sort_keys=True, indent=2))
    return 3 if result["report"]["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
