"""One-pass dual-surface draw for residual threshold v2.

The frozen walk emits round-robin across POS x token-count cells.
The first calibration quota of emissions is CALIBRATION_V2.
The same walk continues for the measurement quota.
There is no RNG. Operator labels are not loaded. Nothing is resolved.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from hyperlexical.residual_threshold_v2 import (
    SAMPLING_RULE_ID,
    calibration_draw_size,
    measurement_draw_size,
)

LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
SOURCE = LEDGER / "operator-review/HLX-EVAL-UNBIND-SEMANTIC-EVIDENCE-SOURCE-V1-001"
SENSE = LEDGER / "operator-review/HLX-EVAL-UNBIND-SENSE-SCREEN-V1-HYPOTHESIS-001"
WORDNET = LEDGER / "acquisition/sources/wordnet-3.0/wordnet"
TRAIN = Path("/home/morpheus/hlx-private/d1-spark-tree-20260924T213846Z/morph78-train-export.jsonl")
EVENTS = LEDGER / "events.jsonl"
LEDGER_FILE = LEDGER / "ledger.json"
TRACKER = SENSE / "HYPOTHESIS.json"
EVIDENCE = SENSE / "DEVELOPMENT_EVIDENCE.json"
PROBE = LEDGER / "operator-review/HLX-EVAL-UNBIND-SCREEN-V5-HYPOTHESIS-001/PROBE_SURFACES.json"
V1_MANIFEST = SOURCE / "RESIDUAL_THRESHOLD_V1_CALIBRATION_MANIFEST.jsonl"

CALIBRATION_MANIFEST = SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_MANIFEST.jsonl"
MEASUREMENT_MANIFEST = SOURCE / "RESIDUAL_THRESHOLD_V2_MEASUREMENT_MANIFEST.jsonl"
DRAW_RECEIPT = SOURCE / "RESIDUAL_THRESHOLD_V2_SURFACE_DRAW_RECEIPT.json"
ISOLATION_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_SURFACE_ISOLATION_REPORT.json"
DISTRIBUTION_PATH = SOURCE / "RESIDUAL_THRESHOLD_V2_SURFACE_DISTRIBUTION_REPORT.json"

AUTHORIZATION = "THRESHOLD_V2_SURFACE_DRAW_AUTHORIZATION"
NEXT_TRANSITION = "THRESHOLD_V2_CALIBRATION_EXECUTION_AUTHORIZATION"
SOURCE_IDENTITY = "wordnet-3.0"
STATE_FROZEN = "SURFACES_FROZEN"
STATE_UNFILLED = "SURFACE_QUOTA_UNFILLED"
STATE_NOT_DETERMINISTIC = "NOT_DETERMINISTIC"
MEASUREMENT_STATE = "SEALED"

MANIFEST_FIELDS = (
    "allocation_rule_id",
    "frozen_gloss",
    "global_draw_order",
    "normalized_text_sha256",
    "pos",
    "pwn30_synset",
    "row_id",
    "source_identity",
    "stratum_id",
    "surface",
    "surface_role",
    "token_count",
    "within_stratum_order",
)

EXPECTED_TRACKER = "041f095c5ca0271e075c8db1a67ea401764486930c86fa5ff2bc96df7d8f1f71"
EXPECTED_EVENTS = "96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c"
EXPECTED_LEDGER = "77e22433203879b252f7a9e309d2013d7550101d1c4a014b494d2c96df87d0e0"
EXPECTED_V1_FAILURE = "1d3f1f26609c1f1a47790d94730fba50e9f4d888dd8d7d89e6fa698a924fb3a8"
EXPECTED_V1_MANIFEST = "ba561935cff5f9f0a36af0b8b24e4b69bce5fb2c61b5ea2236f0a664c56bcf5d"

SEALED = {
    SOURCE / "RESIDUAL_THRESHOLD_V2_PREREGISTRATION.json": "1c962703e12c5c48fd279dc766fd4d1d3108c40486a10789fdda112926e98261",
    SOURCE / "RESIDUAL_THRESHOLD_V2_SAMPLE_SIZE.json": "46e3d32b4a4c8af73c9197557b09ceed872b1918d41143ed551bb3b4572c6151",
    SOURCE / "RESIDUAL_THRESHOLD_V2_CALIBRATION_CONTRACT.json": "51404e675870c3e99ff6bb51f3aa51e95aa585a360fe782e3c89d11927345934",
    SOURCE / "RESIDUAL_THRESHOLD_V2_MEASUREMENT_CONTRACT.json": "f96b7ae1f20fbc9850cf3dcc6f6f74ad046bf35755e18ccc7e6747441184adee",
    SOURCE / "RESIDUAL_THRESHOLD_V2_SELECTION_PROCEDURE.json": "1c8a82ef939a33bbbb327f0f760439113432645438361176de36159a8f56c55c",
    SOURCE / "RESIDUAL_THRESHOLD_V2_SURFACE_ISOLATION_POLICY.json": "a9f5ae333934ff38a75a0a3e7adad5a5abf78b422f370560d0d9735765372189",
    SOURCE / "RESIDUAL_THRESHOLD_V2_ACCEPTANCE.json": "5cea52584a420e91e7b5f8e3512fbb657610bfb41d95008e52346b59cbfe3d50",
    SOURCE / "RESIDUAL_THRESHOLD_V2_ARTIFACT_SCHEMA.json": "dc6017a49ff4ea14f664a4f11a1f2501658cda177d25bd984d491c04f394e327",
    V1_MANIFEST: EXPECTED_V1_MANIFEST,
    SOURCE / "RESIDUAL_THRESHOLD_V1_CALIBRATION_SCORES.jsonl": "f775849b3bb8cdec2ac8eeeea0100e51853fefcebbd88d6b3b4efb33fa8a3895",
    SOURCE / "RESIDUAL_THRESHOLD_V1_CALIBRATION_FAILURE.json": EXPECTED_V1_FAILURE,
    SOURCE / "RESIDUAL_THRESHOLD_V1_CALIBRATION_DESIGN_CLOSURE.json": "a5dbdb8ae497c25e711a81a880ad26ec7ef1ace917278c807497af5ec37e5002",
    SOURCE / "RESIDUAL_THRESHOLD_V1_CALIBRATION_LABEL_AVAILABILITY_REVIEW.json": "3a6c967c3542096714e25b59544bd68d89d7a9bc28ee253dec1b9f224b5a0484",
    SOURCE / "RESIDUAL_THRESHOLD_V1_CALIBRATION_DRAW_RECEIPT.json": "7448adb8c9448c3737a7b7c2c9a3116ced23d2bab7e432d011bc41229c3ef283",
    EVIDENCE: "0e9b3c1af9dd573bf6e2034640e468e8ab9074e1e76c90cef1f39f68d607bc03",
    EVENTS: EXPECTED_EVENTS,
    LEDGER_FILE: EXPECTED_LEDGER,
    SOURCE / "HYPOTHESIS.json": "39127a810d38ede96d7947c33dbc3e5491c9e1cc9b3f76b1064d9e0dd04a7787",
}

OUTPUTS = (
    CALIBRATION_MANIFEST,
    MEASUREMENT_MANIFEST,
    DRAW_RECEIPT,
    ISOLATION_PATH,
    DISTRIBUTION_PATH,
)

DEVELOPMENT_ROW_KEEP = {
    "normalized_identity",
    "partition",
    "row_id",
    "surface",
    "synset_offset",
    "synset_pos",
}
MAGPIE_KEEP = {"hyperlex_synset", "row_id", "synset"}
V1_KEEP = {"calibration_row_id", "normalized_text_sha256", "pwn30_synset", "surface"}
PROBE_KEEP = {"v3_held_out_errors", "v4_measurement_fallthroughs"}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def refuse(message: str) -> None:
    raise SystemExit(message)


def _loads_kept(text: str, keep: set[str]):
    def hook(pairs: list[tuple[str, object]]) -> dict:
        return {key: value for key, value in pairs if key in keep}

    return json.loads(text, object_pairs_hook=hook)


def _load_development(text: str) -> dict:
    """Keep identity fields. Partition names stay on the partitions object."""

    def hook(pairs: list[tuple[str, object]]) -> dict:
        data = dict(pairs)
        if "row_id" in data and "surface" in data:
            return {key: data[key] for key in DEVELOPMENT_ROW_KEEP if key in data}
        if "rows" in data:
            return {"partitions": data.get("partitions"), "rows": data["rows"]}
        return data

    return json.loads(text, object_pairs_hook=hook)


def allocate_surfaces(
    cells: dict[tuple[str, int], list[dict]],
    calibration_quota: int,
    measurement_quota: int,
) -> dict:
    """Fill calibration from the start of one walk, then measurement.

    Cells are sorted by source POS, then token count. Each cell is ordered
    by normalized_text_sha256. Exhausted cells are skipped. Quotas are not
    reduced when the walk runs out of rows.
    """
    if calibration_quota < 1 or measurement_quota < 1:
        refuse("quotas must be positive")
    ordered: dict[tuple[str, int], list[dict]] = {}
    for key, group in cells.items():
        copied = sorted(group, key=lambda item: item["normalized_text_sha256"])
        ordered[key] = copied
    keys = sorted(ordered)
    cursors = {key: 0 for key in keys}
    emitted: list[dict] = []
    target = calibration_quota + measurement_quota
    while len(emitted) < target:
        progressed = False
        for key in keys:
            index = cursors[key]
            group = ordered[key]
            if index >= len(group):
                continue
            item = group[index]
            if item["pos"] != key[0]:
                refuse("stratum POS does not match the row")
            emitted.append(
                {
                    "global_draw_order": len(emitted) + 1,
                    "item": item,
                    "stratum": key,
                    "within_stratum_order": index + 1,
                }
            )
            cursors[key] = index + 1
            progressed = True
            if len(emitted) == target:
                break
        if not progressed:
            break
    filled = len(emitted) == target
    shortage = None
    if not filled:
        shortage = {
            "calibration_quota": calibration_quota,
            "calibration_rows_emitted": min(len(emitted), calibration_quota),
            "cells": [
                {
                    "available": len(ordered[key]),
                    "exhausted": cursors[key] >= len(ordered[key]),
                    "source_pos": key[0],
                    "taken": cursors[key],
                    "token_count": key[1],
                }
                for key in keys
            ],
            "measurement_quota": measurement_quota,
            "measurement_rows_emitted": max(0, len(emitted) - calibration_quota),
        }
        return {
            "calibration": [],
            "filled": False,
            "measurement": [],
            "shortage": shortage,
        }
    calibration = [
        manifest_row(emission, "CALIBRATION_V2")
        for emission in emitted[:calibration_quota]
    ]
    measurement = [
        manifest_row(emission, "MEASUREMENT_V2")
        for emission in emitted[calibration_quota:]
    ]
    return {
        "calibration": calibration,
        "filled": True,
        "measurement": measurement,
        "shortage": None,
    }


def manifest_row(emission: dict, surface_role: str) -> dict:
    item = emission["item"]
    pos, token_count = emission["stratum"]
    digest = item["normalized_text_sha256"]
    row = {
        "allocation_rule_id": SAMPLING_RULE_ID,
        "frozen_gloss": item["frozen_gloss"],
        "global_draw_order": emission["global_draw_order"],
        "normalized_text_sha256": digest,
        "pos": pos,
        "pwn30_synset": item["pwn30_synset"],
        "row_id": digest,
        "source_identity": SOURCE_IDENTITY,
        "stratum_id": f"{pos}:{token_count}",
        "surface": item["surface"],
        "surface_role": surface_role,
        "token_count": token_count,
        "within_stratum_order": emission["within_stratum_order"],
    }
    if set(row) != set(MANIFEST_FIELDS):
        refuse("manifest row left the structural contract")
    return row


def _verify_sealed() -> None:
    if sha256_file(TRACKER) != EXPECTED_TRACKER:
        refuse("tracker hash drifted before the surface draw")
    for path, expected in SEALED.items():
        if sha256_file(path) != expected:
            refuse(f"sealed artifact changed: {path.name}")


def _identity_fences() -> dict:
    from hyperlexical.heldout_census import normalize_group_text
    from hyperlexical.holdout_guard import normalized_text_sha256
    from hyperlexical.unbind_screen_v4 import normalize_lexical

    evidence = _load_development(EVIDENCE.read_text(encoding="utf-8"))
    rows = evidence["rows"]
    if len(rows) != 225:
        refuse("development evidence row count drifted")
    hashes = set()
    lexical = set()
    grouped = set()
    stored = set()
    synsets = set()
    partitions: Counter[str] = Counter()
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
        partitions[str(row.get("partition") or "")] += 1
    magpie_hashes = set()
    magpie_synsets = set()
    for name in ("MAGPIE_SEMANTIC_EVIDENCE.jsonl", "KM_HYPERLEX_SEMANTIC_EVIDENCE.jsonl"):
        for line in (SOURCE / name).read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            row = _loads_kept(line, MAGPIE_KEEP)
            magpie_hashes.add(row["row_id"])
            for key in ("synset", "hyperlex_synset"):
                value = row.get(key)
                if value:
                    magpie_synsets.add(str(value))
    if sha256_file(V1_MANIFEST) != EXPECTED_V1_MANIFEST:
        refuse("v1 calibration manifest changed")
    v1_hashes = set()
    v1_synsets = set()
    v1_lexical = set()
    v1_grouped = set()
    v1_count = 0
    for line in V1_MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        row = _loads_kept(line, V1_KEEP)
        digest = row["normalized_text_sha256"]
        if row["calibration_row_id"] != digest:
            refuse("v1 calibration row_id drifted from its hash")
        v1_hashes.add(digest)
        v1_synsets.add(row["pwn30_synset"])
        v1_lexical.add(normalize_lexical(row["surface"]))
        v1_grouped.add(normalize_group_text(row["surface"]))
        v1_count += 1
    if v1_count != 27 or len(v1_hashes) != 27 or len(v1_synsets) != 27:
        refuse("v1 calibration identity fence is not 27 distinct rows")
    probe = _loads_kept(PROBE.read_text(encoding="utf-8"), PROBE_KEEP)
    probe_hashes = set()
    for key in ("v3_held_out_errors", "v4_measurement_fallthroughs"):
        for surface in probe.get(key) or []:
            probe_hashes.add(normalized_text_sha256(str(surface)))
    reserves = [
        path
        for path in (LEDGER / "operator-review").rglob("*")
        if path.is_file() and "measurement" in path.name.lower() and "reserve" in path.name.lower()
    ]
    if reserves:
        refuse(f"unexpected measurement reserve: {reserves}")
    return {
        "development_grouped": grouped,
        "development_hashes": hashes,
        "development_lexical": lexical,
        "development_partitions": dict(sorted(partitions.items())),
        "development_stored_identity": stored,
        "development_synsets": synsets,
        "magpie_km_hashes": magpie_hashes,
        "magpie_km_synsets": magpie_synsets,
        "probe_hashes_outside_development": probe_hashes - hashes,
        "v1_grouped": v1_grouped,
        "v1_hashes": v1_hashes,
        "v1_lexical": v1_lexical,
        "v1_synsets": v1_synsets,
    }


def _bound_glosses(pending: list[tuple[str, str]]) -> dict[tuple[str, str], str]:
    from hyperlexical.unbind_screen_v3 import FILES, load_glosses

    found: dict[tuple[str, str], str] = {}
    wanted: dict[str, set[str]] = {}
    for pos, offset in pending:
        wanted.setdefault(pos, set()).add(offset)
    for pos, offsets in wanted.items():
        loaded = load_glosses(WORDNET / FILES[pos][1], offsets)
        for offset, gloss in loaded.items():
            found[(pos, offset)] = gloss
    return found


def build_universe() -> tuple[dict[tuple[str, int], list[dict]], dict]:
    """Enumerate the positional-unbind universe and apply frozen fences.

    This function does not read operator labels, residuals, or model output.
    """
    from hyperlexical.clean_unbind import (
        WORDNET_LICENSE,
        gate_rows,
        load_jsonl,
        read_wordnet_index,
        reason_counts,
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
    exclusion: Counter[str] = Counter()
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
    source_universe = len(positional)
    exclusion["admissible_positional"] = source_universe
    kept = []
    for row in positional:
        surface = str(row.get("text") or "")
        digest = normalized_text_sha256(surface)
        lexical = normalize_lexical(surface)
        grouped = normalize_group_text(surface)
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
        if digest in fences["magpie_km_hashes"]:
            exclusion["magpie_km_overlap"] += 1
            continue
        if digest in fences["v1_hashes"]:
            exclusion["threshold_v1_calibration_row_id"] += 1
            continue
        if lexical in fences["v1_lexical"] or grouped in fences["v1_grouped"]:
            exclusion["threshold_v1_calibration_normalized_text"] += 1
            continue
        if digest in fences["probe_hashes_outside_development"]:
            exclusion["historical_review_surface"] += 1
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
        exclusion["duplicate_normalized_identity"] += 1
        current_digest = normalized_text_sha256(str(current.get("text") or ""))
        if digest < current_digest:
            best[lexical] = row
    indexes = load_indexes(str(WORDNET))
    pending = []
    for row in best.values():
        surface = str(row["text"])
        pos = str(row["source_pos"])
        fillers = [str(tok) for tok in row.get("fillers") or []]
        if " ".join(fillers) != surface:
            refuse("positional tokens do not reconstruct the surface")
        if not (2 <= len(fillers) <= 6):
            refuse("positional universe admitted a token count outside 2..6")
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
        if synset in fences["v1_synsets"]:
            exclusion["threshold_v1_calibration_synset"] += 1
            continue
        item = {
            "frozen_gloss": gloss,
            "normalized_text_sha256": normalized_text_sha256(surface),
            "pos": pos,
            "pwn30_synset": synset,
            "surface": surface,
            "token_count": len(fillers),
        }
        current = synset_best.get(synset)
        if current is None:
            synset_best[synset] = item
            continue
        exclusion["duplicate_synset"] += 1
        if item["normalized_text_sha256"] < current["normalized_text_sha256"]:
            synset_best[synset] = item
    cells: dict[tuple[str, int], list[dict]] = {}
    for item in synset_best.values():
        cells.setdefault((item["pos"], item["token_count"]), []).append(item)
    for key in cells:
        cells[key].sort(key=lambda item: item["normalized_text_sha256"])
    eligible = sum(len(group) for group in cells.values())
    account = {
        "development_partitions_fenced": fences["development_partitions"],
        "eligible_after_exclusions": eligible,
        "exclusion_counts": {key: int(value) for key, value in sorted(exclusion.items())},
        "historical_probe_hashes_outside_development": len(fences["probe_hashes_outside_development"]),
        "measurement_reserve_files": 0,
        "source_wordnet_universe_count": source_universe,
        "strata_available": [
            {
                "available": len(cells[key]),
                "source_pos": key[0],
                "token_count": key[1],
            }
            for key in sorted(cells)
        ],
        "v1_calibration_rows_fenced": 27,
    }
    membership = {
        f"{key[0]}:{key[1]}": [item["normalized_text_sha256"] for item in cells[key]]
        for key in sorted(cells)
    }
    account["cell_membership"] = membership
    return cells, account


def _fingerprint(account: dict, allocated: dict) -> dict:
    return {
        "calibration": [row["row_id"] for row in allocated["calibration"]],
        "cell_membership": account["cell_membership"],
        "eligible_after_exclusions": account["eligible_after_exclusions"],
        "exclusion_counts": account["exclusion_counts"],
        "measurement": [row["row_id"] for row in allocated["measurement"]],
        "measurement_glosses": [row["frozen_gloss"] for row in allocated["measurement"]],
        "calibration_glosses": [row["frozen_gloss"] for row in allocated["calibration"]],
        "source_wordnet_universe_count": account["source_wordnet_universe_count"],
    }


def _distribution(rows: list[dict]) -> dict:
    pos_counts: Counter[str] = Counter(row["pos"] for row in rows)
    token_counts: Counter[int] = Counter(row["token_count"] for row in rows)
    cells: Counter[tuple[str, int]] = Counter((row["pos"], row["token_count"]) for row in rows)
    return {
        "pos_counts": dict(sorted(pos_counts.items())),
        "pos_token_cells": [
            {"count": count, "pos": pos, "token_count": token_count}
            for (pos, token_count), count in sorted(cells.items())
        ],
        "row_count": len(rows),
        "token_count_counts": {str(token_count): count for token_count, count in sorted(token_counts.items())},
    }


def _row_overlap(left: list[dict], right_hashes: set[str], right_lexical: set[str], right_grouped: set[str], right_synsets: set[str]) -> dict:
    from hyperlexical.heldout_census import normalize_group_text
    from hyperlexical.unbind_screen_v4 import normalize_lexical

    left_hashes = {row["row_id"] for row in left}
    left_synsets = {row["pwn30_synset"] for row in left}
    normalized = 0
    for row in left:
        lexical = normalize_lexical(row["surface"])
        grouped = normalize_group_text(row["surface"])
        if lexical in right_lexical or grouped in right_grouped:
            normalized += 1
    return {
        "normalized_text": normalized,
        "row_id": len(left_hashes & right_hashes),
        "synset": len(left_synsets & right_synsets),
    }


def _surface_sets(rows: list[dict]) -> dict:
    from hyperlexical.heldout_census import normalize_group_text
    from hyperlexical.unbind_screen_v4 import normalize_lexical

    return {
        "grouped": {normalize_group_text(row["surface"]) for row in rows},
        "hashes": {row["row_id"] for row in rows},
        "lexical": {normalize_lexical(row["surface"]) for row in rows},
        "synsets": {row["pwn30_synset"] for row in rows},
    }


def _isolation(calibration: list[dict], measurement: list[dict], fences: dict) -> dict:
    development = _row_overlap(
        calibration,
        fences["development_hashes"],
        fences["development_lexical"],
        fences["development_grouped"] | fences["development_stored_identity"],
        fences["development_synsets"],
    )
    development_measurement = _row_overlap(
        measurement,
        fences["development_hashes"],
        fences["development_lexical"],
        fences["development_grouped"] | fences["development_stored_identity"],
        fences["development_synsets"],
    )
    v1_calibration = _row_overlap(
        calibration,
        fences["v1_hashes"],
        fences["v1_lexical"],
        fences["v1_grouped"],
        fences["v1_synsets"],
    )
    v1_measurement = _row_overlap(
        measurement,
        fences["v1_hashes"],
        fences["v1_lexical"],
        fences["v1_grouped"],
        fences["v1_synsets"],
    )
    measurement_sets = _surface_sets(measurement)
    calibration_vs_measurement = _row_overlap(
        calibration,
        measurement_sets["hashes"],
        measurement_sets["lexical"],
        measurement_sets["grouped"],
        measurement_sets["synsets"],
    )
    pairs = {
        "calibration_v2_vs_development": development,
        "calibration_v2_vs_measurement_v2": calibration_vs_measurement,
        "calibration_v2_vs_threshold_v1_calibration": v1_calibration,
        "measurement_v2_vs_development": development_measurement,
        "measurement_v2_vs_threshold_v1_calibration": v1_measurement,
    }
    synset_sets = {
        "development": fences["development_synsets"],
        "threshold_v1_calibration": fences["v1_synsets"],
        "threshold_v2_calibration": {row["pwn30_synset"] for row in calibration},
        "threshold_v2_measurement": {row["pwn30_synset"] for row in measurement},
    }
    names = list(synset_sets)
    synset_pairs = []
    for index, left_name in enumerate(names):
        for right_name in names[index + 1 :]:
            synset_pairs.append(
                {
                    "count": len(synset_sets[left_name] & synset_sets[right_name]),
                    "left": left_name,
                    "right": right_name,
                }
            )
    internal = {
        "calibration_duplicate_row_id": len(calibration) - len({row["row_id"] for row in calibration}),
        "calibration_duplicate_synset": len(calibration) - len({row["pwn30_synset"] for row in calibration}),
        "measurement_duplicate_row_id": len(measurement) - len({row["row_id"] for row in measurement}),
        "measurement_duplicate_synset": len(measurement) - len({row["pwn30_synset"] for row in measurement}),
    }
    total = sum(item[key] for item in pairs.values() for key in ("normalized_text", "row_id", "synset"))
    total += sum(internal.values())
    total += sum(item["count"] for item in synset_pairs)
    return {
        "internal_duplicates": internal,
        "pairwise": pairs,
        "synset_pairs": synset_pairs,
        "total": total,
    }


def _verify_glosses(calibration: list[dict], measurement: list[dict]) -> None:
    from hyperlexical.unbind_screen_v3 import FILES, gloss_for, load_glosses, load_indexes

    rows = calibration + measurement
    indexes = load_indexes(str(WORDNET))
    wanted: dict[str, set[str]] = {}
    for row in rows:
        pos, offset = row["pwn30_synset"].split(":", 1)
        lemma = row["surface"].replace(" ", "_")
        bound = (indexes.get(row["pos"]) or {}).get(lemma)
        if row["pos"] != pos or bound != offset:
            refuse(f"source-POS synset drifted: {row['surface']}")
        wanted.setdefault(pos, set()).add(offset)
    glosses: dict[tuple[str, str], str] = {}
    for pos, offsets in wanted.items():
        loaded = load_glosses(WORDNET / FILES[pos][1], offsets)
        for offset, gloss in loaded.items():
            glosses[(pos, offset)] = gloss
    seen_strata = set()
    for row in rows:
        pos, offset = row["pwn30_synset"].split(":", 1)
        if glosses.get((pos, offset)) != row["frozen_gloss"]:
            refuse(f"frozen gloss drifted on rescan: {row['surface']}")
        stratum = (row["pos"], row["token_count"])
        if stratum in seen_strata:
            continue
        seen_strata.add(stratum)
        bound_pos, gloss = gloss_for(row["surface"], row["pos"], str(WORDNET))
        if bound_pos != row["pos"] or gloss != row["frozen_gloss"]:
            refuse(f"frozen gloss drifted from gloss_for: {row['surface']}")


def _render_json(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def _render_jsonl(rows: list[dict]) -> str:
    return "".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in rows)


def _write_new(path: Path, text: str) -> None:
    if path.exists():
        refuse(f"refusing to rewrite {path.name}")
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)


def _public_flags() -> dict:
    return {
        "admitted": 0,
        "extended_lesk_run": False,
        "glossbert_run": False,
        "gold": 0,
        "json_schema_document": None,
        "json_schema_exists": False,
        "measurement_eligible": False,
        "minilm_encode": False,
        "operator_labels_joined": False,
        "operator_labels_loaded": False,
        "residual_scores_created": False,
        "runtime_integration": False,
        "select_005_authorized": False,
        "selected_source": "none",
        "settled": 0,
        "threshold_frozen": False,
        "threshold_value": None,
    }


def _failure_receipt(state: str, detail: dict) -> None:
    if DRAW_RECEIPT.exists():
        refuse(state)
    payload = {
        **_public_flags(),
        "allocation_rule_id": SAMPLING_RULE_ID,
        "authorization": AUTHORIZATION,
        "calibration_surface_frozen": False,
        "detail": detail,
        "determinism": "IDENTICAL" if state != STATE_NOT_DETERMINISTIC else "NOT_IDENTICAL",
        "draw_seed": None,
        "measurement_state": "NOT_DRAWN",
        "measurement_surface_frozen": False,
        "rng_used": False,
        "schema": "hyperlex.residual_threshold_v2_surface_draw_receipt.v1",
        "state": state,
    }
    _write_new(DRAW_RECEIPT, _render_json(payload))
    _update_tracker_failure(state)
    refuse(state)


def _update_tracker_failure(state: str) -> None:
    tracker = json.loads(TRACKER.read_text(encoding="utf-8"))
    if tracker.get("residual_threshold_state") != "CALIBRATION_INSUFFICIENT_SUPPORT":
        refuse("v1 execution state drifted")
    if tracker.get("residual_threshold_v1_disposition") != "CLOSED_CALIBRATION_DESIGN_INSUFFICIENT":
        refuse("v1 disposition drifted")
    tracker["previous_tracker_sha256"] = EXPECTED_TRACKER
    tracker["residual_threshold_v2_state"] = state
    tracker["residual_threshold_v2_value"] = None
    tracker["residual_threshold_v2_frozen"] = False
    tracker["residual_threshold_v2_calibration_surface_drawn"] = False
    tracker["residual_threshold_v2_measurement_surface_drawn"] = False
    tracker["next_legal_transition"] = None
    tracker["next_transition_authorized"] = False
    tracker["selected_source"] = "none"
    tracker["measurement_eligible"] = False
    text = json.dumps(tracker, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    TRACKER.write_text(text, encoding="utf-8")
    TRACKER.chmod(0o600)


def _update_tracker_success(hashes: dict) -> str:
    tracker = json.loads(TRACKER.read_text(encoding="utf-8"))
    if tracker.get("residual_threshold_state") != "CALIBRATION_INSUFFICIENT_SUPPORT":
        refuse("v1 execution state drifted")
    if tracker.get("residual_threshold_v1_disposition") != "CLOSED_CALIBRATION_DESIGN_INSUFFICIENT":
        refuse("v1 disposition drifted")
    if tracker.get("residual_threshold_value") is not None or tracker.get("residual_threshold_frozen") is not False:
        refuse("v1 threshold drifted")
    if tracker.get("residual_threshold_redraw_authorized") is not False:
        refuse("v1 redraw flag drifted")
    tracker["previous_tracker_sha256"] = EXPECTED_TRACKER
    tracker["residual_threshold_v2_state"] = STATE_FROZEN
    tracker["residual_threshold_v2_value"] = None
    tracker["residual_threshold_v2_frozen"] = False
    tracker["residual_threshold_v2_calibration_surface_drawn"] = True
    tracker["residual_threshold_v2_calibration_surface_frozen"] = True
    tracker["residual_threshold_v2_calibration_manifest_rows"] = 200
    tracker["residual_threshold_v2_calibration_resolved"] = False
    tracker["residual_threshold_v2_calibration_scored"] = False
    tracker["residual_threshold_v2_calibration_labeled"] = False
    tracker["residual_threshold_v2_calibration_manifest_sha256"] = hashes["calibration_manifest_sha256"]
    tracker["residual_threshold_v2_measurement_surface_drawn"] = True
    tracker["residual_threshold_v2_measurement_surface_frozen"] = True
    tracker["residual_threshold_v2_measurement_manifest_rows"] = 200
    tracker["residual_threshold_v2_measurement_state"] = MEASUREMENT_STATE
    tracker["residual_threshold_v2_measurement_resolved"] = False
    tracker["residual_threshold_v2_measurement_scored"] = False
    tracker["residual_threshold_v2_measurement_labeled"] = False
    tracker["residual_threshold_v2_measurement_manifest_sha256"] = hashes["measurement_manifest_sha256"]
    tracker["residual_threshold_v2_surface_draw_receipt_sha256"] = hashes["draw_receipt_sha256"]
    tracker["residual_threshold_v2_surface_isolation_report_sha256"] = hashes["isolation_sha256"]
    tracker["residual_threshold_v2_surface_distribution_report_sha256"] = hashes["distribution_sha256"]
    tracker["residual_threshold_v2_redraw_authorized"] = False
    tracker["measurement_eligible"] = False
    tracker["next_legal_transition"] = NEXT_TRANSITION
    tracker["next_transition_authorized"] = False
    tracker["selected_source"] = "none"
    tracker["select_authorized"] = False
    tracker["admitted"] = 0
    tracker["settled"] = 0
    tracker["gold"] = 0
    text = json.dumps(tracker, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    TRACKER.write_text(text, encoding="utf-8")
    TRACKER.chmod(0o600)
    if tracker["residual_threshold_state"] != "CALIBRATION_INSUFFICIENT_SUPPORT":
        refuse("v1 execution state was overwritten")
    return sha256_file(TRACKER)


def freeze_surfaces() -> dict:
    for path in OUTPUTS:
        if path.exists():
            refuse(f"surface artifact already exists: {path.name}")
    _verify_sealed()
    if calibration_draw_size() != 200 or measurement_draw_size() != 200:
        refuse("frozen quotas are not 200")
    print("draw pass 1", file=sys.stderr, flush=True)
    first_cells, first_account = build_universe()
    first_allocated = allocate_surfaces(first_cells, 200, 200)
    print("draw pass 2", file=sys.stderr, flush=True)
    second_cells, second_account = build_universe()
    second_allocated = allocate_surfaces(second_cells, 200, 200)
    if _fingerprint(first_account, first_allocated) != _fingerprint(second_account, second_allocated):
        _failure_receipt(STATE_NOT_DETERMINISTIC, {"draw_passes": 2})
    if not first_allocated["filled"]:
        _failure_receipt(STATE_UNFILLED, first_allocated["shortage"])
    calibration = first_allocated["calibration"]
    measurement = first_allocated["measurement"]
    if len(calibration) != 200 or len(measurement) != 200:
        refuse("filled allocation did not emit the quotas")
    print("gloss check", file=sys.stderr, flush=True)
    _verify_glosses(calibration, measurement)
    fences = _identity_fences()
    isolation_body = _isolation(calibration, measurement, fences)
    if isolation_body["total"] != 0:
        _failure_receipt("ISOLATION_FAILURE", isolation_body)
    for row in calibration + measurement:
        if set(row) != set(MANIFEST_FIELDS):
            refuse("manifest row carries a field outside the contract")
        if row["row_id"] != row["normalized_text_sha256"]:
            refuse("row_id is not normalized_text_sha256")
    calibration_text = _render_jsonl(calibration)
    measurement_text = _render_jsonl(measurement)
    calibration_sha = sha256_bytes(calibration_text.encode("utf-8"))
    measurement_sha = sha256_bytes(measurement_text.encode("utf-8"))
    distribution = {
        **_public_flags(),
        "authorization": AUTHORIZATION,
        "calibration": _distribution(calibration),
        "labels_joined": False,
        "measurement": _distribution(measurement),
        "schema": "hyperlex.residual_threshold_v2_surface_distribution_report.v1",
    }
    isolation = {
        **_public_flags(),
        "authorization": AUTHORIZATION,
        "calibration_manifest_sha256": calibration_sha,
        "internal_duplicates": isolation_body["internal_duplicates"],
        "measurement_manifest_sha256": measurement_sha,
        "pairwise": isolation_body["pairwise"],
        "schema": "hyperlex.residual_threshold_v2_surface_isolation_report.v1",
        "synset_pairs": isolation_body["synset_pairs"],
        "total": isolation_body["total"],
    }
    distribution_text = _render_json(distribution)
    isolation_text = _render_json(isolation)
    distribution_sha = sha256_bytes(distribution_text.encode("utf-8"))
    isolation_sha = sha256_bytes(isolation_text.encode("utf-8"))
    receipt = {
        **_public_flags(),
        "allocation_rule_id": SAMPLING_RULE_ID,
        "authorization": AUTHORIZATION,
        "calibration_labeled": False,
        "calibration_manifest_rows": 200,
        "calibration_manifest_sha256": calibration_sha,
        "calibration_resolved": False,
        "calibration_scored": False,
        "calibration_surface_frozen": True,
        "determinism": "IDENTICAL",
        "development_partitions_fenced": first_account["development_partitions_fenced"],
        "distribution_sha256": distribution_sha,
        "draw_passes": 2,
        "draw_seed": None,
        "eligible_after_exclusions": first_account["eligible_after_exclusions"],
        "exclusion_counts": first_account["exclusion_counts"],
        "historical_probe_hashes_outside_development": first_account["historical_probe_hashes_outside_development"],
        "isolation_sha256": isolation_sha,
        "measurement_labeled": False,
        "measurement_manifest_rows": 200,
        "measurement_manifest_sha256": measurement_sha,
        "measurement_reserve_files": 0,
        "measurement_resolved": False,
        "measurement_scored": False,
        "measurement_state": MEASUREMENT_STATE,
        "measurement_surface_frozen": True,
        "ordering": "normalized_text_sha256 ascending within cell",
        "replacement": "without_replacement",
        "rng_used": False,
        "rule": "RUNE.SEMANTIC_COMPOSITIONALITY_THRESHOLD.v2",
        "schema": "hyperlex.residual_threshold_v2_surface_draw_receipt.v1",
        "source_wordnet_universe_count": first_account["source_wordnet_universe_count"],
        "state": STATE_FROZEN,
        "strata_available": first_account["strata_available"],
        "stratification": "source_pos x token_count",
        "v1_calibration_rows_fenced": 27,
        "v1_failure_sha256": EXPECTED_V1_FAILURE,
        "v1_remains_sealed": True,
        "v2_preregistration_sha256": SEALED[SOURCE / "RESIDUAL_THRESHOLD_V2_PREREGISTRATION.json"],
        "visit_order": "round-robin across cells sorted by source_pos then token_count; skip exhausted cells; first 200 emissions CALIBRATION_V2; next 200 emissions MEASUREMENT_V2",
        "events_sha256": EXPECTED_EVENTS,
        "ledger_sha256": EXPECTED_LEDGER,
    }
    receipt_text = _render_json(receipt)
    receipt_sha = sha256_bytes(receipt_text.encode("utf-8"))
    _write_new(CALIBRATION_MANIFEST, calibration_text)
    _write_new(MEASUREMENT_MANIFEST, measurement_text)
    _write_new(ISOLATION_PATH, isolation_text)
    _write_new(DISTRIBUTION_PATH, distribution_text)
    _write_new(DRAW_RECEIPT, receipt_text)
    if sha256_file(CALIBRATION_MANIFEST) != calibration_sha:
        refuse("calibration manifest hash drifted on write")
    if sha256_file(MEASUREMENT_MANIFEST) != measurement_sha:
        refuse("measurement manifest hash drifted on write")
    if sha256_file(ISOLATION_PATH) != isolation_sha:
        refuse("isolation report hash drifted on write")
    if sha256_file(DISTRIBUTION_PATH) != distribution_sha:
        refuse("distribution report hash drifted on write")
    if sha256_file(DRAW_RECEIPT) != receipt_sha:
        refuse("draw receipt hash drifted on write")
    _verify_sealed()
    tracker_sha = _update_tracker_success(
        {
            "calibration_manifest_sha256": calibration_sha,
            "distribution_sha256": distribution_sha,
            "draw_receipt_sha256": receipt_sha,
            "isolation_sha256": isolation_sha,
            "measurement_manifest_sha256": measurement_sha,
        }
    )
    for path, expected in SEALED.items():
        if sha256_file(path) != expected:
            refuse(f"sealed artifact changed after the draw: {path.name}")
    if sha256_file(EVENTS) != EXPECTED_EVENTS or sha256_file(LEDGER_FILE) != EXPECTED_LEDGER:
        refuse("events or ledger changed")
    report = {
        "allocation_rule_id": SAMPLING_RULE_ID,
        "calibration_manifest_sha256": calibration_sha,
        "distribution_sha256": distribution_sha,
        "draw_receipt_sha256": receipt_sha,
        "eligible_after_exclusions": first_account["eligible_after_exclusions"],
        "exclusion_counts": first_account["exclusion_counts"],
        "isolation_sha256": isolation_sha,
        "isolation_total": isolation_body["total"],
        "measurement_manifest_sha256": measurement_sha,
        "source_wordnet_universe_count": first_account["source_wordnet_universe_count"],
        "state": STATE_FROZEN,
        "tracker_sha256": tracker_sha,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


def main() -> None:
    freeze_surfaces()


if __name__ == "__main__":
    main()
