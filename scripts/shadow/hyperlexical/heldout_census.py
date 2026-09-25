"""Read-only census of a fresh held-out drawn from the current pool.

Counts release-pool rows that pass every admission rule. Writes nothing.
Does not train, load a model, score a test slice, or call the holdout scorer.

The trained union is the release train split plus rows from ``--trained``
files (force/hard JSONL and checkpoint train receipts). Test-split rows are
discarded by the ``split`` field only.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .filler_filter import assert_publishable_vocab
from .selection_surface import drop_test_rows, jaccard, lenient_copy_hit, provenance_source, row_id
from .soft_ceiling import row_key

SCHEMA = "hyperlex.heldout_census.v0.1"
JACCARD_MIN = 0.5
DRAW_READY_MIN = 470
TOPUP_MIN = 150
SOURCE_CAP = 0.60
GROUP_KEY_DEFINITION = (
    "NFKC + casefold + strip punctuation, whitespace, and URLs, plus the sorted filler set"
)
_URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_ID_LIST_KEYS = frozenset({"row_ids", "ids"})
_RECEIPT_PATH_KEYS = ("unbind_force_train_path", "unbind_hard_atoms_path")
_ENV_PATH_KEYS = ("HYPERLEX_UNBIND_FORCE_TRAIN_PATH", "HYPERLEX_UNBIND_HARD_ATOMS_PATH")


def normalize_group_text(text: str) -> str:
    """NFKC, casefold, then drop URLs, punctuation, and extra whitespace."""
    raw = unicodedata.normalize("NFKC", str(text or "")).casefold()
    raw = _URL.sub(" ", raw)
    raw = "".join(ch if ch.isalnum() else " " for ch in raw)
    return " ".join(raw.split())


def normalized_fillers(row: Mapping[str, Any]) -> tuple[str, ...]:
    fillers: set[str] = set()
    for item in row.get("fillers") or []:
        token = normalize_group_text(str(item))
        if token:
            fillers.add(token)
    return tuple(sorted(fillers))


def group_key(row: Mapping[str, Any]) -> tuple[str, tuple[str, ...]]:
    return (normalize_group_text(str(row.get("text") or "")), normalized_fillers(row))


def holdout_key(row: Mapping[str, Any]) -> str:
    """Same ``task|text|scheme`` identity the holdout manifest hashes. Not a test read."""
    text, scheme = row_key({"text": str(row.get("text") or ""), "role_scheme": row.get("role_scheme")})
    return "|".join((str(row.get("task") or ""), text, scheme))


def exclusion_ids(row: Mapping[str, Any]) -> set[str]:
    return {row_id(row), holdout_key(row)}


def admitted_ids_sha256(ids: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(sorted(ids)).encode("utf-8")).hexdigest()


def source_over_cap(max_count: int, n: int) -> bool:
    """True when ``max_count / n > 0.60``. Exact at 60% is inside the cap."""
    if n <= 0:
        return False
    return 5 * max_count > 3 * n


def pinned_verdict(n_admitted: int, max_source_count: int) -> str:
    """Census pin. ``SOURCE_CAP`` is a draw that clears 470 but breaks the 60% cap."""
    if n_admitted >= DRAW_READY_MIN and not source_over_cap(max_source_count, n_admitted):
        return "DRAW_READY"
    if n_admitted >= DRAW_READY_MIN:
        return "SOURCE_CAP"
    if n_admitted >= TOPUP_MIN:
        return "TOPUP_NEEDED"
    return "POOL_EXHAUSTED"


def publish_census(
    candidate: str,
    admitted_hash: str,
    code_commit: str | None,
    prior: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """HOLD until a same-SHA rerun matches the admitted-ID hash."""
    if prior is None:
        status = "pending"
    elif prior.get("code_commit") == code_commit and prior.get("admitted_ids_sha256") == admitted_hash:
        return {
            "candidate": candidate,
            "published": candidate,
            "hold": False,
            "reproduce": "matched",
        }
    else:
        status = "mismatch"
    return {"candidate": candidate, "published": "HOLD", "hold": True, "reproduce": status}


class FillerIndex:
    """Filler-set lookup for Jaccard siblings. Empty sets are not indexed."""

    def __init__(self) -> None:
        self._sets: list[frozenset[str]] = []
        self._known: set[frozenset[str]] = set()
        self._inv: dict[str, list[int]] = {}

    def __len__(self) -> int:
        return len(self._sets)

    def add(self, fillers: frozenset[str]) -> None:
        if not fillers or fillers in self._known:
            return
        index = len(self._sets)
        self._known.add(fillers)
        self._sets.append(fillers)
        for token in fillers:
            self._inv.setdefault(token, []).append(index)

    def sibling(self, fillers: frozenset[str]) -> bool:
        if not fillers:
            return False
        hits: dict[int, int] = {}
        for token in fillers:
            for index in self._inv.get(token, ()):
                hits[index] = hits.get(index, 0) + 1
        for index in hits:
            if jaccard(fillers, self._sets[index]) >= JACCARD_MIN:
                return True
        return False


class SeenIndex:
    """Group keys and filler sets from the trained union."""

    def __init__(self) -> None:
        self.keys: set[tuple[str, tuple[str, ...]]] = set()
        self.texts: set[str] = set()
        self.fillers = FillerIndex()

    def add_row(self, row: Mapping[str, Any], *, text_if_no_fillers: bool = False) -> None:
        key = group_key(row)
        self.keys.add(key)
        fillers = frozenset(key[1])
        if fillers:
            self.fillers.add(fillers)
        elif text_if_no_fillers and key[0]:
            self.texts.add(key[0])

    def blocks(self, row: Mapping[str, Any]) -> bool:
        key = group_key(row)
        if key in self.keys:
            return True
        if key[0] and key[0] in self.texts:
            return True
        return self.fillers.sibling(frozenset(key[1]))


def _publishable(row: Mapping[str, Any]) -> bool:
    fillers = [str(item) for item in (row.get("fillers") or [])]
    try:
        assert_publishable_vocab(fillers)
    except ValueError:
        return False
    return True


def _in_holdout(row: Mapping[str, Any], holdout_ids: set[str]) -> bool:
    if not holdout_ids:
        return False
    return bool(exclusion_ids(row) & holdout_ids)


def rule_failures(row: Mapping[str, Any], seen: SeenIndex, holdout_ids: set[str]) -> list[str]:
    """Rules in admission order. The list is every failure, not only the first."""
    fails: list[str] = []
    task = str(row.get("task") or "")
    in_text = bool(lenient_copy_hit(row))
    if task == "unbind":
        task_ok = True
    elif task == "classify+unbind":
        task_ok = in_text
    else:
        task_ok = False
    if not task_ok:
        fails.append("1")
    if not in_text:
        fails.append("2")
    if seen.blocks(row):
        fails.append("3")
    if not _publishable(row):
        fails.append("4")
    if _in_holdout(row, holdout_ids):
        fails.append("5")
    return fails


def _index_pool(pool: Sequence[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    by_text: dict[str, list[Mapping[str, Any]]] = {}
    for row in pool:
        text = normalize_group_text(str(row.get("text") or ""))
        if text:
            by_text.setdefault(text, []).append(row)
    return by_text


def build_seen(
    pool: Sequence[Mapping[str, Any]],
    trained_rows: Sequence[Mapping[str, Any]],
) -> SeenIndex:
    """Train-split rows plus ``--trained`` rows. Test rows are not accepted here."""
    seen = SeenIndex()
    by_text = _index_pool(pool)
    for row in pool:
        if row.get("split") == "train":
            seen.add_row(row, text_if_no_fillers=True)
    for row in trained_rows:
        if row.get("split") == "test":
            continue
        fillers = [item for item in (row.get("fillers") or []) if str(item).strip()]
        if fillers:
            seen.add_row(row)
            continue
        text = normalize_group_text(str(row.get("text") or ""))
        if text:
            seen.texts.add(text)
        for match in by_text.get(text, ()):
            seen.add_row(match)
    return seen


def _zero_rules() -> dict[str, int]:
    return {str(number): 0 for number in range(1, 6)}


def _source_stats(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    sources: Counter[str] = Counter()
    schemes: Counter[str] = Counter()
    classes: Counter[str] = Counter()
    for row in rows:
        sources[str(row.get("provenance_source") or provenance_source(row))] += 1
        scheme = row.get("role_scheme")
        schemes["" if scheme is None else str(scheme)] += 1
        classes[str(row.get("class") or "").upper()] += 1
    n = len(rows)
    if sources:
        top = max(sources.values())
        name = sorted(label for label, count in sources.items() if count == top)[0]
        share = top / n
    else:
        name, top, share = None, 0, 0.0
    return {
        "n": n,
        "by_source": dict(sorted(sources.items())),
        "by_scheme": dict(sorted(schemes.items())),
        "by_class": dict(sorted(classes.items())),
        "max_source": name,
        "max_source_count": top,
        "max_source_share": share,
    }


def census_rows(
    rows: Sequence[Mapping[str, Any]],
    trained_rows: Sequence[Mapping[str, Any]] = (),
    holdout_ids: Iterable[str] = (),
    *,
    id_list_present: bool = True,
    n_test_discarded: int | None = None,
    n_test_dropped_before_release: int | None = None,
    release_set: Mapping[str, Any] | None = None,
    trained_files: Sequence[str] = (),
    code_commit: str | None = None,
    code_tree_sha256: str | None = None,
    prior: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Admit pool rows. Drops ``split=test`` before any text or gold is used."""
    if n_test_discarded is None:
        pool, n_test_discarded = drop_test_rows(rows)
    else:
        pool = [dict(row) for row in rows if row.get("split") != "test"]
    holdout = {str(item) for item in holdout_ids}
    seen = build_seen(pool, trained_rows)
    first = _zero_rules()
    every = _zero_rules()
    admitted: list[dict] = []
    admitted_ids: list[str] = []
    for row in pool:
        fails = rule_failures(row, seen, holdout)
        if not fails:
            admitted.append(dict(row))
            admitted_ids.append(row_id(row))
            continue
        first[fails[0]] += 1
        for rule in fails:
            every[rule] += 1
    admitted_stats = _source_stats(admitted)
    n_admitted = admitted_stats["n"]
    candidate = pinned_verdict(n_admitted, int(admitted_stats["max_source_count"]))
    id_hash = admitted_ids_sha256(admitted_ids)
    verdict = publish_census(candidate, id_hash, code_commit, prior)
    verdict["checks"] = {
        "n_admitted": n_admitted,
        "max_source_share": admitted_stats["max_source_share"],
        "source_cap": SOURCE_CAP,
        "source_cap_ok": not source_over_cap(int(admitted_stats["max_source_count"]), n_admitted),
        "holdout_id_list_present": id_list_present,
    }
    return {
        "schema": SCHEMA,
        "brier": None,
        "read_only": True,
        "allow_train": False,
        "cpu_only": True,
        "test_slices_scored": False,
        "n_test_discarded": n_test_discarded,
        "n_test_dropped_before_release": n_test_dropped_before_release,
        "test_dropped_before_release_filtering": n_test_dropped_before_release is not None,
        "n_pool": len(pool),
        "n_admitted": n_admitted,
        "n_rejected": len(pool) - n_admitted,
        "group_key": {
            "definition": GROUP_KEY_DEFINITION,
            "jaccard_sibling_min": JACCARD_MIN,
            "compared_to": [
                "train split of the release pool",
                "files passed with --trained (force/hard JSONL and train receipts)",
            ],
        },
        "rules": {
            "1": "unbind, or classify+unbind whose gold fillers are tokens of the text",
            "2": "every gold filler is a token of the text",
            "3": "no group-key twin and no filler-Jaccard >= 0.5 sibling in the trained union",
            "4": "gold passes assert_publishable_vocab",
            "5": "row id is not in the holdout manifest ID list",
        },
        "rejected": {"first_failing": first, "all_failing": every},
        "admitted": admitted_stats,
        "admitted_ids_sha256": id_hash,
        "n_seen_group_keys": len(seen.keys),
        "n_seen_filler_sets": len(seen.fillers),
        "holdout": {"n_ids": len(holdout), "id_list_present": id_list_present},
        "trained_files": [str(path) for path in trained_files],
        "release_set": dict(release_set) if release_set else {"release_set": None},
        "verdict": verdict,
        "code_commit": code_commit,
        "code_tree_sha256": code_tree_sha256,
    }


def _refuse_embedded_rows(obj: Any) -> None:
    if isinstance(obj, dict):
        if "text" in obj and ("fillers" in obj or "task" in obj):
            raise SystemExit("REFUSE: holdout manifest contains row content; reading only an ID list")
        for value in obj.values():
            _refuse_embedded_rows(value)
    elif isinstance(obj, list):
        for value in obj:
            _refuse_embedded_rows(value)


def _collect_ids(obj: Any, found: list[str], present: list[bool]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in _ID_LIST_KEYS and isinstance(value, list):
                if not all(isinstance(item, str) for item in value):
                    raise SystemExit("REFUSE: holdout ID list must be strings")
                present.append(True)
                found.extend(value)
            elif isinstance(value, (dict, list)):
                _collect_ids(value, found, present)
    elif isinstance(obj, list):
        for value in obj:
            if isinstance(value, (dict, list)):
                _collect_ids(value, found, present)


def load_holdout_ids(path: str | Path) -> tuple[set[str], bool]:
    """Read the manifest's ID list and nothing else.

    Accepts a bare JSON list of strings, or string lists under ``row_ids`` / ``ids``.
    Slice hashes, metric names, rules, and trained-file paths are not IDs.
    """
    file = Path(path)
    if not file.is_file():
        raise SystemExit(f"REFUSE: holdout manifest is not a file: {file}")
    if "holdout-scores" in file.name:
        raise SystemExit(f"REFUSE: will not read holdout scores {file}")
    payload = json.loads(file.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        if not all(isinstance(item, str) for item in payload):
            raise SystemExit("REFUSE: holdout ID list must be strings")
        return set(payload), True
    if not isinstance(payload, dict):
        raise SystemExit("REFUSE: holdout manifest must be a JSON object or an ID list")
    _refuse_embedded_rows(payload)
    found: list[str] = []
    present: list[bool] = []
    _collect_ids(payload, found, present)
    return set(found), bool(present)


def _is_receipt(obj: Mapping[str, Any]) -> bool:
    schema = str(obj.get("schema") or "")
    if "train_receipt" in schema:
        return True
    return any(key in obj for key in _RECEIPT_PATH_KEYS)


def _take_trained_row(obj: Any, path: Path, index: int) -> dict | None:
    if not isinstance(obj, dict):
        raise SystemExit(f"REFUSE: {path} line {index} is not an object")
    if obj.get("split") == "test":
        return None
    if "text" not in obj:
        raise SystemExit(f"REFUSE: {path} line {index} has no text")
    return obj


def load_jsonl_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"REFUSE: {path} line {index} is not JSON") from exc
        row = _take_trained_row(obj, path, index)
        if row is not None:
            rows.append(row)
    return rows


def _resolve_receipt_path(name: str, receipt_dir: Path, search_dirs: Sequence[Path]) -> Path:
    candidate = Path(name)
    if candidate.is_file():
        return candidate
    options = [receipt_dir / candidate.name]
    for directory in search_dirs:
        options.append(Path(directory) / candidate.name)
    for option in options:
        if option.is_file():
            return option
    raise SystemExit(f"REFUSE: train receipt path not found: {name}")


def _receipt_names(obj: Mapping[str, Any]) -> list[str]:
    names: list[str] = []
    for key in _RECEIPT_PATH_KEYS:
        value = str(obj.get(key) or "").strip()
        if value:
            names.append(value)
    env = obj.get("hyperlex_env")
    if isinstance(env, dict):
        for key in _ENV_PATH_KEYS:
            value = str(env.get(key) or "").strip()
            if value and value not in names:
                names.append(value)
    return names


def load_trained_files(paths: Sequence[str]) -> tuple[list[dict], list[str]]:
    """Load force/hard JSONL and any JSONL named by a train receipt."""
    files = [Path(path) for path in paths]
    for file in files:
        if not file.is_file():
            raise SystemExit(f"REFUSE: --trained is not a file: {file}")
        if "holdout" in file.name.lower():
            raise SystemExit(f"REFUSE: will not read holdout path as training data: {file}")
    jsonl_paths: list[Path] = []
    receipts: list[tuple[Path, dict]] = []
    for file in files:
        try:
            parsed = json.loads(file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict) and _is_receipt(parsed):
            receipts.append((file, parsed))
        else:
            jsonl_paths.append(file)
    search_dirs = [path.parent for path in jsonl_paths]
    rows: list[dict] = []
    loaded: list[str] = []
    for file in jsonl_paths:
        rows.extend(load_jsonl_rows(file))
        loaded.append(str(file))
    for file, obj in receipts:
        names = _receipt_names(obj)
        if not names:
            raise SystemExit(f"REFUSE: train receipt lists no force/hard files: {file}")
        loaded.append(str(file))
        seen_paths: set[Path] = set()
        for name in names:
            found = _resolve_receipt_path(name, file.parent, search_dirs)
            resolved = found.resolve()
            if resolved in seen_paths:
                continue
            seen_paths.add(resolved)
            if "holdout" in found.name.lower():
                raise SystemExit(f"REFUSE: train receipt points at a holdout path: {found}")
            rows.extend(load_jsonl_rows(found))
            loaded.append(str(found))
    return rows, loaded


def write_census(report: Mapping[str, Any], out_dir: str | Path) -> Path:
    """Write ``census.json`` and no other file."""
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    target = (directory / "census.json").resolve()
    if target.parent != directory.resolve():
        raise SystemExit("REFUSE: census output escaped --out-dir")
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target
