"""Execute the frozen threshold stack on the v2 calibration surface only.

Measurement is hashed and otherwise untouched. Operator labels are loaded
only after the calibration score receipt is on disk.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from hyperlexical.residual_threshold_v1 import (
    ALGORITHM_ID,
    CONFOUND_REVIEW,
    INSUFFICIENT_SUPPORT,
    MIN_CALIBRATION_HIGH,
    MIN_CALIBRATION_SECONDARY,
    NO_DIRECTION,
    NO_THRESHOLD,
    THRESHOLD_FROZEN,
)

LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
SOURCE = LEDGER / "operator-review/HLX-EVAL-UNBIND-SEMANTIC-EVIDENCE-SOURCE-V1-001"
SENSE = LEDGER / "operator-review/HLX-EVAL-UNBIND-SENSE-SCREEN-V1-HYPOTHESIS-001"
WORDNET = LEDGER / "acquisition/sources/wordnet-3.0/wordnet"
EVENTS = LEDGER / "events.jsonl"
LEDGER_FILE = LEDGER / "ledger.json"
TRACKER = SENSE / "HYPOTHESIS.json"
EVIDENCE = SENSE / "DEVELOPMENT_EVIDENCE.json"

CALIBRATION_MANIFEST = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_MANIFEST.jsonl"
MEASUREMENT_MANIFEST = SOURCE / "RESIDUAL_THRESHOLD_V2_MEASUREMENT_MANIFEST.jsonl"
RESOLUTION_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_RESOLUTION.jsonl"
RESOLUTION_RECEIPT = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_RESOLUTION_RECEIPT.json"
SCORES_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SCORES.jsonl"
SCORE_RECEIPT = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SCORE_RECEIPT.json"
LABELS_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_LABELS.jsonl"
ANALYSIS_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_ANALYSIS.json"
CONFOUND_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_CONFOUND_ANALYSIS.json"
SEARCH_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_THRESHOLD_SEARCH.json"
FROZEN_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_THRESHOLD_FROZEN.json"
FAILURE_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_FAILURE.json"

AUTHORIZATION = "THRESHOLD_V2_CALIBRATION_EXECUTION_AUTHORIZATION"
MEASUREMENT_NEXT = "THRESHOLD_V2_MEASUREMENT_EXECUTION_AUTHORIZATION"
OPERATOR_CLASSES = ("HIGH", "SECONDARY", "REJECT", "QUARANTINE")

EXPECTED_CALIBRATION = "34bc70b93039fc6a5ba4bb58685e0fbfe6f91dd1f86a64fec8326a84013a6465"
EXPECTED_MEASUREMENT = "78ca09ab14912681d028e8b9b1c77a8daf1d0c8c81561434eb9b6ade45a753e5"
EXPECTED_TRACKER = "a4264943f0313dcde85c6da8b833ff0c45c5c23972e1a4d0f2e69fa00c3e09ad"
EXPECTED_EVENTS = "96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c"
EXPECTED_LEDGER = "77e22433203879b252f7a9e309d2013d7550101d1c4a014b494d2c96df87d0e0"
EXPECTED_V1_FAILURE = "1d3f1f26609c1f1a47790d94730fba50e9f4d888dd8d7d89e6fa698a924fb3a8"
EXPECTED_RESIDUAL_SPEC = "39c2914e32557ffe1a456a56f8742ea4fe8f1aaec1dc1da451656cd22f0db32d"
EXPECTED_WSD = "ed945989cf4947ac84633ba2c4aa10c1ba381d2396da0b573a844f83ec367a18"
EXPECTED_PREREG = "1c962703e12c5c48fd279dc766fd4d1d3108c40486a10789fdda112926e98261"
EXPECTED_SAMPLE = "46e3d32b4a4c8af73c9197557b09ceed872b1918d41143ed551bb3b4572c6151"
EXPECTED_DRAW = "b89cbd357138c8b9eabeabeca055695b15fd2163840438e53989a920191d3419"
EXPECTED_ISOLATION = "6ac513d9d7b3dd366f7c6f5ce5ca6821a33c5907d4bf2d1de45dc7a5a932bc38"
EXPECTED_DISTRIBUTION = "51d9a98a849248e40aadafd277c1c44adf0c7a7fcc842864f00d2fc3d8125886"

SEALED = {
    CALIBRATION_MANIFEST: EXPECTED_CALIBRATION,
    MEASUREMENT_MANIFEST: EXPECTED_MEASUREMENT,
    SOURCE / "RESIDUAL_THRESHOLD_V2_PREREGISTRATION.json": EXPECTED_PREREG,
    SOURCE / "RESIDUAL_THRESHOLD_V2_SAMPLE_SIZE.json": EXPECTED_SAMPLE,
    SOURCE / "RESIDUAL_THRESHOLD_V2_SURFACE_DRAW_RECEIPT.json": EXPECTED_DRAW,
    SOURCE / "RESIDUAL_THRESHOLD_V2_SURFACE_ISOLATION_REPORT.json": EXPECTED_ISOLATION,
    SOURCE / "RESIDUAL_THRESHOLD_V2_SURFACE_DISTRIBUTION_REPORT.json": EXPECTED_DISTRIBUTION,
    SOURCE / "RESIDUAL_THRESHOLD_V1_CALIBRATION_FAILURE.json": EXPECTED_V1_FAILURE,
    SOURCE / "RESIDUAL_THRESHOLD_V1_CALIBRATION_MANIFEST.jsonl": "ba561935cff5f9f0a36af0b8b24e4b69bce5fb2c61b5ea2236f0a664c56bcf5d",
    SOURCE / "RESIDUAL_CANDIDATE_SPEC.json": EXPECTED_RESIDUAL_SPEC,
    SOURCE / "MODEL_BASED_WSD_RESOLUTION.jsonl": EXPECTED_WSD,
    SOURCE / "INTEGRATED_CONSTITUENT_RESOLUTION_V1.jsonl": "0f5dafc3676a4071ce8c889e58958b90203589aa3e91d78111b4e3292bdd87fb",
    SOURCE / "RESIDUAL_DEVELOPMENT_SCORES.jsonl": "cea638679faeee1bc1c689823e7c0c08562c4d7ef1f8230bbbf4079239e7c3e7",
    EVIDENCE: "0e9b3c1af9dd573bf6e2034640e468e8ab9074e1e76c90cef1f39f68d607bc03",
    EVENTS: EXPECTED_EVENTS,
    LEDGER_FILE: EXPECTED_LEDGER,
    SOURCE / "HYPOTHESIS.json": "39127a810d38ede96d7947c33dbc3e5491c9e1cc9b3f76b1064d9e0dd04a7787",
    SENSE / "CLASSIFICATION_PROCEDURE.v2.json": "3f4071640d0c9f29cf56f53969a88ec25c635444b87765e77e1b9158470e5662",
}

OUTPUTS = (
    RESOLUTION_PATH,
    RESOLUTION_RECEIPT,
    SCORES_PATH,
    SCORE_RECEIPT,
    LABELS_PATH,
    ANALYSIS_PATH,
    CONFOUND_PATH,
    SEARCH_PATH,
    FROZEN_PATH,
    FAILURE_PATH,
)

MEASUREMENT_EXECUTION_NAMES = {
    "RESIDUAL_THRESHOLD_V2_MEASUREMENT_RESOLUTION.jsonl",
    "RESIDUAL_THRESHOLD_V2_MEASUREMENT_SCORES.jsonl",
    "RESIDUAL_THRESHOLD_V2_MEASUREMENT_LABELS.jsonl",
    "RESIDUAL_THRESHOLD_V2_MEASUREMENT_PREDICTIONS.jsonl",
}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def refuse(message: str) -> None:
    raise SystemExit(message)


def support_passed(ready_high: int, ready_secondary: int) -> bool:
    return ready_high >= MIN_CALIBRATION_HIGH and ready_secondary >= MIN_CALIBRATION_SECONDARY


def lesk_tie_rows(rows: list[dict]) -> list[dict]:
    """GlossBERT sees Lesk ties only. A structural pointer conflict stays Tier 1."""
    kept = []
    for row in rows:
        if row.get("constituent_index") is None or row.get("resolution_status") != "AMBIGUOUS":
            continue
        method = row.get("resolution_method")
        if method == "STRUCTURAL_EXACT":
            continue
        if method != "EXTENDED_LESK_V1":
            refuse("constituent decision is outside the frozen stack")
        kept.append(row)
    return kept


def _render_json(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def _render_jsonl(rows: list[dict]) -> str:
    return "".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in rows)


def _write_new(path: Path, text: str) -> str:
    if path.exists():
        refuse(f"refusing to rewrite {path.name}")
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)
    digest = sha256_file(path)
    if digest != sha256_bytes(text.encode("utf-8")):
        refuse(f"hash drifted on write: {path.name}")
    return digest


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _verify_sealed(include_tracker: bool = True) -> None:
    if include_tracker and sha256_file(TRACKER) != EXPECTED_TRACKER:
        refuse("tracker hash drifted")
    for path, expected in SEALED.items():
        if sha256_file(path) != expected:
            refuse(f"sealed artifact changed: {path.name}")


def _assert_measurement_sealed() -> None:
    if sha256_file(MEASUREMENT_MANIFEST) != EXPECTED_MEASUREMENT:
        refuse("measurement manifest changed")
    for name in MEASUREMENT_EXECUTION_NAMES:
        if (SOURCE / name).exists():
            refuse(f"measurement execution artifact exists: {name}")


def _sealed_rows(manifest: list[dict]) -> list[dict]:
    rows = []
    for row in manifest:
        pos, offset = row["pwn30_synset"].split(":", 1)
        if row["row_id"] != row["normalized_text_sha256"]:
            refuse("calibration row_id drifted")
        rows.append(
            {
                "gloss": row["frozen_gloss"],
                "pos": row["pos"],
                "row_id": row["row_id"],
                "sense_class": None,
                "surface": row["surface"],
                "synset_offset": offset,
                "synset_pos": pos,
            }
        )
    return rows


def _parent_summaries(sealed: list[dict], by_parent: dict) -> list[dict]:
    from hyperlexical.residual_model_resolved_replay_v1 import (
        EXACT,
        RESOLVED,
        abstention_reason,
        projection_token,
        row_projection,
    )

    summaries = []
    for row in sealed:
        items = by_parent.get(row["row_id"], [])
        tokens = [projection_token(item["resolution_tier"], item["resolution_status"]) for item in items]
        status = row_projection(tokens)
        raw = []
        for item in items:
            if item["resolution_status"] in {EXACT, RESOLVED}:
                raw.append(RESOLVED if item["resolution_status"] == RESOLVED else EXACT)
            else:
                raw.append(item["resolution_status"])
        summaries.append(
            {
                "abstention_reason": None if status == "RESIDUAL_READY" else abstention_reason(raw),
                "constituent_resolution_tiers": [item["resolution_tier"] for item in items],
                "pos": row["pos"],
                "row_id": row["row_id"],
                "row_resolution_status": status,
                "selected_constituent_synsets": [item["selected_pwn30_synset"] for item in items],
                "selected_sense_keys": [item["selected_sense_key_if_available"] for item in items],
                "surface": row["surface"],
                "synset": f"{row['synset_pos']}:{row['synset_offset']}",
            }
        )
    return summaries


def _resolve(sealed: list[dict]) -> tuple[list[dict], list[dict], dict, int]:
    from hyperlexical.constituent_sense_resolution_v1_replay import (
        PROCEDURE_PATH,
        SPEC_PATH,
        build_catalog,
        resolve_once,
    )
    from hyperlexical.model_based_wsd_candidate_v1 import MODEL_REVISION
    from hyperlexical.model_based_wsd_candidate_v1_replay import (
        import_runtime,
        infer_pass,
        load_sense_index,
        resolution_rows,
    )
    from hyperlexical.residual_model_resolved_replay_v1_replay import build_integrated, public_integrated
    from hyperlexical.residual_threshold_v1_calibration import _tier3_pool
    from hyperlexical.unbind_sense_screen_v1 import load_exceptions

    if MODEL_REVISION != "0cc3b83af5496e27ebcc95ef0cf37ea0a9281a7a":
        refuse("GlossBERT revision drifted")
    print("resolver catalog", file=sys.stderr, flush=True)
    by_id, index = build_catalog()
    exceptions = load_exceptions(WORDNET)
    spec_sha = sha256_file(SPEC_PATH)
    procedure_sha = sha256_file(PROCEDURE_PATH)
    wsd_spec_sha = sha256_file(SOURCE / "MODEL_BASED_WSD_CANDIDATE_SPEC.json")
    print("resolver pass 1", file=sys.stderr, flush=True)
    first = resolve_once(sealed, by_id, index, exceptions, spec_sha, procedure_sha)
    print("resolver pass 2", file=sys.stderr, flush=True)
    second = resolve_once(sealed, by_id, index, exceptions, spec_sha, procedure_sha)
    if first != second:
        _freeze_nondeterministic("resolver")
    sense_index = load_sense_index(WORDNET / "index.sense")
    pool_first = _tier3_pool(lesk_tie_rows(first), by_id, exceptions, sense_index)
    pool_second = _tier3_pool(lesk_tie_rows(second), by_id, exceptions, sense_index)
    if pool_first != pool_second:
        _freeze_nondeterministic("tier3_pool")
    model_rows: list[dict] = []
    if pool_first:
        from hyperlexical.model_based_wsd_candidate_v1_replay import assert_weights

        assert_weights()
        print(f"glossbert pool {len(pool_first)}", file=sys.stderr, flush=True)
        torch, tokenizer, model = import_runtime()
        raw_first = infer_pass(torch, tokenizer, model, pool_first, wsd_spec_sha)
        raw_second = infer_pass(torch, tokenizer, model, pool_second, wsd_spec_sha)
        if raw_first != raw_second:
            _freeze_nondeterministic("glossbert_scores")
        model_first = resolution_rows(pool_first, raw_first)
        model_second = resolution_rows(pool_second, raw_second)
        if model_first != model_second:
            _freeze_nondeterministic("glossbert_resolution")
        model_rows = model_first
    integrated_first, by_parent = build_integrated(first, model_rows, exceptions, sense_index)
    integrated_second, _by_parent_second = build_integrated(second, model_rows, exceptions, sense_index)
    if integrated_first != integrated_second:
        _freeze_nondeterministic("integrated_resolution")
    public_rows = [public_integrated(item) for item in integrated_first]
    return public_rows, model_rows, by_parent, len(pool_first)


def _score(sealed: list[dict], by_parent: dict, model_rows: list[dict], resolution_sha: str) -> tuple[list[dict], dict]:
    from hyperlexical.model_based_wsd_candidate_v1 import MODEL_NAME, MODEL_REVISION
    from hyperlexical.residual_model_resolved_replay_v1 import TIER3_GLOSSBERT
    from hyperlexical.residual_model_resolved_replay_v1_replay import (
        RESIDUAL_SPEC_SHA,
        apply_overflow,
        assemble_scores,
        encode_needed,
        nuisance_for,
        prepare_jobs,
        score_jobs,
    )
    from hyperlexical.semantic_compositionality_residual import MODEL_NAME as RESIDUAL_NAME
    from hyperlexical.semantic_compositionality_residual import MODEL_REVISION as RESIDUAL_REVISION
    from hyperlexical.semantic_compositionality_residual_replay import build_indexes, load_encoder
    from hyperlexical.unbind_sense_screen_v1 import load_exceptions

    if MODEL_NAME != "kanishka/GlossBERT" or MODEL_REVISION != "0cc3b83af5496e27ebcc95ef0cf37ea0a9281a7a":
        refuse("GlossBERT identity drifted")
    if RESIDUAL_NAME != "sentence-transformers/all-MiniLM-L6-v2":
        refuse("residual model drifted")
    if RESIDUAL_REVISION != "1110a243fdf4706b3f48f1d95db1a4f5529b4d41":
        refuse("residual revision drifted")
    if RESIDUAL_SPEC_SHA != EXPECTED_RESIDUAL_SPEC:
        refuse("residual spec hash drifted")
    exceptions = load_exceptions(WORDNET)
    residual_by_id, _residual_index = build_indexes()
    model_index = {(row["parent_row_id"], row["constituent_index"]): row for row in model_rows}
    jobs, unknown = prepare_jobs(sealed, by_parent, residual_by_id, exceptions, model_index)
    encoder = load_encoder()
    kept, overflow = apply_overflow(encoder, jobs)
    print("residual encode pass 1", file=sys.stderr, flush=True)
    vectors_first = encode_needed(encoder, kept)
    scored_first = score_jobs(kept, vectors_first, resolution_sha)
    print("residual encode pass 2", file=sys.stderr, flush=True)
    vectors_second = encode_needed(encoder, kept)
    scored_second = score_jobs(kept, vectors_second, resolution_sha)
    if vectors_first != vectors_second or scored_first != scored_second:
        _freeze_nondeterministic("residual_scores")
    scores = assemble_scores(sealed, scored_first, unknown, overflow)
    nuisance = {job["row_id"]: nuisance_for(job) for job in kept}
    for row in scores:
        if "operator_bucket" in row:
            refuse("score artifact contains an operator label")
        if row["score_status"] == "SCORED":
            row["uses_tier3"] = TIER3_GLOSSBERT in row["constituent_resolution_tiers"]
    return scores, nuisance


def _freeze_nondeterministic(gate: str) -> None:
    _assert_measurement_sealed()
    if FAILURE_PATH.exists():
        refuse(f"NOT_DETERMINISTIC during {gate}")
    payload = {
        "failed_gate": gate,
        "failure_state": "NOT_DETERMINISTIC",
        "json_schema_document": None,
        "json_schema_exists": False,
        "measurement_touched": False,
        "schema": "hyperlex.residual_threshold_v2_calibration_failure.v1",
        "threshold_frozen": False,
        "threshold_value": None,
    }
    _write_new(FAILURE_PATH, _render_json(payload))
    _update_tracker("NOT_DETERMINISTIC", None, sha256_file(FAILURE_PATH), {})
    refuse("NOT_DETERMINISTIC")


def _label_index(calibration_ids: set[str]) -> dict[str, str | None]:
    found: dict[str, str | None] = {}

    def add(row_id: str, bucket: str | None) -> None:
        if row_id not in calibration_ids:
            return
        prior = found.get(row_id)
        if prior is not None and prior != bucket:
            refuse(f"operator labels disagree for {row_id}")
        found[row_id] = bucket

    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    for row in evidence["rows"]:
        add(row["row_id"], row.get("operator_bucket"))
    root = LEDGER / "operator-review"
    for path in sorted(root.rglob("*labels*.jsonl")):
        if "MEASUREMENT" in path.name:
            continue
        for row in _read_jsonl(path):
            if "operator_bucket" not in row or "row_id" not in row:
                continue
            add(row["row_id"], row["operator_bucket"])
    return found


def _support(labels: list[dict]) -> dict:
    ready = Counter()
    unknown = Counter()
    unlabeled = {"SCORED": 0, "UNKNOWN": 0}
    for row in labels:
        bucket = row["operator_bucket"]
        status = row["score_status"]
        if bucket not in OPERATOR_CLASSES:
            unlabeled[status] += 1
            continue
        if status == "SCORED":
            ready[bucket] += 1
        else:
            unknown[bucket] += 1
    return {
        "ready": {name: ready[name] for name in OPERATOR_CLASSES},
        "unlabeled": unlabeled["SCORED"] + unlabeled["UNKNOWN"],
        "unlabeled_scored": unlabeled["SCORED"],
        "unlabeled_unknown": unlabeled["UNKNOWN"],
        "unknown_by_class": {name: unknown[name] for name in OPERATOR_CLASSES},
    }


def _search_payload(selectable: list[dict], selection: dict) -> dict:
    from decimal import Decimal

    from hyperlexical.residual_threshold_v1 import (
        MIN_PREDICTED_YES,
        PRECISION_FLOOR,
        WILSON_LOWER_FLOOR,
        _candidate_thresholds,
        _high_recall,
        _passes_candidate,
        _precision_terms,
        _ready_rows,
        _safety_counts,
        _stable,
        precision_gates,
        wilson_interval,
    )

    if selection["calibration_state"] in {INSUFFICIENT_SUPPORT, NO_DIRECTION, CONFOUND_REVIEW}:
        return {
            "candidate_count": None,
            "candidates_evaluated": False,
            "gate_pass_counts": None,
            "json_schema_document": None,
            "json_schema_exists": False,
            "reason": selection["calibration_state"],
            "schema": "hyperlex.residual_threshold_v2_threshold_search.v1",
            "search_executed": False,
            "selected_threshold": None,
            "selection_algorithm_id": ALGORITHM_ID,
        }
    ready = _ready_rows(selectable)
    comparison = [row for row in ready if row["operator_bucket"] in {"HIGH", "SECONDARY"}]
    candidates = _candidate_thresholds(ready)
    counts: Counter[str] = Counter()
    passing = []
    for threshold in candidates:
        true_high, support = _precision_terms(comparison, threshold)
        precision_ok = precision_gates(
            true_high,
            support,
            minimum_yes=MIN_PREDICTED_YES,
            precision_floor=PRECISION_FLOOR,
            wilson_floor=WILSON_LOWER_FLOOR,
        )
        safety = _safety_counts(ready, threshold)
        reject_ok = safety["reject_predicted_yes"] == 0
        quarantine_ok = safety["quarantine_predicted_yes"] == 0
        stable = _stable(
            comparison,
            threshold,
            minimum_yes=MIN_PREDICTED_YES,
            precision_floor=PRECISION_FLOOR,
            wilson_floor=WILSON_LOWER_FLOOR,
        )
        interval = wilson_interval(true_high, support)
        wilson_ok = interval is not None and interval[0] >= WILSON_LOWER_FLOOR
        support_ok = support >= MIN_PREDICTED_YES
        counts["candidates"] += 1
        counts["predicted_yes_support"] += int(support_ok)
        counts["precision"] += int(precision_ok and support_ok)
        counts["wilson_lower"] += int(wilson_ok)
        counts["leave_one_out"] += int(stable)
        counts["reject_veto"] += int(reject_ok)
        counts["quarantine_veto"] += int(quarantine_ok)
        if _passes_candidate(ready, comparison, threshold):
            counts["all_gates"] += 1
            passing.append((str(_high_recall(comparison, threshold)), threshold))
    selected = selection.get("threshold_value")
    if passing:
        best = max(passing, key=lambda item: (Decimal(item[0]), Decimal(item[1])))
        if selected != best[1]:
            refuse("threshold search disagrees with select_threshold")
    elif selected is not None:
        refuse("select_threshold returned a value with no passing candidate")
    return {
        "candidate_count": len(candidates),
        "candidates_evaluated": True,
        "gate_pass_counts": dict(sorted(counts.items())),
        "json_schema_document": None,
        "json_schema_exists": False,
        "schema": "hyperlex.residual_threshold_v2_threshold_search.v1",
        "search_executed": True,
        "selected_threshold": selected,
        "selection_algorithm_id": ALGORITHM_ID,
    }


def _confound_rows(joined: list[dict], nuisance: dict) -> list[dict]:
    rows = []
    for row in joined:
        if row["score_status"] != "SCORED" or row["operator_bucket"] not in OPERATOR_CLASSES:
            continue
        extra = nuisance.get(row["row_id"])
        if extra is None:
            refuse("ready row is missing nuisance fields")
        rows.append(
            {
                "bucket": row["operator_bucket"],
                "character_length": extra["character_length"],
                "content_count": extra["content_count"],
                "max_candidate_senses": extra["max_candidate_senses"],
                "min_glossbert_confidence": extra["min_glossbert_confidence"],
                "min_glossbert_margin": extra["min_glossbert_margin"],
                "pos": row["pos"],
                "residual_score": row["residual_score"],
                "row_id": row["row_id"],
                "surface": extra["surface"],
                "synset": extra["synset"],
                "tiers": list(extra["tiers"]),
                "token_count": extra["token_count"],
                "uses_tier3": row["uses_tier3"],
            }
        )
    return rows


def _judge(nuisance: dict) -> dict:
    receipt = json.loads(SCORE_RECEIPT.read_text(encoding="utf-8"))
    if receipt["operator_labels_loaded"] is not False or receipt["operator_labels_joined"] is not False:
        refuse("score receipt does not record a pre-label freeze")
    if receipt["calibration_score_frozen"] is not True or receipt["measurement_touched"] is not False:
        refuse("score receipt is not a sealed pre-label freeze")
    if sha256_file(SCORES_PATH) != receipt["score_sha256"]:
        refuse("score hash drifted before the label join")
    scores = _read_jsonl(SCORES_PATH)
    manifest = {row["row_id"]: row for row in _read_jsonl(CALIBRATION_MANIFEST)}
    labels_by_id = _label_index(set(manifest))
    joined = []
    for score in scores:
        row_id = score["row_id"]
        manifest_row = manifest[row_id]
        bucket = labels_by_id.get(row_id)
        if bucket not in OPERATOR_CLASSES:
            bucket = None
        joined.append(
            {
                "operator_bucket": bucket,
                "operator_label_present": bucket is not None,
                "pos": score.get("pos", manifest_row["pos"]),
                "residual_score": score.get("residual_score"),
                "row_id": row_id,
                "score_status": score["score_status"],
                "surface": manifest_row["surface"],
                "uses_tier3": score.get("uses_tier3"),
            }
        )
    label_rows = [
        {
            "operator_bucket": row["operator_bucket"],
            "operator_label_present": row["operator_label_present"],
            "row_id": row["row_id"],
            "score_status": row["score_status"],
        }
        for row in joined
    ]
    label_sha = _write_new(LABELS_PATH, _render_jsonl(label_rows))
    support = _support(joined)
    passed = support_passed(support["ready"]["HIGH"], support["ready"]["SECONDARY"])
    analysis = {
        "admitted": 0,
        "authorization": AUTHORIZATION,
        "confound_result": "NOT_RUN",
        "direction_result": "NOT_RUN",
        "gold": 0,
        "json_schema_document": None,
        "json_schema_exists": False,
        "label_sha256": label_sha,
        "measurement_labels_loaded": False,
        "measurement_state": "SEALED",
        "schema": "hyperlex.residual_threshold_v2_calibration_analysis.v1",
        "score_receipt_sha256": sha256_file(SCORE_RECEIPT),
        "score_sha256": sha256_file(SCORES_PATH),
        "select_005_authorized": False,
        "selected_source": "none",
        "settled": 0,
        "support": support,
        "support_gate": {
            "minimum_ready_high": MIN_CALIBRATION_HIGH,
            "minimum_ready_secondary": MIN_CALIBRATION_SECONDARY,
            "passed": passed,
        },
    }
    if not passed:
        analysis["calibration_state"] = INSUFFICIENT_SUPPORT
        analysis_sha = _write_new(ANALYSIS_PATH, _render_json(analysis))
        confound = {
            "confound_gate_executed": False,
            "confound_result": "NOT_RUN",
            "frozen_stop_conditions": ["tier3_concentrated", "extreme_driven", "pos_partitioned"],
            "json_schema_document": None,
            "json_schema_exists": False,
            "reason": INSUFFICIENT_SUPPORT,
            "schema": "hyperlex.residual_threshold_v2_calibration_confound_analysis.v1",
        }
        confound_sha = _write_new(CONFOUND_PATH, _render_json(confound))
        search = _search_payload([], {"calibration_state": INSUFFICIENT_SUPPORT})
        search_sha = _write_new(SEARCH_PATH, _render_json(search))
        failure = _failure(INSUFFICIENT_SUPPORT, "support", analysis_sha, label_sha, search_sha, confound_sha, support, None, None, None)
        return _finish(INSUFFICIENT_SUPPORT, None, failure, {
            "analysis": analysis_sha,
            "confound": confound_sha,
            "failure": sha256_file(FAILURE_PATH),
            "labels": label_sha,
            "search": search_sha,
        })
    return _select(joined, analysis, label_sha, nuisance)


def _failure(state: str, gate: str, analysis_sha: str, label_sha: str, search_sha: str, confound_sha: str, support: dict, direction, confound, candidate_count) -> str:
    payload = {
        "analysis_sha256": analysis_sha,
        "confound_sha256": confound_sha,
        "failed_gate": gate,
        "failure_state": state,
        "json_schema_document": None,
        "json_schema_exists": False,
        "label_sha256": label_sha,
        "measurement_touched": False,
        "observed_confounds": confound,
        "observed_direction": direction,
        "observed_support": support,
        "observed_threshold_candidate_count": candidate_count,
        "schema": "hyperlex.residual_threshold_v2_calibration_failure.v1",
        "search_sha256": search_sha,
        "threshold_frozen": False,
        "threshold_value": None,
    }
    return _write_new(FAILURE_PATH, _render_json(payload))


def _select(joined: list[dict], analysis: dict, label_sha: str, nuisance: dict) -> dict:
    from hyperlexical.residual_model_resolved_replay_v1 import confound_report
    from hyperlexical.residual_threshold_v1 import select_threshold

    selectable = []
    for row in joined:
        if row["operator_bucket"] not in OPERATOR_CLASSES:
            continue
        if row["uses_tier3"] is None or row["pos"] is None:
            refuse("labeled calibration row is missing tier or pos provenance")
        selectable.append(
            {
                "development_row": False,
                "operator_bucket": row["operator_bucket"],
                "pos": row["pos"],
                "residual_score": row["residual_score"],
                "score_status": row["score_status"],
                "uses_tier3": row["uses_tier3"],
            }
        )
    print("threshold selection pass 1", file=sys.stderr, flush=True)
    first = select_threshold(selectable)
    print("threshold selection pass 2", file=sys.stderr, flush=True)
    second = select_threshold(selectable)
    if first != second:
        _freeze_nondeterministic("threshold_selection")
    state = first["calibration_state"]
    analysis["calibration_state"] = state
    analysis["direction_result"] = first.get("direction", "NOT_RUN")
    analysis["confound_result"] = first.get("confound", "NOT_RUN")
    analysis["selection"] = first
    analysis_sha = _write_new(ANALYSIS_PATH, _render_json(analysis))
    direction = first.get("direction")
    confound_body: dict
    if direction != "SUPPORTED_DIRECTION":
        confound_body = {
            "confound_gate_executed": False,
            "confound_result": "NOT_RUN",
            "frozen_stop_conditions": ["tier3_concentrated", "extreme_driven", "pos_partitioned"],
            "json_schema_document": None,
            "json_schema_exists": False,
            "reason": state,
            "schema": "hyperlex.residual_threshold_v2_calibration_confound_analysis.v1",
        }
    else:
        report = confound_report(_confound_rows(joined, nuisance))
        flags = {
            "extreme_driven": report["extreme_driven"],
            "pos_partitioned": report["pos_partitioned"],
            "tier3_concentrated": bool(report["tier3"]["concentrated"]),
        }
        selector_flags = first.get("confound")
        if selector_flags is not None and selector_flags != flags:
            refuse("confound report disagrees with select_threshold")
        fired = flags["extreme_driven"] or flags["pos_partitioned"] or flags["tier3_concentrated"]
        confound_body = {
            "confound_gate_executed": True,
            "confound_result": "STOP" if fired else "PASS",
            "frozen_stop_conditions": flags,
            "json_schema_document": None,
            "json_schema_exists": False,
            "nuisance_changes_stop_decision": False,
            "report": report,
            "schema": "hyperlex.residual_threshold_v2_calibration_confound_analysis.v1",
        }
    confound_sha = _write_new(CONFOUND_PATH, _render_json(confound_body))
    search = _search_payload(selectable, first)
    search_sha = _write_new(SEARCH_PATH, _render_json(search))
    support = analysis["support"]
    if state != THRESHOLD_FROZEN:
        gates = {
            INSUFFICIENT_SUPPORT: "support",
            NO_DIRECTION: "direction",
            CONFOUND_REVIEW: "confound",
            NO_THRESHOLD: "precision_gate",
        }
        failure_sha = _failure(
            state,
            gates[state],
            analysis_sha,
            label_sha,
            search_sha,
            confound_sha,
            support,
            direction,
            first.get("confound"),
            search["candidate_count"],
        )
        return _finish(state, None, failure_sha, {
            "analysis": analysis_sha,
            "confound": confound_sha,
            "failure": failure_sha,
            "labels": label_sha,
            "search": search_sha,
        })
    metrics = first["selection_metrics"]
    frozen = {
        "algorithm_id": ALGORITHM_ID,
        "calibration_label_sha256": label_sha,
        "calibration_manifest_sha256": EXPECTED_CALIBRATION,
        "calibration_resolution_sha256": sha256_file(RESOLUTION_PATH),
        "calibration_score_sha256": sha256_file(SCORES_PATH),
        "confound_result": confound_body["confound_result"],
        "confound_sha256": confound_sha,
        "direction_result": direction,
        "false_high": metrics["false_high"],
        "high_recall": metrics["high_recall"],
        "json_schema_document": None,
        "json_schema_exists": False,
        "leave_one_out_result": "PASS",
        "measurement_state": "SEALED",
        "measurement_touched": False,
        "precision": metrics["precision"],
        "predicted_yes_support": metrics["predicted_yes_support"],
        "quarantine_predicted_yes": metrics["quarantine_predicted_yes"],
        "reject_predicted_yes": metrics["reject_predicted_yes"],
        "residual_candidate_spec_sha256": EXPECTED_RESIDUAL_SPEC,
        "runtime_integration": False,
        "schema": "hyperlex.residual_threshold_v2_threshold_frozen.v1",
        "search_sha256": search_sha,
        "select_005_authorized": False,
        "selected_source": "none",
        "selection_algorithm_id": ALGORITHM_ID,
        "selection_receipt": first,
        "threshold_frozen": True,
        "threshold_id": "T_HIGH",
        "threshold_value": first["threshold_value"],
        "true_high": metrics["true_high"],
        "wilson_lower": metrics["precision_interval"][0],
        "wilson_upper": metrics["precision_interval"][1],
    }
    frozen_sha = _write_new(FROZEN_PATH, _render_json(frozen))
    return _finish(THRESHOLD_FROZEN, first["threshold_value"], frozen_sha, {
        "analysis": analysis_sha,
        "confound": confound_sha,
        "labels": label_sha,
        "search": search_sha,
        "threshold": frozen_sha,
    })


def _update_tracker(state: str, threshold_value, outcome_sha: str, hashes: dict) -> str:
    if sha256_file(TRACKER) != EXPECTED_TRACKER:
        refuse("tracker hash drifted before the calibration update")
    tracker = json.loads(TRACKER.read_text(encoding="utf-8"))
    if tracker.get("residual_threshold_state") != "CALIBRATION_INSUFFICIENT_SUPPORT":
        refuse("v1 execution state drifted")
    if tracker.get("residual_threshold_v1_disposition") != "CLOSED_CALIBRATION_DESIGN_INSUFFICIENT":
        refuse("v1 disposition drifted")
    if tracker.get("residual_threshold_value") is not None or tracker.get("residual_threshold_frozen") is not False:
        refuse("v1 threshold drifted")
    tracker["previous_tracker_sha256"] = EXPECTED_TRACKER
    tracker["residual_threshold_v2_state"] = state
    tracker["residual_threshold_v2_value"] = threshold_value
    tracker["residual_threshold_v2_frozen"] = state == THRESHOLD_FROZEN
    tracker["residual_threshold_v2_calibration_executed"] = state != "NOT_DETERMINISTIC" or RESOLUTION_PATH.exists()
    tracker["residual_threshold_v2_calibration_resolution_frozen"] = RESOLUTION_PATH.exists()
    tracker["residual_threshold_v2_calibration_scores_frozen"] = SCORES_PATH.exists()
    tracker["residual_threshold_v2_calibration_labeled"] = LABELS_PATH.exists()
    tracker["residual_threshold_v2_measurement_state"] = "SEALED"
    tracker["residual_threshold_v2_measurement_resolved"] = False
    tracker["residual_threshold_v2_measurement_scored"] = False
    tracker["residual_threshold_v2_measurement_labeled"] = False
    tracker["residual_threshold_v2_redraw_authorized"] = False
    tracker["measurement_eligible"] = False
    tracker["selected_source"] = "none"
    tracker["select_authorized"] = False
    tracker["admitted"] = 0
    tracker["settled"] = 0
    tracker["gold"] = 0
    if state == THRESHOLD_FROZEN:
        tracker["next_legal_transition"] = MEASUREMENT_NEXT
    else:
        tracker["next_legal_transition"] = "NONE"
    tracker["next_transition_authorized"] = False
    if RESOLUTION_PATH.exists():
        tracker["residual_threshold_v2_calibration_resolution_sha256"] = sha256_file(RESOLUTION_PATH)
    if RESOLUTION_RECEIPT.exists():
        tracker["residual_threshold_v2_calibration_resolution_receipt_sha256"] = sha256_file(RESOLUTION_RECEIPT)
    if SCORES_PATH.exists():
        tracker["residual_threshold_v2_calibration_scores_sha256"] = sha256_file(SCORES_PATH)
    if SCORE_RECEIPT.exists():
        tracker["residual_threshold_v2_calibration_score_receipt_sha256"] = sha256_file(SCORE_RECEIPT)
    for key, digest in hashes.items():
        tracker[f"residual_threshold_v2_calibration_{key}_sha256"] = digest
    if state == THRESHOLD_FROZEN:
        tracker["residual_threshold_v2_threshold_frozen_sha256"] = outcome_sha
    elif FAILURE_PATH.exists():
        tracker["residual_threshold_v2_calibration_failure_sha256"] = outcome_sha
    text = json.dumps(tracker, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    TRACKER.write_text(text, encoding="utf-8")
    TRACKER.chmod(0o600)
    if tracker["residual_threshold_state"] != "CALIBRATION_INSUFFICIENT_SUPPORT":
        refuse("v1 execution state was overwritten")
    return sha256_file(TRACKER)


def _finish(state: str, threshold_value, outcome_sha: str, hashes: dict) -> dict:
    _assert_measurement_sealed()
    _verify_sealed()
    tracker_sha = _update_tracker(state, threshold_value, outcome_sha, hashes)
    for path, expected in SEALED.items():
        if sha256_file(path) != expected:
            refuse(f"sealed artifact changed after calibration: {path.name}")
    if sha256_file(EVENTS) != EXPECTED_EVENTS or sha256_file(LEDGER_FILE) != EXPECTED_LEDGER:
        refuse("events or ledger changed")
    report = {
        "determinism": "IDENTICAL",
        "outcome_sha256": outcome_sha,
        "state": state,
        "threshold_value": threshold_value,
        "tracker_sha256": tracker_sha,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


def execute() -> dict:
    for path in OUTPUTS:
        if path.exists():
            refuse(f"calibration artifact already exists: {path.name}")
    _verify_sealed()
    _assert_measurement_sealed()
    manifest = _read_jsonl(CALIBRATION_MANIFEST)
    if len(manifest) != 200 or sha256_file(CALIBRATION_MANIFEST) != EXPECTED_CALIBRATION:
        refuse("calibration manifest failed the pre-resolution check")
    if sha256_file(MEASUREMENT_MANIFEST) != EXPECTED_MEASUREMENT:
        refuse("measurement manifest failed the pre-resolution check")
    sealed = _sealed_rows(manifest)
    public_rows, model_rows, by_parent, pool_size = _resolve(sealed)
    rendered_resolution = _render_jsonl(public_rows)
    resolution_sha = sha256_bytes(rendered_resolution.encode("utf-8"))
    summaries = _parent_summaries(sealed, by_parent)
    if len(summaries) != 200:
        refuse("resolution did not cover 200 calibration rows")
    ready = sum(1 for row in summaries if row["row_resolution_status"] == "RESIDUAL_READY")
    unknown = sum(1 for row in summaries if row["row_resolution_status"] == "UNKNOWN")
    if ready + unknown != 200:
        refuse("row resolution status left the frozen vocabulary")
    resolution_receipt = {
        "abstention_reasons_present": True,
        "authorization": AUTHORIZATION,
        "calibration_rows": 200,
        "determinism": "IDENTICAL",
        "extended_lesk_run": True,
        "glossbert_revision": "0cc3b83af5496e27ebcc95ef0cf37ea0a9281a7a",
        "glossbert_run": pool_size > 0,
        "json_schema_document": None,
        "json_schema_exists": False,
        "measurement_glossbert_run": False,
        "measurement_labels_loaded": False,
        "measurement_minilm_run": False,
        "measurement_resolved": False,
        "measurement_touched": False,
        "operator_labels_joined": False,
        "operator_labels_loaded": False,
        "parent_rows": summaries,
        "residual_ready_rows": ready,
        "resolution_passes": 2,
        "resolution_sha256": resolution_sha,
        "schema": "hyperlex.residual_threshold_v2_calibration_resolution_receipt.v1",
        "tier3_pool": pool_size,
        "unknown_rows": unknown,
    }
    _write_new(RESOLUTION_PATH, rendered_resolution)
    _write_new(RESOLUTION_RECEIPT, _render_json(resolution_receipt))
    if sha256_file(RESOLUTION_PATH) != resolution_sha:
        refuse("resolution hash drifted")
    scores, nuisance = _score(sealed, by_parent, model_rows, resolution_sha)
    scored_ready = sum(1 for row in scores if row["score_status"] == "SCORED")
    if scored_ready != ready:
        refuse("scored rows do not match residual-ready rows")
    score_text = _render_jsonl(scores)
    score_sha = sha256_bytes(score_text.encode("utf-8"))
    score_receipt = {
        "authorization": AUTHORIZATION,
        "calibration_score_frozen": True,
        "determinism": "IDENTICAL",
        "extended_lesk_run": True,
        "glossbert_run": pool_size > 0,
        "integrated_resolution_sha256": resolution_sha,
        "json_schema_document": None,
        "json_schema_exists": False,
        "measurement_glossbert_run": False,
        "measurement_labels_loaded": False,
        "measurement_minilm_run": False,
        "measurement_resolved": False,
        "measurement_scored": False,
        "measurement_touched": False,
        "minilm_encode": True,
        "operator_labels_joined": False,
        "operator_labels_loaded": False,
        "ready_rows": scored_ready,
        "residual_candidate_spec_sha256": EXPECTED_RESIDUAL_SPEC,
        "residual_model_revision": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
        "schema": "hyperlex.residual_threshold_v2_calibration_score_receipt.v1",
        "score_passes": 2,
        "score_sha256": score_sha,
        "selected_source": "none",
        "unknown_rows": 200 - scored_ready,
    }
    _write_new(SCORES_PATH, score_text)
    _write_new(SCORE_RECEIPT, _render_json(score_receipt))
    _assert_measurement_sealed()
    if sha256_file(CALIBRATION_MANIFEST) != EXPECTED_CALIBRATION:
        refuse("calibration manifest changed during scoring")
    return _judge(nuisance)


def main() -> None:
    execute()


if __name__ == "__main__":
    main()
