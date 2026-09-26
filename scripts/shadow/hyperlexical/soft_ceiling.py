"""soft_ceiling_tiebreak gate + contamination-safe eval surfaces. No torch.

Ported from the Spark ``~/hlx`` chain used for morph75–78. Differences from
that chain (publish audit 2026-09-24):

- ``clean_surface`` removes eval rows whose ``(text, role_scheme)`` is in the
  candidate's force-train / hard-atom files, or whose text is in train. The
  morph78 broad val shared 193 of 256 rows with its own force-train file.
- ``decide`` fails closed with ``REJECT_CONTAMINATED`` when the scored surface
  still overlaps the candidate's training files.
- ``oov_filler_surface`` keeps rows whose gold fillers are absent from the
  train filler vocab, so a clean score is not a copy task.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

PIN_BROAD_EXACT = 0.889763779527559
PIN_BROAD_N = 254


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def row_key(row: dict) -> tuple[str, str]:
    return _norm(str(row.get("text") or "")), str(row.get("role_scheme") or "")


def load_jsonl_keys(path: str | Path | None) -> set[tuple[str, str]]:
    if not path:
        return set()
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(p)
    keys = set()
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            keys.add(row_key(json.loads(line)))
    return keys


def clean_surface(
    eval_rows: Iterable[dict],
    *,
    train_rows: Iterable[dict] = (),
    trained_keys: Iterable[tuple[str, str]] = (),
) -> tuple[list[dict], dict]:
    """Drop eval rows the candidate trained on. Returns (rows, accounting)."""
    trained = set(trained_keys)
    trained_texts = {k[0] for k in trained}
    train_texts = {_norm(str(r.get("text") or "")) for r in train_rows}
    kept, by_key, by_text, by_train = [], 0, 0, 0
    for row in eval_rows:
        key = row_key(row)
        if key in trained:
            by_key += 1
        elif key[0] in trained_texts:
            by_text += 1
        elif key[0] in train_texts:
            by_train += 1
        else:
            kept.append(row)
    total = by_key + by_text + by_train + len(kept)
    return kept, {
        "n_input": total,
        "n_kept": len(kept),
        "n_excluded_trained_key": by_key,
        "n_excluded_trained_text": by_text,
        "n_excluded_train_split_text": by_train,
    }


def oov_filler_surface(rows: Iterable[dict], train_rows: Iterable[dict]) -> list[dict]:
    """Rows whose every gold filler is absent from train fillers."""
    seen = set()
    for r in train_rows:
        for f in r.get("fillers") or []:
            seen.add(str(f).lower())
    out = []
    for r in rows:
        fillers = [str(f).lower() for f in (r.get("fillers") or [])]
        if fillers and all(f not in seen for f in fillers):
            out.append(r)
    return out


def overlap(eval_rows: Iterable[dict], trained_keys: Iterable[tuple[str, str]]) -> int:
    trained = set(trained_keys)
    trained_texts = {k[0] for k in trained}
    return sum(1 for r in eval_rows if row_key(r) in trained or row_key(r)[0] in trained_texts)


def _base(**kw: Any) -> dict[str, Any]:
    return {"gate": "soft_ceiling_tiebreak", **kw}


def decide(
    *,
    force_fair: float,
    force_fair_n: int,
    best_exact: float,
    val_n: int,
    e2_pass: bool,
    broad_exact: float | None = None,
    broad_n: int | None = None,
    prior_broad_exact: float | None = None,
    prior_broad_n: int | None = None,
    broad_overlap: int | None = None,
) -> dict[str, Any]:
    """Promote decision. ``broad_overlap`` = rows on the broad surface the candidate trained on."""
    common = dict(
        force_fair=force_fair,
        force_fair_n=force_fair_n,
        best_exact=best_exact,
        val_n=val_n,
        e2_pass=e2_pass,
        broad_exact=broad_exact,
        broad_n=broad_n,
        prior_broad_exact=prior_broad_exact,
        prior_broad_n=prior_broad_n,
        broad_overlap=broad_overlap,
    )
    ceiling = float(force_fair) >= 1.0 - 1e-12
    if not ceiling:
        surface_ok = int(val_n) == int(force_fair_n)
        promote = bool(best_exact > force_fair and e2_pass and surface_ok)
        decision = "REJECT_SURFACE" if not surface_ok else ("PROMOTE_BEST" if promote else "REJECT_VS_BEST")
        return _base(
            mode="force_fair",
            promote=promote,
            decision=decision,
            surface_ok=surface_ok,
            reason=f"force_fair mode: best {best_exact} > fair {force_fair} n={force_fair_n} + E2",
            **common,
        )
    if broad_exact is None or broad_n is None:
        return _base(
            mode="ceiling_escape",
            promote=False,
            decision="REJECT_NO_BROAD_EVAL",
            surface_ok=False,
            reason="force_fair==1.0 but candidate broad OBSERVED eval missing",
            **common,
        )
    if broad_overlap is None:
        return _base(
            mode="ceiling_escape",
            promote=False,
            decision="REJECT_UNKNOWN_CONTAMINATION",
            surface_ok=False,
            reason="broad surface overlap with candidate training files not measured",
            **common,
        )
    if int(broad_overlap) > 0:
        return _base(
            mode="ceiling_escape",
            promote=False,
            decision="REJECT_CONTAMINATED",
            surface_ok=False,
            reason=f"broad surface shares {broad_overlap} rows with candidate training files",
            **common,
        )
    if prior_broad_exact is not None and prior_broad_n is not None:
        baseline_exact, baseline_n, src = float(prior_broad_exact), int(prior_broad_n), "live_prior_broad"
    else:
        baseline_exact, baseline_n, src = PIN_BROAD_EXACT, PIN_BROAD_N, "authorize_pin"
    surface_ok = int(broad_n) == int(baseline_n)
    promote = bool(float(broad_exact) > baseline_exact and e2_pass and surface_ok)
    decision = "REJECT_BROAD_SURFACE" if not surface_ok else ("PROMOTE_BEST" if promote else "REJECT_VS_BROAD_BASELINE")
    return _base(
        mode="ceiling_escape",
        promote=promote,
        decision=decision,
        surface_ok=surface_ok,
        broad_baseline=baseline_exact,
        broad_baseline_n=baseline_n,
        broad_baseline_src=src,
        reason=(
            f"ceiling escape: broad {broad_exact} {'>' if promote else 'not >'} baseline {baseline_exact} "
            f"(src={src}) n={baseline_n}, e2_pass={e2_pass}, surface_ok={surface_ok}, overlap 0"
        ),
        **common,
    )
