#!/usr/bin/env python3
"""Read-only held-out feasibility census. No training, no GPU, no test scoring.

Counts release-pool rows that pass all five admission rules and writes
``census.json`` under ``--out-dir``. Does not write a split, a manifest, or
gold. Does not import the holdout scorer or load a model.

Refuses to run when ``HYPERLEX_ALLOW_TRAIN`` is set. Requires
``HYPERLEX_OFFLINE=1`` so the process stays off the network.

See ``RUN_COMMAND`` for the Spark invocation. A second checkout of the same
SHA re-runs with ``--reproduce`` pointed at the first ``census.json``. The
published verdict stays HOLD until those admitted-ID hashes match.

The holdout manifest is opened only for a string ID list (``row_ids`` or
``ids``). The committed rc1 manifest stores slice hashes, not that list, so
an id match excludes nobody until an ID list is present. Rule 5 also
excludes a row whose normalized text matches a holdout row or a ``--trained``
row, including a demoted or re-tasked twin of a spent id. ``split=test``
rows are discarded by the split field before release filtering, and their
text is not hashed. Rebuilding the ID list from test rows is refused.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "shadow"))

from hyperlexical.export import export_dataset  # noqa: E402
from hyperlexical.heldout_census import census_rows, load_holdout_ids, load_trained_files, write_census  # noqa: E402
from hyperlexical.provenance import provenance  # noqa: E402
from hyperlexical.release_set import maybe_release  # noqa: E402
from hyperlexical.selection_surface import drop_test_rows  # noqa: E402

RUN_COMMAND = """\
docker run --rm \\
  --name hlx-heldout-census \\
  -w /home/morpheus/Hyperlex \\
  -v /home/morpheus/.cache:/home/morpheus/.cache \\
  -v /home/morpheus/hlx:/home/morpheus/hlx \\
  -v /home/morpheus/Hyperlex:/home/morpheus/Hyperlex \\
  -v /home/morpheus/.hyperlex:/home/morpheus/.hyperlex \\
  -e HOME=/home/morpheus \\
  -e PYTHONPATH=scripts/shadow:scripts/spark/soft_ceiling \\
  -e PYTHONUNBUFFERED=1 \\
  -e HF_HUB_OFFLINE=1 \\
  -e HYPERLEX_OFFLINE=1 \\
  -e HYPERLEX_INCLUDE_LIVE=1 \\
  -e HYPERLEX_RELEASE_SET=1 \\
  -e HYPERLEX_FILLER_FILTER=strict \\
  -e HYPERLEX_TASK_ROUTING=legacy_split \\
  lmsysorg/sglang:dev-qwen38-27b-dflash2 \\
  python scripts/spark/soft_ceiling/heldout_census.py \\
    --trained /home/morpheus/hlx/force_train_morph78_expanded.jsonl \\
    --trained /home/morpheus/hlx/hard_atoms_train_morph78.jsonl \\
    --trained /home/morpheus/hlx/force_train_morph50_expanded.jsonl \\
    --trained /home/morpheus/hlx/hard_atoms_train_morph50.jsonl \\
    --trained /home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph78/train-receipt.json \\
    --trained /home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph65/train-receipt.json \\
    --trained /home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-rc1/train-receipt.json \\
    --holdout-manifest specs/007-hyperlexical-model/receipts/rc1-prereg-20260924/holdout-manifest-rc1.json \\
    --out-dir specs/007-hyperlexical-model/receipts/heldout-census-20260924
"""
# CPU-only: no --gpus, no guard.py, no HYPERLEX_ALLOW_TRAIN.


def require_census_env() -> None:
    """Fail closed. Training permission is a refusal, not something to strip."""
    if "HYPERLEX_ALLOW_TRAIN" in os.environ:
        raise SystemExit("REFUSE: HYPERLEX_ALLOW_TRAIN is set")
    if os.environ.get("HYPERLEX_OFFLINE") != "1":
        raise SystemExit("REFUSE: HYPERLEX_OFFLINE=1 is required")
    if os.environ.get("HYPERLEX_RELEASE_SET") != "1":
        raise SystemExit("REFUSE: HYPERLEX_RELEASE_SET=1 is required")
    if os.environ.get("HYPERLEX_INCLUDE_LIVE") != "1":
        raise SystemExit("REFUSE: HYPERLEX_INCLUDE_LIVE=1 is required")


def load_release_pool() -> tuple[list[dict], dict]:
    """Export the pool, drop ``split=test`` by that field, then release-filter.

    ``release_rows`` reads text and fillers. Test rows must already be gone,
    or a share-alike test phrase can drop a val candidate and enter
    ``release_content_sha256``. The drop count is attached for the report
    and removed before that dict is stored; the dropped rows are not hashed.
    """
    bundle = export_dataset(REPO, include_live=True)
    rows = bundle.pop("rows")
    kept, n_test = drop_test_rows(rows)
    del rows
    released, stats = maybe_release(kept)
    stats = dict(stats)
    stats["n_test_dropped_before_release"] = n_test
    stats["test_dropped_before_release_filtering"] = True
    return released, stats


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--trained",
        action="append",
        default=[],
        help="force/hard JSONL or a checkpoint train receipt (repeatable)",
    )
    parser.add_argument("--holdout-manifest", default="", help="rc1 manifest; only its ID list is read")
    parser.add_argument("--reproduce", default="", help="prior census.json from a second checkout of this SHA")
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--print-command", action="store_true")
    args = parser.parse_args(argv)
    if args.print_command:
        print(RUN_COMMAND, end="")
        return 0
    require_census_env()
    if not args.out_dir:
        raise SystemExit("REFUSE: --out-dir is required")
    if not args.holdout_manifest:
        raise SystemExit("REFUSE: --holdout-manifest is required")
    if args.reproduce and "holdout" in Path(args.reproduce).name.lower():
        raise SystemExit(f"REFUSE: --reproduce must be a census.json, not {args.reproduce}")

    holdout_ids, id_list_present = load_holdout_ids(args.holdout_manifest)
    trained_rows, trained_files = load_trained_files(args.trained)
    pool, stats = load_release_pool()
    stats = dict(stats)
    n_test_before = stats.pop("n_test_dropped_before_release", None)
    stats.pop("test_dropped_before_release_filtering", None)
    prior = None
    if args.reproduce:
        prior_path = Path(args.reproduce)
        if not prior_path.is_file():
            raise SystemExit(f"REFUSE: --reproduce is not a file: {prior_path}")
        prior = json.loads(prior_path.read_text(encoding="utf-8"))
        if "admitted_ids_sha256" not in prior or "code_commit" not in prior:
            raise SystemExit("REFUSE: --reproduce JSON has no admitted_ids_sha256 and code_commit")
    prov = provenance(REPO)
    report = census_rows(
        pool,
        trained_rows,
        holdout_ids,
        id_list_present=id_list_present,
        n_test_discarded=n_test_before,
        n_test_dropped_before_release=n_test_before,
        release_set=stats,
        trained_files=trained_files,
        code_commit=prov.get("code_commit"),
        code_tree_sha256=prov.get("code_tree_sha256"),
        prior=prior,
    )
    del pool
    path = write_census(report, args.out_dir)
    print(json.dumps({
        "json": str(path),
        "verdict": report["verdict"]["published"],
        "candidate": report["verdict"]["candidate"],
        "reproduce": report["verdict"]["reproduce"],
        "n_admitted": report["n_admitted"],
        "max_source_share": report["admitted"]["max_source_share"],
        "admitted_ids_sha256": report["admitted_ids_sha256"],
        "n_test_discarded": report["n_test_discarded"],
        "holdout_id_list_present": report["holdout"]["id_list_present"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
