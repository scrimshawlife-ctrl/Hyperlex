"""Research export templates — paper-ready markdown + JSON packets."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def export_research_packet(
    payload: Dict[str, Any],
    *,
    out_dir: Path | str,
    title: Optional[str] = None,
    snapshot_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Write a minimal research packet (JSON + Markdown) from a Phase 5 payload.

    Suitable for commits under docs/archive or out/research/.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    sid = snapshot_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = title or payload.get("schema") or "hyperlex-research"
    safe = "".join(c if c.isalnum() or c in "-_." else "-" for c in str(name))[:48]
    base = f"{safe}-{sid}"

    # strip heavy agent lists for paper JSON
    paper = json.loads(json.dumps(payload))
    if isinstance(paper.get("multi_agent"), dict):
        paper["multi_agent"].pop("agents", None)
    if isinstance(paper.get("full"), dict):
        paper["full"].pop("agents", None)
    for run in paper.get("runs") or []:
        if isinstance(run, dict):
            run.pop("full", None)

    json_path = out / f"{base}.json"
    md_path = out / f"{base}.md"
    json_path.write_text(json.dumps(paper, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    schema = paper.get("schema") or "unknown"
    brier = paper.get("brier")
    prov = paper.get("provenance") or "SPECULATIVE"
    lines = [
        f"# Research packet — `{base}`",
        "",
        f"- **Schema:** `{schema}`",
        f"- **Provenance:** {prov}",
        f"- **Brier:** `{brier}` (must remain null unless settled calibration export)",
        f"- **Created:** {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Summary",
        "",
    ]
    if paper.get("ranking"):
        lines.append("| Scenario | Adoption | Cascade | t½ |")
        lines.append("|----------|----------:|:-------:|---:|")
        for r in paper["ranking"]:
            lines.append(
                f"| {r.get('scenario_id')} | {r.get('final_adoption_rate')} | "
                f"{r.get('cascade_success')} | {r.get('time_to_half')} |"
            )
        lines.append("")
    if paper.get("best_params"):
        bp = paper["best_params"]
        lines.append(f"Best transmission params: β={bp.get('beta')}, γ={bp.get('gamma')}, MAE={paper.get('mae')}")
        lines.append("")
    if paper.get("hyperstition_risk"):
        hr = paper["hyperstition_risk"]
        lines.append(f"Risk tier: **{hr.get('tier')}** (score {hr.get('risk_score')})")
        lines.append("")
    if paper.get("summary"):
        lines.append("```json")
        lines.append(json.dumps(paper["summary"], indent=2, sort_keys=True))
        lines.append("```")
        lines.append("")
    lines.extend([
        "## Machine packet",
        "",
        f"- [`{json_path.name}`](./{json_path.name})",
        "",
        "## Notes",
        "",
        "- SPECULATIVE research export unless otherwise labeled.",
        "- Do not treat simulation peaks as settled Brier outcomes.",
        "",
    ])
    md_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "ok": True,
        "schema": "hyperlex.research_export.v1",
        "snapshot_id": sid,
        "json_path": str(json_path),
        "md_path": str(md_path),
        "brier": None,
        "provenance": "SPECULATIVE",
    }
