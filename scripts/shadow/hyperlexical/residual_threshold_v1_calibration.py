"""One blind calibration draw for the frozen residual threshold.

The sample size is the historical positional prefix for this universe
(per cell = 2). It is not computed from operator labels. Operator labels
are read only after the score receipt is hashed. A failed gate is frozen.
This module does not redraw, and it does not draw a measurement surface.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

from hyperlexical.residual_threshold_v1 import (
    MIN_CALIBRATION_HIGH,
    MIN_CALIBRATION_SECONDARY,
    ALGORITHM_ID,
)

LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
HYPERLEX = Path("/home/morpheus/Hyperlex")
SOURCE = LEDGER / "operator-review/HLX-EVAL-UNBIND-SEMANTIC-EVIDENCE-SOURCE-V1-001"
SENSE = LEDGER / "operator-review/HLX-EVAL-UNBIND-SENSE-SCREEN-V1-HYPOTHESIS-001"
WORDNET = LEDGER / "acquisition/sources/wordnet-3.0/wordnet"
TRAIN = Path("/home/morpheus/hlx-private/d1-spark-tree-20260924T213846Z/morph78-train-export.jsonl")
EVENTS = LEDGER / "events.jsonl"
LEDGER_FILE = LEDGER / "ledger.json"
TRACKER = SENSE / "HYPOTHESIS.json"
EVIDENCE = SENSE / "DEVELOPMENT_EVIDENCE.json"

SAMPLING_RULE_ID = "positional_stratified_hash_prefix_v1"
PER_CELL = 2
DRAW_SEED = None
ORDERING = "normalized_text_sha256 ascending"
STRATIFICATION = "source_pos x token_count"
REPLACEMENT = "without_replacement"
SOURCE_IDENTITY = "wordnet-3.0"
AUTHORIZATION = "RESIDUAL_CALIBRATION_SURFACE_DRAW_AUTHORIZATION"

MANIFEST_FIELDS = (
    "calibration_row_id",
    "normalized_text_sha256",
    "surface",
    "pos",
    "pwn30_synset",
    "frozen_gloss",
    "source_identity",
    "draw_order",
    "draw_seed",
    "sampling_rule_id",
)

DRAW_RECEIPT = SOURCE / "RESIDUAL_THRESHOLD_V1_CALIBRATION_DRAW_RECEIPT.json"
MANIFEST_PATH = SOURCE / "RESIDUAL_THRESHOLD_V1_CALIBRATION_MANIFEST.jsonl"
ISOLATION_PATH = SOURCE / "RESIDUAL_THRESHOLD_V1_CALIBRATION_ISOLATION_REPORT.json"
RESOLUTION_PATH = SOURCE / "RESIDUAL_THRESHOLD_V1_CALIBRATION_RESOLUTION.jsonl"
SCORES_PATH = SOURCE / "RESIDUAL_THRESHOLD_V1_CALIBRATION_SCORES.jsonl"
SCORE_RECEIPT = SOURCE / "RESIDUAL_THRESHOLD_V1_CALIBRATION_SCORE_RECEIPT.json"
LABELS_PATH = SOURCE / "RESIDUAL_THRESHOLD_V1_CALIBRATION_LABELS.jsonl"
ANALYSIS_PATH = SOURCE / "RESIDUAL_THRESHOLD_V1_CALIBRATION_ANALYSIS.json"
SEARCH_PATH = SOURCE / "RESIDUAL_THRESHOLD_V1_CALIBRATION_THRESHOLD_SEARCH.json"
FROZEN_PATH = SOURCE / "RESIDUAL_THRESHOLD_V1_THRESHOLD_FROZEN.json"
FAILURE_PATH = SOURCE / "RESIDUAL_THRESHOLD_V1_CALIBRATION_FAILURE.json"

PREREGISTRATION = {
    SOURCE / "RESIDUAL_THRESHOLD_V1_PREREGISTRATION.json": "86b4cb5578fa63d3e8f4f2968ed0e32db5b5f571c9b2604e29597bce70fac5e0",
    SOURCE / "RESIDUAL_THRESHOLD_V1_ACCEPTANCE.json": "99aa20bdb046a449571f043b8ddb6c246ed610fb7c7cfc454a020a6c9464da6e",
    SOURCE / "RESIDUAL_THRESHOLD_V1_SELECTION_PROCEDURE.json": "afa2fe92e3f70756c6a6f5a2f44d1f1a82f291b58bef171db0db8cc39e13ed1a",
    SOURCE / "RESIDUAL_THRESHOLD_V1_CALIBRATION_CONTRACT.json": "99c3dc10a5ea6b6990f350163ea975f99b9c1b895504c0260952d0b67a5bd323",
    SOURCE / "RESIDUAL_THRESHOLD_V1_MEASUREMENT_CONTRACT.json": "3463caaa22f0fd45342ce9946e1669bb453f91a776a195b14d62a014f898d2c9",
    SOURCE / "RESIDUAL_THRESHOLD_V1_ARTIFACT_SCHEMA.json": "87cea8897b709c00c5917f0a00499237f3e9c8923dee974f0184bc98881fa7b4",
    SOURCE / "RESIDUAL_THRESHOLD_V1_SURFACE_ISOLATION_POLICY.json": "e24cccdd1a2db315531a98c7468c70b9751083bf2c0f3c4206cad1f6e51b3d26",
}
ANCESTORS = {
    EVIDENCE: "0e9b3c1af9dd573bf6e2034640e468e8ab9074e1e76c90cef1f39f68d607bc03",
    EVENTS: "96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c",
    LEDGER_FILE: "77e22433203879b252f7a9e309d2013d7550101d1c4a014b494d2c96df87d0e0",
    SOURCE / "RESIDUAL_CANDIDATE_SPEC.json": "39c2914e32557ffe1a456a56f8742ea4fe8f1aaec1dc1da451656cd22f0db32d",
    SOURCE / "RESIDUAL_DEVELOPMENT_SCORES.jsonl": "cea638679faeee1bc1c689823e7c0c08562c4d7ef1f8230bbbf4079239e7c3e7",
    SOURCE / "INTEGRATED_CONSTITUENT_RESOLUTION_V1.jsonl": "0f5dafc3676a4071ce8c889e58958b90203589aa3e91d78111b4e3292bdd87fb",
    SOURCE / "RESIDUAL_V1_MODEL_RESOLVED_REPLAY_SCORES.jsonl": "16c0a9eaa918ac4a6e8223cafcbf4b1918cb212769063e262cf29a279f1048f6",
    SOURCE / "RESIDUAL_V1_MODEL_RESOLVED_REPLAY_RECEIPT.json": "675b1b8b8f1b1e6f19c7d320e7b8fe516eae92b60e966afbce407c1f0482e736",
    SOURCE / "RESIDUAL_V1_MODEL_RESOLVED_DEVELOPMENT_ANALYSIS.json": "4367930648a68c2f84a1fd8e011fa07d9f3bf111303079f3ec07688f7d5425fb",
    SOURCE / "RESIDUAL_V1_MODEL_RESOLVED_CONFOUND_ANALYSIS.json": "d0f2496ca7623050eb5519969abcf7c5e2d0e23e0c1961859c40cae4dcdb7021",
    SOURCE / "RESIDUAL_V1_MODEL_RESOLVED_CANDIDATE_DECISION.json": "ed0296fe6888e7c9fe864a2c6c7ab6cecbd4f490d6b7d650e442dafc0bd0976d",
    SOURCE / "MODEL_BASED_WSD_CANDIDATE_SPEC.json": "c861ff7fff11ae6a790531267229c18d6e6e0a171a9bf6c34cfb6f7e7b14498c",
    SOURCE / "MODEL_BASED_WSD_RESOLUTION.jsonl": "ed945989cf4947ac84633ba2c4aa10c1ba381d2396da0b573a844f83ec367a18",
    SOURCE / "MODEL_BASED_WSD_READINESS_PROJECTION.json": "c75834faf4a84d36e83246244e0aa7c6c7788c3a57cfdb7f77c7628a52023328",
    SOURCE / "CONSTITUENT_SENSE_RESOLUTION_V1_SPEC.json": "176e6219ddc3127814a25d39ad26e3571817f7ea8323d685e081d2e0fd867acb",
    SOURCE / "CONSTITUENT_SENSE_RESOLUTION_V1_REPLAY.jsonl": "a0c707ab55e02f627a698c33ddc0ca398e34aa0bafc19b13e72422bc26d97d0a",
    SOURCE / "MAGPIE_CANDIDATE_DECISION.json": "6eaa968b6260946998dba13e5c423f178d3349cdfe06e5ea401717f5a9bcdd0d",
    SOURCE / "KM_CANDIDATE_DECISION.json": "93a07e3c78b53a69965497410c34ddb52c2a5d3add3fb2f3cd3fd9ca84eb3d9f",
    SOURCE / "SEMANTIC_RESIDUAL_V1_COVERAGE_LIMITATION.json": "fc8839c15a7638b2bfca1cf0548bfb4d5f433434bae0fea2944a528dd15d6142",
    SENSE / "WORDNET_STRUCTURAL_SOURCE_LIMITATION.json": "3c05cd9d6301fab0791e31b542d767cc757307cf3e304065362b479cc40e964a",
    SENSE / "CLASSIFICATION_PROCEDURE.v2.json": "3f4071640d0c9f29cf56f53969a88ec25c635444b87765e77e1b9158470e5662",
    SOURCE / "HYPOTHESIS.json": "39127a810d38ede96d7947c33dbc3e5491c9e1cc9b3f76b1064d9e0dd04a7787",
    TRACKER: "5dda813835ee11424f3d803f50ddc9eab5842cf0185f59ca396da207635a1daf",
}
OPERATOR_CLASSES = ("HIGH", "SECONDARY", "REJECT", "QUARANTINE")
JSON_SCHEMA_DOCUMENT = None


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def refuse(message: str) -> None:
    raise SystemExit(message)


def write_json(path: Path, payload: dict) -> str:
    if path.exists():
        refuse(f"refusing to rewrite {path.name}")
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_jsonl(path: Path, rows: list[dict]) -> str:
    if path.exists():
        refuse(f"refusing to rewrite {path.name}")
    text = "".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def verify_sealed(include_tracker: bool = True) -> None:
    for path, expected in PREREGISTRATION.items():
        if sha256(path) != expected:
            refuse(f"preregistration changed: {path.name}")
    for path, expected in ANCESTORS.items():
        if path == TRACKER and not include_tracker:
            continue
        if sha256(path) != expected:
            refuse(f"sealed ancestor changed: {path.name}")


def _identity_fences() -> dict:
    from hyperlexical.heldout_census import normalize_group_text
    from hyperlexical.holdout_guard import normalized_text_sha256
    from hyperlexical.unbind_screen_v4 import normalize_lexical

    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    rows = evidence["rows"]
    if len(rows) != 225:
        refuse("development evidence row count drifted")
    hashes = set()
    lexical = set()
    grouped = set()
    stored = set()
    synsets = set()
    for row in rows:
        surface = str(row["surface"])
        digest = normalized_text_sha256(surface)
        if digest != row["row_id"]:
            refuse("development row_id is not normalized_text_sha256")
        hashes.add(row["row_id"])
        lexical.add(normalize_lexical(surface))
        grouped.add(normalize_group_text(surface))
        stored.add(str(row["normalized_identity"]))
        offset = str(row.get("synset_offset") or "")
        if offset:
            synsets.add(f"{row['synset_pos']}:{offset}")
    magpie_hashes = set()
    magpie_synsets = set()
    for name in ("MAGPIE_SEMANTIC_EVIDENCE.jsonl", "KM_HYPERLEX_SEMANTIC_EVIDENCE.jsonl"):
        for row in read_jsonl(SOURCE / name):
            magpie_hashes.add(row["row_id"])
            for key in ("synset", "hyperlex_synset"):
                value = row.get(key)
                if value:
                    magpie_synsets.add(str(value))
    reserves = [
        path
        for path in (LEDGER / "operator-review").rglob("*")
        if path.is_file() and "measurement" in path.name.lower() and "reserve" in path.name.lower()
    ]
    if reserves:
        refuse(f"unexpected measurement reserve: {reserves}")
    return {
        "development_hashes": hashes,
        "development_lexical": lexical,
        "development_grouped": grouped,
        "development_stored_identity": stored,
        "development_synsets": synsets,
        "magpie_km_hashes": magpie_hashes,
        "magpie_km_synsets": magpie_synsets,
        "measurement_reserve_hashes": set(),
        "measurement_reserve_files": 0,
    }


def _bound_glosses(pending: list[tuple[str, str]]) -> dict[tuple[str, str], str]:
    """One scan per POS. The gloss is the same first clause gloss_for stores."""
    from hyperlexical.unbind_screen_v3 import FILES, load_glosses

    found = {}
    wanted: dict[str, set[str]] = {}
    for pos, offset in pending:
        wanted.setdefault(pos, set()).add(offset)
    for pos, offsets in wanted.items():
        loaded = load_glosses(WORDNET / FILES[pos][1], offsets)
        for offset, gloss in loaded.items():
            found[(pos, offset)] = gloss
    return found


def draw_calibration() -> tuple[list[dict], dict]:
    """Enumerate, fence, and draw. This function does not read operator labels."""
    from hyperlexical.clean_unbind import (
        WORDNET_LICENSE,
        gate_rows,
        load_jsonl,
        read_wordnet_index,
        rows_from_wordnet_atoms,
    )
    from hyperlexical.heldout_census import normalize_group_text
    from hyperlexical.holdout_guard import normalized_text_sha256
    from hyperlexical.identity_ledger import IdentityLedger
    from hyperlexical.unbind_screen_v3 import load_indexes
    from hyperlexical.unbind_screen_v4 import normalize_lexical

    fences = _identity_fences()
    atoms = read_wordnet_index(WORDNET)
    generated = rows_from_wordnet_atoms(atoms, license=WORDNET_LICENSE)
    admissible, rejections, _account = gate_rows(
        generated,
        train_rows=load_jsonl(TRAIN),
        ledger=IdentityLedger.load(LEDGER),
        require_settlement=False,
    )
    from hyperlexical.clean_unbind import reason_counts

    exclusion = Counter()
    exclusion["wordnet_rows"] = len(generated)
    exclusion["gate_rejected"] = len(rejections)
    for reason, count in sorted(reason_counts(rejections).items()):
        exclusion[f"gate_{reason}"] = count
    positional = []
    for row in admissible:
        if row.get("role_scheme") != "positional":
            exclusion["not_positional"] += 1
            continue
        positional.append(row)
    exclusion["admissible_positional"] = len(positional)
    kept = []
    magpie_overlap_with_development = 0
    for row in positional:
        surface = str(row.get("text") or "")
        digest = normalized_text_sha256(surface)
        lexical = normalize_lexical(surface)
        grouped = normalize_group_text(surface)
        if digest in fences["magpie_km_hashes"] and digest in fences["development_hashes"]:
            magpie_overlap_with_development += 1
        if digest in fences["development_hashes"]:
            exclusion["development_row_id"] += 1
            continue
        if (
            lexical in fences["development_lexical"]
            or grouped in fences["development_grouped"]
            or grouped in fences["development_stored_identity"]
            or lexical in fences["development_stored_identity"]
        ):
            exclusion["development_normalized_text"] += 1
            continue
        if digest in fences["magpie_km_hashes"] or grouped in fences["development_grouped"]:
            exclusion["magpie_km_overlap"] += 1
            continue
        if digest in fences["measurement_reserve_hashes"]:
            exclusion["measurement_reserve"] += 1
            continue
        kept.append(row)
    best: dict[str, dict] = {}
    for row in kept:
        lexical = normalize_lexical(str(row.get("text") or ""))
        digest = normalized_text_sha256(str(row.get("text") or ""))
        current = best.get(lexical)
        if current is None:
            best[lexical] = row
            continue
        current_digest = normalized_text_sha256(str(current.get("text") or ""))
        if digest < current_digest:
            best[lexical] = row
        exclusion["duplicate_normalized_identity"] += 1
    indexes = load_indexes(str(WORDNET))
    pending = []
    for row in best.values():
        surface = str(row["text"])
        pos = str(row["source_pos"])
        fillers = [str(tok) for tok in row.get("fillers") or []]
        if " ".join(fillers) != surface:
            refuse("positional tokens do not reconstruct the surface")
        offset = (indexes.get(pos) or {}).get(surface.replace(" ", "_"))
        if not offset:
            exclusion["missing_or_unbound_synset"] += 1
            continue
        pending.append((surface, pos, offset, fillers))
    glosses = _bound_glosses([(pos, offset) for _surface, pos, offset, _fillers in pending])
    synset_best: dict[str, dict] = {}
    for surface, pos, offset, fillers in pending:
        gloss = glosses.get((pos, offset), "")
        synset = f"{pos}:{offset}"
        if not gloss:
            exclusion["missing_or_unbound_synset"] += 1
            continue
        if synset in fences["development_synsets"] or synset in fences["magpie_km_synsets"]:
            exclusion["development_synset"] += 1
            continue
        item = {
            "fillers": fillers,
            "frozen_gloss": gloss,
            "pos": pos,
            "pwn30_synset": synset,
            "surface": surface,
            "normalized_text_sha256": normalized_text_sha256(surface),
        }
        current = synset_best.get(synset)
        if current is None or item["normalized_text_sha256"] < current["normalized_text_sha256"]:
            if current is not None:
                exclusion["duplicate_synset"] += 1
            synset_best[synset] = item
        else:
            exclusion["duplicate_synset"] += 1
    bound_rows = list(synset_best.values())
    cells: dict[tuple[str, int], list[dict]] = {}
    for item in bound_rows:
        cells.setdefault((item["pos"], len(item["fillers"])), []).append(item)
    picked = []
    strata = []
    for key in sorted(cells):
        group = sorted(cells[key], key=lambda item: item["normalized_text_sha256"])
        taken = group[:PER_CELL]
        picked.extend(taken)
        strata.append(
            {
                "available": len(group),
                "source_pos": key[0],
                "taken": len(taken),
                "token_count": key[1],
            }
        )
    if not picked:
        refuse("calibration draw is empty")
    manifest = []
    for draw_order, item in enumerate(picked, start=1):
        manifest.append(
            {
                "calibration_row_id": item["normalized_text_sha256"],
                "draw_order": draw_order,
                "draw_seed": DRAW_SEED,
                "frozen_gloss": item["frozen_gloss"],
                "normalized_text_sha256": item["normalized_text_sha256"],
                "pos": item["pos"],
                "pwn30_synset": item["pwn30_synset"],
                "sampling_rule_id": SAMPLING_RULE_ID,
                "source_identity": SOURCE_IDENTITY,
                "surface": item["surface"],
            }
        )
    accounting = {
        "eligible_before_draw": len(bound_rows),
        "exclusion_counts": dict(sorted(exclusion.items())),
        "magpie_km_overlap_with_development_row_id": magpie_overlap_with_development,
        "measurement_reserve_files": 0,
        "strata": strata,
    }
    return manifest, accounting


def _isolation(manifest: list[dict]) -> dict:
    fences = _identity_fences()
    from hyperlexical.heldout_census import normalize_group_text
    from hyperlexical.unbind_screen_v4 import normalize_lexical

    hashes = [row["normalized_text_sha256"] for row in manifest]
    synsets = [row["pwn30_synset"] for row in manifest]
    overlap = {
        "development_normalized_text": 0,
        "development_row_id": len(set(hashes) & fences["development_hashes"]),
        "development_synset": len(set(synsets) & fences["development_synsets"]),
        "internal_duplicate_row_id": len(hashes) - len(set(hashes)),
        "internal_duplicate_synset": len(synsets) - len(set(synsets)),
        "magpie_km_row_id": len(set(hashes) & fences["magpie_km_hashes"]),
        "magpie_km_synset": len(set(synsets) & fences["magpie_km_synsets"]),
        "measurement_reserve": 0,
    }
    for row in manifest:
        lexical = normalize_lexical(row["surface"])
        grouped = normalize_group_text(row["surface"])
        if (
            lexical in fences["development_lexical"]
            or grouped in fences["development_grouped"]
            or grouped in fences["development_stored_identity"]
        ):
            overlap["development_normalized_text"] += 1
        if set(row) != set(MANIFEST_FIELDS):
            refuse("manifest row carries a field outside the pre-score contract")
        if "operator_bucket" in row:
            refuse("manifest contains an operator label")
    overlap["total"] = sum(overlap.values())
    return overlap


def freeze_draw() -> dict:
    if MANIFEST_PATH.exists() or DRAW_RECEIPT.exists() or ISOLATION_PATH.exists():
        refuse("calibration draw already exists; redraw is not authorized")
    verify_sealed()
    print("draw pass 1", file=sys.stderr, flush=True)
    first_manifest, first_account = draw_calibration()
    print("draw pass 2", file=sys.stderr, flush=True)
    second_manifest, second_account = draw_calibration()
    if first_manifest != second_manifest or first_account != second_account:
        _write_failure_early("NOT_DETERMINISTIC", "draw_reconstruction")
    from hyperlexical.unbind_screen_v3 import gloss_for

    for row in first_manifest:
        bound_pos, gloss = gloss_for(row["surface"], row["pos"], str(WORDNET))
        if bound_pos != row["pos"] or gloss != row["frozen_gloss"]:
            refuse(f"frozen gloss drifted from gloss_for: {row['surface']}")
    overlap = _isolation(first_manifest)
    if overlap["total"] != 0:
        refuse(f"calibration surface leaks development material: {overlap}")
    manifest_sha = write_jsonl(MANIFEST_PATH, first_manifest)
    isolation = {
        "admitted": 0,
        "authorization": AUTHORIZATION,
        "gold": 0,
        "json_schema_document": JSON_SCHEMA_DOCUMENT,
        "json_schema_exists": False,
        "manifest_sha256": manifest_sha,
        "measurement_surface_drawn": False,
        "operator_labels_consulted": False,
        "overlap": overlap,
        "schema": "hyperlex.residual_threshold_v1_calibration_isolation.v1",
        "scores_consulted": False,
        "selected_source": "none",
        "select_005_authorized": False,
        "settled": 0,
    }
    isolation_sha = write_json(ISOLATION_PATH, isolation)
    receipt = {
        "admitted": 0,
        "authorization": AUTHORIZATION,
        "calibration_surface_drawn": True,
        "calibration_surface_frozen": True,
        "determinism": "IDENTICAL",
        "draw_passes": 2,
        "draw_seed": DRAW_SEED,
        "eligible_universe_before_draw": first_account["eligible_before_draw"],
        "exclusion_counts": first_account["exclusion_counts"],
        "gold": 0,
        "isolation_sha256": isolation_sha,
        "json_schema_document": JSON_SCHEMA_DOCUMENT,
        "json_schema_exists": False,
        "magpie_km_overlap_with_development_row_id": first_account["magpie_km_overlap_with_development_row_id"],
        "manifest_row_count": len(first_manifest),
        "manifest_sha256": manifest_sha,
        "measurement_reserve_files": 0,
        "measurement_surface_drawn": False,
        "operator_labels_consulted": False,
        "ordering": ORDERING,
        "per_cell": PER_CELL,
        "redraw_authorized": False,
        "replacement": REPLACEMENT,
        "sample_size_source": "historical positional draw_measurement default; not derived from operator labels",
        "sampling_rule_id": SAMPLING_RULE_ID,
        "schema": "hyperlex.residual_threshold_v1_calibration_draw_receipt.v1",
        "scores_consulted": False,
        "select_005_authorized": False,
        "selected_source": "none",
        "settled": 0,
        "strata": first_account["strata"],
        "stratification": STRATIFICATION,
        "threshold_frozen": False,
        "threshold_value": None,
    }
    receipt_sha = write_json(DRAW_RECEIPT, receipt)
    receipt["draw_receipt_sha256"] = receipt_sha
    return receipt


def _write_failure_early(state: str, gate: str) -> None:
    if FAILURE_PATH.exists():
        refuse(state)
    payload = {
        "failure_state": state,
        "failed_gate": gate,
        "json_schema_document": JSON_SCHEMA_DOCUMENT,
        "observed_confounds": None,
        "observed_direction": None,
        "observed_support": None,
        "observed_threshold_candidate_count": None,
        "schema": "hyperlex.residual_threshold_v1_calibration_failure.v1",
        "threshold_frozen": False,
        "threshold_value": None,
    }
    write_json(FAILURE_PATH, payload)
    refuse(state)


def _sealed_rows(manifest: list[dict]) -> list[dict]:
    rows = []
    for row in manifest:
        pos, offset = row["pwn30_synset"].split(":", 1)
        rows.append(
            {
                "gloss": row["frozen_gloss"],
                "pos": row["pos"],
                "row_id": row["calibration_row_id"],
                "sense_class": None,
                "surface": row["surface"],
                "synset_offset": offset,
                "synset_pos": pos,
            }
        )
    return rows


def _tier3_pool(resolver_rows: list[dict], by_id: dict, exceptions: dict, sense_index: dict) -> list[dict]:
    from hyperlexical.model_based_wsd_candidate_v1 import candidate_gloss_text, gloss_lemma, quoted_context
    from hyperlexical.model_based_wsd_candidate_v1_replay import sense_keys_for

    pool = []
    for row in resolver_rows:
        if row["constituent_index"] is None:
            continue
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
    return pool


def resolve_and_score() -> dict:
    if not MANIFEST_PATH.exists() or not DRAW_RECEIPT.exists():
        refuse("manifest was not frozen before resolution")
    if SCORES_PATH.exists() or SCORE_RECEIPT.exists():
        refuse("scores already exist")
    verify_sealed()
    manifest = read_jsonl(MANIFEST_PATH)
    if sha256(MANIFEST_PATH) != json.loads(DRAW_RECEIPT.read_text(encoding="utf-8"))["manifest_sha256"]:
        refuse("manifest hash does not match the draw receipt")
    from hyperlexical.constituent_sense_resolution_v1_replay import (
        PROCEDURE_PATH,
        SPEC_PATH,
        build_catalog,
        resolve_once,
    )
    from hyperlexical.model_based_wsd_candidate_v1_replay import (
        import_runtime,
        infer_pass,
        load_sense_index,
        resolution_rows,
    )
    from hyperlexical.residual_model_resolved_replay_v1 import TIER3_GLOSSBERT
    from hyperlexical.residual_model_resolved_replay_v1_replay import (
        RESIDUAL_SPEC_SHA,
        apply_overflow,
        assemble_scores,
        build_integrated,
        encode_needed,
        prepare_jobs,
        public_integrated,
        score_jobs,
    )
    from hyperlexical.semantic_compositionality_residual_replay import build_indexes, load_encoder
    from hyperlexical.unbind_sense_screen_v1 import load_exceptions

    sealed = _sealed_rows(manifest)
    print("resolver catalog", file=sys.stderr, flush=True)
    by_id, index = build_catalog()
    exceptions = load_exceptions(WORDNET)
    spec_sha = sha256(SPEC_PATH)
    procedure_sha = sha256(PROCEDURE_PATH)
    wsd_spec_sha = sha256(SOURCE / "MODEL_BASED_WSD_CANDIDATE_SPEC.json")
    print("resolver pass 1", file=sys.stderr, flush=True)
    resolved_first = resolve_once(sealed, by_id, index, exceptions, spec_sha, procedure_sha)
    print("resolver pass 2", file=sys.stderr, flush=True)
    resolved_second = resolve_once(sealed, by_id, index, exceptions, spec_sha, procedure_sha)
    if resolved_first != resolved_second:
        _write_failure_early("NOT_DETERMINISTIC", "integrated_resolution")
    sense_index = load_sense_index(WORDNET / "index.sense")
    pool_first = _tier3_pool(resolved_first, by_id, exceptions, sense_index)
    pool_second = _tier3_pool(resolved_second, by_id, exceptions, sense_index)
    if pool_first != pool_second:
        _write_failure_early("NOT_DETERMINISTIC", "tier3_pool")
    model_rows: list[dict] = []
    if pool_first:
        print(f"glossbert pool {len(pool_first)}", file=sys.stderr, flush=True)
        torch, tokenizer, model = import_runtime()
        raw_first = infer_pass(torch, tokenizer, model, pool_first, wsd_spec_sha)
        raw_second = infer_pass(torch, tokenizer, model, pool_second, wsd_spec_sha)
        if raw_first != raw_second:
            _write_failure_early("NOT_DETERMINISTIC", "glossbert_scores")
        model_first = resolution_rows(pool_first, raw_first)
        model_second = resolution_rows(pool_second, raw_second)
        if model_first != model_second:
            _write_failure_early("NOT_DETERMINISTIC", "glossbert_resolution")
        model_rows = model_first
    integrated_first, by_parent_first = build_integrated(resolved_first, model_rows, exceptions, sense_index)
    integrated_second, _by_parent_second = build_integrated(resolved_second, model_rows, exceptions, sense_index)
    if integrated_first != integrated_second:
        _write_failure_early("NOT_DETERMINISTIC", "integrated_resolution")
    public_rows = [public_integrated(item) for item in integrated_first]
    if RESOLUTION_PATH.exists():
        if read_jsonl(RESOLUTION_PATH) != public_rows:
            _write_failure_early("NOT_DETERMINISTIC", "integrated_resolution")
        resolution_sha = sha256(RESOLUTION_PATH)
    else:
        resolution_sha = write_jsonl(RESOLUTION_PATH, public_rows)
    residual_by_id, _residual_index = build_indexes()
    # prepare_jobs uses constituent_representation from the replay module, which
    # closes over the residual index built above. Rebind by calling prepare_jobs
    # after the replay's own index loader is the frozen path: prepare_jobs calls
    # constituent_representation, and that function expects by_id from build_indexes.
    jobs, unknown = prepare_jobs(sealed, by_parent_first, residual_by_id, exceptions, {
        (row["parent_row_id"], row["constituent_index"]): row for row in model_rows
    })
    encoder = load_encoder()
    kept, overflow = apply_overflow(encoder, jobs)
    print("residual encode pass 1", file=sys.stderr, flush=True)
    vectors_first = encode_needed(encoder, kept)
    scored_first = score_jobs(kept, vectors_first, resolution_sha)
    print("residual encode pass 2", file=sys.stderr, flush=True)
    vectors_second = encode_needed(encoder, kept)
    scored_second = score_jobs(kept, vectors_second, resolution_sha)
    if vectors_first != vectors_second or scored_first != scored_second:
        RESOLUTION_PATH.unlink()
        _write_failure_early("NOT_DETERMINISTIC", "residual_scores")
    scores = assemble_scores(sealed, scored_first, unknown, overflow)
    for row in scores:
        if row["score_status"] == "SCORED" and "constituent_resolution_tiers" in row:
            row["uses_tier3"] = TIER3_GLOSSBERT in row["constituent_resolution_tiers"]
    if any(row.get("operator_bucket") for row in scores):
        refuse("score artifact contains an operator label")
    score_sha = write_jsonl(SCORES_PATH, scores)
    receipt = {
        "admitted": 0,
        "determinism": "IDENTICAL",
        "gold": 0,
        "integrated_resolution_sha256": resolution_sha,
        "json_schema_document": JSON_SCHEMA_DOCUMENT,
        "json_schema_exists": False,
        "manifest_sha256": sha256(MANIFEST_PATH),
        "operator_labels_joined": False,
        "ready_rows": sum(1 for row in scores if row["score_status"] == "SCORED"),
        "residual_candidate_spec_sha256": RESIDUAL_SPEC_SHA,
        "schema": "hyperlex.residual_threshold_v1_calibration_score_receipt.v1",
        "score_passes": 2,
        "score_sha256": score_sha,
        "selected_source": "none",
        "settled": 0,
        "tier3_pool": len(pool_first),
        "unknown_rows": sum(1 for row in scores if row["score_status"] != "SCORED"),
    }
    receipt_sha = write_json(SCORE_RECEIPT, receipt)
    if json.loads(SCORE_RECEIPT.read_text(encoding="utf-8"))["operator_labels_joined"] is not False:
        refuse("score receipt joined labels early")
    receipt["score_receipt_sha256"] = receipt_sha
    return receipt


def _label_index() -> dict[str, str]:
    found: dict[str, str] = {}

    def add(row_id: str, bucket: str) -> None:
        prior = found.get(row_id)
        if prior is not None and prior != bucket:
            refuse(f"operator labels disagree for {row_id}")
        found[row_id] = bucket

    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    for row in evidence["rows"]:
        add(row["row_id"], row["operator_bucket"])
    root = LEDGER / "operator-review"
    for path in sorted(root.rglob("*labels*.jsonl")):
        for row in read_jsonl(path):
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
        if bucket is None:
            unlabeled[status] += 1
            continue
        if status == "SCORED":
            ready[bucket] += 1
        else:
            unknown[bucket] += 1
    return {
        "ready": {name: ready[name] for name in OPERATOR_CLASSES},
        "unlabeled_scored": unlabeled["SCORED"],
        "unlabeled_unknown": unlabeled["UNKNOWN"],
        "unknown_by_class": {name: unknown[name] for name in OPERATOR_CLASSES},
    }


def join_and_judge() -> dict:
    if not SCORE_RECEIPT.exists() or not SCORES_PATH.exists():
        refuse("scores were not frozen before the label join")
    if LABELS_PATH.exists() or ANALYSIS_PATH.exists() or SEARCH_PATH.exists():
        refuse("label join artifacts already exist")
    if FROZEN_PATH.exists() or FAILURE_PATH.exists():
        refuse("threshold outcome already exists")
    receipt = json.loads(SCORE_RECEIPT.read_text(encoding="utf-8"))
    if receipt["operator_labels_joined"] is not False:
        refuse("score receipt does not record a pre-label freeze")
    if sha256(SCORES_PATH) != receipt["score_sha256"]:
        refuse("score hash drifted before the label join")
    verify_sealed()
    labels_by_id = _label_index()
    scores = read_jsonl(SCORES_PATH)
    manifest = {row["calibration_row_id"]: row for row in read_jsonl(MANIFEST_PATH)}
    joined = []
    for score in scores:
        row_id = score["row_id"]
        manifest_row = manifest[row_id]
        bucket = labels_by_id.get(row_id)
        joined.append(
            {
                "calibration_row_id": row_id,
                "development_row": False,
                "draw_order": manifest_row["draw_order"],
                "operator_bucket": bucket,
                "operator_label_present": bucket is not None,
                "pos": score.get("pos", manifest_row["pos"]),
                "residual_score": score.get("residual_score"),
                "score_status": score["score_status"],
                "surface": manifest_row["surface"],
                "uses_tier3": score.get("uses_tier3"),
            }
        )
    label_rows = [
        {
            "calibration_row_id": row["calibration_row_id"],
            "operator_bucket": row["operator_bucket"],
            "operator_label_present": row["operator_label_present"],
            "score_status": row["score_status"],
        }
        for row in joined
    ]
    label_sha = write_jsonl(LABELS_PATH, label_rows)
    support = _support(joined)
    ready_high = support["ready"]["HIGH"]
    ready_secondary = support["ready"]["SECONDARY"]
    analysis = {
        "admitted": 0,
        "confound_result": "NOT_RUN",
        "direction_result": "NOT_RUN",
        "gold": 0,
        "json_schema_document": JSON_SCHEMA_DOCUMENT,
        "json_schema_exists": False,
        "label_sha256": label_sha,
        "measurement_surface_drawn": False,
        "schema": "hyperlex.residual_threshold_v1_calibration_analysis.v1",
        "score_receipt_sha256": sha256(SCORE_RECEIPT),
        "score_sha256": sha256(SCORES_PATH),
        "select_005_authorized": False,
        "selected_source": "none",
        "settled": 0,
        "support": support,
        "support_gate": {
            "minimum_ready_high": MIN_CALIBRATION_HIGH,
            "minimum_ready_secondary": MIN_CALIBRATION_SECONDARY,
            "passed": ready_high >= MIN_CALIBRATION_HIGH and ready_secondary >= MIN_CALIBRATION_SECONDARY,
        },
    }
    if not analysis["support_gate"]["passed"]:
        analysis["calibration_state"] = "CALIBRATION_INSUFFICIENT_SUPPORT"
        analysis_sha = write_json(ANALYSIS_PATH, analysis)
        search = {
            "candidate_count": None,
            "candidates_evaluated": False,
            "gate_pass_counts": None,
            "json_schema_document": JSON_SCHEMA_DOCUMENT,
            "reason": "CALIBRATION_INSUFFICIENT_SUPPORT",
            "schema": "hyperlex.residual_threshold_v1_calibration_threshold_search.v1",
            "search_executed": False,
            "selected_threshold": None,
        }
        search_sha = write_json(SEARCH_PATH, search)
        failure = {
            "analysis_sha256": analysis_sha,
            "failure_state": "CALIBRATION_INSUFFICIENT_SUPPORT",
            "failed_gate": "support",
            "json_schema_document": JSON_SCHEMA_DOCUMENT,
            "json_schema_exists": False,
            "label_sha256": label_sha,
            "observed_confounds": None,
            "observed_direction": None,
            "observed_support": support,
            "observed_threshold_candidate_count": None,
            "schema": "hyperlex.residual_threshold_v1_calibration_failure.v1",
            "search_sha256": search_sha,
            "threshold_frozen": False,
            "threshold_value": None,
        }
        failure_sha = write_json(FAILURE_PATH, failure)
        return _finish_tracker(failure["failure_state"], None, failure_sha, {
            "analysis": analysis_sha,
            "failure": failure_sha,
            "labels": label_sha,
            "search": search_sha,
        })
    return _select(joined, analysis, label_sha)


def _select(joined: list[dict], analysis: dict, label_sha: str) -> dict:
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
        analysis["calibration_state"] = "NOT_DETERMINISTIC"
        analysis_sha = write_json(ANALYSIS_PATH, analysis)
        failure = {
            "analysis_sha256": analysis_sha,
            "failure_state": "NOT_DETERMINISTIC",
            "failed_gate": "threshold_selection",
            "json_schema_document": JSON_SCHEMA_DOCUMENT,
            "observed_confounds": None,
            "observed_direction": None,
            "observed_support": analysis["support"],
            "observed_threshold_candidate_count": None,
            "schema": "hyperlex.residual_threshold_v1_calibration_failure.v1",
            "threshold_frozen": False,
            "threshold_value": None,
        }
        failure_sha = write_json(FAILURE_PATH, failure)
        return _finish_tracker("NOT_DETERMINISTIC", None, failure_sha, {"analysis": analysis_sha, "failure": failure_sha, "labels": label_sha})
    state = first["calibration_state"]
    analysis["calibration_state"] = state
    analysis["direction_result"] = first.get("direction", "NOT_RUN")
    analysis["confound_result"] = first.get("confound", "NOT_RUN")
    analysis["selection"] = first
    analysis_sha = write_json(ANALYSIS_PATH, analysis)
    search, search_sha = _search_artifact(selectable, first)
    if state != "THRESHOLD_FROZEN":
        failure = {
            "analysis_sha256": analysis_sha,
            "failure_state": state,
            "failed_gate": _failed_gate(state),
            "json_schema_document": JSON_SCHEMA_DOCUMENT,
            "json_schema_exists": False,
            "label_sha256": label_sha,
            "observed_confounds": first.get("confound"),
            "observed_direction": first.get("direction"),
            "observed_support": analysis["support"],
            "observed_threshold_candidate_count": search["candidate_count"],
            "schema": "hyperlex.residual_threshold_v1_calibration_failure.v1",
            "search_sha256": search_sha,
            "threshold_frozen": False,
            "threshold_value": None,
        }
        failure_sha = write_json(FAILURE_PATH, failure)
        return _finish_tracker(state, None, failure_sha, {
            "analysis": analysis_sha,
            "failure": failure_sha,
            "labels": label_sha,
            "search": search_sha,
        })
    metrics = first["selection_metrics"]
    frozen = {
        "algorithm_id": ALGORITHM_ID,
        "calibration_label_hash": label_sha,
        "calibration_manifest_hash": sha256(MANIFEST_PATH),
        "calibration_resolution_hash": sha256(RESOLUTION_PATH),
        "calibration_score_hash": sha256(SCORES_PATH),
        "confound_result": first.get("confound"),
        "direction_result": first.get("direction"),
        "false_high": metrics["false_high"],
        "high_recall": metrics["high_recall"],
        "json_schema_document": JSON_SCHEMA_DOCUMENT,
        "json_schema_exists": False,
        "leave_one_out_result": "PASS",
        "measurement_surface_drawn": False,
        "precision": metrics["precision"],
        "predicted_yes_support": metrics["predicted_yes_support"],
        "ready_quarantine_yes": metrics["quarantine_predicted_yes"],
        "ready_reject_yes": metrics["reject_predicted_yes"],
        "residual_candidate_spec_hash": json.loads(SCORE_RECEIPT.read_text(encoding="utf-8"))["residual_candidate_spec_sha256"],
        "resolver_stack_hashes": {
            "constituent_resolution_replay_sha256": ANCESTORS[SOURCE / "CONSTITUENT_SENSE_RESOLUTION_V1_REPLAY.jsonl"],
            "constituent_resolution_spec_sha256": ANCESTORS[SOURCE / "CONSTITUENT_SENSE_RESOLUTION_V1_SPEC.json"],
            "glossbert_resolution_sha256": ANCESTORS[SOURCE / "MODEL_BASED_WSD_RESOLUTION.jsonl"],
            "glossbert_spec_sha256": ANCESTORS[SOURCE / "MODEL_BASED_WSD_CANDIDATE_SPEC.json"],
        },
        "runtime_integration": False,
        "schema": "hyperlex.residual_threshold_v1_threshold_frozen.v1",
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
    frozen_sha = write_json(FROZEN_PATH, frozen)
    return _finish_tracker("THRESHOLD_FROZEN", first["threshold_value"], frozen_sha, {
        "analysis": analysis_sha,
        "labels": label_sha,
        "search": search_sha,
        "threshold": frozen_sha,
    })


def _failed_gate(state: str) -> str:
    return {
        "CALIBRATION_INSUFFICIENT_SUPPORT": "support",
        "NO_DIRECTIONAL_SIGNAL": "direction",
        "CALIBRATION_CONFOUND_REVIEW": "confound",
        "NO_THRESHOLD_PASSES_PRECISION_GATE": "precision_gate",
        "NOT_DETERMINISTIC": "determinism",
    }[state]


def _search_artifact(selectable: list[dict], selection: dict) -> tuple[dict, str]:
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

    if selection["calibration_state"] in {"CALIBRATION_INSUFFICIENT_SUPPORT", "NO_DIRECTIONAL_SIGNAL", "CALIBRATION_CONFOUND_REVIEW"}:
        payload = {
            "candidate_count": None,
            "candidates_evaluated": False,
            "gate_pass_counts": None,
            "json_schema_document": JSON_SCHEMA_DOCUMENT,
            "reason": selection["calibration_state"],
            "schema": "hyperlex.residual_threshold_v1_calibration_threshold_search.v1",
            "search_executed": False,
            "selected_threshold": None,
        }
        return payload, write_json(SEARCH_PATH, payload)
    ready = _ready_rows(selectable)
    comparison = [row for row in ready if row["operator_bucket"] in {"HIGH", "SECONDARY"}]
    candidates = _candidate_thresholds(ready)
    counts = Counter()
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
    payload = {
        "candidate_count": len(candidates),
        "candidates_evaluated": True,
        "gate_pass_counts": dict(sorted(counts.items())),
        "json_schema_document": JSON_SCHEMA_DOCUMENT,
        "schema": "hyperlex.residual_threshold_v1_calibration_threshold_search.v1",
        "search_executed": True,
        "selected_threshold": selected,
        "selection_algorithm_id": ALGORITHM_ID,
    }
    return payload, write_json(SEARCH_PATH, payload)


def _finish_tracker(state: str, threshold_value, outcome_sha: str, hashes: dict) -> dict:
    verify_sealed()
    tracker = json.loads(TRACKER.read_text(encoding="utf-8"))
    prior = sha256(TRACKER)
    if prior != ANCESTORS[TRACKER]:
        refuse("tracker hash drifted before the calibration update")
    tracker["previous_tracker_sha256"] = prior
    tracker["residual_threshold_state"] = state
    tracker["residual_threshold_value"] = threshold_value
    tracker["residual_threshold_frozen"] = state == "THRESHOLD_FROZEN"
    tracker["residual_threshold_calibration_surface_drawn"] = True
    tracker["residual_threshold_calibration_surface_frozen"] = True
    tracker["residual_threshold_measurement_surface_drawn"] = False
    tracker["residual_threshold_redraw_authorized"] = False
    tracker["measurement_sample_drawn"] = False
    tracker["measurement_eligible"] = False
    tracker["selected_source"] = "none"
    tracker["select_authorized"] = False
    tracker["admitted"] = 0
    tracker["settled"] = 0
    tracker["gold"] = 0
    tracker["next_legal_transition"] = "NONE"
    tracker["next_transition_authorized"] = False
    tracker["residual_threshold_json_schema_document"] = None
    tracker["residual_threshold_calibration_draw_receipt_sha256"] = sha256(DRAW_RECEIPT)
    tracker["residual_threshold_calibration_manifest_sha256"] = sha256(MANIFEST_PATH)
    tracker["residual_threshold_calibration_isolation_sha256"] = sha256(ISOLATION_PATH)
    tracker["residual_threshold_calibration_resolution_sha256"] = sha256(RESOLUTION_PATH)
    tracker["residual_threshold_calibration_scores_sha256"] = sha256(SCORES_PATH)
    tracker["residual_threshold_calibration_score_receipt_sha256"] = sha256(SCORE_RECEIPT)
    tracker["residual_threshold_calibration_labels_sha256"] = hashes["labels"]
    tracker["residual_threshold_calibration_analysis_sha256"] = hashes["analysis"]
    if "search" in hashes:
        tracker["residual_threshold_calibration_search_sha256"] = hashes["search"]
    if state == "THRESHOLD_FROZEN":
        tracker["residual_threshold_frozen_sha256"] = outcome_sha
    else:
        tracker["residual_threshold_calibration_failure_sha256"] = outcome_sha
    text = json.dumps(tracker, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    TRACKER.write_text(text, encoding="utf-8")
    TRACKER.chmod(0o600)
    verify_sealed(include_tracker=False)
    if sha256(EVENTS) != ANCESTORS[EVENTS] or sha256(LEDGER_FILE) != ANCESTORS[LEDGER_FILE]:
        refuse("events or ledger changed")
    report = {
        "determinism": "IDENTICAL",
        "hashes": {key: value for key, value in hashes.items()},
        "outcome_sha256": outcome_sha,
        "state": state,
        "threshold_value": threshold_value,
        "tracker_sha256": sha256(TRACKER),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


def main() -> None:
    os.umask(0o077)
    if not MANIFEST_PATH.exists():
        freeze_draw()
    if not SCORES_PATH.exists():
        resolve_and_score()
    if not FAILURE_PATH.exists() and not FROZEN_PATH.exists():
        join_and_judge()


if __name__ == "__main__":
    main()
