#!/usr/bin/env python3
"""Dry-run a train recipe's data preparation and compare with a train receipt.

No torch, no GPU, no writes. Mirrors the data-prep head of ``loop.run_loop``
(export → classify routing → ``prepare_unbind_splits``) under a recorded
``HYPERLEX_*`` environment, then diffs the counts and ``data_sha256`` against
the receipt. Publish-readiness step 1b.

  python scripts/spark/soft_ceiling/equivalence_check.py \
      --env scripts/spark/soft_ceiling/morph78-train-env.json \
      --receipt ~/.hyperlex/models/<pin>/train-receipt.json --out OUT.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

KEYS = (
    "data_sha256",
    "live_included",
    "n_train_classify",
    "n_train_unbind",
    "n_unbind_force_train",
    "n_unbind_force_train_keys",
    "n_unbind_val_after_force_train",
    "n_unbind_hard_atoms_matched",
    "n_unbind_hard_extra_copies",
    "n_unbind_observed",
    "n_unbind_inferred",
    "n_unbind_morph_negatives",
)


def content_sha256(rows: list[dict]) -> str:
    """Row-content hash with typology order normalized (receipt data_sha256 is order-sensitive)."""
    import hashlib

    norm = [{**r, "typology": sorted(r.get("typology") or [])} for r in rows]
    blob = "\n".join(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in norm)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def prepare(root: Path) -> dict:
    from hyperlexical.export import export_dataset
    from hyperlexical.loop import prepare_unbind_splits

    import inspect

    from hyperlexical import loop

    bundle = export_dataset(root, include_live=True)
    legacy = getattr(loop, "task_routing", None) and loop.task_routing() == "legacy_split"
    if "route_rows(bundle" in inspect.getsource(loop.run_loop) and not legacy:
        from hyperlexical.training_routing import route_rows

        routed, _ = route_rows(bundle["rows"])
        classify_tr = routed["classify"]["train"]
        routing = "route_rows"
    else:
        classify_tr = [r for r in bundle["rows"] if r["task"] == "classify" and r["split"] == "train"]
        routing = "split_filter"
    unbind_tr, _unbind_va, recipe = prepare_unbind_splits(bundle["rows"])
    got = {
        "data_sha256": bundle["sha256"],
        "live_included": bundle["counts"].get("live_included", 0),
        "n_train_classify": len(classify_tr),
        "n_train_unbind": len(unbind_tr),
    }
    for k in KEYS:
        if k not in got and k in recipe:
            got[k] = recipe[k]
    got["classify_routing"] = routing
    got["_rows"] = bundle["rows"]
    return got


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--env", required=True)
    p.add_argument("--receipt", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--root", default=str(REPO), help="repo checkout whose code/data to use")
    p.add_argument("--train-export", default="", help="civilian.v0.1.jsonl written by the training run")
    args = p.parse_args(argv)
    # Import code from the checkout under test, not from this script's repo.
    sys.path.insert(0, str(Path(args.root) / "scripts" / "shadow"))
    for name in [m for m in sys.modules if m == "hyperlexical" or m.startswith("hyperlexical.")]:
        del sys.modules[name]
    env = json.loads(Path(args.env).read_text())
    os.environ.update(env)
    receipt = json.loads(Path(args.receipt).read_text())
    got = prepare(Path(args.root))
    rows = got.pop("_rows")
    got["data_content_sha256"] = content_sha256(rows)
    content_match = None
    if args.train_export:
        train_rows = [json.loads(l) for l in Path(args.train_export).read_text().splitlines() if l.strip()]
        got["train_export_content_sha256"] = content_sha256(train_rows)
        content_match = got["train_export_content_sha256"] == got["data_content_sha256"]
    keys = [k for k in KEYS if not (k == "data_sha256" and content_match)]
    diff = {k: {"receipt": receipt.get(k), "now": got.get(k)} for k in keys if receipt.get(k) != got.get(k)}
    import hyperlexical

    code_dir = str(Path(hyperlexical.__file__).resolve().parent)
    try:
        from hyperlexical.provenance import provenance

        prov = provenance(Path(args.root))
    except ImportError:
        prov = {"code_commit": None, "code_tree_sha256": None}
    out = {
        "schema": "hyperlex.recipe_equivalence.v0.1",
        "receipt": args.receipt,
        "root": args.root,
        "equivalent": not diff,
        "data_content_match_train_export": content_match,
        "diff": diff,
        "now": got,
        "code_dir": code_dir,
        **prov,
    }
    Path(args.out).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"equivalent": out["equivalent"], "content_match": content_match, "diff": diff, "classify_routing": got["classify_routing"], "code_dir": code_dir}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
