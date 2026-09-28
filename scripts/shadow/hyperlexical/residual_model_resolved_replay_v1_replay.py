"""Replay the frozen residual on the frozen constituent-sense stack.

Operator labels are read only after the score artifact and its receipt have
been hashed. The residual model, the three resolution tiers, and the residual
formula are not changed.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from hyperlexical.constituent_sense_resolution_v1_replay import (
    EVENTS,
    EVIDENCE_MANIFEST,
    HYPERLEX,
    LEDGER_FILE,
    OPERATOR_COUNTS,
    OPERATORS,
    REPLAY_PATH as RESOLVER_REPLAY_PATH,
    SOURCE,
    TRACKER,
    WORDNET,
    load_sealed_rows,
    refuse,
    sha256,
    write_json,
    write_jsonl,
)
from hyperlexical.model_based_wsd_candidate_v1_replay import (
    ANALYSIS_PATH as WSD_ANALYSIS_PATH,
    DECISION_PATH as WSD_DECISION_PATH,
    EXPECTED as WSD_EXPECTED,
    LICENSE_PATH as WSD_LICENSE_PATH,
    PROJECTION_PATH,
    PROVENANCE_PATH as WSD_PROVENANCE_PATH,
    RAW_PATH as WSD_RAW_PATH,
    RESOLUTION_PATH as WSD_RESOLUTION_PATH,
    SPEC_PATH as WSD_SPEC_PATH,
    load_jsonl,
    load_sense_index,
    sense_keys_for,
)
from hyperlexical.residual_model_resolved_replay_v1 import (
    AMBIGUOUS,
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    EXACT,
    RESOLVED,
    TIER1_STRUCTURAL,
    TIER3_GLOSSBERT,
    UNRESOLVED,
    abstention_reason,
    analysis_plan,
    bootstrap_intervals,
    confound_report,
    direction_result,
    full_distribution,
    integrate_constituent,
    outlier_pair,
    pair_comparison,
    projection_token,
    replay_decision,
    row_projection,
)
from hyperlexical.semantic_compositionality_residual import (
    COMPOSITION_OPERATOR,
    DISTANCE_METRIC,
    MODEL_NAME,
    MODEL_REVISION,
    representation_text,
    residual_score,
    select_lemma,
    vector_hash,
)
from hyperlexical.semantic_compositionality_residual_replay import (
    MAX_SEQUENCE_LENGTH,
    OUTPUT_DIMENSION,
    build_indexes,
    encode_texts,
    load_encoder,
    pointer_records,
    token_length,
)
from hyperlexical.unbind_sense_screen_v1 import load_exceptions

RESIDUAL_SPEC = SOURCE / "RESIDUAL_CANDIDATE_SPEC.json"
RESIDUAL_SCORES = SOURCE / "RESIDUAL_DEVELOPMENT_SCORES.jsonl"
INTEGRATED_PATH = SOURCE / "INTEGRATED_CONSTITUENT_RESOLUTION_V1.jsonl"
SCORES_PATH = SOURCE / "RESIDUAL_V1_MODEL_RESOLVED_REPLAY_SCORES.jsonl"
RECEIPT_PATH = SOURCE / "RESIDUAL_V1_MODEL_RESOLVED_REPLAY_RECEIPT.json"
ANALYSIS_PATH = SOURCE / "RESIDUAL_V1_MODEL_RESOLVED_DEVELOPMENT_ANALYSIS.json"
CONFOUND_PATH = SOURCE / "RESIDUAL_V1_MODEL_RESOLVED_CONFOUND_ANALYSIS.json"
DECISION_PATH = SOURCE / "RESIDUAL_V1_MODEL_RESOLVED_CANDIDATE_DECISION.json"

CURRENT_TRACKER = "6da1e9730c785d2784d23433455515989d312ed8c76f4763b3a2dd6a1f2c4b2d"
RESIDUAL_SPEC_SHA = "39c2914e32557ffe1a456a56f8742ea4fe8f1aaec1dc1da451656cd22f0db32d"
RESIDUAL_SCORES_SHA = "cea638679faeee1bc1c689823e7c0c08562c4d7ef1f8230bbbf4079239e7c3e7"
AUTHORIZATION = "RESIDUAL_REPLAY_WITH_MODEL_RESOLVED_SENSES_AUTHORIZATION"
EXPECTED_READY = 73
EXPECTED_UNKNOWN = 152

EXPECTED = dict(WSD_EXPECTED)
EXPECTED[TRACKER] = CURRENT_TRACKER
EXPECTED[WSD_SPEC_PATH] = "c861ff7fff11ae6a790531267229c18d6e6e0a171a9bf6c34cfb6f7e7b14498c"
EXPECTED[WSD_PROVENANCE_PATH] = "6d91283244a88f44477c836e6549118d5d96a36bb878bf448fcadb13ff765e11"
EXPECTED[WSD_LICENSE_PATH] = "67d45243959e3e76643a675d49b508a73d0f7f0bf8fbf060ce7b83c9200c621b"
EXPECTED[WSD_RAW_PATH] = "a0e508c225e6db4cdbcae701682202b1d854f3762546dbfe10b84a15e0e9e17c"
EXPECTED[WSD_RESOLUTION_PATH] = "ed945989cf4947ac84633ba2c4aa10c1ba381d2396da0b573a844f83ec367a18"
EXPECTED[PROJECTION_PATH] = "c75834faf4a84d36e83246244e0aa7c6c7788c3a57cfdb7f77c7628a52023328"
EXPECTED[WSD_ANALYSIS_PATH] = "8ca0d8c8dd7e510a04daef6b3fbd78ace6d20b173e88d2a3d0c2e10fdaafe30b"
EXPECTED[WSD_DECISION_PATH] = "c8ed0b8acaaa415277c5f9bdbf982d075136b795b5d95fd8813d5a3010072dbb"
EXPECTED[HYPERLEX / "scripts/shadow/hyperlexical/model_based_wsd_candidate_v1.py"] = (
    "7f489772162dd0be249df3fe8c0a5476e69e5a4ca73fba7468f61c60cda84bad"
)
EXPECTED[HYPERLEX / "scripts/shadow/hyperlexical/model_based_wsd_candidate_v1_replay.py"] = (
    "5981978209da5884fe6cd6efbaf7593a37e1a40138a75aa70906694cee8b8a09"
)


def check_sealed(skip: set[Path] | None = None) -> None:
    skipped = skip or set()
    for path, expected in EXPECTED.items():
        if path in skipped:
            continue
        if not path.is_file() or sha256(path) != expected:
            refuse(f"sealed file changed: {path}")


def _digest(payload) -> str:
    text = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def attach_sense_key(item: dict, exceptions: dict, sense_index: dict) -> None:
    """Fill a unique PWN 3.0 sense key. The selected synset stays as frozen."""
    synset = item["selected_pwn30_synset"]
    if synset is None:
        return
    keys = sense_keys_for(synset, item["constituent_surface"], exceptions, sense_index)
    current = item["selected_sense_key_if_available"]
    if current is not None:
        if current not in keys:
            refuse(f"frozen sense key is not in the PWN 3.0 index for {synset}")
        return
    if len(keys) == 1:
        item["selected_sense_key_if_available"] = keys[0]


def build_integrated(resolver_rows: list[dict], model_rows: list[dict], exceptions: dict, sense_index: dict):
    model = {(row["parent_row_id"], row["constituent_index"]): row for row in model_rows}
    if len(model) != len(model_rows):
        refuse("duplicate model constituent keys")
    consumed = set()
    integrated = []
    by_parent = defaultdict(list)
    for row in resolver_rows:
        if row["constituent_index"] is None:
            continue
        key = (row["parent_row_id"], row["constituent_index"])
        model_row = model.get(key)
        if model_row is not None:
            consumed.add(key)
        item = integrate_constituent(row, model_row)
        attach_sense_key(item, exceptions, sense_index)
        item["candidate_count"] = len(row["candidate_synsets"])
        integrated.append(item)
        by_parent[row["parent_row_id"]].append(item)
    if consumed != set(model):
        refuse("a model row does not match a frozen lesk tie")
    for items in by_parent.values():
        items.sort(key=lambda item: item["constituent_index"])
    return integrated, by_parent


def project_manifest(sealed: list[dict], by_parent: dict) -> list[dict]:
    projected = []
    for row in sealed:
        items = by_parent.get(row["row_id"], [])
        tokens = [projection_token(item["resolution_tier"], item["resolution_status"]) for item in items]
        projected.append(
            {
                "constituent_statuses": tokens,
                "content_count": len(tokens),
                "parent_row_id": row["row_id"],
                "projected_status": row_projection(tokens),
            }
        )
    return projected


def projection_failure(projected: list[dict]) -> str | None:
    frozen = json.loads(PROJECTION_PATH.read_text(encoding="utf-8"))
    if frozen.get("operator_labels_included") is not False:
        return "READINESS_REPRODUCTION_FAILURE projection includes operator labels"
    frozen_rows = {row["parent_row_id"]: row for row in frozen["rows"]}
    if len(frozen_rows) != 225 or len(projected) != 225:
        return "READINESS_REPRODUCTION_FAILURE row count"
    for row in projected:
        prior = frozen_rows.get(row["parent_row_id"])
        if prior is None:
            return f"READINESS_REPRODUCTION_FAILURE missing {row['parent_row_id']}"
        if prior["constituent_statuses"] != row["constituent_statuses"] or prior["content_count"] != row["content_count"] or prior["projected_status"] != row["projected_status"]:
            return (
                f"READINESS_REPRODUCTION_FAILURE {row['parent_row_id']} "
                f"got {row['constituent_statuses']} {row['projected_status']} "
                f"expected {prior['constituent_statuses']} {prior['projected_status']}"
            )
    counts = Counter(row["projected_status"] for row in projected)
    if counts["RESIDUAL_READY"] != EXPECTED_READY or counts["UNKNOWN"] != EXPECTED_UNKNOWN:
        return "READINESS_REPRODUCTION_FAILURE totals"
    return None


def public_integrated(item: dict) -> dict:
    return {
        "constituent_index": item["constituent_index"],
        "constituent_pos": item["constituent_pos"],
        "constituent_surface": item["constituent_surface"],
        "parent_row_id": item["parent_row_id"],
        "parent_surface": item["parent_surface"],
        "parent_synset": item["parent_synset"],
        "resolution_provenance": item["resolution_provenance"],
        "resolution_status": item["resolution_status"],
        "resolution_tier": item["resolution_tier"],
        "selected_pwn30_synset": item["selected_pwn30_synset"],
        "selected_sense_key_if_available": item["selected_sense_key_if_available"],
    }


def constituent_representation(item: dict, by_id: dict, pointers: list, exceptions: dict) -> str:
    synset = item["selected_pwn30_synset"]
    record = by_id.get(synset)
    if record is None:
        refuse(f"selected synset is not in PWN 3.0: {synset}")
    if item["resolution_tier"] == TIER1_STRUCTURAL:
        pool = [
            lemma
            for symbol, target_word, target_id, lemma in pointers
            if target_id == synset and symbol in {"+", "\\"} and target_word > 0 and lemma
        ]
    else:
        pool = list(record["lemmas"])
    lemma = select_lemma(pool, item["constituent_surface"], exceptions)
    return representation_text(lemma, record["pos"], record["gloss"])


def prepare_jobs(sealed: list[dict], by_parent: dict, by_id: dict, exceptions: dict, model_index: dict):
    jobs = []
    unknown = []
    for row in sealed:
        items = by_parent.get(row["row_id"], [])
        tokens = [projection_token(item["resolution_tier"], item["resolution_status"]) for item in items]
        readiness = row_projection(tokens)
        if readiness != "RESIDUAL_READY":
            statuses = []
            for item in items:
                if item["resolution_status"] in {EXACT, RESOLVED}:
                    statuses.append(RESOLVED if item["resolution_status"] == RESOLVED else EXACT)
                else:
                    statuses.append(item["resolution_status"])
            unknown.append(
                {
                    "abstention_reason": abstention_reason(statuses),
                    "readiness": readiness,
                    "row_id": row["row_id"],
                }
            )
            continue
        parent = f"{row['synset_pos']}:{row['synset_offset']}"
        pointers = pointer_records(parent, by_id)
        parts = [constituent_representation(item, by_id, pointers, exceptions) for item in items]
        whole = representation_text(row["surface"], row["pos"], row["gloss"])
        confidences = []
        margins = []
        for item in items:
            if item["resolution_tier"] != TIER3_GLOSSBERT:
                continue
            model_row = model_index[(row["row_id"], item["constituent_index"])]
            confidences.append(Decimal(model_row["model_confidence"]))
            margins.append(Decimal(model_row["model_margin"]))
        jobs.append(
            {
                "constituent_representation_texts": parts,
                "content_constituents": [item["constituent_surface"] for item in items],
                "max_candidate_senses": max(item["candidate_count"] for item in items),
                "min_glossbert_confidence": format(min(confidences), "f") if confidences else None,
                "min_glossbert_margin": format(min(margins), "f") if margins else None,
                "pos": row["pos"],
                "readiness": readiness,
                "resolved_constituent_synsets": [item["selected_pwn30_synset"] for item in items],
                "row_id": row["row_id"],
                "surface": row["surface"],
                "synset": parent,
                "tiers": [item["resolution_tier"] for item in items],
                "whole_representation_text": whole,
            }
        )
    return jobs, unknown


def score_jobs(jobs: list[dict], vectors: dict[str, list[float]], integrated_sha: str) -> list[dict]:
    scored = []
    for job in jobs:
        whole = vectors[job["whole_representation_text"]]
        parts = [vectors[text] for text in job["constituent_representation_texts"]]
        result = residual_score(whole, parts)
        if result is None:
            refuse(f"residual formula returned no score for {job['row_id']}")
        residual, composed = result
        if len(whole) != OUTPUT_DIMENSION:
            refuse("encoder width drifted")
        scored.append(
            {
                "composed_vector_hash": vector_hash(composed),
                "constituent_representation_texts": list(job["constituent_representation_texts"]),
                "constituent_resolution_tiers": list(job["tiers"]),
                "constituent_vector_hashes": [vector_hash(part) for part in parts],
                "content_constituents": list(job["content_constituents"]),
                "integrated_resolution_sha256": integrated_sha,
                "pos": job["pos"],
                "residual_candidate_spec_sha256": RESIDUAL_SPEC_SHA,
                "residual_score": residual,
                "resolved_constituent_synsets": list(job["resolved_constituent_synsets"]),
                "row_id": job["row_id"],
                "score_status": "SCORED",
                "surface": job["surface"],
                "synset": job["synset"],
                "whole_representation_text": job["whole_representation_text"],
                "whole_vector_hash": vector_hash(whole),
            }
        )
    return scored


def identity_rows(jobs: list[dict], scored: list[dict], unknown: list[dict]) -> list[dict]:
    scored_by = {row["row_id"]: row for row in scored}
    rows = []
    for job in jobs:
        row = scored_by[job["row_id"]]
        rows.append(
            {
                "composed_vector_hash": row["composed_vector_hash"],
                "constituent_representation_texts": row["constituent_representation_texts"],
                "constituent_vector_hashes": row["constituent_vector_hashes"],
                "readiness": job["readiness"],
                "residual_score": row["residual_score"],
                "row_id": job["row_id"],
                "whole_representation_text": row["whole_representation_text"],
                "whole_vector_hash": row["whole_vector_hash"],
            }
        )
    for row in unknown:
        rows.append(
            {
                "composed_vector_hash": None,
                "constituent_representation_texts": None,
                "constituent_vector_hashes": None,
                "readiness": row["readiness"],
                "residual_score": None,
                "row_id": row["row_id"],
                "whole_representation_text": None,
                "whole_vector_hash": None,
            }
        )
    return sorted(rows, key=lambda row: row["row_id"])


def encode_needed(model, jobs: list[dict]) -> dict[str, list[float]]:
    needed = sorted({text for job in jobs for text in [job["whole_representation_text"], *job["constituent_representation_texts"]]})
    return encode_texts(model, needed)


def apply_overflow(model, jobs: list[dict]) -> tuple[list[dict], list[dict]]:
    kept = []
    overflow = []
    for job in jobs:
        texts = [job["whole_representation_text"], *job["constituent_representation_texts"]]
        if any(token_length(model, text) > MAX_SEQUENCE_LENGTH for text in texts):
            overflow.append({"abstention_reason": "representation_exceeds_max_sequence_length", "row_id": job["row_id"]})
            continue
        kept.append(job)
    return kept, overflow


def assemble_scores(sealed: list[dict], scored: list[dict], unknown: list[dict], overflow: list[dict]) -> list[dict]:
    scored_by = {row["row_id"]: row for row in scored}
    unknown_by = {row["row_id"]: row["abstention_reason"] for row in unknown}
    overflow_by = {row["row_id"]: row["abstention_reason"] for row in overflow}
    rows = []
    for row in sealed:
        if row["row_id"] in scored_by:
            rows.append(scored_by[row["row_id"]])
            continue
        reason = unknown_by.get(row["row_id"], overflow_by.get(row["row_id"]))
        if reason is None:
            refuse(f"row has no score and no abstention: {row['row_id']}")
        rows.append({"abstention_reason": reason, "row_id": row["row_id"], "score_status": "UNKNOWN"})
    return rows


def nuisance_for(job: dict) -> dict:
    return {
        "character_length": str(len(job["surface"])),
        "content_count": str(len(job["content_constituents"])),
        "max_candidate_senses": str(job["max_candidate_senses"]),
        "min_glossbert_confidence": job["min_glossbert_confidence"],
        "min_glossbert_margin": job["min_glossbert_margin"],
        "pos": job["pos"],
        "surface": job["surface"],
        "synset": job["synset"],
        "tiers": list(job["tiers"]),
        "token_count": str(len(job["surface"].split())),
        "uses_tier3": TIER3_GLOSSBERT in job["tiers"],
    }


def load_operator_buckets() -> dict[str, str]:
    manifest = json.loads(EVIDENCE_MANIFEST.read_text(encoding="utf-8"))
    if sha256(EVIDENCE_MANIFEST) != EXPECTED[EVIDENCE_MANIFEST]:
        refuse("manifest changed during scoring")
    buckets = {}
    for row in manifest["rows"]:
        buckets[row["row_id"]] = row["operator_bucket"]
        if row.get("sense_class") is not None:
            refuse("manifest sense class changed")
    counted = Counter(buckets.values())
    for name, expected_count in OPERATOR_COUNTS.items():
        if counted[name] != expected_count:
            refuse(f"operator count {name} is {counted[name]}")
    return buckets


def tier_counts(rows: list[dict]) -> dict:
    report = {}
    for bucket in ("HIGH", "SECONDARY"):
        chosen = [row for row in rows if row["bucket"] == bucket]
        report[f"{bucket.lower()}_with_tier3"] = sum(row["uses_tier3"] for row in chosen)
        report[f"{bucket.lower()}_without_tier3"] = sum(not row["uses_tier3"] for row in chosen)
    return report


def composition_counts(rows: list[dict]) -> dict:
    report = {}
    for bucket in ("HIGH", "SECONDARY", "REJECT"):
        counter = Counter(tuple(row["tiers"]) for row in rows if row["bucket"] == bucket)
        report[bucket] = {",".join(key): value for key, value in sorted(counter.items())}
    return report


def write_failure(status: str, transition: str, detail: str, hashes: dict | None = None) -> None:
    payload = {
        "candidate_status": status,
        "detail": detail,
        "emits_yes_no": False,
        "json_schema_document": None,
        "measurement_eligible": False,
        "measurement_sample_drawn": False,
        "next_legal_transition": transition,
        "next_transition_authorized": False,
        "residual_formula_count": 1,
        "runtime_integration": False,
        "select_005_authorized": False,
        "selected_source": "none",
        "semantic_noncompositionality_threshold": None,
        "state": "RESIDUAL_DEVELOPMENT_ANALYZED_V2",
        "threshold_eligible": False,
    }
    decision_sha = write_json(DECISION_PATH, payload)
    recorded = dict(hashes or {})
    recorded["decision_sha256"] = decision_sha
    update_tracker(payload, recorded)
    refuse(detail)


def update_tracker(decision: dict, hashes: dict) -> str:
    check_sealed(skip={TRACKER})
    tracker = json.loads(TRACKER.read_text(encoding="utf-8"))
    if sha256(TRACKER) != CURRENT_TRACKER:
        refuse("tracker hash drifted before update")
    if tracker.get("model_based_wsd_candidate_status") != "CANDIDATE_PROMISING":
        refuse("model WSD status drifted")
    if tracker.get("constituent_sense_resolution_candidate_status") != "COVERAGE_INSUFFICIENT":
        refuse("constituent resolver status drifted")
    if tracker.get("residual_evaluation_status") != "CANDIDATE_DISTRIBUTION_FROZEN":
        refuse("residual freeze status drifted")
    tracker["previous_state"] = tracker.get("state")
    tracker["previous_tracker_sha256"] = CURRENT_TRACKER
    tracker["state"] = "CANDIDATE_SOURCE_EVALUATED"
    tracker["residual_evaluation_status"] = "CANDIDATE_DISTRIBUTION_FROZEN"
    tracker["residual_model_resolved_state"] = decision["state"]
    tracker["residual_model_resolved_candidate_status"] = decision["candidate_status"]
    tracker["residual_model_resolved_threshold_eligible"] = False
    tracker["residual_model_resolved_integrated_sha256"] = hashes.get("integrated_sha256")
    tracker["residual_model_resolved_scores_sha256"] = hashes.get("scores_sha256")
    tracker["residual_model_resolved_receipt_sha256"] = hashes.get("receipt_sha256")
    tracker["residual_model_resolved_analysis_sha256"] = hashes.get("analysis_sha256")
    tracker["residual_model_resolved_confound_sha256"] = hashes.get("confound_sha256")
    tracker["residual_model_resolved_decision_sha256"] = hashes.get("decision_sha256")
    tracker["residual_threshold_eligible"] = False
    tracker["residual_threshold"] = None
    tracker["residual_yes_no_emitted"] = False
    tracker["selected_source"] = "none"
    tracker["semantic_evidence_source_selected"] = "none"
    tracker["semantic_evidence_source_runtime_integration"] = False
    tracker["measurement_sample_drawn"] = False
    tracker["measurement_eligible"] = False
    tracker["select_authorized"] = False
    tracker["authorized"] = False
    tracker["admitted"] = 0
    tracker["settled"] = 0
    tracker["gold"] = 0
    tracker["procedure_v3_created"] = False
    tracker["procedure_v2_retuned"] = False
    tracker["next_legal_transition"] = decision["next_legal_transition"]
    tracker["next_transition_authorized"] = False
    tracker_sha = write_json(TRACKER, tracker)
    check_sealed(skip={TRACKER})
    if sha256(EVENTS) != EXPECTED[EVENTS] or sha256(LEDGER_FILE) != EXPECTED[LEDGER_FILE]:
        refuse("ledger or events changed")
    if sha256(RESIDUAL_SPEC) != RESIDUAL_SPEC_SHA or sha256(RESIDUAL_SCORES) != RESIDUAL_SCORES_SHA:
        refuse("frozen residual artifact changed")
    return tracker_sha


def main() -> None:
    check_sealed()
    if sha256(RESIDUAL_SPEC) != RESIDUAL_SPEC_SHA or sha256(RESIDUAL_SCORES) != RESIDUAL_SCORES_SHA:
        refuse("frozen residual artifact changed")
    if MODEL_NAME != "sentence-transformers/all-MiniLM-L6-v2":
        refuse("residual model name drifted")
    if MODEL_REVISION != "1110a243fdf4706b3f48f1d95db1a4f5529b4d41":
        refuse("residual model revision drifted")
    if COMPOSITION_OPERATOR != "normalized_mean_v1" or DISTANCE_METRIC != "one_minus_cosine_v1":
        refuse("residual formula drifted")
    sealed = load_sealed_rows()
    resolver_rows = load_jsonl(RESOLVER_REPLAY_PATH)
    model_rows = load_jsonl(WSD_RESOLUTION_PATH)
    if any("operator_bucket" in row for row in resolver_rows) or any("operator_bucket" in row for row in model_rows):
        refuse("upstream resolution artifact contains an operator bucket")
    exceptions = load_exceptions(WORDNET)
    sense_index = load_sense_index(WORDNET / "index.sense")
    integrated, by_parent = build_integrated(resolver_rows, model_rows, exceptions, sense_index)
    if len(integrated) != 504:
        refuse(f"integrated constituent count is {len(integrated)}")
    projected = project_manifest(sealed, by_parent)
    failure = projection_failure(projected)
    if failure:
        refuse(failure)
    public_rows = [public_integrated(item) for item in integrated]
    integrated_sha = write_jsonl(INTEGRATED_PATH, public_rows)
    if sha256(INTEGRATED_PATH) != integrated_sha:
        refuse("integrated hash drifted at freeze")
    print(f"INTEGRATED_FROZEN {integrated_sha}", file=sys.stderr, flush=True)
    by_id, _index = build_indexes()
    model_index = {(row["parent_row_id"], row["constituent_index"]): row for row in model_rows}
    jobs, unknown = prepare_jobs(sealed, by_parent, by_id, exceptions, model_index)
    if len(jobs) + len(unknown) != 225:
        refuse("prepared row count drifted")
    if len(jobs) != EXPECTED_READY or len(unknown) != EXPECTED_UNKNOWN:
        refuse("READINESS_REPRODUCTION_FAILURE")
    encoder = load_encoder()
    kept, overflow = apply_overflow(encoder, jobs)
    first_vectors = encode_needed(encoder, kept)
    second_vectors = encode_needed(encoder, kept)
    first_scored = score_jobs(kept, first_vectors, integrated_sha)
    second_scored = score_jobs(kept, second_vectors, integrated_sha)
    if identity_rows(kept, first_scored, unknown) != identity_rows(kept, second_scored, unknown):
        write_failure(
            "NOT_DETERMINISTIC",
            "RESIDUAL_REPLAY_DETERMINISM_REVIEW_AUTHORIZATION",
            "NOT_DETERMINISTIC",
            {"integrated_sha256": integrated_sha},
        )
    scores = assemble_scores(sealed, first_scored, unknown, overflow)
    if len(scores) != 225:
        refuse("score row count drifted")
    if any("operator_bucket" in row or row.get("score_status") not in {"SCORED", "UNKNOWN"} for row in scores):
        refuse("score row is malformed")
    if any(row.get("semantic_noncompositional") is not None for row in scores):
        refuse("score row emits a semantic decision")
    score_sha = write_jsonl(SCORES_PATH, scores)
    if sha256(SCORES_PATH) != score_sha:
        refuse("score hash drifted at freeze")
    print(f"SCORES_FROZEN {score_sha}", file=sys.stderr, flush=True)
    receipt = {
        "analysis_plan": analysis_plan(),
        "authorization": AUTHORIZATION,
        "composition_operator": COMPOSITION_OPERATOR,
        "determinism": "IDENTICAL",
        "distance_metric": DISTANCE_METRIC,
        "integrated_resolution_sha256": integrated_sha,
        "json_schema_document": None,
        "model_name": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "model_settings": {
            "batch_size": 1,
            "device": "cpu",
            "dtype": "float32",
            "eval_mode": True,
            "max_sequence_length": MAX_SEQUENCE_LENGTH,
            "normalize_embeddings": True,
            "seed": 0,
            "threads": 1,
        },
        "operator_labels_joined": False,
        "original_residual_score_sha256": RESIDUAL_SCORES_SHA,
        "overflow_count": len(overflow),
        "readiness_unknown_count": EXPECTED_UNKNOWN,
        "ready_count": EXPECTED_READY,
        "residual_candidate_spec_sha256": RESIDUAL_SPEC_SHA,
        "residual_formula": "1 - cosine_similarity(whole_sense_vector, normalized_mean(constituent_sense_vectors))",
        "residual_formula_count": 1,
        "scored_count": len(first_scored),
        "scores_sha256": score_sha,
        "sequence": [
            "integrated_resolution_hashed",
            "residual_scores_hashed",
            "operator_labels_not_yet_joined",
        ],
        "stored_precision": "10 decimal places",
        "yes_no_emitted": False,
    }
    receipt_sha = write_json(RECEIPT_PATH, receipt)
    if receipt["operator_labels_joined"] is not False:
        refuse("receipt joined labels early")
    buckets = load_operator_buckets()
    joined = []
    job_by = {job["row_id"]: job for job in jobs}
    score_by = {row["row_id"]: row for row in first_scored}
    for row_id, score in score_by.items():
        job = job_by[row_id]
        meta = nuisance_for(job)
        joined.append(
            {
                "bucket": buckets[row_id],
                "residual_score": score["residual_score"],
                "row_id": row_id,
                **meta,
            }
        )
    ready_joined = []
    for job in jobs:
        meta = nuisance_for(job)
        ready_joined.append({"bucket": buckets[job["row_id"]], "row_id": job["row_id"], **meta})
    ready_by = Counter(row["bucket"] for row in ready_joined)
    if ready_by["HIGH"] != 28 or ready_by["SECONDARY"] != 11 or ready_by["REJECT"] != 34 or ready_by["QUARANTINE"] != 0:
        write_failure(
            "NOT_COMPUTABLE",
            "RESIDUAL_REPLAY_READINESS_REVIEW_AUTHORIZATION",
            "READINESS_REPRODUCTION_FAILURE",
        )
    high = [row["residual_score"] for row in joined if row["bucket"] == "HIGH"]
    secondary = [row["residual_score"] for row in joined if row["bucket"] == "SECONDARY"]
    reject = [row["residual_score"] for row in joined if row["bucket"] == "REJECT"]
    comparison = pair_comparison(high, secondary)
    direction = direction_result(comparison)
    intervals = bootstrap_intervals(high, secondary)
    confounds = confound_report(joined)
    decision = replay_decision(
        readiness_reproduced=True,
        determinism="IDENTICAL",
        direction=direction,
        tier3_concentrated=confounds["tier3"]["concentrated"],
        extremes=confounds["extreme_driven"],
        pos_split=confounds["pos_partitioned"],
    )
    analysis = {
        "bootstrap": intervals,
        "comparison": comparison,
        "direction": direction,
        "high": full_distribution(high),
        "hypothesis": "HIGH residual > SECONDARY residual",
        "integrated_resolution_sha256": integrated_sha,
        "json_schema_document": None,
        "outliers": {
            "HIGH": outlier_pair(joined, "HIGH"),
            "REJECT": outlier_pair(joined, "REJECT"),
            "SECONDARY": outlier_pair(joined, "SECONDARY"),
        },
        "ready_by_operator": {name: ready_by[name] for name in OPERATORS},
        "receipt_sha256": receipt_sha,
        "reject": full_distribution(reject),
        "scores_sha256": score_sha,
        "secondary": full_distribution(secondary),
        "threshold_eligible": False,
        "yes_no_emitted": False,
    }
    analysis_sha = write_json(ANALYSIS_PATH, analysis)
    confound_payload = {
        "composition": composition_counts(joined),
        "confounds": confounds,
        "integrated_resolution_sha256": integrated_sha,
        "json_schema_document": None,
        "ready_tier3_counts": tier_counts(ready_joined),
        "receipt_sha256": receipt_sha,
        "scores_sha256": score_sha,
        "token_definition": "whitespace_separated_surface_tokens",
    }
    confound_sha = write_json(CONFOUND_PATH, confound_payload)
    decision_payload = {
        "analysis_sha256": analysis_sha,
        "candidate_status": decision["candidate_status"],
        "confound_sha256": confound_sha,
        "determinism": "IDENTICAL",
        "direction": direction,
        "emits_yes_no": False,
        "integrated_resolution_sha256": integrated_sha,
        "json_schema_document": None,
        "measurement_eligible": False,
        "measurement_sample_drawn": False,
        "next_legal_transition": decision["next_legal_transition"],
        "next_transition_authorized": False,
        "original_residual_score_sha256": RESIDUAL_SCORES_SHA,
        "receipt_sha256": receipt_sha,
        "residual_candidate_spec_sha256": RESIDUAL_SPEC_SHA,
        "residual_formula_count": 1,
        "runtime_integration": False,
        "scores_sha256": score_sha,
        "select_005_authorized": False,
        "selected_source": "none",
        "semantic_noncompositionality_threshold": None,
        "state": decision["state"],
        "threshold_eligible": False,
    }
    decision_sha = write_json(DECISION_PATH, decision_payload)
    hashes = {
        "analysis_sha256": analysis_sha,
        "confound_sha256": confound_sha,
        "decision_sha256": decision_sha,
        "integrated_sha256": integrated_sha,
        "receipt_sha256": receipt_sha,
        "scores_sha256": score_sha,
    }
    tracker_sha = update_tracker(decision_payload, hashes)
    print(
        json.dumps(
            {
                "analysis_sha256": analysis_sha,
                "candidate_status": decision["candidate_status"],
                "confound_sha256": confound_sha,
                "decision_sha256": decision_sha,
                "direction": direction,
                "integrated_sha256": integrated_sha,
                "receipt_sha256": receipt_sha,
                "scores_sha256": score_sha,
                "tracker_sha256": tracker_sha,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
