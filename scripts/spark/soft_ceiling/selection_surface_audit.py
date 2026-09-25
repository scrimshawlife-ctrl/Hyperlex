#!/usr/bin/env python3
"""Eval-only selection-surface audit. No training, no test slices, no gold writes.

Runs inside the rc1 container (image ``lmsysorg/sglang:dev-qwen38-27b-dflash2``),
every Python step via ``scripts/spark/guard.py 0.3``. Does not set
``HYPERLEX_ALLOW_TRAIN`` and strips it if the process inherited it.

See ``RUN_COMMAND`` for the Spark invocation. A second checkout of the same
SHA re-runs with ``--reproduce`` pointed at the first JSON. The published
verdict stays HOLD until those row lists match.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "shadow"))

from hyperlexical.export import export_dataset  # noqa: E402
from hyperlexical.provenance import provenance  # noqa: E402
from hyperlexical.release_set import maybe_release  # noqa: E402
from hyperlexical.selection_surface import (  # noqa: E402
    assert_no_test,
    assemble_report,
    drop_test_rows,
    load_force_keys,
    write_report,
)
from hyperlexical.soft_ceiling import load_jsonl_keys  # noqa: E402

RUN_COMMAND = """\
docker run --rm --gpus all \\
  --name hlx-surface-audit \\
  -w /home/morpheus/Hyperlex \\
  -v /home/morpheus/.cache:/home/morpheus/.cache \\
  -v /home/morpheus/hlx:/home/morpheus/hlx \\
  -v /home/morpheus/Hyperlex:/home/morpheus/Hyperlex \\
  -v /home/morpheus/.hyperlex:/home/morpheus/.hyperlex \\
  -e HOME=/home/morpheus \\
  -e PYTHONPATH=scripts/shadow:scripts/spark/soft_ceiling \\
  -e PYTHONUNBUFFERED=1 \\
  -e TOKENIZERS_PARALLELISM=false \\
  -e HF_HUB_OFFLINE=1 \\
  -e HYPERLEX_OFFLINE=1 \\
  -e HYPERLEX_INCLUDE_LIVE=1 \\
  -e HYPERLEX_RELEASE_SET=1 \\
  -e HYPERLEX_FILLER_FILTER=strict \\
  -e HYPERLEX_TASK_ROUTING=legacy_split \\
  -e HYPERLEX_CUDA_MEM_FRACTION=0.3 \\
  -e HYPERLEX_TRUNK_DIR=/home/morpheus/.hyperlex/models/trunks/ModernBERT-base \\
  lmsysorg/sglang:dev-qwen38-27b-dflash2 \\
  python scripts/spark/guard.py 0.3 selection_surface_audit \\
    --model morph78=/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph78 \\
    --model morph65=/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph65 \\
    --model rc1=/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-rc1 \\
    --trained /home/morpheus/hlx/force_train_morph78_expanded.jsonl \\
    --trained /home/morpheus/hlx/hard_atoms_train_morph78.jsonl \\
    --trained /home/morpheus/hlx/force_train_morph50_expanded.jsonl \\
    --trained /home/morpheus/hlx/hard_atoms_train_morph50.jsonl \\
    --force-train /home/morpheus/hlx/force_train_morph78_expanded.jsonl \\
    --out-dir specs/007-hyperlexical-model/receipts/selection-surface-audit-20260924
"""
# The command string above is the Spark run. It deliberately omits HYPERLEX_ALLOW_TRAIN.

_BANNED_ENV = (
    "HYPERLEX_ALLOW_TRAIN",
    "HYPERLEX_TRAIN_OUT",
    "HYPERLEX_EXPORT_DIR",
    "HYPERLEX_UNBIND_RESIDUAL_DUMP",
    "HYPERLEX_SAVE_BEST_UNBIND",
)


def require_eval_env() -> dict:
    """Fail closed unless the process is the rc1 eval container, not a trainer."""
    stripped = os.environ.pop("HYPERLEX_ALLOW_TRAIN", None)
    if os.environ.get("HYPERLEX_RELEASE_SET") != "1":
        raise SystemExit("REFUSE: HYPERLEX_RELEASE_SET=1 is required")
    if os.environ.get("HYPERLEX_INCLUDE_LIVE") != "1":
        raise SystemExit("REFUSE: HYPERLEX_INCLUDE_LIVE=1 is required")
    filler = os.environ.get("HYPERLEX_FILLER_FILTER", "").strip()
    if filler not in ("", "strict"):
        raise SystemExit("REFUSE: HYPERLEX_FILLER_FILTER must be strict")
    routing = os.environ.get("HYPERLEX_TASK_ROUTING", "").strip()
    if routing not in ("", "legacy_split"):
        raise SystemExit("REFUSE: HYPERLEX_TASK_ROUTING must be legacy_split")
    return {"allow_train": False, "allow_train_stripped": stripped is not None}


def _refuse_holdout(path: Path) -> None:
    name = path.name
    if "holdout" in name or name.startswith("holdout-scores"):
        raise SystemExit(f"REFUSE: will not read holdout path {path}")


def _apply_env_file(path: Path) -> None:
    _refuse_holdout(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    for key in _BANNED_ENV:
        payload.pop(key, None)
    os.environ.update({str(k): str(v) for k, v in payload.items()})


def _model_root(model: Path) -> Path:
    if (model / "model.safetensors").is_file():
        return model
    if (model / "best" / "model.safetensors").is_file():
        return model / "best"
    return model


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_rows() -> tuple[list[dict], dict, int]:
    bundle = export_dataset(REPO, include_live=True)
    released, stats = maybe_release(bundle["rows"])
    # Share-alike text can originate on any split; after that filter, drop test.
    kept, n_test = drop_test_rows(released)
    del released
    return kept, stats, n_test


def _score_model(name: str, model_dir: Path, rows: list[dict], trunk: str) -> tuple[dict, str]:
    assert_no_test(rows, where=f"score {name}")
    if any(row.get("split") != "val" for row in rows):
        raise SystemExit(f"REFUSE: {name} score set is not val-only")
    import torch
    from torch import nn
    from transformers import AutoModel, AutoTokenizer

    from hyperlexical.eval_forward import (
        _load_filler_head,
        _load_maps,
        _weight_parts,
        apply_encoder_trainable,
        predict_unbind_pairs,
    )
    from hyperlexical.layout import HIDDEN

    torch.manual_seed(0)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(0)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    scored = [row for row in rows if row.get("fillers")]
    root = _model_root(model_dir)
    weight = root / "model.safetensors"
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tok = AutoTokenizer.from_pretrained(trunk, local_files_only=True)
    enc = AutoModel.from_pretrained(trunk, local_files_only=True)
    filler_state, encoder_tensors, heads_blob = _weight_parts(weight, torch)
    apply_encoder_trainable(enc, encoder_tensors)
    maps = _load_maps(model_dir if (model_dir / "layout.json").is_file() else root, heads_blob)
    head = _load_filler_head(nn, int(getattr(enc.config, "hidden_size", HIDDEN)), filler_state, maps)
    enc.to(dev)
    head.to(dev)
    pairs = predict_unbind_pairs(enc, head, tok, maps, scored, dev) if scored else []
    if len(pairs) != len(scored):
        raise SystemExit(f"REFUSE: {name} prediction count {len(pairs)} != {len(scored)} val rows")
    del enc, head
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return {row["row_id"]: pair for row, pair in zip(scored, pairs)}, _file_sha256(weight)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", action="append", default=[], help="NAME=DIR (morph78, morph65, rc1)")
    parser.add_argument("--trained", action="append", default=[], help="force/hard jsonl for the n=51 clean surface")
    parser.add_argument("--force-train", default="", help="morph78 force-train jsonl for the n=164 and n=140 surfaces")
    parser.add_argument("--trunk", default=os.environ.get("HYPERLEX_TRUNK_DIR", str(Path.home() / ".hyperlex/models/trunks/ModernBERT-base")))
    parser.add_argument("--env", default="", help="optional env json; ALLOW_TRAIN and train output keys are stripped")
    parser.add_argument("--reproduce", default="", help="prior selection-surface-audit.json from a second checkout")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--print-command", action="store_true")
    args = parser.parse_args(argv)
    if args.print_command:
        print(RUN_COMMAND, end="")
        return 0
    if args.env:
        _apply_env_file(Path(args.env))
    env_note = require_eval_env()
    if not args.model:
        raise SystemExit("REFUSE: at least one --model NAME=DIR")
    specs: list[tuple[str, Path]] = []
    for spec in args.model:
        if "=" not in spec:
            raise SystemExit(f"REFUSE: --model must be NAME=DIR, got {spec!r}")
        name, raw = spec.split("=", 1)
        path = Path(raw)
        _refuse_holdout(path)
        specs.append((name, path))
    for raw in args.trained:
        _refuse_holdout(Path(raw))
    if args.force_train:
        _refuse_holdout(Path(args.force_train))
    if args.reproduce:
        _refuse_holdout(Path(args.reproduce))

    kept, stats, n_test = _load_rows()
    trained = set()
    for raw in args.trained:
        trained |= load_jsonl_keys(raw)
    force = load_force_keys(args.force_train) if args.force_train else None
    reproduce_rows = None
    if args.reproduce:
        prior = json.loads(Path(args.reproduce).read_text(encoding="utf-8"))
        reproduce_rows = prior.get("rows")
        if not isinstance(reproduce_rows, list):
            raise SystemExit("REFUSE: --reproduce JSON has no rows list")

    predictions: dict[str, dict] = {}
    weights: dict[str, str] = {}
    # Score after the report's row set is fixed: val only, test already dropped.
    from hyperlexical.selection_surface import annotate_rows, release_val_rows

    val = annotate_rows(release_val_rows(kept), [row for row in kept if row.get("split") == "train"])
    for name, model_dir in specs:
        predictions[name], weights[name] = _score_model(name, model_dir, val, args.trunk)

    report = assemble_report(
        kept,
        predictions,
        trained_keys=trained if args.trained else None,
        force_keys=force,
        reproduce_rows=reproduce_rows,
        release_set=stats,
        n_test_discarded=n_test,
    )
    prov = provenance(REPO)
    report["code_commit"] = prov["code_commit"]
    report["code_tree_sha256"] = prov["code_tree_sha256"]
    report["weights_sha256"] = weights
    report["allow_train_stripped"] = env_note["allow_train_stripped"]
    report["models_named"] = [name for name, _path in specs]
    json_path, md_path = write_report(report, args.out_dir)
    print(json.dumps({
        "json": str(json_path),
        "summary": str(md_path),
        "verdict": report["verdict"]["published"],
        "candidate": report["verdict"]["candidate"],
        "n_release_val": report["release_val"]["n_rows"],
        "n_test_discarded": n_test,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
