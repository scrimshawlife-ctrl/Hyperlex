"""Evaluate the 2009 Korkontzelos–Manandhar Table 1 on the 225 development rows.

The pass does not select the source, integrate it, or draw a measurement sample.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from hyperlexical.km_candidate_evaluation import align_item, join_synset, lookup_key
from hyperlexical.unbind_sense_screen_v1 import load_wordnet

LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
HYPERLEX = Path("/home/morpheus/Hyperlex")
SENSE = LEDGER / "operator-review/HLX-EVAL-UNBIND-SENSE-SCREEN-V1-HYPOTHESIS-001"
SOURCE = LEDGER / "operator-review/HLX-EVAL-UNBIND-SEMANTIC-EVIDENCE-SOURCE-V1-001"
WORDNET = LEDGER / "acquisition/sources/wordnet-3.0/wordnet"
PDF = LEDGER / "acquisition/sources/korkontzelos-manandhar-2009/P09-2017.pdf"
TRACKER = SENSE / "HYPOTHESIS.json"
EVIDENCE_MANIFEST = SENSE / "DEVELOPMENT_EVIDENCE.json"
EVENTS = LEDGER / "events.jsonl"
LEDGER_FILE = LEDGER / "ledger.json"

PROVENANCE_PATH = SOURCE / "KM_SOURCE_PROVENANCE.json"
LICENSE_PATH = SOURCE / "KM_LICENSE_RECEIPT.json"
INVENTORY_PATH = SOURCE / "KM_RAW_EVALUATION_INVENTORY.jsonl"
ALIGNMENT_PATH = SOURCE / "KM_PWN30_ALIGNMENT.jsonl"
SEMANTIC_PATH = SOURCE / "KM_HYPERLEX_SEMANTIC_EVIDENCE.jsonl"
EVALUATION_PATH = SOURCE / "KM_DEVELOPMENT_EVALUATION.json"
COMPARISON_PATH = SOURCE / "KM_MAGPIE_COMPARISON.json"
DECISION_PATH = SOURCE / "KM_CANDIDATE_DECISION.json"

PUBLICATION = "P09-2017"
OPERATORS = ("HIGH", "SECONDARY", "REJECT", "QUARANTINE", "UNRESOLVED")
SEMANTIC_STATES = ("YES", "NO", "UNKNOWN")
ALIGNMENT_STATES = (
    "EXACT_SOURCE_ID",
    "EXACT_UNIQUE_RECONSTRUCTION",
    "AMBIGUOUS_MULTIPLE_SYNSETS",
    "NO_PWN3_MATCH",
    "VERSION_CONFLICT",
    "UNKNOWN",
)
TABLE = (
    ("KM2009-NC-01", "NONCOMPOSITIONAL", "agony aunt"),
    ("KM2009-NC-02", "NONCOMPOSITIONAL", "black maria"),
    ("KM2009-NC-03", "NONCOMPOSITIONAL", "dead end"),
    ("KM2009-NC-04", "NONCOMPOSITIONAL", "dutch oven"),
    ("KM2009-NC-05", "NONCOMPOSITIONAL", "fish finger"),
    ("KM2009-NC-06", "NONCOMPOSITIONAL", "fool\u2019s paradise"),
    ("KM2009-NC-07", "NONCOMPOSITIONAL", "goat\u2019s rue"),
    ("KM2009-NC-08", "NONCOMPOSITIONAL", "green light"),
    ("KM2009-NC-09", "NONCOMPOSITIONAL", "high jump"),
    ("KM2009-NC-10", "NONCOMPOSITIONAL", "joint chiefs"),
    ("KM2009-NC-11", "NONCOMPOSITIONAL", "lip service"),
    ("KM2009-NC-12", "NONCOMPOSITIONAL", "living rock"),
    ("KM2009-NC-13", "NONCOMPOSITIONAL", "monkey puzzle"),
    ("KM2009-NC-14", "NONCOMPOSITIONAL", "motor pool"),
    ("KM2009-NC-15", "NONCOMPOSITIONAL", "prince Albert"),
    ("KM2009-NC-16", "NONCOMPOSITIONAL", "stocking stuffer"),
    ("KM2009-NC-17", "NONCOMPOSITIONAL", "sweet bay"),
    ("KM2009-NC-18", "NONCOMPOSITIONAL", "teddy boy"),
    ("KM2009-NC-19", "NONCOMPOSITIONAL", "think tank"),
    ("KM2009-CO-01", "COMPOSITIONAL", "box white oak"),
    ("KM2009-CO-02", "COMPOSITIONAL", "cartridge brass"),
    ("KM2009-CO-03", "COMPOSITIONAL", "common iguana"),
    ("KM2009-CO-04", "COMPOSITIONAL", "closed chain"),
    ("KM2009-CO-05", "COMPOSITIONAL", "eastern pipistrel"),
    ("KM2009-CO-06", "COMPOSITIONAL", "field mushroom"),
    ("KM2009-CO-07", "COMPOSITIONAL", "hard candy"),
    ("KM2009-CO-08", "COMPOSITIONAL", "king snake"),
    ("KM2009-CO-09", "COMPOSITIONAL", "labor camp"),
    ("KM2009-CO-10", "COMPOSITIONAL", "lemon tree"),
    ("KM2009-CO-11", "COMPOSITIONAL", "life form"),
    ("KM2009-CO-12", "COMPOSITIONAL", "parenthesis-free notation"),
    ("KM2009-CO-13", "COMPOSITIONAL", "parking brake"),
    ("KM2009-CO-14", "COMPOSITIONAL", "petit juror"),
    ("KM2009-CO-15", "COMPOSITIONAL", "relational adjective"),
    ("KM2009-CO-16", "COMPOSITIONAL", "taxonomic category"),
    ("KM2009-CO-17", "COMPOSITIONAL", "telephone service"),
    ("KM2009-CO-18", "COMPOSITIONAL", "tea table"),
    ("KM2009-CO-19", "COMPOSITIONAL", "upland cotton"),
)

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
    SOURCE / "MAGPIE_SOURCE_PROVENANCE.json": "bf0dd1dd747a6423406d97393f375f99620894a20af6bd4758e2de738d5c82dd",
    SOURCE / "MAGPIE_LICENSE_RECEIPT.json": "8813818aa3704ba1e764121d2f66ff1630862a66d6c0c0b959b6afa35e0c3972",
    SOURCE / "MAGPIE_DEVELOPMENT_MATCHES.jsonl": "84c847cfa545883de5a31979133fed87b0cdf9a7d13074c74cf227d9bfcadc83",
    SOURCE / "MAGPIE_SENSE_ALIGNMENT.jsonl": "037b0f4d96d463aa7c5fbecdbef06a530ffbf770735232c92bd6abd0dd71fc66",
    SOURCE / "MAGPIE_SEMANTIC_EVIDENCE.jsonl": "89f7227e1098407c7aaae6d9876b1f5780dbfe5b6a2eb3c3b09357d57822b577",
    SOURCE / "MAGPIE_DEVELOPMENT_EVALUATION.json": "74e2174d15c486dc60e9ad6be338199ff66a2d0950ed268105119323711108ba",
    SOURCE / "MAGPIE_CANDIDATE_DECISION.json": "6eaa968b6260946998dba13e5c423f178d3349cdfe06e5ea401717f5a9bcdd0d",
    LEDGER / "operator-review/HLX-EVAL-UNBIND-SCREEN-V7-001/unbind_screen_v7/measurement_error_analysis.json": "ebc56d4d4499efee19bc368365b0d6d3a7afc27ede4e78f40fb9d0fd15fcb9c8",
    EVENTS: "96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c",
    LEDGER_FILE: "77e22433203879b252f7a9e309d2013d7550101d1c4a014b494d2c96df87d0e0",
    TRACKER: "c3fe6f2fd21d07b8b45d9f26ffeebbcfbe3cb68a1f5a7952dee94d9a2c995936",
    HYPERLEX / "scripts/shadow/hyperlexical/unbind_sense_screen_v1.py": "531b58422e6f18b42276c6dde36493c7d0f8841556785b4b8911017879f93ad0",
    HYPERLEX / "scripts/shadow/hyperlexical/unbind_sense_screen_v2.py": "4b6f125da435b365af143c187902093bee5c9502db5b813a3d2bba11f889fa2b",
    HYPERLEX / "scripts/shadow/hyperlexical/unbind_screen_v3.py": "179d8dcc112214c70566bd3c9a0397e1ebab9131666b0ca1f2a3817973aaccc6",
    HYPERLEX / "scripts/shadow/hyperlexical/unbind_screen_v4.py": "f1e86e2f21544655cda6a136885a186b20885d501cb7ea9c75e18b3dd4a42377",
    HYPERLEX / "scripts/shadow/hyperlexical/unbind_screen_v5.py": "70504574523f2e8fde0fb974e3027205dded2c96213dd997f44475ea6856f948",
    HYPERLEX / "scripts/shadow/hyperlexical/unbind_screen_v6.py": "59699496c15aaedfbe69a7e49b5c6e62d1e543ce5a1e0e9a0255a98a62036fba",
    HYPERLEX / "scripts/shadow/hyperlexical/unbind_screen_v7.py": "73335bde8eec262ebecfedfc0d0ecb0a965da5c6b66e53c16f2aee2f38b061ab",
    PDF: "046da9fc26cfdf220e41ad914314f0703ea3c84cd86e045b20146b34189113d1",
    WORDNET / "data.noun": "489f145e0f68877c0be5bd0eb4117adaaac52f38f6204eb8d85dbe2158b614cc",
    WORDNET / "data.verb": "29cc96ed80c9f47d94fe75e332a9df80f4b1c737205f92d2f433d63c6da2ab51",
    WORDNET / "data.adj": "f24b635368be441501c9b8001e9271fd3b30b203f00d91e332979e6f8fe35646",
    WORDNET / "data.adv": "e66dbbda0e0359e41b7f225bff71dd0c263dc7c66c1b61abc9ba334973d92979",
    WORDNET / "README": "adad8d28ddea1db05b67ba1ac23506b025d29e0bcbf23bb35dde346089d8808d",
}


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


def fraction(numerator: int, denominator: int) -> str:
    return f"{numerator}/{denominator}"


def lemma_index(root: Path) -> dict[str, list[dict]]:
    synsets, glosses = load_wordnet(root)
    grouped: dict[str, dict[str, dict]] = defaultdict(dict)
    for (pos, offset), synset in synsets.items():
        if pos not in {"noun", "verb", "adj", "adv"}:
            continue
        synset_id = f"{pos}:{offset}"
        gloss = " ".join(glosses[(pos, offset)].split())
        bucket = grouped[synset_id]
        if not bucket:
            bucket["gloss"] = gloss
            bucket["lemmas"] = []
            bucket["synset"] = synset_id
        for lemma in synset.lemmas:
            if lemma not in bucket["lemmas"]:
                bucket["lemmas"].append(lemma)
    by_key: dict[str, list[dict]] = defaultdict(list)
    for record in grouped.values():
        record["lemmas"] = sorted(record["lemmas"])
        for lemma in record["lemmas"]:
            by_key[lookup_key(lemma)].append(record)
    for key, records in by_key.items():
        unique = {item["synset"]: item for item in records}
        by_key[key] = [unique[name] for name in sorted(unique)]
    return by_key


def candidate_status(yes_count: int, yes_exact: int) -> str:
    if yes_count == 0:
        return "CANDIDATE_INSUFFICIENT"
    if yes_exact != yes_count:
        return "CANDIDATE_REJECTED"
    return "CANDIDATE_PROMISING"


def main() -> None:
    magpie_module = HYPERLEX / "scripts/shadow/hyperlexical/magpie_candidate_evaluation.py"
    if not magpie_module.is_file():
        refuse("MAGPIE evaluator is missing")
    for path, expected in EXPECTED.items():
        if expected is None:
            continue
        if sha256(path) != expected:
            refuse(f"sealed artifact changed before evaluation: {path}")
    readme = (WORDNET / "README").read_text(encoding="utf-8", errors="replace")
    if "WordNet 3.0" not in readme:
        refuse("local WordNet README does not identify release 3.0")
    labels = Counter(label for _item_id, label, _surface in TABLE)
    if labels["NONCOMPOSITIONAL"] != 19 or labels["COMPOSITIONAL"] != 19 or len(TABLE) != 38:
        refuse("recovered table does not match the published 19/19 split")
    when = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pdf_mtime = datetime.fromtimestamp(PDF.stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    by_key = lemma_index(WORDNET)
    inventory = []
    alignments = []
    for item_id, label, surface in TABLE:
        records = by_key.get(lookup_key(surface), [])
        synset_ids = [record["synset"] for record in records]
        aligned = align_item(label, None, synset_ids)
        inventory.append({
            "schema": "hyperlex.km_raw_evaluation_item.v1",
            "source_context": None,
            "source_item_id": item_id,
            "source_label": label,
            "source_page_or_location": "P09-2017 Table 1, proceedings page 67",
            "surface": surface,
        })
        alignments.append({
            "aligned_pwn30_synset": aligned["aligned_pwn30_synset"],
            "alignment_status": aligned["alignment_status"],
            "candidate_glosses": [record["gloss"] for record in records],
            "candidate_lemmas": sorted({lemma for record in records for lemma in record["lemmas"]}),
            "candidate_synsets": synset_ids,
            "exact_sense_identity_preserved_by_source": False,
            "json_schema_document": None,
            "lookup_key": lookup_key(surface),
            "primary_evidence_code": aligned["primary_evidence_code"],
            "schema": "hyperlex.km_pwn30_alignment_row.v1",
            "semantic_noncompositional": aligned["semantic_noncompositional"],
            "source_gloss": None,
            "source_item_id": item_id,
            "source_label": label,
            "source_lemma_key": None,
            "source_pos": None,
            "source_sense_key": None,
            "source_synset_identifier": None,
            "source_synset_offset": None,
            "surface": surface,
            "wordnet_version_in_source": "3.0",
        })
    exact = {}
    ambiguous: dict[str, list[str]] = defaultdict(list)
    for row in alignments:
        if row["alignment_status"] in {"EXACT_SOURCE_ID", "EXACT_UNIQUE_RECONSTRUCTION"}:
            synset = row["aligned_pwn30_synset"]
            if synset in exact:
                refuse("two exact items share one synset")
            exact[synset] = row
        elif row["alignment_status"] == "AMBIGUOUS_MULTIPLE_SYNSETS":
            for synset in row["candidate_synsets"]:
                ambiguous[synset].append(row["source_item_id"])
    manifest = json.loads(EVIDENCE_MANIFEST.read_text(encoding="utf-8"))
    rows = manifest["rows"]
    if len(rows) != 225 or any(row.get("sense_class") is not None for row in rows):
        refuse("development manifest changed")
    semantic_rows = []
    surface_key_hits = []
    inventory_keys = {lookup_key(surface) for _item_id, _label, surface in TABLE}
    for row in rows:
        synset = f"{row['synset_pos']}:{row['synset_offset']}"
        joined = join_synset(synset, exact, ambiguous)
        if lookup_key(row["surface"]) in inventory_keys:
            surface_key_hits.append(row["row_id"])
        semantic_rows.append({
            "alignment_status": joined["alignment_status"],
            "candidate_aligned_synset": joined["candidate_aligned_synset"],
            "candidate_source": "KORKONTZELOS_MANANDHAR",
            "candidate_source_item_id": joined["candidate_source_item_id"],
            "hyperlex_synset": synset,
            "json_schema_document": None,
            "pos": row["pos"],
            "primary_evidence_code": joined["primary_evidence_code"],
            "provenance": {
                "gloss_used_to_choose_synset": False,
                "operator_label_used": False,
                "publication": PUBLICATION,
                "publication_pdf_sha256": EXPECTED[PDF],
                "surface_join": False,
                "wordnet_release": "3.0",
            },
            "row_id": row["row_id"],
            "schema": "hyperlex.km_hyperlex_semantic_evidence_row.v1",
            "semantic_noncompositional": joined["semantic_noncompositional"],
            "surface": row["surface"],
        })
    alignment_counts = Counter(row["alignment_status"] for row in alignments)
    label_counts = Counter(row["source_label"] for row in alignments)
    inventory_sha = write_jsonl(INVENTORY_PATH, inventory)
    alignment_sha = write_jsonl(ALIGNMENT_PATH, alignments)
    semantic_sha = write_jsonl(SEMANTIC_PATH, semantic_rows)
    frozen = [json.loads(line) for line in SEMANTIC_PATH.read_text(encoding="utf-8").splitlines() if line]
    if any("operator_bucket" in row for row in frozen):
        refuse("operator label entered semantic evidence")
    by_operator = {name: Counter() for name in OPERATORS}
    semantic_counts = Counter()
    code_counts = Counter()
    false_yes = []
    false_no = []
    for manifest_row, evidence_row in zip(rows, frozen):
        operator = manifest_row["operator_bucket"]
        semantic = evidence_row["semantic_noncompositional"]
        if operator not in by_operator:
            refuse(f"unexpected operator bucket: {operator}")
        by_operator[operator][semantic] += 1
        semantic_counts[semantic] += 1
        code_counts[evidence_row["primary_evidence_code"]] += 1
        if semantic == "YES" and operator != "HIGH":
            false_yes.append(evidence_row["row_id"])
        if semantic == "NO" and operator == "HIGH":
            false_no.append(evidence_row["row_id"])
    yes_count = semantic_counts["YES"]
    no_count = semantic_counts["NO"]
    unknown_count = semantic_counts["UNKNOWN"]
    yes_exact = sum(1 for row in frozen if row["semantic_noncompositional"] == "YES" and row["alignment_status"] in {"EXACT_SOURCE_ID", "EXACT_UNIQUE_RECONSTRUCTION"})
    sense_covered = sum(1 for row in frozen if row["alignment_status"] in {"EXACT_SOURCE_ID", "EXACT_UNIQUE_RECONSTRUCTION"})
    polysemous = alignment_counts["AMBIGUOUS_MULTIPLE_SYNSETS"]
    unique = alignment_counts["EXACT_UNIQUE_RECONSTRUCTION"]
    identity_not_preserved = unique == 0 and polysemous > (len(TABLE) / 2)
    status = "CANDIDATE_INSUFFICIENT" if identity_not_preserved else candidate_status(yes_count, yes_exact)
    provenance = {
        "acquisition_method": "HTTPS GET of the ACL Anthology PDF",
        "acquisition_timestamp_utc": pdf_mtime,
        "acquisition_url": "https://aclanthology.org/P09-2017.pdf",
        "authors": ["Ioannis Korkontzelos", "Suresh Manandhar"],
        "canonical_publication_url": "https://aclanthology.org/P09-2017/",
        "evaluated_at": when,
        "historical_count_hint_not_used": {"compositional": 60, "noncompositional": 56},
        "json_schema_document": None,
        "later_naacl_2010_sample_acquired": False,
        "publication": "Detecting Compositionality in Multi-Word Expressions",
        "publication_year": 2009,
        "schema": "hyperlex.km_source_provenance.v1",
        "source_artifact": "P09-2017.pdf",
        "source_artifact_sha256": EXPECTED[PDF],
        "source_name": "Korkontzelos-Manandhar WordNet-derived MWE compositionality evaluation set",
        "source_preserves_synset_identifier": False,
        "table": "Table 1, proceedings pages 65-68, table printed on page 67",
        "venue": "ACL-IJCNLP 2009 short papers",
        "verified_inventory_counts": {"COMPOSITIONAL": 19, "NONCOMPOSITIONAL": 19, "items": 38},
        "version": "ACL Anthology P09-2017",
        "wordnet_data_sha256": {
            "data.adj": EXPECTED[WORDNET / "data.adj"],
            "data.adv": EXPECTED[WORDNET / "data.adv"],
            "data.noun": EXPECTED[WORDNET / "data.noun"],
            "data.verb": EXPECTED[WORDNET / "data.verb"],
        },
        "wordnet_release_used_for_reconstruction": "Princeton WordNet 3.0",
        "wordnet_version_stated_in_paper": "3.0",
    }
    receipt = {
        "anthology_distribution_license": "CC-BY-NC-SA-3.0",
        "anthology_distribution_license_basis": "ACL Anthology footer: materials prior to 2016 are licensed under CC-BY-NC-SA 3.0, and permission is granted to make copies for teaching and research.",
        "code_license": None,
        "code_license_note": "No code artifact was published with Table 1 and none was acquired.",
        "data_license": None,
        "data_license_note": "No separate dataset license exists. The evaluation list is Table 1 of the paper.",
        "json_schema_document": None,
        "license_status": "ESTABLISHED_FOR_RESEARCH_EXTRACTION",
        "pdf_copyright_notice": "c\u00a92009 ACL and AFNLP",
        "publication_license": "CC-BY-NC-SA-3.0",
        "schema": "hyperlex.km_license_receipt.v1",
        "source_name": "KORKONTZELOS_MANANDHAR",
        "source_version": "P09-2017",
        "used": "Table 1 surfaces and the two section labels only",
        "not_used_from_table_typography": "Bold, underline, and italic marks report system detections, not gold labels.",
    }
    provenance_sha = write_json(PROVENANCE_PATH, provenance)
    receipt_sha = write_json(LICENSE_PATH, receipt)
    evaluation = {
        "abstention_count": unknown_count,
        "abstention_rate_fraction": fraction(unknown_count, 225),
        "alignment_counts": {name: alignment_counts[name] for name in ALIGNMENT_STATES},
        "candidate": "KORKONTZELOS_MANANDHAR",
        "candidate_inventory_size": 38,
        "compositional_source_count": label_counts["COMPOSITIONAL"],
        "development_manifest_sha256": EXPECTED[EVIDENCE_MANIFEST],
        "development_rows": 225,
        "diagnostics_are_descriptive": True,
        "evidence_code_counts": dict(sorted(code_counts.items())),
        "false_no_count": len(false_no),
        "false_yes_count": len(false_yes),
        "inventory_sha256": inventory_sha,
        "json_schema_document": None,
        "mapping_assumptions": {
            "false_no": "A semantic NO whose operator bucket is HIGH. Operator HIGH is not gold semantic YES.",
            "false_yes": "A semantic YES whose operator bucket is not HIGH. Operator REJECT is not compositional evidence.",
            "no_precision": "Among semantic NO rows, the fraction whose operator bucket is SECONDARY. SECONDARY is not defined as compositional NO.",
            "operator_quarantine": "Quarantine is not compositionality evidence.",
            "operator_reject": "Reject stays in its own joint-table row. It is a different axis from compositionality.",
            "yes_precision": "Among semantic YES rows, the fraction whose operator bucket is HIGH. The correlation is a proxy, not an identity.",
        },
        "no_precision": "NOT_COMPUTABLE" if no_count == 0 else fraction(by_operator["SECONDARY"]["NO"], no_count),
        "no_support": no_count,
        "noncompositional_source_count": label_counts["NONCOMPOSITIONAL"],
        "operator_by_semantic": {
            name: {state: by_operator[name][state] for state in SEMANTIC_STATES}
            for name in OPERATORS
        },
        "operator_labels_joined_after_semantic_evidence_was_written": True,
        "operator_labels_used_as_runtime_evidence": False,
        "pwn30_alignment_sha256": alignment_sha,
        "schema": "hyperlex.km_development_evaluation.v1",
        "selected_source": "none",
        "semantic_evidence_sha256": semantic_sha,
        "sense_aligned_coverage_count": sense_covered,
        "sense_aligned_coverage_fraction": fraction(sense_covered, 225),
        "source_version": "P09-2017",
        "surface_key_overlap_count": len(surface_key_hits),
        "surface_key_overlap_not_used_as_join": True,
        "unknown_support": unknown_count,
        "yes_precision": "NOT_COMPUTABLE" if yes_count == 0 else fraction(by_operator["HIGH"]["YES"], yes_count),
        "yes_support": yes_count,
    }
    evaluation_sha = write_json(EVALUATION_PATH, evaluation)
    magpie_path = SOURCE / "MAGPIE_DEVELOPMENT_EVALUATION.json"
    magpie = json.loads(magpie_path.read_text(encoding="utf-8"))
    comparison = {
        "json_schema_document": None,
        "korkontzelos_manandhar": {
            "abstention": evaluation["abstention_rate_fraction"],
            "no_support": no_count,
            "sense_aligned_coverage": evaluation["sense_aligned_coverage_fraction"],
            "surface_coverage": fraction(len(surface_key_hits), 225),
            "target_quality": "Human compositional versus noncompositional labels on a WordNet 3.0 MWE sample. The paper stores no synset id. A unique PWN 3.0 lemma reconstructs one synset for monosemous items.",
            "yes_support": yes_count,
        },
        "magpie": {
            "abstention": magpie["abstention_rate_fraction"],
            "development_evaluation_sha256": EXPECTED[magpie_path],
            "no_support": magpie["no_support"],
            "sense_aligned_coverage": magpie["sense_alignment_coverage_fraction"],
            "surface_coverage": magpie["surface_coverage_fraction"],
            "target_quality": "Contextual literal versus idiomatic labels. The artifact stores no WordNet sense identifier.",
            "yes_support": magpie["yes_support"],
        },
        "purpose": "Compare sense-aligned support. Raw surface coverage is not the ranking.",
        "schema": "hyperlex.km_magpie_comparison.v1",
        "sense_alignment_barrier": {
            "korkontzelos_manandhar_inventory_unique_reconstructions": unique,
            "korkontzelos_manandhar_hyperlex_sense_aligned_rows": sense_covered,
            "magpie_hyperlex_sense_aligned_rows": 0,
        },
    }
    comparison_sha = write_json(COMPARISON_PATH, comparison)
    decision = {
        "candidate": "KORKONTZELOS_MANANDHAR",
        "comparison_sha256": comparison_sha,
        "evaluation_sha256": evaluation_sha,
        "evaluation_status": status,
        "inventory_sha256": inventory_sha,
        "json_schema_document": None,
        "license_receipt_sha256": receipt_sha,
        "measurement_eligible": False,
        "measurement_sample_drawn": False,
        "next_legal_transition": "NEXT_CANDIDATE_SOURCE_EVALUATION_AUTHORIZATION",
        "next_transition_authorized": False,
        "pwn30_alignment_sha256": alignment_sha,
        "readiness_question_met": yes_count > 0 and yes_exact == yes_count,
        "runtime_integration": False,
        "schema": "hyperlex.km_candidate_decision.v1",
        "select_005_authorized": False,
        "selected_source": "none",
        "semantic_evidence_sha256": semantic_sha,
        "sense_identity_not_preserved_finding": identity_not_preserved,
        "sense_identity_not_preserved_finding_name": "WORDNET_DERIVED_BUT_SENSE_IDENTITY_NOT_PRESERVED" if identity_not_preserved else None,
        "source_provenance_sha256": provenance_sha,
        "source_version": "P09-2017",
        "state": "CANDIDATE_SOURCE_EVALUATED",
        "why": "Table 1 stores surfaces and labels, not synset ids. Unique PWN 3.0 lemmas reconstruct 30 synsets, and 8 items are polysemous and stay UNKNOWN. None of the reconstructed synsets occur in the 225 development rows, so Hyperlex YES support is 0.",
    }
    decision_sha = write_json(DECISION_PATH, decision)
    for path, expected in EXPECTED.items():
        if path == TRACKER or expected is None:
            continue
        if sha256(path) != expected:
            refuse(f"evaluation mutated {path}")
    tracker = json.loads(TRACKER.read_text(encoding="utf-8"))
    tracker["previous_state"] = tracker.get("state")
    tracker["previous_tracker_sha256"] = EXPECTED[TRACKER]
    tracker["state"] = "CANDIDATE_SOURCE_EVALUATED"
    tracker["semantic_evidence_source_state"] = "CANDIDATE_SOURCE_EVALUATED"
    tracker["evaluated_candidates"] = ["MAGPIE", "KORKONTZELOS_MANANDHAR"]
    tracker["magpie_evaluation_status"] = "CANDIDATE_INSUFFICIENT"
    tracker["km_evaluation_status"] = status
    tracker["latest_evaluated_candidate"] = "KORKONTZELOS_MANANDHAR"
    tracker["selected_source"] = "none"
    tracker["semantic_evidence_source_selected"] = "none"
    tracker["semantic_evidence_source_runtime_integration"] = False
    tracker["semantic_evidence_source_applied"] = False
    tracker["semantic_evidence_source_encoded"] = False
    tracker["km_source_provenance_sha256"] = provenance_sha
    tracker["km_license_receipt_sha256"] = receipt_sha
    tracker["km_raw_inventory_sha256"] = inventory_sha
    tracker["km_pwn30_alignment_sha256"] = alignment_sha
    tracker["km_hyperlex_semantic_evidence_sha256"] = semantic_sha
    tracker["km_development_evaluation_sha256"] = evaluation_sha
    tracker["km_magpie_comparison_sha256"] = comparison_sha
    tracker["km_candidate_decision_sha256"] = decision_sha
    tracker["km_source_version"] = "P09-2017"
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
        if path == TRACKER or expected is None:
            continue
        if sha256(path) != expected:
            refuse(f"tracker update mutated {path}")
    print(json.dumps({
        "alignment_counts": evaluation["alignment_counts"],
        "candidate_decision_sha256": decision_sha,
        "comparison_sha256": comparison_sha,
        "development_evaluation_sha256": evaluation_sha,
        "evaluation_status": status,
        "inventory_sha256": inventory_sha,
        "license_receipt_sha256": receipt_sha,
        "no_support": no_count,
        "operator_by_semantic": evaluation["operator_by_semantic"],
        "pwn30_alignment_sha256": alignment_sha,
        "selected_source": "none",
        "semantic_evidence_sha256": semantic_sha,
        "sense_aligned_coverage_fraction": evaluation["sense_aligned_coverage_fraction"],
        "sense_identity_not_preserved_finding": identity_not_preserved,
        "source_provenance_sha256": provenance_sha,
        "tracker_sha256": tracker_sha,
        "unknown_support": unknown_count,
        "yes_support": yes_count,
        "label_counts": dict(label_counts),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
