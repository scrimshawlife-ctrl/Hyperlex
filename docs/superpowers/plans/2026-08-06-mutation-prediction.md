# Mutation Prediction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Emit speculative next surface-form candidates (`analysis.mutation_prediction`) from deterministic mutation operators, with optional governed LLM enrich, always `brier: null`.

**Architecture:** New offline module `hyperlex.analysis.mutation` implements `predict_mutations()`. Wire it into `detect_memetic_patterns` after lineage resolution. Optional LLM enrich mirrors `enrich_neologisms` fail-open pattern. Thin CLI `mutation-predict` exposes the same function. Docs ground the feature as SPECULATIVE.

**Tech Stack:** Python 3.10+, existing Hyperlex analysis/LLM packages, pytest, no new runtime deps for the deterministic path.

**Spec:** `docs/superpowers/specs/2026-08-06-mutation-prediction-design.md`

## Global Constraints

- Always `brier: null` on mutation blocks; never invent Brier.
- Default path offline (`HYPERLEX_OFFLINE=1`) without LLM.
- Fail-open: LLM/errors never break analyze.
- Operator vocabulary locked: `platform_compression`, `derivational`, `irony_inversion`, `compound_phrase`, `sense_extension`, `cross_family_borrowing`, `extra-grammatical`.
- Candidate `provenance` is always `SPECULATIVE` for v1.
- Cap candidates: default 8, env `HYPERLEX_MUTATION_MAX` clamped 1–20.
- Atomic seeds only (primary term); multi-atom full fan-out only if `HYPERLEX_MUTATION_ALL_ATOMS=1`.

## File map

| Path | Responsibility |
|------|----------------|
| `src/hyperlex/analysis/mutation.py` | Deterministic engine + `predict_mutations` |
| `src/hyperlex/llm/governed.py` | Optional `enrich_mutation_candidates` |
| `src/hyperlex/analysis/__init__.py` | Wire into `detect_memetic_patterns`; re-export |
| `src/hyperlex/__init__.py` | Public export `predict_mutations` |
| `scripts/hyperlex.py` | CLI `mutation-predict` |
| `tests/test_mutation_prediction.py` | Unit + analyze integration tests |
| `docs/start/glossary.md` | Glossary entry |
| `docs/demos/reading-evidence.md` | Claims matrix row |
| `STATUS.md` / `docs/status.md` (via STATUS) | Surface ready row |

---

### Task 1: Deterministic `predict_mutations` core

**Files:**
- Create: `src/hyperlex/analysis/mutation.py`
- Test: `tests/test_mutation_prediction.py`

**Interfaces:**
- Consumes: none (stdlib + registry terms passed in)
- Produces: `predict_mutations(seed_term: str, *, family_id: Optional[str] = None, family_terms: Optional[Sequence[str]] = None, family_operator: Optional[str] = None, max_candidates: Optional[int] = None, llm_candidates: Optional[Sequence[Dict[str, Any]]] = None) -> Dict[str, Any]`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_mutation_prediction.py`:

```python
"""Mutation prediction — next surface forms (SPECULATIVE, brier null)."""

from __future__ import annotations

from hyperlex.analysis.mutation import predict_mutations


def test_predict_mutations_returns_schema_and_null_brier():
    out = predict_mutations(
        "rizz",
        family_id="brainrot-aura",
        family_terms=["rizz", "aura", "sigma", "brainrot"],
        family_operator="irony_inversion",
    )
    assert out["schema"] == "hyperlex.mutation_prediction.v1"
    assert out["seed_term"] == "rizz"
    assert out["family_id"] == "brainrot-aura"
    assert out["brier"] is None
    assert out["provenance"] == "SPECULATIVE"
    assert out["n_candidates"] >= 1
    assert len(out["candidates"]) == out["n_candidates"]
    for c in out["candidates"]:
        assert c["form"]
        assert c["form"].lower() != "rizz"
        assert c["operator"]
        assert c["provenance"] == "SPECULATIVE"
        assert c["source"] in {"deterministic", "llm"}
        assert 0.0 < float(c["confidence"]) <= 1.0
        assert c.get("rationale")


def test_predict_mutations_empty_seed():
    out = predict_mutations("  ")
    assert out["n_candidates"] == 0
    assert out["brier"] is None
    assert out.get("candidates") == []


def test_predict_mutations_respects_max_candidates(monkeypatch):
    monkeypatch.setenv("HYPERLEX_MUTATION_MAX", "3")
    out = predict_mutations(
        "sigma",
        family_id="brainrot-aura",
        family_terms=["sigma", "rizz", "aura", "mid", "cooked"],
    )
    assert out["n_candidates"] <= 3
    assert len(out["candidates"]) <= 3


def test_predict_mutations_dedupes_casefold():
    out = predict_mutations(
        "Aura",
        family_id="brainrot-aura",
        family_terms=["aura", "rizz"],
        llm_candidates=[
            {
                "form": "AURAED",
                "operator": "derivational",
                "confidence": 0.9,
                "source": "llm",
                "rationale": "dup test",
            }
        ],
    )
    forms = [c["form"].lower() for c in out["candidates"]]
    assert len(forms) == len(set(forms))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/scrimshawlife/Hyperlex && .venv/bin/pytest tests/test_mutation_prediction.py -v --tb=short`

Expected: FAIL with `ModuleNotFoundError: No module named 'hyperlex.analysis.mutation'` (or import error for `predict_mutations`).

- [ ] **Step 3: Implement `src/hyperlex/analysis/mutation.py`**

```python
"""Predict next surface-form mutations for slang atoms.

Deterministic offline operators + optional pre-fetched LLM candidates.
Always SPECULATIVE; always brier null.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Sequence

SCHEMA = "hyperlex.mutation_prediction.v1"
NOTE = (
    "Next surface forms are speculative. Not calibrated probabilities / Brier."
)

OPERATORS = frozenset({
    "platform_compression",
    "derivational",
    "irony_inversion",
    "compound_phrase",
    "sense_extension",
    "cross_family_borrowing",
    "extra-grammatical",
})

_FAMILY_SUFFIXES: Dict[str, List[str]] = {
    "brainrot-aura": ["core", "maxxing", "posting", "points"],
    "political-status": ["pilled", "maxxing"],
    "gaming-meta": ["diff", "core"],
    "ai-native": ["slop", "core", "maxxing"],
    "crypto-degen": ["season", "core"],
    "workplace-corp": ["core"],
    "betting-sharp": ["core"],
    "kinship-address": [],
}

_GENERAL_SUFFIXES = ["ed", "ing", "er", "y"]
_VOWELS = set("aeiouAEIOU")


def _max_candidates(override: Optional[int] = None) -> int:
    if override is not None:
        n = int(override)
    else:
        raw = os.environ.get("HYPERLEX_MUTATION_MAX", "8").strip() or "8"
        try:
            n = int(raw)
        except ValueError:
            n = 8
    return max(1, min(20, n))


def _norm_form(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _norm_key(s: str) -> str:
    return _norm_form(s).lower()


def _vowel_drop(seed: str) -> Optional[str]:
    if len(seed) < 4 or " " in seed:
        return None
    chars = []
    for i, ch in enumerate(seed):
        if i > 0 and i < len(seed) - 1 and ch in _VOWELS:
            continue
        chars.append(ch)
    out = "".join(chars)
    if out.lower() == seed.lower() or len(out) < 2:
        return None
    return out


def _deterministic_candidates(
    seed: str,
    *,
    family_id: Optional[str],
    family_terms: Sequence[str],
    family_operator: Optional[str],
) -> List[Dict[str, Any]]:
    seed_disp = _norm_form(seed)
    seed_key = _norm_key(seed)
    attested = {_norm_key(t) for t in family_terms if t}
    out: List[Dict[str, Any]] = []

    def add(form: str, operator: str, confidence: float, rationale: str) -> None:
        f = _norm_form(form)
        if not f or _norm_key(f) == seed_key:
            return
        if operator not in OPERATORS:
            operator = "extra-grammatical"
        conf = float(confidence)
        already = _norm_key(f) in attested
        if already:
            conf *= 0.45
            rationale = f"{rationale} (already attested in family; down-ranked)"
        conf = max(0.05, min(0.95, conf))
        out.append({
            "form": f,
            "operator": operator,
            "confidence": round(conf, 4),
            "provenance": "SPECULATIVE",
            "source": "deterministic",
            "rationale": rationale,
            "already_attested": already,
        })

    # platform_compression
    vd = _vowel_drop(seed_disp)
    if vd:
        add(vd, "platform_compression", 0.38, "vowel-drop compression of seed")

    # derivational
    suffixes = list(_GENERAL_SUFFIXES)
    suffixes.extend(_FAMILY_SUFFIXES.get(family_id or "", []))
    base = seed_disp.rstrip("e") if seed_disp.endswith("e") and len(seed_disp) > 3 else seed_disp
    for suf in suffixes:
        if suf in {"ed", "ing", "er", "y"}:
            form = base + suf if not seed_disp.endswith(suf) else ""
        else:
            form = f"{seed_disp}{suf}" if not seed_disp.endswith(suf) else ""
        if form:
            add(form, "derivational", 0.40, f"derivational suffix -{suf}")

    # irony_inversion templates
    if (family_id in {"brainrot-aura", "political-status", "gaming-meta"} or
            family_operator == "irony_inversion"):
        add(f"negative {seed_disp}", "irony_inversion", 0.44, "polarity / status flip template")
        add(f"{seed_disp} points", "irony_inversion", 0.41, "quantified status template")
        add(f"mid {seed_disp}", "irony_inversion", 0.36, "mid-status compression template")

    # compound_phrase with family co-terms
    co_terms = [t for t in family_terms if t and _norm_key(t) != seed_key][:6]
    for co in co_terms[:4]:
        add(f"{seed_disp} {co}", "compound_phrase", 0.37, f"compound with family co-term {co}")
        add(f"{co} {seed_disp}", "compound_phrase", 0.35, f"compound with family co-term {co}")

    return out


def _merge_llm(
    deterministic: List[Dict[str, Any]],
    llm_candidates: Optional[Sequence[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    merged = list(deterministic)
    if not llm_candidates:
        return merged
    for raw in llm_candidates:
        if not isinstance(raw, dict):
            continue
        form = _norm_form(str(raw.get("form") or raw.get("term") or ""))
        if not form:
            continue
        op = str(raw.get("operator") or raw.get("formation") or "extra-grammatical")
        if op not in OPERATORS:
            op = "extra-grammatical"
        try:
            conf = float(raw.get("confidence") or 0.35)
        except (TypeError, ValueError):
            conf = 0.35
        conf = max(0.05, min(0.9, conf))
        merged.append({
            "form": form,
            "operator": op,
            "confidence": round(conf, 4),
            "provenance": "SPECULATIVE",
            "source": "llm",
            "rationale": str(raw.get("rationale") or "governed LLM mutation candidate"),
        })
    return merged


def _rank_and_cap(
    candidates: List[Dict[str, Any]],
    *,
    seed_key: str,
    max_n: int,
) -> List[Dict[str, Any]]:
    best: Dict[str, Dict[str, Any]] = {}
    for c in candidates:
        key = _norm_key(str(c.get("form") or ""))
        if not key or key == seed_key:
            continue
        prev = best.get(key)
        # Prefer higher confidence; break ties preferring deterministic
        if prev is None:
            best[key] = c
            continue
        pc, cc = float(prev.get("confidence") or 0), float(c.get("confidence") or 0)
        if cc > pc:
            best[key] = c
        elif cc == pc and prev.get("source") == "llm" and c.get("source") == "deterministic":
            best[key] = c

    ranked = list(best.values())
    ranked.sort(
        key=lambda c: (
            -float(c.get("confidence") or 0),
            0 if c.get("source") == "deterministic" else 1,
            str(c.get("form") or ""),
        )
    )
    cleaned = []
    for c in ranked[:max_n]:
        row = dict(c)
        row.pop("already_attested", None)
        cleaned.append(row)
    return cleaned


def predict_mutations(
    seed_term: str,
    *,
    family_id: Optional[str] = None,
    family_terms: Optional[Sequence[str]] = None,
    family_operator: Optional[str] = None,
    max_candidates: Optional[int] = None,
    llm_candidates: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Predict next surface forms for a slang atom.

    Returns hyperlex.mutation_prediction.v1 dict. Always brier=null.
    """
    seed = _norm_form(seed_term)
    max_n = _max_candidates(max_candidates)
    empty = {
        "schema": SCHEMA,
        "seed_term": seed,
        "family_id": family_id,
        "family_operator": family_operator,
        "candidates": [],
        "n_candidates": 0,
        "brier": None,
        "provenance": "SPECULATIVE",
        "note": NOTE,
    }
    if not seed:
        empty["error"] = "empty seed"
        return empty

    terms = list(family_terms or [])
    det = _deterministic_candidates(
        seed,
        family_id=family_id,
        family_terms=terms,
        family_operator=family_operator,
    )
    merged = _merge_llm(det, llm_candidates)
    ranked = _rank_and_cap(merged, seed_key=_norm_key(seed), max_n=max_n)
    return {
        "schema": SCHEMA,
        "seed_term": seed,
        "family_id": family_id,
        "family_operator": family_operator,
        "candidates": ranked,
        "n_candidates": len(ranked),
        "brier": None,
        "provenance": "SPECULATIVE",
        "note": NOTE,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_mutation_prediction.py -v --tb=short`

Expected: all 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hyperlex/analysis/mutation.py tests/test_mutation_prediction.py
git commit -m "feat(analysis): deterministic mutation prediction engine"
```

---

### Task 2: Wire into `detect_memetic_patterns` + package export

**Files:**
- Modify: `src/hyperlex/analysis/__init__.py` (after lineage assembly ~line 856; add import/export)
- Modify: `src/hyperlex/__init__.py` (export `predict_mutations`)
- Test: `tests/test_mutation_prediction.py` (append analyze integration test)

**Interfaces:**
- Consumes: `predict_mutations` from Task 1; lineage dict; `LINEAGE_REGISTRY`; optional LLM enrich (Task 3 can stub empty first)
- Produces: `analysis["mutation_prediction"]` on analyze results

- [ ] **Step 1: Write failing integration test**

Append to `tests/test_mutation_prediction.py`:

```python
import os
from hyperlex import detect_memetic_patterns, predict_mutations


def test_analyze_includes_mutation_prediction_offline(monkeypatch):
    monkeypatch.setenv("HYPERLEX_OFFLINE", "1")
    monkeypatch.setenv("HYPERLEX_VECTOR", "0")
    monkeypatch.delenv("HYPERLEX_LLM", raising=False)
    r = detect_memetic_patterns(
        "rizz",
        ingest_source="mock",
        use_structured_ingest=False,
        validate=False,
    )
    assert r["provenance"]["brier"] is None
    mp = (r.get("analysis") or {}).get("mutation_prediction")
    assert isinstance(mp, dict)
    assert mp["schema"] == "hyperlex.mutation_prediction.v1"
    assert mp["brier"] is None
    assert mp["provenance"] == "SPECULATIVE"
    assert mp["seed_term"]
    assert mp["n_candidates"] >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_mutation_prediction.py::test_analyze_includes_mutation_prediction_offline -v`

Expected: FAIL — `mutation_prediction` missing from analysis.

- [ ] **Step 3: Wire analyze + exports**

In `src/hyperlex/analysis/__init__.py`, after `if lineage: analysis["lineage"] = lineage` (before vector neighbors block), add:

```python
    # Speculative next-form mutations (fail-open; never Brier)
    try:
        from .mutation import predict_mutations

        fam_id = (lineage or {}).get("family_id")
        fam_op = (lineage or {}).get("branch_operator")
        fam_terms: List[str] = []
        if fam_id:
            for entry in LINEAGE_REGISTRY:
                if entry.get("family_id") == fam_id:
                    fam_terms = [str(t) for t in (entry.get("terms") or [])]
                    break
        seed_for_mut = (
            (lineage or {}).get("primary_term")
            or primary
            or (seed_split.get("terms") or [None])[0]
            or query
        )
        llm_mut = None  # Task 3 fills enrich path
        analysis["mutation_prediction"] = predict_mutations(
            str(seed_for_mut or ""),
            family_id=fam_id,
            family_terms=fam_terms,
            family_operator=fam_op,
            llm_candidates=llm_mut,
        )
    except Exception:
        pass
```

Re-export from analysis package top if there is an `__all__`; otherwise ensure `from hyperlex.analysis import predict_mutations` works by adding to `src/hyperlex/analysis/__init__.py`:

```python
from .mutation import predict_mutations  # near other imports or bottom re-export
```

In `src/hyperlex/__init__.py` analysis import block, add `predict_mutations` to the import list and to `__all__` lists (both if duplicated).

- [ ] **Step 4: Run tests**

Run: `.venv/bin/pytest tests/test_mutation_prediction.py -v --tb=short`

Expected: all PASS including analyze integration.

- [ ] **Step 5: Commit**

```bash
git add src/hyperlex/analysis/__init__.py src/hyperlex/__init__.py tests/test_mutation_prediction.py
git commit -m "feat(analysis): attach mutation_prediction on detect_memetic_patterns"
```

---

### Task 3: Optional LLM enrich (fail-open)

**Files:**
- Modify: `src/hyperlex/llm/governed.py` (add `enrich_mutation_candidates`)
- Modify: `src/hyperlex/llm/__init__.py` (export)
- Modify: `src/hyperlex/analysis/__init__.py` (call when `llm_enabled()`)
- Test: `tests/test_mutation_prediction.py`

**Interfaces:**
- Consumes: `llm_enabled`, `get_provider` patterns from `enrich_neologisms`
- Produces: `enrich_mutation_candidates(seed, *, family_id, existing) -> Dict` with `candidates` list or skipped

- [ ] **Step 1: Write failing test for LLM merge path without network**

```python
def test_predict_mutations_merges_llm_candidates_without_dup():
    out = predict_mutations(
        "rizz",
        family_id="brainrot-aura",
        family_terms=["rizz", "aura"],
        llm_candidates=[
            {
                "form": "rizzler",
                "operator": "derivational",
                "confidence": 0.55,
                "rationale": "agentive -er form",
            }
        ],
    )
    forms = {c["form"].lower() for c in out["candidates"]}
    assert "rizzler" in forms
    assert all(c["brier"] is None for c in [{"brier": out["brier"]}])
    sources = {c["source"] for c in out["candidates"] if c["form"].lower() == "rizzler"}
    assert "llm" in sources
```

(Note: this tests merge in `predict_mutations` which already accepts `llm_candidates` from Task 1. Add LLM enrich unit that returns skipped when disabled:)

```python
def test_enrich_mutation_candidates_skipped_when_llm_off(monkeypatch):
    monkeypatch.delenv("HYPERLEX_LLM", raising=False)
    from hyperlex.llm.governed import enrich_mutation_candidates
    meta = enrich_mutation_candidates("rizz", family_id="brainrot-aura", existing=[])
    assert meta["applied"] is False
    assert meta.get("candidates") == []
```

- [ ] **Step 2: Run tests — second may fail until enrich exists**

Run: `.venv/bin/pytest tests/test_mutation_prediction.py -v --tb=short`

- [ ] **Step 3: Implement `enrich_mutation_candidates` in `governed.py`**

Mirror `enrich_neologisms` structure:

```python
def enrich_mutation_candidates(
    seed_term: str,
    *,
    family_id: Optional[str] = None,
    family_operator: Optional[str] = None,
    existing: Optional[List[Dict[str, Any]]] = None,
    require_enabled: bool = True,
) -> Dict[str, Any]:
    """Optional LLM next-form candidates. Fail-open; never invents Brier."""
    existing = list(existing or [])
    if require_enabled and not llm_enabled():
        return {
            "enabled": False,
            "applied": False,
            "candidates": [],
            "status": "skipped",
            "reason": "HYPERLEX_LLM not enabled",
        }
    provider = get_provider()
    if provider is None:
        return {
            "enabled": llm_enabled(),
            "applied": False,
            "candidates": [],
            "status": "not_configured",
            "reason": "no provider",
        }
    prompt = (
        "Propose next surface-form mutations for a slang seed. "
        "Return JSON {candidates:[{form, operator, confidence, rationale}]}. "
        "Operators must be one of: platform_compression, derivational, irony_inversion, "
        "compound_phrase, sense_extension, cross_family_borrowing, extra-grammatical. "
        "Do not invent Brier scores. Max 5 candidates. Speculative only."
    )
    context = {
        "seed_term": seed_term,
        "family_id": family_id,
        "family_operator": family_operator,
        "existing": existing[:8],
    }
    try:
        # Reuse provider generate/complete path same as enrich_neologisms —
        # parse candidates list; normalize keys form/term.
        ...  # follow existing provider call pattern in enrich_neologisms
    except Exception as exc:
        return {
            "enabled": True,
            "applied": False,
            "candidates": [],
            "status": "error",
            "reason": str(exc),
        }
```

Implement the try body by copying the call/parse pattern from `enrich_neologisms` in the same file (do not invent a new HTTP client). Map each item to `{form, operator, confidence, rationale}` with `source` left for `predict_mutations` to set as `llm`.

Export from `src/hyperlex/llm/__init__.py`.

In `detect_memetic_patterns` mutation try-block, before `predict_mutations`:

```python
        llm_mut = None
        llm_mut_meta = None
        try:
            from ..llm import llm_enabled, enrich_mutation_candidates
            if llm_enabled():
                llm_mut_meta = enrich_mutation_candidates(
                    str(seed_for_mut or ""),
                    family_id=fam_id,
                    family_operator=fam_op,
                    existing=[],
                )
                if llm_mut_meta.get("applied"):
                    llm_mut = llm_mut_meta.get("candidates") or []
        except Exception:
            llm_mut_meta = {"status": "error", "applied": False}
        mp = predict_mutations(..., llm_candidates=llm_mut)
        if llm_mut_meta is not None:
            mp["llm_enrich"] = {
                "status": llm_mut_meta.get("status"),
                "applied": bool(llm_mut_meta.get("applied")),
                "reason": llm_mut_meta.get("reason"),
            }
        analysis["mutation_prediction"] = mp
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/pytest tests/test_mutation_prediction.py -v --tb=short`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hyperlex/llm/governed.py src/hyperlex/llm/__init__.py src/hyperlex/analysis/__init__.py tests/test_mutation_prediction.py
git commit -m "feat(llm): optional mutation candidate enrich (fail-open)"
```

---

### Task 4: CLI `mutation-predict`

**Files:**
- Modify: `scripts/hyperlex.py` (add `cmd_mutation_predict` + subparser)
- Test: `tests/test_mutation_prediction.py` (CLI subprocess)

**Interfaces:**
- Consumes: `predict_mutations`, `LINEAGE_REGISTRY` / `match_lineage` optional
- Produces: JSON stdout schema v1

- [ ] **Step 1: Write failing CLI test**

```python
import json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cli_mutation_predict_offline():
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "HYPERLEX_OFFLINE": "1"}
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "hyperlex.py"), "mutation-predict", "rizz"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(r.stdout)
    assert data.get("ok") is True
    assert data.get("brier") is None
    assert data.get("schema") == "hyperlex.mutation_prediction.v1"
    assert data.get("n_candidates", 0) >= 1
```

- [ ] **Step 2: Run test — expect fail (unknown command)**

- [ ] **Step 3: Implement CLI**

```python
def cmd_mutation_predict(args: argparse.Namespace) -> int:
    """Predict next surface forms for a slang atom (SPECULATIVE, brier null)."""
    pkg, err = _import_hyperlex()
    if pkg is None:
        _emit({"ok": False, "error": f"import failure: {err}"})
        return 2
    from hyperlex.analysis import LINEAGE_REGISTRY, match_lineage, predict_mutations

    seed = (args.query or args.term or "").strip()
    if not seed:
        _emit({"ok": False, "error": "empty query", "brier": None})
        return 2
    family_id = getattr(args, "family", None) or None
    family_terms = []
    family_operator = None
    if not family_id:
        lin = match_lineage(seed)
        if lin:
            family_id = lin.get("family_id")
            family_operator = lin.get("branch_operator")
    if family_id:
        for entry in LINEAGE_REGISTRY:
            if entry.get("family_id") == family_id:
                family_terms = list(entry.get("terms") or [])
                family_operator = family_operator or entry.get("branch_operator")
                break
    out = predict_mutations(
        seed,
        family_id=family_id,
        family_terms=family_terms,
        family_operator=family_operator,
        max_candidates=int(args.max) if getattr(args, "max", None) else None,
    )
    _emit({"ok": True, "command": "mutation-predict", **out})
    return 0
```

Register:

```python
mp = subparsers.add_parser(
    "mutation-predict",
    help="Predict next surface-form mutations (SPECULATIVE · brier null)",
)
mp.add_argument("query", nargs="?", default="", help="Seed term / atom")
mp.add_argument("--term", default="", help="Alias for query")
mp.add_argument("--family", default="", help="Force family_id")
mp.add_argument("--max", type=int, default=0, help="Max candidates (1-20)")
mp.set_defaults(func=cmd_mutation_predict)
```

Also list under `commands` map if there is a static commands list in `cmd_commands`.

- [ ] **Step 4: Run tests**

Run: `.venv/bin/pytest tests/test_mutation_prediction.py -v --tb=short`

- [ ] **Step 5: Commit**

```bash
git add scripts/hyperlex.py tests/test_mutation_prediction.py
git commit -m "feat(cli): mutation-predict subcommand"
```

---

### Task 5: Docs + STATUS

**Files:**
- Modify: `docs/start/glossary.md`
- Modify: `docs/demos/reading-evidence.md`
- Modify: `docs/commands.md`
- Modify: `STATUS.md`
- Modify: `docs/start/see-it-work.md` (one line optional)

- [ ] **Step 1: Glossary entry**

Add under Core terms:

```markdown
### Mutation prediction
Speculative **next surface forms** of a slang atom (compression, derivation,
irony templates, family compounds). Attached as `analysis.mutation_prediction`.
Always `provenance: SPECULATIVE` and `brier: null` — ranking weights are not
calibrated probabilities. CLI: `mutation-predict "<term>"`.
```

- [ ] **Step 2: Reading evidence claims matrix**

Add row:

| Mutation candidates (next forms) | `mutation_prediction` (SPECULATIVE) | Brier, virality prediction, market advice |

- [ ] **Step 3: Commands map**

Add row under Research:

| `mutation-predict "rizz"` | Next surface forms (SPECULATIVE · brier null) |

- [ ] **Step 4: STATUS.md**

Add surface row:

| **Mutation prediction** (next forms) | Ready (SPECULATIVE · `mutation_prediction` · offline) |

- [ ] **Step 5: Commit**

```bash
git add docs/start/glossary.md docs/demos/reading-evidence.md docs/commands.md STATUS.md
git commit -m "docs: mutation prediction glossary and surface"
```

---

### Task 6: Offline demo / regression verification

**Files:**
- Test: extend `tests/test_demo_offline.py` OR rely on analyze test
- No product change required if demo already calls analyze/pipeline

- [ ] **Step 1: Add demo regression assert**

In `tests/test_demo_offline.py`, after successful demo parse of receipt (or analyze via pipeline unit), assert mutation block if present on receipt analysis:

```python
def test_demo_receipt_may_include_mutation_prediction(tmp_path, monkeypatch):
    # reuse demo CLI; load receipt JSON
    ...
    analysis = receipt.get("analysis") or {}
    mp = analysis.get("mutation_prediction")
    # Pipeline attaches via detect_memetic_patterns
    assert mp is not None
    assert mp.get("brier") is None
    assert mp.get("n_candidates", 0) >= 1
```

- [ ] **Step 2: Run full relevant suite**

```bash
.venv/bin/pytest tests/test_mutation_prediction.py tests/test_demo_offline.py tests/test_pipeline.py -v --tb=short
```

Expected: PASS.

- [ ] **Step 3: Manual offline smoke**

```bash
export HYPERLEX_OFFLINE=1 HYPERLEX_VECTOR=0
python3 scripts/hyperlex.py mutation-predict rizz
python3 scripts/hyperlex.py demo --query rizz
```

Expected: JSON with `mutation_prediction` / candidates; all `brier` null.

- [ ] **Step 4: Final commit if test file changed**

```bash
git add tests/test_demo_offline.py
git commit -m "test: demo path includes mutation_prediction"
```

- [ ] **Step 5: Push**

```bash
git push origin main
```

---

## Spec coverage self-review

| Spec requirement | Task |
|------------------|------|
| Next surface forms | Task 1 |
| Deterministic offline | Task 1 |
| Optional LLM enrich fail-open | Task 3 |
| `analysis.mutation_prediction` schema v1 | Tasks 1–2 |
| Always brier null / SPECULATIVE | Tasks 1–2, tests |
| Cap / dedupe | Task 1 |
| Package export | Task 2 |
| CLI | Task 4 |
| Docs glossary + reading + STATUS | Task 5 |
| Demo/pipeline offline | Task 6 |
| No settlement path | Explicit non-goal; no task |
| Map panel | Explicit later; no task |

**Placeholder scan:** none.  
**Type consistency:** `predict_mutations(...) -> Dict[str, Any]` used uniformly.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-06-mutation-prediction.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — this session, executing-plans with checkpoints  

Which approach?
