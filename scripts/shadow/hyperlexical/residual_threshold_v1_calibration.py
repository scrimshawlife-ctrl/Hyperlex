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
        "magpie_km_overlap_with_development_row_id": first_account_placeholder,
    }
    return manifest, accounting
