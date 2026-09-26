"""Read-only row flags for a later manifest-v2 holdout draw.

Annotations only. This module does not relabel a row, replace a filler,
invent a label, or promote anything to OBSERVED. It does not train, load a
model, or score a test slice.

``split=test`` rows are discarded by :func:`selection_surface.drop_test_rows`
before text, gold, or hashes are read. Output is row ids, normalized-text
hashes, sources, splits, and flag names.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .heldout_census import blocking_texts, normalize_group_text
from .selection_surface import drop_test_rows, lenient_copy_hit, provenance_source, row_id

SCHEMA = "hyperlex.row_flags.v0.1"
LIST_DIR = Path(__file__).resolve().parent / "lists"
UNDEFINED_TERMS_PATH = LIST_DIR / "undefined_fillers.txt"
JEV_PHRASES_PATH = LIST_DIR / "jev_selected_phrases.txt"
FLAG_ORDER = (
    "fallback_label",
    "gold_not_in_text",
    "demoted",
    "undefined_term",
    "jev_selected",
    "cross_split_text",
    "spent_or_trained_text",
    "holdout_ineligible",
)
BARRING_FLAGS = FLAG_ORDER[:-1]
_TRAIN_VAL = frozenset({"train", "val"})


def file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_term_file(path: str | Path) -> frozenset[str]:
    """Normalized terms. Blank lines and ``#`` comments are ignored."""
    terms: set[str] = set()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        token = normalize_group_text(raw)
        if token:
            terms.add(token)
    return frozenset(terms)


def _fillers(row: Mapping[str, Any]) -> list[str]:
    labels: list[str] = []
    for item in row.get("fillers") or []:
        text = str(item).strip()
        if text:
            labels.append(text)
    return labels


def _text_sha256(normalized: str) -> str:
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _cross_split_texts(pool: Sequence[Mapping[str, Any]]) -> set[str]:
    by_split: dict[str, set[str]] = {"train": set(), "val": set()}
    for row in pool:
        split = row.get("split")
        if split not in by_split:
            continue
        text = normalize_group_text(str(row.get("text") or ""))
        if text:
            by_split[split].add(text)
    return by_split["train"] & by_split["val"]


def row_flags(
    row: Mapping[str, Any],
    *,
    cross_texts: set[str],
    spent_texts: set[str],
    undefined_terms: frozenset[str],
    jev_phrases: frozenset[str],
) -> list[str]:
    """Flag names in canonical order. ``holdout_ineligible`` is the union."""
    fillers = _fillers(row)
    flags: list[str] = []
    if any(item.casefold() == "general" for item in fillers):
        flags.append("fallback_label")
    if fillers and not lenient_copy_hit(row):
        flags.append("gold_not_in_text")
    if str(row.get("gold_demote_reason") or "").strip():
        flags.append("demoted")
    if any(normalize_group_text(item) in undefined_terms for item in fillers):
        flags.append("undefined_term")
    text = normalize_group_text(str(row.get("text") or ""))
    filler_norms = {normalize_group_text(item) for item in fillers}
    filler_norms.discard("")
    if (text and text in jev_phrases) or (filler_norms & jev_phrases):
        flags.append("jev_selected")
    if text and text in cross_texts and row.get("split") in _TRAIN_VAL:
        flags.append("cross_split_text")
    if text and text in spent_texts:
        flags.append("spent_or_trained_text")
    if any(flag in BARRING_FLAGS for flag in flags):
        flags.append("holdout_ineligible")
    return flags


def _not_computed(
    *,
    trained_supplied: bool,
    holdout_supplied: bool,
    n_unresolved: int,
) -> list[str]:
    items = [
        "live ingest rows that exist only on the training machine and are absent from this export jsonl",
        "split=test rows (discarded by the split field before text, gold, or hashes are read)",
        "manifest-v2 draw, training, and gold promotion",
    ]
    if not trained_supplied:
        items.append("trained-row text (--trained was not passed)")
    if not holdout_supplied:
        items.append("holdout id list (--holdout-ids was not passed)")
    elif n_unresolved:
        items.append(
            f"{n_unresolved} holdout ids did not match a non-test export or trained row, "
            "so their text was not recovered"
        )
    return items


def _summary_counts(records: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, dict[str, int]]]:
    sources = sorted({str(rec["source"]) for rec in records if rec.get("split") in _TRAIN_VAL})
    counts: dict[str, dict[str, dict[str, int]]] = {
        source: {flag: {"train": 0, "val": 0} for flag in FLAG_ORDER}
        for source in sources
    }
    for rec in records:
        split = rec.get("split")
        if split not in _TRAIN_VAL:
            continue
        bucket = counts[str(rec["source"])]
        for flag in rec.get("flags") or []:
            if flag in bucket:
                bucket[flag][str(split)] += 1
    return counts


def flag_dataset(
    rows: Sequence[Mapping[str, Any]],
    trained_rows: Sequence[Mapping[str, Any]] = (),
    holdout_ids: Iterable[str] = (),
    *,
    id_list_present: bool = False,
    code_commit: str | None = None,
    code_tree_sha256: str | None = None,
    input_sha256: Mapping[str, Any] | None = None,
    trained_supplied: bool = False,
    holdout_supplied: bool = False,
    undefined_terms: frozenset[str] | None = None,
    jev_phrases: frozenset[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Flag non-test rows. The first action is ``drop_test_rows``."""
    pool, n_test_discarded = drop_test_rows(rows)
    trained, _trained_test = drop_test_rows(trained_rows)
    holdout = {str(item) for item in holdout_ids}
    blocked = blocking_texts(pool, trained, holdout)
    cross = _cross_split_texts(pool)
    if undefined_terms is None:
        undefined = load_term_file(UNDEFINED_TERMS_PATH)
    else:
        undefined = undefined_terms
    if jev_phrases is None:
        jev = load_term_file(JEV_PHRASES_PATH)
    else:
        jev = jev_phrases
    records: list[dict[str, Any]] = []
    for row in pool:
        text = normalize_group_text(str(row.get("text") or ""))
        flags = row_flags(
            row,
            cross_texts=cross,
            spent_texts=blocked["texts"],
            undefined_terms=undefined,
            jev_phrases=jev,
        )
        records.append(
            {
                "row_id": row_id(row),
                "normalized_text_sha256": _text_sha256(text),
                "source": provenance_source(row),
                "split": str(row.get("split") or ""),
                "flags": flags,
            }
        )
    records.sort(key=lambda rec: (rec["row_id"], rec["split"], rec["source"], tuple(rec["flags"])))
    trained_supplied = bool(trained_supplied or trained)
    holdout_supplied = bool(holdout_supplied or holdout)
    n_unresolved = int(blocked["n_holdout_ids_unresolved"])
    summary = {
        "schema": SCHEMA,
        "brier": None,
        "read_only": True,
        "cpu_only": True,
        "allow_train": False,
        "normalization": "NFKC + casefold + strip punctuation, whitespace, and URLs",
        "n_test_discarded": n_test_discarded,
        "n_rows": len(records),
        "n_train": sum(rec["split"] == "train" for rec in records),
        "n_val": sum(rec["split"] == "val" for rec in records),
        "n_holdout_ineligible": sum("holdout_ineligible" in rec["flags"] for rec in records),
        "counts": _summary_counts(records),
        "input_sha256": {
            "export": None if not input_sha256 else input_sha256.get("export"),
            "trained": [] if not input_sha256 else list(input_sha256.get("trained") or []),
            "holdout_ids": None if not input_sha256 else input_sha256.get("holdout_ids"),
            "undefined_fillers": file_sha256(UNDEFINED_TERMS_PATH),
            "jev_selected_phrases": file_sha256(JEV_PHRASES_PATH),
        },
        "holdout": {
            "n_ids": blocked["n_holdout_ids"],
            "n_resolved": blocked["n_holdout_ids_resolved"],
            "n_unresolved": n_unresolved,
            "id_list_present": bool(id_list_present or holdout),
        },
        "n_trained_rows": len(trained),
        "code_commit": code_commit,
        "code_tree_sha256": code_tree_sha256,
        "not_computed": _not_computed(
            trained_supplied=trained_supplied,
            holdout_supplied=holdout_supplied,
            n_unresolved=n_unresolved,
        ),
    }
    return records, summary


def load_export_jsonl(path: str | Path) -> list[dict]:
    """Load an export JSONL, including ``split=test`` rows.

    Parsing is required to see the split field. Flagging drops those rows
    before text or gold is used. A non-JSON line is a refusal, not a skip.
    """
    file = Path(path)
    rows: list[dict] = []
    for index, line in enumerate(file.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"REFUSE: {file} line {index} is not JSON") from exc
        if not isinstance(obj, dict):
            raise SystemExit(f"REFUSE: {file} line {index} is not an object")
        rows.append(obj)
    return rows


def write_flags(
    records: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
    out_dir: str | Path,
) -> tuple[Path, Path]:
    """Write ``flags.jsonl`` and ``flags_summary.json``. No other files."""
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    flags_path = (directory / "flags.jsonl").resolve()
    summary_path = (directory / "flags_summary.json").resolve()
    if flags_path.parent != directory.resolve() or summary_path.parent != directory.resolve():
        raise SystemExit("REFUSE: flags output escaped --out-dir")
    lines = [json.dumps(dict(rec), sort_keys=True, ensure_ascii=True) for rec in records]
    body = ("\n".join(lines) + "\n") if lines else ""
    flags_path.write_text(body, encoding="utf-8")
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return flags_path, summary_path
