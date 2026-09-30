"""Score EVAL_RESERVE once under frozen HYPERLEX_FAMILY_RETRIEVAL_DECISION_V1.

Uses the sealed training-only embedding index and frozen thresholds.
Does not train, recalibrate, rebuild the index, change ontology, use Jev, or
move BEST.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
PRIVATE = Path(
    "/home/morpheus/hlx-private/classification-v2-family-retrieval-reserve-20260930"
)
RETRIEVAL_DIR = Path(
    "/home/morpheus/hlx-private/classification-v2-family-retrieval-20260930"
)
RETRIEVAL = RETRIEVAL_DIR / "FAMILY_RETRIEVAL.json"
RETRIEVAL_SHA = "4030e6a36ca1fea34dc728ae913bc96697e7484be532260f7b580ba5eadf2c8f"
INDEX = RETRIEVAL_DIR / "FAMILY_RETRIEVAL_INDEX.json"
INDEX_SHA = "b1cd64d9e50e35f2c195f2e115ffdbd77f0a28089f8bd90792f36f1abc4b0177"
EXPORT = Path(
    "/home/morpheus/hlx-private/classification-v2-train-forward-20260930/civilian.v0.7.hub.jsonl"
)
EXPORT_SHA = "0d8f4532f84ed9fade3fd4e69af0d1e0717fb1098d40754e95c0090d8282bfe1"
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926/ledger.json")
PRIOR_ROWS = Path(
    "/home/morpheus/hlx-private/classification-v2-train-ready-20260929/reserve-eval-rows.jsonl"
)
PRIOR_ROWS_SHA = "8c5276442ce37cf99fff597653a28917b3b4dc69ac87ad01f815fa458416ed36"
OUT = Path(
    "/home/morpheus/.hyperlex/models/"
    "hyperlex-encoder-modernbert-base-seed-classification-v2-forward-hub"
)
WEIGHTS = OUT / "model.safetensors"
WEIGHTS_SHA = "adf5db93dfe258290be531f0a25035dfaae03873bd800fd929bee43b38c9f89c"
CALIBRATION = OUT / "classification-v2-calibration.json"
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
BEST_LINK = Path("/home/morpheus/.hyperlex/models/BEST")
INIT_FROM = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004"
)
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
DEST = PRIVATE / "RESERVE_EVAL.json"
ROWS_PATH = PRIVATE / "reserve-eval-rows.jsonl"

FROZEN_SCORE = 0.85
FROZEN_MARGIN = 0.03

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sudo_sha256(path: Path) -> str:
    try:
        return sha256_file(path)
    except PermissionError:
        pass
    completed = subprocess.run(
        ["sudo", "-n", "sha256sum", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.split()[0]


def sudo_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except PermissionError:
        completed = subprocess.run(
            ["sudo", "-n", "cat", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def write_private(path: Path, payload: dict | str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def pin_inputs() -> dict:
    retrieval = json.loads(sudo_read_text(RETRIEVAL))
    if retrieval.get("artifact_sha256") != RETRIEVAL_SHA:
        fail("retrieval artifact digest mismatch")
    thresholds = retrieval.get("thresholds") or {}
    if float(thresholds.get("minimum_family_score")) != FROZEN_SCORE:
        fail("minimum_family_score drifted")
    if float(thresholds.get("minimum_top1_top2_margin")) != FROZEN_MARGIN:
        fail("minimum_top1_top2_margin drifted")
    index = json.loads(sudo_read_text(INDEX))
    if index.get("index_sha256") != INDEX_SHA:
        fail("embedding index digest mismatch")
    if index.get("uses_family_centroid") is not False:
        fail("index uses centroid")
    if sha256_file(EXPORT) != EXPORT_SHA:
        fail("hub export digest mismatch")
    if sudo_sha256(WEIGHTS) != WEIGHTS_SHA:
        fail("forward-hub weights digest mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if not BEST_LINK.is_symlink() or BEST_LINK.resolve() != INIT_FROM.resolve():
        fail("BEST symlink is not the production checkpoint")
    if sha256_file(PRIOR_ROWS) != PRIOR_ROWS_SHA:
        fail("sealed reserve-eval rows digest mismatch")
    calibration = json.loads(sudo_read_text(CALIBRATION))
    if calibration.get("surface") != "validation" or calibration.get("reserve_used") is not False:
        fail("applicability calibration is not the validation freeze")
    return {
        "applicability_calibration": calibration,
        "index": index,
        "retrieval": retrieval,
    }


def load_reserve_rows(index_identities: set[str]) -> tuple[list[dict], list[str], str]:
    from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY
    from hyperlexical.holdout_guard import normalized_text_sha256

    invalid: list[str] = []
    rows = [
        json.loads(line)
        for line in PRIOR_ROWS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != 115:
        invalid.append(f"reserve_row_count={len(rows)}!=115")
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    reserve_ids = set()
    for record in ledger["identities"]:
        if record.get("state") != "EVAL_RESERVE":
            continue
        labels = [label for label in (record.get("labels") or []) if label.get("task") == "classify"]
        if labels:
            reserve_ids.add(record["normalized_text_sha256"])
    if len(reserve_ids) != 115:
        invalid.append(f"ledger_classify_reserve={len(reserve_ids)}!=115")
    export_ids = set()
    with EXPORT.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            export_ids.add(normalized_text_sha256(str(json.loads(line).get("text") or "")))
    seen = set()
    cleaned = []
    for row in rows:
        digest = str(row.get("normalized_text_sha256") or "")
        text = str(row.get("text") or "")
        lineage = row.get("lineage")
        klass = row.get("class")
        if digest != normalized_text_sha256(text):
            invalid.append(f"identity_text_mismatch:{digest}")
        if digest not in reserve_ids:
            invalid.append(f"not_in_ledger:{digest}")
        if digest in index_identities:
            invalid.append(f"overlaps_index:{digest}")
        if digest in export_ids:
            invalid.append(f"overlaps_export:{digest}")
        if lineage != "none" and lineage not in ACTIVE_FAMILY_VOCABULARY:
            invalid.append(f"lineage_outside_forward_vocab:{lineage}")
        if klass not in {"OBSERVED", "INFERRED"}:
            invalid.append(f"class_invalid:{klass}")
        if digest in seen:
            invalid.append(f"duplicate:{digest}")
        seen.add(digest)
        cleaned.append(
            {
                "class": klass,
                "lineage": lineage,
                "normalized_text_sha256": digest,
                "source": row.get("source"),
                "text": text,
            }
        )
    missing = sorted(reserve_ids - seen)
    if missing:
        invalid.append(f"missing_reserve_texts:{len(missing)}")
    identity_hash = hashlib.sha256(
        "\n".join(sorted(row["normalized_text_sha256"] for row in cleaned)).encode("utf-8")
    ).hexdigest()
    return cleaned, invalid, identity_hash


def inner() -> int:
    import torch
    from safetensors.torch import load_file
    from torch import nn
    from transformers import AutoModel, AutoTokenizer

    from hyperlexical.classification_v2 import (
        ACTIVE_FAMILY_VOCABULARY,
        APPLICABILITY,
        APPLICABILITY_NONE,
        APPLICABILITY_PRESENT,
        FORWARD_ONTOLOGY,
        V1_NONE_CLASS,
        _softmax,
        canonical_json,
        prf_table,
        sha256_text,
    )
    from hyperlexical.classification_v2_family_retrieval import (
        FROZEN_MINIMUM_FAMILY_SCORE,
        FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
        RETRIEVAL_ARTIFACT_SHA256,
        RETRIEVAL_INDEX_SHA256,
        RULE,
        assemble_reserve_eval_artifact,
        decide_reserve_disposition,
        evaluate_retrieval_decisions,
        family_scores,
        next_action_for_disposition,
        selective_contract_generalizes,
        validation_vs_reserve,
        wrong_family_emissions,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.layout import HIDDEN, MAX_LEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors

    if not FORWARD_ONTOLOGY:
        fail("HLX_V2_FORWARD_ONTOLOGY must be enabled")
    if (
        FROZEN_MINIMUM_FAMILY_SCORE != FROZEN_SCORE
        or FROZEN_MINIMUM_TOP1_TOP2_MARGIN != FROZEN_MARGIN
    ):
        fail("frozen threshold constants drifted")
    pinned = pin_inputs()
    index = pinned["index"]
    retrieval = pinned["retrieval"]
    index_identities = {str(row["source_identity"]) for row in index["records"]}
    rows, invalid, identity_hash = load_reserve_rows(index_identities)
    # Preserve the sealed reserve-row bytes exactly; do not re-serialize.
    ROWS_PATH.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    ROWS_PATH.write_bytes(PRIOR_ROWS.read_bytes())
    os.chmod(ROWS_PATH, 0o600)
    if sha256_file(ROWS_PATH) != PRIOR_ROWS_SHA:
        invalid.append("copied_reserve_rows_digest_mismatch")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        invalid.append("cuda_unavailable")
        disposition = decide_reserve_disposition(
            invalid_reasons=invalid, family_emission_precision=None
        )
        artifact = assemble_reserve_eval_artifact(
            {
                "applicability": {},
                "disposition": disposition,
                "evaluation": {},
                "generalization": selective_contract_generalizes(
                    reserve_precision=None,
                    validation_precision=retrieval["evaluation"].get(
                        "family_emission_precision"
                    ),
                ),
                "next_action": next_action_for_disposition(disposition),
                "pinned": {
                    "index_sha256": INDEX_SHA,
                    "minimum_family_score": FROZEN_SCORE,
                    "minimum_top1_top2_margin": FROZEN_MARGIN,
                    "retrieval_artifact_sha256": RETRIEVAL_SHA,
                    "weights_sha256": WEIGHTS_SHA,
                },
                "reserve_identity": {
                    "identity_list_sha256": identity_hash,
                    "n": len(rows),
                    "rows_sha256": PRIOR_ROWS_SHA,
                },
                "validation_vs_reserve": {},
                "wrong_family_emissions": [],
            }
        )
        write_private(DEST, artifact)
        print(json.dumps({"disposition": disposition, "destination": str(DEST)}, indent=2))
        return 2

    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tokenizer.padding_side = "right"
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    freeze_encoder(encoder)
    warm = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    tensors = split_weight_tensors(load_file(str(WEIGHTS), device="cpu"))
    if apply_encoder_trainable(encoder, warm.get("encoder") or {})["loaded"] != 48:
        fail("production overlay missed 48 tensors")
    if apply_encoder_trainable(encoder, tensors.get("encoder") or {})["loaded"] != 12:
        fail("forward-hub overlay missed 12 tensors")
    applicability = nn.Linear(HIDDEN, 2)
    applicability.load_state_dict(tensors["applicability"])
    encoder.to(device).eval()
    applicability.to(device).eval()
    cal = pinned["applicability_calibration"]
    app_temperature = float(cal["applicability_temperature"])
    app_threshold = float(cal["applicability_threshold"])

    score_rows = []
    app_gold = []
    app_pred = []
    with torch.no_grad():
        for row in rows:
            text = str(row["text"])
            encoded = tokenizer(
                [text],
                padding=True,
                truncation=True,
                max_length=MAX_LEN,
                return_tensors="pt",
            )
            encoded = {key: value.to(device) for key, value in encoded.items()}
            pooled = encoder(**encoded).last_hidden_state[:, 0]
            hidden = torch.nn.functional.normalize(pooled, dim=-1)[0].detach().cpu().tolist()
            app_logits = [float(value) for value in applicability(pooled)[0].detach().cpu()]
            app_distribution = _softmax(app_logits, app_temperature)
            p_present = float(app_distribution[1])
            applicability_label = (
                APPLICABILITY_PRESENT if p_present >= app_threshold else APPLICABILITY_NONE
            )
            ranked = family_scores(hidden, index["records"])
            gold = row["lineage"]
            score_rows.append(
                {
                    "applicability": applicability_label,
                    "gold_lineage": gold,
                    "source_identity": row["normalized_text_sha256"],
                    "top1_family": ranked["top1"]["family"],
                    "top1_score": ranked["top1"]["score"],
                    "top2_family": ranked["top2"]["family"],
                    "top2_score": ranked["top2"]["score"],
                }
            )
            gold_app = APPLICABILITY_NONE if gold == V1_NONE_CLASS else APPLICABILITY_PRESENT
            app_gold.append(gold_app)
            app_pred.append(applicability_label)

    evaluation = evaluate_retrieval_decisions(
        score_rows,
        minimum_family_score=FROZEN_SCORE,
        minimum_top1_top2_margin=FROZEN_MARGIN,
    )
    # Attach source identities onto decisions for wrong-emission audit.
    for decided, scored in zip(evaluation["decisions"], score_rows, strict=True):
        decided["source_identity"] = scored["source_identity"]
    wrong = wrong_family_emissions(evaluation["decisions"])
    app_table = prf_table(app_gold, app_pred, APPLICABILITY)
    applicability_metrics = {
        "macro_f1": app_table["macro_f1"],
        "per_label": app_table["per_label"],
        "threshold": app_threshold,
        "temperature": app_temperature,
    }
    validation_eval = retrieval.get("evaluation") or {}
    comparison = validation_vs_reserve(validation_eval, evaluation)
    generalization = selective_contract_generalizes(
        reserve_precision=evaluation.get("family_emission_precision"),
        validation_precision=validation_eval.get("family_emission_precision"),
    )
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        invalid.append("best_changed_during_scoring")
    if sudo_sha256(WEIGHTS) != WEIGHTS_SHA:
        invalid.append("weights_changed_during_scoring")
    if json.loads(sudo_read_text(INDEX)).get("index_sha256") != INDEX_SHA:
        invalid.append("index_changed_during_scoring")
    disposition = decide_reserve_disposition(
        invalid_reasons=invalid,
        family_emission_precision=evaluation.get("family_emission_precision"),
    )
    next_action = next_action_for_disposition(disposition)
    artifact = assemble_reserve_eval_artifact(
        {
            "applicability": applicability_metrics,
            "disposition": disposition,
            "evaluation": evaluation,
            "generalization": generalization,
            "next_action": next_action,
            "pinned": {
                "best_sha256": BEST_SHA,
                "export_sha256": EXPORT_SHA,
                "index_sha256": RETRIEVAL_INDEX_SHA256,
                "minimum_family_score": FROZEN_SCORE,
                "minimum_top1_top2_margin": FROZEN_MARGIN,
                "retrieval_artifact_sha256": RETRIEVAL_ARTIFACT_SHA256,
                "rule": RULE,
                "weights_sha256": WEIGHTS_SHA,
            },
            "reserve_identity": {
                "identity_list_sha256": identity_hash,
                "n": len(rows),
                "rows_sha256": PRIOR_ROWS_SHA,
            },
            "validation_vs_reserve": comparison,
            "wrong_family_emissions": wrong,
        }
    )
    write_private(DEST, artifact)
    print(
        json.dumps(
            {
                "artifact_sha256": artifact["artifact_sha256"],
                "coverage": evaluation.get("coverage"),
                "destination": str(DEST),
                "disposition": disposition["disposition"],
                "family_emission_precision": evaluation.get("family_emission_precision"),
                "generalizes": generalization.get("generalizes"),
                "n": len(rows),
                "next_action": next_action,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    if "--inner" in sys.argv:
        return inner()
    pinned = pin_inputs()
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    write_private(
        PRIVATE / "LAUNCH.json",
        {
            "authorization": "OPERATOR_AUTHORIZE_RESERVE_EVAL",
            "best_sha256": BEST_SHA,
            "index_sha256": INDEX_SHA,
            "minimum_family_score": FROZEN_SCORE,
            "minimum_top1_top2_margin": FROZEN_MARGIN,
            "moves_best": False,
            "recalibrate": False,
            "rebuild_index": False,
            "reserve_rows_sha256": PRIOR_ROWS_SHA,
            "retrieval_artifact_sha256": RETRIEVAL_SHA,
            "train": False,
            "validation_family_emission_precision": pinned["retrieval"]["evaluation"].get(
                "family_emission_precision"
            ),
            "weights_sha256": WEIGHTS_SHA,
        },
    )
    command = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "--name",
        "hlx-classification-v2-family-retrieval-reserve",
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
        "HLX_V2_FORWARD_ONTOLOGY=1",
        "-e",
        "PYTHONDONTWRITEBYTECODE=1",
        "-e",
        "PYTHONPATH=/home/morpheus/Hyperlex/scripts/shadow",
        "-e",
        "PYTHONUNBUFFERED=1",
        "-e",
        "TRANSFORMERS_OFFLINE=1",
        IMAGE,
        "python3",
        "-u",
        str(REPO / "scripts/spark/run_classification_v2_family_retrieval_reserve_eval.py"),
        "--inner",
    ]
    log_path = PRIVATE / "reserve_eval.log"
    print(json.dumps({"launching": str(DEST), "log": str(log_path)}), flush=True)
    with log_path.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, check=False)
    write_private(PRIVATE / "EXIT.json", {"code": completed.returncode})
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed during reserve eval")
    if completed.returncode != 0:
        fail(f"reserve eval exit {completed.returncode}; see {log_path}")
    artifact = json.loads(sudo_read_text(DEST))
    print(
        json.dumps(
            {
                "artifact_sha256": artifact["artifact_sha256"],
                "coverage": artifact["evaluation"].get("coverage"),
                "destination": str(DEST),
                "disposition": artifact["disposition"]["disposition"],
                "family_emission_precision": artifact["evaluation"].get(
                    "family_emission_precision"
                ),
                "generalizes": artifact.get("selective_contract_generalizes"),
                "next_action": artifact["next_action"],
                "n": artifact["reserve_identity"]["n"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
