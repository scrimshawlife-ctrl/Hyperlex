"""Read-only applicability invariance diagnostic for the surface checkpoint.

Replays validation rows through the saved weights. Does not train, does not
score the evaluation reserve, does not rewrite the historical surface report
or SETTLEMENT.json, and does not move BEST.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
EXPORT = Path("/home/morpheus/hlx-private/classification-v2-surface-20260929/civilian.v0.3.jsonl")
EXPORT_SHA = "c4677011ea61f135c8fb82bed9d973dffe3a5db582d34421403e71498c5fd243"
OUT = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-classification-v2-surface"
)
PRIMARY_SHA = "e3c0545424e7fe9ca93a9b8c5e423698974f5cecab405ed99590c8293a5bb463"
BEST_DIR = Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004")
BEST_WEIGHTS = BEST_DIR / "model.safetensors"
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
PRIVATE = Path("/home/morpheus/hlx-private/classification-v2-train-surface-20260929")
DESTINATION = PRIVATE / "INVARIANCE_DIAGNOSTIC.json"
TEMPERATURE = 1.47
EXPECTED_N = 598
EXPECTED_GLOBAL = 0.42150272051315185
EXPECTED_FAMILY_MACRO = 0.1960828268105939
STORED_MEANS = {
    "FAMILY_PRESENT/ATOM": 0.7852956405720147,
    "FAMILY_PRESENT/PROSE": 0.911294776451496,
    "NONE/ATOM": 0.1279144847425886,
    "NONE/PROSE": 0.12663721872007336,
}
STORED_SUPPORT = {
    "FAMILY_PRESENT/ATOM": 155,
    "FAMILY_PRESENT/PROSE": 135,
    "NONE/ATOM": 268,
    "NONE/PROSE": 31,
}
STORED_F1 = {
    "FAMILY_PRESENT/ATOM": 0.8453608247422681,
    "FAMILY_PRESENT/PROSE": 0.9776119402985074,
    "NONE/ATOM": 0.918918918918919,
    "NONE/PROSE": 0.90625,
}
STORED_FAMILY_BY_SURFACE = {
    "ATOM": 0.226814225201322,
    "PROSE": 0.2664313342411146,
}
SEALED = (
    OUT / "classification-v2-surface.json",
    OUT / "classification-v2-calibration.json",
    OUT / "model.safetensors",
    PRIVATE / "SETTLEMENT.json",
    BEST_WEIGHTS,
)

sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sudo_sha256(path: Path) -> str:
    completed = subprocess.run(
        ["sudo", "-n", "sha256sum", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.split()[0]


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def sealed_digests() -> dict[str, str]:
    return {str(path): sudo_sha256(path) for path in SEALED}


def inner() -> int:
    import torch
    from safetensors.torch import load_file
    from transformers import AutoModel, AutoTokenizer

    from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY
    from hyperlexical.classification_v2_surface import (
        applicability_invariance,
        applicability_surface_report,
        calibrated_present_probability,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.layout import HIDDEN, MAX_LEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors
    from hyperlexical.training_routing import route_rows

    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if sha256_file(OUT / "model.safetensors") != PRIMARY_SHA:
        fail("primary checkpoint changed")
    if sha256_file(EXPORT) != EXPORT_SHA:
        fail("surface export changed")
    stored = json.loads((OUT / "classification-v2-surface.json").read_text(encoding="utf-8"))
    calibration = json.loads((OUT / "classification-v2-calibration.json").read_text(encoding="utf-8"))
    if stored.get("pass") is not False:
        fail("historical surface guard is no longer FAIL")
    if abs(float(stored["corr_word_count_p_family_present"]) - EXPECTED_GLOBAL) > 1e-12:
        fail("historical global correlation moved")
    if abs(float(calibration["applicability_temperature"]) - TEMPERATURE) > 1e-12:
        fail("calibration temperature moved")
    if calibration.get("reserve_used") or calibration.get("training_rows_used"):
        fail("calibration artifact used the reserve or the training split")
    cells = stored["applicability_by_cell"]
    for name, expected in STORED_MEANS.items():
        if abs(float(cells[name]["mean_p_family_present"]) - expected) > 1e-12:
            fail(f"stored mean moved for {name}")
        if int(cells[name]["support"]) != STORED_SUPPORT[name]:
            fail(f"stored support moved for {name}")
        if abs(float(cells[name]["applicability_f1"]) - STORED_F1[name]) > 1e-12:
            fail(f"stored f1 moved for {name}")
    for form, expected in STORED_FAMILY_BY_SURFACE.items():
        if abs(float(stored["family_macro_f1_by_surface"][form]) - expected) > 1e-12:
            fail(f"stored family macro moved for {form}")
    receipt = json.loads((OUT / "train-receipt.json").read_text(encoding="utf-8"))
    best = receipt.get("val_best") or {}
    if abs(float(best["active_family_macro_f1"]) - EXPECTED_FAMILY_MACRO) > 1e-12:
        fail("stored active-family macro-F1 moved")
    rows = []
    with EXPORT.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    validation = route_rows(rows)[0]["classify"]["val"]
    prohibited = {"held_out", "evaluation_reserve", "settlement", "measurement"}
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("invariance replay requires the same CUDA forward as training")
    tokenizer = AutoTokenizer.from_pretrained(TRUNK)
    tokenizer.padding_side = "right"
    encoder = AutoModel.from_pretrained(TRUNK)
    freeze_encoder(encoder)
    warm = split_weight_tensors(load_file(str(BEST_WEIGHTS)))
    tensors = split_weight_tensors(load_file(OUT / "model.safetensors"))
    warm_loaded = apply_encoder_trainable(encoder, warm["encoder"])
    trained_loaded = apply_encoder_trainable(encoder, tensors["encoder"])
    if warm_loaded["loaded"] != 48 or trained_loaded["loaded"] != 12:
        fail(f"encoder overlay {warm_loaded['loaded']}/{trained_loaded['loaded']} != 48/12")
    applicability = torch.nn.Linear(HIDDEN, 2)
    applicability.load_state_dict(tensors["applicability"])
    encoder.to(device).eval()
    applicability.to(device).eval()
    records = []
    with torch.no_grad():
        for row in validation:
            if row.get("split") != "val" or row.get("evaluation_reserve") or row.get("held_out"):
                fail("replay refused a non-validation row")
            if row.get("surface") in prohibited:
                fail("replay refused a reserved surface")
            lineage = row.get("lineage")
            if lineage not in ACTIVE_FAMILY_VOCABULARY and lineage != "none":
                continue
            encoded = tokenizer(
                [row["text"]],
                padding=True,
                truncation=True,
                max_length=MAX_LEN,
                return_tensors="pt",
            )
            encoded = {key: value.to(device) for key, value in encoded.items()}
            pooled = encoder(**encoded).last_hidden_state[:, 0]
            logits = [float(value) for value in applicability(pooled)[0].detach().cpu()]
            probability = calibrated_present_probability(logits, TEMPERATURE)
            records.append(
                {
                    "lineage": lineage,
                    "prediction": "FAMILY_PRESENT" if logits[1] > logits[0] else "NONE",
                    "probability": probability,
                    "text": row.get("text"),
                }
            )
    if len(records) != EXPECTED_N:
        fail(f"validation applicability rows {len(records)} != {EXPECTED_N}")
    report = applicability_surface_report(records)
    invariance = applicability_invariance(records)
    deltas = {}
    for name, expected in STORED_MEANS.items():
        got = report["applicability_by_cell"][name]["mean_p_family_present"]
        deltas[name] = None if got is None else got - expected
        if got is None or abs(got - expected) > 1e-4:
            fail(f"replay mean drifted for {name}: {got} vs {expected}")
        if int(report["applicability_by_cell"][name]["support"]) != STORED_SUPPORT[name]:
            fail(f"replay support drifted for {name}")
        got_f1 = report["applicability_by_cell"][name]["applicability_f1"]
        if got_f1 is None or abs(got_f1 - STORED_F1[name]) > 1e-6:
            fail(f"replay f1 drifted for {name}: {got_f1}")
    if report.get("reserve_used"):
        fail("replay report marked the reserve")
    status = "RESOLVED" if invariance["pass"] else "OPEN"
    artifact = {
        "active_family_discrimination": {
            "active_family_macro_f1": EXPECTED_FAMILY_MACRO,
            "atom_family_macro_f1": STORED_FAMILY_BY_SURFACE["ATOM"],
            "prose_family_macro_f1": STORED_FAMILY_BY_SURFACE["PROSE"],
            "status": "UNRESOLVED",
        },
        "applicability_surface_shortcut": status,
        "checkpoint_identity": PRIMARY_SHA,
        "encoder_overlay": {"production": 48, "surface": 12},
        "historical_run": {
            "global_abs_correlation": EXPECTED_GLOBAL,
            "guard": "abs(corr(word_count, P(FAMILY_PRESENT))) <= 0.30",
            "result": "FAIL",
            "unchanged": True,
        },
        "invariance": invariance,
        "mean_deltas_vs_stored": deltas,
        "moves_best": False,
        "n_applicability": len(records),
        "promotion": "not_eligible",
        "replay_blunt_correlation": report["corr_word_count_p_family_present"],
        "replay_blunt_pass": report["pass"],
        "reserve_scored": False,
        "schema": "hyperlex.classification.v2.surface_invariance_diagnostic.v1",
        "surface": "validation",
        "temperature": TEMPERATURE,
        "training": False,
    }
    DESTINATION.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(DESTINATION, 0o644)
    print(json.dumps({
        "applicability_surface_shortcut": status,
        "family_surface_gap": invariance["family_surface_gap"],
        "guard_results": invariance["guard_results"],
        "none_surface_gap": invariance["none_surface_gap"],
        "residualized_length_correlation": invariance["residualized_length_correlation"]["correlation"],
        "wrote": str(DESTINATION),
    }, sort_keys=True))
    return 0


def main() -> int:
    if os.environ.get("HLX_INVARIANCE_INNER") == "1":
        return inner()
    if not EXPORT.is_file():
        fail(f"missing export {EXPORT}")
    before = sealed_digests()
    if before[str(BEST_WEIGHTS)] != BEST_SHA or before[str(OUT / "model.safetensors")] != PRIMARY_SHA:
        fail("weight pin mismatch before replay")
    command = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "--name",
        "hlx-classification-v2-surface-invariance",
        "-v",
        "/home/morpheus/Hyperlex:/home/morpheus/Hyperlex",
        "-v",
        "/home/morpheus/hlx-private:/home/morpheus/hlx-private",
        "-v",
        "/home/morpheus/.hyperlex:/home/morpheus/.hyperlex",
        "-w",
        "/home/morpheus/Hyperlex",
        "-e",
        "HOME=/home/morpheus",
        "-e",
        "HF_HUB_OFFLINE=1",
        "-e",
        "TRANSFORMERS_OFFLINE=1",
        "-e",
        "PYTHONPATH=/home/morpheus/Hyperlex/scripts/shadow",
        "-e",
        "PYTHONUNBUFFERED=1",
        "-e",
        "HLX_INVARIANCE_INNER=1",
        IMAGE,
        "python",
        "-u",
        "scripts/spark/diagnose_classification_v2_surface_invariance.py",
    ]
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    log_path = PRIVATE / "invariance.log"
    print(json.dumps({"diagnosing": str(OUT)}, sort_keys=True), flush=True)
    with log_path.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, check=False)
    after = sealed_digests()
    if after != before:
        fail("sealed artifact changed during the diagnostic")
    if completed.returncode != 0:
        fail(f"invariance replay exit {completed.returncode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
