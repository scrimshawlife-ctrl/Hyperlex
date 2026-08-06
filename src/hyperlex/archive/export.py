"""Export sanitized long-term analysis archive from receipts + ledger.

GitHub Pages hosts this as a **static history of runs**:
  docs/archive/runs/<snapshot_id>/   — immutable dated snapshots
  docs/archive/latest/               — copy of the most recent analysis export
  docs/archive/index.md + catalog.json — browsable history catalog
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from collections import Counter

from ..receipt.ledger import default_ledger_path, list_receipts
from ..receipt.stats import ledger_stats

ARCHIVE_SCHEMA = "hyperlex.analysis_archive.v1"
CATALOG_SCHEMA = "hyperlex.archive_catalog.v1"
RUN_KIND_ANALYSIS = "analysis"
RUN_KIND_PHASE5 = "phase5_scenario"
RUN_KIND_SCAN = "scan"


def sanitize_receipt_summary(
    receipt: Dict[str, Any],
    *,
    max_observed: int = 240,
) -> Dict[str, Any]:
    """
    Reduce a full receipt to a publish-safe summary for long-term analysis.

    Drops bulk raw_signal / full observed text beyond preview.
    Keeps hashes, lineage, typology, virality metrics, hyperstition stage.
    """
    prov = receipt.get("provenance") or {}
    analysis = receipt.get("analysis") or {}
    lineage = analysis.get("lineage") or {}
    mem = analysis.get("memetics") or {}
    vir = analysis.get("virality") or {}
    hyper = analysis.get("hyperstition") or {}
    rec = receipt.get("receipt") or {}
    ingest = receipt.get("ingest") or {}
    observed = str(receipt.get("observed") or "")

    return {
        "integrity": rec.get("integrity"),
        "canonical_hash": prov.get("canonical_hash"),
        "timestamp": prov.get("timestamp"),
        "version": prov.get("version"),
        "ingest_source": prov.get("ingest_source") or ingest.get("source"),
        "query": ingest.get("query"),
        "source_fingerprint_id": (prov.get("source_fingerprint") or {}).get("fingerprint_id"),
        "brier": prov.get("brier"),  # should be null on open receipts
        "lineage_family": lineage.get("family_id"),
        "lineage_confidence": lineage.get("confidence"),
        "matched_terms": (lineage.get("matched_terms") or [])[:12],
        "typology": mem.get("typology_primary") or mem.get("typology"),
        "is_memetic": mem.get("is_memetic"),
        "virality_hybrid": vir.get("hybrid_score"),
        "virality_predicted": (vir.get("prediction") or {}).get("predicted_hybrid"),
        "hyperstition_stage": hyper.get("loop_stage") or prov.get("hyperstition_risk"),
        "n_neologisms": len(analysis.get("neologisms") or []),
        "observed_preview": observed[:max_observed],
        "epistemic": {
            "lineage": "INFERRED" if lineage else "NOT_COMPUTABLE",
            "virality_prediction": "SPECULATIVE",
            "brier": "NOT_COMPUTABLE" if prov.get("brier") is None else "REQUIRES_SERIES",
        },
    }


def sanitize_phase5_summary(scenario: Dict[str, Any]) -> Dict[str, Any]:
    """Publish-safe Phase 5 scenario digest (no full agent lists / long trajectories)."""
    # Multi-term packet: one summary per atomic seed (never a blended seed_term)
    if scenario.get("schema") == "hyperlex.phase5_multi_term.v1" or scenario.get("multi_term"):
        summaries = list(scenario.get("summaries") or [])
        agg = scenario.get("aggregate") or {}
        return {
            "schema": "hyperlex.phase5_run_summary.v1",
            "seed_term": None,
            "terms": list(scenario.get("terms") or []),
            "original_seed": scenario.get("original_seed"),
            "multi_term": True,
            "n_terms": scenario.get("n_terms") or len(summaries),
            "per_term": summaries,
            "lineage_family": None,
            "domain": scenario.get("domain"),
            "created_at": scenario.get("created_at"),
            "risk_score": None,
            "risk_tier": agg.get("top_risk_tier"),
            "transmission_peak": None,
            "transmission_reach": None,
            "agent_adoption_rate": None,
            "cascade_success": None,
            "phylogeny_family": None,
            "phylogeny_n_nodes": None,
            "provenance": "SPECULATIVE",
            "brier": None,
            "publish_safe": True,
            "note": (
                "Atomic multi-term run: each lexicon item simulated separately "
                "(e.g. sigma | rizz | locked in). top_risk_tier is max severity only."
            ),
        }

    risk = scenario.get("hyperstition_risk") or {}
    tsum = (scenario.get("transmission") or {}).get("summary") or {}
    asum = (scenario.get("multi_agent") or {}).get("summary") or {}
    phylo = scenario.get("phylogeny") or {}
    return {
        "schema": "hyperlex.phase5_run_summary.v1",
        "seed_term": scenario.get("seed_term"),
        "terms": [scenario.get("seed_term")] if scenario.get("seed_term") else [],
        "multi_term": False,
        "lineage_family": scenario.get("lineage_family"),
        "domain": scenario.get("domain"),
        "created_at": scenario.get("created_at"),
        "risk_score": risk.get("risk_score"),
        "risk_tier": risk.get("tier"),
        "transmission_peak": tsum.get("peak_mean_adoption"),
        "transmission_reach": tsum.get("final_reach_fraction"),
        "agent_adoption_rate": asum.get("final_adoption_rate"),
        "cascade_success": asum.get("cascade_success"),
        "phylogeny_family": phylo.get("family_id") if phylo.get("ok") else None,
        "phylogeny_n_nodes": phylo.get("n_nodes"),
        "provenance": "SPECULATIVE",
        "brier": None,
        "publish_safe": True,
    }


def _load_receipt_files(paths: Sequence[Path]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in paths:
        if not p.exists() or p.suffix != ".json" or p.name == "MANIFEST.json":
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and ("analysis" in data or "provenance" in data):
            out.append(data)
    return out


def _write_analysis_bundle(
    out: Path,
    *,
    snap: str,
    summaries: List[Dict[str, Any]],
    ledger_rows: List[Dict[str, Any]],
    stats: Dict[str, Any],
    run_kind: str = RUN_KIND_ANALYSIS,
    notes: str = "",
) -> Dict[str, Any]:
    receipts_out = out / "receipts"
    receipts_out.mkdir(parents=True, exist_ok=True)

    # clear old receipts when refreshing a directory
    for old in receipts_out.glob("*.json"):
        try:
            old.unlink()
        except OSError:
            pass

    written_receipts: List[str] = []
    for i, s in enumerate(summaries):
        integ = s.get("integrity") or f"anon_{i}"
        name = f"{integ}.json"
        (receipts_out / name).write_text(
            json.dumps(s, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written_receipts.append(f"receipts/{name}")

    if ledger_rows:
        with (out / "ledger_index.jsonl").open("w", encoding="utf-8") as fh:
            for row in ledger_rows:
                fh.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")

    # Family / stage counts from receipt *summaries* (not ledger-only — avoids
    # misleading "betting-sharp:5" when goldens span 8 families).
    fam_ctr: Counter = Counter()
    stage_ctr: Counter = Counter()
    src_ctr: Counter = Counter()
    confs: List[float] = []
    for s in summaries:
        fam = s.get("lineage_family") or "(none)"
        fam_ctr[str(fam)] += 1
        st = s.get("hyperstition_stage")
        if st:
            stage_ctr[str(st)] += 1
        src = s.get("ingest_source")
        if src:
            src_ctr[str(src)] += 1
        lc = s.get("lineage_confidence")
        if isinstance(lc, (int, float)):
            confs.append(float(lc))
    summary_families = dict(fam_ctr.most_common())
    n_with_lineage = sum(v for k, v in summary_families.items() if k != "(none)")
    mean_lc = round(sum(confs) / len(confs), 3) if confs else None

    index = {
        "schema": ARCHIVE_SCHEMA,
        "run_kind": run_kind,
        "snapshot_id": snap,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "static_run_history",
        "primary_store": "local ~/.hyperlex (not replaced by this archive)",
        "publish_safe": True,
        "n_receipt_summaries": len(summaries),
        "n_ledger_rows": len(ledger_rows),
        "receipt_files": written_receipts,
        "notes": notes or None,
        "stats": {
            "n_entries": len(summaries) if summaries else stats.get("n_entries"),
            "n_with_lineage": n_with_lineage if summaries else stats.get("n_with_lineage"),
            "families": summary_families if summaries else (stats.get("families") or {}),
            "families_from_ledger": stats.get("families") or {},
            "hyperstition_stages": dict(stage_ctr.most_common()) if stage_ctr else (stats.get("hyperstition_stages") or {}),
            "ingest_sources": dict(src_ctr.most_common()) if src_ctr else (stats.get("ingest_sources") or {}),
            "mean_lineage_confidence": mean_lc if mean_lc is not None else stats.get("mean_lineage_confidence"),
            "chain_ok": stats.get("chain_ok"),
        },
        "summaries": summaries,
    }
    (out / "index.json").write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    display_fams = index["stats"]["families"] or {}
    fam_lines = "\n".join(
        f"| `{k}` | {v} | [map](../../../map/index.md?family={k}) |"
        for k, v in display_fams.items()
        if k != "(none)"
    ) or "| — | 0 | — |"
    none_line = ""
    if "(none)" in display_fams:
        none_line = f"\n| `(none)` | {display_fams['(none)']} | — |"
    md = f"""# Run snapshot — `{snap}`

**Kind:** `{run_kind}` · **Publish-safe static history** for GitHub Pages.

Primary durable store remains local (`~/.hyperlex/`). This bundle is sanitized
for the docs site / git history — not a replacement for the operator ledger.

| Field | Value |
|-------|-------|
| Snapshot | `{snap}` |
| Kind | `{run_kind}` |
| Receipt summaries | {len(summaries)} |
| Ledger rows | {len(ledger_rows)} |
| Chain OK | {stats.get("chain_ok")} |

## Family distribution

| Family | Count | Map |
|--------|------:|-----|
{fam_lines}{none_line}

Open the [slang lineage map](../../../map/index.md) for the full constellation.
Deep-link a term from a receipt: `…/map/index.md?term=<primary_term>`.

## Machine index

- [`index.json`](./index.json) — full snapshot metadata + summaries
- `ledger_index.jsonl` — ledger extract when exported with ledger
- `receipts/` — per-receipt sanitized JSON (JSON files; browse via index)

## Epistemic notes

- Lineage matches are **INFERRED**
- Virality predictions are **SPECULATIVE**
- Open receipts keep `brier: null` (Brier requires settlement)
- This Pages snapshot is a **static history of runs**, not live state
- Map / cosine neighbors are **not** Brier

Regenerate / append history:

```bash
python3 scripts/hyperlex.py archive-export --include-golden --history
```

Back to [run history catalog](../../index.md) · [Slang map](../../../map/index.md).
"""
    (out / "README.md").write_text(md, encoding="utf-8")
    (out / "index.md").write_text(md, encoding="utf-8")
    return index


def export_analysis_archive(
    *,
    out_dir: Path | str,
    ledger_path: Optional[Path | str] = None,
    receipt_dirs: Optional[Sequence[Path | str]] = None,
    receipt_files: Optional[Sequence[Path | str]] = None,
    include_ledger_index: bool = True,
    snapshot_id: Optional[str] = None,
    notes: str = "",
) -> Dict[str, Any]:
    """
    Write a long-term analysis archive bundle to ``out_dir``.

    For dated history + catalog, prefer ``export_run_history`` or pass
    ``history_root`` via the CLI ``--history`` flag.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    snap = snapshot_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ledger = Path(ledger_path) if ledger_path else default_ledger_path()

    files: List[Path] = []
    for d in receipt_dirs or []:
        dp = Path(d)
        if dp.is_dir():
            files.extend(sorted(dp.glob("*.json")))
    for f in receipt_files or []:
        files.append(Path(f))

    full_receipts = _load_receipt_files(files)
    summaries = [sanitize_receipt_summary(r) for r in full_receipts]

    ledger_rows: List[Dict[str, Any]] = []
    if include_ledger_index and ledger.exists():
        for row in list_receipts(ledger, limit=10**9):
            ledger_rows.append({
                "integrity": row.get("integrity"),
                "canonical_hash": row.get("canonical_hash"),
                "timestamp": row.get("timestamp") or row.get("logged_at"),
                "lineage_family": row.get("lineage_family"),
                "lineage_confidence": row.get("lineage_confidence"),
                "hyperstition_risk": row.get("hyperstition_risk"),
                "ingest_source": row.get("ingest_source"),
                "receipt_path": row.get("receipt_path"),
                "observed_preview": (row.get("observed_preview") or "")[:240],
            })

    stats = ledger_stats(ledger) if ledger.exists() else {
        "n_entries": 0,
        "families": {},
        "chain_ok": None,
        "note": "no local ledger",
    }

    _write_analysis_bundle(
        out,
        snap=snap,
        summaries=summaries,
        ledger_rows=ledger_rows,
        stats=stats,
        notes=notes,
    )

    return {
        "ok": True,
        "snapshot_id": snap,
        "run_kind": RUN_KIND_ANALYSIS,
        "out_dir": str(out),
        "n_receipt_summaries": len(summaries),
        "n_ledger_rows": len(ledger_rows),
        "index": str(out / "index.json"),
    }


def default_archive_root(repo_root: Optional[Path | str] = None) -> Path:
    if repo_root is not None:
        return Path(repo_root) / "docs" / "archive"
    # package → parents[3] may be repo when editable
    here = Path(__file__).resolve()
    candidates = [
        here.parents[3] / "docs" / "archive",
        Path.cwd() / "docs" / "archive",
    ]
    for c in candidates:
        if c.parent.is_dir():
            return c
    return candidates[-1]


def rebuild_archive_catalog(
    archive_root: Path | str,
    *,
    site_base: str = "https://scrimshawlife-ctrl.github.io/Hyperlex-Hermes-Specs/archive/",
) -> Dict[str, Any]:
    """
    Scan ``runs/`` (+ ``latest``) and write catalog.json + index.md for Pages.
    """
    root = Path(archive_root)
    root.mkdir(parents=True, exist_ok=True)
    runs_dir = root / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    entries: List[Dict[str, Any]] = []
    for d in runs_dir.iterdir():
        if not d.is_dir():
            continue
        idx_path = d / "index.json"
        if not idx_path.is_file():
            continue
        try:
            idx = json.loads(idx_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        snap = idx.get("snapshot_id") or d.name
        kind = idx.get("run_kind") or RUN_KIND_ANALYSIS
        phase5 = idx.get("phase5") or {}
        terms = idx.get("terms") or phase5.get("terms") or []
        multi = bool(idx.get("multi_term") or phase5.get("multi_term"))
        entries.append({
            "snapshot_id": snap,
            "run_kind": kind,
            "created_at": idx.get("created_at"),
            "n_receipt_summaries": idx.get("n_receipt_summaries"),
            "n_ledger_rows": idx.get("n_ledger_rows"),
            "families": (idx.get("stats") or {}).get("families") or {},
            "path": f"runs/{d.name}/",
            "site_path": f"runs/{d.name}/",
            "risk_tier": idx.get("risk_tier") or phase5.get("risk_tier"),
            "seed_term": idx.get("seed_term") or phase5.get("seed_term"),
            "terms": terms,
            "multi_term": multi,
            "notes": idx.get("notes"),
        })
    # Newest first by created_at (ISO), not directory name
    entries.sort(key=lambda e: (e.get("created_at") or "", e.get("snapshot_id") or ""), reverse=True)

    # also record latest pointer
    latest_idx = root / "latest" / "index.json"
    latest_snap = None
    if latest_idx.is_file():
        try:
            latest_snap = json.loads(latest_idx.read_text(encoding="utf-8")).get("snapshot_id")
        except (OSError, json.JSONDecodeError):
            latest_snap = None

    catalog = {
        "schema": CATALOG_SCHEMA,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "static_history_of_runs",
        "primary_store": "local ~/.hyperlex",
        "publish_safe": True,
        "site_base": site_base,
        "n_runs": len(entries),
        "latest_snapshot_id": latest_snap,
        "runs": entries,
    }
    (root / "catalog.json").write_text(
        json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    def _index_row(e: Dict[str, Any]) -> str:
        fam = e.get("families") or {}
        top_fam = ", ".join(f"`{k}`×{v}" for k, v in list(fam.items())[:5]) or "—"
        link = f"./runs/{Path(e['path']).name}/index.md"
        kind = e.get("run_kind") or "analysis"
        is_phase5 = kind == "phase5_scenario"
        kind_cls = "hlx-kind hlx-kind--phase5" if is_phase5 else "hlx-kind hlx-kind--analysis"
        kind_label = "phase5 · SPECULATIVE" if is_phase5 else "analysis"
        bits: List[str] = []
        if e.get("n_receipt_summaries"):
            bits.append(f"{e['n_receipt_summaries']} receipts")
        if e.get("risk_tier"):
            bits.append(f"risk **{e['risk_tier']}**")
        terms = e.get("terms") or []
        if e.get("multi_term") and terms:
            bits.append("atoms " + " · ".join(f"`{t}`" for t in terms[:6]))
        elif e.get("seed_term"):
            bits.append(f"term `{e['seed_term']}`")
        meta = " · ".join(bits) if bits else "—"
        note = f"  \n  <span class=\"hlx-index-note\">{e['notes']}</span>" if e.get("notes") else ""
        return (
            f'<div class="hlx-index-row {"hlx-index-row--phase5" if is_phase5 else "hlx-index-row--analysis"}" markdown>\n\n'
            f'<span class="{kind_cls}">{kind_label}</span>\n'
            f"**[{e['snapshot_id']}]({link})**  \n"
            f"{meta}  \n"
            f"Families: {top_fam}{note}\n\n"
            f"</div>\n"
        )

    analysis_entries = [e for e in entries if (e.get("run_kind") or "analysis") != "phase5_scenario"]
    phase5_entries = [e for e in entries if (e.get("run_kind") or "") == "phase5_scenario"]
    analysis_block = "\n".join(_index_row(e) for e in analysis_entries) or "_No analysis snapshots yet._\n"
    phase5_block = "\n".join(_index_row(e) for e in phase5_entries) or "_No Phase 5 snapshots yet._\n"

    md = f"""# Run history

<div class="hlx-status" markdown>
<span><span class="hlx-dot"></span><strong>{len(entries)} runs</strong></span>
<span>Static · publish-safe · GitHub Pages</span>
<span>Primary store: <code>~/.hyperlex/</code></span>
{f"<span>Latest analysis: <code>{latest_snap}</code></span>" if latest_snap else ""}
</div>

Publish-safe history of Hyperlex runs. **Not** live operator state — that lives in `~/.hyperlex/`.

<div class="hlx-path-grid" markdown>

<div class="hlx-path-card hlx-path-card--primary" markdown>

**Researchers**

How to interpret kinds, atoms, risk, and vector scores without overclaiming.

[Reading evidence →](../demos/reading-evidence.md){{ .md-button .md-button--primary }}

</div>

<div class="hlx-path-card" markdown>

**Operators**

Append sanitized snapshots from local receipts / Phase 5.

[Operator loop →](../operator-loop.md){{ .md-button }}

</div>

</div>

**How to read this index**

| Kind | Meaning |
|------|---------|
| <span class="hlx-kind hlx-kind--analysis">analysis</span> | Receipt-backed analyze / pipeline snapshots |
| <span class="hlx-kind hlx-kind--phase5">phase5 · SPECULATIVE</span> | Research sim. **atoms** = separate lexicon terms (not one blended seed) |
| risk tier | Advisory only — not market advice; not Brier |
| vector / similarity | Cosine neighbors if present — **not** Brier; see [reading guide](../demos/reading-evidence.md) |

Machine index: [`catalog.json`](./catalog.json) ·
[Latest analysis](./latest/index.md){f" (`{latest_snap}`)" if latest_snap else ""} ·
[Atomic terms](../demos/atomic-terms.md) ·
[Reading evidence](../demos/reading-evidence.md) ·
[Operator loop](../operator-loop.md)

## Analysis snapshots

Receipt-backed history. Prefer these when citing lineage / receipts.

{analysis_block}

## Phase 5 research (SPECULATIVE)

Scenario literature only — never Brier. Atoms stay separate.

{phase5_block}

## Published vs not

| On Pages | Stays local |
|----------|-------------|
| Sanitized receipt summaries | Full raw signals / API keys |
| Lineage, typology, virality, stage | Score-log settlements (unless you export) |
| Phase 5 digests (SPECULATIVE) | Invented Brier (never) |
| Vector method + samples | Live `~/.hyperlex/chroma` / Cloud |

## Append a run

```bash
python3 scripts/hyperlex.py archive-export --include-golden --history
python3 scripts/hyperlex.py archive-export --include-home-receipts --history
python3 scripts/hyperlex.py simulate --term rizz --out /tmp/p5.json
python3 scripts/hyperlex.py archive-export --phase5 /tmp/p5.json --history
python3 scripts/hyperlex.py archive-catalog
```

Commit + push `docs/archive/` → Pages rebuild (`.github/workflows/docs.yml`).

<p class="hlx-posture">
Hermes skill · Brier requires settlement · vector ≠ probability · primary store ~/.hyperlex
</p>
"""
    (root / "index.md").write_text(md, encoding="utf-8")
    (root / "README.md").write_text(md, encoding="utf-8")
    return catalog


def _copy_tree(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def export_run_history(
    *,
    archive_root: Path | str,
    ledger_path: Optional[Path | str] = None,
    receipt_dirs: Optional[Sequence[Path | str]] = None,
    receipt_files: Optional[Sequence[Path | str]] = None,
    include_ledger_index: bool = True,
    snapshot_id: Optional[str] = None,
    update_latest: bool = True,
    notes: str = "",
    phase5_scenario: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Write a dated run under ``archive_root/runs/<snapshot_id>/``, refresh catalog,
    and optionally mirror to ``latest/`` (analysis runs only).
    """
    root = Path(archive_root)
    snap = snapshot_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    # filesystem-safe
    safe = "".join(c if c.isalnum() or c in "-_." else "-" for c in snap)
    run_dir = root / "runs" / safe

    if phase5_scenario is not None:
        run_dir.mkdir(parents=True, exist_ok=True)
        summary = sanitize_phase5_summary(phase5_scenario)
        multi = bool(summary.get("multi_term"))
        # keep compact scenario without full agent table
        if multi:
            compact = {
                "schema": phase5_scenario.get("schema") or "hyperlex.phase5_multi_term.v1",
                "original_seed": phase5_scenario.get("original_seed"),
                "terms": phase5_scenario.get("terms"),
                "n_terms": phase5_scenario.get("n_terms"),
                "multi_term": True,
                "domain": phase5_scenario.get("domain"),
                "created_at": phase5_scenario.get("created_at"),
                "brier": None,
                "provenance": "SPECULATIVE",
                "summaries": phase5_scenario.get("summaries"),
                "aggregate": phase5_scenario.get("aggregate"),
                "note": phase5_scenario.get("note"),
            }
            terms_list = summary.get("terms") or []
            terms_disp = " · ".join(f"`{t}`" for t in terms_list)
            md_seed_row = f"| Terms (atomic) | {terms_disp} |"
            # per-term table for usable Pages reading
            per_rows = []
            for row in (summary.get("per_term") or phase5_scenario.get("summaries") or []):
                per_rows.append(
                    f"| `{row.get('seed_term')}` | `{row.get('risk_tier')}` | "
                    f"`{row.get('risk_score')}` | `{row.get('transmission_peak')}` | `null` |"
                )
            per_table = "\n".join(per_rows) if per_rows else "| — | — | — | — | `null` |"
            multi_body = f"""
### Per-term results (separate)

The free-text input may look like one phrase, but each **atom** is simulated alone.

| Atom | Risk tier | Risk score | Transmission peak | Brier |
|------|-----------|------------|-------------------|-------|
{per_table}

`original_seed` (input only): `{phase5_scenario.get("original_seed")}`
"""
        else:
            compact = {
                "schema": phase5_scenario.get("schema") or "hyperlex.phase5_scenario.v1",
                "seed_term": phase5_scenario.get("seed_term"),
                "lineage_family": phase5_scenario.get("lineage_family"),
                "domain": phase5_scenario.get("domain"),
                "created_at": phase5_scenario.get("created_at"),
                "brier": None,
                "provenance": "SPECULATIVE",
                "hyperstition_risk": phase5_scenario.get("hyperstition_risk"),
                "transmission_summary": (phase5_scenario.get("transmission") or {}).get("summary"),
                "multi_agent_summary": (phase5_scenario.get("multi_agent") or {}).get("summary"),
                "phylogeny": {
                    "family_id": (phase5_scenario.get("phylogeny") or {}).get("family_id"),
                    "n_nodes": (phase5_scenario.get("phylogeny") or {}).get("n_nodes"),
                    "ok": (phase5_scenario.get("phylogeny") or {}).get("ok"),
                }
                if phase5_scenario.get("phylogeny")
                else None,
            }
            md_seed_row = f"| Seed term | `{summary.get('seed_term')}` |"
            multi_body = ""
        (run_dir / "phase5.json").write_text(
            json.dumps(compact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        index = {
            "schema": ARCHIVE_SCHEMA,
            "run_kind": RUN_KIND_PHASE5,
            "snapshot_id": snap,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "purpose": "static_run_history",
            "publish_safe": True,
            "primary_store": "local ~/.hyperlex (not replaced by this archive)",
            "n_receipt_summaries": 0,
            "n_ledger_rows": 0,
            "seed_term": summary.get("seed_term"),
            "terms": summary.get("terms"),
            "multi_term": multi,
            "risk_tier": summary.get("risk_tier"),
            "phase5": summary,
            "notes": notes or None,
            "stats": {"families": {}, "chain_ok": None},
        }
        (run_dir / "index.json").write_text(
            json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        md = f"""# Phase 5 run — `{snap}`

**Kind:** `phase5_scenario` · SPECULATIVE research snapshot for Pages.
{"**Multi-term:** each lexicon atom is a separate scenario — not one blended seed." if multi else ""}

| Field | Value |
|-------|-------|
{md_seed_row}
| Domain | `{summary.get("domain")}` |
| Family | `{summary.get("lineage_family") or "—"}` |
| Aggregate risk tier | `{summary.get("risk_tier") or "—"}` |
| Risk score | `{summary.get("risk_score") if summary.get("risk_score") is not None else "—"}` |
| Brier | `null` (never invented) |

{multi_body}

### Files

- [`index.json`](./index.json) — snapshot index
- [`phase5.json`](./phase5.json) — compact scenario / multi-term summaries

[← Run history](../../index.md) · [Atomic terms demo](../../../demos/atomic-terms.md) · [Operator loop](../../../operator-loop.md)
"""
        (run_dir / "index.md").write_text(md, encoding="utf-8")
        (run_dir / "README.md").write_text(md, encoding="utf-8")
        catalog = rebuild_archive_catalog(root)
        return {
            "ok": True,
            "snapshot_id": snap,
            "run_kind": RUN_KIND_PHASE5,
            "out_dir": str(run_dir),
            "catalog_runs": catalog.get("n_runs"),
            "latest_updated": False,
            "index": str(run_dir / "index.json"),
            "multi_term": multi,
        }

    # analysis path
    result = export_analysis_archive(
        out_dir=run_dir,
        ledger_path=ledger_path,
        receipt_dirs=receipt_dirs,
        receipt_files=receipt_files,
        include_ledger_index=include_ledger_index,
        snapshot_id=snap,
        notes=notes,
    )
    latest_updated = False
    if update_latest:
        _copy_tree(run_dir, root / "latest")
        latest_updated = True
    catalog = rebuild_archive_catalog(root)
    result["catalog_runs"] = catalog.get("n_runs")
    result["latest_updated"] = latest_updated
    result["history_path"] = str(run_dir)
    result["catalog"] = str(root / "catalog.json")
    return result
