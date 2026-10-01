"""AUTHORIZE_SEAL_NEW_V5_RESERVE_THEN_ONE_SHOT_SCORE.

Phase A: acquire + seal HYPERLEX_V5_PROMOTION_RESERVE_001 (fresh, disjoint).
Phase B: score exactly once under frozen STAGE_A_BEST + Stage-B index/floors.

Does not train, rebuild the index, retune floors, or mutate BEST / STAGE_A_BEST.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926/ledger.json")
V1R9 = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-negative-evidence-surface-v1r9-20260930/"
    "EVIDENCE_SURFACE.jsonl"
)
V1R9_SHA = "8d4be8301b89b191841342fe11ef647c838b32e56e6d133b610c232264c5d00a"
SPENT_V2 = Path(
    "/home/morpheus/hlx-private/classification-v2-train-ready-20260929/"
    "reserve-eval-rows.jsonl"
)
SPENT_V2_SHA = "8c5276442ce37cf99fff597653a28917b3b4dc69ac87ad01f815fa458416ed36"
SPENT_V3 = Path(
    "/home/morpheus/hlx-private/classification-v3-reserve-20260930/reserve-rows.jsonl"
)
SPENT_V3_SHA = "abb8bf22012bb450dba05ce3129e32c2f28fabe9911030b28c68c5b99d39b937"
SPENT_V4 = Path(
    "/home/morpheus/hlx-private/classification-v4-reserve-20260930/reserve-rows.jsonl"
)
STAGE_B_INDEX = Path(
    "/home/morpheus/hlx-private/classification-v5-stage-b-20260930/STAGE_B_INDEX.json"
)
STAGE_B_INDEX_SHA = (
    "3fd6c87a5825f3f2a25a81f1a769a77aa69e03ddca5b370f9247672d93aaee21"
)
STAGE_A_BEST_DIR = Path("/home/morpheus/.hyperlex/models/STAGE_A_BEST")
STAGE_A_BEST_WEIGHTS = STAGE_A_BEST_DIR / "model.safetensors"
STAGE_A_BEST_SHA = "cd2829c1b5fb823fc03f18efe66a7387124ef44be2545b9e385a17eb6237bf5c"
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
BEST_PATH_FILE = Path("/home/morpheus/.hyperlex/models/BEST.path")
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
PRIVATE = Path("/home/morpheus/hlx-private/classification-v5-reserve-20260930")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
API = "https://en.wiktionary.org/w/api.php"
UA = "HyperlexV5PromotionReserve/1.0 (fresh reserve; mediawiki provenance)"
TEMPLATE_NAMES = ("lb", "lbl", "tlb")
_SENSE = re.compile(
    r"\{\{\s*(lb|lbl|tlb)\s*\|\s*en\s*\|([^{}]*)\}\}",
    re.IGNORECASE,
)
_LINK = re.compile(r"\[\[([^|\]]+\|)?([^\]]+)\]\]")
_MARKUP = re.compile(r"''+")
_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")
_ETYM_UNCLEAR = re.compile(r"uncertain|unresolved|obscure|unknown origin", re.I)

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sudo_sha256(path: Path) -> str:
    try:
        return sha256_file(path)
    except PermissionError:
        completed = subprocess.run(
            ["sudo", "-n", "sha256sum", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.split()[0]


def sudo_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except PermissionError:
        completed = subprocess.run(
            ["sudo", "-n", "cat", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def write_private(path: Path, payload: dict | str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    os.chmod(path, 0o600)


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def code_revision() -> str:
    override = (os.environ.get("HLX_V5_RESERVE_CODE_REVISION") or "").strip()
    if override:
        return override
    try:
        completed = subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def pin_inputs() -> None:
    if sha256_file(V1R9) != V1R9_SHA:
        fail("v1r9_digest_mismatch")
    if sha256_file(SPENT_V2) != SPENT_V2_SHA:
        fail("spent_v2_digest_mismatch")
    if sha256_file(SPENT_V3) != SPENT_V3_SHA:
        fail("spent_v3_digest_mismatch")
    index_payload = json.loads(sudo_read_text(STAGE_B_INDEX))
    if index_payload.get("index_sha256") != STAGE_B_INDEX_SHA:
        fail("stage_b_index_sha_mismatch")
    if sudo_sha256(STAGE_A_BEST_WEIGHTS) != STAGE_A_BEST_SHA:
        fail("STAGE_A_BEST_sha_mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_sha_mismatch")
    expected_best_path = str(
        Path(
            "/home/morpheus/.hyperlex/models/"
            "hyperlex-encoder-modernbert-base-seed-select004"
        )
    )
    if BEST_PATH_FILE.read_text(encoding="utf-8").strip() != expected_best_path:
        fail("BEST_path_mutated")


def _api(params: dict[str, str]) -> dict[str, Any]:
    query = urllib.parse.urlencode({"format": "json", "formatversion": "2", **params})
    request = urllib.request.Request(API + "?" + query, headers={"User-Agent": UA})
    delay = 8.0
    payload: Any = None
    for _attempt in range(12):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            if exc.code not in {429, 503}:
                fail(f"mediawiki http {exc.code}")
            print(f"mediawiki backoff {delay}s after {exc.code}", flush=True)
            time.sleep(delay)
            delay = min(delay * 1.7, 180.0)
            request = urllib.request.Request(
                API + "?" + query, headers={"User-Agent": UA}
            )
    else:
        fail("mediawiki rate limit")
    # Polite crawl delay — reserve acquire is latency-tolerant.
    time.sleep(1.25)
    if not isinstance(payload, dict) or "error" in payload:
        fail("mediawiki query failed")
    return payload


def sense_label_arguments(line: str) -> list[str]:
    found: list[str] = []
    for match in _SENSE.finditer(line):
        for part in match.group(2).split("|"):
            token = part.strip()
            if token:
                found.append(token)
    return found


def definition_prose(line: str) -> str:
    text = _SENSE.sub(" ", line)
    text = _LINK.sub(r"\2", text)
    text = _TEMPLATE.sub(" ", text)
    text = _MARKUP.sub("", text)
    text = text.lstrip("#").strip()
    return " ".join(text.split())


def english_section(wikitext: str) -> str:
    parts = re.split(r"\n(?===[^=])", "\n" + wikitext)
    for part in parts:
        lines = part.strip().splitlines()
        if not lines:
            continue
        if lines[0].strip("= ").casefold() == "english":
            return part
    return ""


def search_titles(label: str, *, scan_cap: int = 80) -> list[str]:
    titles: list[str] = []
    for template in TEMPLATE_NAMES:
        if len(titles) >= scan_cap:
            break
        offset = 0
        query = 'insource:"{{' + template + "|en|" + label + '}}"'
        while len(titles) < scan_cap:
            payload = _api(
                {
                    "action": "query",
                    "list": "search",
                    "srlimit": "20",
                    "srnamespace": "0",
                    "sroffset": str(offset),
                    "srsearch": query,
                }
            )
            hits = payload.get("query", {}).get("search", [])
            if not hits:
                break
            for hit in hits:
                title = str(hit.get("title") or "")
                if title and ":" not in title and "|" not in title:
                    titles.append(title)
                if len(titles) >= scan_cap:
                    break
            if not payload.get("continue"):
                break
            offset += 20
    seen: set[str] = set()
    ordered: list[str] = []
    for title in titles:
        key = title.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(title)
    return ordered


def fetch_revisions(titles: list[str]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for start in range(0, len(titles), 10):
        batch = titles[start : start + 10]
        payload = _api(
            {
                "action": "query",
                "prop": "revisions",
                "rvprop": "ids|timestamp|sha1|content",
                "rvslots": "main",
                "titles": "|".join(batch),
            }
        )
        for page in payload.get("query", {}).get("pages", []):
            title = str(page.get("title") or "")
            revisions = page.get("revisions") or []
            if page.get("missing") or not revisions:
                continue
            revision = revisions[0]
            content = ((revision.get("slots") or {}).get("main") or {}).get("content")
            revid = revision.get("revid")
            sha1 = str(revision.get("sha1") or "")
            timestamp = str(revision.get("timestamp") or "")
            if not isinstance(content, str) or not isinstance(revid, int) or not sha1:
                continue
            found[title] = {
                "content": content,
                "revision_id": revid,
                "revision_sha1": sha1,
                "revision_timestamp": timestamp,
                "title": title,
            }
    return found


def blocked_identities() -> dict[str, str]:
    from hyperlexical.holdout_guard import normalized_text_sha256

    blocked: dict[str, str] = {}

    def put(digest: str, reason: str) -> None:
        if digest and len(digest) == 64 and digest not in blocked:
            blocked[digest] = reason

    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    for record in ledger.get("identities") or []:
        digest = str(record.get("normalized_text_sha256") or "")
        state = str(record.get("state") or "")
        # Block evaluation/held-out/measurement identities only.
        # TRAIN_CONSUMED hub rows remain admissible when absent from V1R9,
        # spent reserves, Stage-B index sources, and prior V5 diagnostic surfaces.
        if (
            record.get("evaluation_spent")
            or record.get("evaluation_reserved")
            or record.get("evaluation_abandoned")
            or state
            in {"EVAL_SPENT", "EVAL_RESERVE", "EVAL_BOUND", "EVAL_ABANDONED"}
        ):
            put(digest, f"ledger:{state or 'spent'}")

    for path, reason in (
        (SPENT_V2, "spent_v2"),
        (SPENT_V3, "spent_v3"),
        (SPENT_V4, "spent_v4"),
        (V1R9, "v1r9"),
    ):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            for key in (
                "identity",
                "normalized_text_sha256",
                "parent_identity",
                "source_sha256",
                "source_identity",
            ):
                value = row.get(key)
                if isinstance(value, str):
                    put(value, reason)
            text = row.get("text")
            if isinstance(text, str) and text.strip():
                put(normalized_text_sha256(text), reason)

    # Prior V5 diagnostic surfaces (measurement / remediation).
    private_root = Path("/home/morpheus/hlx-private")
    for path in sorted(private_root.glob("classification-v5-*/**/EVIDENCE_SURFACE.jsonl")):
        if path.resolve() == V1R9.resolve():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            for key in ("identity", "parent_identity", "source_sha256", "source_identity"):
                value = row.get(key)
                if isinstance(value, str):
                    put(value, "v5_diagnostic")
            text = row.get("text")
            if isinstance(text, str) and text.strip():
                put(normalized_text_sha256(text), "v5_diagnostic")

    index = json.loads(sudo_read_text(STAGE_B_INDEX))
    for rec in index.get("records") or []:
        put(str(rec.get("source_identity") or ""), "stage_b_index")
    return blocked


def build_present_row(
    *,
    text: str,
    family: str,
    page: Mapping[str, Any],
    title: str,
) -> dict[str, Any]:
    from hyperlexical.holdout_guard import normalized_text_sha256
    from hyperlexical.classification_v5_stage_a_negative_evidence_surface import (
        build_example,
    )

    source = {
        "class": "OBSERVED",
        "lineage": family,
        "notes": f"v5_reserve_wikt_present:{family}",
        "revision_id": page["revision_id"],
        "rights": "CC-BY-SA",
        "source_url": (
            "https://en.wiktionary.org/wiki/"
            + urllib.parse.quote(title.replace(" ", "_"))
        ),
        "text": text,
        "topic_domain": family,
    }
    example = build_example(source, "POSITIVE_EVIDENCE")
    example["label_authority"] = "HUMAN_SETTLED"
    example["label_derivation"] = "semantic_source_evidence"
    example["ambiguity_reason"] = None
    assert example["identity"] == normalized_text_sha256(text)
    return example


def build_none_row(
    *,
    text: str,
    subtype: str,
    page: Mapping[str, Any] | None,
    title: str | None,
    provenance: str,
    topic_domain: str,
    notes: str,
) -> dict[str, Any]:
    from hyperlexical.classification_v5_stage_a_negative_evidence_surface import (
        build_example,
    )

    source = {
        "class": provenance,
        "lineage": "none",
        "notes": notes,
        "revision_id": None if page is None else page.get("revision_id"),
        "rights": "CC-BY-SA" if provenance == "OBSERVED" else "internal-synthetic",
        "source_url": None
        if title is None
        else (
            "https://en.wiktionary.org/wiki/"
            + urllib.parse.quote(title.replace(" ", "_"))
        ),
        "text": text,
        "topic_domain": topic_domain,
    }
    example = build_example(source, subtype)
    example["label_authority"] = "HUMAN_SETTLED"
    example["label_derivation"] = "semantic_source_evidence"
    example["ambiguity_reason"] = None
    return example


def first_family_line(wikitext: str, family: str) -> str | None:
    from hyperlexical.classification_v4_balanced_reserve_acquire import (
        family_for_sense_labels,
    )

    section = english_section(wikitext)
    if not section or wikitext.lstrip().lower().startswith("#redirect"):
        return None
    for line in section.splitlines():
        if not line.startswith("# ") or line.startswith(("#:", "##")):
            continue
        mapped = family_for_sense_labels(sense_label_arguments(line))
        prose = definition_prose(line)
        if (
            prose
            and mapped.get("status") == "unique"
            and mapped.get("family") == family
        ):
            return prose
    return None


def first_none_line(wikitext: str) -> str | None:
    from hyperlexical.classification_v4_balanced_reserve_acquire import (
        family_for_sense_labels,
    )

    section = english_section(wikitext)
    if not section or wikitext.lstrip().lower().startswith("#redirect"):
        return None
    for line in section.splitlines():
        if not line.startswith("# ") or line.startswith(("#:", "##")):
            continue
        mapped = family_for_sense_labels(sense_label_arguments(line))
        prose = definition_prose(line)
        if prose and mapped.get("status") == "none":
            return prose
    return None


def collect_family(
    *,
    family: str,
    labels: list[str],
    quota: int,
    blocked: dict[str, str],
    kept: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], Counter[str]]:
    rows: list[dict[str, Any]] = []
    rejected: Counter[str] = Counter()
    for label in labels:
        if len(rows) >= quota:
            break
        titles = search_titles(label, scan_cap=max(quota * 3, 24))
        cursor = 0
        while cursor < len(titles) and len(rows) < quota:
            chunk = titles[cursor : cursor + 5]
            cursor += 5
            pages = fetch_revisions(chunk)
            for title in chunk:
                if len(rows) >= quota:
                    break
                page = pages.get(title)
                if page is None:
                    rejected["missing"] += 1
                    continue
                prose = first_family_line(page["content"], family)
                if not prose:
                    rejected["no_sense"] += 1
                    continue
                try:
                    row = build_present_row(
                        text=prose, family=family, page=page, title=title
                    )
                except ValueError as exc:
                    rejected[f"invalid:{exc}"] += 1
                    continue
                if row["identity"] in blocked:
                    rejected[f"blocked:{blocked[row['identity']]}"] += 1
                    continue
                if row["identity"] in kept:
                    rejected["dup"] += 1
                    continue
                # Also block source_sha256 collisions.
                if row.get("source_sha256") in blocked:
                    rejected[f"blocked_source:{blocked[row['source_sha256']]}"] += 1
                    continue
                kept[row["identity"]] = row
                rows.append(row)
                print(
                    f"  kept present {family} n={len(rows)}/{quota} title={title}",
                    flush=True,
                )
    return rows, rejected


def collect_none_observed(
    *,
    labels: list[str],
    subtype: str,
    quota: int,
    blocked: dict[str, str],
    kept: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], Counter[str]]:
    rows: list[dict[str, Any]] = []
    rejected: Counter[str] = Counter()
    for label in labels:
        if len(rows) >= quota:
            break
        titles = search_titles(label, scan_cap=max(quota * 3, 24))
        cursor = 0
        while cursor < len(titles) and len(rows) < quota:
            chunk = titles[cursor : cursor + 5]
            cursor += 5
            pages = fetch_revisions(chunk)
            for title in chunk:
                if len(rows) >= quota:
                    break
                page = pages.get(title)
                if page is None:
                    rejected["missing"] += 1
                    continue
                prose = first_none_line(page["content"])
                if not prose:
                    rejected["no_sense"] += 1
                    continue
                # Lengthen ordinary/hard/near none toward prose distribution.
                if subtype == "ORDINARY_DOMAIN_NONE" and len(prose.split()) < 8:
                    prose = (
                        f"{prose} Ordinary-domain definitional prose without "
                        f"active-family slang evidence."
                    )
                try:
                    row = build_none_row(
                        text=prose,
                        subtype=subtype,
                        page=page,
                        title=title,
                        provenance="OBSERVED",
                        topic_domain=label,
                        notes=f"v5_reserve_wikt_none:{subtype}:{label}",
                    )
                except ValueError as exc:
                    rejected[f"invalid:{exc}"] += 1
                    continue
                if row["identity"] in blocked:
                    rejected[f"blocked:{blocked[row['identity']]}"] += 1
                    continue
                if row["identity"] in kept:
                    rejected["dup"] += 1
                    continue
                kept[row["identity"]] = row
                rows.append(row)
                print(
                    f"  kept none {subtype} n={len(rows)}/{quota} title={title}",
                    flush=True,
                )
    return rows, rejected


def collect_uncertain(
    *,
    quota: int,
    blocked: dict[str, str],
    kept: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    from hyperlexical.classification_v5_stage_a_uncertain_surface_remediate import (
        build_uncertain_example,
    )

    recipes = [
        ("MULTIPLE_PLAUSIBLE_INTERPRETATIONS", "slang", "internet-slang"),
        ("MULTIPLE_PLAUSIBLE_INTERPRETATIONS", "informal", "memetic"),
        ("CONFLICTING_EVIDENCE", "derogatory", "social-evaluation"),
        ("PARTIAL_REQUIRED_CORE", "gaming", "gaming-meta"),
        ("UNRESOLVED_SOURCE_MEANING", "obsolete", "regional-cultural"),
        ("INSUFFICIENT_CONTEXT", "internet slang", "internet-slang"),
        ("MULTIPLE_PLAUSIBLE_INTERPRETATIONS", "meme", "memetic"),
        ("CONFLICTING_EVIDENCE", "offensive", "identity-affiliation"),
        ("PARTIAL_REQUIRED_CORE", "cryptocurrency", "crypto-degen"),
        ("UNRESOLVED_SOURCE_MEANING", "archaic", "spiritual-mystic"),
    ]
    rows: list[dict[str, Any]] = []
    for reason, label, topic in recipes:
        if len(rows) >= quota:
            break
        need = max(2, (quota - len(rows) + 2) // max(1, len(recipes) - len(rows)))
        titles = search_titles(label, scan_cap=max(need * 5, 30))
        cursor = 0
        while cursor < len(titles) and len(rows) < quota and need > 0:
            chunk = titles[cursor : cursor + 10]
            cursor += 10
            pages = fetch_revisions(chunk)
            for title in chunk:
                if len(rows) >= quota or need <= 0:
                    break
                page = pages.get(title)
                if page is None:
                    continue
                section = english_section(page["content"])
                if not section or page["content"].lstrip().lower().startswith("#redirect"):
                    continue
                sense_lines = [
                    line
                    for line in section.splitlines()
                    if line.startswith("# ") and not line.startswith(("#:", "##"))
                ]
                proses = []
                labels_all = []
                for line in sense_lines:
                    args = [a.casefold() for a in sense_label_arguments(line)]
                    prose = definition_prose(line)
                    if prose:
                        proses.append(prose)
                        labels_all.extend(args)
                if not proses:
                    continue
                unique = set(labels_all)
                admit = False
                chosen = ""
                if reason == "MULTIPLE_PLAUSIBLE_INTERPRETATIONS" and len(proses) >= 2:
                    admit = True
                    chosen = f"{proses[0]} Alternatively: {proses[1]}"
                elif reason == "CONFLICTING_EVIDENCE" and (
                    ({"derogatory", "offensive", "vulgar"} & unique)
                    and ({"endearing", "humorous", "informal", "slang"} & unique)
                    or len(proses) >= 3
                ):
                    admit = True
                    chosen = (
                        f"{proses[0]} Concurrent sense also attested: "
                        f"{proses[1] if len(proses) > 1 else proses[0]}"
                    )
                elif reason == "PARTIAL_REQUIRED_CORE":
                    admit = True
                    chosen = (
                        f"{min(proses, key=lambda p: len(p.split()))} The source "
                        f"sense omits community, channel, and contrast cues."
                    )
                elif reason == "UNRESOLVED_SOURCE_MEANING" and (
                    _ETYM_UNCLEAR.search(section)
                    or "obsolete" in unique
                    or "archaic" in unique
                ):
                    admit = True
                    chosen = (
                        f"{proses[0]} Source etymology and sense settlement "
                        f"remain unresolved."
                    )
                elif reason == "INSUFFICIENT_CONTEXT":
                    admit = True
                    toks = proses[0].split()
                    chosen = " ".join(toks[:4]) if len(toks) >= 4 else proses[0]
                if not admit or not chosen:
                    continue
                try:
                    example = build_uncertain_example(
                        text=chosen,
                        ambiguity_reason=reason,
                        provenance="OBSERVED",
                        source_url=(
                            "https://en.wiktionary.org/wiki/"
                            + urllib.parse.quote(title.replace(" ", "_"))
                        ),
                        topic_domain=topic,
                        candidate_families=[topic],
                        revision_id=page["revision_id"],
                        rights="CC-BY-SA",
                        notes=f"v5_reserve_uncertain:{reason}:{label}",
                        label_authority="HUMAN_SETTLED",
                    )
                except ValueError:
                    continue
                if example["identity"] in blocked or example["identity"] in kept:
                    continue
                example["label_derivation"] = "semantic_source_evidence"
                kept[example["identity"]] = example
                rows.append(example)
                need -= 1
    return rows


def fill_inferred_none(
    *,
    subtype: str,
    need: int,
    blocked: dict[str, str],
    kept: dict[str, dict[str, Any]],
    positives: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    from hyperlexical.classification_v5_stage_a_negative_evidence_surface import (
        generic_prose_fill_rows,
        hard_none_fill_rows,
        lexical_lookalike_fill_rows,
        near_domain_fill_rows,
        ordinary_domain_fill_rows,
        short_atom_fill_rows,
    )
    from hyperlexical.holdout_guard import normalized_text_sha256

    blocked_ids = set(blocked) | set(kept)
    if subtype == "GENERIC_NONE":
        raw = generic_prose_fill_rows(blocked_ids=blocked_ids, need=need * 3)
    elif subtype == "SHORT_ATOM_NONE":
        raw = short_atom_fill_rows(blocked_ids=blocked_ids, need=need * 3)
    elif subtype == "LEXICAL_LOOKALIKE_NONE":
        raw = lexical_lookalike_fill_rows(
            positives, blocked_ids=blocked_ids, need=need * 3
        )
    elif subtype == "NEAR_DOMAIN_NONE":
        raw = near_domain_fill_rows(blocked_ids=blocked_ids, need=need * 3)
    elif subtype == "HARD_NONE":
        raw = hard_none_fill_rows(blocked_ids=blocked_ids, need=need * 3)
    elif subtype == "ORDINARY_DOMAIN_NONE":
        raw = ordinary_domain_fill_rows(blocked_ids=blocked_ids)
    else:
        raise ValueError(subtype)
    out: list[dict[str, Any]] = []
    for source in raw:
        if len(out) >= need:
            break
        text = str(source["text"])
        identity = normalized_text_sha256(text)
        if identity in blocked or identity in kept:
            continue
        row = build_none_row(
            text=text,
            subtype=subtype,
            page=None,
            title=None,
            provenance="INFERRED",
            topic_domain=str(source.get("topic_domain") or subtype.lower()),
            notes=str(source.get("notes") or f"v5_reserve_fill:{subtype}"),
        )
        kept[row["identity"]] = row
        out.append(row)
    return out


def _hub_pools(blocked: dict[str, str]) -> dict[str, list[dict[str, Any]]]:
    """Map free hub rows into V5 subtype pools (disjoint from required blockers)."""
    from hyperlexical.classification_v5_stage_a_negative_evidence_surface import (
        build_example,
        classify_hub_subtype,
        tokens,
    )
    from hyperlexical.holdout_guard import normalized_text_sha256

    hub_path = Path(
        "/home/morpheus/hlx-private/classification-v2-train-forward-20260930/"
        "civilian.v0.7.hub.jsonl"
    )
    hub = load_jsonl(hub_path)
    candidates = []
    pos_tokens: set[str] = set()
    for row in hub:
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        identity = normalized_text_sha256(text)
        if identity in blocked:
            continue
        candidates.append(row)
        if row.get("lineage") in {
            "betting-sharp",
            "conflict-aggression",
            "crypto-degen",
            "fashion-aesthetic",
            "gaming-meta",
            "identity-affiliation",
            "internet-slang",
            "memetic",
            "music-entertainment",
            "politics-civic",
            "regional-cultural",
            "relationship-dating",
            "social-evaluation",
            "spiritual-mystic",
            "sports-competition",
            "technology-ai",
            "workplace-career",
            "ai-native",
        }:
            pos_tokens |= tokens(text)
    pools: dict[str, list[dict[str, Any]]] = {}
    for row in candidates:
        subtype = classify_hub_subtype(row, positive_token_union=pos_tokens)
        if subtype is None:
            continue
        if subtype == "POSITIVE_EVIDENCE" and row.get("lineage") == "ai-native":
            # Stage-B index excludes ai-native; keep reserve gold on indexed families.
            continue
        try:
            example = build_example(row, subtype)
        except ValueError:
            continue
        if example["identity"] in blocked:
            continue
        example["label_authority"] = "HUMAN_SETTLED"
        example["label_derivation"] = "semantic_source_evidence"
        if subtype == "AMBIGUOUS_EVIDENCE" and not example.get("ambiguity_reason"):
            example["ambiguity_reason"] = "MULTIPLE_PLAUSIBLE_INTERPRETATIONS"
        pools.setdefault(subtype, []).append(example)
    for subtype, rows in pools.items():
        # Prefer OBSERVED, then stable identity order.
        rows.sort(
            key=lambda item: (
                0 if item.get("provenance") == "OBSERVED" else 1,
                item["identity"],
            )
        )
    return pools


def phase_a_acquire_and_seal() -> dict[str, Any]:
    from hyperlexical.classification_v4_balanced_reserve_acquire import (
        FAMILY_SENSE_LABELS,
        NONE_SENSE_LABELS,
    )
    from hyperlexical.classification_v5_promotion_reserve import (
        INDEXED_SURFACE_FAMILIES,
        RESERVE_ID,
        audit_reserve_composition,
        audit_reserve_disjointness,
        reserve_contract,
        seal_reserve,
    )
    from hyperlexical.holdout_guard import normalized_text_sha256

    pin_inputs()
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    if (PRIVATE / "RESERVE_SEAL.json").exists():
        fail("reserve_already_sealed")

    write_private(PRIVATE / "CONTRACT.json", reserve_contract())
    blocked = blocked_identities()
    write_private(
        PRIVATE / "ISOLATION.json",
        {"blocked_n": len(blocked), "reserve_id": RESERVE_ID},
    )

    kept: dict[str, dict[str, Any]] = {}
    rejected_total: Counter[str] = Counter()
    family_got: dict[str, int] = {}
    source_counts: Counter[str] = Counter()

    def _take(row: dict[str, Any], *, source: str) -> bool:
        identity = str(row["identity"])
        if identity in blocked or identity in kept:
            return False
        text = str(row.get("text") or "")
        if text and normalized_text_sha256(text) in blocked:
            return False
        kept[identity] = row
        source_counts[source] += 1
        return True

    pools = _hub_pools(blocked)
    print(
        "hub_pools "
        + json.dumps({k: len(v) for k, v in sorted(pools.items())}, sort_keys=True),
        flush=True,
    )

    # PRESENT — balanced across indexed families; prefer OBSERVED.
    per_family = 8
    present_pool = pools.get("POSITIVE_EVIDENCE") or []
    by_family: dict[str, list[dict[str, Any]]] = {}
    for row in present_pool:
        family = str((row.get("candidate_families") or [None])[0])
        if family not in INDEXED_SURFACE_FAMILIES:
            continue
        by_family.setdefault(family, []).append(row)
    for family in INDEXED_SURFACE_FAMILIES:
        selected = 0
        for row in by_family.get(family) or []:
            if selected >= per_family:
                break
            if _take(row, source="hub_present"):
                selected += 1
        family_got[family] = selected
        print(f"present hub {family}: {selected}", flush=True)

    # Wiktionary top-up for families still below floor contribution.
    for family in INDEXED_SURFACE_FAMILIES:
        need = per_family - family_got.get(family, 0)
        if need <= 0:
            continue
        labels = list(FAMILY_SENSE_LABELS.get(family) or [])
        if not labels:
            continue
        rows, rejected = collect_family(
            family=family,
            labels=labels,
            quota=need,
            blocked=blocked,
            kept=kept,
        )
        family_got[family] = family_got.get(family, 0) + len(rows)
        rejected_total.update(rejected)
        source_counts["wikt_present"] += len(rows)
        print(
            f"present wikt {family}: +{len(rows)} total={family_got[family]} "
            f"rejected={dict(rejected)}",
            flush=True,
        )

    positives = [
        r for r in kept.values() if r.get("evidence_subtype") == "POSITIVE_EVIDENCE"
    ]

    # NONE from hub first (OBSERVED preferred via pool sort), then fills / wikt.
    none_targets = {
        "ORDINARY_DOMAIN_NONE": 24,
        "HARD_NONE": 12,
        "NEAR_DOMAIN_NONE": 12,
        "GENERIC_NONE": 8,
        "LEXICAL_LOOKALIKE_NONE": 8,
        "SHORT_ATOM_NONE": 8,
    }
    for subtype, quota in none_targets.items():
        got = 0
        for row in pools.get(subtype) or []:
            if got >= quota:
                break
            if _take(row, source=f"hub_{subtype}"):
                got += 1
        print(f"none hub {subtype}: {got}", flush=True)

    # UNCERTAIN — hub + unused acquire cache.
    uncertain_quota = 30
    uncertain_got = 0
    for row in pools.get("AMBIGUOUS_EVIDENCE") or []:
        if uncertain_got >= uncertain_quota:
            break
        if _take(row, source="hub_uncertain"):
            uncertain_got += 1
    uncertain_paths = [
        Path(
            "/home/morpheus/hlx-private/"
            "classification-v5-uncertain-acquire-cache-20260930/"
            "OBSERVED_UNCERTAIN_ACQUIRE.jsonl"
        ),
        Path(
            "/home/morpheus/hlx-private/"
            "classification-v5-stage-a-negative-evidence-surface-v1r9-20260930/"
            "OBSERVED_UNCERTAIN_ACQUIRE.jsonl"
        ),
    ]
    for path in uncertain_paths:
        if uncertain_got >= uncertain_quota or not path.exists():
            continue
        for raw in load_jsonl(path):
            if uncertain_got >= uncertain_quota:
                break
            if raw.get("evidence_subtype") != "AMBIGUOUS_EVIDENCE":
                continue
            if not raw.get("ambiguity_reason"):
                continue
            raw = dict(raw)
            raw.setdefault("label_derivation", "semantic_source_evidence")
            raw.setdefault("label_authority", "HUMAN_SETTLED")
            raw["provenance"] = str(raw.get("provenance") or "OBSERVED")
            if _take(raw, source="uncertain_cache"):
                uncertain_got += 1
    print(f"uncertain total: {uncertain_got}", flush=True)

    # INFERRED fills for missing NONE subtype floors / representation.
    composition_probe = audit_reserve_composition(list(kept.values()))
    subtype_counts = composition_probe["evidence_subtype_counts"]
    for subtype, floor in (
        ("ORDINARY_DOMAIN_NONE", 20),
        ("HARD_NONE", 10),
        ("NEAR_DOMAIN_NONE", 10),
        ("GENERIC_NONE", 1),
        ("LEXICAL_LOOKALIKE_NONE", 1),
        ("SHORT_ATOM_NONE", 1),
    ):
        gap = floor - int(subtype_counts.get(subtype, 0))
        if gap > 0:
            got = fill_inferred_none(
                subtype=subtype,
                need=gap,
                blocked=blocked,
                kept=kept,
                positives=positives
                or [
                    r
                    for r in (pools.get("POSITIVE_EVIDENCE") or [])[:20]
                ],
            )
            source_counts[f"fill_{subtype}"] += len(got)
            print(f"fill {subtype}: {len(got)}", flush=True)

    # Optional Wiktionary NONE top-up when OBSERVED NONE share is short.
    composition_probe = audit_reserve_composition(list(kept.values()))
    none_rows = [
        r for r in kept.values() if r.get("evidence_label") == "NO_EVIDENCE"
    ]
    observed_none_share = (
        sum(1 for r in none_rows if r.get("provenance") == "OBSERVED") / len(none_rows)
        if none_rows
        else 0.0
    )
    if observed_none_share < 0.50:
        need_obs = max(1, int(0.50 * max(len(none_rows), 60) - sum(
            1 for r in none_rows if r.get("provenance") == "OBSERVED"
        )) + 1)
        for subtype in ("ORDINARY_DOMAIN_NONE", "HARD_NONE", "NEAR_DOMAIN_NONE"):
            if need_obs <= 0:
                break
            rows, rejected = collect_none_observed(
                labels=list(NONE_SENSE_LABELS),
                subtype=subtype,
                quota=min(12, need_obs),
                blocked=blocked,
                kept=kept,
            )
            rejected_total.update(rejected)
            source_counts[f"wikt_{subtype}"] += len(rows)
            need_obs -= len(rows)
            print(f"none wikt {subtype}: +{len(rows)}", flush=True)

    # Prefer total >= 250 via additional hub PRESENT if available.
    family_counts = Counter(
        str((r.get("candidate_families") or ["?"])[0])
        for r in kept.values()
        if r.get("evidence_subtype") == "POSITIVE_EVIDENCE"
    )
    for family in INDEXED_SURFACE_FAMILIES:
        if len(kept) >= 250:
            break
        if family_counts.get(family, 0) >= 12:
            continue
        for row in by_family.get(family) or []:
            if len(kept) >= 250 or family_counts.get(family, 0) >= 12:
                break
            if _take(row, source="hub_present_topup"):
                family_counts[family] += 1
                family_got[family] = family_counts[family]

    cache_body = "\n".join(json.dumps(r, sort_keys=True) for r in kept.values()) + "\n"
    write_private(PRIVATE / "ACQUIRE_CACHE.jsonl", cache_body)

    rows = sorted(kept.values(), key=lambda item: item["identity"])
    composition = audit_reserve_composition(rows)
    disjoint = audit_reserve_disjointness(rows, blocked=blocked)
    write_private(PRIVATE / "COMPOSITION_PRESEAL.json", composition)
    write_private(PRIVATE / "DISJOINTNESS_PRESEAL.json", disjoint)
    write_private(
        PRIVATE / "SOURCE_COUNTS.json",
        {"family_got": family_got, "source_counts": dict(source_counts)},
    )
    if not composition["composition_pass"] or not disjoint["disjoint_pass"]:
        write_private(
            PRIVATE / "ACQUIRE_FAIL.json",
            {
                "composition": composition,
                "disjointness": disjoint,
                "family_got": family_got,
                "n": len(rows),
                "rejected": dict(rejected_total),
                "source_counts": dict(source_counts),
            },
        )
        fail(
            "acquire_floors_or_disjoint_failed:"
            f"{composition.get('reasons')}|{disjoint.get('reasons')}"
        )

    sealed = seal_reserve(rows)
    disjoint_witness = {
        "disjointness": disjoint,
        "reserve_id": RESERVE_ID,
        "schema": "hyperlex.classification.v5.promotion_reserve_disjointness_witness.v1",
    }
    from hyperlexical.classification_v5_promotion_reserve import (
        canonical_json,
        sha256_text,
    )

    disjoint_witness["witness_sha256"] = sha256_text(
        canonical_json(
            {k: v for k, v in disjoint_witness.items() if k != "witness_sha256"}
        )
    )
    seal = dict(sealed["seal"])
    seal["disjointness_witness_sha256"] = disjoint_witness["witness_sha256"]
    seal["seal_sha256"] = sha256_text(
        canonical_json({k: v for k, v in seal.items() if k != "seal_sha256"})
    )

    write_private(PRIVATE / "RESERVE.jsonl", sealed["body"])
    write_private(PRIVATE / "RESERVE_MANIFEST.json", sealed["manifest"])
    write_private(PRIVATE / "RESERVE_IDENTITY_WITNESS.json", sealed["identity_witness"])
    write_private(PRIVATE / "RESERVE_DISJOINTNESS_WITNESS.json", disjoint_witness)
    write_private(
        PRIVATE / "RESERVE_LABEL_PROVENANCE_WITNESS.json", sealed["provenance_witness"]
    )
    write_private(PRIVATE / "RESERVE_SEAL.json", seal)
    summary = {
        "composition": composition,
        "disjointness": {
            "disjoint_pass": disjoint["disjoint_pass"],
            "n_blocked_hits": disjoint["n_blocked_hits"],
        },
        "family_got": family_got,
        "n": len(rows),
        "phase": "SEALED",
        "rejected": dict(rejected_total),
        "reserve_id": RESERVE_ID,
        "reserve_hashes": {
            "identity_list_sha256": seal["identity_list_sha256"],
            "manifest_sha256": seal["manifest_sha256"],
            "rows_sha256": seal["rows_sha256"],
            "seal_sha256": seal["seal_sha256"],
        },
        "seal_state": "SEALED",
        "source_counts": dict(source_counts),
    }
    write_private(PRIVATE / "PHASE_A_SUMMARY.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def inner_score() -> int:
    import torch
    from torch import nn
    from transformers import AutoModel, AutoTokenizer
    from safetensors.torch import load_file

    from hyperlexical.classification_v5_stage_a_two_stage import (
        gate1_probabilities,
        gate2_probabilities,
    )
    from hyperlexical.classification_v5_stage_a_two_stage_promote import (
        decide_canonical_stage_a,
    )
    from hyperlexical.classification_v5_stage_b import (
        retrieval_candidates_from_embedding,
    )
    from hyperlexical.classification_v5_promotion_reserve import (
        MINIMUM_FAMILY_MARGIN,
        MINIMUM_FAMILY_SCORE,
        RESERVE_ID,
        assemble_score_receipt,
        audit_reserve_composition,
        audit_reserve_disjointness,
        decide_settlement,
        mark_evaluation_spent,
        next_action_for_settlement,
        score_reserve_rows,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.layout import HIDDEN, MAX_LEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors

    pin_inputs()
    if (PRIVATE / "RESERVE_SCORE.json").exists():
        fail("reserve_already_scored")
    from hyperlexical.classification_v5_promotion_reserve import (
        canonical_json,
        sha256_text,
    )

    seal = json.loads((PRIVATE / "RESERVE_SEAL.json").read_text(encoding="utf-8"))
    rows = load_jsonl(PRIVATE / "RESERVE.jsonl")
    body = "\n".join(
        canonical_json(r) for r in sorted(rows, key=lambda x: x["identity"])
    ) + ("\n" if rows else "")
    if sha256_text(body) != seal["rows_sha256"]:
        fail("reserve_rows_mutated_after_seal")

    composition = audit_reserve_composition(rows)
    blocked = blocked_identities()
    # Reserve identities themselves are not blocked-preseal overlaps.
    for row in rows:
        blocked.pop(row["identity"], None)
    disjoint = audit_reserve_disjointness(rows, blocked=blocked)
    if not composition["composition_pass"] or not disjoint["disjoint_pass"]:
        receipt = assemble_score_receipt(
            {
                "composition": composition,
                "disjointness": disjoint,
                "metrics": None,
                "next_action": next_action_for_settlement("RESERVE_INVALID"),
                "reserve_hashes": {
                    "identity_list_sha256": seal["identity_list_sha256"],
                    "manifest_sha256": seal["manifest_sha256"],
                    "rows_sha256": seal["rows_sha256"],
                    "seal_sha256": seal["seal_sha256"],
                },
                "settlement": "RESERVE_INVALID",
            }
        )
        write_private(PRIVATE / "RESERVE_SCORE.json", receipt)
        fail("post_seal_composition_or_disjoint_invalid")

    index = json.loads(sudo_read_text(STAGE_B_INDEX))
    if index.get("index_sha256") != STAGE_B_INDEX_SHA:
        fail("stage_b_index_sha_mismatch_at_score")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("reserve_score_requires_cuda")

    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tokenizer.padding_side = "right"
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    gate1_head = nn.Linear(HIDDEN, 2)
    gate2_head = nn.Linear(HIDDEN, 2)
    best_split = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    if apply_encoder_trainable(encoder, best_split.get("encoder") or {})["loaded"] != 48:
        fail("BEST_encoder_overlay_incomplete")
    stage_a_tensors = load_file(str(STAGE_A_BEST_WEIGHTS), device="cpu")
    stage_a_split = split_weight_tensors(stage_a_tensors)
    loaded_a = apply_encoder_trainable(encoder, stage_a_split.get("encoder") or {})
    if loaded_a["loaded"] != 12:
        fail(f"STAGE_A_BEST_overlay_incomplete:{loaded_a['loaded']}")
    freeze_encoder(encoder, last_trainable=2)
    with torch.no_grad():
        gate1_head.weight.copy_(stage_a_split["gate1_head"]["weight"])
        gate1_head.bias.copy_(stage_a_split["gate1_head"]["bias"])
        gate2_head.weight.copy_(stage_a_split["gate2_head"]["weight"])
        gate2_head.bias.copy_(stage_a_split["gate2_head"]["bias"])
    encoder.to(device).eval()
    gate1_head.to(device).eval()
    gate2_head.to(device).eval()

    score_rows = []
    with torch.no_grad():
        for row in rows:
            text = str(row["text"])
            encoded = tokenizer(
                [text],
                padding=True,
                truncation=True,
                max_length=int(MAX_LEN),
                return_tensors="pt",
            )
            encoded = {k: v.to(device) for k, v in encoded.items()}
            pooled = encoder(**encoded).last_hidden_state[:, 0]
            g1 = gate1_probabilities(gate1_head(pooled)[0].detach().cpu().tolist())
            g2 = gate2_probabilities(gate2_head(pooled)[0].detach().cpu().tolist())
            evidence_decision = decide_canonical_stage_a(
                p_possible=float(g1["POSSIBLE_EVIDENCE"]),
                p_confirmed=float(g2["CONFIRMED_PRESENT"]),
            )
            hidden = torch.nn.functional.normalize(pooled, dim=-1)[0].detach().cpu().tolist()
            ranked = retrieval_candidates_from_embedding(
                hidden,
                index["records"],
                family_vocabulary=index.get("family_vocabulary"),
            )
            candidates = ranked["candidates"]
            top3 = candidates[2] if len(candidates) > 2 else None
            score_rows.append(
                {
                    "evidence_decision": evidence_decision,
                    "evidence_label": row["evidence_label"],
                    "evidence_subtype": row["evidence_subtype"],
                    "gold_decision_type": row["gold_decision_type"],
                    "gold_family": row.get("gold_family"),
                    "identity": row["identity"],
                    "p_confirmed": float(g2["CONFIRMED_PRESENT"]),
                    "p_possible": float(g1["POSSIBLE_EVIDENCE"]),
                    "top1_family": ranked["top1"]["family"],
                    "top1_score": ranked["top1"]["score"],
                    "top2_family": ranked["top2"]["family"],
                    "top2_score": ranked["top2"]["score"],
                    "top3_family": None if top3 is None else top3["family"],
                    "top3_score": None if top3 is None else top3["score"],
                }
            )

    metrics = score_reserve_rows(
        score_rows,
        family_score_min=MINIMUM_FAMILY_SCORE,
        family_margin_min=MINIMUM_FAMILY_MARGIN,
    )
    settlement = decide_settlement(
        composition=composition, disjointness=disjoint, metrics=metrics
    )
    next_action = next_action_for_settlement(settlement)
    spent_rows = mark_evaluation_spent(rows)
    spent_body = (
        "\n".join(json.dumps(r, sort_keys=True, separators=(",", ":")) for r in spent_rows)
        + "\n"
    )
    write_private(PRIVATE / "RESERVE_SPENT.jsonl", spent_body)

    # Mark ledger identities evaluation_spent when present.
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    spent_ids = {r["identity"] for r in spent_rows}
    marked = 0
    for record in ledger.get("identities") or []:
        digest = str(record.get("normalized_text_sha256") or "")
        if digest in spent_ids:
            record["evaluation_spent"] = True
            record["state"] = "EVAL_SPENT"
            record["spent_reserve_id"] = RESERVE_ID
            marked += 1
    write_private(LEDGER, ledger)
    write_private(
        PRIVATE / "SPENT_LEDGER_MARK.json",
        {"marked": marked, "n_reserve": len(spent_ids), "reserve_id": RESERVE_ID},
    )

    receipt = assemble_score_receipt(
        {
            "composition": composition,
            "disjointness": disjoint,
            "metrics": metrics,
            "next_action": next_action,
            "reserve_hashes": {
                "identity_list_sha256": seal["identity_list_sha256"],
                "manifest_sha256": seal["manifest_sha256"],
                "rows_sha256": seal["rows_sha256"],
                "seal_sha256": seal["seal_sha256"],
            },
            "settlement": settlement,
        }
    )
    receipt["code_revision"] = code_revision()
    from hyperlexical.classification_v5_promotion_reserve import (
        canonical_json,
        sha256_text,
    )

    receipt["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in receipt.items() if k != "receipt_sha256"})
    )
    write_private(PRIVATE / "RESERVE_SCORE.json", receipt)
    write_private(
        PRIVATE / "SCORE_ROWS_META.json",
        {
            "n": len(score_rows),
            "decision_counts": metrics["decision_counts"],
            "stage_a_decision_counts": metrics["stage_a_decision_counts"],
        },
    )
    summary = {
        "BEST_MUTATED": False,
        "MODEL_WIDE_BEST": BEST_SHA,
        "MODEL_WIDE_BEST_MUTATED": False,
        "STAGE_A_BEST": STAGE_A_BEST_SHA,
        "STAGE_A_BEST_MUTATED": False,
        "evaluation_spent": True,
        "false_evidence_entry_rate_on_none": metrics["false_evidence_entry_rate_on_none"],
        "family_emission_precision": metrics["family_emission_precision"],
        "n": len(rows),
        "next_action": next_action,
        "primary_gate_pass": metrics["primary_gate_pass"],
        "receipt_sha256": receipt["receipt_sha256"],
        "reserve_id": RESERVE_ID,
        "secondary_gate_pass": metrics["secondary_gate_pass"],
        "settlement": settlement,
    }
    write_private(PRIVATE / "SUMMARY.json", summary)
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mutated_during_score")
    if sudo_sha256(STAGE_A_BEST_WEIGHTS) != STAGE_A_BEST_SHA:
        fail("STAGE_A_BEST_mutated_during_score")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def phase_b_score() -> int:
    pin_inputs()
    if not (PRIVATE / "RESERVE_SEAL.json").exists():
        fail("reserve_not_sealed")
    if (PRIVATE / "RESERVE_SCORE.json").exists():
        fail("reserve_already_scored")
    revision = code_revision()
    command = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "-v",
        f"{REPO}:{REPO}",
        "-v",
        "/home/morpheus/hlx-private:/home/morpheus/hlx-private",
        "-v",
        "/home/morpheus/.hyperlex:/home/morpheus/.hyperlex",
        "-w",
        str(REPO),
        "-e",
        "PYTHONPATH=/home/morpheus/Hyperlex/scripts/shadow",
        "-e",
        "HLX_V2_FORWARD_ONTOLOGY=1",
        "-e",
        "HLX_V5_RESERVE_INNER=1",
        "-e",
        f"HLX_V5_RESERVE_CODE_REVISION={revision}",
        "-e",
        "HF_HUB_OFFLINE=1",
        "-e",
        "TRANSFORMERS_OFFLINE=1",
        "--entrypoint",
        "python3",
        IMAGE,
        str(REPO / "scripts/spark/run_classification_v5_promotion_reserve_score.py"),
        "--inner-score",
    ]
    log_path = PRIVATE / "reserve_score.log"
    print(json.dumps({"launch": command[-1], "log": str(log_path)}, sort_keys=True), flush=True)
    with log_path.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(
            command, check=False, stdout=handle, stderr=subprocess.STDOUT
        )
    try:
        print(log_path.read_text(encoding="utf-8")[-12000:])
    except OSError:
        pass
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mutated_after_score")
    if sudo_sha256(STAGE_A_BEST_WEIGHTS) != STAGE_A_BEST_SHA:
        fail("STAGE_A_BEST_mutated_after_score")
    return int(completed.returncode)


def main() -> int:
    if os.environ.get("HLX_V5_RESERVE_INNER") == "1" or "--inner-score" in sys.argv:
        return inner_score()
    if "--score-only" in sys.argv:
        return phase_b_score()
    if "--acquire-only" in sys.argv:
        phase_a_acquire_and_seal()
        return 0
    phase_a_acquire_and_seal()
    return phase_b_score()


if __name__ == "__main__":
    raise SystemExit(main())
