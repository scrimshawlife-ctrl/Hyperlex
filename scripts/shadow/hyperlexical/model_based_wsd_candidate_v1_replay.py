"""Evaluate one pinned GlossBERT checkpoint on Extended Lesk ties.

The specification is hashed before any Hyperlex constituent is scored. Operator
labels are read only after the readiness projection is hashed. Residual scores
are not loaded and are not recomputed.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from hyperlexical.constituent_sense_resolution_v1_replay import (
    ANALYSIS_PATH as RESOLVER_ANALYSIS_PATH,
)
from hyperlexical.constituent_sense_resolution_v1_replay import (
    DECISION_PATH as RESOLVER_DECISION_PATH,
)
from hyperlexical.constituent_sense_resolution_v1_replay import (
    EXPECTED as RESOLVER_EXPECTED,
)
from hyperlexical.constituent_sense_resolution_v1_replay import (
    EVENTS,
    EVIDENCE_MANIFEST,
    HYPERLEX,
    LEDGER_FILE,
    LIMITATION_PATH,
    OPERATOR_COUNTS,
    OPERATORS,
    PROCEDURE_PATH as RESOLVER_PROCEDURE_PATH,
    REPLAY_PATH as RESOLVER_REPLAY_PATH,
    REVIEW_PATH,
    SOURCE,
    SPEC_PATH as RESOLVER_SPEC_PATH,
    TRACKER,
    WORDNET,
    build_catalog,
    load_sealed_rows,
    refuse,
    sha256,
    write_json,
    write_jsonl,
)
from hyperlexical.km_candidate_evaluation import lookup_key
from hyperlexical.model_based_wsd_candidate_v1 import (
    BASELINE_HIGH_READY,
    BASELINE_SECONDARY_READY,
    BASELINE_TOTAL_READY,
    CANONICAL_SOURCE,
    IDENTICAL,
    LICENSE_NAME,
    MAX_TOKENS,
    MODEL_FAMILY,
    MODEL_NAME,
    MODEL_REVISION,
    POSITIVE_CLASS_INDEX,
    REJECTED,
    RULE_VERSION,
    candidate_gloss_text,
    candidate_policy,
    coverage_gate,
    format_probability,
    gloss_lemma,
    overlay_status,
    project_row_status,
    quoted_context,
    resolve_model_scores,
    summarize_confidence,
)
from hyperlexical.semantic_compositionality_residual import neighbor_keys
from hyperlexical.unbind_sense_screen_v1 import load_exceptions

MODEL_DIR = (
    Path("/home/morpheus/hlx-private/eval-reserve-20260926/acquisition/sources/glossbert")
    / MODEL_REVISION
)
CODE_LICENSE = (
    Path("/home/morpheus/hlx-private/eval-reserve-20260926/acquisition/sources/glossbert")
    / "ORIGINAL_CODE_MIT_LICENSE.txt"
)
SPEC_PATH = SOURCE / "MODEL_BASED_WSD_CANDIDATE_SPEC.json"
PROVENANCE_PATH = SOURCE / "MODEL_BASED_WSD_PROVENANCE.json"
LICENSE_PATH = SOURCE / "MODEL_BASED_WSD_LICENSE_RECEIPT.json"
RAW_PATH = SOURCE / "MODEL_BASED_WSD_RAW_OUTPUT.jsonl"
RESOLUTION_PATH = SOURCE / "MODEL_BASED_WSD_RESOLUTION.jsonl"
PROJECTION_PATH = SOURCE / "MODEL_BASED_WSD_READINESS_PROJECTION.json"
ANALYSIS_PATH = SOURCE / "MODEL_BASED_WSD_DEVELOPMENT_ANALYSIS.json"
DECISION_PATH = SOURCE / "MODEL_BASED_WSD_CANDIDATE_DECISION.json"

CURRENT_TRACKER = "c72e55c8096143b8675d4aa995c5d4b19de95d256dd234d32a421ba098bc7d4f"
WEIGHTS = {
    "config.json": "70f859c899543d9c8f822e64201e1a77530f0de12aabb0daf04b9570f538b638",
    "pytorch_model.bin": "60706c7618f8ccbfa7d0a6d1d1009765a7146ea5f4232924ed9f1c46d521c898",
    "README.md": "27577f2e0742d2e91ccad99778cc15fe521386de53d7bfe8acedfa0a78f8c186",
    "special_tokens_map.json": "303df45a03609e4ead04bc3dc1536d0ab19b5358db685b6f3da123d05ec200e3",
    "tokenizer_config.json": "09e49d0e788d25991da77d37b10eaa6a86a4e94e2127de8bedc94eb45baf2d84",
    "vocab.txt": "07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3",
}
CODE_LICENSE_SHA = "333e83b83ae30a1c9af100ea742de8ab34ac9d6d8c8aae52e0bbec47cf9df80f"
RUNTIME = {
    "numpy": "2.5.3",
    "python": "3.12.3",
    "tokenizers": "0.23.2",
    "torch": "2.14.0+cpu",
    "transformers": "5.17.0",
}
FINANCIAL_CONTEXT = 'She deposited the check at the "bank" yesterday.'
RIVER_CONTEXT = 'They picnicked on the grassy "bank" of the river.'
FINANCIAL_SYNSET = "noun:08420278"
RIVER_SYNSET = "noun:09213565"
POOL_ATTEMPTS = 249
SS_POS = {"1": "noun", "2": "verb", "3": "adj", "4": "adv", "5": "adj"}

_THIRD_PARTY = (
    "The Hugging Face card is a third-party upload. It is not the authors' "
    "Google Drive checkpoint. The card declares MIT. The original GlossBERT "
    "code repository is MIT. No API key is required."
)
_CODE_REPOSITORY = "https://github.com/HSLCY/GlossBERT"

EXPECTED = dict(RESOLVER_EXPECTED)
EXPECTED[TRACKER] = CURRENT_TRACKER
EXPECTED[REVIEW_PATH] = "1c1b69856dd88567167fd5c958cd8db6d39ab9ec74a4e0ed3e667a521c82e6fa"
EXPECTED[LIMITATION_PATH] = "fc8839c15a7638b2bfca1cf0548bfb4d5f433434bae0fea2944a528dd15d6142"
EXPECTED[RESOLVER_SPEC_PATH] = "176e6219ddc3127814a25d39ad26e3571817f7ea8323d685e081d2e0fd867acb"
EXPECTED[RESOLVER_PROCEDURE_PATH] = "9f76b64aa6aac09bd56ca9cc8a847cda12b31a58eea8c4b51426733917d54248"
EXPECTED[RESOLVER_REPLAY_PATH] = "a0c707ab55e02f627a698c33ddc0ca398e34aa0bafc19b13e72422bc26d97d0a"
EXPECTED[RESOLVER_ANALYSIS_PATH] = "6d47610014f74094394355a50419fe24441103bec09458b6f25ea392fb57151c"
EXPECTED[RESOLVER_DECISION_PATH] = "ff8b90ebe5d48151dc68ddbf676e1f27d4cee5e3be2730f999c9b089f1392caa"
EXPECTED[HYPERLEX / "scripts/shadow/hyperlexical/constituent_sense_resolution_v1.py"] = (
    "927fb5c6f627d5488ecbc66779595812e8c2154ad47d6a07db1e377639f36fc6"
)
EXPECTED[HYPERLEX / "scripts/shadow/hyperlexical/constituent_sense_resolution_v1_replay.py"] = (
    "d8cd1c1719d9764cb0a77ad51a2d305268181b42294cd1adddd3ff9d4ea57e0b"
)
EXPECTED[HYPERLEX / "tests/shadow/test_constituent_sense_resolution_v1.py"] = (
    "104ac0edc643b76df4ca1fe905e30ed96c7417dddfc14010b23d3b3c613adeb9"
)


def check_sealed(skip: set[Path] | None = None) -> None:
    skipped = skip or set()
    for path, expected in EXPECTED.items():
        if path in skipped:
            continue
        if not path.is_file() or sha256(path) != expected:
            refuse(f"sealed file changed: {path}")


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def load_sense_index(path: Path) -> dict[str, list[dict]]:
    index = defaultdict(list)
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) < 2 or "%" not in parts[0]:
            continue
        sense_key, offset = parts[0], parts[1]
        lemma, _, rest = sense_key.partition("%")
        pos = SS_POS.get(rest.split(":", 1)[0])
        if pos is None:
            continue
        index[f"{pos}:{offset.zfill(8)}"].append({"lemma": lemma, "sense_key": sense_key})
    return dict(index)


def sense_keys_for(synset_id: str, constituent: str, exceptions: dict, sense_index: dict) -> list[str]:
    allowed = neighbor_keys(constituent, exceptions)
    found = [
        item["sense_key"]
        for item in sense_index.get(synset_id, [])
        if lookup_key(item["lemma"]) in allowed
    ]
    return sorted(set(found))


def assert_weights() -> dict:
    if not MODEL_DIR.is_dir():
        refuse("glossbert directory is missing")
    found = {}
    for name, expected in WEIGHTS.items():
        path = MODEL_DIR / name
        digest = sha256(path)
        if digest != expected:
            refuse(f"weight hash mismatch: {name}")
        found[name] = digest
    if not CODE_LICENSE.is_file() or sha256(CODE_LICENSE) != CODE_LICENSE_SHA:
        refuse("original code license file mismatch")
    readme = (MODEL_DIR / "README.md").read_text(encoding="utf-8")
    if "license: mit" not in readme.lower():
        refuse("model card does not declare mit")
    return found


def license_payload(weights: dict) -> dict:
    return {
        "api_required": False,
        "artifact_license_file_present": False,
        "canonical_source": CANONICAL_SOURCE,
        "card_license": "mit",
        "code_license_sha256": CODE_LICENSE_SHA,
        "datasets": ["SemCor3.0"],
        "evaluation_permitted": True,
        "json_schema_document": None,
        "license_name": LICENSE_NAME,
        "model_family": MODEL_FAMILY,
        "model_name": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "original_code_license": "MIT",
        "original_code_repository": _CODE_REPOSITORY,
        "pytorch_model_bin_sha256": weights["pytorch_model.bin"],
        "schema": "hyperlex.model_based_wsd_candidate_v1_license_receipt.v1",
        "source_license_unresolved": False,
        "third_party_note": _THIRD_PARTY,
        "third_party_upload": True,
        "vocab_txt_sha256": weights["vocab.txt"],
    }


def spec_payload(weights: dict, license_sha: str) -> dict:
    return {
        "artifacts": {
            "config_json_sha256": weights["config.json"],
            "pytorch_model_bin_sha256": weights["pytorch_model.bin"],
            "readme_md_sha256": weights["README.md"],
            "special_tokens_map_json_sha256": weights["special_tokens_map.json"],
            "tokenizer_config_json_sha256": weights["tokenizer_config.json"],
            "vocab_txt_sha256": weights["vocab.txt"],
        },
        "expected_tier3_attempts": POOL_ATTEMPTS,
        "json_schema_document": None,
        "license_receipt_sha256": license_sha,
        "polarity_control": {
            "financial_context": FINANCIAL_CONTEXT,
            "financial_synset": FINANCIAL_SYNSET,
            "hyperlex_rows_used": False,
            "river_context": RIVER_CONTEXT,
            "river_synset": RIVER_SYNSET,
        },
        "policy": candidate_policy(),
        "prior_resolver_replay_sha256": EXPECTED[RESOLVER_REPLAY_PATH],
        "residual_scores_included": False,
        "runtime": dict(RUNTIME),
        "schema": "hyperlex.model_based_wsd_candidate_v1_spec.v1",
        "selected_source": "none",
    }


def prepare_pool(frozen: list[dict], by_id: dict, exceptions: dict, sense_index: dict) -> list[dict]:
    attempts = [row for row in frozen if row["constituent_index"] is not None]
    counts = Counter(row["resolution_status"] for row in attempts)
    if counts["EXACT"] != 64 or counts["RESOLVED"] != 121 or counts["AMBIGUOUS"] != 249 or counts["UNRESOLVED"] != 70:
        refuse("frozen resolver counts drifted")
    pool = []
    for row in attempts:
        if row["resolution_status"] != "AMBIGUOUS":
            continue
        if row["resolution_method"] != "EXTENDED_LESK_V1":
            refuse("ambiguous constituent is not an extended lesk tie")
        pairs = []
        for synset_id in row["candidate_synsets"]:
            record = by_id.get(synset_id)
            if record is None:
                refuse(f"missing candidate synset {synset_id}")
            lemma = gloss_lemma(record["lemmas"], row["constituent_surface"], exceptions)
            if lemma is None:
                refuse(f"candidate lemma missing for {synset_id}")
            pairs.append(
                {
                    "gloss_text": candidate_gloss_text(lemma, record["gloss_first"]),
                    "sense_keys": sense_keys_for(synset_id, row["constituent_surface"], exceptions, sense_index),
                    "synset": synset_id,
                }
            )
        pool.append(
            {
                "candidate_pwn30_synsets": list(row["candidate_synsets"]),
                "candidate_sense_keys": {item["synset"]: list(item["sense_keys"]) for item in pairs},
                "constituent_index": row["constituent_index"],
                "constituent_pos": row["constituent_pos"],
                "constituent_surface": row["constituent_surface"],
                "context": quoted_context(row["parent_surface"], row["constituent_index"], row["constituent_surface"]),
                "pairs": pairs,
                "parent_row_id": row["parent_row_id"],
                "parent_surface": row["parent_surface"],
                "parent_synset": row["parent_synset"],
                "prior_lesk_margin": row["margin"],
                "prior_lesk_second_score": row["second_score"],
                "prior_lesk_top_score": row["top_score"],
                "prior_resolution_status": "AMBIGUOUS",
            }
        )
    if len(pool) != POOL_ATTEMPTS:
        refuse(f"tier 3 pool is {len(pool)}")
    return pool


def import_runtime():
    import numpy
    import torch
    import tokenizers
    import transformers
    from transformers import AutoTokenizer, BertForSequenceClassification

    versions = {
        "numpy": numpy.__version__,
        "python": ".".join(str(part) for part in sys.version_info[:3]),
        "tokenizers": tokenizers.__version__,
        "torch": torch.__version__,
        "transformers": transformers.__version__,
    }
    if versions != RUNTIME:
        refuse(f"runtime drift: {versions}")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.backends.mkldnn.enabled = False
    torch.use_deterministic_algorithms(False)
    torch.manual_seed(0)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, local_files_only=True)
    model = BertForSequenceClassification.from_pretrained(MODEL_DIR, local_files_only=True)
    model.eval()
    model.to("cpu")
    if model.num_labels != 2:
        refuse("classifier head is not binary")
    return torch, tokenizer, model


def score_pair(torch, tokenizer, model, context: str, gloss_text: str) -> dict:
    encoded = tokenizer(context, gloss_text, truncation=False, padding=False, return_tensors="pt")
    length = int(encoded["input_ids"].shape[-1])
    if length > MAX_TOKENS:
        return {"overflow": True, "positive_probability": None, "token_count": length}
    with torch.inference_mode():
        logits = model(**encoded).logits[0]
        probability = torch.softmax(logits, dim=-1)[POSITIVE_CLASS_INDEX]
    return {
        "overflow": False,
        "positive_probability": format_probability(float(probability)),
        "token_count": length,
    }


def score_context(torch, tokenizer, model, context: str, pairs: list[dict]) -> dict:
    scored = []
    overflow = False
    error = None
    try:
        for pair in pairs:
            result = score_pair(torch, tokenizer, model, context, pair["gloss_text"])
            overflow = overflow or result["overflow"]
            scored.append(
                {
                    "gloss_text": pair["gloss_text"],
                    "overflow": result["overflow"],
                    "positive_probability": result["positive_probability"],
                    "sense_keys": list(pair["sense_keys"]),
                    "synset": pair["synset"],
                    "token_count": result["token_count"],
                }
            )
    except Exception as exc:
        error = type(exc).__name__
        scored = []
        overflow = False
    return {"error": error, "overflow": overflow, "scored_pairs": scored}


def polarity_control(torch, tokenizer, model, by_id: dict, sense_index: dict) -> dict:
    synsets = sorted(
        {
            synset_id
            for synset_id, items in sense_index.items()
            if any(item["sense_key"].startswith("bank%1:") and item["lemma"] == "bank" for item in items)
        }
    )
    pairs = []
    for synset_id in synsets:
        record = by_id.get(synset_id)
        if record is None:
            refuse(f"missing polarity synset {synset_id}")
        pairs.append(
            {
                "gloss_text": candidate_gloss_text("bank", record["gloss_first"]),
                "sense_keys": [item["sense_key"] for item in sense_index[synset_id] if item["lemma"] == "bank"],
                "synset": synset_id,
            }
        )
    report = {"hyperlex_rows_used": False}
    for name, context, expected in (
        ("financial", FINANCIAL_CONTEXT, FINANCIAL_SYNSET),
        ("river", RIVER_CONTEXT, RIVER_SYNSET),
    ):
        scored = score_context(torch, tokenizer, model, context, pairs)
        probabilities = {
            row["synset"]: row["positive_probability"]
            for row in scored["scored_pairs"]
            if row["positive_probability"] is not None
        }
        decision = resolve_model_scores(
            [pair["synset"] for pair in pairs],
            {pair["synset"]: sorted(pair["sense_keys"]) for pair in pairs},
            None if scored["error"] or scored["overflow"] else probabilities,
            overflow=scored["overflow"],
            error=scored["error"],
        )
        report[name] = {
            "expected_synset": expected,
            "selected_synset": decision["selected_synset"],
            "status": decision["model_resolution_status"],
            "top_probability": decision["model_confidence"],
        }
        if decision["model_resolution_status"] != "RESOLVED" or decision["selected_synset"] != expected:
            report["passed"] = False
            return report
    report["passed"] = True
    report["positive_class_index"] = POSITIVE_CLASS_INDEX
    return report


def infer_pass(torch, tokenizer, model, pool: list[dict], spec_sha: str) -> list[dict]:
    torch.manual_seed(0)
    rows = []
    for index, item in enumerate(pool):
        scored = score_context(torch, tokenizer, model, item["context"], item["pairs"])
        rows.append(
            {
                "candidate_pwn30_synsets": list(item["candidate_pwn30_synsets"]),
                "constituent_index": item["constituent_index"],
                "constituent_pos": item["constituent_pos"],
                "constituent_surface": item["constituent_surface"],
                "context": item["context"],
                "error": scored["error"],
                "model_name": MODEL_NAME,
                "model_revision": MODEL_REVISION,
                "overflow": scored["overflow"],
                "pairs": scored["scored_pairs"],
                "parent_row_id": item["parent_row_id"],
                "parent_surface": item["parent_surface"],
                "parent_synset": item["parent_synset"],
                "record_kind": "hyperlex_tier3_constituent",
                "spec_sha256": spec_sha,
            }
        )
        if index % 25 == 0:
            print(f"scored {index}", file=sys.stderr, flush=True)
    return rows


def resolution_rows(pool: list[dict], raw_rows: list[dict]) -> list[dict]:
    resolved = []
    for item, raw in zip(pool, raw_rows, strict=True):
        probabilities = None
        if not raw["error"] and not raw["overflow"]:
            probabilities = {pair["synset"]: pair["positive_probability"] for pair in raw["pairs"]}
        decision = resolve_model_scores(
            item["candidate_pwn30_synsets"],
            item["candidate_sense_keys"],
            probabilities,
            overflow=raw["overflow"],
            error=raw["error"],
        )
        if decision["selected_synset"] is not None and decision["selected_synset"] not in item["candidate_pwn30_synsets"]:
            refuse("selected synset left the candidate set")
        resolved.append(
            {
                "candidate_pwn30_synsets": list(item["candidate_pwn30_synsets"]),
                "candidate_sense_keys": item["candidate_sense_keys"],
                "constituent_index": item["constituent_index"],
                "constituent_pos": item["constituent_pos"],
                "constituent_surface": item["constituent_surface"],
                "model_candidate_scores": decision["model_candidate_scores"],
                "model_confidence": decision["model_confidence"],
                "model_margin": decision["model_margin"],
                "model_name": MODEL_NAME,
                "model_resolution_status": decision["model_resolution_status"],
                "model_revision": MODEL_REVISION,
                "parent_row_id": item["parent_row_id"],
                "parent_surface": item["parent_surface"],
                "parent_synset": item["parent_synset"],
                "primary_evidence_code": decision["primary_evidence_code"],
                "prior_lesk_margin": item["prior_lesk_margin"],
                "prior_lesk_second_score": item["prior_lesk_second_score"],
                "prior_lesk_top_score": item["prior_lesk_top_score"],
                "prior_resolution_status": "AMBIGUOUS",
                "selected_sense_key": decision["selected_sense_key"],
                "selected_synset": decision["selected_synset"],
                "spec_sha256": raw["spec_sha256"],
            }
        )
    return resolved


def project_rows(frozen: list[dict], resolutions: list[dict]) -> tuple[list[dict], dict]:
    tier3 = {(row["parent_row_id"], row["constituent_index"]): row for row in resolutions}
    if len(tier3) != len(resolutions):
        refuse("duplicate tier 3 keys")
    grouped = defaultdict(list)
    for row in frozen:
        grouped[row["parent_row_id"]].append(row)
    projected = []
    combined = Counter()
    for sealed in load_sealed_rows():
        items = [row for row in grouped[sealed["row_id"]] if row["constituent_index"] is not None]
        items.sort(key=lambda row: row["constituent_index"])
        statuses = []
        for item in items:
            key = (item["parent_row_id"], item["constituent_index"])
            model_status = None
            if key in tier3:
                if item["resolution_status"] != "AMBIGUOUS" or item["resolution_method"] != "EXTENDED_LESK_V1":
                    refuse("tier 3 key is not an extended lesk tie")
                model_status = tier3[key]["model_resolution_status"]
            status = overlay_status(item["resolution_status"], item["resolution_method"], model_status)
            statuses.append(status)
            combined[status] += 1
        projected.append(
            {
                "constituent_statuses": statuses,
                "content_count": len(statuses),
                "parent_row_id": sealed["row_id"],
                "projected_status": project_row_status(statuses),
            }
        )
    if len(projected) != 225:
        refuse("projection does not cover 225 rows")
    if sum(combined.values()) != 504:
        refuse("combined constituent count is not 504")
    counts = Counter(row["projected_status"] for row in projected)
    if counts["RESIDUAL_READY"] + counts["UNKNOWN"] != 225:
        refuse("projected row count drifted")
    return projected, {
        "combined_constituent_counts": {
            "AMBIGUOUS": combined["AMBIGUOUS"],
            "ERROR": combined["ERROR"],
            "EXACT": combined["EXACT"],
            "INVALID": combined["INVALID"],
            "LESK_RESOLVED": combined["LESK_RESOLVED"],
            "MODEL_RESOLVED": combined["MODEL_RESOLVED"],
            "UNRESOLVED": combined["UNRESOLVED"],
        },
        "row_counts": {"RESIDUAL_READY": counts["RESIDUAL_READY"], "UNKNOWN": counts["UNKNOWN"]},
    }


def update_tracker(outcome: dict, hashes: dict) -> str:
    check_sealed(skip={TRACKER})
    tracker = json.loads(TRACKER.read_text(encoding="utf-8"))
    if sha256(TRACKER) != CURRENT_TRACKER:
        refuse("tracker hash drifted before update")
    tracker["previous_state"] = tracker.get("state")
    tracker["previous_tracker_sha256"] = CURRENT_TRACKER
    tracker["state"] = "CANDIDATE_SOURCE_EVALUATED"
    tracker["model_based_wsd_rule"] = RULE_VERSION
    tracker["model_based_wsd_state"] = "CANDIDATE_EVALUATED"
    tracker["model_based_wsd_candidate_status"] = outcome["candidate_status"]
    tracker["model_based_wsd_model_name"] = MODEL_NAME
    tracker["model_based_wsd_model_revision"] = MODEL_REVISION
    tracker["model_based_wsd_runtime_integration"] = False
    tracker["model_based_wsd_spec_sha256"] = hashes.get("spec_sha256")
    tracker["model_based_wsd_provenance_sha256"] = hashes.get("provenance_sha256")
    tracker["model_based_wsd_license_receipt_sha256"] = hashes.get("license_sha256")
    tracker["model_based_wsd_raw_output_sha256"] = hashes.get("raw_sha256")
    tracker["model_based_wsd_resolution_sha256"] = hashes.get("resolution_sha256")
    tracker["model_based_wsd_readiness_projection_sha256"] = hashes.get("projection_sha256")
    tracker["model_based_wsd_analysis_sha256"] = hashes.get("analysis_sha256")
    tracker["model_based_wsd_decision_sha256"] = hashes.get("decision_sha256")
    tracker["model_based_wsd_residual_ready_rows"] = outcome.get("total_ready")
    tracker["model_based_wsd_high_ready"] = outcome.get("high_ready")
    tracker["model_based_wsd_secondary_ready"] = outcome.get("secondary_ready")
    tracker["selected_source"] = "none"
    tracker["semantic_evidence_source_selected"] = "none"
    tracker["semantic_evidence_source_runtime_integration"] = False
    tracker["semantic_evidence_source_applied"] = False
    tracker["semantic_evidence_source_encoded"] = False
    tracker["semantic_evidence_source_state"] = "CANDIDATE_SOURCE_EVALUATED"
    tracker["residual_evaluation_status"] = "CANDIDATE_DISTRIBUTION_FROZEN"
    tracker["residual_threshold_eligible"] = False
    tracker["residual_source_selection_eligible"] = False
    tracker["residual_threshold"] = None
    tracker["residual_yes_no_emitted"] = False
    tracker["constituent_sense_resolution_state"] = "DEVELOPMENT_ANALYZED"
    tracker["constituent_sense_resolution_candidate_status"] = "COVERAGE_INSUFFICIENT"
    tracker["measurement_sample_drawn"] = False
    tracker["measurement_eligible"] = False
    tracker["revision_eligible"] = False
    tracker["select_authorized"] = False
    tracker["authorized"] = False
    tracker["admitted"] = 0
    tracker["settled"] = 0
    tracker["gold"] = 0
    tracker["procedure_v3_created"] = False
    tracker["procedure_v2_retuned"] = False
    tracker["next_legal_transition"] = outcome["next_legal_transition"]
    tracker["next_transition_authorized"] = False
    tracker_sha = write_json(TRACKER, tracker)
    check_sealed(skip={TRACKER})
    if sha256(EVENTS) != EXPECTED[EVENTS] or sha256(LEDGER_FILE) != EXPECTED[LEDGER_FILE]:
        refuse("ledger or events changed")
    return tracker_sha


def write_decision(outcome: dict, hashes: dict, analysis_sha: str | None) -> str:
    payload = {
        "analysis_sha256": analysis_sha,
        "candidate_status": outcome["candidate_status"],
        "determinism": outcome.get("determinism"),
        "high_ready": outcome.get("high_ready"),
        "json_schema_document": None,
        "license_receipt_sha256": hashes.get("license_sha256"),
        "measurement_eligible": False,
        "measurement_sample_drawn": False,
        "model_name": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "next_legal_transition": outcome["next_legal_transition"],
        "next_transition_authorized": False,
        "projection_sha256": hashes.get("projection_sha256"),
        "provenance_sha256": hashes.get("provenance_sha256"),
        "raw_output_sha256": hashes.get("raw_sha256"),
        "residual_replay_performed": False,
        "residual_scores_recomputed": False,
        "residual_state": "CANDIDATE_DISTRIBUTION_FROZEN",
        "residual_threshold_created": False,
        "resolution_sha256": hashes.get("resolution_sha256"),
        "rule": RULE_VERSION,
        "runtime_integration": False,
        "schema": "hyperlex.model_based_wsd_candidate_v1_decision.v1",
        "secondary_ready": outcome.get("secondary_ready"),
        "select_005_authorized": False,
        "selected_source": "none",
        "spec_sha256": hashes.get("spec_sha256"),
        "state": "CANDIDATE_EVALUATED",
        "threshold_eligible": False,
        "total_ready": outcome.get("total_ready"),
        "yes_no_emitted": False,
    }
    return write_json(DECISION_PATH, payload)


def main() -> None:
    check_sealed()
    weights = assert_weights()
    license_sha = write_json(LICENSE_PATH, license_payload(weights))
    spec = spec_payload(weights, license_sha)
    spec_text = json.dumps(spec, sort_keys=True)
    if "0.2139784896" in spec_text or "operator_bucket" in spec_text:
        refuse("spec contains a residual score or an operator field")
    spec_sha = write_json(SPEC_PATH, spec)
    if sha256(SPEC_PATH) != spec_sha:
        refuse("spec hash drifted at freeze")
    print(f"SPEC_FROZEN {spec_sha}", file=sys.stderr, flush=True)
    sealed_rows = load_sealed_rows()
    surfaces = {row["surface"] for row in sealed_rows}
    if FINANCIAL_CONTEXT in surfaces or RIVER_CONTEXT in surfaces:
        refuse("polarity control collides with a development surface")
    frozen = load_jsonl(RESOLVER_REPLAY_PATH)
    if sha256(RESOLVER_REPLAY_PATH) != EXPECTED[RESOLVER_REPLAY_PATH]:
        refuse("resolver replay changed while loading")
    exceptions = load_exceptions(WORDNET)
    by_id, _index = build_catalog()
    sense_index = load_sense_index(WORDNET / "index.sense")
    pool = prepare_pool(frozen, by_id, exceptions, sense_index)
    torch, tokenizer, model = import_runtime()
    polarity = polarity_control(torch, tokenizer, model, by_id, sense_index)
    hashes = {"license_sha256": license_sha, "spec_sha256": spec_sha}
    if not polarity["passed"]:
        provenance = {
            "hyperlex_scoring_started": False,
            "json_schema_document": None,
            "model_name": MODEL_NAME,
            "model_revision": MODEL_REVISION,
            "polarity_control": polarity,
            "schema": "hyperlex.model_based_wsd_candidate_v1_provenance.v1",
            "spec_sha256": spec_sha,
        }
        hashes["provenance_sha256"] = write_json(PROVENANCE_PATH, provenance)
        outcome = {
            "candidate_status": REJECTED,
            "determinism": None,
            "next_legal_transition": "MODEL_BASED_WSD_CANDIDATE_REVISION_AUTHORIZATION",
        }
        hashes["analysis_sha256"] = None
        hashes["decision_sha256"] = write_decision(outcome, hashes, None)
        update_tracker(outcome, hashes)
        print(json.dumps({"candidate_status": REJECTED, "spec_sha256": spec_sha}, sort_keys=True))
        return
    provenance = {
        "canonical_source": CANONICAL_SOURCE,
        "device": "cpu",
        "dtype": "float32",
        "hyperlex_scoring_started": False,
        "json_schema_document": None,
        "license_receipt_sha256": license_sha,
        "model_family": MODEL_FAMILY,
        "model_name": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "polarity_control_passed": True,
        "polarity_financial_winner": polarity["financial"]["selected_synset"],
        "polarity_river_winner": polarity["river"]["selected_synset"],
        "positive_class_index": POSITIVE_CLASS_INDEX,
        "residual_embeddings_used": False,
        "runtime": dict(RUNTIME),
        "schema": "hyperlex.model_based_wsd_candidate_v1_provenance.v1",
        "spec_sha256": spec_sha,
        "third_party_upload": True,
        "weights": {
            "pytorch_model_bin_sha256": weights["pytorch_model.bin"],
            "vocab_txt_sha256": weights["vocab.txt"],
        },
    }
    provenance_sha = write_json(PROVENANCE_PATH, provenance)
    hashes["provenance_sha256"] = provenance_sha
    if sha256(SPEC_PATH) != spec_sha:
        refuse("spec changed after provenance")
    print("HYPERLEX_SCORING_START", file=sys.stderr, flush=True)
    first = infer_pass(torch, tokenizer, model, pool, spec_sha)
    print("PASS_1_DONE", file=sys.stderr, flush=True)
    second = infer_pass(torch, tokenizer, model, pool, spec_sha)
    print("PASS_2_DONE", file=sys.stderr, flush=True)
    first_text = "".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in first)
    second_text = "".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in second)
    if first_text != second_text:
        mismatch = {
            "determinism": "NOT_DETERMINISTIC",
            "first_sha256": hashlib.sha256(first_text.encode("utf-8")).hexdigest(),
            "record_kind": "determinism_mismatch",
            "second_sha256": hashlib.sha256(second_text.encode("utf-8")).hexdigest(),
            "spec_sha256": spec_sha,
        }
        hashes["raw_sha256"] = write_jsonl(RAW_PATH, [mismatch])
        outcome = {
            "candidate_status": "NOT_DETERMINISTIC",
            "determinism": "NOT_DETERMINISTIC",
            "next_legal_transition": "MODEL_BASED_WSD_DETERMINISM_REVIEW_AUTHORIZATION",
        }
        hashes["decision_sha256"] = write_decision(outcome, hashes, None)
        update_tracker(outcome, hashes)
        print(json.dumps(outcome, sort_keys=True))
        return
    raw_sha = write_jsonl(RAW_PATH, first)
    hashes["raw_sha256"] = raw_sha
    resolutions = resolution_rows(pool, first)
    if any(row["prior_resolution_status"] != "AMBIGUOUS" for row in resolutions):
        refuse("tier 3 row was not previously ambiguous")
    resolution_sha = write_jsonl(RESOLUTION_PATH, resolutions)
    hashes["resolution_sha256"] = resolution_sha
    if sha256(SPEC_PATH) != spec_sha:
        refuse("scoring mutated the spec")
    projected, summary = project_rows(frozen, resolutions)
    tier3_counts = Counter(row["model_resolution_status"] for row in resolutions)
    confidence = summarize_confidence(resolutions)
    projection = {
        "combined_constituent_counts": summary["combined_constituent_counts"],
        "confidence": confidence,
        "determinism": IDENTICAL,
        "json_schema_document": None,
        "operator_labels_included": False,
        "raw_output_sha256": raw_sha,
        "residual_replay_performed": False,
        "residual_scores_recomputed": False,
        "resolution_sha256": resolution_sha,
        "row_counts": summary["row_counts"],
        "rows": projected,
        "schema": "hyperlex.model_based_wsd_candidate_v1_readiness_projection.v1",
        "spec_sha256": spec_sha,
        "tier3_attempts": len(resolutions),
        "tier3_counts": {
            "AMBIGUOUS": tier3_counts["AMBIGUOUS"],
            "ERROR": tier3_counts["ERROR"],
            "INVALID": tier3_counts["INVALID"],
            "RESOLVED": tier3_counts["RESOLVED"],
        },
    }
    projection_text = json.dumps(projection, sort_keys=True)
    if "operator_bucket" in projection_text or "HIGH" in projection["row_counts"]:
        refuse("projection carries an operator field")
    projection_sha = write_json(PROJECTION_PATH, projection)
    hashes["projection_sha256"] = projection_sha
    manifest = json.loads(EVIDENCE_MANIFEST.read_text(encoding="utf-8"))
    if sha256(EVIDENCE_MANIFEST) != EXPECTED[EVIDENCE_MANIFEST]:
        refuse("manifest changed during scoring")
    buckets = {row["row_id"]: row["operator_bucket"] for row in manifest["rows"]}
    counted = Counter(buckets.values())
    for name, expected_count in OPERATOR_COUNTS.items():
        if counted[name] != expected_count:
            refuse(f"operator count {name} is {counted[name]}")
    ready_by = {name: {"RESIDUAL_READY": 0, "UNKNOWN": 0} for name in OPERATORS}
    for row in projected:
        ready_by[buckets[row["parent_row_id"]]][row["projected_status"]] += 1
    total_ready = summary["row_counts"]["RESIDUAL_READY"]
    outcome = coverage_gate(
        high_ready=ready_by["HIGH"]["RESIDUAL_READY"],
        secondary_ready=ready_by["SECONDARY"]["RESIDUAL_READY"],
        total_ready=total_ready,
        invalid_output_count=tier3_counts["INVALID"],
        error_count=tier3_counts["ERROR"],
        determinism=IDENTICAL,
    )
    outcome["determinism"] = IDENTICAL
    outcome["high_ready"] = ready_by["HIGH"]["RESIDUAL_READY"]
    outcome["secondary_ready"] = ready_by["SECONDARY"]["RESIDUAL_READY"]
    outcome["total_ready"] = total_ready
    analysis = {
        "baseline": {
            "high_ready": BASELINE_HIGH_READY,
            "secondary_ready": BASELINE_SECONDARY_READY,
            "total_ready": BASELINE_TOTAL_READY,
        },
        "candidate_status": outcome["candidate_status"],
        "change_versus_lexical_baseline": {
            "high_ready_delta": outcome["high_ready"] - BASELINE_HIGH_READY,
            "secondary_ready_delta": outcome["secondary_ready"] - BASELINE_SECONDARY_READY,
            "total_ready_delta": total_ready - BASELINE_TOTAL_READY,
        },
        "combined_constituent_counts": summary["combined_constituent_counts"],
        "confidence": confidence,
        "determinism": IDENTICAL,
        "json_schema_document": None,
        "model_name": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "operator_labels_joined_after_projection_was_hashed": True,
        "operator_labels_used_during_inference": False,
        "projection_sha256": projection_sha,
        "ready_by_operator": ready_by,
        "residual_embeddings_used": False,
        "residual_replay_performed": False,
        "residual_scores_recomputed": False,
        "row_counts": summary["row_counts"],
        "rule": RULE_VERSION,
        "schema": "hyperlex.model_based_wsd_candidate_v1_development_analysis.v1",
        "selected_source": "none",
        "spec_sha256": spec_sha,
        "tier3_attempts": len(resolutions),
        "tier3_counts": projection["tier3_counts"],
        "yes_no_emitted": False,
    }
    for banned in ("accuracy", "precision", "recall", "f1"):
        if banned in analysis:
            refuse("analysis reports an accuracy metric")
    analysis_sha = write_json(ANALYSIS_PATH, analysis)
    hashes["analysis_sha256"] = analysis_sha
    hashes["decision_sha256"] = write_decision(outcome, hashes, analysis_sha)
    tracker_sha = update_tracker(outcome, hashes)
    if sha256(SPEC_PATH) != spec_sha or sha256(PROVENANCE_PATH) != provenance_sha:
        refuse("late write mutated the frozen spec")
    print(
        json.dumps(
            {
                "analysis_sha256": analysis_sha,
                "candidate_status": outcome["candidate_status"],
                "combined_constituent_counts": summary["combined_constituent_counts"],
                "decision_sha256": hashes["decision_sha256"],
                "determinism": IDENTICAL,
                "high_ready": outcome["high_ready"],
                "license_sha256": license_sha,
                "projection_sha256": projection_sha,
                "provenance_sha256": provenance_sha,
                "raw_sha256": raw_sha,
                "reject_ready": ready_by["REJECT"]["RESIDUAL_READY"],
                "resolution_sha256": resolution_sha,
                "secondary_ready": outcome["secondary_ready"],
                "spec_sha256": spec_sha,
                "tier3_counts": projection["tier3_counts"],
                "total_ready": total_ready,
                "tracker_sha256": tracker_sha,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
