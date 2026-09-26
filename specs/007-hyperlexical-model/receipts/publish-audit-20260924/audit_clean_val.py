import json, os, sys
from pathlib import Path
sys.path.insert(0, "/home/morpheus/Hyperlex/scripts/shadow")
import torch
from transformers import AutoModel, AutoTokenizer
from hyperlexical.eval_forward import _weight_parts, _load_maps, _load_filler_head, apply_encoder_trainable, score_unbind_exact
from torch import nn
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
rows = json.loads(Path("/home/morpheus/hlx/audit-clean-val.json").read_text())
out = {}
for name in ("morph78", "morph65"):
    M = Path(f"/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-{name}")
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tok = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    enc = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    fs, et, hb = _weight_parts(M / "model.safetensors", torch)
    apply_encoder_trainable(enc, et)
    maps = _load_maps(M, hb)
    fh = _load_filler_head(nn, 768, fs, maps)
    enc.to(dev); fh.to(dev)
    s = score_unbind_exact(enc, fh, tok, maps, rows, dev)
    out[name] = {"unbind_exact": s.get("unbind_exact"), "n": s.get("n_unbind_eval")}
print("AUDIT_CLEAN", json.dumps(out))
Path("/home/morpheus/hlx/audit-clean-val-scores.json").write_text(json.dumps(out, indent=2))
