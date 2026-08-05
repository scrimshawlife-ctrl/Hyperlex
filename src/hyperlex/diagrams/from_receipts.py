"""Build Mermaid diagrams from Hyperlex receipts / receipt ledger."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


def _esc(text: str) -> str:
    """Escape text for Mermaid node labels."""
    t = (text or "").replace('"', "'").replace("\n", " ").strip()
    return t[:80] if len(t) > 80 else t


def _safe_id(raw: str, prefix: str = "n") -> str:
    s = "".join(c if c.isalnum() else "_" for c in (raw or "x"))
    if not s or s[0].isdigit():
        s = f"{prefix}_{s}"
    return s[:48]


def _load_receipt_file(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"receipt must be object: {path}")
    return data


def _index_from_receipts(receipts: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize full receipts or ledger bodies into diagram rows."""
    rows: List[Dict[str, Any]] = []
    for i, r in enumerate(receipts):
        if not isinstance(r, dict):
            continue
        # Full receipt vs ledger body
        if "analysis" in r or "provenance" in r:
            prov = r.get("provenance") or {}
            analysis = r.get("analysis") or {}
            lineage = analysis.get("lineage") or {}
            receipt = r.get("receipt") or {}
            hyper = analysis.get("hyperstition") or {}
            vir = analysis.get("virality") or {}
            rows.append({
                "seq": i,
                "integrity": receipt.get("integrity") or prov.get("canonical_hash") or f"r{i}",
                "canonical_hash": prov.get("canonical_hash"),
                "timestamp": prov.get("timestamp"),
                "logged_at": prov.get("timestamp"),
                "lineage_family": lineage.get("family_id"),
                "lineage_confidence": lineage.get("confidence"),
                "matched_terms": lineage.get("matched_terms") or [],
                "hyperstition_risk": prov.get("hyperstition_risk") or hyper.get("loop_stage"),
                "virality": vir.get("hybrid_score"),
                "ingest_source": prov.get("ingest_source"),
                "query": (r.get("ingest") or {}).get("query"),
                "receipt_path": receipt.get("path"),
            })
        else:
            # ledger index body
            rows.append({
                "seq": i,
                "integrity": r.get("integrity") or f"r{i}",
                "canonical_hash": r.get("canonical_hash"),
                "timestamp": r.get("timestamp") or r.get("logged_at"),
                "logged_at": r.get("logged_at") or r.get("timestamp"),
                "lineage_family": r.get("lineage_family"),
                "lineage_confidence": r.get("lineage_confidence"),
                "matched_terms": r.get("matched_terms") or [],
                "hyperstition_risk": r.get("hyperstition_risk"),
                "virality": r.get("virality"),
                "ingest_source": r.get("ingest_source"),
                "query": r.get("query"),
                "receipt_path": r.get("receipt_path"),
            })
    return rows


def diagram_lineage_distribution(rows: Sequence[Dict[str, Any]]) -> str:
    """Pie + mindmap-style flowchart of family frequencies."""
    counts: Counter[str] = Counter()
    for row in rows:
        fam = row.get("lineage_family") or "unmatched"
        counts[str(fam)] += 1
    if not counts:
        counts["empty"] = 0

    lines = [
        "%% hyperlex.diagram.v1 kind=lineage_distribution",
        "pie showData",
        '  title Lineage families in receipt history',
    ]
    for fam, n in counts.most_common():
        lines.append(f'  "{_esc(fam)}" : {n}')
    return "\n".join(lines) + "\n"


def diagram_receipt_timeline(rows: Sequence[Dict[str, Any]], *, max_nodes: int = 24) -> str:
    """Left-to-right timeline of receipts with lineage labels."""
    subset = list(rows)[-max_nodes:]
    lines = [
        "%% hyperlex.diagram.v1 kind=receipt_timeline",
        "flowchart LR",
        "  classDef fam fill:#0f3460,stroke:#e94560,color:#fff",
        "  classDef none fill:#1a1a2e,stroke:#888,color:#ccc",
        "  classDef act fill:#e94560,stroke:#fff,color:#fff",
    ]
    if not subset:
        lines.append('  empty["No receipts"]')
        lines.append("  class empty none")
        return "\n".join(lines) + "\n"

    prev = None
    for i, row in enumerate(subset):
        nid = _safe_id(str(row.get("integrity") or i), "r")
        fam = row.get("lineage_family") or "unmatched"
        stage = row.get("hyperstition_risk") or "?"
        conf = row.get("lineage_confidence")
        conf_s = f"{float(conf):.2f}" if isinstance(conf, (int, float)) else "-"
        ts = str(row.get("timestamp") or row.get("logged_at") or "")[:19]
        label = f"{_esc(str(fam))}\\n{stage} conf={conf_s}\\n{_esc(ts)}"
        lines.append(f'  {nid}["{label}"]')
        if stage == "ACTUALIZING":
            lines.append(f"  class {nid} act")
        elif fam == "unmatched":
            lines.append(f"  class {nid} none")
        else:
            lines.append(f"  class {nid} fam")
        if prev is not None:
            lines.append(f"  {prev} --> {nid}")
        prev = nid
    return "\n".join(lines) + "\n"


def diagram_receipt_flow(receipt: Dict[str, Any]) -> str:
    """Single-receipt emergence flowchart (intake → analysis cascade → archive)."""
    analysis = receipt.get("analysis") or {}
    prov = receipt.get("provenance") or {}
    lineage = analysis.get("lineage") or {}
    hyper = analysis.get("hyperstition") or {}
    vir = analysis.get("virality") or {}
    mem = analysis.get("memetics") or {}
    neos = analysis.get("neologisms") or []
    receipt_b = receipt.get("receipt") or {}

    fam = lineage.get("family_id") or "none"
    conf = lineage.get("confidence")
    conf_s = f"{float(conf):.2f}" if isinstance(conf, (int, float)) else "n/a"
    stage = hyper.get("loop_stage") or prov.get("hyperstition_risk") or "?"
    hybrid = vir.get("hybrid_score")
    hybrid_s = f"{float(hybrid):.2f}" if isinstance(hybrid, (int, float)) else "?"
    typology = mem.get("typology") or "?"
    n_neo = len(neos)
    integ = receipt_b.get("integrity") or prov.get("canonical_hash") or "?"
    src = prov.get("ingest_source") or "?"
    terms = ", ".join(str(t) for t in (lineage.get("matched_terms") or [])[:5]) or "—"

    lines = [
        "%% hyperlex.diagram.v1 kind=receipt_flow",
        "flowchart TB",
        f'  intake["Gate of Intake\\nsource={_esc(str(src))}"]',
        f'  neo["Neologisms\\nn={n_neo}"]',
        f'  lin["Lineage\\n{_esc(str(fam))} conf={conf_s}\\n{_esc(terms)}"]',
        f'  vir["Virality\\nhybrid={hybrid_s}"]',
        f'  mem["Memetics\\n{_esc(str(typology))}"]',
        f'  hyp["Hyperstition\\n{_esc(str(stage))}"]',
        f'  arch["Archive\\nintegrity={_esc(str(integ)[:12])}\\nbrier=null"]',
        "  intake --> neo --> lin --> vir --> mem --> hyp --> arch",
        "  hyp -.->|feedback| intake",
        "  style intake fill:#0f3460,stroke:#e94560,color:#fff",
        "  style hyp fill:#e94560,stroke:#fff,color:#fff",
        "  style arch fill:#1a1a2e,stroke:#e94560,color:#fff",
        "  style lin fill:#16213e,stroke:#e94560,color:#fff",
    ]
    return "\n".join(lines) + "\n"


def diagram_family_graph(rows: Sequence[Dict[str, Any]]) -> str:
    """Family nodes with edges to matched terms seen across history."""
    fam_terms: Dict[str, Counter[str]] = defaultdict(Counter)
    fam_n: Counter[str] = Counter()
    for row in rows:
        fam = str(row.get("lineage_family") or "unmatched")
        fam_n[fam] += 1
        for t in row.get("matched_terms") or []:
            fam_terms[fam][str(t)] += 1

    lines = [
        "%% hyperlex.diagram.v1 kind=family_graph",
        "flowchart LR",
        "  classDef family fill:#0f3460,stroke:#e94560,color:#fff",
        "  classDef term fill:#1a1a2e,stroke:#888,color:#eee",
    ]
    if not fam_n:
        lines.append('  empty["No lineage data"]')
        return "\n".join(lines) + "\n"

    for fam, n in fam_n.most_common():
        fid = _safe_id(fam, "f")
        lines.append(f'  {fid}["{_esc(fam)}\\nn={n}"]')
        lines.append(f"  class {fid} family")
        for term, tc in fam_terms[fam].most_common(8):
            tid = _safe_id(f"{fam}_{term}", "t")
            lines.append(f'  {tid}("{_esc(term)}×{tc}")')
            lines.append(f"  class {tid} term")
            lines.append(f"  {fid} --> {tid}")
    return "\n".join(lines) + "\n"


def diagram_from_ledger(
    *,
    ledger_path: Optional[Path | str] = None,
    limit: int = 50,
    lineage_family: Optional[str] = None,
) -> Dict[str, str]:
    """Load receipt ledger and return named Mermaid sources."""
    from ..receipt.ledger import list_receipts

    bodies = list_receipts(ledger_path, limit=limit, lineage_family=lineage_family)
    rows = _index_from_receipts(bodies)
    return {
        "lineage_distribution": diagram_lineage_distribution(rows),
        "receipt_timeline": diagram_receipt_timeline(rows),
        "family_graph": diagram_family_graph(rows),
        "meta": json.dumps({
            "n_rows": len(rows),
            "source": "receipt_ledger",
            "lineage_family_filter": lineage_family,
        }, sort_keys=True),
    }


def diagram_from_receipt_files(
    paths: Iterable[Path | str],
) -> Dict[str, str]:
    """Load receipt JSON files and return diagram set + per-receipt flows."""
    receipts: List[Dict[str, Any]] = []
    flows: Dict[str, str] = {}
    for p in paths:
        path = Path(p)
        if not path.exists():
            continue
        rec = _load_receipt_file(path)
        receipts.append(rec)
        flows[f"flow_{path.stem}"] = diagram_receipt_flow(rec)

    rows = _index_from_receipts(receipts)
    out = {
        "lineage_distribution": diagram_lineage_distribution(rows),
        "receipt_timeline": diagram_receipt_timeline(rows),
        "family_graph": diagram_family_graph(rows),
        "meta": json.dumps({"n_receipts": len(receipts), "source": "receipt_files"}, sort_keys=True),
    }
    out.update(flows)
    return out


def _html_shell(title: str, mermaid_src: str) -> str:
    # strip fence if present
    body = mermaid_src.strip()
    if body.startswith("```"):
        body = "\n".join(body.split("\n")[1:])
        if body.endswith("```"):
            body = body[: body.rfind("```")]
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>{_esc(title)}</title>
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});
  </script>
  <style>
    body {{ background:#0b0b12; color:#eee; font-family: system-ui, sans-serif; margin: 1.5rem; }}
    h1 {{ font-size: 1.1rem; color:#e94560; }}
    .mermaid {{ background:#12121c; padding:1rem; border-radius:8px; }}
  </style>
</head>
<body>
  <h1>{_esc(title)}</h1>
  <pre class="mermaid">
{body}
  </pre>
</body>
</html>
"""


def write_diagram_bundle(
    diagrams: Dict[str, str],
    out_dir: Path | str,
    *,
    html: bool = True,
    prefix: str = "hyperlex",
) -> Dict[str, str]:
    """
    Write .mmd (and optional .html) files for each diagram key.

    Returns map of diagram_key → written path.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: Dict[str, str] = {}
    for key, src in diagrams.items():
        if key == "meta":
            meta_path = out / f"{prefix}_meta.json"
            # meta may already be JSON string
            try:
                payload = json.loads(src) if isinstance(src, str) else src
            except json.JSONDecodeError:
                payload = {"raw": src}
            meta_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            written["meta"] = str(meta_path)
            continue
        mmd_path = out / f"{prefix}_{key}.mmd"
        # store as fenced mermaid for markdown paste + bare for HTML
        fenced = f"```mermaid\n{src.strip()}\n```\n"
        mmd_path.write_text(fenced, encoding="utf-8")
        written[key] = str(mmd_path)
        if html:
            html_path = out / f"{prefix}_{key}.html"
            html_path.write_text(_html_shell(f"{prefix} · {key}", src), encoding="utf-8")
            written[f"{key}_html"] = str(html_path)
    return written
