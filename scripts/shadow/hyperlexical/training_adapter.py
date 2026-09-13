"""Pure reviewed-contract projection. Not runnable through the legacy loop yet.

Provenance: Hyperlex Spec 007; base 54db59e0cb1e5c800d49498c61cce179b72c4f7d.
"""
from collections import Counter
from copy import deepcopy

from .layout import FAMILIES, UNK
from .training_contracts import digest, validate_dataset
from .training_routing import route_rows


def adapt_reviewed(dataset, *, expected_ontology):
    validate_dataset(dataset)
    if not isinstance(expected_ontology, str) or not expected_ontology.strip():
        raise ValueError("expected ontology required")
    sources = {s["source_id"]: s for s in dataset["sources"]}
    splits = {s["example_id"]: s["partition"] for s in dataset["split"]["assignments"]}
    rows, excluded = [], []
    for ann in dataset["annotations"]:
        if ann["ontology_version"] != expected_ontology:
            raise ValueError("ontology mismatch")
        active = {head: label for head, label in ann["labels"].items() if label["loss_mask"]}
        if set(active) - {"family", "structure"}:
            raise ValueError("unsupported active supervision")
        if any(label["status"] != "reviewed" for label in active.values()):
            raise ValueError("active labels must be reviewed")
        if "family" in active:
            values = active["family"]["values"]
            if len(values) != 1 or values[0] not in FAMILIES:
                raise ValueError("family must be one existing ontology value")
        if not active:
            excluded.append({"example_id": ann["example_id"], "reason": "NO_ACTIVE_SUPERVISION"})
            continue
        family, structure = "family" in active, "structure" in active
        source = sources[ann["source_id"]]
        spans = deepcopy(ann["spans"]) if structure else []
        row = {
            "example_id": ann["example_id"], "source_id": source["source_id"],
            "source_sha256": source["text_sha256"], "text": source["raw_text"],
            "task": "classify+unbind" if family and structure else "classify" if family else "unbind",
            "split": {"train": "train", "dev": "val", "test": "test"}[splits[ann["example_id"]]],
            "loss_masks": {"family": family, "structure": structure},
            "labels": deepcopy(ann["labels"]), "ontology_version": expected_ontology,
            "group_ids": list(ann["group_ids"]), "occurrence_spans": spans,
            "roles": [s["role"] for s in spans], "fillers": [s["text"] for s in spans],
            "role_scheme": "reviewed_occurrences", "offset_unit": "unicode_codepoint",
        }
        if family:
            row["lineage"] = active["family"]["values"][0]
        rows.append(row)
    _, routing = route_rows(rows)
    assert len(rows) + len(excluded) == len(dataset["annotations"])
    return {"status": "ADAPTED_NOT_RUNNABLE", "rows": rows, "excluded": excluded,
            "dataset_sha256": digest(dataset), "rows_sha256": digest(rows),
            "input_examples": len(dataset["annotations"]), "routing": routing,
            "training_ready": False, "name_gate": False,
            "remaining": ["OCCURRENCE_AWARE_LOOP_ALIGNMENT", "SOURCE_REVIEW_EVIDENCE",
                          "EVALUATION_AND_RUNTIME_CHECKS"]}


def align_occurrences(text, spans, offsets):
    """Exact codepoint spans only; reject truncation, gaps and token spillover.

    Offsets must come from the same pinned tokenization used for encoding.
    Whitespace gaps between subwords are allowed; no first-occurrence fallback.
    This constructs gold-span diagnostic targets, not bound-vector evaluation.
    """
    if not isinstance(offsets, list):
        raise TypeError("offset list required")
    previous = 0
    for pair in offsets:
        if (not isinstance(pair, (list, tuple)) or len(pair) != 2
                or any(type(n) is not int for n in pair)):
            raise ValueError("integer offset pairs required")
        start, end = pair
        if pair == [0, 0] or pair == (0, 0):
            continue  # tokenizer special/padding position
        if start < previous or start >= end or end > len(text):
            raise ValueError("invalid or overlapping token offsets")
        previous = end
    aligned = []
    for span in spans:
        start, end = span["start"], span["end"]
        if (type(start) is not int or type(end) is not int or start < 0 or start >= end
                or end > len(text) or text[start:end] != span["text"]):
            raise ValueError("invalid occurrence span")
        indices, covered = [], set()
        for i, (s, e) in enumerate(offsets):
            if e <= s or e <= start or s >= end:
                continue
            if s < start or e > end:
                raise ValueError("token crosses occurrence boundary")
            indices.append(i)
            covered.update(range(s, e))
        if not indices or any(i not in covered and not text[i].isspace() for i in range(start, end)):
            raise ValueError("occurrence truncated or uncovered")
        aligned.append({**deepcopy(span), "token_indices": indices})
    return aligned


def prepare_reviewed(dataset, *, expected_ontology, tokenization=None):
    """Standalone data plan; never removes the legacy trainer guard.

    Tokenization is a strict dataset-bound offset sidecar. It is a declaration,
    not independent proof that a named tokenizer produced those offsets.
    """
    adapted = adapt_reviewed(dataset, expected_ontology=expected_ontology)
    rows = adapted["rows"]
    structure_ids = {r["example_id"] for r in rows if r["loss_masks"]["structure"]}
    if tokenization is not None:
        if (not isinstance(tokenization, dict)
                or set(tokenization) != {"dataset_sha256", "tokenizer_revision", "offset_unit", "examples"}
                or tokenization["dataset_sha256"] != adapted["dataset_sha256"]
                or tokenization["offset_unit"] != "unicode_codepoint"
                or not isinstance(tokenization["tokenizer_revision"], str)
                or not tokenization["tokenizer_revision"].strip()
                or not isinstance(tokenization["examples"], dict)
                or set(tokenization["examples"]) != structure_ids):
            raise ValueError("tokenization contract mismatch")
        digest(tokenization)
    selected = {h: {p: [] for p in ("train", "val")} for h in ("family", "structure")}
    blocked, outcomes = [], Counter()
    for row in rows:
        eid = row["example_id"]
        if row["loss_masks"]["structure"]:
            if tokenization is None:
                blocked.append({"example_id": eid, "reason": "MISSING_TOKENIZATION"})
            else:
                row["aligned_occurrences"] = align_occurrences(
                    row["text"], row["occurrence_spans"], tokenization["examples"][eid])
        if row["split"] == "test":
            outcomes["reserved_test"] += 1
            continue
        outcomes["selected"] += 1
        for head, active in row["loss_masks"].items():
            if active and (head != "structure" or tokenization is not None):
                selected[head][row["split"]].append(eid)
    blockers = []
    if blocked:
        blockers.append("MISSING_TOKENIZATION")
    if not any(selected[h]["train"] for h in selected):
        blockers.append("NO_TRAIN_SUPERVISION")
    for head in selected:
        if selected[head]["train"] and not selected[head]["val"]:
            blockers.append("NO_DEV_SUPERVISION:" + head)
    if not any(a["partition"] == "test" for a in dataset["split"]["assignments"]):
        blockers.append("NO_RESERVED_TEST")
    # Build learned target vocabulary from selected training rows only. Never
    # turn unseen held-out surfaces into a new output neuron or an exact match.
    train_ids = set(selected["structure"]["train"])
    train_rows = [r for r in rows if r["example_id"] in train_ids]
    vocabularies = {key: [UNK] + sorted({value for r in train_rows for value in r[key]} - {UNK})
                    for key in ("roles", "fillers")}
    maps = {key: {value: i for i, value in enumerate(vocab)} for key, vocab in vocabularies.items()}
    for row in rows:
        if row["loss_masks"]["family"]:
            row["family_target_id"] = FAMILIES.index(row["lineage"])
        if row["loss_masks"]["structure"]:
            if any(UNK in row[key] for key in maps):
                raise ValueError("reserved unknown target cannot be supervised")
            row["target_ids"] = {key: [maps[key].get(value, 0) for value in row[key]] for key in maps}
            row["target_known"] = {key: [value in maps[key] for value in row[key]] for key in maps}
    return {"version": "reviewed_preparation.v1", "status": "DATA_BLOCKED" if blockers else "PREPARED_NOT_RUNNABLE",
            "rows": rows, "excluded": adapted["excluded"], "alignment_blocked": blocked,
            "selected_example_ids": selected, "row_outcomes": dict(outcomes),
            "input_examples": adapted["input_examples"], "blockers": blockers,
            "dataset_sha256": adapted["dataset_sha256"], "rows_sha256": digest(rows),
            "tokenization_sha256": digest(tokenization) if tokenization is not None else None,
            "tokenizer_revision": tokenization["tokenizer_revision"] if tokenization is not None else None,
            "train_only_vocabularies": vocabularies, "families": list(FAMILIES),
            "legacy_routing_diagnostic": adapted["routing"], "training_ready": False, "name_gate": False,
            "remaining": ["SOURCE_REVIEW_EVIDENCE", "TRAINER_CONTRACT_INTEGRATION",
                          "EVALUATION_AND_RESUME_SMOKE", "OPERATOR_RUN_GATE"]}
