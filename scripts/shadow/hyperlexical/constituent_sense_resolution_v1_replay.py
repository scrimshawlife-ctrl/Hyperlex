"""Review residual-v1 coverage, then resolve constituent senses on the 225 rows.

The resolver specification is written before any constituent is resolved. Operator
labels are read only after the resolution artifact is hashed. Residual scores are
not recomputed.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from hyperlexical.constituent_sense_resolution_v1 import (
    RELATION_EXPANSION_SYMBOLS,
    RULE_VERSION,
    coverage_decision,
    lesk_tokens,
    overlap_score,
    resolve_constituent_sense,
    resolver_policy,
    row_resolution_status,
    structural_synset_ids,
)
from hyperlexical.km_candidate_evaluation import lookup_key
from hyperlexical.semantic_compositionality_residual import (
    exact_synset_ids,
    extract_constituents,
    lexical_synset_ids,
    neighbor_keys,
    resolve_constituent,
)
from hyperlexical.semantic_compositionality_residual_replay import EXPECTED as RESIDUAL_EXPECTED
from hyperlexical.unbind_sense_screen_v1 import load_exceptions, load_wordnet, parse_data_line

LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
HYPERLEX = Path("/home/morpheus/Hyperlex")
SENSE = LEDGER / "operator-review/HLX-EVAL-UNBIND-SENSE-SCREEN-V1-HYPOTHESIS-001"
SOURCE = LEDGER / "operator-review/HLX-EVAL-UNBIND-SEMANTIC-EVIDENCE-SOURCE-V1-001"
WORDNET = LEDGER / "acquisition/sources/wordnet-3.0/wordnet"
TRACKER = SENSE / "HYPOTHESIS.json"
EVIDENCE_MANIFEST = SENSE / "DEVELOPMENT_EVIDENCE.json"
EVENTS = LEDGER / "events.jsonl"
LEDGER_FILE = LEDGER / "ledger.json"

REVIEW_PATH = SOURCE / "RESIDUAL_V1_DEVELOPMENT_RESULT_REVIEW.json"
LIMITATION_PATH = SOURCE / "SEMANTIC_RESIDUAL_V1_COVERAGE_LIMITATION.json"
SPEC_PATH = SOURCE / "CONSTITUENT_SENSE_RESOLUTION_V1_SPEC.json"
PROCEDURE_PATH = SOURCE / "CONSTITUENT_SENSE_RESOLUTION_V1_PROCEDURE.json"
REPLAY_PATH = SOURCE / "CONSTITUENT_SENSE_RESOLUTION_V1_REPLAY.jsonl"
ANALYSIS_PATH = SOURCE / "CONSTITUENT_SENSE_RESOLUTION_V1_DEVELOPMENT_ANALYSIS.json"
DECISION_PATH = SOURCE / "CONSTITUENT_SENSE_RESOLUTION_V1_DECISION.json"

RESIDUAL_SPEC = SOURCE / "RESIDUAL_CANDIDATE_SPEC.json"
RESIDUAL_PROVENANCE = SOURCE / "RESIDUAL_SOURCE_PROVENANCE.json"
RESIDUAL_SCORES = SOURCE / "RESIDUAL_DEVELOPMENT_SCORES.jsonl"
RESIDUAL_EVALUATION = SOURCE / "RESIDUAL_DEVELOPMENT_EVALUATION.json"
RESIDUAL_DECISION = SOURCE / "RESIDUAL_CANDIDATE_DECISION.json"
RESIDUAL_LICENSE = SOURCE / "RESIDUAL_LICENSE_RECEIPT.json"

OPERATORS = ("HIGH", "SECONDARY", "REJECT", "QUARANTINE", "UNRESOLVED")
OPERATOR_COUNTS = {"HIGH": 101, "SECONDARY": 46, "REJECT": 77, "QUARANTINE": 1, "UNRESOLVED": 0}
POS_NAME = {"n": "noun", "v": "verb", "a": "adj", "r": "adv", "s": "adj"}
FILES = {"noun": "data.noun", "verb": "data.verb", "adj": "data.adj", "adv": "data.adv"}
BASELINE_COUNTS = {"AMBIGUOUS": 370, "EXACT": 4, "UNIQUE": 60, "UNRESOLVED": 70}
ROW_FIELDS = ("row_id", "surface", "pos", "gloss", "synset_offset", "synset_pos", "sense_class")

EXPECTED = dict(RESIDUAL_EXPECTED)
EXPECTED.update(
    {
        TRACKER: "14d4daaab1e4740a596acaef7f4dbd9ed11edaf2182ff22f7aa339325febf591",
        RESIDUAL_SPEC: "39c2914e32557ffe1a456a56f8742ea4fe8f1aaec1dc1da451656cd22f0db32d",
        RESIDUAL_PROVENANCE: "2c34a7d0d480cde564bda694dbaa349550814c5fb7c647bfa3bbbc9db5e26886",
        RESIDUAL_SCORES: "cea638679faeee1bc1c689823e7c0c08562c4d7ef1f8230bbbf4079239e7c3e7",
        RESIDUAL_EVALUATION: "ba782622d4c68d23c53ae0ffb5f54f1e43c8cf059b44b7adb34e0eb356ef3896",
        RESIDUAL_DECISION: "45922eba294b0b7d7238ce71c6157641259ea292f65743ba2ee1324ff9b52617",
        RESIDUAL_LICENSE: "323a5bad21ac74d6a1fd94c54dba95a0046b633cd7328dd6680972525abc0909",
        HYPERLEX / "scripts/shadow/hyperlexical/semantic_compositionality_residual.py": "795b433413e86f05ea91186cfa85a68915f18bc6515e70a5ce5cfa6e1b8847d8",
        HYPERLEX / "scripts/shadow/hyperlexical/semantic_compositionality_residual_replay.py": "36091d4cde5d7580d66ca2f9d8c2a568c996d10cef5d294ba1ed736505ff21ee",
        HYPERLEX / "tests/shadow/test_semantic_compositionality_residual.py": "13df0dab6867f9adcf94605df7da5e779696f5e140ae1386c3d0b6600de6c07f",
    }
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def refuse(message: str) -> None:
    raise SystemExit(message)


def write_json(path: Path, payload: dict) -> str:
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_jsonl(path: Path, rows: list[dict]) -> str:
    text = "".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def check_sealed(skip: set[Path] | None = None) -> None:
    skipped = skip or set()
    for path, expected in EXPECTED.items():
        if path in skipped:
            continue
        if not path.is_file() or sha256(path) != expected:
            refuse(f"sealed file changed: {path}")


def load_sealed_rows() -> list[dict]:
    manifest = json.loads(EVIDENCE_MANIFEST.read_text(encoding="utf-8"))
    if len(manifest["rows"]) != 225:
        refuse("manifest row count drifted")
    sealed = []
    for row in manifest["rows"]:
        if row.get("sense_class") is not None:
            refuse("development row has a sense class")
        if row.get("pos") != row.get("synset_pos"):
            refuse("row POS and synset POS differ")
        sealed.append({field: row[field] for field in ROW_FIELDS})
    return sealed


def build_catalog() -> tuple[dict, dict]:
    synsets, first_glosses = load_wordnet(WORDNET)
    full = {}
    for pos, name in FILES.items():
        for line in (WORDNET / name).read_text(encoding="utf-8", errors="replace").splitlines():
            parsed = parse_data_line(line)
            if parsed is None:
                continue
            synset, _first = parsed
            full[(pos, synset.offset)] = " ".join(line.partition("|")[2].split())
    by_id = {}
    index = defaultdict(list)
    for (pos, offset), synset in synsets.items():
        if pos not in FILES:
            continue
        synset_id = f"{pos}:{offset}"
        if synset_id in by_id:
            continue
        if (pos, offset) not in full:
            refuse(f"missing gloss {synset_id}")
        by_id[synset_id] = {
            "gloss_first": " ".join(first_glosses[(pos, offset)].split()),
            "gloss_full": full[(pos, offset)],
            "lemmas": list(synset.lemmas),
            "pointers": list(synset.pointers),
            "pos": pos,
            "synset_id": synset_id,
        }
        for lemma in synset.lemmas:
            index[lookup_key(lemma)].append(synset_id)
    for key, identifiers in index.items():
        index[key] = sorted(set(identifiers))
    return by_id, dict(index)


def pointer_tuples(record: dict | None, by_id: dict) -> list[tuple[str, int, str, str]]:
    if record is None:
        return []
    rows = []
    for pointer in record["pointers"]:
        pos = POS_NAME.get(pointer.pos)
        target_id = f"{pos}:{pointer.offset}" if pos else f"unknown:{pointer.offset}"
        target = by_id.get(target_id)
        if target is None or pointer.target < 1 or pointer.target > len(target["lemmas"]):
            lemma = ""
        else:
            lemma = target["lemmas"][pointer.target - 1]
        rows.append((pointer.symbol, pointer.target, target_id, lemma))
    return rows


def related_clauses(record: dict, by_id: dict) -> list[str]:
    found = []
    seen = set()
    ordered = sorted(
        record["pointers"],
        key=lambda pointer: (pointer.symbol, pointer.pos, pointer.offset, pointer.source, pointer.target),
    )
    for pointer in ordered:
        if pointer.symbol not in RELATION_EXPANSION_SYMBOLS:
            continue
        pos = POS_NAME.get(pointer.pos)
        if pos is None:
            continue
        target_id = f"{pos}:{pointer.offset}"
        if target_id in seen or target_id == record["synset_id"]:
            continue
        target = by_id.get(target_id)
        if target is None:
            continue
        seen.add(target_id)
        found.append(target["gloss_first"])
    return found


def candidate_tokens(record: dict, by_id: dict) -> list[str]:
    tokens = lesk_tokens(record["gloss_full"])
    for clause in related_clauses(record, by_id):
        tokens.extend(lesk_tokens(clause))
    return tokens


def lemma_supported(record: dict, constituent: str, exceptions: dict[str, set[str]]) -> bool:
    keys = neighbor_keys(constituent, exceptions)
    return any(lookup_key(lemma) in keys for lemma in record["lemmas"])


def resolve_once(rows: list[dict], by_id: dict, index: dict, exceptions: dict[str, set[str]], spec_sha: str, procedure_sha: str) -> list[dict]:
    records = []
    for row in rows:
        parent_synset = f"{row['synset_pos']}:{row['synset_offset']}"
        parent = by_id.get(parent_synset)
        pointers = pointer_tuples(parent, by_id)
        extraction = extract_constituents(row["surface"])
        content = extraction["content_constituents"]
        if not content:
            records.append(
                {
                    "baseline_resolution_status": None,
                    "candidate_glosses": [],
                    "candidate_synsets": [],
                    "constituent_index": None,
                    "constituent_pos": None,
                    "constituent_surface": None,
                    "margin": None,
                    "parent_row_id": row["row_id"],
                    "parent_surface": row["surface"],
                    "parent_synset": parent_synset,
                    "primary_evidence_code": "fewer_than_two_content_constituents",
                    "procedure_sha256": procedure_sha,
                    "resolution_method": "NONE",
                    "resolution_status": None,
                    "row_resolution_status": "UNKNOWN",
                    "second_score": None,
                    "selected_synset": None,
                    "spec_sha256": spec_sha,
                    "supporting_evidence": [],
                    "top_score": None,
                }
            )
            continue
        prepared = []
        for index_in_row, constituent in enumerate(content):
            structural = structural_synset_ids(pointers, constituent, exceptions)
            lexical = lexical_synset_ids(index, constituent, exceptions)
            baseline = resolve_constituent(
                exact_synset_ids(pointers, constituent, exceptions),
                lexical,
            )
            prepared.append(
                {
                    "baseline": baseline,
                    "constituent": constituent,
                    "lexical": lexical,
                    "structural": structural,
                }
            )
        exact_gloss = {}
        for index_in_row, item in enumerate(prepared):
            structural = list(dict.fromkeys(item["structural"]))
            lexical = list(dict.fromkeys(item["lexical"]))
            selected = structural[0] if len(structural) == 1 else lexical[0] if not structural and len(lexical) == 1 else None
            if selected is None:
                continue
            record = by_id.get(selected)
            if record is None or not lemma_supported(record, item["constituent"], exceptions):
                refuse(f"structural selection is not a constituent lemma: {selected}")
            exact_gloss[index_in_row] = record["gloss_first"]
        statuses = []
        emitted = []
        for index_in_row, item in enumerate(prepared):
            structural = list(dict.fromkeys(item["structural"]))
            lexical = list(dict.fromkeys(item["lexical"]))
            lesk_scores = None
            support_extra = []
            if not structural and len(lexical) > 1:
                others = [exact_gloss[other] for other in range(len(prepared)) if other != index_in_row and other in exact_gloss]
                context = lesk_tokens(row["gloss"])
                for clause in others:
                    context.extend(lesk_tokens(clause))
                lesk_scores = []
                for synset_id in lexical:
                    candidate = by_id.get(synset_id)
                    if candidate is None:
                        refuse(f"missing candidate synset {synset_id}")
                    if not lemma_supported(candidate, item["constituent"], exceptions):
                        refuse(f"candidate does not match constituent {synset_id}")
                    lesk_scores.append((synset_id, overlap_score(context, candidate_tokens(candidate, by_id))))
                support_extra.append(f"context_tokens:{len(context)}")
            decision = resolve_constituent_sense(structural, lexical, lesk_scores)
            if decision["selected_synset"] is not None:
                chosen = by_id.get(decision["selected_synset"])
                if chosen is None or not lemma_supported(chosen, item["constituent"], exceptions):
                    refuse(f"selected synset fails the lemma check: {decision['selected_synset']}")
            candidates = sorted(set(structural) | set(lexical))
            glosses = []
            for synset_id in candidates:
                candidate = by_id.get(synset_id)
                if candidate is None:
                    refuse(f"missing candidate gloss {synset_id}")
                glosses.append(candidate["gloss_full"])
            poses = {synset_id.split(":", 1)[0] for synset_id in candidates}
            if decision["selected_synset"]:
                pos = decision["selected_synset"].split(":", 1)[0]
            elif len(poses) == 1:
                pos = next(iter(poses))
            else:
                pos = None
            statuses.append(decision["resolution_status"])
            support = list(decision["supporting_evidence"]) + support_extra
            emitted.append(
                {
                    "baseline_resolution_status": item["baseline"],
                    "candidate_glosses": glosses,
                    "candidate_synsets": candidates,
                    "constituent_index": index_in_row,
                    "constituent_pos": pos,
                    "constituent_surface": item["constituent"],
                    "margin": decision["margin"],
                    "parent_row_id": row["row_id"],
                    "parent_surface": row["surface"],
                    "parent_synset": parent_synset,
                    "primary_evidence_code": decision["primary_evidence_code"],
                    "procedure_sha256": procedure_sha,
                    "resolution_method": decision["resolution_method"],
                    "resolution_status": decision["resolution_status"],
                    "second_score": decision["second_score"],
                    "selected_synset": decision["selected_synset"],
                    "spec_sha256": spec_sha,
                    "supporting_evidence": support,
                    "top_score": decision["top_score"],
                }
            )
        status = row_resolution_status(len(content), statuses)
        for item in emitted:
            item["row_resolution_status"] = status
            records.append(item)
    return records


def fraction(numerator: int, denominator: int) -> str:
    return f"{numerator}/{denominator}"


def main() -> None:
    check_sealed()
    evaluation = json.loads(RESIDUAL_EVALUATION.read_text(encoding="utf-8"))
    if evaluation["scored_count"] != 3 or evaluation["unknown_count"] != 222:
        refuse("frozen residual evaluation counts drifted")
    if evaluation["high_comparison"] != "NOT_COMPUTABLE":
        refuse("frozen HIGH comparison drifted")
    if evaluation["semantic_noncompositionality_threshold"] is not None or evaluation["emits_yes_no"] is not False:
        refuse("frozen residual evaluation carries a threshold or a yes/no claim")
    observed = {
        "ambiguous_content_rows": 145,
        "fewer_than_two_content_tokens": 59,
        "scored_HIGH": 0,
        "scored_REJECT": 3,
        "scored_SECONDARY": 0,
        "scored_rows": 3,
        "unknown_rows": 222,
        "unresolved_content_rows": 18,
    }
    if evaluation["abstention_reason_counts"] != {
        "ambiguous_content_constituent": 145,
        "fewer_than_two_content_constituents": 59,
        "unresolved_content_constituent": 18,
    }:
        refuse("frozen abstention counts drifted")
    limitation = {
        "conclusion": {
            "primary_limitation": "constituent_sense_resolution",
            "source_selection_eligible": False,
            "threshold_eligible": False,
        },
        "finding": "SEMANTIC_RESIDUAL_V1_COVERAGE_LIMITATION_CONFIRMED",
        "interpretation": "The dominant blocker for semantic-compositionality residual evaluation is deterministic constituent sense resolution, not the residual model itself.",
        "json_schema_document": None,
        "observed": observed,
        "residual_candidate_decision_sha256": EXPECTED[RESIDUAL_DECISION],
        "residual_candidate_spec_sha256": EXPECTED[RESIDUAL_SPEC],
        "residual_development_evaluation_sha256": EXPECTED[RESIDUAL_EVALUATION],
        "residual_development_scores_sha256": EXPECTED[RESIDUAL_SCORES],
        "residual_model_name": "sentence-transformers/all-MiniLM-L6-v2",
        "residual_model_revision": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
        "residual_source_provenance_sha256": EXPECTED[RESIDUAL_PROVENANCE],
        "residual_state": "CANDIDATE_DISTRIBUTION_FROZEN",
        "schema": "hyperlex.semantic_residual_v1_coverage_limitation.v1",
        "threshold_authorization": "RESIDUAL_THRESHOLD_FREEZE_AUTHORIZATION",
        "threshold_authorization_granted": False,
    }
    limitation_sha = write_json(LIMITATION_PATH, limitation)
    review = {
        "authorized_transition": "RESIDUAL_DEVELOPMENT_RESULT_REVIEW",
        "coverage_limitation": "CONFIRMED",
        "coverage_limitation_sha256": limitation_sha,
        "finding": "SEMANTIC_RESIDUAL_V1_COVERAGE_LIMITATION_CONFIRMED",
        "json_schema_document": None,
        "next_research_track": RULE_VERSION,
        "next_research_track_state_at_review": "SPEC_FROZEN",
        "residual_artifacts_modified": False,
        "residual_state": "CANDIDATE_DISTRIBUTION_FROZEN",
        "schema": "hyperlex.residual_v1_development_result_review.v1",
        "selected_source": "none",
        "source_selection_eligible": False,
        "threshold_authorization_granted": False,
        "threshold_eligible": False,
    }
    review_sha = write_json(REVIEW_PATH, review)
    policy = resolver_policy()
    spec = {
        "coverage_limitation_sha256": limitation_sha,
        "development_result_review_sha256": review_sha,
        "json_schema_document": None,
        "policy": policy,
        "residual_model_unchanged": {
            "composition": "normalized_mean_v1",
            "distance": "one_minus_cosine_v1",
            "model_name": "sentence-transformers/all-MiniLM-L6-v2",
            "model_revision": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
        },
        "residual_replay_authorized": False,
        "residual_scores_included": False,
        "schema": "hyperlex.constituent_sense_resolution_v1_spec.v1",
        "selected_source": "none",
    }
    spec_text = json.dumps(spec, sort_keys=True)
    if "operator_bucket" in spec_text or "0.2139784896" in spec_text:
        refuse("resolver spec contains a label or a residual score")
    spec_sha = write_json(SPEC_PATH, spec)
    procedure = {
        "json_schema_document": None,
        "policy": policy,
        "rule": RULE_VERSION,
        "schema": "hyperlex.constituent_sense_resolution_v1_procedure.v1",
        "spec_sha256": spec_sha,
    }
    procedure_sha = write_json(PROCEDURE_PATH, procedure)
    rows = load_sealed_rows()
    exceptions = load_exceptions(WORDNET)
    first_catalog = build_catalog()
    second_catalog = build_catalog()
    first = resolve_once(rows, first_catalog[0], first_catalog[1], exceptions, spec_sha, procedure_sha)
    second = resolve_once(rows, second_catalog[0], second_catalog[1], exceptions, spec_sha, procedure_sha)
    first_text = "".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in first)
    second_text = "".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in second)
    if first_text != second_text:
        refuse("NOT_DETERMINISTIC")
    baseline_counts = Counter(
        row["baseline_resolution_status"] for row in first if row["constituent_index"] is not None
    )
    for name, expected_count in BASELINE_COUNTS.items():
        if baseline_counts[name] != expected_count:
            refuse(f"baseline {name} is {baseline_counts[name]}")
    if any("operator_bucket" in row for row in first):
        refuse("resolution row carries an operator bucket")
    replay_sha = write_jsonl(REPLAY_PATH, first)
    if sha256(SPEC_PATH) != spec_sha or sha256(PROCEDURE_PATH) != procedure_sha:
        refuse("resolution mutated the frozen spec")

    rejoined = json.loads(EVIDENCE_MANIFEST.read_text(encoding="utf-8"))
    if sha256(EVIDENCE_MANIFEST) != EXPECTED[EVIDENCE_MANIFEST]:
        refuse("manifest changed during resolution")
    buckets = {row["row_id"]: row["operator_bucket"] for row in rejoined["rows"]}
    counted = Counter(buckets.values())
    for name, expected_count in OPERATOR_COUNTS.items():
        if counted[name] != expected_count:
            refuse(f"operator count {name} is {counted[name]}")
    attempts = [row for row in first if row["constituent_index"] is not None]
    status_counts = Counter(row["resolution_status"] for row in attempts)
    method_counts = Counter(row["resolution_method"] for row in attempts)
    code_counts = Counter(row["primary_evidence_code"] for row in attempts)
    baseline_ambiguous_rows = [row for row in attempts if row["baseline_resolution_status"] == "AMBIGUOUS"]
    not_resolved = sum(row["resolution_status"] in {"AMBIGUOUS", "UNRESOLVED"} for row in baseline_ambiguous_rows)
    lesk_attempts = [row for row in attempts if row["resolution_method"] == "EXTENDED_LESK_V1"]
    ties = sum(row["primary_evidence_code"] == "extended_lesk_tie" for row in lesk_attempts)
    row_status = {}
    for row in first:
        row_status[row["parent_row_id"]] = row["row_resolution_status"]
    if len(row_status) != 225:
        refuse("row status does not cover 225 rows")
    ready_by_operator = {name: {"RESIDUAL_READY": 0, "UNKNOWN": 0} for name in OPERATORS}
    for row_id, status in row_status.items():
        ready_by_operator[buckets[row_id]][status] += 1
    ready_total = sum(item["RESIDUAL_READY"] for item in ready_by_operator.values())
    unknown_total = sum(item["UNKNOWN"] for item in ready_by_operator.values())
    outcome = coverage_decision(
        baseline_ambiguous=BASELINE_COUNTS["AMBIGUOUS"],
        baseline_ambiguous_not_resolved=not_resolved,
        residual_ready_high=ready_by_operator["HIGH"]["RESIDUAL_READY"],
        residual_ready_secondary=ready_by_operator["SECONDARY"]["RESIDUAL_READY"],
    )
    attempt_count = len(attempts)
    analysis = {
        "abstention_rate_fraction": fraction(status_counts["AMBIGUOUS"] + status_counts["UNRESOLVED"], attempt_count),
        "baseline_ambiguous_not_resolved": not_resolved,
        "baseline_counts": {name: BASELINE_COUNTS[name] for name in ("EXACT", "UNIQUE", "AMBIGUOUS", "UNRESOLVED")},
        "candidate_status": outcome["candidate_status"],
        "change_versus_residual_v1": {
            "baseline_AMBIGUOUS": BASELINE_COUNTS["AMBIGUOUS"],
            "baseline_EXACT": BASELINE_COUNTS["EXACT"],
            "baseline_UNIQUE": BASELINE_COUNTS["UNIQUE"],
            "baseline_UNRESOLVED": BASELINE_COUNTS["UNRESOLVED"],
            "new_AMBIGUOUS": status_counts["AMBIGUOUS"],
            "new_EXACT": status_counts["EXACT"],
            "new_RESOLVED": status_counts["RESOLVED"],
            "new_UNRESOLVED": status_counts["UNRESOLVED"],
        },
        "coverage_finding": outcome["coverage_finding"],
        "coverage_limitation_sha256": limitation_sha,
        "determinism": "IDENTICAL",
        "development_result_review_sha256": review_sha,
        "exact_fraction": fraction(status_counts["EXACT"], attempt_count),
        "high_residual_ready": ready_by_operator["HIGH"]["RESIDUAL_READY"],
        "high_unknown": ready_by_operator["HIGH"]["UNKNOWN"],
        "json_schema_document": None,
        "method_counts": dict(sorted(method_counts.items())),
        "necessary_condition_met": outcome["necessary_condition_met"],
        "operator_labels_joined_after_resolution_artifact_was_hashed": True,
        "operator_labels_used_during_resolution": False,
        "primary_evidence_code_counts": dict(sorted(code_counts.items())),
        "procedure_sha256": procedure_sha,
        "projection": {
            "REJECT_rows": ready_by_operator["REJECT"]["RESIDUAL_READY"],
            "HIGH_rows": ready_by_operator["HIGH"]["RESIDUAL_READY"],
            "QUARANTINE_rows": ready_by_operator["QUARANTINE"]["RESIDUAL_READY"],
            "SECONDARY_rows": ready_by_operator["SECONDARY"]["RESIDUAL_READY"],
            "residual_replay_candidate_rows": ready_total,
            "residual_replay_performed": False,
        },
        "quarantine_residual_ready": ready_by_operator["QUARANTINE"]["RESIDUAL_READY"],
        "quarantine_unknown": ready_by_operator["QUARANTINE"]["UNKNOWN"],
        "reject_residual_ready": ready_by_operator["REJECT"]["RESIDUAL_READY"],
        "reject_unknown": ready_by_operator["REJECT"]["UNKNOWN"],
        "replay_sha256": replay_sha,
        "residual_ready_by_operator": ready_by_operator,
        "residual_ready_rows": ready_total,
        "residual_scores_recomputed": False,
        "resolution_counts": {
            "AMBIGUOUS": status_counts["AMBIGUOUS"],
            "EXACT": status_counts["EXACT"],
            "RESOLVED": status_counts["RESOLVED"],
            "UNRESOLVED": status_counts["UNRESOLVED"],
        },
        "resolved_fraction": fraction(status_counts["RESOLVED"], attempt_count),
        "row_count": 225,
        "rule": RULE_VERSION,
        "schema": "hyperlex.constituent_sense_resolution_v1_development_analysis.v1",
        "secondary_residual_ready": ready_by_operator["SECONDARY"]["RESIDUAL_READY"],
        "secondary_unknown": ready_by_operator["SECONDARY"]["UNKNOWN"],
        "selected_source": "none",
        "semantic_noncompositionality_threshold": None,
        "spec_sha256": spec_sha,
        "tie_rate_fraction": fraction(ties, len(lesk_attempts)) if lesk_attempts else "0/0",
        "total_constituent_attempts": attempt_count,
        "unknown_rows": unknown_total,
        "unresolved_rate_fraction": fraction(status_counts["UNRESOLVED"], attempt_count),
        "yes_no_emitted": False,
    }
    analysis_sha = write_json(ANALYSIS_PATH, analysis)
    decision = {
        "analysis_sha256": analysis_sha,
        "candidate_status": outcome["candidate_status"],
        "coverage_finding": outcome["coverage_finding"],
        "coverage_limitation_sha256": limitation_sha,
        "development_result_review_sha256": review_sha,
        "encoded": True,
        "high_residual_ready": ready_by_operator["HIGH"]["RESIDUAL_READY"],
        "json_schema_document": None,
        "measurement_eligible": False,
        "measurement_sample_drawn": False,
        "necessary_condition_met": outcome["necessary_condition_met"],
        "next_legal_transition": outcome["next_legal_transition"],
        "next_transition_authorized": False,
        "procedure_sha256": procedure_sha,
        "replay_sha256": replay_sha,
        "residual_replay_performed": False,
        "residual_state": "CANDIDATE_DISTRIBUTION_FROZEN",
        "residual_threshold_created": False,
        "rule": RULE_VERSION,
        "runtime_integration": False,
        "schema": "hyperlex.constituent_sense_resolution_v1_decision.v1",
        "secondary_residual_ready": ready_by_operator["SECONDARY"]["RESIDUAL_READY"],
        "select_005_authorized": False,
        "selected_source": "none",
        "spec_sha256": spec_sha,
        "state": "DEVELOPMENT_ANALYZED",
        "threshold_eligible": False,
    }
    decision_sha = write_json(DECISION_PATH, decision)
    check_sealed(skip={TRACKER})
    tracker = json.loads(TRACKER.read_text(encoding="utf-8"))
    tracker["previous_state"] = tracker.get("state")
    tracker["previous_tracker_sha256"] = EXPECTED[TRACKER]
    tracker["state"] = "CANDIDATE_SOURCE_EVALUATED"
    tracker["residual_evaluation_status"] = "CANDIDATE_DISTRIBUTION_FROZEN"
    tracker["residual_coverage_limitation"] = "CONFIRMED"
    tracker["residual_threshold_eligible"] = False
    tracker["residual_source_selection_eligible"] = False
    tracker["residual_threshold"] = None
    tracker["residual_yes_no_emitted"] = False
    tracker["residual_development_result_review_sha256"] = review_sha
    tracker["residual_coverage_limitation_sha256"] = limitation_sha
    tracker["constituent_sense_resolution_rule"] = RULE_VERSION
    tracker["constituent_sense_resolution_state"] = "DEVELOPMENT_ANALYZED"
    tracker["constituent_sense_resolution_candidate_status"] = outcome["candidate_status"]
    tracker["constituent_sense_resolution_coverage_finding"] = outcome["coverage_finding"]
    tracker["constituent_sense_resolution_encoded"] = True
    tracker["constituent_sense_resolution_runtime_applied"] = False
    tracker["constituent_sense_resolution_spec_sha256"] = spec_sha
    tracker["constituent_sense_resolution_procedure_sha256"] = procedure_sha
    tracker["constituent_sense_resolution_replay_sha256"] = replay_sha
    tracker["constituent_sense_resolution_analysis_sha256"] = analysis_sha
    tracker["constituent_sense_resolution_decision_sha256"] = decision_sha
    tracker["constituent_sense_resolution_residual_ready_rows"] = ready_total
    tracker["constituent_sense_resolution_high_ready"] = ready_by_operator["HIGH"]["RESIDUAL_READY"]
    tracker["constituent_sense_resolution_secondary_ready"] = ready_by_operator["SECONDARY"]["RESIDUAL_READY"]
    tracker["selected_source"] = "none"
    tracker["semantic_evidence_source_selected"] = "none"
    tracker["semantic_evidence_source_runtime_integration"] = False
    tracker["semantic_evidence_source_applied"] = False
    tracker["semantic_evidence_source_encoded"] = False
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
    print(
        json.dumps(
            {
                "analysis_sha256": analysis_sha,
                "candidate_status": outcome["candidate_status"],
                "coverage_finding": outcome["coverage_finding"],
                "coverage_limitation_sha256": limitation_sha,
                "decision_sha256": decision_sha,
                "determinism": "IDENTICAL",
                "high_residual_ready": ready_by_operator["HIGH"]["RESIDUAL_READY"],
                "high_unknown": ready_by_operator["HIGH"]["UNKNOWN"],
                "method_counts": analysis["method_counts"],
                "necessary_condition_met": outcome["necessary_condition_met"],
                "next_legal_transition": outcome["next_legal_transition"],
                "procedure_sha256": procedure_sha,
                "projection": analysis["projection"],
                "reject_residual_ready": ready_by_operator["REJECT"]["RESIDUAL_READY"],
                "replay_sha256": replay_sha,
                "residual_ready_rows": ready_total,
                "resolution_counts": analysis["resolution_counts"],
                "review_sha256": review_sha,
                "secondary_residual_ready": ready_by_operator["SECONDARY"]["RESIDUAL_READY"],
                "secondary_unknown": ready_by_operator["SECONDARY"]["UNKNOWN"],
                "spec_sha256": spec_sha,
                "tie_rate_fraction": analysis["tie_rate_fraction"],
                "total_constituent_attempts": attempt_count,
                "tracker_sha256": tracker_sha,
                "unknown_rows": unknown_total,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
