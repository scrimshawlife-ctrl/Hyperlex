"""Read-only recovery evidence; never launches or authorizes training.

Provenance: Notion Sprint 001 Hub NOT_COMPUTABLE + Loop 805 Slice N/A
+ Hash: b3eee725054c1ed1dae16fad3464af005edad0cc (base).
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from .training_contracts import _strict_object, digest, validate, validate_dataset


def file_digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def assess(dataset, *, historical=None, checkpoint=None):
    """Historical errors never silently select a clean baseline. No writes."""
    counts = validate_dataset(dataset)
    assignments = {a["example_id"]: a["partition"] for a in dataset["split"]["assignments"]}
    partitions = Counter(assignments.values())
    signals = {p: Counter() for p in ("train", "dev", "test")}
    for ann in dataset["annotations"]:
        for head, label in ann["labels"].items():
            if label["loss_mask"]:
                signals[assignments[ann["example_id"]]][head] += 1
    blockers = []
    if not signals["train"]:
        blockers.append("NO_TRAIN_SUPERVISION")
    for head in signals["train"]:
        if not signals["dev"][head]:
            blockers.append("NO_DEV_SUPERVISION:" + head)
    if not partitions["test"]:
        blockers.append("NO_RESERVED_TEST")
    mode = "CLEAN_BASELINE_PROPOSED"
    checkpoint_hash = None
    if checkpoint is not None and historical is None:
        raise ValueError("checkpoint requires historical bundle")
    if historical is not None:
        validate(historical)
        if checkpoint is None:
            raise ValueError("historical bundle requires checkpoint bytes")
        checkpoint_hash = file_digest(checkpoint)
        if checkpoint_hash != historical["run"]["checkpoint_sha256"]:
            raise ValueError("checkpoint hash mismatch")
        if any(digest(dataset[k]) != digest(historical[k]) for k in dataset):
            raise ValueError("historical dataset differs; choose clean baseline explicitly")
        mode = "HISTORICAL_BYTES_MATCHED"
    return {
        "status": "DATA_BLOCKED" if blockers else "DATA_CONTRACT_CHECKS_PASSED",
        "mode": mode, "dataset_sha256": digest(dataset), "checkpoint_sha256": checkpoint_hash,
        **counts, "partitions": dict(partitions),
        "active_labels_by_partition_head": {p: dict(v) for p, v in signals.items()},
        "blockers": blockers, "training_ready": False, "name_gate": False, "brier": None,
        "remaining": ["SOURCE_AND_REVIEW_EVIDENCE", "TRAINER_CONTRACT_INTEGRATION",
                      "RUNTIME_AND_RESUME_SMOKE", "OPERATOR_EXPERIMENT_GATE"],
        "runtime_proof": "NOT_COMPUTABLE",
        "note": "Declarations and file hashes only; not exact-resume or historical consumption proof.",
    }


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=_strict_object)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--historical-bundle", type=Path)
    parser.add_argument("--checkpoint", type=Path)
    args = parser.parse_args(argv)
    try:
        report = assess(read_json(args.dataset),
                        historical=read_json(args.historical_bundle) if args.historical_bundle else None,
                        checkpoint=args.checkpoint)
    except (OSError, ValueError, UnicodeError):
        print(json.dumps({"status": "INVALID_EVIDENCE", "training_ready": False}))
        return 2
    print(json.dumps(report, sort_keys=True, indent=2))
    return 3 if report["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
