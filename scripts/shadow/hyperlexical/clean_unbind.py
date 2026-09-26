"""Clean-unbind reserve gate.

The executed unbind row is ``export._unbind_dual_scheme_rows``: fillers are
the source atom's own tokens, positional roles are ``pos_N``, and type_slot
roles are structural ``TOKEN`` / ``SLOT`` / ``MARKER``. A gloss is not gold.

``unbind_clean`` is ``soft_ceiling.clean_surface`` against train-split rows,
the call ``holdout_eligibility.census`` makes. That predicate is not
``normalized_text_sha256``. The hash is only the contamination identity.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from .export import (
    COLLISION_HOLD,
    LIVE_UNBIND_MAX_LEN,
    LIVE_UNBIND_MAX_TOKENS,
    TYPE_SLOT_TAGS,
    reject_candidate_text,
)
from .holdout_guard import normalized_text_sha256
from .identity_ledger import PLANNING_TARGETS, IdentityLedger, derived_state
from .soft_ceiling import clean_surface
from .unbind_settlement import ADMIT_DECISIONS

UNBIND_CLEAN_DEFINITION = "soft_ceiling.clean_surface"
CONTRACT_SHAPE = "hyperlexical.export._unbind_dual_scheme_rows"
BLOCKED_TARGET_ORIGINS = frozenset(
    {
        "model",
        "hyperlex_model",
        "jev",
        "classification_family",
        "source_hint",
    }
)
ALLOWED_TARGET_ORIGINS = frozenset({"source_lemma_tokens", "operator_authored"})
CLASSIFY_SLICES = ("classify", "classify_observed", "classify_non_none")
BLOCKING_STATES = frozenset(
    {
        "TRAIN_CONSUMED",
        "EVAL_SPENT",
        "EVAL_ABANDONED",
        "EVAL_RESERVE",
        "EVAL_BOUND",
        "TRAIN_CANDIDATE",
    }
)
INDEX_FILES = (
    ("noun", "index.noun"),
    ("verb", "index.verb"),
    ("adj", "index.adj"),
    ("adv", "index.adv"),
)


def refuse(message: str) -> None:
    raise SystemExit(f"REFUSE: {message}")


def target_sha256(fillers: Sequence[str]) -> str:
    """Identity of the filler list. Not a surface hash."""
    joined = " ".join(str(item).casefold() for item in fillers)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def schema_example() -> dict[str, Any]:
    """Synthetic placeholders. Not an acquired row."""
    return {
        "positional": {
            "text": "EXAMPLE_TOKEN_A EXAMPLE_TOKEN_B",
            "split": "eval",
            "lineage": "none",
            "typology": [],
            "stage": "noise",
            "roles": ["pos_0", "pos_1"],
            "fillers": ["EXAMPLE_TOKEN_A", "EXAMPLE_TOKEN_B"],
            "role_scheme": "positional",
            "task": "unbind",
            "provenance": "source:EXAMPLE_LOCATOR",
            "class": "INFERRED",
            "license": "EXAMPLE_RIGHTS_GRANT",
            "target_origin": "source_lemma_tokens",
        },
        "type_slot": {
            "text": "TOKEN:EXAMPLE_TOKEN_A SLOT:EXAMPLE_TOKEN_B",
            "split": "eval",
            "lineage": "none",
            "typology": [],
            "stage": "noise",
            "roles": ["TOKEN", "SLOT"],
            "fillers": ["EXAMPLE_TOKEN_A", "EXAMPLE_TOKEN_B"],
            "role_scheme": "type_slot",
            "task": "unbind",
            "provenance": "source:EXAMPLE_LOCATOR",
            "class": "INFERRED",
            "license": "EXAMPLE_RIGHTS_GRANT",
            "target_origin": "source_lemma_tokens",
        },
        "scorer": {
            "module": "hyperlexical.eval_forward.score_unbind_exact",
            "gold": "row fillers, one string per role",
            "empty_fillers": "skipped",
            "metrics": [
                "unbind_exact",
                "unbind_token_f1",
                "unbind_slot_f1",
                "unbind_exact_strict",
                "unbind_token_f1_strict",
                "unbind_slot_f1_strict",
            ],
            "by_role_scheme": ["positional", "type_slot"],
            "baseline": "unbind_copy_token",
            "clean_slice": UNBIND_CLEAN_DEFINITION,
            "this_module_scores": False,
        },
    }


def structural_tags(n: int) -> list[str]:
    return [TYPE_SLOT_TAGS[i % len(TYPE_SLOT_TAGS)] for i in range(n)]


def dual_scheme_rows(
    tokens: Sequence[str],
    *,
    license: str,
    provenance: str,
    target_origin: str,
    source_pos: str = "",
    lineage: str = "none",
    stage: str = "noise",
    epistemic: str = "INFERRED",
) -> list[dict[str, Any]]:
    """Same text/role/filler shape as ``_unbind_dual_scheme_rows``."""
    items = [str(tok) for tok in tokens]
    atom = " ".join(items)
    tags = structural_tags(len(items))
    common = {
        "split": "eval",
        "lineage": lineage,
        "typology": [],
        "stage": stage,
        "task": "unbind",
        "provenance": provenance,
        "class": epistemic,
        "license": license,
        "target_origin": target_origin,
        "source_pos": source_pos,
    }
    positional = {
        **common,
        "text": atom,
        "roles": [f"pos_{k}" for k in range(len(items))],
        "fillers": list(items),
        "role_scheme": "positional",
    }
    typed = {
        **common,
        "text": " ".join(f"{tag}:{tok}" for tag, tok in zip(tags, items)),
        "roles": tags,
        "fillers": list(items),
        "role_scheme": "type_slot",
    }
    return [positional, typed]


def structural_reason(row: Mapping[str, Any]) -> str | None:
    if str(row.get("task") or "") != "unbind":
        return "not_unbind"
    scheme = row.get("role_scheme")
    if scheme not in {"positional", "type_slot"}:
        return "role_scheme"
    fillers = row.get("fillers")
    if not isinstance(fillers, list) or not fillers:
        return "missing_target"
    if not all(isinstance(item, str) and item.strip() for item in fillers):
        return "missing_target"
    if not (2 <= len(fillers) <= LIVE_UNBIND_MAX_TOKENS):
        return "token_count"
    atom = " ".join(str(item) for item in fillers)
    if len(atom) > LIVE_UNBIND_MAX_LEN:
        return "atom_length"
    if atom.lower() in COLLISION_HOLD:
        return "collision_hold"
    junk = reject_candidate_text(atom)
    if junk:
        return f"candidate_{junk}"
    roles = row.get("roles")
    if not isinstance(roles, list) or len(roles) != len(fillers):
        return "role_alignment"
    text = str(row.get("text") or "")
    if scheme == "positional":
        if text.split() != list(fillers):
            return "surface_filler_mismatch"
        if list(roles) != [f"pos_{k}" for k in range(len(fillers))]:
            return "role_alignment"
    else:
        tags = structural_tags(len(fillers))
        expected = " ".join(f"{tag}:{tok}" for tag, tok in zip(tags, fillers))
        if text != expected or list(roles) != tags:
            return "surface_filler_mismatch"
    if str(row.get("class") or "") not in {"OBSERVED", "INFERRED"}:
        return "class"
    if "lineage" not in row:
        return "lineage"
    return None


def rights_reason(row: Mapping[str, Any]) -> str | None:
    license_text = row.get("license")
    if not isinstance(license_text, str) or not license_text.strip():
        return "rights_unresolved"
    lowered = license_text.lower()
    if "rights_unresolved" in lowered or "not cc" in lowered:
        return "rights_unresolved"
    return None


def target_reason(row: Mapping[str, Any]) -> str | None:
    origin = str(row.get("target_origin") or "").strip()
    if not origin:
        return "unbind_unresolved"
    if origin in BLOCKED_TARGET_ORIGINS:
        return "model_derived_target"
    if origin not in ALLOWED_TARGET_ORIGINS:
        return "unbind_unresolved"
    provenance = str(row.get("provenance") or "").lower()
    if any(mark in provenance for mark in ("jev", "model-derived", "hyperlex-encoder", "source_hint_only")):
        return "model_derived_target"
    return None


def unbind_clean_hashes(
    rows: Sequence[Mapping[str, Any]],
    train_rows: Sequence[Mapping[str, Any]],
) -> tuple[set[str], dict[str, Any]]:
    """Canonical clean predicate. Train split only. No trained-key extra."""
    train_for_clean = [row for row in train_rows if row.get("split") == "train"]
    unbind = [row for row in rows if row.get("task") == "unbind"]
    kept, account = clean_surface(unbind, train_rows=train_for_clean)
    hashes = {normalized_text_sha256(str(row.get("text") or "")) for row in kept}
    account = dict(account)
    account["definition"] = UNBIND_CLEAN_DEFINITION
    account["train_split_rows"] = len(train_for_clean)
    return hashes, account


def _reject(bucket: list[dict[str, str]], digest: str, reason: str) -> None:
    bucket.append({"normalized_text_sha256": digest, "reason": reason})


def gate_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    train_rows: Sequence[Mapping[str, Any]],
    ledger: IdentityLedger,
    settlements: Mapping[str, Mapping[str, Any]] | None = None,
    require_settlement: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, str]], dict[str, Any]]:
    """Return admissible rows, hash rejections, and clean accounting.

    One rejection per canonical text hash. The first failing check wins.
    """
    rejections: list[dict[str, str]] = []
    survivors: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        digest = normalized_text_sha256(str(row.get("text") or ""))
        if digest in seen:
            continue
        seen.add(digest)
        reason = structural_reason(row) or target_reason(row) or rights_reason(row)
        if reason:
            _reject(rejections, digest, reason)
            continue
        record = ledger.identities.get(digest)
        state = derived_state(record) if record else "NEW"
        if state in BLOCKING_STATES:
            _reject(rejections, digest, state)
            continue
        if state not in {"NEW", "AVAILABLE"}:
            _reject(rejections, digest, state)
            continue
        survivors.append(dict(row))
    clean_hashes, account = unbind_clean_hashes(survivors, train_rows)
    admissible: list[dict[str, Any]] = []
    for row in survivors:
        digest = normalized_text_sha256(str(row.get("text") or ""))
        if digest not in clean_hashes:
            _reject(rejections, digest, "not_clean")
            continue
        if not require_settlement:
            admissible.append(row)
            continue
        settled = settlements or {}
        settlement = settled.get(digest)
        if settlement is None:
            _reject(rejections, digest, "unsettled")
            continue
        decision = str(settlement.get("decision") or "")
        if decision == "REJECT":
            _reject(rejections, digest, "settlement_reject")
            continue
        if decision == "UNRESOLVED":
            _reject(rejections, digest, "settlement_unresolved")
            continue
        if decision not in ADMIT_DECISIONS:
            _reject(rejections, digest, "unsettled")
            continue
        expected = target_sha256(row.get("fillers") or [])
        if str(settlement.get("target_sha256") or "") != expected:
            _reject(rejections, digest, "target_mismatch")
            continue
        if str(settlement.get("target_provenance") or "") != str(row.get("target_origin") or ""):
            _reject(rejections, digest, "target_mismatch")
            continue
        admissible.append(row)
    return admissible, rejections, account


def select_diverse(rows: Sequence[Mapping[str, Any]], limit: int) -> list[dict[str, Any]]:
    """Round-robin atoms by filler count and source pos. Both schemes stay paired."""
    if limit <= 0:
        return []
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(target_sha256(list(row.get("fillers") or [])), []).append(dict(row))
    buckets: dict[tuple[int, str], list[list[dict[str, Any]]]] = {}
    for group in groups.values():
        n_fillers = len(group[0].get("fillers") or [])
        source_pos = str(group[0].get("source_pos") or "")
        buckets.setdefault((n_fillers, source_pos), []).append(group)
    for group_list in buckets.values():
        group_list.sort(key=lambda group: normalized_text_sha256(str(group[0].get("text") or "")))
    order = sorted(buckets)
    indexes = {key: 0 for key in order}
    picked: list[dict[str, Any]] = []
    while len(picked) < limit:
        progressed = False
        for key in order:
            index = indexes[key]
            if index >= len(buckets[key]):
                continue
            group = buckets[key][index]
            indexes[key] = index + 1
            ordered = sorted(
                group,
                key=lambda row: (row.get("role_scheme") != "positional", str(row.get("role_scheme") or "")),
            )
            room = limit - len(picked)
            if len(ordered) <= room:
                picked.extend(ordered)
                progressed = True
            else:
                positional = [row for row in ordered if row.get("role_scheme") == "positional"]
                if positional and len(positional) <= room:
                    picked.extend(positional)
                    progressed = True
            if len(picked) >= limit:
                break
        if not progressed:
            break
    return picked


def diversity_report(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Dimensions the unbind row already has. No new taxonomy."""
    schemes: Counter[str] = Counter()
    filler_counts: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    classes: Counter[str] = Counter()
    lineages: Counter[str] = Counter()
    surfaces_per_target: Counter[str] = Counter()
    for row in rows:
        schemes[str(row.get("role_scheme") or "")] += 1
        filler_counts[str(len(row.get("fillers") or []))] += 1
        sources[str(row.get("source_pos") or "unspecified")] += 1
        classes[str(row.get("class") or "")] += 1
        lineages[str(row.get("lineage") or "")] += 1
        surfaces_per_target[target_sha256(list(row.get("fillers") or []))] += 1
    histogram = Counter(surfaces_per_target.values())
    return {
        "rows": len(rows),
        "role_scheme": dict(schemes),
        "filler_count": dict(sorted(filler_counts.items(), key=lambda item: int(item[0]) if item[0].isdigit() else 0)),
        "source_pos_metadata": dict(sources),
        "source_pos_metadata_note": "WordNet index file. Not a Hyperlex family.",
        "class": dict(classes),
        "lineage": dict(lineages),
        "unique_targets": len(surfaces_per_target),
        "max_surfaces_per_target": max(surfaces_per_target.values()) if surfaces_per_target else 0,
        "surfaces_per_target_histogram": {str(size): histogram[size] for size in sorted(histogram)},
    }


def assert_wordnet_license(text: str) -> None:
    if "Permission to use, copy, modify and distribute" not in text:
        refuse("WordNet license grant is not in the license file")
    if "Copyright 2006 by Princeton University" not in text:
        refuse("WordNet copyright notice is not in the license file")


def read_wordnet_index(index_dir: str | Path) -> list[dict[str, Any]]:
    """Multiword index lemmas only. Does not read glosses in ``data.*``."""
    root = Path(index_dir)
    atoms: list[dict[str, Any]] = []
    seen_surface: set[tuple[str, str]] = set()
    for source_pos, name in INDEX_FILES:
        path = root / name
        if not path.is_file():
            refuse(f"WordNet index missing: {name}")
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line or line[0] == " ":
                continue
            lemma = line.split(" ", 1)[0]
            if "_" not in lemma:
                continue
            tokens = [part for part in lemma.split("_") if part]
            if len(tokens) != lemma.count("_") + 1:
                continue
            surface = " ".join(tokens)
            if not (2 <= len(tokens) <= LIVE_UNBIND_MAX_TOKENS):
                continue
            if len(surface) > LIVE_UNBIND_MAX_LEN:
                continue
            if surface.lower() in COLLISION_HOLD:
                continue
            if reject_candidate_text(surface):
                continue
            key = (source_pos, surface.casefold())
            if key in seen_surface:
                continue
            seen_surface.add(key)
            atoms.append(
                {
                    "source_pos": source_pos,
                    "tokens": tokens,
                    "surface": surface,
                    "lemma_sha256": hashlib.sha256(lemma.encode("utf-8")).hexdigest(),
                }
            )
    return atoms


def rows_from_wordnet_atoms(
    atoms: Sequence[Mapping[str, Any]],
    *,
    license: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for atom in atoms:
        tokens = list(atom["tokens"])
        provenance = (
            "wordnet-3.0:index."
            + str(atom.get("source_pos") or "")
            + ":lemma:"
            + str(atom.get("lemma_sha256") or "")
        )
        rows.extend(
            dual_scheme_rows(
                tokens,
                license=license,
                provenance=provenance,
                target_origin="source_lemma_tokens",
                source_pos=str(atom.get("source_pos") or ""),
            )
        )
    return rows


def reason_counts(rejections: Sequence[Mapping[str, str]]) -> dict[str, int]:
    counts: Counter[str] = Counter(item["reason"] for item in rejections)
    return dict(sorted(counts.items()))


def admit_clean_unbind(
    ledger: IdentityLedger,
    rows: Sequence[Mapping[str, Any]],
    *,
    batch_id: str,
    source_artifact: str,
    train_rows: Sequence[Mapping[str, Any]],
    settlements: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Admit only gated clean-unbind rows. Does not persist."""
    before = ledger.reserve_counts()
    admissible, rejections, clean_account = gate_rows(
        rows,
        train_rows=train_rows,
        ledger=ledger,
        settlements=settlements,
    )
    room = max(int(PLANNING_TARGETS["unbind_clean"]) - int(before.get("unbind_clean", 0)), 0)
    if len(admissible) <= room:
        selected = list(admissible)
    else:
        selected = select_diverse(admissible, room)
    clean_hashes = {normalized_text_sha256(str(row.get("text") or "")) for row in selected}
    report = ledger.admit(
        selected,
        batch_id=batch_id,
        source_artifact=source_artifact,
        unbind_clean_hashes=clean_hashes,
    )
    after = ledger.reserve_counts()
    for key in CLASSIFY_SLICES:
        if int(after.get(key, 0)) < int(before.get(key, 0)):
            refuse(f"STOP: {key} decreased")
    if int(after.get("unbind_clean", 0)) < int(before.get("unbind_clean", 0)):
        refuse("STOP: unbind_clean decreased")
    if report["unique_routed_to_train_candidate"]:
        refuse("clean-unbind admission routed rows to TRAIN_CANDIDATE")
    report = dict(report)
    report["reserve_counts_before"] = before
    report["reserve_counts_after"] = after
    report["rejection_counts"] = reason_counts(rejections)
    report["rejected_hashes"] = len(rejections)
    report["admissible_before_cap"] = len(admissible)
    report["selected_rows"] = len(selected)
    report["clean_account"] = clean_account
    report["diversity"] = diversity_report(selected)
    report["unbind_clean_definition"] = UNBIND_CLEAN_DEFINITION
    report["contract_shape"] = CONTRACT_SHAPE
    report["vendor_calls"] = 0
    return report


def wordnet_license_text(index_dir: str | Path) -> str:
    path = Path(index_dir) / "LICENSE"
    if not path.is_file():
        path = Path(index_dir).parent / "LICENSE"
    if not path.is_file():
        refuse("WordNet LICENSE file is missing")
    text = path.read_text(encoding="utf-8", errors="replace")
    assert_wordnet_license(text)
    return text


WORDNET_LICENSE = (
    "WordNet 3.0 Copyright 2006 by Princeton University. "
    "Permission to use, copy, modify and distribute this software and "
    "database and its documentation for any purpose and without fee or "
    "royalty is granted, provided the copyright notice and statements "
    "appear on all copies."
)


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            refuse(f"{path} line {index} is not JSON")
        if not isinstance(obj, dict):
            refuse(f"{path} line {index} must be an object")
        rows.append(obj)
    return rows


def _walk_forbid(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"text", "normalized_text", "raw_text", "surface", "fillers"}:
                refuse(f"receipt must not carry {key}")
            _walk_forbid(item)
    elif isinstance(value, list):
        for item in value:
            _walk_forbid(item)


def planning_progress(counts: Mapping[str, int]) -> list[dict[str, Any]]:
    rows = []
    for key, target in PLANNING_TARGETS.items():
        have = int(counts.get(key, 0))
        rows.append(
            {
                "slice": key,
                "current": have,
                "planning_target": target,
                "planning_target_class": "PLANNING_TARGET",
                "progress": have / target if target else 0,
                "gap_vs_planning_target": max(target - have, 0),
                "minimum_required": "NOT_COMPUTABLE",
            }
        )
    return rows


def admission_result_label(before: Mapping[str, int], after: Mapping[str, int], gate: Mapping[str, Any]) -> str:
    for key in CLASSIFY_SLICES:
        if int(after.get(key, 0)) < int(before.get(key, 0)):
            refuse(f"STOP: {key} decreased")
    if int(after.get("unbind_clean", 0)) <= int(before.get("unbind_clean", 0)):
        return "ACQUISITION_BLOCKED"
    if gate.get("eligible") is True:
        return "SELECT_003_ELIGIBLE"
    if int(after.get("unbind_clean", 0)) > 0:
        return "CLEAN_UNBIND_PARTIALLY_FILLED"
    return "ACQUISITION_BLOCKED"


ZERO_SUPPORT_FAMILIES = (
    "relationship-dating",
    "conflict-aggression",
    "sports-competition",
    "fashion-aesthetic",
    "regional-cultural",
    "spiritual-mystic",
)


def main(argv: Sequence[str] | None = None) -> int:
    """Acquire clean-unbind reserve rows. Does not train or score."""
    import argparse
    import sys
    from datetime import datetime, timezone

    from .unbind_settlement import append_events, event_from_decision, latest_by_hash, load_events

    parser = argparse.ArgumentParser(description="Hyperlex clean-unbind reserve acquisition")
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--train-export", required=True)
    parser.add_argument("--index-dir", required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--source-artifact", required=True)
    parser.add_argument("--settlement-log", required=True)
    parser.add_argument("--operator", required=True)
    parser.add_argument("--rows-out", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    if Path(args.receipt).exists():
        refuse(f"receipt already exists: {args.receipt}")
    if Path(args.rows_out).exists():
        refuse(f"rows output already exists: {args.rows_out}")

    index_dir = Path(args.index_dir)
    license_body = wordnet_license_text(index_dir)
    license_path = index_dir / "LICENSE"
    if not license_path.is_file():
        license_path = index_dir.parent / "LICENSE"
    atoms = read_wordnet_index(index_dir)
    rows = rows_from_wordnet_atoms(atoms, license=WORDNET_LICENSE)
    ledger = IdentityLedger.load(args.ledger)
    before = ledger.reserve_counts()
    train_rows = load_jsonl(Path(args.train_export))
    admissible, rejections, clean_account = gate_rows(
        rows,
        train_rows=train_rows,
        ledger=ledger,
        require_settlement=False,
    )
    room = int(PLANNING_TARGETS["unbind_clean"]) - int(before.get("unbind_clean", 0))
    selected = select_diverse(admissible, max(room, 0))
    settled_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    events = []
    for row in selected:
        events.append(
            event_from_decision(
                normalized_text_sha256=normalized_text_sha256(str(row.get("text") or "")),
                decision="ACCEPT",
                target_sha256=target_sha256(list(row.get("fillers") or [])),
                target_provenance=str(row.get("target_origin") or ""),
                operator=args.operator,
                settled_at=settled_at,
                decision_basis="source_lemma_token_identity",
            )
        )
    append_events(args.settlement_log, events)
    settlements = latest_by_hash(load_events(args.settlement_log))
    prior_events = len(ledger.events)
    report = admit_clean_unbind(
        ledger,
        selected,
        batch_id=args.batch_id,
        source_artifact=args.source_artifact,
        train_rows=train_rows,
        settlements=settlements,
    )
    after = ledger.reserve_counts()
    train_hashes = {
        normalized_text_sha256(str(row.get("text") or ""))
        for row in train_rows
    }
    gate = ledger.select_003_gate(train_hashes)
    label = admission_result_label(before, after, gate)
    events_path = Path(args.ledger) / "events.jsonl"
    events_sha256_before = file_sha256(events_path)
    written = ledger.persist_append(args.ledger, prior_events)
    events_sha256_after = file_sha256(events_path)
    Path(args.settlement_log).chmod(0o600)
    rows_out = Path(args.rows_out)
    rows_out.parent.mkdir(parents=True, exist_ok=True)
    rows_out.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in selected),
        encoding="utf-8",
    )
    rows_out.chmod(0o600)
    receipt = {
        "schema": "hyperlex.eval_unbind_acquisition.v1",
        "batch_id": args.batch_id,
        "source": "Princeton WordNet 3.0 index lemmas",
        "source_artifact": args.source_artifact,
        "source_rights": WORDNET_LICENSE,
        "license_file_sha256": file_sha256(license_path),
        "raw_artifact_sha256": file_sha256(args.source_artifact),
        "license_notice_present": "Copyright 2006 by Princeton University" in license_body,
        "schema_contract": CONTRACT_SHAPE,
        "unbind_clean_definition": UNBIND_CLEAN_DEFINITION,
        "timestamp": settled_at,
        "collector": args.operator,
        "transformation_pipeline": [
            "read index.noun/verb/adj/adv lemmas only",
            "do not read data.* glosses",
            "underscore to space",
            "keep 2..6 tokens and atom length <= 80",
            "emit positional and type_slot from export._unbind_dual_scheme_rows shape",
            "fillers are the source lemma tokens",
            "novelty screen via normalized_text_sha256",
            "clean_surface against train split",
            "ACCEPT settlement where fillers equal the lemma tokens",
            "IdentityLedger.admit with derived unbind_clean hashes",
        ],
        "index_mwe_atoms": len(atoms),
        "dual_scheme_rows": len(rows),
        "screen_rejection_counts": reason_counts(rejections),
        "screen_clean_account": {
            key: clean_account.get(key)
            for key in (
                "n_input",
                "n_kept",
                "n_excluded_trained_key",
                "n_excluded_trained_text",
                "n_excluded_train_split_text",
                "definition",
                "train_split_rows",
            )
        },
        "admissible_before_planning_cap": len(admissible),
        "selected_rows": len(selected),
        "settlement": {
            "schema": "hyperlex.eval_unbind_settlement.v1",
            "log": args.settlement_log,
            "events_appended": len(events),
            "decisions": {"ACCEPT": len(events), "CORRECT_TARGET": 0, "REJECT": 0, "UNRESOLVED": 0},
            "decision_basis": "source_lemma_token_identity",
        },
        "admission": {
            "events_sha256_before": events_sha256_before,
            "events_sha256_after": events_sha256_after,
            "events_appended": written,
            "unique_admitted_to_eval_reserve": report["unique_admitted_to_eval_reserve"],
            "unique_routed_to_train_candidate": report["unique_routed_to_train_candidate"],
            "rejected_existing_identities": report["rejected_existing_identities"],
            "model_outcomes_consulted": report["model_outcomes_consulted"],
        },
        "diversity": report["diversity"],
        "reserve_counts_before": before,
        "reserve_counts_after": after,
        "planning_progress": planning_progress(after),
        "select_003_gate": gate,
        "admission_result": label,
        "select_003": "NOT_DRAFTED",
        "vendor_calls": 0,
        "zero_support_families_not_collected": list(ZERO_SUPPORT_FAMILIES),
        "evaluation_quality_note": (
            "Representation completeness is separate from evaluation quality. "
            "This batch is one lexicon, class INFERRED, lineage none."
        ),
    }
    _walk_forbid(receipt)
    receipt_path = Path(args.receipt)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt_path.chmod(0o600)
    public = {
        "admission_result": label,
        "reserve_counts_before": before,
        "reserve_counts_after": after,
        "selected_rows": len(selected),
        "admissible_before_planning_cap": len(admissible),
        "events_appended": written,
        "vendor_calls": 0,
        "select_003": "NOT_DRAFTED",
        "gate_eligible": gate.get("eligible"),
        "diversity": report["diversity"],
        "screen_rejection_counts": reason_counts(rejections),
    }
    _walk_forbid(public)
    sys.stdout.write(json.dumps(public, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
