#!/usr/bin/env python3
"""Read-only row flags for a fresh holdout draw. No training, no GPU, no test scoring.

Reads an export JSONL and writes ``flags.jsonl`` plus ``flags_summary.json``
under ``--out-dir``. Does not rebuild the export, relabel a row, or promote
gold. Does not import the holdout scorer or load a model.

Refuses to run when ``HYPERLEX_ALLOW_TRAIN`` is set. Requires
``HYPERLEX_OFFLINE=1`` so the process stays off the network.

``split=test`` rows are discarded by the split field before text, gold, or
hashes are read. ``--trained`` and ``--holdout-ids`` are optional. Without
the training-machine files, spent text from those files is listed under
``not_computed`` and is not guessed.

See ``RUN_COMMAND``. Output is counts, row ids, and normalized-text hashes.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "shadow"))

from hyperlexical.flag_rows import file_sha256, flag_dataset, load_export_jsonl, write_flags  # noqa: E402
from hyperlexical.heldout_census import load_holdout_ids, load_trained_files  # noqa: E402
from hyperlexical.provenance import provenance  # noqa: E402

RUN_COMMAND = """\
docker run --rm \\
  --name hlx-row-flags \\
  -w /home/morpheus/Hyperlex \\
  -v /home/morpheus/Hyperlex:/home/morpheus/Hyperlex \\
  -e HOME=/home/morpheus \\
  -e PYTHONPATH=scripts/shadow:scripts/spark/soft_ceiling \\
  -e PYTHONUNBUFFERED=1 \\
  -e HF_HUB_OFFLINE=1 \\
  -e HYPERLEX_OFFLINE=1 \\
  lmsysorg/sglang:dev-qwen38-27b-dflash2 \\
  python scripts/spark/soft_ceiling/flag_rows.py \\
    --export specs/007-hyperlexical-model/exports/civilian.v0.1.jsonl \\
    --out-dir /tmp/hlx-row-flags
"""
# CPU-only: no --gpus, no guard.py, no HYPERLEX_ALLOW_TRAIN.
# Trained JSONL and the holdout id list live on the training machine.
# Omit them and flags_summary.json lists that text under not_computed.


def require_flag_env() -> None:
    """Fail closed. Training permission is a refusal, not something to strip."""
    if "HYPERLEX_ALLOW_TRAIN" in os.environ:
        raise SystemExit("REFUSE: HYPERLEX_ALLOW_TRAIN is set")
    if os.environ.get("HYPERLEX_OFFLINE") != "1":
        raise SystemExit("REFUSE: HYPERLEX_OFFLINE=1 is required")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--export", default="", help="export JSONL to flag; not rebuilt")
    parser.add_argument(
        "--trained",
        action="append",
        default=[],
        help="force/hard JSONL or a checkpoint train receipt (repeatable)",
    )
    parser.add_argument(
        "--holdout-ids",
        default="",
        help="holdout manifest; only its string ID list is read",
    )
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--print-command", action="store_true")
    args = parser.parse_args(argv)
    if args.print_command:
        print(RUN_COMMAND, end="")
        return 0
    require_flag_env()
    if not args.export:
        raise SystemExit("REFUSE: --export is required")
    if not args.out_dir:
        raise SystemExit("REFUSE: --out-dir is required")
    export_path = Path(args.export)
    if not export_path.is_file():
        raise SystemExit(f"REFUSE: --export is not a file: {export_path}")

    rows = load_export_jsonl(export_path)
    trained_rows, trained_files = load_trained_files(args.trained) if args.trained else ([], [])
    if args.holdout_ids:
        holdout_ids, id_list_present = load_holdout_ids(args.holdout_ids)
        holdout_sha = file_sha256(args.holdout_ids)
    else:
        holdout_ids, id_list_present, holdout_sha = set(), False, None
    prov = provenance(REPO)
    records, summary = flag_dataset(
        rows,
        trained_rows,
        holdout_ids,
        id_list_present=id_list_present,
        trained_supplied=bool(args.trained),
        holdout_supplied=bool(args.holdout_ids),
        code_commit=prov.get("code_commit"),
        code_tree_sha256=prov.get("code_tree_sha256"),
        input_sha256={
            "export": file_sha256(export_path),
            "trained": [file_sha256(path) for path in trained_files],
            "holdout_ids": holdout_sha,
        },
    )
    del rows
    flags_path, summary_path = write_flags(records, summary, args.out_dir)
    print(json.dumps({
        "flags": str(flags_path),
        "summary": str(summary_path),
        "n_rows": summary["n_rows"],
        "n_train": summary["n_train"],
        "n_val": summary["n_val"],
        "n_test_discarded": summary["n_test_discarded"],
        "n_holdout_ineligible": summary["n_holdout_ineligible"],
        "not_computed": summary["not_computed"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
