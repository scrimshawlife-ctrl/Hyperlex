"""Selection-surface validity audit. Eval only. No torch. No gold writes.

Scores are computed by the caller (the Spark CLI). This module tags release
unbind val rows, builds slice metrics, and applies the post-rc1 verdict rule.

The frozen test split is spent. ``drop_test_rows`` discards every ``split=test``
row before tagging, sibling indexing, baselines, or metrics. Nothing here
opens a holdout manifest or calls the holdout scorer.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .export import TYPE_SLOT_TAGS
from .filler_filter import filter_unbind_rows
from .soft_ceiling import clean_surface
from .unbind_metrics import slot_counts, summarize_unbind_pairs, token_multiset_counts

# Published morph78 test-clean Wilson 95% from the spent rc1 receipt (n=306).
# Pinned, not recomputed. This audit does not read that split.
PINNED_MORPH78_TEST_CLEAN_WILSON = (0.673, 0.772)
Z95 = 1.959963984540054
JACCARD_SIBLING = 0.5
EXPECTED_SURFACE_N = {
    "broad_clean": 51,
    "force_fair": 164,
    "train_val_strict": 140,
}
RELEASE_VAL_TASKS = frozenset({"unbind", "classify+unbind"})
CANONICAL_RANK = ("morph78", "morph65", "rc1")


class HoldoutSliceRefused(RuntimeError):
    """Raised when a test-split row reaches tagging, scoring, or output."""


def wilson_interval(k: int, n: int, *, z: float = Z95) -> tuple[float, float] | None:
    """Wilson score interval for k successes in n trials. None when n is 0."""
    if n <= 0:
        return None
    if k < 0 or k > n:
        raise ValueError(f"wilson k={k} outside 0..n={n}")
    phat = k / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (phat + z2 / (2.0 * n)) / denom
    half = z * math.sqrt(phat * (1.0 - phat) / n + z2 / (4.0 * n * n)) / denom
    lo = max(0.0, center - half)
    hi = min(1.0, center + half)
    # k=0 and k=n are exactly 0 and 1; float error leaves a 1 ulp gap.
    if lo < 1e-12:
        lo = 0.0
    if hi > 1.0 - 1e-12:
        hi = 1.0
    return (lo, hi)


def intervals_overlap(left: Sequence[float] | None, right: Sequence[float]) -> bool:
    if not left or len(left) != 2:
        return False
    return float(left[0]) <= float(right[1]) and float(right[0]) <= float(left[1])


def _rate(k: int, n: int) -> dict[str, Any]:
    if n <= 0:
        return {"k": 0, "n": 0, "value": None, "wilson95": None}
    interval = wilson_interval(k, n)
    return {
        "k": k,
        "n": n,
        "value": k / n,
        "wilson95": list(interval) if interval else None,
    }


def _strip_type_slot(text: str) -> str:
    parts: list[str] = []
    for tok in (text or "").split():
        if ":" in tok:
            tag, rest = tok.split(":", 1)
            if tag in TYPE_SLOT_TAGS and rest:
                parts.append(rest)
                continue
        parts.append(tok)
    return " ".join(parts)


def norm_text(text: str) -> str:
    """Lowercase phrase with punctuation stripped. Type-slot tags removed first."""
    raw = _strip_type_slot(text).lower()
    raw = raw.replace("\u2019", "'").replace("\u2018", "'")
    raw = re.sub(r"[^a-z0-9']+", " ", raw)
    return " ".join(raw.split())


def stem_token(token: str) -> str:
    """One-suffix stem. ``quitting`` and ``quits`` both become ``quit``.

    Strips ``ing`` / ``ed`` / ``es`` / ``s`` when at least three characters
    remain. After ``ing`` or ``ed``, a doubled final consonant other than
    ``s`` is dropped once (``quitt`` → ``quit``, ``pass`` stays ``pass``).
    """
    t = token.lower()
    stripped = ""
    for suf in ("ing", "ed", "es"):
        if t.endswith(suf) and len(t) - len(suf) >= 3:
            t = t[: -len(suf)]
            stripped = suf
            break
    if not stripped and t.endswith("s") and not t.endswith("ss") and len(t) - 1 >= 3:
        t = t[:-1]
        stripped = "s"
    if stripped in {"ing", "ed"} and len(t) >= 4 and t[-1] == t[-2] and t[-1] not in "aeious":
        t = t[:-1]
    return t


def stem_key(text: str) -> tuple[str, ...]:
    tokens = [stem_token(tok) for tok in norm_text(text).split() if tok]
    return tuple(sorted(tokens))


def filler_set(row: Mapping[str, Any]) -> frozenset[str]:
    return frozenset(str(item).lower() for item in (row.get("fillers") or []) if str(item).strip())


def jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _prov_text(row: Mapping[str, Any]) -> str:
    raw = row.get("provenance")
    if isinstance(raw, dict):
        return json.dumps(raw, sort_keys=True, ensure_ascii=False)
    return str(raw or "")


def provenance_bucket(row: Mapping[str, Any]) -> str:
    """``templated`` is civilian / val-settle whitespace gold. Else ``harvested``."""
    prov = _prov_text(row).lower()
    license_ = str(row.get("license") or "").lower()
    if (
        prov.startswith("civilian-pos:")
        or prov.startswith("civilian-type:")
        or prov.startswith("civilian:")
        or "val-settle" in prov
        or "unbind structural whitespace" in license_
    ):
        return "templated"
    return "harvested"


def provenance_source(row: Mapping[str, Any]) -> str:
    raw = row.get("provenance")
    if isinstance(raw, dict):
        return "dict:" + str(raw.get("source") or "unknown")
    text = str(raw or "")
    if "val-settle" in text:
        return "val_settle"
    if text.startswith("civilian-pos:") or text.startswith("civilian-type:"):
        return "civilian_template"
    if text.startswith("live-pos:") or text.startswith("live-type:"):
        return "live"
    head = text.split(":", 1)[0]
    return head or "unknown"


def assert_no_test(rows: Iterable[Mapping[str, Any]], *, where: str) -> None:
    n = sum(1 for row in rows if row.get("split") == "test")
    if n:
        raise HoldoutSliceRefused(f"REFUSE: {where} includes {n} holdout test rows")


def drop_test_rows(rows: Sequence[Mapping[str, Any]]) -> tuple[list[dict], int]:
    """Return non-test rows and the discarded count. Test rows are not copied."""
    kept: list[dict] = []
    discarded = 0
    for row in rows:
        if row.get("split") == "test":
            discarded += 1
            continue
        kept.append(dict(row))
    return kept, discarded


class TrainIndex:
    """Sibling lookup over train rows only. Test rows are refused."""

    def __init__(self, train_rows: Sequence[Mapping[str, Any]]):
        assert_no_test(train_rows, where="train sibling corpus")
        self.norms: set[str] = set()
        self.stems: set[tuple[str, ...]] = set()
        self.fillers: list[frozenset[str]] = []
        for row in train_rows:
            phrase = norm_text(str(row.get("text") or ""))
            if phrase:
                self.norms.add(phrase)
                key = stem_key(phrase)
                if key:
                    self.stems.add(key)
            fillers = filler_set(row)
            if fillers:
                self.fillers.append(fillers)

    def match(self, row: Mapping[str, Any]) -> tuple[bool, str | None]:
        phrase = norm_text(str(row.get("text") or ""))
        if phrase and phrase in self.norms:
            return True, "norm_text"
        key = stem_key(phrase) if phrase else ()
        if key and key in self.stems:
            return True, "lemma"
        fillers = filler_set(row)
        if fillers and any(jaccard(fillers, other) >= JACCARD_SIBLING for other in self.fillers):
            return True, "filler_jaccard"
        return False, None


def row_id(row: Mapping[str, Any]) -> str:
    parts = [
        str(row.get("task") or ""),
        str(row.get("split") or ""),
        str(row.get("role_scheme") or ""),
        str(row.get("class") or ""),
        str(row.get("lineage") or ""),
        str(row.get("text") or ""),
    ]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:16]


def annotate_rows(rows: Sequence[Mapping[str, Any]], train_rows: Sequence[Mapping[str, Any]]) -> list[dict]:
    """Tag val rows. Refuses any test row in either argument."""
    assert_no_test(rows, where="annotate")
    index = TrainIndex(train_rows)
    tagged: list[dict] = []
    seen: set[str] = set()
    for row in rows:
        flag, reason = index.match(row)
        ident = row_id(row)
        if ident in seen:
            raise HoldoutSliceRefused(f"REFUSE: duplicate row_id {ident}")
        seen.add(ident)
        tagged.append(
            {
                "row_id": ident,
                "task": str(row.get("task") or ""),
                "split": str(row.get("split") or ""),
                "text": str(row.get("text") or ""),
                "lineage": str(row.get("lineage") or ""),
                "role_scheme": str(row.get("role_scheme") or ""),
                "class": str(row.get("class") or "").upper(),
                "fillers": [str(item) for item in (row.get("fillers") or [])],
                "provenance": _prov_text(row),
                "provenance_bucket": provenance_bucket(row),
                "provenance_source": provenance_source(row),
                "train_sibling": flag,
                "sibling_reason": reason,
            }
        )
    tagged.sort(key=lambda item: item["row_id"])
    return tagged


def release_val_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict]:
    """``unbind:val`` plus ``classify+unbind:val``. Test rows are refused."""
    assert_no_test(rows, where="release val")
    return [
        dict(row)
        for row in rows
        if row.get("split") == "val" and row.get("task") in RELEASE_VAL_TASKS
    ]


def surface_tokens(text: str) -> list[str]:
    """Same atom tokens as ``score_holdout.copy_baseline`` (text after the first colon)."""
    return [tok.split(":", 1)[-1].lower() for tok in str(text or "").split()]


def lenient_copy_hit(row: Mapping[str, Any]) -> bool:
    """True when every gold filler appears among atom tokens. Slot order ignored.

    Matches ``score_holdout.copy_baseline`` on a single row.
    """
    fillers = [str(item).lower() for item in (row.get("fillers") or [])]
    if not fillers:
        return False
    toks = surface_tokens(str(row.get("text") or ""))
    return all(fill in toks for fill in fillers)


def strict_slot_pair(row: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    """Predict gold slots by placing surface tokens in order.

    Exact credit requires the i-th surface token to be the i-th gold filler.
    Extra surface tokens are ignored. A missing token is an empty prediction.
    """
    gold = [str(item).lower() for item in (row.get("fillers") or [])]
    if not gold:
        return [], []
    toks = surface_tokens(str(row.get("text") or ""))
    pred = [toks[i] if i < len(toks) else "" for i in range(len(gold))]
    return gold, pred


def metric_block(pairs: Sequence[tuple[Sequence[str], Sequence[str]]]) -> dict[str, Any]:
    """Exact, token-F1, and slot-F1. Wilson on exact (row hits) and on micro recall."""
    usable = [([str(g) for g in gold], [str(p) for p in pred]) for gold, pred in pairs if gold]
    n = len(usable)
    if n == 0:
        empty = {"value": None, "n": 0, "wilson95": None}
        return {
            "n": 0,
            "unbind_exact": {**_rate(0, 0)},
            "unbind_token_f1": {**empty, "micro_tp": 0, "micro_gold": 0},
            "unbind_slot_f1": {**empty, "micro_tp": 0, "micro_gold": 0},
        }
    summary = summarize_unbind_pairs(usable)
    k = sum(gold == pred for gold, pred in usable)
    tok_tp = tok_g = 0
    slot_tp = slot_g = 0
    for gold, pred in usable:
        tp, _pn, gn = token_multiset_counts(gold, pred)
        tok_tp += tp
        tok_g += gn
        stp, _spn, sgn = slot_counts(gold, pred)
        slot_tp += stp
        slot_g += sgn
    tok_w = wilson_interval(tok_tp, tok_g)
    slot_w = wilson_interval(slot_tp, slot_g)
    return {
        "n": n,
        "unbind_exact": _rate(k, n),
        "unbind_token_f1": {
            "value": summary["unbind_token_f1"],
            "n": n,
            "micro_tp": tok_tp,
            "micro_gold": tok_g,
            "wilson95": list(tok_w) if tok_w else None,
        },
        "unbind_slot_f1": {
            "value": summary["unbind_slot_f1"],
            "n": n,
            "micro_tp": slot_tp,
            "micro_gold": slot_g,
            "wilson95": list(slot_w) if slot_w else None,
        },
    }


def copy_token_block(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    scored = [row for row in rows if row.get("fillers")]
    k = sum(1 for row in scored if lenient_copy_hit(row))
    return _rate(k, len(scored))


def strict_slot_block(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    scored = [row for row in rows if row.get("fillers")]
    return metric_block([strict_slot_pair(row) for row in scored])


def slice_groups(rows: Sequence[Mapping[str, Any]]) -> list[tuple[str, list]]:
    grouped = [
        ("all", list(rows)),
        ("harvested", [row for row in rows if row.get("provenance_bucket") == "harvested"]),
        ("templated", [row for row in rows if row.get("provenance_bucket") == "templated"]),
        ("sibling", [row for row in rows if row.get("train_sibling")]),
        ("no_sibling", [row for row in rows if not row.get("train_sibling")]),
    ]
    for label in sorted({str(row.get("class") or "") for row in rows}):
        grouped.append((f"class:{label}", [row for row in rows if str(row.get("class") or "") == label]))
    for label in sorted({str(row.get("role_scheme") or "") for row in rows}):
        grouped.append((f"scheme:{label}", [row for row in rows if str(row.get("role_scheme") or "") == label]))
    return grouped


def _pairs_for(rows: Sequence[Mapping[str, Any]], pred_map: Mapping[str, tuple]) -> list[tuple[list[str], list[str]]]:
    pairs: list[tuple[list[str], list[str]]] = []
    for row in rows:
        if not row.get("fillers"):
            continue
        ident = str(row["row_id"])
        if ident not in pred_map:
            raise KeyError(f"missing prediction for {ident}")
        gold, pred = pred_map[ident]
        pairs.append((list(gold), list(pred)))
    return pairs


def model_slice_metrics(rows: Sequence[Mapping[str, Any]], pred_map: Mapping[str, tuple]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, group in slice_groups(rows):
        out[name] = metric_block(_pairs_for(group, pred_map))
    return out


def control_slice_metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    copy: dict[str, Any] = {}
    strict: dict[str, Any] = {}
    for name, group in slice_groups(rows):
        copy[name] = copy_token_block(group)
        strict[name] = strict_slot_block(group)
    return {"unbind_copy_token": copy, "strict_slot_copy": strict}


def _exact(models: Mapping[str, Any], name: str, slice_name: str) -> float | None:
    try:
        return models[name]["slices"][slice_name]["unbind_exact"]["value"]
    except (KeyError, TypeError):
        return None


def _wilson(models: Mapping[str, Any], name: str, slice_name: str) -> list | None:
    try:
        return models[name]["slices"][slice_name]["unbind_exact"]["wilson95"]
    except (KeyError, TypeError):
        return None


def _le(value: float | None, thresh: float) -> bool:
    return value is not None and value <= thresh + 1e-9


def _ge(value: float | None, thresh: float) -> bool:
    return value is not None and value >= thresh - 1e-9


def surface_verdict(models: Mapping[str, Any]) -> dict[str, Any]:
    """Post-rc1 pin. Does not read test rows; the test interval is the pinned constant.

    ``SURFACE_SWAP_SUPPORTED`` when morph78 release-val exact is off the ceiling,
    its Wilson interval overlaps the pinned test-clean interval, the three
    checkpoints rank morph78 ≥ morph65 ≥ rc1, and morph78 harvested < templated.
    ``LEAK_NOT_SURFACE`` when morph78 overall ≥ 0.95 and no-sibling ≤ 0.85.
    ``H1_REJECTED`` when morph78 sibling and no-sibling are both ≥ 0.95.
    Otherwise ``NO_RULE_MATCH``.
    """
    all78 = _exact(models, "morph78", "all")
    harv = _exact(models, "morph78", "harvested")
    temp = _exact(models, "morph78", "templated")
    sib = _exact(models, "morph78", "sibling")
    nosib = _exact(models, "morph78", "no_sibling")
    m65 = _exact(models, "morph65", "all")
    rc1 = _exact(models, "rc1", "all")
    wilson = _wilson(models, "morph78", "all")
    ranking_ok = None not in (all78, m65, rc1) and all78 + 1e-12 >= m65 and m65 + 1e-12 >= rc1
    overlap = intervals_overlap(wilson, PINNED_MORPH78_TEST_CLEAN_WILSON)
    off_ceiling = _le(all78, 0.85)
    harvested_below = harv is not None and temp is not None and harv < temp
    checks = {
        "morph78_exact": all78,
        "morph78_wilson95": wilson,
        "pinned_test_clean_wilson95": list(PINNED_MORPH78_TEST_CLEAN_WILSON),
        "off_ceiling": off_ceiling,
        "wilson_overlaps_test_clean": overlap,
        "ranking_morph78_ge_morph65_ge_rc1": bool(ranking_ok),
        "morph65_exact": m65,
        "rc1_exact": rc1,
        "harvested_below_templated": harvested_below,
        "morph78_harvested": harv,
        "morph78_templated": temp,
        "morph78_sibling": sib,
        "morph78_no_sibling": nosib,
    }
    if off_ceiling and overlap and ranking_ok and harvested_below:
        candidate = "SURFACE_SWAP_SUPPORTED"
    elif _ge(all78, 0.95) and _le(nosib, 0.85):
        candidate = "LEAK_NOT_SURFACE"
    elif _ge(sib, 0.95) and _ge(nosib, 0.95):
        candidate = "H1_REJECTED"
    else:
        candidate = "NO_RULE_MATCH"
    return {"candidate": candidate, "checks": checks}


def publish_verdict(candidate: str, rows: list, reproduce_rows: list | None) -> dict[str, Any]:
    """HOLD until a second run's rows match. CI green is not a reproduce."""
    if reproduce_rows is None:
        status, published = "pending", "HOLD"
    elif reproduce_rows == rows:
        status, published = "matched", candidate
    else:
        status, published = "mismatch", "HOLD"
    return {
        "candidate": candidate,
        "published": published,
        "hold": published == "HOLD",
        "reproduce": status,
    }


def provenance_mix(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Count provenance tags.

    Annotated rows already store ``provenance_bucket`` and ``provenance_source``.
    ``annotate_rows`` drops ``license`` and flattens dict provenance to text, so
    re-deriving the tags mis-counts license-only templates and dict sources.
    Raw export rows omit the tags; derive them in that case.
    """
    buckets: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    schemes: Counter[str] = Counter()
    classes: Counter[str] = Counter()
    for row in rows:
        buckets[row.get("provenance_bucket") or provenance_bucket(row)] += 1
        sources[row.get("provenance_source") or provenance_source(row)] += 1
        schemes[str(row.get("role_scheme") or "")] += 1
        classes[str(row.get("class") or "").upper()] += 1
    return {
        "n_rows": len(rows),
        "n_scored": sum(1 for row in rows if row.get("fillers")),
        "provenance_bucket": dict(sorted(buckets.items())),
        "provenance_source": dict(sorted(sources.items())),
        "role_scheme": dict(sorted(schemes.items())),
        "class": dict(sorted(classes.items())),
    }


def load_force_keys(path: str | Path) -> set[tuple[str, str]]:
    """``(stripped text, role_scheme)`` keys. Same fields as force-train move."""
    keys: set[tuple[str, str]] = set()
    file = Path(path)
    for index, line in enumerate(file.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        obj = json.loads(line)
        text = obj.get("text")
        scheme = obj.get("role_scheme")
        if not isinstance(text, str) or scheme not in {"positional", "type_slot"}:
            raise ValueError(f"{file} line {index} needs text and positional|type_slot role_scheme")
        keys.add((text.strip(), str(scheme)))
    return keys


def val_after_force(val_rows: Sequence[Mapping[str, Any]], force_keys: Iterable[tuple[str, str]]) -> list[dict]:
    """Keep rule of ``apply_unbind_force_train``: OBSERVED force keys leave val."""
    keys = set(force_keys)
    kept: list[dict] = []
    for row in val_rows:
        key = (str(row.get("text") or "").strip(), str(row.get("role_scheme") or ""))
        if key in keys and row.get("class") == "OBSERVED":
            continue
        kept.append(dict(row))
    return kept


def broad_clean_rows(rows: Sequence[Mapping[str, Any]], trained_keys: Iterable[tuple[str, str]]) -> tuple[list[dict], dict]:
    """eval_broad clean slice: OBSERVED unbind val minus trained keys and train text."""
    assert_no_test(rows, where="broad clean")
    unbind = [row for row in rows if row.get("task") == "unbind"]
    train = [row for row in unbind if row.get("split") == "train"]
    val_obs = [
        row
        for row in unbind
        if row.get("split") == "val" and str(row.get("class") or "").upper() == "OBSERVED"
    ]
    return clean_surface(val_obs, train_rows=train, trained_keys=trained_keys)


def force_fair_rows(rows: Sequence[Mapping[str, Any]], force_keys: Iterable[tuple[str, str]]) -> list[dict]:
    """n=164 surface: legacy unbind val after the morph78 force-train move. Filter off."""
    assert_no_test(rows, where="force fair")
    val = [row for row in rows if row.get("task") == "unbind" and row.get("split") == "val"]
    return val_after_force(val, force_keys)


def train_val_strict_rows(rows: Sequence[Mapping[str, Any]], force_keys: Iterable[tuple[str, str]]) -> list[dict]:
    """n=140 surface: force-fair val after the strict filler filter (rc1 train val)."""
    kept, _stats = filter_unbind_rows(force_fair_rows(rows, force_keys), mode="strict")
    return kept


def _surface_record(name: str, rows: Sequence[Mapping[str, Any]], *, extra: dict | None = None) -> dict[str, Any]:
    mix = provenance_mix(rows)
    body = {
        "status": "OK",
        "expected_n": EXPECTED_SURFACE_N[name],
        "n_matches_expected": mix["n_scored"] == EXPECTED_SURFACE_N[name],
        **mix,
    }
    if extra:
        body.update(extra)
    return body


def known_surfaces(
    rows: Sequence[Mapping[str, Any]],
    *,
    trained_keys: Iterable[tuple[str, str]] | None,
    force_keys: Iterable[tuple[str, str]] | None,
) -> dict[str, Any]:
    """Provenance mix of the n=51, n=164, and n=140 selection surfaces. No model."""
    assert_no_test(rows, where="known surfaces")
    out: dict[str, Any] = {}
    if trained_keys is None:
        out["broad_clean"] = {
            "status": "NOT_COMPUTABLE",
            "expected_n": EXPECTED_SURFACE_N["broad_clean"],
            "reason": "trained force/hard keys not provided",
        }
    else:
        clean, accounting = broad_clean_rows(rows, trained_keys)
        out["broad_clean"] = _surface_record(
            "broad_clean",
            clean,
            extra={
                "definition": "OBSERVED unbind val after clean_surface (eval_broad clean, n=51 at rc1)",
                "accounting": accounting,
            },
        )
    if force_keys is None:
        missing = {
            "status": "NOT_COMPUTABLE",
            "reason": "morph78 force-train jsonl not provided",
        }
        out["force_fair"] = {**missing, "expected_n": EXPECTED_SURFACE_N["force_fair"]}
        out["train_val_strict"] = {**missing, "expected_n": EXPECTED_SURFACE_N["train_val_strict"]}
    else:
        fair = force_fair_rows(rows, force_keys)
        strict = train_val_strict_rows(rows, force_keys)
        out["force_fair"] = _surface_record(
            "force_fair",
            fair,
            extra={"definition": "unbind val after OBSERVED force-train move; filler filter off (n=164 at rc1)"},
        )
        out["train_val_strict"] = _surface_record(
            "train_val_strict",
            strict,
            extra={"definition": "force-fair val after strict filler filter (rc1 train-time val, n=140)"},
        )
    return out


def _sibling_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    sibling = sum(1 for row in rows if row.get("train_sibling"))
    return {"sibling": sibling, "no_sibling": len(rows) - sibling}


def attach_predictions(rows: Sequence[Mapping[str, Any]], predictions: Mapping[str, Mapping[str, tuple]]) -> list[dict]:
    attached: list[dict] = []
    for row in rows:
        models: dict[str, Any] = {}
        for name in sorted(predictions):
            pred_map = predictions[name]
            if not row.get("fillers"):
                continue
            if row["row_id"] not in pred_map:
                raise KeyError(f"missing prediction for {name} {row['row_id']}")
            gold, pred = pred_map[row["row_id"]]
            gold_l = [str(item) for item in gold]
            pred_l = [str(item) for item in pred]
            models[name] = {"exact": int(gold_l == pred_l), "gold": gold_l, "pred": pred_l}
        attached.append({**row, "models": models})
    return attached


def assemble_report(
    rows: Sequence[Mapping[str, Any]],
    predictions: Mapping[str, Mapping[str, tuple]] | None = None,
    *,
    trained_keys: Iterable[tuple[str, str]] | None = None,
    force_keys: Iterable[tuple[str, str]] | None = None,
    reproduce_rows: list | None = None,
    release_set: Mapping[str, Any] | None = None,
    n_test_discarded: int | None = None,
) -> dict[str, Any]:
    """Build the audit report. Drops test rows unless the caller already did."""
    if n_test_discarded is None:
        kept, n_test_discarded = drop_test_rows(rows)
    else:
        assert_no_test(rows, where="assemble")
        kept = [dict(row) for row in rows]
    predictions = predictions or {}
    val = release_val_rows(kept)
    train = [row for row in kept if row.get("split") == "train"]
    annotated = annotate_rows(val, train)
    emitted = attach_predictions(annotated, predictions)
    assert_no_test(emitted, where="report rows")
    models = {
        name: {"slices": model_slice_metrics(emitted, pred_map)}
        for name, pred_map in sorted(predictions.items())
    }
    decided = surface_verdict(models)
    verdict = {**publish_verdict(decided["candidate"], emitted, reproduce_rows), "checks": decided["checks"]}
    mix = provenance_mix(emitted)
    report = {
        "schema": "hyperlex.selection_surface_audit.v0.1",
        "brier": None,
        "eval_only": True,
        "allow_train": False,
        "test_slices_scored": False,
        "n_test_discarded": n_test_discarded,
        "release_set": {"release_set": bool(release_set.get("release_set"))} if release_set else {"release_set": None},
        "release_val": {**mix, "train_sibling": _sibling_counts(emitted)},
        "known_surfaces": known_surfaces(kept, trained_keys=trained_keys, force_keys=force_keys),
        "models": models,
        "controls": control_slice_metrics(emitted),
        "verdict": verdict,
        "rows": emitted,
    }
    return report


def render_summary(report: Mapping[str, Any]) -> str:
    """Short markdown. Deterministic: no clock, no host paths required."""
    verdict = report["verdict"]
    release = report["release_val"]
    lines = [
        "# Selection-surface audit",
        "",
        f"Published verdict: **{verdict['published']}** "
        f"(candidate `{verdict['candidate']}`, reproduce {verdict['reproduce']}).",
        "",
        "Eval only. The test split was discarded and not scored. Brier is null.",
        f"Test rows discarded: {report['n_test_discarded']}.",
        "",
        "## Release unbind val",
        "",
        f"n_rows={release['n_rows']} n_scored={release['n_scored']}",
        f"provenance={json.dumps(release['provenance_bucket'], sort_keys=True)}",
        f"source={json.dumps(release['provenance_source'], sort_keys=True)}",
        f"sibling={json.dumps(release['train_sibling'], sort_keys=True)}",
        "",
        "## Unbind exact",
        "",
        "| model | slice | exact | n | wilson95 |",
        "|---|---|---:|---:|---|",
    ]
    for name, body in report["models"].items():
        for slice_name in ("all", "harvested", "templated", "sibling", "no_sibling"):
            block = body["slices"][slice_name]["unbind_exact"]
            lines.append(
                f"| {name} | {slice_name} | {block['value']} | {block['n']} | {block['wilson95']} |"
            )
    lines.extend(["", "## Controls on all", ""])
    copy = report["controls"]["unbind_copy_token"]["all"]
    strict = report["controls"]["strict_slot_copy"]["all"]
    lines.append(
        f"unbind_copy_token exact={copy['value']} n={copy['n']} wilson95={copy['wilson95']}"
    )
    lines.append(
        "strict_slot_copy "
        f"exact={strict['unbind_exact']['value']} "
        f"token_f1={strict['unbind_token_f1']['value']} "
        f"slot_f1={strict['unbind_slot_f1']['value']} "
        f"n={strict['n']}"
    )
    lines.extend(["", "## Known selection surfaces", ""])
    for name, body in report["known_surfaces"].items():
        if body.get("status") != "OK":
            lines.append(f"{name}: {body.get('status')} ({body.get('reason')})")
            continue
        lines.append(
            f"{name}: n_scored={body['n_scored']} expected={body['expected_n']} "
            f"match={body['n_matches_expected']} "
            f"provenance={json.dumps(body['provenance_bucket'], sort_keys=True)}"
        )
    lines.extend(
        [
            "",
            "Wilson beside exact and the lenient copy baseline is the row-hit interval. "
            "Wilson beside token-F1 and slot-F1 is the micro-recall interval (tp/gold).",
            "A first run stays HOLD. Re-run from a second checkout of the same SHA with "
            "`--reproduce` pointing at the first JSON. The candidate is published only when rows match.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(report: Mapping[str, Any], out_dir: str | Path) -> tuple[Path, Path]:
    """Write JSON and markdown under ``out_dir`` only."""
    dest = Path(out_dir)
    dest.mkdir(parents=True, exist_ok=True)
    json_path = dest / "selection-surface-audit.json"
    md_path = dest / "SUMMARY.md"
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    json_path.write_text(payload, encoding="utf-8")
    md_path.write_text(render_summary(report), encoding="utf-8")
    return json_path, md_path
