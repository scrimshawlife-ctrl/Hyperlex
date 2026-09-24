#!/usr/bin/env python3
"""Build a Hub-shaped folder for a pin and check the remote-code loader offline.

Publish-readiness step 6a. No network, no upload. Copies the pin weights, the
card config (plus the pin's vocab and calibration), the tokenizer from the local
trunk, and ``modeling_hyperlexical.py`` into ``--out``; loads it with
``AutoModel.from_pretrained(..., trust_remote_code=True, trunk=...)``; and checks
lineage/filler parity with ``hyperlexical.infer_model`` on sample inputs.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "shadow"))
PKG = REPO / "specs" / "007-hyperlexical-model" / "hf-package"
SAMPLES = ["rizz", "no cap fr", "touch grass", "bet that up", "have fun staying poor"]
TOKENIZER_FILES = ("tokenizer.json", "tokenizer_config.json", "special_tokens_map.json")


def build_folder(model: Path, trunk: Path, out: Path, calibration: dict | None) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    pin_cfg = json.loads((model / "config.json").read_text())
    cfg = json.loads((PKG / "config.json").read_text())
    cfg["role_vocab"] = pin_cfg["role_vocab"]
    cfg["filler_vocab"] = pin_cfg["filler_vocab"]
    cfg["auto_map"] = {
        "AutoConfig": "modeling_hyperlexical.HyperlexicalConfig",
        "AutoModel": "modeling_hyperlexical.HyperlexicalModel",
    }
    if calibration:
        cfg["lineage_temperature"] = calibration["temperature"]
        cfg["abstain_threshold"] = calibration["abstain_threshold"]
    (out / "config.json").write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n")
    shutil.copy2(PKG / "modeling_hyperlexical.py", out / "modeling_hyperlexical.py")
    shutil.copy2(model / "model.safetensors", out / "model.safetensors")
    for name in TOKENIZER_FILES:
        if (trunk / name).is_file():
            shutil.copy2(trunk / name, out / name)
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--trunk", required=True)
    p.add_argument("--calibration", default="")
    p.add_argument("--out", required=True)
    p.add_argument("--report", required=True)
    args = p.parse_args(argv)
    cal = json.loads(Path(args.calibration).read_text())["all"] if args.calibration else None
    folder = build_folder(Path(args.model), Path(args.trunk), Path(args.out), cal)

    import torch
    from transformers import AutoModel, AutoTokenizer
    from hyperlexical.infer_model import infer

    hub = AutoModel.from_pretrained(str(folder), trust_remote_code=True, trunk=args.trunk, local_files_only=True)
    tok = AutoTokenizer.from_pretrained(str(folder), local_files_only=True)
    fams = [hub.config.id2label[i] if i in hub.config.id2label else hub.config.id2label[str(i)] for i in range(len(hub.config.id2label))]
    rows = []
    for text in SAMPLES:
        with torch.no_grad():
            out = hub(**tok([text], return_tensors="pt", truncation=True, max_length=64))
        hub_family = fams[int(out["lineage_logits"][0].argmax())]
        ref = infer(text, model_dir=Path(args.model), trunk_dir=Path(args.trunk))
        rows.append({"text": text, "hub_family": hub_family, "infer_family": ref["lineage_family"], "match": hub_family == ref["lineage_family"]})
    report = {
        "schema": "hyperlex.hub_loader_check.v0.1",
        "folder": str(folder),
        "files": sorted(p.name for p in folder.iterdir()),
        "samples": rows,
        "parity": all(r["match"] for r in rows),
        "lineage_temperature": hub.config.lineage_temperature,
        "network": False,
        "uploaded": False,
    }
    Path(args.report).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["parity"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
