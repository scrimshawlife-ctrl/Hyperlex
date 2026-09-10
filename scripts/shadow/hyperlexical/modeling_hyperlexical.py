"""Load contract for the composed encoder. Torch is lazy. No Hub fetch."""

from __future__ import annotations

import json
from pathlib import Path

from .layout import FAMILIES, HIDDEN, TRUNK


class LoadError(RuntimeError):
    pass


def read_config(model_dir: Path) -> dict:
    path = model_dir / "config.json"
    if not path.is_file():
        raise LoadError("missing config.json")
    return json.loads(path.read_text())


def load_encoder(model_dir: Path, trunk_dir: Path):
    from transformers import AutoModel, AutoTokenizer

    cfg = read_config(model_dir)
    if cfg.get("base_model") != TRUNK:
        raise LoadError(f"unexpected base_model {cfg.get('base_model')}")
    tok = AutoTokenizer.from_pretrained(str(trunk_dir), local_files_only=True)
    enc = AutoModel.from_pretrained(str(trunk_dir), local_files_only=True)
    return tok, enc, cfg
