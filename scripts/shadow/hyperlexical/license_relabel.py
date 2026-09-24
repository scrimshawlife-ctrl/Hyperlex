"""Relabel Wiktionary-sourced rows with their real licence. No network. D5(a).

692 of 709 Wiktionary-sourced SoT rows carried ``license: operator-local``.
This sets ``license`` to ``CC BY-SA 4.0 (Wiktionary); <previous label note>``
and adds ``source_license: CC-BY-SA-4.0`` (+ ``source_url`` when known). Harvest
sidecar unbind rows whose text (either scheme) derives from a relabelled SoT
text get the same marking. Labels, classes, splits, and texts are untouched.
Idempotent; ``--dry-run`` writes only the summary.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

CC = "CC BY-SA 4.0 (Wiktionary)"
SPDX = "CC-BY-SA-4.0"
_TAG = re.compile(r"\b(?:TOKEN|SLOT|MARKER):")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", _TAG.sub("", text or "").strip().lower())


def is_wiktionary(row: dict) -> bool:
    return (
        "wiktionary.org" in str(row.get("harvest_page") or "")
        or "wiktionary" in str(row.get("provenance") or "").lower()
        or bool(row.get("wiktionary_categories"))
        or str(row.get("license") or "").startswith("CC BY-SA")
    )


def relabelled(license_value: str | None) -> str:
    old = str(license_value or "").strip()
    if old.startswith("CC BY-SA"):
        return old
    if not old:
        return f"{CC}; operator-local labels"
    note = old.replace("operator-local", "operator-local labels", 1) if old.startswith("operator-local") else old
    note = note.replace("labels; labels", "labels")
    return f"{CC}; {note}"


def relabel(store: list[dict], harvest: list[dict]) -> dict:
    texts, changed_store, before = set(), 0, Counter()
    for row in store:
        if not is_wiktionary(row):
            continue
        texts.add(_norm(row.get("text")))
        before[str(row.get("license"))] += 1
        new = relabelled(row.get("license"))
        updates = {"license": new, "source_license": SPDX}
        if row.get("harvest_page") and "wiktionary.org" in str(row["harvest_page"]):
            updates["source_url"] = row["harvest_page"]
        if any(row.get(k) != v for k, v in updates.items()):
            row.update(updates)
            changed_store += 1
    changed_harvest = 0
    for row in harvest:
        if _norm(row.get("text")) in texts:
            new = relabelled(row.get("license"))
            if row.get("license") != new or row.get("source_license") != SPDX:
                row["license"] = new
                row["source_license"] = SPDX
                changed_harvest += 1
    return {
        "n_store": len(store),
        "n_wiktionary_store": sum(1 for r in store if is_wiktionary(r)),
        "n_store_changed": changed_store,
        "n_harvest": len(harvest),
        "n_harvest_changed": changed_harvest,
        "licenses_before": dict(before),
        "licenses_after": dict(Counter(str(r.get("license")) for r in store if is_wiktionary(r))),
    }


def _load(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] if path.is_file() else []


def _write(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--store", required=True)
    p.add_argument("--harvest", required=True)
    p.add_argument("--summary", required=True)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    store_p, harvest_p = Path(args.store), Path(args.harvest)
    store, harvest = _load(store_p), _load(harvest_p)
    summary = relabel(store, harvest)
    summary.update({"as_of": datetime.now(timezone.utc).isoformat(), "dry_run": args.dry_run, "store": str(store_p), "harvest": str(harvest_p)})
    if not args.dry_run and (summary["n_store_changed"] or summary["n_harvest_changed"]):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        for path in (store_p, harvest_p):
            shutil.copy2(path, path.with_name(f"{path.name}.bak-pre-license-relabel-{stamp}"))
        _write(store_p, store)
        _write(harvest_p, harvest)
    Path(args.summary).write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
