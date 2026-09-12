"""U3 eval harness. Stub/digest vs Spec 004 probe. Trunk-forward is opt-in.

Stub/digest swap has no civilian filler lists, so unbind_token_f1 /
unbind_slot_f1 stay null. Trunk-forward scores the same aligned filler
lists as train val and fills those fields. name_gate stays false.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

from .unbind_metrics import null_unbind_secondary

HEAD_NAMES = ("heads.json", "model.safetensors", "heads.pt")
FORWARD_WEIGHT_NAMES = ("model.safetensors", "heads.pt")
DEFAULT_TRAIN_OUT = Path.home() / ".hyperlex" / "models" / "hyperlex-encoder-modernbert-base-seed"
DEFAULT_TRAIN_OUT_LIVE = Path.home() / ".hyperlex" / "models" / "hyperlex-encoder-modernbert-base-seed-live"
DEFAULT_TRUNK = Path.home() / ".hyperlex" / "models" / "trunks" / "ModernBERT-base"
TYPE_SLOT_TAGS = ("TOKEN", "SLOT", "MARKER")


class TrunkForwardError(RuntimeError):
    """Fail-closed trunk-forward E2. Not a stub miss."""


def _shadow() -> Path:
    return Path(__file__).resolve().parents[1]


def stub_swap(spans: list[dict]) -> float:
    """Chance-like filler guess from text hash. Not Hyperlexical."""
    hit = 0
    for sp in spans:
        items = list(sp["item_ids"])
        guess = []
        for i, it in enumerate(items):
            digest = hashlib.sha256(f"stub-unbind:{i}:{it}".encode()).digest()
            guess.append(items[digest[0] % len(items)])
        if guess == items:
            hit += 1
    return hit / max(1, len(spans))


def model_swap(spans: list[dict], seed: bytes) -> float:
    """Permutation guess seeded by loaded head bytes. Not a trunk forward."""
    hit = 0
    for sp in spans:
        items = list(sp["item_ids"])
        guess = []
        for i, it in enumerate(items):
            digest = hashlib.sha256(seed + f":unbind:{i}:{it}".encode()).digest()
            guess.append(items[digest[0] % len(items)])
        if guess == items:
            hit += 1
    return hit / max(1, len(spans))


def spans_to_unbind_rows(spans: list[dict]) -> list[dict]:
    """Export-shaped 004 rows: positional + type_slot only."""
    rows = []
    for sp in spans:
        items = list(sp["item_ids"])
        tags = list(sp.get("type_tags") or [])
        if len(tags) != len(items):
            tags = [TYPE_SLOT_TAGS[k % len(TYPE_SLOT_TAGS)] for k in range(len(items))]
        rows.append(
            {
                "text": " ".join(items),
                "fillers": items,
                "roles": [f"pos_{k}" for k in range(len(items))],
                "role_scheme": "positional",
            }
        )
        rows.append(
            {
                "text": " ".join(f"{t}:{it}" for t, it in zip(tags, items)),
                "fillers": items,
                "roles": tags,
                "role_scheme": "type_slot",
            }
        )
    return rows


def want_trunk_forward(cli_flag: bool = False) -> bool:
    return bool(cli_flag) or os.environ.get("HYPERLEX_E2_TRUNK_FORWARD") == "1"


def resolve_trunk_dir() -> Path:
    env = os.environ.get("HYPERLEX_TRUNK_DIR", "").strip()
    return Path(env) if env else DEFAULT_TRUNK


def trunk_ready(trunk: Path) -> bool:
    return trunk.is_dir() and (trunk / "config.json").is_file()


def torch_importable() -> bool:
    try:
        return importlib.util.find_spec("torch") is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


def resolve_model_dir(explicit: str | Path | None = None) -> Path | None:
    if explicit not in (None, ""):
        return Path(explicit)
    env = os.environ.get("HYPERLEX_TRAIN_OUT", "").strip()
    if env:
        return Path(env)
    for candidate in (DEFAULT_TRAIN_OUT_LIVE, DEFAULT_TRAIN_OUT):
        if candidate.is_dir():
            return candidate
    return None


def find_weight_file(model_dir: Path) -> Path | None:
    for name in HEAD_NAMES:
        path = model_dir / name
        if path.is_file() and path.stat().st_size > 0:
            return path
    return None


def find_forward_weight_file(model_dir: Path) -> Path | None:
    for name in FORWARD_WEIGHT_NAMES:
        path = model_dir / name
        if path.is_file() and path.stat().st_size > 0:
            return path
    return None


def load_heads_meta(weight_path: Path) -> dict:
    """Torch-free load. JSON fixture or sibling layout/config + file digest."""
    model_dir = weight_path.parent
    meta = {
        "weight_file": weight_path.name,
        "model_id": "hyperlex-encoder-modernbert-base-seed",
        "digest": hashlib.sha256(weight_path.read_bytes()).hexdigest(),
    }
    if weight_path.suffix == ".json":
        blob = json.loads(weight_path.read_text(encoding="utf-8"))
        if not isinstance(blob, dict):
            raise ValueError("heads.json must be an object")
        if blob.get("model_id"):
            meta["model_id"] = str(blob["model_id"])
        if blob.get("weight_digest"):
            meta["digest"] = str(blob["weight_digest"])
        return meta
    for name in ("config.json", "layout.json", "train-receipt.json"):
        side = model_dir / name
        if not side.is_file():
            continue
        try:
            side_blob = json.loads(side.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(side_blob, dict) and side_blob.get("model_id"):
            meta["model_id"] = str(side_blob["model_id"])
            break
    return meta


def _probe_report() -> tuple[dict, list[dict], float, float, float, float]:
    sys.path.insert(0, str(_shadow()))
    from recoverable_structure.fit import run_probe
    from recoverable_structure.fixtures import snapshot

    snap = snapshot("tpr", n=48, length=4, dim=12, seed=7)
    probe = run_probe(snap, schemes=("positional", "type_slot"))
    rec = probe["receipt"]
    pos = next(b for b in rec["schemes"] if b["scheme"] == "positional")
    typ = next(b for b in rec["schemes"] if b["scheme"] == "type_slot")
    test_spans = [snap["spans"][i] for i in probe["test_idx"]]
    stub_acc = stub_swap(test_spans)
    probe_acc = min(float(pos["swap_accuracy"]), float(typ["swap_accuracy"]))
    return rec, test_spans, stub_acc, probe_acc, float(pos["swap_accuracy"]), float(typ["swap_accuracy"])


def require_trunk_forward(model_dir: str | Path | None = None) -> tuple[Path, Path, Path]:
    if not torch_importable():
        raise TrunkForwardError("trunk-forward requested but torch is not importable")
    trunk = resolve_trunk_dir()
    if not trunk_ready(trunk):
        raise TrunkForwardError(
            f"trunk-forward requested but trunk is missing or has no config.json: {trunk}"
        )
    directory = resolve_model_dir(model_dir)
    if directory is None:
        raise TrunkForwardError(
            "trunk-forward requested but no train out dir "
            "(--model-dir / HYPERLEX_TRAIN_OUT / "
            "~/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-live|seed)"
        )
    weight = find_forward_weight_file(directory)
    if weight is None:
        raise TrunkForwardError(
            f"trunk-forward requested but no model.safetensors or heads.pt in {directory}"
        )
    return trunk, directory, weight


def _base_report(rec: dict, stub_acc: float, probe_acc: float, pos_acc: float, typ_acc: float, n_test: int) -> dict:
    return {
        "schema": "hyperlex.hyperlexical.eval_unbind.v0.1",
        "probe_schema": rec.get("schema"),
        "probe_positional_swap": pos_acc,
        "probe_type_slot_swap": typ_acc,
        "probe_swap_min": probe_acc,
        "stub_swap": stub_acc,
        "n_test": n_test,
        "trunk": "answerdotai/ModernBERT-base",
        "trunk_loaded": False,
        "brier": None,
        "forecast_eligible": False,
        **null_unbind_secondary(),
    }


def _digest_or_stub(model_dir: str | Path | None, rec, test_spans, stub_acc, probe_acc, pos_acc, typ_acc) -> dict:
    directory = resolve_model_dir(model_dir)
    weight = find_weight_file(directory) if directory is not None else None
    base = _base_report(rec, stub_acc, probe_acc, pos_acc, typ_acc, len(test_spans))
    if weight is None:
        base.update(
            {
                "e2_pass": stub_acc > probe_acc,
                "model_id": "stub",
                "heads_loaded": False,
                "weight_file": None,
                "model_swap": None,
                "note": (
                    "E2 requires a trained T1 to beat the 004 probe. Stub is "
                    "expected to fail. unbind_token_f1/unbind_slot_f1 are null "
                    "(004 probe swap has no civilian filler lists)."
                ),
            }
        )
        return base
    meta = load_heads_meta(weight)
    model_acc = model_swap(test_spans, meta["digest"].encode("utf-8"))
    base.update(
        {
            "e2_pass": model_acc > probe_acc,
            "model_id": meta["model_id"],
            "heads_loaded": True,
            "weight_file": meta["weight_file"],
            "model_swap": model_acc,
            "note": (
                f"Loaded heads from {weight}. E2 still requires beating the 004 probe. "
                "unbind_token_f1/unbind_slot_f1 stay null (digest path has no "
                "civilian filler lists)."
            ),
        }
    )
    return base


def run_eval(model_dir: str | Path | None = None, trunk_forward: bool = False) -> dict:
    if want_trunk_forward(trunk_forward):
        trunk, directory, weight = require_trunk_forward(model_dir)
        rec, test_spans, stub_acc, probe_acc, pos_acc, typ_acc = _probe_report()
        from .eval_forward import run_unbind_exact

        scored = run_unbind_exact(
            trunk_dir=trunk,
            model_dir=directory,
            weight_path=weight,
            spans=test_spans,
        )
        model_acc = float(scored["unbind_exact"])
        meta = load_heads_meta(weight)
        report = _base_report(rec, stub_acc, probe_acc, pos_acc, typ_acc, len(test_spans))
        report.update(
            {
                "e2_pass": model_acc > probe_acc,
                "model_id": meta["model_id"],
                "heads_loaded": True,
                "weight_file": meta["weight_file"],
                "model_swap": model_acc,
                "unbind_exact": model_acc,
                "n_unbind_eval": scored["n_unbind_eval"],
                "unbind_token_f1": scored.get("unbind_token_f1"),
                "unbind_token_precision": scored.get("unbind_token_precision"),
                "unbind_token_recall": scored.get("unbind_token_recall"),
                "unbind_slot_f1": scored.get("unbind_slot_f1"),
                "trunk_loaded": True,
                "trunk_forward": True,
                "trunk_dir": str(trunk),
                "model_dir": str(directory),
                "name_gate": False,
                "device": scored.get("device"),
                "encoder_trainable_loaded": scored.get("encoder_trainable_loaded", 0),
                "encoder_trainable_present": scored.get("encoder_trainable_present", 0),
                "note": (
                    f"Trunk-forward unbind_exact + token/slot F1 from {weight} vs 004 "
                    "probe_swap_min. Stub/digest leaves F1 null (no civilian filler "
                    "lists). name_gate stays false. "
                    + scored.get(
                        "encoder_note",
                        "Encoder is the local trunk snapshot; heads from train out.",
                    )
                ),
            }
        )
        return report
    rec, test_spans, stub_acc, probe_acc, pos_acc, typ_acc = _probe_report()
    return _digest_or_stub(model_dir, rec, test_spans, stub_acc, probe_acc, pos_acc, typ_acc)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="hyperlexical-eval-unbind")
    p.add_argument("--out", default="")
    p.add_argument(
        "--model-dir",
        default="",
        help="train out dir with heads.json / heads.pt / model.safetensors",
    )
    p.add_argument(
        "--trunk-forward",
        action="store_true",
        help="load local ModernBERT + trained heads and score real unbind_exact (Spark)",
    )
    args = p.parse_args(argv)
    try:
        report = run_eval(model_dir=args.model_dir or None, trunk_forward=args.trunk_forward)
    except TrunkForwardError as exc:
        print(
            json.dumps(
                {
                    "abort": True,
                    "error": str(exc),
                    "brier": None,
                    "e2_pass": False,
                    "trunk_loaded": False,
                    "name_gate": False,
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0 if report["e2_pass"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
