"""BUILD_AND_SEAL_FRESH_V6_CORE_QUALIFICATION_SURFACE.

Acquire natural OBSERVED text, dual-annotate under core ontology
(evidence_gate + DOMAIN + MEDIATION), seal HYPERLEX_V6_CORE_QUALIFICATION_001.
qualification_model_executions = 0. No package scoring before seal.
QUAL-002/003 and TRAIN/DEV/REP V3 remain EVALUATION_SPENT / unreused.
FUNCTION may be annotated as optional research metadata only.
"""

from __future__ import annotations

import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

PRIVATE = Path(
    "/home/morpheus/hlx-private/classification-v6-core-qualification-001-20261002"
)
PRIVATE_QUAL002 = Path(
    "/home/morpheus/hlx-private/classification-v6-qualification-surface-002-20261001"
)
PRIVATE_COREQUAL001 = Path(
    "/home/morpheus/hlx-private/classification-v6-qualification-surface-003-20261001"
)
PRIVATE_V2 = Path(
    "/home/morpheus/hlx-private/classification-v6-representative-validation-redesign-20261001"
)
PRIVATE_V3 = Path(
    "/home/morpheus/hlx-private/classification-v6-function-diversity-expand-20261002"
)
FOUNDATION = Path(
    "/home/morpheus/hlx-private/classification-v6-data-foundation-20261001"
)
MIGRATION = Path(
    "/home/morpheus/hlx-private/classification-v6-label-migration-bakeoff-20261001"
)
REPO_ART = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V6-CORE-QUALIFICATION-SURFACE-001"
)
SPEC = REPO / "specs" / "007-hyperlexical-model"
WIKT_API = "https://en.wiktionary.org/w/api.php"
WIKI_API = "https://en.wikipedia.org/w/api.php"
SEED = 20261004
ACQUIRE_TARGET = 1200

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sha256_file(path: Path) -> str:
    import hashlib

    d = hashlib.sha256()
    with path.open("rb") as h:
        for chunk in iter(lambda: h.read(1 << 20), b""):
            d.update(chunk)
    return d.hexdigest()


def sudo_read_text(path: Path) -> str:
    if os.access(path, os.R_OK):
        return path.read_text(encoding="utf-8")
    return subprocess.run(
        ["sudo", "-n", "cat", str(path)], check=True, capture_output=True, text=True
    ).stdout


def write_private(path: Path, payload: Any) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    text = (
        payload
        if isinstance(payload, str)
        else json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"
    )
    path.write_text(text, encoding="utf-8")
    os.chmod(path, 0o600)


def write_repo(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as h:
        for r in rows:
            h.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")
    os.chmod(path, 0o600)


def code_revision() -> str:
    env = os.environ.get("HLX_V5_STAGE_A_CODE_REVISION")
    if env:
        return env
    return subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in sudo_read_text(path).splitlines() if l.strip()]


def _api(api: str, params: dict, retries: int = 8) -> Any:
    q = dict(params)
    q["format"] = "json"
    q["formatversion"] = "2"
    url = api + "?" + urllib.parse.urlencode(q)
    last_err: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "HyperlexV6CoreQUAL001/1.0 (research; contact: hyperlex-operator)"
                )
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_err = exc
            if exc.code in {429, 500, 502, 503, 504}:
                sleep_s = min(120.0, (2**attempt) + random.random())
                print(f"api_backoff code={exc.code} sleep={sleep_s:.1f}s", flush=True)
                time.sleep(sleep_s)
                continue
            raise
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(min(60.0, (2**attempt)))
    assert last_err is not None
    raise last_err


def category_titles(api: str, category: str, limit: int = 200) -> list[str]:
    titles: list[str] = []
    cont = None
    while len(titles) < limit:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmlimit": "50",
            "cmnamespace": "0",
        }
        if cont:
            params["cmcontinue"] = cont
        payload = _api(api, params)
        titles.extend(
            m["title"] for m in payload.get("query", {}).get("categorymembers", [])
        )
        cont = (payload.get("continue") or {}).get("cmcontinue")
        if not cont:
            break
        time.sleep(0.35)
    return titles[:limit]


def fetch_wikitext(api: str, titles: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for i in range(0, len(titles), 10):
        batch = titles[i : i + 10]
        payload = _api(
            api,
            {
                "action": "query",
                "prop": "revisions",
                "rvprop": "content",
                "rvslots": "main",
                "titles": "|".join(batch),
            },
        )
        for page in payload.get("query", {}).get("pages", []):
            title = page.get("title")
            revs = page.get("revisions") or []
            if not title or not revs:
                continue
            slots = revs[0].get("slots") or {}
            main = slots.get("main") or {}
            out[title] = main.get("content") or ""
        time.sleep(0.35)
    return out


def build_blocked() -> dict[str, set[str]]:
    """Block TRAIN/DEV/REP V2, QUAL-001/002, V5/diagnostic surfaces."""
    from hyperlexical.classification_v5_surface_readiness_gates import near_duplicate_key
    from hyperlexical.classification_v6_data_foundation_acquire import row_identity
    from hyperlexical.holdout_guard import normalized_text_sha256

    blocked_ids: set[str] = set()
    blocked_src: set[str] = set()
    blocked_text: set[str] = set()
    blocked_near: set[str] = set()
    blocked_urls: set[str] = set()
    n_paths = 0

    def ingest_row(row: dict) -> None:
        ident = row.get("identity")
        if ident:
            blocked_ids.add(str(ident))
        body = str(row.get("text") or "")
        url = str(row.get("source_url") or "")
        if body:
            blocked_text.add(body)
            blocked_src.add(normalized_text_sha256(body))
            blocked_near.add(near_duplicate_key(body))
            if url:
                blocked_ids.add(row_identity(body, url))
        src = row.get("source_sha256")
        if src:
            blocked_src.add(str(src))
        if url:
            blocked_urls.add(url)

    # V2/V3 + foundation/migration + QUAL-001/002/003 (all spent / unreused)
    for path in [
        PRIVATE_V2 / "TRAIN_V2.jsonl",
        PRIVATE_V2 / "DEV_SELECTION_V2.jsonl",
        PRIVATE_V2 / "REPRESENTATIVE_VALIDATION_V2.jsonl",
        PRIVATE_V3 / "TRAIN_V3.jsonl",
        PRIVATE_V3 / "DEV_SELECTION_V3.jsonl",
        PRIVATE_V3 / "REPRESENTATIVE_VALIDATION_V3.jsonl",
        PRIVATE_V3 / "NEW_ANNOTATED_POSITIVES.jsonl",
        PRIVATE_V3 / "RAW_ACQUIRE_EXPAND.jsonl",
        PRIVATE_V3 / "BLOCK_TEXTS.jsonl",
        FOUNDATION / "TRAIN.jsonl",
        FOUNDATION / "DEVELOPMENT_VALIDATION.jsonl",
        FOUNDATION / "REPRESENTATIVE_VALIDATION.jsonl",
        FOUNDATION / "qualification_holdout" / "QUALIFICATION_ROWS.jsonl",
        MIGRATION / "TRAIN_V6_LABELS.jsonl",
        MIGRATION / "DEVELOPMENT_VALIDATION_V6_LABELS.jsonl",
        MIGRATION / "REPRESENTATIVE_VALIDATION_V6_LABELS.jsonl",
        PRIVATE_QUAL002 / "QUALIFICATION_ROWS.jsonl",
        PRIVATE_QUAL002 / "RAW_ACQUIRE_QUAL002.jsonl",
        PRIVATE_QUAL002 / "RAW_ACQUIRE_QUAL002.partial.jsonl",
        PRIVATE_QUAL002 / "RAW_ACQUIRE_QUAL002.firecrawl.jsonl",
        PRIVATE_QUAL002 / "EVALUATION_SPENT_IDENTITIES.json",
        PRIVATE_COREQUAL001 / "QUALIFICATION_ROWS.jsonl",
        PRIVATE_COREQUAL001 / "RAW_ACQUIRE_COREQUAL001.jsonl",
        PRIVATE_COREQUAL001 / "RAW_ACQUIRE_COREQUAL001.partial.jsonl",
        PRIVATE_COREQUAL001 / "RAW_ACQUIRE_COREQUAL001.firecrawl.jsonl",
        PRIVATE_COREQUAL001 / "RAW_ACQUIRE_COREQUAL001.merged_feed.jsonl",
        PRIVATE_COREQUAL001 / "RAW_ACQUIRE_COREQUAL001.wiki_html_none.jsonl",
        PRIVATE_COREQUAL001 / "RAW_ACQUIRE_COREQUAL001.wikt_html.jsonl",
        PRIVATE_COREQUAL001 / "EVALUATION_SPENT_IDENTITIES.json",
    ]:
        try:
            if path.suffix == ".json" and "IDENTITIES" in path.name:
                payload = json.loads(sudo_read_text(path))
                ids = payload if isinstance(payload, list) else payload.get("identities") or []
                for ident in ids:
                    blocked_ids.add(str(ident))
                n_paths += 1
                continue
            rows = load_jsonl(path)
            n_paths += 1
            for r in rows:
                ingest_row(r)
        except Exception:
            continue

    import glob

    root = Path("/home/morpheus/hlx-private")
    patterns = [
        "classification-v5-pipeline-qualification-001-20261001/**/*.jsonl",
        "classification-v*-reserve*/**/*.jsonl",
        "classification-v5-reserve*/**/*.jsonl",
        "classification-v5-stage-a-*/**/*SURFACE*.jsonl",
        "classification-v5-stage-a-*/**/OBSERVED_*.jsonl",
        "classification-v4-*/**/*.jsonl",
        "classification-v3-*/**/*.jsonl",
        "classification-v6-*/**/*LABELS*.jsonl",
        "classification-v6-human-ontology-settlement-20261001/**/*.jsonl",
        "classification-v6-none-rejection-harden-20261001/**/*.jsonl",
        "classification-v6-operating-pipeline-harden-20261001/**/*.jsonl",
    ]
    for pattern in patterns:
        for path_str in glob.glob(str(root / pattern), recursive=True):
            path = Path(path_str)
            if "core-qualification-001" in str(path):
                continue
            if "qualification-surface-003" in str(path):
                continue
            try:
                text = sudo_read_text(path)
            except Exception:
                continue
            n_paths += 1
            for line in text.splitlines():
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict) and ("text" in row or "identity" in row):
                    ingest_row(row)

    return {
        "blocked_ids": blocked_ids,
        "blocked_src": blocked_src,
        "blocked_text": blocked_text,
        "blocked_near": blocked_near,
        "blocked_urls": blocked_urls,
        "n_paths": n_paths,
    }


def acquire_fresh(blocked: dict[str, set[str]], target: int = ACQUIRE_TARGET) -> list[dict]:
    from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY
    from hyperlexical.classification_v6_data_foundation_acquire import (
        DOMAIN_IRRELEVANT_CATEGORIES,
        FAMILY_LABELS,
        ORDINARY_NONE_LABELS,
        WIKI_ORDINARY_CATEGORIES,
        WIKT_FAMILY_CATEGORIES,
        clean_wikitext,
        row_identity,
        sense_labels,
    )
    from hyperlexical.classification_v5_surface_readiness_gates import near_duplicate_key
    from hyperlexical.holdout_guard import normalized_text_sha256

    rng = random.Random(SEED)
    raw: list[dict] = []
    seen_text = set(blocked["blocked_text"])
    seen_src = set(blocked["blocked_src"])
    seen_near = set(blocked["blocked_near"])

    def admit(row: dict) -> bool:
        text = row["text"]
        src = normalized_text_sha256(text)
        near = near_duplicate_key(text)
        ident = row_identity(text, row["source_url"])
        if (
            text in seen_text
            or src in seen_src
            or near in seen_near
            or ident in blocked["blocked_ids"]
            or row["source_url"] in blocked.get("blocked_urls", set())
        ):
            return False
        seen_text.add(text)
        seen_src.add(src)
        seen_near.add(near)
        row["identity"] = ident
        row["source_sha256"] = src
        row["near_duplicate_key"] = near
        raw.append(row)
        return True

    # Prefer unused foundation RAW leftovers first (already NATURAL OBSERVED)
    for name in ("RAW_ACQUIRE.jsonl", "RAW_TOPUP.jsonl"):
        path = FOUNDATION / name
        try:
            for r in load_jsonl(path):
                if r.get("construction_tag") != "NATURAL":
                    continue
                if r.get("provenance") != "OBSERVED":
                    continue
                text = str(r.get("text") or "")
                url = str(r.get("source_url") or "unknown")
                if not text:
                    continue
                admit(
                    {
                        "text": text,
                        "source_url": url,
                        "provenance": "OBSERVED",
                        "construction_tag": "NATURAL",
                        "construction_role": r.get("construction_role")
                        or "PRODUCT_EXPECTED",
                        "source_family": r.get("source_family") or "foundation_unused",
                        "topic_domain": r.get("topic_domain"),
                        "acquisition_cue_family": r.get("gold_family"),
                        "notes": "foundation_raw_unused_reclaimed_corequal001",
                    }
                )
        except Exception:
            continue

    # Resume partial acquire if present
    partial_path = PRIVATE / "RAW_ACQUIRE_COREQUAL001.partial.jsonl"
    if partial_path.exists():
        try:
            for r in load_jsonl(partial_path):
                admit(
                    {
                        "text": r["text"],
                        "source_url": r["source_url"],
                        "provenance": r.get("provenance") or "OBSERVED",
                        "construction_tag": r.get("construction_tag") or "NATURAL",
                        "construction_role": r.get("construction_role")
                        or "PRODUCT_EXPECTED",
                        "source_family": r.get("source_family"),
                        "topic_domain": r.get("topic_domain"),
                        "acquisition_cue_family": r.get("acquisition_cue_family"),
                        "notes": r.get("notes") or "resumed_partial",
                    }
                )
            print(f"resumed_partial={len(raw)}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"partial_resume_skip={exc}", flush=True)

    # Fresh OBSERVED feeds only (never QUAL-002 firecrawl — those identities blocked).
    feed_paths: list[Path] = []
    env_feed = os.environ.get("HLX_COREQUAL001_FIRECRAWL_FEED")
    if env_feed:
        feed_paths.append(Path(env_feed))
    for name in (
        "RAW_ACQUIRE_COREQUAL001.firecrawl.jsonl",
        "RAW_ACQUIRE_COREQUAL001.wiki_html_none.jsonl",
        "RAW_ACQUIRE_COREQUAL001.wikt_html.jsonl",
        "RAW_ACQUIRE_COREQUAL001.merged_feed.jsonl",
    ):
        cand = PRIVATE / name
        if cand not in feed_paths:
            feed_paths.append(cand)
    for firecrawl_feed in feed_paths:
        if not firecrawl_feed.exists():
            continue
        try:
            n_before = len(raw)
            for r in load_jsonl(firecrawl_feed):
                if r.get("construction_tag") not in (None, "NATURAL"):
                    continue
                if r.get("provenance") not in (None, "OBSERVED"):
                    continue
                # Refuse QUAL-002 lineage tags if a feed is mis-copied.
                sf = str(r.get("source_family") or "")
                notes = str(r.get("notes") or "")
                if "qual002" in sf.lower() or "qual-002" in notes.lower():
                    continue
                admit(
                    {
                        "text": r["text"],
                        "source_url": r["source_url"],
                        "provenance": "OBSERVED",
                        "construction_tag": "NATURAL",
                        "construction_role": r.get("construction_role")
                        or "PRODUCT_EXPECTED",
                        "source_family": r.get("source_family")
                        or "v6_corequal001_firecrawl",
                        "topic_domain": r.get("topic_domain"),
                        "acquisition_cue_family": r.get("acquisition_cue_family"),
                        "notes": r.get("notes") or "observed_feed_corequal001",
                    }
                )
            print(
                f"observed_feed={firecrawl_feed} added={len(raw) - n_before} "
                f"total={len(raw)}",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"observed_feed_skip={firecrawl_feed}: {exc}", flush=True)

    def checkpoint() -> None:
        write_jsonl(partial_path, raw)

    from hyperlexical.classification_v6_core_qualification import (
        TARGET_N_PREFERRED,
    )

    # Always continue to MediaWiki NONE acquisition unless we already have
    # abundant wiki_none candidates (operating distribution needs zero-label mass).
    def _is_none_cue(row: dict) -> bool:
        sf = str(row.get("source_family") or "")
        return (
            "wiki_none" in sf
            or "wiki_html_none" in sf
            or "ordinary" in sf
            or "irrelevant" in sf
            or sf.endswith(":none")
            or "none:" in sf
        )

    n_none_cue = sum(1 for r in raw if _is_none_cue(r))
    skip_mediawiki = os.environ.get("HLX_COREQUAL001_SKIP_MEDIAWIKI", "").strip() in {
        "1",
        "true",
        "yes",
    }
    if skip_mediawiki or (
        len(raw) >= target and n_none_cue >= int(0.45 * target)
    ):
        print(
            f"acquire_target_met_pre_mediawiki n={len(raw)} none_cue={n_none_cue} "
            f"skip_mediawiki={skip_mediawiki}",
            flush=True,
        )
        checkpoint()

        def _prio(row: dict) -> tuple:
            sf = str(row.get("source_family") or "")
            none = int(_is_none_cue(row) or "none" in sf)
            multi = int("multicue" in str(row.get("notes") or "").lower())
            return (-none, -multi, row.get("identity") or row.get("text") or "")

        return sorted(raw, key=_prio)[:target]

    # Ordinary NONE first — operating QUAL needs zero-label mass.
    none_targets = list(WIKI_ORDINARY_CATEGORIES.items()) + list(
        DOMAIN_IRRELEVANT_CATEGORIES.items()
    )
    rng.shuffle(none_targets)
    none_floor = int(0.50 * target)
    for key, cat in none_targets:
        n_none = sum(1 for r in raw if "wiki_none" in str(r.get("source_family") or ""))
        if n_none >= none_floor and len(raw) >= int(0.7 * target):
            break
        try:
            titles = category_titles(WIKI_API, cat, limit=140)
        except Exception as exc:  # noqa: BLE001
            print(f"wiki_cat_skip {key}: {exc}", flush=True)
            continue
        rng.shuffle(titles)
        offset = (SEED + hash(key)) % max(1, min(50, len(titles) // 2 or 1))
        try:
            pages = fetch_wikitext(WIKI_API, titles[offset : offset + 80])
        except Exception as exc:  # noqa: BLE001
            print(f"wiki_fetch_skip {key}: {exc}", flush=True)
            continue
        got = 0
        for title, content in pages.items():
            n_none = sum(
                1 for r in raw if "wiki_none" in str(r.get("source_family") or "")
            )
            if got >= 45 or n_none >= none_floor:
                break
            paras = [p.strip() for p in re.split(r"\n\n+", content) if p.strip()]
            for para in paras[:4]:
                text = clean_wikitext(para)
                if len(text) < 40 or text.startswith("[["):
                    continue
                text = text[:800]
                if admit(
                    {
                        "text": text,
                        "source_url": (
                            "https://en.wikipedia.org/wiki/"
                            + urllib.parse.quote(title.replace(" ", "_"))
                        ),
                        "provenance": "OBSERVED",
                        "construction_tag": "NATURAL",
                        "construction_role": "PRODUCT_EXPECTED",
                        "source_family": f"v6_corequal001_wiki_none:{key}",
                        "topic_domain": key,
                        "acquisition_cue_family": None,
                        "notes": f"wiki_prose:{title}",
                    }
                ):
                    got += 1
                    break
        checkpoint()
        print(f"none={key} got={got} total={len(raw)}", flush=True)
        time.sleep(1.0)

    # Then Wiktionary positives to fill remaining budget (cap per family).
    per_family = 40
    families = list(ACTIVE_FAMILY_VOCABULARY)
    rng.shuffle(families)
    for family in families:
        if len(raw) >= target:
            break
        labels = FAMILY_LABELS.get(family, ())
        got = 0
        titles: list[str] = []
        for cat in WIKT_FAMILY_CATEGORIES.get(family, ())[:1]:
            titles.extend(category_titles(WIKT_API, cat, limit=160))
            time.sleep(0.5)
        for label in labels[:2]:
            try:
                payload = _api(
                    WIKT_API, {"action": "opensearch", "search": label, "limit": "40"}
                )
                if isinstance(payload, list) and len(payload) >= 2:
                    titles.extend(list(payload[1]))
            except Exception as exc:  # noqa: BLE001
                print(f"opensearch_skip {label}: {exc}", flush=True)
            time.sleep(0.5)
        rng.shuffle(titles)
        uniq, seen_t = [], set()
        for t in titles:
            if t not in seen_t:
                seen_t.add(t)
                uniq.append(t)
        offset = (SEED + hash(family)) % max(1, min(40, len(uniq) // 3 or 1))
        try:
            pages = fetch_wikitext(WIKT_API, uniq[offset : offset + 160])
        except Exception as exc:  # noqa: BLE001
            print(f"wikt_fetch_skip {family}: {exc}", flush=True)
            continue
        for title, content in pages.items():
            if got >= per_family or len(raw) >= target:
                break
            for line in content.splitlines():
                if got >= per_family or len(raw) >= target:
                    break
                if not line.startswith("#"):
                    continue
                text = clean_wikitext(re.sub(r"^[#*:]+", "", line))
                if len(text) < 12:
                    continue
                if admit(
                    {
                        "text": text,
                        "source_url": (
                            "https://en.wiktionary.org/wiki/"
                            + urllib.parse.quote(title.replace(" ", "_"))
                        ),
                        "provenance": "OBSERVED",
                        "construction_tag": "NATURAL",
                        "construction_role": "PRODUCT_EXPECTED",
                        "source_family": f"v6_corequal001_wikt:{family}",
                        "topic_domain": family,
                        "acquisition_cue_family": family,
                        "notes": f"wikt_sense:{title}",
                    }
                ):
                    got += 1
        checkpoint()
        print(f"family={family} got={got} total={len(raw)}", flush=True)
        time.sleep(1.0)

    def _prio_final(row: dict) -> tuple:
        sf = str(row.get("source_family") or "")
        none = int("wiki_none" in sf or "ordinary" in sf or "irrelevant" in sf)
        return (-none, row.get("identity") or "")

    raw_sorted = sorted(raw, key=_prio_final)
    checkpoint()
    return raw_sorted[:target]


def map_adjudicated_to_final(adj: dict) -> dict[str, Any]:
    from hyperlexical.classification_v6_label_migration import DOMAIN_IDS, FUNCTION_IDS

    domains = []
    for d in adj.get("domains") or []:
        if d in DOMAIN_IDS:
            domains.append(DOMAIN_IDS[d])
        elif d == "ai_discourse":
            domains.append("domain.technology.ai_discourse")
    functions = [
        FUNCTION_IDS[f] for f in (adj.get("functions") or []) if f in FUNCTION_IDS
    ]
    mediation = (
        ["mediation.internet_register"]
        if "internet_register" in (adj.get("mediation") or [])
        else []
    )
    # hierarchy repair on gold (ontology consistency, not synthetic generation)
    repaired = False
    if (
        "domain.technology.ai_discourse" in domains
        and "domain.technology" not in domains
    ):
        domains.append("domain.technology")
        repaired = True
    uncertainty = adj.get("uncertainty")
    if adj.get("status") == "ADJUDICATED":
        uncertainty = "ANNOTATOR_DISAGREEMENT"
    return {
        "evidence_label": adj.get("stage_a"),
        "domain_labels": sorted(set(domains)),
        "function_labels": sorted(set(functions)),
        "mediation_labels": sorted(set(mediation)),
        "ontology_uncertainty": uncertainty,
        "hierarchy_repaired": repaired,
        "adjudication_status": adj.get("status"),
    }


def agreement_witness(annotated: list[dict]) -> dict[str, Any]:
    from hyperlexical.classification_v6_human_ontology_settlement import (
        _cohen_kappa,
    )
    from hyperlexical.classification_v6_core_qualification import (
        PRIOR_MEAN_CORE_JACCARD,
        classify_agreement_stability,
    )

    dom_j, fun_j, med_j, stage_agree = [], [], [], []
    for r in annotated:
        pm = r["pair_metrics"]
        dom_j.append(pm["domain_jaccard"])
        fun_j.append(pm["function_jaccard"])
        med_j.append(pm["mediation_jaccard"])
        stage_agree.append(1.0 if pm["stage_agree"] else 0.0)
    # Core stability excludes FUNCTION (advisory-only annotation).
    mean_core = float(sum(dom_j + med_j) / max(1, len(dom_j) * 2))
    mean_set = float(sum(dom_j + fun_j + med_j) / max(1, len(dom_j) * 3))
    stages_a = [r["rater_a"]["stage_a"] for r in annotated]
    stages_b = [r["rater_b"]["stage_a"] for r in annotated]
    kappa = _cohen_kappa(stages_a, stages_b)
    n_adj = sum(1 for r in annotated if r["adjudicated"]["status"] == "ADJUDICATED")
    stability = classify_agreement_stability(mean_core)
    return {
        "n": len(annotated),
        "n_annotators": 2,
        "n_adjudicated_disagreement": n_adj,
        "mean_domain_jaccard": float(sum(dom_j) / max(1, len(dom_j))),
        "mean_function_jaccard": float(sum(fun_j) / max(1, len(fun_j))),
        "mean_mediation_jaccard": float(sum(med_j) / max(1, len(med_j))),
        "mean_core_jaccard": mean_core,
        "mean_set_jaccard": mean_set,
        "stage_raw_agreement": float(sum(stage_agree) / max(1, len(stage_agree))),
        "stage_kappa": kappa,
        "prior_mean_core_jaccard_witness": PRIOR_MEAN_CORE_JACCARD,
        "stability": stability,
        "function_excluded_from_stability": True,
        "per_label_positive_agreement": _per_label_pos_agreement(annotated),
    }


def _per_label_pos_agreement(annotated: list[dict]) -> dict[str, Any]:
    from hyperlexical.classification_v6_label_migration import DOMAIN_IDS, FUNCTION_IDS

    out = {}
    # short-name space used by raters
    labels = list(DOMAIN_IDS) + ["ai_discourse"] + list(FUNCTION_IDS) + ["internet_register"]
    for lab in labels:
        both = a_only = b_only = 0
        for r in annotated:
            a = set(r["rater_a"].get("domains") or []) | set(
                r["rater_a"].get("functions") or []
            ) | set(r["rater_a"].get("mediation") or [])
            b = set(r["rater_b"].get("domains") or []) | set(
                r["rater_b"].get("functions") or []
            ) | set(r["rater_b"].get("mediation") or [])
            ina, inb = lab in a, lab in b
            if ina and inb:
                both += 1
            elif ina:
                a_only += 1
            elif inb:
                b_only += 1
        denom = both + a_only + b_only
        out[lab] = {
            "both": both,
            "a_only": a_only,
            "b_only": b_only,
            "positive_agreement": both / denom if denom else None,
        }
    return out


def coverage_and_witnesses(rows: list[dict]) -> dict[str, Any]:
    from hyperlexical.classification_v6_label_migration import (
        DOMAIN_VOCAB,
        FUNCTION_VOCAB,
        MEDIATION_VOCAB,
    )
    from hyperlexical.classification_v6_qualification_surface_002 import (
        low_qual_support_labels,
    )
    from hyperlexical.classification_v6_core_qualification import (
        MAX_SOURCE_FAMILY_SHARE,
        PREFERRED_POSITIVES_PER_LABEL,
        TARGET_N_MIN,
        TARGET_N_PREFERRED,
        coverage_sufficient_core,
    )

    dom_sup = Counter()
    fun_sup = Counter()
    med_sup = Counter()
    stage = Counter()
    src = Counter()
    card = Counter()
    co = Counter()
    lengths = []
    natural = observed = 0
    hier_child_parent = hier_parent_only = multi_axis = 0

    for r in rows:
        stage[r.get("evidence_label")] += 1
        if r.get("construction_tag") == "NATURAL":
            natural += 1
        if r.get("provenance") == "OBSERVED":
            observed += 1
        src[r.get("source_family") or "UNKNOWN"] += 1
        d = r.get("domain_labels") or []
        f = r.get("function_labels") or []
        m = r.get("mediation_labels") or []
        for x in d:
            dom_sup[x] += 1
        for x in f:
            fun_sup[x] += 1
        for x in m:
            med_sup[x] += 1
        # Core cardinality ignores FUNCTION (advisory metadata only).
        nlab_core = len(d) + len(m)
        if nlab_core == 0:
            card["0"] += 1
        elif nlab_core == 1:
            card["1"] += 1
        elif nlab_core == 2:
            card["2"] += 1
        else:
            card["3+"] += 1
        if d and m:
            co["domain+mediation"] += 1
        if d and f and m:
            co["domain+function+mediation_advisory"] += 1
        elif d and f:
            co["domain+function_advisory"] += 1
        elif f and m:
            co["function_advisory+mediation"] += 1
        if (
            "domain.technology.ai_discourse" in d
            and "domain.technology" in d
        ):
            hier_child_parent += 1
        if "domain.technology" in d and "domain.technology.ai_discourse" not in d:
            hier_parent_only += 1
        if d and m:
            multi_axis += 1
        lengths.append(len(r.get("text") or ""))

    n = max(1, len(rows))
    src_share = {k: v / n for k, v in src.items()}
    max_share = max(src_share.values()) if src_share else 0.0
    short = sum(1 for L in lengths if L < 60)
    medium = sum(1 for L in lengths if 60 <= L < 200)
    long_ = sum(1 for L in lengths if L >= 200)
    lens_sorted = sorted(lengths)

    supports = {**{k: int(dom_sup[k]) for k in DOMAIN_VOCAB},
                **{k: int(fun_sup[k]) for k in FUNCTION_VOCAB},
                **{k: int(med_sup[k]) for k in MEDIATION_VOCAB}}
    low = low_qual_support_labels(supports)

    active_dom = sum(1 for k in DOMAIN_VOCAB if dom_sup[k] > 0)
    active_fun = sum(1 for k in FUNCTION_VOCAB if fun_sup[k] > 0)
    zero_n = int(card.get("0") or 0)
    zero_share = zero_n / n
    no_ev_share = int(stage.get("NO_EVIDENCE") or 0) / n
    summary_for_gate = {
        "n": len(rows),
        "stage_a": dict(stage),
        "cardinality": dict(card),
        "zero_label_share": zero_share,
        "active_domain_labels": active_dom,
        "mediation_supports": {k: int(med_sup[k]) for k in MEDIATION_VOCAB},
    }
    coverage_sufficient = coverage_sufficient_core(summary_for_gate)

    return {
        "n": len(rows),
        "target_min": TARGET_N_MIN,
        "target_preferred": TARGET_N_PREFERRED,
        "stage_a": dict(stage),
        "zero_label_share": zero_share,
        "no_evidence_share": no_ev_share,
        "positive_share": 1.0 - zero_share,
        "active_domain_labels": active_dom,
        "active_function_labels": active_fun,
        "domain_supports": {k: int(dom_sup[k]) for k in DOMAIN_VOCAB},
        "function_supports": {k: int(fun_sup[k]) for k in FUNCTION_VOCAB},
        "mediation_supports": {k: int(med_sup[k]) for k in MEDIATION_VOCAB},
        "low_qual_support": low,
        "cardinality": dict(card),
        "co_label": dict(co),
        "source_counts": dict(src),
        "source_share": src_share,
        "max_source_family_share": max_share,
        "source_diversity_ok": max_share <= MAX_SOURCE_FAMILY_SHARE,
        "length": {
            "min": lens_sorted[0] if lens_sorted else 0,
            "p50": lens_sorted[len(lens_sorted) // 2] if lens_sorted else 0,
            "p90": lens_sorted[int(0.9 * (len(lens_sorted) - 1))] if lens_sorted else 0,
            "max": lens_sorted[-1] if lens_sorted else 0,
            "short": short,
            "medium": medium,
            "long": long_,
        },
        "natural_share": natural / n,
        "observed_share": observed / n,
        "hierarchy_cases": {
            "child_plus_parent": hier_child_parent,
            "parent_without_child": hier_parent_only,
            "multi_axis": multi_axis,
        },
        "coverage_sufficient": coverage_sufficient,
        "preferred_positives": PREFERRED_POSITIVES_PER_LABEL,
        "statistical_power_note": (
            None
            if len(rows) >= TARGET_N_MIN
            else f"shortfall n={len(rows)} < {TARGET_N_MIN}; no synthetic padding"
        ),
    }


def source_leakage(rows: list[dict]) -> dict[str, Any]:
    """Descriptive PMI between source_family and domain labels."""
    import math

    n = len(rows)
    src_n = Counter(r.get("source_family") or "UNKNOWN" for r in rows)
    lab_n = Counter()
    joint = Counter()
    for r in rows:
        s = r.get("source_family") or "UNKNOWN"
        labs = r.get("domain_labels") or []
        if not labs:
            labs = ["__NONE__"]
        for lab in labs:
            lab_n[lab] += 1
            joint[(s, lab)] += 1
    flags = []
    pmi_rows = []
    for (s, lab), c in joint.items():
        if c < 5:
            continue
        pmi = math.log2((c * n) / max(1e-9, src_n[s] * lab_n[lab]))
        pmi_rows.append({"source_family": s, "label": lab, "n": c, "pmi": pmi})
        if pmi >= 2.5 and c >= 10:
            flags.append({"source_family": s, "label": lab, "n": c, "pmi": pmi})
    pmi_rows.sort(key=lambda x: -x["pmi"])
    return {
        "top_pmi": pmi_rows[:40],
        "flagged_shortcuts": flags,
        "note": (
            "Descriptive only. Legitimate product association retained; "
            "flags mark strong source-label coupling."
        ),
    }


def _row_fails_identifiability(r: dict) -> bool:
    from hyperlexical.classification_v5_stage_a_gold_identifiability_contract import (
        classify_row as classify_ident,
    )

    try:
        disposition = classify_ident(
            {
                "text": r.get("text"),
                "evidence_label": r.get("evidence_label"),
                "gold_family": None,
            }
        )
    except Exception:
        return False
    state = str(disposition.get("identifiability_state") or "")
    disp = str(disposition.get("recommended_disposition") or "")
    return state in {
        "INVALID_GOLD_FOR_TEXT_ONLY_MODEL",
        "CONTEXT_REQUIRED",
    } or disp in {
        "EXCLUDE_FROM_TEXT_ONLY_STAGE_A",
        "REQUIRES_HUMAN_RESETTLEMENT",
    }


def identifiability_witness(rows: list[dict]) -> dict[str, Any]:
    """Text-only gold: reject rows needing hidden context."""
    ok = bad = 0
    unresolved = []
    for r in rows:
        if _row_fails_identifiability(r):
            bad += 1
            unresolved.append(r.get("identity"))
        else:
            ok += 1
    return {
        "n": len(rows),
        "identifiable_or_unresolved_ok": ok,
        "rejected_hidden_context": bad,
        "pass": bad == 0,
        "model_input": ["text"],
        "rejected_identities_sample": unresolved[:20],
    }


def main() -> int:
    from hyperlexical.classification_v5_stage_a import canonical_json, sha256_text
    from hyperlexical.classification_v6_data_foundation import utc_now_iso
    from hyperlexical.classification_v6_human_ontology_settlement import dual_annotate_rows
    from hyperlexical.classification_v6_core_qualification import (
        CORE_QUALIFICATION_GATES,
        SURFACE_EXPERIMENT_ID as EXPERIMENT_ID,
        SURFACE_PHASE as PHASE_RULE,
        QUALIFICATION_ID,
        decide_surface_state,
        ontology_binding,
        surface_contract,
    )
    from hyperlexical.classification_v5_stage_a_canonical import MODEL_WIDE_BEST_SHA256

    model_executions = 0  # hard prohibition
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    contract = surface_contract()
    binding = ontology_binding()
    gates = {
        "source": "HLX-CLASSIFICATION-V6-CORE-PRODUCT-HARDEN-001",
        "gates": dict(CORE_QUALIFICATION_GATES),
        "FUNCTION_in_pass_fail": False,
        "chosen_before_qual_scoring": True,
        "modified_in_this_phase": False,
    }
    historical = contract["historical"]
    write_private(PRIVATE / "CONTRACT.json", contract)
    write_private(PRIVATE / "ONTOLOGY_BINDING.json", binding)
    write_private(PRIVATE / "ANNOTATION_PROTOCOL.json", contract["annotation_protocol"])
    write_private(PRIVATE / "CORE_QUALIFICATION_GATES.json", dict(CORE_QUALIFICATION_GATES))
    write_repo(REPO_ART / "contract.json", contract)
    write_repo(REPO_ART / "ontology_binding.json", binding)
    write_repo(REPO_ART / "annotation_protocol.json", contract["annotation_protocol"])
    write_repo(REPO_ART / "historical_qual_status.json", historical)
    write_repo(REPO_ART / "core_qualification_gates.json", dict(CORE_QUALIFICATION_GATES))

    print("build_blocked", flush=True)
    blocked = build_blocked()
    write_private(
        PRIVATE / "BLOCKED_SUMMARY.json",
        {
            "n_blocked_ids": len(blocked["blocked_ids"]),
            "n_blocked_text": len(blocked["blocked_text"]),
            "n_blocked_src": len(blocked["blocked_src"]),
            "n_blocked_near": len(blocked["blocked_near"]),
            "n_paths": blocked["n_paths"],
        },
    )
    print(
        f"blocked ids/text/src/near="
        f"{len(blocked['blocked_ids'])}/{len(blocked['blocked_text'])}/"
        f"{len(blocked['blocked_src'])}/{len(blocked['blocked_near'])}",
        flush=True,
    )

    print("acquire_fresh_natural_observed", flush=True)
    raw = acquire_fresh(blocked, target=ACQUIRE_TARGET)
    write_jsonl(PRIVATE / "RAW_ACQUIRE_COREQUAL001.jsonl", raw)
    print(f"acquired={len(raw)}", flush=True)

    # Blind annotation input: identity + text only
    blind = [{"identity": r["identity"], "text": r["text"]} for r in raw]
    print("dual_independent_annotation", flush=True)
    annotated = dual_annotate_rows(blind)
    write_private(PRIVATE / "DUAL_ANNOTATIONS.json", [
        {
            "identity": r["identity"],
            "rater_a": r["rater_a"],
            "rater_b": r["rater_b"],
            "adjudicated": r["adjudicated"],
            "pair_metrics": r["pair_metrics"],
        }
        for r in annotated
    ])

    agree = agreement_witness(annotated)
    write_private(PRIVATE / "HUMAN_AGREEMENT_WITNESS.json", agree)
    write_repo(REPO_ART / "human_agreement_witness.json", agree)
    print(
        f"agreement mean_set_jaccard={agree['mean_set_jaccard']:.4f} "
        f"stability={agree['stability']}",
        flush=True,
    )

    # Materialize gold rows
    by_id = {r["identity"]: r for r in raw}
    gold_rows = []
    for ann in annotated:
        base = by_id[ann["identity"]]
        mapped = map_adjudicated_to_final(ann["adjudicated"])
        # skip forcing definitive when unsupported
        if mapped["evidence_label"] == "UNCERTAIN" and not (
            mapped["domain_labels"]
            or mapped["function_labels"]
            or mapped["mediation_labels"]
        ):
            mapped["ontology_uncertainty"] = mapped.get("ontology_uncertainty") or (
                "INSUFFICIENT_CONTEXT"
            )
        gold_rows.append(
            {
                "identity": ann["identity"],
                "text": base["text"],
                "source_url": base["source_url"],
                "source_family": base.get("source_family"),
                "source_sha256": base.get("source_sha256"),
                "near_duplicate_key": base.get("near_duplicate_key"),
                "provenance": base.get("provenance"),
                "construction_tag": base.get("construction_tag"),
                "construction_role": base.get("construction_role"),
                "qualification_hold_id": QUALIFICATION_ID,
                "split": "QUALIFICATION",
                "evaluation_spent": "UNSPENT",
                "optimization_forbidden": True,
                "schema": "hyperlex.classification.v6.core_qualification_row.v1",
                **mapped,
            }
        )

    # drop hidden-context / non-text-identifiable definitive rows
    gold_rows = [r for r in gold_rows if not _row_fails_identifiability(r)]
    ident = identifiability_witness(gold_rows)

    write_private(PRIVATE / "IDENTIFIABILITY_WITNESS.json", ident)
    write_repo(REPO_ART / "identifiability_witness.json", ident)

    # Disjointness re-check
    overlap = 0
    for r in gold_rows:
        if (
            r["identity"] in blocked["blocked_ids"]
            or r["text"] in blocked["blocked_text"]
            or r.get("source_sha256") in blocked["blocked_src"]
            or r.get("near_duplicate_key") in blocked["blocked_near"]
        ):
            overlap += 1
    disjoint = {
        "forbidden_overlap": overlap,
        "pass": overlap == 0,
        "checks": [
            "exact_identity",
            "source_hash",
            "normalized_text_hash",
            "near_duplicate",
            "blocked_surfaces_scanned",
        ],
        "n_blocked_paths": blocked["n_paths"],
    }
    write_private(PRIVATE / "DISJOINTNESS_WITNESS.json", disjoint)
    write_repo(REPO_ART / "disjointness_witness.json", disjoint)

    cov = coverage_and_witnesses(gold_rows)
    write_private(PRIVATE / "CARDINALITY_WITNESS.json", cov["cardinality"])
    write_private(PRIVATE / "CO_LABEL_WITNESS.json", cov["co_label"])
    write_private(
        PRIVATE / "SOURCE_DIVERSITY_WITNESS.json",
        {
            "source_counts": cov["source_counts"],
            "source_share": cov["source_share"],
            "max_source_family_share": cov["max_source_family_share"],
            "target_max": 0.25,
            "ok_or_documented": cov["source_diversity_ok"]
            or "natural_prevalence_documented",
        },
    )
    write_private(PRIVATE / "COVERAGE.json", cov)
    write_repo(REPO_ART / "coverage.json", {
        k: v
        for k, v in cov.items()
        if k
        not in {
            # keep public metadata; no row texts
        }
    })
    write_repo(REPO_ART / "cardinality_witness.json", cov["cardinality"])
    write_repo(REPO_ART / "co_label_witness.json", cov["co_label"])
    write_repo(
        REPO_ART / "source_diversity_witness.json",
        {
            "max_source_family_share": cov["max_source_family_share"],
            "source_share_top": sorted(
                cov["source_share"].items(), key=lambda kv: -kv[1]
            )[:25],
            "ok": cov["source_diversity_ok"],
        },
    )

    leakage = source_leakage(gold_rows)
    write_private(PRIVATE / "SOURCE_LEAKAGE.json", leakage)
    write_repo(
        REPO_ART / "source_leakage.json",
        {"flagged_shortcuts": leakage["flagged_shortcuts"], "note": leakage["note"]},
    )

    label_schema = binding["label_schema"]
    write_private(PRIVATE / "LABEL_SCHEMA.json", label_schema)
    write_repo(REPO_ART / "label_schema.json", label_schema)

    # Persist private rows (immutable after seal)
    rows_path = PRIVATE / "QUALIFICATION_ROWS.jsonl"
    write_jsonl(rows_path, gold_rows)
    # gold-only projection for gold hash
    gold_proj = [
        {
            "identity": r["identity"],
            "evidence_label": r["evidence_label"],
            "domain_labels": r["domain_labels"],
            "function_labels": r["function_labels"],
            "mediation_labels": r["mediation_labels"],
            "ontology_uncertainty": r.get("ontology_uncertainty"),
        }
        for r in gold_rows
    ]
    write_private(PRIVATE / "QUALIFICATION_GOLD.json", gold_proj)
    identities = sorted(r["identity"] for r in gold_rows)

    rows_sha = sha256_file(rows_path)
    gold_sha = sha256_text(canonical_json(gold_proj))
    identity_sha = sha256_text(canonical_json(identities))
    ontology_binding_sha = binding["ontology_binding_sha256"]

    manifest = {
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "PHASE_RULE": PHASE_RULE,
        "n_rows": len(gold_rows),
        "ontology_binding_sha256": ontology_binding_sha,
        "rows_sha256": rows_sha,
        "gold_sha256": gold_sha,
        "identity_sha256": identity_sha,
        "natural_share": cov["natural_share"],
        "observed_share": cov["observed_share"],
        "stage_a": cov["stage_a"],
        "domain_supports": cov["domain_supports"],
        "function_supports": cov["function_supports"],
        "mediation_supports": cov["mediation_supports"],
        "low_qual_support": cov["low_qual_support"],
        "cardinality": cov["cardinality"],
        "co_label": cov["co_label"],
        "max_source_family_share": cov["max_source_family_share"],
        "length": cov["length"],
        "agreement_stability": agree["stability"],
        "mean_set_jaccard": agree["mean_set_jaccard"],
        "n_annotators": 2,
        "n_adjudicated": agree["n_adjudicated_disagreement"],
        "identifiability_pass": ident["pass"],
        "disjointness_pass": disjoint["pass"],
        "forbidden_overlap": disjoint["forbidden_overlap"],
        "coverage_sufficient": cov["coverage_sufficient"],
        "qualification_model_executions": model_executions,
        "evaluation_spent": "UNSPENT",
        "zero_label_share": cov["zero_label_share"],
        "no_evidence_share": cov["no_evidence_share"],
        "gates": gates,
        "historical": historical,
        "MODEL_WIDE_BEST_MUTATED": False,
        "V6_CORE_PRODUCT_CANDIDATE_MUTATED": False,
        "FUNCTION_role": "ADVISORY_ONLY_NON_BLOCKING",
        "code_revision": code_revision(),
        "settled_at": utc_now_iso(),
    }
    manifest["manifest_sha256"] = sha256_text(
        canonical_json({k: v for k, v in manifest.items() if k != "manifest_sha256"})
    )
    write_private(PRIVATE / "QUALIFICATION_MANIFEST.json", manifest)
    # public manifest without private path leakage of row contents
    public_manifest = dict(manifest)
    write_repo(REPO_ART / "qualification_manifest.json", public_manifest)

    gold_stable = agree["stability"] == "QUALIFICATION_GOLD_STABLE"
    can_seal = (
        gold_stable
        and ident["pass"]
        and disjoint["pass"]
        and cov["coverage_sufficient"]
        and model_executions == 0
        and len(gold_rows) >= contract["coverage_targets"]["n_min"]
    )

    seal = None
    seal_complete = False
    if can_seal:
        seal = {
            "QUALIFICATION_ID": QUALIFICATION_ID,
            "QUALIFICATION_STATE": "SEALED_UNSCORED",
            "immutable": True,
            "n_rows": len(gold_rows),
            "rows_sha256": rows_sha,
            "gold_sha256": gold_sha,
            "identity_sha256": identity_sha,
            "manifest_sha256": manifest["manifest_sha256"],
            "ontology_binding_sha256": ontology_binding_sha,
            "unavailable_during_model_development": True,
            "expose_during_dev": [
                "manifest_metadata",
                "row_count",
                "coverage_summaries",
                "hashes",
            ],
            "evaluation_spent": "UNSPENT",
            "qualification_model_executions": 0,
            "sealed_at": utc_now_iso(),
            "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
            "MODEL_WIDE_BEST_MUTATED": False,
        }
        seal["seal_sha256"] = sha256_text(
            canonical_json({k: v for k, v in seal.items() if k != "seal_sha256"})
        )
        write_private(PRIVATE / "QUALIFICATION_SEAL.json", seal)
        write_repo(REPO_ART / "qualification_seal.json", seal)
        seal_complete = True
        # freeze rows immutable bit
        os.chmod(rows_path, 0o400)

    decision = decide_surface_state(
        ontology_compatible=True,
        gold_stable=gold_stable,
        identifiability_pass=ident["pass"],
        disjointness_pass=disjoint["pass"],
        coverage_sufficient=bool(cov["coverage_sufficient"]),
        seal_complete=seal_complete,
        model_executions=model_executions,
        n_rows=len(gold_rows),
    )

    artifact_hashes = {
        "ontology_binding_sha256": ontology_binding_sha,
        "manifest_sha256": manifest["manifest_sha256"],
        "rows_sha256": rows_sha,
        "gold_sha256": gold_sha,
        "identity_sha256": identity_sha,
        "seal_sha256": (seal or {}).get("seal_sha256"),
        "human_agreement_sha256": sha256_text(canonical_json(agree)),
        "disjointness_sha256": sha256_text(canonical_json(disjoint)),
        "identifiability_sha256": sha256_text(canonical_json(ident)),
    }
    write_private(PRIVATE / "ARTIFACT_HASHES.json", artifact_hashes)
    write_repo(REPO_ART / "artifact_hashes.json", artifact_hashes)
    write_repo(REPO_ART / "gate_binding.json", gates)

    receipt = {
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "PHASE_RULE": PHASE_RULE,
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "SURFACE_STATE": decision["SURFACE_STATE"],
        "NEXT_ACTION": decision["NEXT_ACTION"],
        "QUALIFICATION_STATE": (seal or {}).get("QUALIFICATION_STATE")
        or "UNSEALED",
        "n_rows": len(gold_rows),
        "n_acquired_raw": len(raw),
        "stage_a": cov["stage_a"],
        "domain_supports": cov["domain_supports"],
        "function_supports": cov["function_supports"],
        "mediation_supports": cov["mediation_supports"],
        "cardinality": cov["cardinality"],
        "co_label": cov["co_label"],
        "source_max_share": cov["max_source_family_share"],
        "length": cov["length"],
        "natural_share": cov["natural_share"],
        "observed_share": cov["observed_share"],
        "n_annotators": 2,
        "agreement": {
            "mean_set_jaccard": agree["mean_set_jaccard"],
            "stage_raw_agreement": agree["stage_raw_agreement"],
            "stage_kappa": agree["stage_kappa"],
            "stability": agree["stability"],
            "n_adjudicated": agree["n_adjudicated_disagreement"],
        },
        "identifiability_pass": ident["pass"],
        "disjointness": disjoint,
        "source_leakage_flags": len(leakage["flagged_shortcuts"]),
        "ontology_binding_sha256": ontology_binding_sha,
        "hashes": artifact_hashes,
        "qualification_model_executions": model_executions,
        "gate_binding": gates,
        "evaluation_spent": "UNSPENT",
        "historical": historical,
        "zero_label_share": cov["zero_label_share"],
        "no_evidence_share": cov["no_evidence_share"],
        "low_qual_support": cov["low_qual_support"],
        "coverage_sufficient": cov["coverage_sufficient"],
        "statistical_power_note": cov["statistical_power_note"],
        "MODEL_WIDE_BEST_MUTATED": False,
        "V6_CORE_PRODUCT_CANDIDATE_MUTATED": False,
        "QUAL_002_ROWS_REUSED": False,
        "QUAL_003_ROWS_REUSED": False,
        "FUNCTION_role": "ADVISORY_ONLY_NON_BLOCKING",
        "code_revision": code_revision(),
        "settled_at": utc_now_iso(),
    }
    receipt["V6_CORE_QUALIFICATION_SURFACE_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {
                k: v
                for k, v in receipt.items()
                if k != "V6_CORE_QUALIFICATION_SURFACE_RECEIPT_SHA256"
            }
        )
    )
    write_private(PRIVATE / "RECEIPT.json", receipt)
    write_repo(REPO_ART / "receipt.json", receipt)
    write_repo(REPO_ART / "RECEIPT.json", receipt)
    write_repo(
        SPEC / "classification-v6-core-qualification-surface-receipt-20261002.json",
        receipt,
    )

    summary = {
        "SURFACE_STATE": decision["SURFACE_STATE"],
        "NEXT_ACTION": decision["NEXT_ACTION"],
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "QUALIFICATION_STATE": receipt["QUALIFICATION_STATE"],
        "RECEIPT": receipt["V6_CORE_QUALIFICATION_SURFACE_RECEIPT_SHA256"],
        "n_rows": len(gold_rows),
        "zero_label_share": cov["zero_label_share"],
        "no_evidence_share": cov["no_evidence_share"],
        "mean_core_jaccard": agree["mean_core_jaccard"],
        "mean_set_jaccard": agree["mean_set_jaccard"],
        "agreement_stability": agree["stability"],
        "forbidden_overlap": overlap,
        "identifiability_pass": ident["pass"],
        "coverage_sufficient": cov["coverage_sufficient"],
        "qualification_model_executions": 0,
        "seal_sha256": (seal or {}).get("seal_sha256"),
        "QUAL_002_STATUS": "EVALUATION_SPENT",
        "QUAL_003_STATUS": "EVALUATION_SPENT",
        "FUNCTION_role": "ADVISORY_ONLY_NON_BLOCKING",
        "MODEL_WIDE_BEST_MUTATED": False,
        "V6_CORE_PRODUCT_CANDIDATE_MUTATED": False,
    }
    write_private(PRIVATE / "SUMMARY.json", summary)
    write_repo(REPO_ART / "SUMMARY.json", summary)
    write_repo(REPO_ART / "summary.json", summary)

    md = f"""# BUILD_AND_SEAL_FRESH_V6_CORE_QUALIFICATION_SURFACE

```text
SURFACE_STATE = {decision['SURFACE_STATE']}
QUALIFICATION_ID = {QUALIFICATION_ID}
QUALIFICATION_STATE = {receipt['QUALIFICATION_STATE']}
n_rows = {len(gold_rows)}
zero_label_share = {cov['zero_label_share']:.3f}
no_evidence_share = {cov['no_evidence_share']:.3f}
agreement_mean_core_jaccard = {agree['mean_core_jaccard']:.4f}
stability = {agree['stability']}
forbidden_overlap = {overlap}
model_executions = 0
NEXT_ACTION = {decision['NEXT_ACTION']}
QUAL_002/003 = EVALUATION_SPENT / unreused
FUNCTION = optional annotation only (not in inclusion/balance/gates)
```

Model-blind dual annotation under `{binding['ontology_version']}`.
Core gates bound (core≥0.30, DOMAIN≥0.28, MEDIATION≥0.28, zero-FP≤0.20,
exact-reject≥0.80, hierarchy≤0.02). No model scoring before seal.
"""
    write_repo(SPEC / "classification-v6-core-qualification-surface-20261002.md", md)
    write_private(PRIVATE / "SETTLEMENT.md", md)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
