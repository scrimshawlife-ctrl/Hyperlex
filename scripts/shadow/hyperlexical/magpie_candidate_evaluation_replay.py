"""Evaluate the pinned MAGPIE author corpus on the 225 development rows.

This is candidate-source evidence research. It does not select MAGPIE,
integrate it, draw a measurement sample, or authorize SELECT-005.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from hyperlexical.magpie_candidate_evaluation import build_index, evaluate_row

LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
HYPERLEX = Path("/home/morpheus/Hyperlex")
SENSE = LEDGER / "operator-review/HLX-EVAL-UNBIND-SENSE-SCREEN-V1-HYPOTHESIS-001"
SOURCE = LEDGER / "operator-review/HLX-EVAL-UNBIND-SEMANTIC-EVIDENCE-SOURCE-V1-001"
MAGPIE = (
    LEDGER
    / "acquisition/sources/magpie-corpus/7fa677b82b9a772dfa54bbdd0fb414412d73db3b"
)
COMMIT = "7fa677b82b9a772dfa54bbdd0fb414412d73db3b"
UNFILTERED = MAGPIE / "MAGPIE_unfiltered.jsonl"
LICENSE = MAGPIE / "LICENSE"
README = MAGPIE / "README.md"
TRACKER = SENSE / "HYPOTHESIS.json"
EVIDENCE_MANIFEST = SENSE / "DEVELOPMENT_EVIDENCE.json"
EVENTS = LEDGER / "events.jsonl"
LEDGER_FILE = LEDGER / "ledger.json"

PROVENANCE_PATH = SOURCE / "MAGPIE_SOURCE_PROVENANCE.json"
LICENSE_PATH = SOURCE / "MAGPIE_LICENSE_RECEIPT.json"
MATCHES_PATH = SOURCE / "MAGPIE_DEVELOPMENT_MATCHES.jsonl"
ALIGNMENT_PATH = SOURCE / "MAGPIE_SENSE_ALIGNMENT.jsonl"
SEMANTIC_PATH = SOURCE / "MAGPIE_SEMANTIC_EVIDENCE.jsonl"
EVALUATION_PATH = SOURCE / "MAGPIE_DEVELOPMENT_EVALUATION.json"
DECISION_PATH = SOURCE / "MAGPIE_CANDIDATE_DECISION.json"

EXPECTED = {
    SENSE / "CLASSIFICATION_PROCEDURE.json": "4d9dad77d8d315e810863101041229c53570ed16970074c86abaecd0cc3012ad",
    SENSE / "CLASSIFICATION_PROCEDURE.v2.json": "3f4071640d0c9f29cf56f53969a88ec25c635444b87765e77e1b9158470e5662",
    SENSE / "ACCEPTANCE.json": "cff6af0f05ec5e12fb29ddfd2ec321addc94c73258c31860345f6d49960065b0",
    SENSE / "HYPOTHESIS.draft.json": "93375446b1f4a1f70c60f747a56b626ae667c8944d0eea54deddb9d57d3d9e38",
    EVIDENCE_MANIFEST: "0e9b3c1af9dd573bf6e2034640e468e8ab9074e1e76c90cef1f39f68d607bc03",
    SENSE / "development_replay_predictions.jsonl": "69ea6b8714f3cb6105222d636af3f17bd5c5caac7b290c3c3d87e4efaeedd0ef",
    SENSE / "development_replay_report.json": "38ada8bc32d8b19361cc974346d5972f6020eb0c32c2ca537abff4d17f66c7f0",
    SENSE / "development_replay_v2_predictions.jsonl": "1f7fc03547d24de851326a4848d93f1dbef16714e74e3e9f86d8c8aa6f8aaa8a",
    SENSE / "development_replay_v2_report.json": "93d8fb76da8aa7155fb0ce57b0841ca455eca3e904edf50b9f76e595dd095ca5",
    SENSE / "LEXEME_STRUCTURE_SCREEN.architecture.json": "529defbc2b56152c3290d5b09f309764128b035906797229dab54857cd249df0",
    SENSE / "LINEAGE_RETIREMENT.json": "fd5d9ebb94d7a6e6ea69609c4e2125ec9914f6705ae256b780223bbea2e26f6f",
    SENSE / "PROCEDURE_V1_ERROR_ANALYSIS.json": "471bc27b89f550fae36b3471daaad282a6dd8735414846cb18aafe1195e0a52e",
    SENSE / "PROCEDURE_V1_TO_V2_CHANGE_NOTE.json": "443ce2964d4e4fcd8257055cb1404965faa70b838264b1f623be192d1cae085c",
    SENSE / "V2_DEVELOPMENT_RESULT_REVIEW.json": "77ae2c0491def0b75cd4213cc23fdcb6f2eec18dc2d0641764a276a583ee537d",
    SENSE / "WORDNET_STRUCTURAL_SOURCE_LIMITATION.json": "3c05cd9d6301fab0791e31b542d767cc757307cf3e304065362b479cc40e964a",
    SOURCE / "HYPOTHESIS.json": "39127a810d38ede96d7947c33dbc3e5491c9e1cc9b3f76b1064d9e0dd04a7787",
    SOURCE / "ACCEPTANCE.json": "1252c8c20ce3f49fe61ed8aeeec3157df7f4185b3aa7c468938ff47342d81b94",
    SOURCE / "CANDIDATE_SOURCE_EVALUATION_PLAN.json": "472b3819c050bbc9b1dd2eec3183cdb27c3659521408c321acb12b9c1b69dc8a",
    SOURCE / "SEMANTIC_COMPOSITIONALITY.architecture.json": "180b6721c4e19847516364f441ecc2101ed9a7758643889673dfdb7be6f41d36",
    LEDGER / "operator-review/HLX-EVAL-UNBIND-SCREEN-V7-001/unbind_screen_v7/measurement_error_analysis.json": "ebc56d4d4499efee19bc368365b0d6d3a7afc27ede4e78f40fb9d0fd15fcb9c8",
    EVENTS: "96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c",
    LEDGER_FILE: "77e22433203879b252f7a9e309d2013d7550101d1c4a014b494d2c96df87d0e0",
    TRACKER: "521eccb8bd068d4697a3ffdc06e3b44feb4eec3c8a3bd6aebcea11dd288b7dfc",
    HYPERLEX / "scripts/shadow/hyperlexical/unbind_sense_screen_v1.py": "531b58422e6f18b42276c6dde36493c7d0f8841556785b4b8911017879f93ad0",
    HYPERLEX / "scripts/shadow/hyperlexical/unbind_sense_screen_v2.py": "4b6f125da435b365af143c187902093bee5c9502db5b813a3d2bba11f889fa2b",
    HYPERLEX / "scripts/shadow/hyperlexical/unbind_screen_v3.py": "179d8dcc112214c70566bd3c9a0397e1ebab9131666b0ca1f2a3817973aaccc6",
    HYPERLEX / "scripts/shadow/hyperlexical/unbind_screen_v4.py": "f1e86e2f21544655cda6a136885a186b20885d501cb7ea9c75e18b3dd4a42377",
    HYPERLEX / "scripts/shadow/hyperlexical/unbind_screen_v5.py": "70504574523f2e8fde0fb974e3027205dded2c96213dd997f44475ea6856f948",
    HYPERLEX / "scripts/shadow/hyperlexical/unbind_screen_v6.py": "59699496c15aaedfbe69a7e49b5c6e62d1e543ce5a1e0e9a0255a98a62036fba",
    HYPERLEX / "scripts/shadow/hyperlexical/unbind_screen_v7.py": "73335bde8eec262ebecfedfc0d0ecb0a965da5c6b66e53c16f2aee2f38b061ab",
    UNFILTERED: "541ee535e93d71eff85351351665115e2a9f22ad736423881da5774a93bc880e",
    LICENSE: "05ab88f3f9da1d05f9c5bf0a7c45c49a9007f877dd9c237a5bf668276fe04c3b",
    README: "bc9d281e2348a780b91929e44de0e58bc26a822d69835b0e6dd8a666754af6db",
}
BLOB = {
    UNFILTERED: "24a6ef5cc6b226859956a903395caddb81c09493",
    LICENSE: "56902ed9fa665f4aeebdb8cc3df5743a6de02542",
    README: "f20506c021aa1484ea3ece67dedde20c202bbf53",
}
EXPECTED_INSTANCES = 56622
EXPECTED_TYPES = 1756
EXPECTED_LABELS = {"?": 7, "i": 40011, "l": 16168, "o": 436}
OPERATORS = ("HIGH", "SECONDARY", "REJECT", "QUARANTINE", "UNRESOLVED")
SEMANTIC_STATES = ("YES", "NO", "UNKNOWN")
SURFACE_STATES = ("EXACT", "NORMALIZED", "VARIANT", "NONE", "AMBIGUOUS")
ALIGNMENTS = ("ALIGNED_IDIOMATIC", "ALIGNED_LITERAL", "MIXED", "CONFLICT", "UNKNOWN")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def refuse(message: str) -> None:
    raise SystemExit(message)


def iso_mtime(path: Path) -> str:
    stamp = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    return stamp.strftime("%Y-%m-%dT%H:%M:%SZ")


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


def fraction(numerator: int, denominator: int) -> str:
    return f"{numerator}/{denominator}"


def load_instances(path: Path) -> tuple[list[dict], Counter]:
    rows = []
    labels: Counter[str] = Counter()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            instance = json.loads(line, parse_float=Decimal)
            rows.append(instance)
            labels[str(instance.get("label"))] += 1
    return rows, labels


def license_established(text: str) -> bool:
    if "Attribution 4.0 International" not in text:
        return False
    if "NonCommercial" in text or "Non-Commercial" in text:
        return False
    return True


def project_match(row: dict, found: dict) -> dict:
    return {
        "ambiguous_candidates": found["ambiguous_candidates"],
        "annotation_confidence": found["annotation_confidence"],
        "idiomatic_instance_count": found["idiomatic_instance_count"],
        "literal_instance_count": found["literal_instance_count"],
        "matched_magpie_expression": found["matched_magpie_expression"],
        "pos": row["pos"],
        "row_id": row["row_id"],
        "schema": "hyperlex.magpie_development_match_row.v1",
        "source_instance_ids": found["source_instance_ids"],
        "source_name": "MAGPIE",
        "surface": row["surface"],
        "surface_match": found["surface_match"],
        "synset": found["synset"],
        "unresolved_instance_count": found["unresolved_instance_count"],
        "variant_types": found["variant_types"],
    }


def project_alignment(row: dict, found: dict) -> dict:
    return {
        "alignment_basis": found["alignment_basis"],
        "gloss_used": False,
        "json_schema_document": None,
        "matched_magpie_expression": found["matched_magpie_expression"],
        "operator_label_used": False,
        "pos": row["pos"],
        "row_id": row["row_id"],
        "schema": "hyperlex.magpie_sense_alignment_row.v1",
        "sense_alignment": found["sense_alignment"],
        "sense_alignment_rule": "identifier_equality_only",
        "surface": row["surface"],
        "surface_match": found["surface_match"],
        "synset": found["synset"],
    }


def project_evidence(row: dict, found: dict, provenance: dict) -> dict:
    return {
        "idiomatic_instance_count": found["idiomatic_instance_count"],
        "json_schema_document": None,
        "literal_instance_count": found["literal_instance_count"],
        "matched_magpie_expression": found["matched_magpie_expression"],
        "pos": row["pos"],
        "primary_evidence_code": found["primary_evidence_code"],
        "provenance": provenance,
        "row_id": row["row_id"],
        "schema": "hyperlex.magpie_semantic_evidence_row.v1",
        "semantic_noncompositional": found["semantic_noncompositional"],
        "sense_alignment": found["sense_alignment"],
        "source_artifact_hash": found["source_artifact_hash"],
        "source_instance_ids": found["source_instance_ids"],
        "source_name": "MAGPIE",
        "source_version": found["source_version"],
        "surface": row["surface"],
        "surface_match": found["surface_match"],
        "synset": found["synset"],
        "unresolved_instance_count": found["unresolved_instance_count"],
    }


def candidate_status(yes_count: int, yes_aligned: int) -> str:
    if yes_count == 0:
        return "CANDIDATE_INSUFFICIENT"
    if yes_aligned != yes_count:
        return "CANDIDATE_REJECTED"
    return "CANDIDATE_PROMISING"


def main() -> None:
    for path, expected in EXPECTED.items():
        if sha256(path) != expected:
            refuse(f"sealed artifact changed before evaluation: {path}")
    for path, expected in BLOB.items():
        if git_blob_sha1(path) != expected:
            refuse(f"git blob does not match hslh/magpie-corpus: {path.name}")
    license_text = LICENSE.read_text(encoding="utf-8")
    established = license_established(license_text)
    when = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    artifact_hash = EXPECTED[UNFILTERED]
    publication_pdf_sha = "8247c926909772ce317d5f33cddb83caa51969eb5ef928bcbadbbcf05e39c979"
    provenance = {
        "acquisition_timestamp_utc": {
            "LICENSE": iso_mtime(LICENSE),
            "MAGPIE_unfiltered.jsonl": iso_mtime(UNFILTERED),
            "README.md": iso_mtime(README),
        },
        "acquisition_urls": {
            "LICENSE": f"https://raw.githubusercontent.com/hslh/magpie-corpus/{COMMIT}/LICENSE",
            "MAGPIE_unfiltered.jsonl": f"https://raw.githubusercontent.com/hslh/magpie-corpus/{COMMIT}/MAGPIE_unfiltered.jsonl",
            "README.md": f"https://raw.githubusercontent.com/hslh/magpie-corpus/{COMMIT}/README.md",
        },
        "artifact_filenames": ["LICENSE", "MAGPIE_unfiltered.jsonl", "README.md"],
        "artifact_hashes_sha256": {
            "LICENSE": EXPECTED[LICENSE],
            "MAGPIE_unfiltered.jsonl": artifact_hash,
            "README.md": EXPECTED[README],
        },
        "canonical_source_repository": "https://github.com/hslh/magpie-corpus",
        "dataset_variant": "author corpus, MAGPIE_unfiltered.jsonl",
        "filtered_splits_acquired": False,
        "filtered_splits_not_used": {
            "MAGPIE_filtered_split_random.jsonl": {
                "acquired": False,
                "git_blob_sha1": "59c24bffbccb38d912930d761abc0e8d7846e128",
                "sha256": None,
            },
            "MAGPIE_filtered_split_typebased.jsonl": {
                "acquired": False,
                "git_blob_sha1": "722546a2df509b5f50556445fdabb13179019b85",
                "sha256": None,
            },
        },
        "git_blob_sha1": {path.name: digest for path, digest in BLOB.items()},
        "hugging_face_package_used": False,
        "publication": {
            "anthology_url": "https://aclanthology.org/2020.lrec-1.35/",
            "authors": ["Hessel Haagsma", "Johan Bos", "Malvina Nissim"],
            "pdf_sha256": publication_pdf_sha,
            "pdf_url": "https://aclanthology.org/2020.lrec-1.35.pdf",
            "title": "MAGPIE: A Large Corpus of Potentially Idiomatic Expressions",
            "venue": "LREC 2020",
        },
        "repository_full_name": "hslh/magpie-corpus",
        "schema": "hyperlex.magpie_source_provenance.v1",
        "source_name": "MAGPIE — A Large Corpus of Potentially Idiomatic Expressions",
        "unrelated_magpie_repository_used": False,
        "version_or_commit": COMMIT,
        "version_recorded_at": "2020-06-07T09:57:12Z",
    }
    receipt = {
        "code_license": "CC-BY-4.0",
        "code_license_note": "The pinned commit has one LICENSE file and no separate software license.",
        "dataset_artifact_license": "CC-BY-4.0" if established else "SOURCE_LICENSE_UNRESOLVED",
        "dataset_license_basis": "LICENSE file in hslh/magpie-corpus at the pinned commit, corroborated by the GitHub license API SPDX CC-BY-4.0. The jsonl itself has no license field.",
        "evaluated_artifact": "MAGPIE_unfiltered.jsonl",
        "hugging_face_dataset_card_consulted": False,
        "json_schema_document": None,
        "license_status": "ESTABLISHED" if established else "SOURCE_LICENSE_UNRESOLVED",
        "publication_license": "CC-BY-NC",
        "publication_license_basis": "Page 1 of the anthology PDF states that the ELRA proceedings text is licensed under CC-BY-NC. That statement is not the dataset license.",
        "publication_pdf_sha256": publication_pdf_sha,
        "schema": "hyperlex.magpie_license_receipt.v1",
        "source_name": "MAGPIE",
        "source_version": COMMIT,
    }
    if not established:
        provenance_sha = write_json(PROVENANCE_PATH, provenance)
        receipt_sha = write_json(LICENSE_PATH, receipt)
        decision = {
            "candidate": "MAGPIE",
            "evaluation_status": "SOURCE_LICENSE_UNRESOLVED",
            "license_receipt_sha256": receipt_sha,
            "runtime_integration": False,
            "schema": "hyperlex.magpie_candidate_decision.v1",
            "selected_source": "none",
            "source_provenance_sha256": provenance_sha,
        }
        write_json(DECISION_PATH, decision)
        refuse("SOURCE_LICENSE_UNRESOLVED")

    instances, labels = load_instances(UNFILTERED)
    if labels != Counter(EXPECTED_LABELS):
        refuse(f"label census does not match the pinned corpus: {dict(labels)}")
    index = build_index(instances)
    if index.instance_count != EXPECTED_INSTANCES or index.type_count != EXPECTED_TYPES:
        refuse("instance or type count does not match the pinned corpus")
    if index.records_bound_sense:
        refuse("pinned corpus unexpectedly carries a sense identifier")
    manifest = json.loads(EVIDENCE_MANIFEST.read_text(encoding="utf-8"))
    rows = manifest["rows"]
    if len(rows) != 225:
        refuse("development manifest is not 225 rows")
    if any(row.get("sense_class") is not None for row in rows):
        refuse("development manifest already has a sense class")
    if manifest.get("sense_classes_assigned") is not False:
        refuse("development manifest sense_classes_assigned flag changed")

    row_provenance = {
        "alignment_basis_field": "alignment_basis",
        "artifact": "MAGPIE_unfiltered.jsonl",
        "artifact_sha256": artifact_hash,
        "commit": COMMIT,
        "gloss_used": False,
        "operator_label_used": False,
        "repository": "https://github.com/hslh/magpie-corpus",
        "sense_alignment_rule": "identifier_equality_only",
        "surface_match_assigns_semantic_yes": False,
        "variant_type_is_not_an_alternate_expression": True,
    }
    matches = []
    alignments = []
    semantic_rows = []
    for row in rows:
        synset = f"{row['synset_pos']}:{row['synset_offset']}"
        found = evaluate_row(row["surface"], synset, index, COMMIT, artifact_hash)
        found["synset"] = synset
        item_provenance = dict(row_provenance)
        item_provenance["alignment_basis"] = found["alignment_basis"]
        matches.append(project_match(row, found))
        alignments.append(project_alignment(row, found))
        semantic_rows.append(project_evidence(row, found, item_provenance))

    provenance["evaluated_at"] = when
    provenance["instance_count"] = index.instance_count
    provenance["label_counts"] = dict(sorted(labels.items()))
    provenance["records_bound_sense_identifier"] = False
    provenance["type_count"] = index.type_count
    provenance["variant_match_available"] = False
    provenance_sha = write_json(PROVENANCE_PATH, provenance)
    receipt_sha = write_json(LICENSE_PATH, receipt)
    matches_sha = write_jsonl(MATCHES_PATH, matches)
    alignment_sha = write_jsonl(ALIGNMENT_PATH, alignments)
    semantic_sha = write_jsonl(SEMANTIC_PATH, semantic_rows)

    frozen_semantic = [
        json.loads(line)
        for line in SEMANTIC_PATH.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if [row["row_id"] for row in frozen_semantic] != [row["row_id"] for row in rows]:
        refuse("semantic evidence row order drifted")
    if any("operator_bucket" in row for row in frozen_semantic):
        refuse("operator label entered the semantic evidence")

    by_operator = {name: Counter() for name in OPERATORS}
    semantic_counts = Counter()
    surface_counts = Counter()
    alignment_counts = Counter()
    code_counts = Counter()
    false_yes = []
    false_no = []
    mixed_usage_rows = []
    mixed_expressions = set()
    sense_conflict_rows = []
    for manifest_row, evidence_row in zip(rows, frozen_semantic):
        operator = manifest_row["operator_bucket"]
        semantic = evidence_row["semantic_noncompositional"]
        if operator not in by_operator:
            refuse(f"unexpected operator bucket: {operator}")
        by_operator[operator][semantic] += 1
        semantic_counts[semantic] += 1
        surface_counts[evidence_row["surface_match"]] += 1
        alignment_counts[evidence_row["sense_alignment"]] += 1
        code_counts[evidence_row["primary_evidence_code"]] += 1
        if semantic == "YES" and operator != "HIGH":
            false_yes.append(evidence_row["row_id"])
        if semantic == "NO" and operator == "HIGH":
            false_no.append(evidence_row["row_id"])
        literal = evidence_row["literal_instance_count"]
        idiomatic = evidence_row["idiomatic_instance_count"]
        if literal and idiomatic:
            mixed_usage_rows.append(evidence_row["row_id"])
            mixed_expressions.add(evidence_row["matched_magpie_expression"])
        if evidence_row["sense_alignment"] == "CONFLICT":
            sense_conflict_rows.append(evidence_row["row_id"])

    yes_count = semantic_counts["YES"]
    no_count = semantic_counts["NO"]
    unknown_count = semantic_counts["UNKNOWN"]
    yes_aligned = sum(
        1
        for row in frozen_semantic
        if row["semantic_noncompositional"] == "YES" and row["sense_alignment"] == "ALIGNED_IDIOMATIC"
    )
    covered = surface_counts["EXACT"] + surface_counts["NORMALIZED"] + surface_counts["VARIANT"]
    sense_covered = sum(alignment_counts[name] for name in ALIGNMENTS if name != "UNKNOWN")
    status = candidate_status(yes_count, yes_aligned)
    mapping_assumptions = {
        "false_no": "A semantic NO whose operator bucket is HIGH. This is a descriptive disagreement under an explicit proxy. Operator HIGH is not gold semantic YES.",
        "false_yes": "A semantic YES whose operator bucket is not HIGH. This is a descriptive disagreement under an explicit proxy. It is not computed by treating REJECT as compositional.",
        "no_precision": "Among semantic NO rows, the fraction whose operator bucket is SECONDARY. SECONDARY is not defined as compositional NO.",
        "operator_reject": "Operator REJECT is reported as its own row in the joint table. It is not mapped to semantic YES or NO.",
        "yes_precision": "Among semantic YES rows, the fraction whose operator bucket is HIGH. Operator HIGH is not defined as semantic noncompositionality.",
    }
    evaluation = {
        "abstention_count": unknown_count,
        "abstention_rate_fraction": fraction(unknown_count, 225),
        "candidate": "MAGPIE",
        "coverage_is_not_success": True,
        "development_manifest_sha256": EXPECTED[EVIDENCE_MANIFEST],
        "development_rows": 225,
        "diagnostics_are_descriptive": True,
        "evidence_code_counts": dict(sorted(code_counts.items())),
        "false_no_count": len(false_no),
        "false_no_row_ids": false_no,
        "false_yes_count": len(false_yes),
        "false_yes_row_ids": false_yes,
        "high_unknown_rate_is_acceptable": True,
        "json_schema_document": None,
        "mapping_assumptions": mapping_assumptions,
        "mixed_usage_expression_count": len(mixed_expressions),
        "mixed_usage_is_not_sense_alignment_mixed": True,
        "mixed_usage_row_count": len(mixed_usage_rows),
        "no_precision": "NOT_COMPUTABLE" if no_count == 0 else fraction(by_operator["SECONDARY"]["NO"], no_count),
        "no_support": no_count,
        "operator_by_semantic": {
            name: {state: by_operator[name][state] for state in SEMANTIC_STATES}
            for name in OPERATORS
        },
        "operator_labels_joined_after_semantic_evidence_was_written": True,
        "operator_labels_used_as_runtime_evidence": False,
        "schema": "hyperlex.magpie_development_evaluation.v1",
        "selected_source": "none",
        "semantic_evidence_sha256": semantic_sha,
        "sense_alignment_counts": {name: alignment_counts[name] for name in ALIGNMENTS},
        "sense_alignment_coverage_count": sense_covered,
        "sense_alignment_coverage_fraction": fraction(sense_covered, 225),
        "sense_conflict_count": len(sense_conflict_rows),
        "source_artifact_hash": artifact_hash,
        "source_version": COMMIT,
        "surface_ambiguous_count": surface_counts["AMBIGUOUS"],
        "surface_coverage_count": covered,
        "surface_coverage_excludes_ambiguous": True,
        "surface_coverage_fraction": fraction(covered, 225),
        "surface_match_counts": {name: surface_counts[name] for name in SURFACE_STATES},
        "surface_none_count": surface_counts["NONE"],
        "unknown_support": unknown_count,
        "yes_precision": "NOT_COMPUTABLE" if yes_count == 0 else fraction(by_operator["HIGH"]["YES"], yes_count),
        "yes_support": yes_count,
        "yes_support_with_aligned_idiomatic": yes_aligned,
    }
    evaluation_sha = write_json(EVALUATION_PATH, evaluation)
    decision = {
        "candidate": "MAGPIE",
        "candidate_family": "C_curated_linguistic_resource",
        "coverage_was_not_treated_as_success": True,
        "evaluation_sha256": evaluation_sha,
        "evaluation_status": status,
        "json_schema_document": None,
        "license_receipt_sha256": receipt_sha,
        "measurement_eligible": False,
        "measurement_sample_drawn": False,
        "next_legal_transition": "NEXT_CANDIDATE_SOURCE_EVALUATION_AUTHORIZATION",
        "next_transition_authorized": False,
        "not_selected_reason": "Semantic YES support is zero. MAGPIE annotates idiomatic and literal uses of a potentially idiomatic expression. The pinned unfiltered artifact has no WordNet synset, sense key, or gloss, so the supplied Hyperlex sense cannot be identified by equality. Surface coverage is not sense alignment.",
        "readiness_question_met": False,
        "recommended_next_candidate": "A later authorization may name one curated resource whose entries carry a WordNet synset offset or sense key for the expression sense. PARSEME, STREUSLE, PIE, EPIE, and NCS were not downloaded and are not selected.",
        "runtime_integration": False,
        "schema": "hyperlex.magpie_candidate_decision.v1",
        "select_005_authorized": False,
        "selected_source": "none",
        "sense_alignment_sha256": alignment_sha,
        "source_provenance_sha256": provenance_sha,
        "source_version": COMMIT,
        "state": "CANDIDATE_SOURCE_EVALUATED",
    }
    decision_sha = write_json(DECISION_PATH, decision)

    if sha256(EVIDENCE_MANIFEST) != EXPECTED[EVIDENCE_MANIFEST]:
        refuse("evaluation wrote into the development manifest")
    reloaded = json.loads(EVIDENCE_MANIFEST.read_text(encoding="utf-8"))
    if any(row.get("sense_class") is not None for row in reloaded["rows"]):
        refuse("evaluation wrote a sense class")
    for path, expected in EXPECTED.items():
        if path == TRACKER:
            continue
        if sha256(path) != expected:
            refuse(f"evaluation mutated {path}")

    tracker = json.loads(TRACKER.read_text(encoding="utf-8"))
    tracker["previous_state"] = "SEMANTIC_EVIDENCE_SOURCE_SPEC_FROZEN"
    tracker["previous_tracker_sha256"] = EXPECTED[TRACKER]
    tracker["state"] = "CANDIDATE_SOURCE_EVALUATED"
    tracker["semantic_evidence_source_state"] = "CANDIDATE_SOURCE_EVALUATED"
    tracker["semantic_evidence_source_candidate"] = "MAGPIE"
    tracker["semantic_evidence_source_evaluation_status"] = status
    tracker["semantic_evidence_source_selected"] = "none"
    tracker["selected_source"] = "none"
    tracker["semantic_evidence_source_runtime_integration"] = False
    tracker["semantic_evidence_source_applied"] = False
    tracker["semantic_evidence_source_encoded"] = False
    tracker["magpie_source_provenance_sha256"] = provenance_sha
    tracker["magpie_license_receipt_sha256"] = receipt_sha
    tracker["magpie_development_matches_sha256"] = matches_sha
    tracker["magpie_sense_alignment_sha256"] = alignment_sha
    tracker["magpie_semantic_evidence_sha256"] = semantic_sha
    tracker["magpie_development_evaluation_sha256"] = evaluation_sha
    tracker["magpie_candidate_decision_sha256"] = decision_sha
    tracker["magpie_source_version"] = COMMIT
    tracker["magpie_source_artifact_sha256"] = artifact_hash
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
    tracker["next_legal_transition"] = "NEXT_CANDIDATE_SOURCE_EVALUATION_AUTHORIZATION"
    tracker["next_transition_authorized"] = False
    tracker_sha = write_json(TRACKER, tracker)
    for path, expected in EXPECTED.items():
        if path == TRACKER:
            continue
        if sha256(path) != expected:
            refuse(f"tracker update mutated {path}")
    print(json.dumps({
        "candidate_decision_sha256": decision_sha,
        "development_evaluation_sha256": evaluation_sha,
        "evaluation_status": status,
        "license_receipt_sha256": receipt_sha,
        "no_support": no_count,
        "operator_by_semantic": evaluation["operator_by_semantic"],
        "selected_source": "none",
        "semantic_evidence_sha256": semantic_sha,
        "sense_alignment_coverage_fraction": evaluation["sense_alignment_coverage_fraction"],
        "sense_alignment_sha256": alignment_sha,
        "source_provenance_sha256": provenance_sha,
        "surface_coverage_fraction": evaluation["surface_coverage_fraction"],
        "surface_match_counts": evaluation["surface_match_counts"],
        "tracker_sha256": tracker_sha,
        "unknown_support": unknown_count,
        "yes_support": yes_count,
        "false_no_count": len(false_no),
        "false_yes_count": len(false_yes),
        "mixed_usage_expression_count": len(mixed_expressions),
        "mixed_usage_row_count": len(mixed_usage_rows),
        "evidence_code_counts": evaluation["evidence_code_counts"],
        "matches_sha256": matches_sha,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
