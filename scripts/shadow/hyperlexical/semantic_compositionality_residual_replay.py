"""Score the semantic-compositionality residual on the 225 development rows.

The candidate specification is written before any row is encoded. Operator
labels are read only after the score artifact has been hashed. The pass does
not select the source, integrate it, or draw a measurement sample.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from hyperlexical.km_candidate_evaluation import lookup_key
from hyperlexical.semantic_compositionality_residual import (
    COMPOSITION_OPERATOR,
    DISTANCE_METRIC,
    MODEL_NAME,
    MODEL_REVISION,
    candidate_policy,
    distribution,
    evaluation_status,
    exact_synset_ids,
    extract_constituents,
    lexical_synset_ids,
    primary_abstention,
    representation_text,
    resolve_constituent,
    resolved_synset,
    score_record,
    select_lemma,
    vector_hash,
)
from hyperlexical.unbind_sense_screen_v1 import load_exceptions, load_wordnet

LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
HYPERLEX = Path("/home/morpheus/Hyperlex")
SENSE = LEDGER / "operator-review/HLX-EVAL-UNBIND-SENSE-SCREEN-V1-HYPOTHESIS-001"
SOURCE = LEDGER / "operator-review/HLX-EVAL-UNBIND-SEMANTIC-EVIDENCE-SOURCE-V1-001"
WORDNET = LEDGER / "acquisition/sources/wordnet-3.0/wordnet"
MODEL_DIR = (
    LEDGER
    / "acquisition/sources/all-MiniLM-L6-v2"
    / MODEL_REVISION
)
TRACKER = SENSE / "HYPOTHESIS.json"
EVIDENCE_MANIFEST = SENSE / "DEVELOPMENT_EVIDENCE.json"
EVENTS = LEDGER / "events.jsonl"
LEDGER_FILE = LEDGER / "ledger.json"

PROVENANCE_PATH = SOURCE / "RESIDUAL_SOURCE_PROVENANCE.json"
LICENSE_PATH = SOURCE / "RESIDUAL_LICENSE_RECEIPT.json"
SPEC_PATH = SOURCE / "RESIDUAL_CANDIDATE_SPEC.json"
SCORES_PATH = SOURCE / "RESIDUAL_DEVELOPMENT_SCORES.jsonl"
EVALUATION_PATH = SOURCE / "RESIDUAL_DEVELOPMENT_EVALUATION.json"
DECISION_PATH = SOURCE / "RESIDUAL_CANDIDATE_DECISION.json"

OPERATORS = ("HIGH", "SECONDARY", "REJECT", "QUARANTINE", "UNRESOLVED")
OPERATOR_COUNTS = {"HIGH": 101, "SECONDARY": 46, "REJECT": 77, "QUARANTINE": 1, "UNRESOLVED": 0}
POS_NAME = {"n": "noun", "v": "verb", "a": "adj", "r": "adv", "s": "adj"}
FILE_POS = frozenset({"noun", "verb", "adj", "adv"})
MAX_SEQUENCE_LENGTH = 256
OUTPUT_DIMENSION = 384

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
    SOURCE / "KM_SOURCE_PROVENANCE.json": "88fbfa077d2394b8ce631ec700c482ad98a0f62f0ab06964f4f43a77d906f9aa",
    SOURCE / "KM_LICENSE_RECEIPT.json": "eb4c9406aab7f9021d346ebd24634cad1dcf0e6076f069e73b1d4b2702dbe2f8",
    SOURCE / "KM_RAW_EVALUATION_INVENTORY.jsonl": "3a35ddc0b2c04a5386c6112a2bb3cdf22735edbe2fd791f0c2ec542fe9184d81",
    SOURCE / "KM_PWN30_ALIGNMENT.jsonl": "531d13cf1bdbc939fc11d9ef5864c6878a9f58210368c596c0aad08ff75e61c9",
    SOURCE / "KM_HYPERLEX_SEMANTIC_EVIDENCE.jsonl": "4e98f8f06713ffcf02549305aef140e92b9b8b2790f471f3ce1f41fe208b2f7a",
    SOURCE / "KM_DEVELOPMENT_EVALUATION.json": "00a1d1f667635354e20e5002c4ece846fe3a8125a7ca12ebe09bb7e28dedd1a7",
    SOURCE / "KM_MAGPIE_COMPARISON.json": "240b3ea468d22a80ac5e5765521cc691b80f914b7baff6bb1ae4819475f54965",
    SOURCE / "KM_CANDIDATE_DECISION.json": "93a07e3c78b53a69965497410c34ddb52c2a5d3add3fb2f3cd3fd9ca84eb3d9f",
    LEDGER / "operator-review/HLX-EVAL-UNBIND-SCREEN-V7-001/unbind_screen_v7/measurement_error_analysis.json": "ebc56d4d4499efee19bc368365b0d6d3a7afc27ede4e78f40fb9d0fd15fcb9c8",
    EVENTS: "96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c",
    LEDGER_FILE: "77e22433203879b252f7a9e309d2013d7550101d1c4a014b494d2c96df87d0e0",
    TRACKER: "b3546102410058d3596c4563604998685753a698b2bc533b353e1f039440f704",
    HYPERLEX / "scripts/shadow/hyperlexical/unbind_sense_screen_v1.py": "531b58422e6f18b42276c6dde36493c7d0f8841556785b4b8911017879f93ad0",
    HYPERLEX / "scripts/shadow/hyperlexical/unbind_sense_screen_v2.py": "4b6f125da435b365af143c187902093bee5c9502db5b813a3d2bba11f889fa2b",
    HYPERLEX / "scripts/shadow/hyperlexical/unbind_screen_v3.py": "179d8dcc112214c70566bd3c9a0397e1ebab9131666b0ca1f2a3817973aaccc6",
    HYPERLEX / "scripts/shadow/hyperlexical/unbind_screen_v4.py": "f1e86e2f21544655cda6a136885a186b20885d501cb7ea9c75e18b3dd4a42377",
    HYPERLEX / "scripts/shadow/hyperlexical/unbind_screen_v5.py": "70504574523f2e8fde0fb974e3027205dded2c96213dd997f44475ea6856f948",
    HYPERLEX / "scripts/shadow/hyperlexical/unbind_screen_v6.py": "59699496c15aaedfbe69a7e49b5c6e62d1e543ce5a1e0e9a0255a98a62036fba",
    HYPERLEX / "scripts/shadow/hyperlexical/unbind_screen_v7.py": "73335bde8eec262ebecfedfc0d0ecb0a965da5c6b66e53c16f2aee2f38b061ab",
    HYPERLEX / "scripts/shadow/hyperlexical/km_candidate_evaluation.py": "c6e6cb69a215de395023fa44237fc4a9f1a02199fd4b92627b7d9345b2b5fbeb",
    HYPERLEX / "scripts/shadow/hyperlexical/km_candidate_evaluation_replay.py": "274da840325e0782c938a42a7e5f8ca7a3945982391cd144a50e674059bb333f",
    HYPERLEX / "scripts/shadow/hyperlexical/magpie_candidate_evaluation.py": "3cf19b6e3468e55d0636d4df0d2882bc886e9c7024548653a08c26f7ab43c7a9",
    HYPERLEX / "scripts/shadow/hyperlexical/magpie_candidate_evaluation_replay.py": "f01c3361956ae81df772c7b78448d7a58dad342a1f4fe7d084ef00a889587710",
    WORDNET / "data.noun": "489f145e0f68877c0be5bd0eb4117adaaac52f38f6204eb8d85dbe2158b614cc",
    WORDNET / "data.verb": "29cc96ed80c9f47d94fe75e332a9df80f4b1c737205f92d2f433d63c6da2ab51",
    WORDNET / "data.adj": "f24b635368be441501c9b8001e9271fd3b30b203f00d91e332979e6f8fe35646",
    WORDNET / "data.adv": "e66dbbda0e0359e41b7f225bff71dd0c263dc7c66c1b61abc9ba334973d92979",
    WORDNET / "README": "adad8d28ddea1db05b67ba1ac23506b025d29e0bcbf23bb35dde346089d8808d",
    WORDNET / "LICENSE": "7731175a77952e259390b496fab905e57118b8d19ad3a8383c67eee724ff443f",
    MODEL_DIR / "model.safetensors": "53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db",
    MODEL_DIR / "tokenizer.json": "be50c3628f2bf5bb5e3a7f17b1f74611b2561a3a27eeab05e5aa30f411572037",
    MODEL_DIR / "vocab.txt": "07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3",
}

MODEL_FILES = (
    "1_Pooling/config.json",
    "README.md",
    "config.json",
    "config_sentence_transformers.json",
    "model.safetensors",
    "modules.json",
    "sentence_bert_config.json",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.txt",
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
        if sha256(path) != expected:
            refuse(f"sealed file changed: {path}")


def package_license(name: str) -> str:
    root = Path("/home/morpheus/hlx-private/venv-residual/lib")
    matches = sorted(root.glob(f"python*/site-packages/{name}-*.dist-info/METADATA"))
    if not matches:
        refuse(f"missing package metadata for {name}")
    header = matches[-1].read_text(encoding="utf-8", errors="replace").split("\n\n", 1)[0]
    expression = None
    generic = None
    classified = None
    for line in header.splitlines():
        if line.startswith("License-Expression:"):
            expression = line.split(":", 1)[1].strip()
        elif line.startswith("License:"):
            generic = line.split(":", 1)[1].strip()
        elif line.startswith("Classifier: License"):
            classified = line.split("::")[-1].strip()
    found = expression or generic or classified
    if not found:
        refuse(f"no license line for {name}")
    return found


def build_indexes() -> tuple[dict, dict]:
    synsets, glosses = load_wordnet(WORDNET)
    by_id = {}
    index = defaultdict(list)
    for (pos, offset), synset in synsets.items():
        if pos not in FILE_POS:
            continue
        synset_id = f"{pos}:{offset}"
        if synset_id in by_id:
            continue
        by_id[synset_id] = {
            "gloss": " ".join(glosses[(pos, offset)].split()),
            "lemmas": list(synset.lemmas),
            "pos": pos,
            "synset": synset,
        }
        for lemma in synset.lemmas:
            index[lookup_key(lemma)].append(synset_id)
    for key, identifiers in index.items():
        index[key] = sorted(set(identifiers))
    return by_id, dict(index)


def pointer_records(synset_id: str, by_id: dict) -> list[tuple[str, int, str, str]]:
    record = by_id.get(synset_id)
    if record is None:
        return []
    rows = []
    for pointer in record["synset"].pointers:
        pos = POS_NAME.get(pointer.pos)
        if pos is None:
            continue
        target_id = f"{pos}:{pointer.offset}"
        target = by_id.get(target_id)
        if target is None or pointer.target < 1 or pointer.target > len(target["lemmas"]):
            lemma = ""
        else:
            lemma = target["lemmas"][pointer.target - 1]
        rows.append((pointer.symbol, pointer.target, target_id, lemma))
    return rows


def prepare_rows(manifest_rows: list[dict], by_id: dict, index: dict, exceptions: dict[str, set[str]]) -> list[dict]:
    prepared = []
    for row in manifest_rows:
        if row.get("sense_class") is not None:
            refuse("development row has a sense class")
        if row.get("pos") != row.get("synset_pos"):
            refuse("row POS and synset POS differ")
        if not row.get("synset_offset") or not row.get("gloss") or not row.get("surface"):
            refuse("development row is missing surface, gloss, or synset")
        synset = f"{row['synset_pos']}:{row['synset_offset']}"
        extraction = extract_constituents(row["surface"])
        pointers = pointer_records(synset, by_id)
        resolutions = []
        synsets = []
        lemmas = []
        representations = []
        for constituent in extraction["content_constituents"]:
            exact = exact_synset_ids(pointers, constituent, exceptions)
            lexical = lexical_synset_ids(index, constituent, exceptions)
            status = resolve_constituent(exact, lexical)
            chosen = resolved_synset(exact, lexical)
            resolutions.append(status)
            synsets.append(chosen)
            if chosen is None:
                lemmas.append(None)
                continue
            record = by_id.get(chosen)
            if record is None:
                refuse(f"resolved synset is not in PWN 3.0: {chosen}")
            if status == "EXACT":
                pool = [
                    lemma
                    for symbol, target_word, target_id, lemma in pointers
                    if target_id == chosen and symbol in {"+", "\\"} and target_word > 0 and lemma
                ]
            else:
                pool = list(record["lemmas"])
            lemma = select_lemma(pool, constituent, exceptions)
            lemmas.append(lemma)
            representations.append(representation_text(lemma, record["pos"], record["gloss"]))
        reason = primary_abstention(extraction["constituent_extraction_status"], resolutions)
        whole = None
        constituent_texts = None
        if reason is None:
            whole = representation_text(row["surface"], row["pos"], row["gloss"])
            constituent_texts = representations
        prepared.append(
            {
                "constituent_representations": constituent_texts,
                "extraction": extraction,
                "gloss": row["gloss"],
                "lemmas": lemmas,
                "pos": row["pos"],
                "resolutions": resolutions,
                "row_id": row["row_id"],
                "surface": row["surface"],
                "synset": synset,
                "synsets": synsets,
                "whole_representation": whole,
            }
        )
    return prepared


def load_encoder():
    import torch
    from sentence_transformers import SentenceTransformer

    torch.manual_seed(0)
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass
    model = SentenceTransformer(
        str(MODEL_DIR),
        device="cpu",
        local_files_only=True,
        backend="torch",
        model_kwargs={"torch_dtype": torch.float32},
    )
    model.eval()
    if int(model.max_seq_length) != MAX_SEQUENCE_LENGTH:
        refuse(f"max sequence length is {model.max_seq_length}")
    return model


def token_length(model, text: str) -> int:
    encoded = model.tokenizer(text, add_special_tokens=True, truncation=False)
    return len(encoded["input_ids"])


def encode_texts(model, texts: list[str]) -> dict[str, list[float]]:
    import torch

    encoded = {}
    with torch.inference_mode():
        for text in texts:
            torch.manual_seed(0)
            vector = model.encode(
                [text],
                batch_size=1,
                convert_to_numpy=True,
                device="cpu",
                normalize_embeddings=True,
                precision="float32",
                show_progress_bar=False,
            )[0]
            values = [float(item) for item in vector.tolist()]
            if len(values) != OUTPUT_DIMENSION:
                refuse(f"encoder width is {len(values)}")
            encoded[text] = values
    return encoded


def runtime_versions() -> dict:
    import numpy
    import tokenizers
    import torch
    import transformers
    import sentence_transformers

    return {
        "numpy": numpy.__version__,
        "python": ".".join(map(str, __import__("sys").version_info[:3])),
        "sentence_transformers": sentence_transformers.__version__,
        "tokenizers": tokenizers.__version__,
        "torch": torch.__version__,
        "transformers": transformers.__version__,
    }


def file_hashes() -> dict[str, str]:
    return {name: sha256(MODEL_DIR / name) for name in MODEL_FILES}


def iso_mtime(path: Path) -> str:
    stamp = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    return stamp.strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> None:
    check_sealed()
    manifest = json.loads(EVIDENCE_MANIFEST.read_text(encoding="utf-8"))
    rows = manifest["rows"]
    if len(rows) != 225:
        refuse(f"manifest row count is {len(rows)}")
    for row in rows:
        row.pop("operator_bucket", None)
        row.pop("operator_reason", None)
        row.pop("historical_unbind_screen", None)
    exceptions = load_exceptions(WORDNET)
    by_id, index = build_indexes()
    prepared = prepare_rows(rows, by_id, index, exceptions)
    if len(prepared) != 225:
        refuse("prepared row count drifted")

    import torch

    torch.manual_seed(0)
    torch.set_num_threads(1)
    versions = runtime_versions()
    hashes = file_hashes()
    pooling = json.loads((MODEL_DIR / "1_Pooling/config.json").read_text(encoding="utf-8"))
    tokenizer_config = json.loads((MODEL_DIR / "tokenizer_config.json").read_text(encoding="utf-8"))
    modules = json.loads((MODEL_DIR / "modules.json").read_text(encoding="utf-8"))
    provenance = {
        "acquired_at": iso_mtime(MODEL_DIR / "model.safetensors"),
        "api_embedding_service_used": False,
        "candidate": "SEMANTIC_COMPOSITIONALITY_RESIDUAL",
        "device": "cpu",
        "dtype": "float32",
        "file_sha256": hashes,
        "json_schema_document": None,
        "local_dir": str(MODEL_DIR),
        "model_name": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "model_source": "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2",
        "modules": modules,
        "not_acquired": ["onnx", "openvino", "pytorch_model.bin", "tf_model.h5"],
        "output_dimension": OUTPUT_DIMENSION,
        "pooling": pooling,
        "runtime_versions": versions,
        "schema": "hyperlex.residual_source_provenance.v1",
        "tokenizer_do_lower_case": tokenizer_config["do_lower_case"],
        "tokenizer_model_max_length": tokenizer_config["model_max_length"],
        "weights_sha256": hashes["model.safetensors"],
        "wordnet_license_sha256": EXPECTED[WORDNET / "LICENSE"],
        "wordnet_readme_sha256": EXPECTED[WORDNET / "README"],
        "wordnet_root": str(WORDNET),
    }
    provenance_sha = write_json(PROVENANCE_PATH, provenance)
    license_receipt = {
        "api_embedding_service_used": False,
        "candidate": "SEMANTIC_COMPOSITIONALITY_RESIDUAL",
        "json_schema_document": None,
        "model_license": "apache-2.0",
        "model_license_source": "README.md front matter of the pinned revision",
        "runtime_licenses": {
            "numpy": package_license("numpy"),
            "sentence_transformers": package_license("sentence_transformers"),
            "tokenizers": package_license("tokenizers"),
            "torch": package_license("torch"),
            "transformers": package_license("transformers"),
        },
        "schema": "hyperlex.residual_license_receipt.v1",
        "wordnet_license": "WordNet Release 3.0, Copyright 2006 Princeton University",
        "wordnet_license_sha256": EXPECTED[WORDNET / "LICENSE"],
    }
    receipt_sha = write_json(LICENSE_PATH, license_receipt)
    spec = {
        "candidate": "SEMANTIC_COMPOSITIONALITY_RESIDUAL",
        "cuda_available_at_spec_freeze": bool(torch.cuda.is_available()),
        "determinism": {
            "batch_size": 1,
            "device": "cpu",
            "dtype": "float32",
            "eval_mode": True,
            "inference_mode": True,
            "interop_threads": 1,
            "mkl_num_threads": "1",
            "normalize_embeddings": True,
            "num_threads": 1,
            "omp_num_threads": "1",
            "precision": "float32",
            "seed": 0,
            "tokenizers_parallelism": "false",
            "use_deterministic_algorithms": False,
        },
        "effective_max_sequence_length": MAX_SEQUENCE_LENGTH,
        "json_schema_document": None,
        "license_receipt_sha256": receipt_sha,
        "model_name": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "output_dimension": OUTPUT_DIMENSION,
        "policy": candidate_policy(),
        "provenance_sha256": provenance_sha,
        "row_scores_included": False,
        "runtime_versions": versions,
        "schema": "hyperlex.residual_candidate_spec.v1",
        "selected_source": "none",
        "source_provenance_sha256": provenance_sha,
        "tokenizer_json_sha256": hashes["tokenizer.json"],
        "tokenizer_revision": MODEL_REVISION,
        "vocab_sha256": hashes["vocab.txt"],
        "weights_sha256": hashes["model.safetensors"],
    }
    spec_text = json.dumps(spec, indent=2, sort_keys=True, ensure_ascii=True)
    if "residual_score" in spec_text or "operator_bucket" in spec_text:
        refuse("candidate spec contains a score or an operator label")
    spec_sha = write_json(SPEC_PATH, spec)
    if sha256(SPEC_PATH) != spec_sha:
        refuse("spec hash mismatch")

    model = load_encoder()
    for item in prepared:
        item["sequence_overflow"] = False
        if item["whole_representation"] is None:
            continue
        texts = [item["whole_representation"], *item["constituent_representations"]]
        if any(token_length(model, text) > MAX_SEQUENCE_LENGTH for text in texts):
            item["sequence_overflow"] = True
            item["whole_representation"] = None
            item["constituent_representations"] = None
    needed = []
    seen = set()
    for item in prepared:
        if item["whole_representation"] is None:
            continue
        for text in [item["whole_representation"], *item["constituent_representations"]]:
            if text not in seen:
                seen.add(text)
                needed.append(text)
    needed.sort()
    first = encode_texts(model, needed)
    second = encode_texts(model, needed)
    for text in needed:
        if vector_hash(first[text]) != vector_hash(second[text]):
            refuse("encoder replay did not match")
    vectors = first

    scores = []
    for item in prepared:
        whole_vector = None
        constituent_vectors = None
        if item["whole_representation"] is not None:
            whole_vector = vectors[item["whole_representation"]]
            constituent_vectors = [vectors[text] for text in item["constituent_representations"]]
        record = score_record(
            row_id=item["row_id"],
            surface=item["surface"],
            pos=item["pos"],
            synset=item["synset"],
            extraction=item["extraction"],
            resolutions=item["resolutions"],
            resolved_synsets=item["synsets"],
            resolved_lemmas=item["lemmas"],
            whole_representation=item["whole_representation"],
            constituent_representations=item["constituent_representations"],
            whole_vector=whole_vector,
            constituent_vectors=constituent_vectors,
            candidate_spec_sha256=spec_sha,
            sequence_overflow=item["sequence_overflow"],
        )
        if "operator_bucket" in record:
            refuse("score row carries an operator bucket")
        scores.append(record)
    if [row["row_id"] for row in scores] != [row["row_id"] for row in rows]:
        refuse("score order drifted from the manifest")
    score_sha = write_jsonl(SCORES_PATH, scores)
    if sha256(SCORES_PATH) != score_sha:
        refuse("score hash mismatch")
    if sha256(SPEC_PATH) != spec_sha:
        refuse("scoring mutated the spec")

    rejoined = json.loads(EVIDENCE_MANIFEST.read_text(encoding="utf-8"))
    if sha256(EVIDENCE_MANIFEST) != EXPECTED[EVIDENCE_MANIFEST]:
        refuse("manifest changed during scoring")
    buckets = {}
    for row in rejoined["rows"]:
        buckets[row["row_id"]] = row["operator_bucket"]
    counted = Counter(buckets.values())
    for name, expected_count in OPERATOR_COUNTS.items():
        if counted[name] != expected_count:
            refuse(f"operator count {name} is {counted[name]}")
    if any(row.get("sense_class") is not None for row in rejoined["rows"]):
        refuse("manifest sense class changed")

    by_operator = {name: [] for name in OPERATORS}
    unknown_by_operator = Counter()
    for record in scores:
        bucket = buckets[record["row_id"]]
        if bucket not in by_operator:
            refuse(f"unexpected operator bucket {bucket}")
        if record["score_status"] == "SCORED":
            by_operator[bucket].append(record["residual_score"])
        else:
            unknown_by_operator[bucket] += 1
    distributions = {name: distribution(by_operator[name]) for name in OPERATORS}
    high = distributions["HIGH"]
    high_comparison = "NOT_COMPUTABLE" if high["count"] == 0 else "DESCRIPTIVE_ONLY"
    scored_count = sum(item["count"] for item in distributions.values())
    status, next_transition = evaluation_status(scored_count)
    extraction_counts = Counter(record["constituent_extraction_status"] for record in scores)
    resolution_counts = Counter(
        status_name
        for record in scores
        for status_name in record["constituent_resolution_status"]
    )
    abstention_counts = Counter(
        record["primary_abstention_reason"]
        for record in scores
        if record["primary_abstention_reason"]
    )
    odd_content_tokens = 0
    content_tokens = 0
    for record in scores:
        for token in record["content_constituents"]:
            content_tokens += 1
            folded = token.casefold()
            if any(not (character.isalpha() or character.isdigit() or character in "-'") for character in folded):
                odd_content_tokens += 1
    evaluation = {
        "abstention_reason_counts": dict(sorted(abstention_counts.items())),
        "candidate": "SEMANTIC_COMPOSITIONALITY_RESIDUAL",
        "candidate_rule": "RUNE.SEMANTIC_COMPOSITIONALITY_RESIDUAL.v1",
        "candidate_spec_sha256": spec_sha,
        "composition_operator": COMPOSITION_OPERATOR,
        "content_tokens": content_tokens,
        "content_tokens_outside_letter_digit_hyphen_apostrophe": odd_content_tokens,
        "distance_metric": DISTANCE_METRIC,
        "distributions_by_operator": distributions,
        "emits_yes_no": False,
        "encode_replay_matched": True,
        "encoded_text_count": len(needed),
        "extraction_counts": dict(sorted(extraction_counts.items())),
        "high_comparison": high_comparison,
        "high_distribution": high,
        "high_proxy": "expected noncompositionality; not an identity",
        "json_schema_document": None,
        "license_receipt_sha256": receipt_sha,
        "operator_counts": {name: OPERATOR_COUNTS[name] for name in OPERATORS},
        "operator_labels_joined_after_score_artifact_was_hashed": True,
        "operator_labels_used_as_scoring_inputs": False,
        "operator_unknown_counts": {name: unknown_by_operator[name] for name in OPERATORS},
        "primary_analysis_bucket": "HIGH",
        "quarantine_is_not_semantic_evidence": True,
        "reject_is_not_semantic_no": True,
        "resolution_counts": dict(sorted(resolution_counts.items())),
        "row_count": 225,
        "schema": "hyperlex.residual_development_evaluation.v1",
        "score_artifact_sha256": score_sha,
        "scored_count": scored_count,
        "secondary_is_a_proxy_for_expected_compositionality": True,
        "selected_source": "none",
        "semantic_noncompositionality_threshold": None,
        "source_provenance_sha256": provenance_sha,
        "unknown_count": 225 - scored_count,
    }
    evaluation_sha = write_json(EVALUATION_PATH, evaluation)
    decision = {
        "candidate": "SEMANTIC_COMPOSITIONALITY_RESIDUAL",
        "candidate_rule": "RUNE.SEMANTIC_COMPOSITIONALITY_RESIDUAL.v1",
        "candidate_spec_sha256": spec_sha,
        "evaluation_sha256": evaluation_sha,
        "evaluation_status": status,
        "high_comparison": high_comparison,
        "high_scored_count": high["count"],
        "json_schema_document": None,
        "license_receipt_sha256": receipt_sha,
        "measurement_eligible": False,
        "measurement_sample_drawn": False,
        "next_legal_transition": next_transition,
        "next_transition_authorized": False,
        "runtime_integration": False,
        "schema": "hyperlex.residual_candidate_decision.v1",
        "score_artifact_sha256": score_sha,
        "scored_count": scored_count,
        "select_005_authorized": False,
        "selected_source": "none",
        "semantic_noncompositionality_threshold": None,
        "source_provenance_sha256": provenance_sha,
        "state": "CANDIDATE_SOURCE_EVALUATED",
        "unknown_count": 225 - scored_count,
        "why": (
            "The residual is a continuous score. No semantic-noncompositionality "
            "threshold is chosen in this pass, and operator labels were joined "
            "only after the score file was hashed."
        ),
        "yes_no_emitted": False,
    }
    decision_sha = write_json(DECISION_PATH, decision)
    check_sealed(skip={TRACKER})
    tracker = json.loads(TRACKER.read_text(encoding="utf-8"))
    tracker["previous_state"] = tracker.get("state")
    tracker["previous_tracker_sha256"] = EXPECTED[TRACKER]
    tracker["state"] = "CANDIDATE_SOURCE_EVALUATED"
    tracker["semantic_evidence_source_state"] = "CANDIDATE_SOURCE_EVALUATED"
    tracker["evaluated_candidates"] = [
        "MAGPIE",
        "KORKONTZELOS_MANANDHAR",
        "SEMANTIC_COMPOSITIONALITY_RESIDUAL",
    ]
    tracker["latest_evaluated_candidate"] = "SEMANTIC_COMPOSITIONALITY_RESIDUAL"
    tracker["residual_candidate"] = "RUNE.SEMANTIC_COMPOSITIONALITY_RESIDUAL.v1"
    tracker["residual_evaluation_status"] = status
    tracker["residual_candidate_spec_sha256"] = spec_sha
    tracker["residual_source_provenance_sha256"] = provenance_sha
    tracker["residual_license_receipt_sha256"] = receipt_sha
    tracker["residual_development_scores_sha256"] = score_sha
    tracker["residual_development_evaluation_sha256"] = evaluation_sha
    tracker["residual_candidate_decision_sha256"] = decision_sha
    tracker["residual_model_name"] = MODEL_NAME
    tracker["residual_model_revision"] = MODEL_REVISION
    tracker["residual_scored_count"] = scored_count
    tracker["residual_unknown_count"] = 225 - scored_count
    tracker["residual_high_comparison"] = high_comparison
    tracker["residual_threshold"] = None
    tracker["residual_yes_no_emitted"] = False
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
    tracker["next_legal_transition"] = next_transition
    tracker["next_transition_authorized"] = False
    tracker_sha = write_json(TRACKER, tracker)
    check_sealed(skip={TRACKER})
    if sha256(EVENTS) != EXPECTED[EVENTS] or sha256(LEDGER_FILE) != EXPECTED[LEDGER_FILE]:
        refuse("ledger or events changed")
    print(
        json.dumps(
            {
                "abstention_reason_counts": evaluation["abstention_reason_counts"],
                "candidate_decision_sha256": decision_sha,
                "candidate_spec_sha256": spec_sha,
                "development_evaluation_sha256": evaluation_sha,
                "development_scores_sha256": score_sha,
                "distributions_by_operator": distributions,
                "encoded_text_count": len(needed),
                "evaluation_status": status,
                "extraction_counts": evaluation["extraction_counts"],
                "high_comparison": high_comparison,
                "license_receipt_sha256": receipt_sha,
                "next_legal_transition": next_transition,
                "resolution_counts": evaluation["resolution_counts"],
                "scored_count": scored_count,
                "selected_source": "none",
                "source_provenance_sha256": provenance_sha,
                "tracker_sha256": tracker_sha,
                "unknown_count": 225 - scored_count,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
