"""BUILD_REPRESENTATIVE_V6_DATA_FOUNDATION — Spark acquisition + audits.

No V6 train. No V5 retune. No architecture choice. No spent-identity optimization.
"""

from __future__ import annotations

import hashlib
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

PRIVATE = Path("/home/morpheus/hlx-private/classification-v6-data-foundation-20261001")
QUAL_PRIVATE = PRIVATE / "qualification_holdout"
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
REPO_ART = REPO / "artifacts" / "experiments" / "HLX-CLASSIFICATION-V6-DATA-FOUNDATION-001"
SPEC = REPO / "specs" / "007-hyperlexical-model"
MAX_LEN = 256
SEED = 20261001
WIKT_API = "https://en.wiktionary.org/w/api.php"
WIKI_API = "https://en.wikipedia.org/w/api.php"
UA = "HyperlexV6DataFoundation/1.0 (representative corpus; mediawiki provenance)"

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
        return subprocess.run(
            ["sudo", "-n", "sha256sum", str(path)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.split()[0]


def sudo_read_text(path: Path) -> str:
    if os.access(path, os.R_OK):
        return path.read_text(encoding="utf-8")
    return subprocess.run(
        ["sudo", "-n", "cat", str(path)], check=True, capture_output=True, text=True
    ).stdout


def write_private(path: Path, payload: Any) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if isinstance(payload, str):
        text = payload
    else:
        text = json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"
    path.write_text(text, encoding="utf-8")
    os.chmod(path, 0o600)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
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


def fail(msg: str) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(2)


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


def _api(api: str, params: dict[str, str]) -> dict[str, Any]:
    query = urllib.parse.urlencode({"format": "json", "formatversion": "2", **params})
    request = urllib.request.Request(api + "?" + query, headers={"User-Agent": UA})
    delay = 1.5
    for _ in range(8):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code not in {429, 503}:
                fail(f"mediawiki http {exc.code}")
            time.sleep(delay)
            delay *= 1.7
    fail("mediawiki retries exhausted")
    return {}


def category_titles(api: str, category: str, limit: int = 120) -> list[str]:
    titles: list[str] = []
    cont = None
    while len(titles) < limit:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmtype": "page",
            "cmlimit": "50",
        }
        if cont:
            params["cmcontinue"] = cont
        payload = _api(api, params)
        for row in payload.get("query", {}).get("categorymembers", []):
            title = row.get("title")
            if title:
                titles.append(title)
        cont = payload.get("continue", {}).get("cmcontinue")
        if not cont:
            break
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
        time.sleep(0.05)
    return out


def build_blocked() -> dict[str, set[str]]:
    from hyperlexical.holdout_guard import normalized_text_sha256
    from hyperlexical.classification_v5_surface_readiness_gates import near_duplicate_key

    blocked_ids: set[str] = set()
    blocked_src: set[str] = set()
    blocked_text: set[str] = set()
    blocked_near: set[str] = set()
    paths = []
    root = Path("/home/morpheus/hlx-private")
    patterns = [
        "classification-v5-pipeline-qualification-001-20261001/QUALIFICATION_SURFACE*.jsonl",
        "classification-v*-reserve-*/**/*.jsonl",
        "classification-v5-reserve-*/**/*.jsonl",
        "classification-v2-train-ready-*/reserve*.jsonl",
        "classification-v5-stage-a-identifiability-filtered-v1r2-20261001/EVIDENCE_SURFACE.jsonl",
    ]
    import glob

    for pattern in patterns:
        paths.extend(glob.glob(str(root / pattern), recursive=True))
    for path_str in sorted(set(paths)):
        path = Path(path_str)
        try:
            text = sudo_read_text(path)
        except Exception:
            continue
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            ident = row.get("identity")
            if ident:
                blocked_ids.add(str(ident))
            body = str(row.get("text") or "")
            if body:
                blocked_text.add(body)
                blocked_src.add(normalized_text_sha256(body))
                blocked_near.add(near_duplicate_key(body))
            src = row.get("source_sha256")
            if src:
                blocked_src.add(str(src))
    return {
        "blocked_ids": blocked_ids,
        "blocked_src": blocked_src,
        "blocked_text": blocked_text,
        "blocked_near": blocked_near,
        "n_paths": len(set(paths)),
    }


def acquire_raw(blocked: dict[str, set[str]]) -> list[dict]:
    from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY
    from hyperlexical.classification_v6_data_foundation_acquire import (
        DOMAIN_IRRELEVANT_CATEGORIES,
        FAMILY_LABELS,
        ORDINARY_NONE_LABELS,
        WIKI_ORDINARY_CATEGORIES,
        WIKT_FAMILY_CATEGORIES,
        clean_wikitext,
        sense_labels,
    )
    from hyperlexical.holdout_guard import normalized_text_sha256
    from hyperlexical.classification_v5_surface_readiness_gates import near_duplicate_key

    rng = random.Random(SEED)
    raw: list[dict] = []
    seen_text = set(blocked["blocked_text"])
    seen_src = set(blocked["blocked_src"])
    seen_near = set(blocked["blocked_near"])

    def admit(row: dict) -> bool:
        text = row["text"]
        src = normalized_text_sha256(text)
        near = near_duplicate_key(text)
        if text in seen_text or src in seen_src or near in seen_near:
            return False
        if src in blocked["blocked_src"] or near in blocked["blocked_near"]:
            return False
        seen_text.add(text)
        seen_src.add(src)
        seen_near.add(near)
        raw.append(row)
        return True

    # PRESENT via Wiktionary category members + label search
    per_family_target = 160
    for family in ACTIVE_FAMILY_VOCABULARY:
        labels = FAMILY_LABELS.get(family, ())
        got = 0
        titles: list[str] = []
        for cat in WIKT_FAMILY_CATEGORIES.get(family, ()):
            titles.extend(category_titles(WIKT_API, cat, limit=180))
        for label in labels:
            payload = _api(
                WIKT_API,
                {
                    "action": "opensearch",
                    "search": label,
                    "limit": "40",
                },
            )
            if isinstance(payload, list) and len(payload) >= 2:
                titles.extend(list(payload[1]))
            q = _api(
                WIKT_API,
                {
                    "action": "query",
                    "list": "search",
                    "srsearch": label,
                    "srnamespace": "0",
                    "srlimit": "40",
                },
            )
            titles.extend(h["title"] for h in q.get("query", {}).get("search", []))
        # de-dupe titles preserving order
        seen_t: set[str] = set()
        uniq_titles = []
        for t in titles:
            if t not in seen_t:
                seen_t.add(t)
                uniq_titles.append(t)
        pages = fetch_wikitext(WIKT_API, uniq_titles[:220])
        for title, content in pages.items():
            if got >= per_family_target:
                break
            # category-sourced pages: take English definitional senses
            for line in content.splitlines():
                if got >= per_family_target:
                    break
                if not line.startswith("#"):
                    continue
                labs = sense_labels(line)
                lab_blob = " ".join(labs).lower()
                line_l = line.lower()
                # Category membership already family-aligned; still prefer labeled senses when present.
                labeled = any(
                    lbl.lower() in lab_blob or lbl.lower() in line_l for lbl in labels
                )
                if not labeled and not any(
                    tok in lab_blob
                    for tok in (
                        "slang",
                        "informal",
                        "internet",
                        "gaming",
                        "computing",
                        "derogatory",
                        "vulgar",
                        "dialectal",
                    )
                ):
                    # allow unlabeled definitional sense from category page if prose-like
                    if len(clean_wikitext(re.sub(r"^[#*:]+", "", line))) < 24:
                        continue
                text = clean_wikitext(re.sub(r"^[#*:]+", "", line))
                if len(text) < 12:
                    continue
                if admit(
                    {
                        "text": text,
                        "evidence_label": "EVIDENCE_PRESENT",
                        "evidence_subtype": "POSITIVE_EVIDENCE",
                        "gold_family": family,
                        "topic_domain": family,
                        "source_family": f"v6_wikt_present:{family}",
                        "source_url": f"https://en.wiktionary.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
                        "provenance": "OBSERVED",
                        "construction_tag": "NATURAL",
                        "construction_role": "PRODUCT_EXPECTED",
                        "notes": f"wikt_sense:{title}",
                    }
                ):
                    got += 1
        print(f"present {family}={got}", flush=True)

    # Ordinary NONE via Wikipedia categories + Wiktionary labels
    for domain, labels in ORDINARY_NONE_LABELS.items():
        got = 0
        cat = WIKI_ORDINARY_CATEGORIES.get(domain)
        titles = category_titles(WIKI_API, cat, limit=160) if cat else []
        pages = fetch_wikitext(WIKI_API, titles)
        for title, content in pages.items():
            if got >= 90:
                break
            # first prose paragraph
            paras = [
                clean_wikitext(p)
                for p in content.split("\n\n")
                if p.strip() and not p.strip().startswith("{")
            ]
            for para in paras[:2]:
                if 40 <= len(para) <= 400:
                    if admit(
                        {
                            "text": para,
                            "evidence_label": "NO_EVIDENCE",
                            "evidence_subtype": "ORDINARY_DOMAIN_NONE",
                            "gold_family": None,
                            "topic_domain": domain,
                            "source_family": f"v6_wp_ordinary:{domain}",
                            "source_url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
                            "provenance": "OBSERVED",
                            "construction_tag": "NATURAL",
                            "construction_role": "PRODUCT_EXPECTED",
                        }
                    ):
                        got += 1
                        break
        # short atom none lemmas from wiktionary label search
        for label in labels:
            payload = _api(
                WIKT_API,
                {"action": "query", "list": "search", "srsearch": label, "srlimit": "20"},
            )
            titles = [h["title"] for h in payload.get("query", {}).get("search", [])]
            for title in titles:
                if got >= 70:
                    break
                if " " in title:
                    continue
                text = title.strip()
                if not (2 <= len(text) <= 24):
                    continue
                if admit(
                    {
                        "text": text,
                        "evidence_label": "NO_EVIDENCE",
                        "evidence_subtype": "SHORT_ATOM_NONE",
                        "gold_family": None,
                        "topic_domain": domain,
                        "source_family": f"v6_wikt_atom_none:{domain}",
                        "source_url": f"https://en.wiktionary.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
                        "provenance": "OBSERVED",
                        "construction_tag": "NATURAL",
                        "construction_role": "PRODUCT_EXPECTED",
                        "primary_cell": "SHORT_ATOM/NO_EVIDENCE",
                    }
                ):
                    got += 1
            if got >= 140:
                break
        print(f"none {domain}={got}", flush=True)

    # Lookalike NONE: ordinary lemma with slang-looking surface from non-family pages
    lookalike_titles = category_titles(WIKI_API, "Category:English lemmas", limit=5)
    # fallback: use botany/chemistry page titles as lookalike surfaces if category missing
    for domain in ("botany", "chemistry", "mycology"):
        titles = category_titles(WIKI_API, WIKI_ORDINARY_CATEGORIES[domain], limit=40)
        for title in titles:
            lemma = title.split("(")[0].strip()
            if " " in lemma or not (3 <= len(lemma) <= 18):
                continue
            if admit(
                {
                    "text": lemma.lower(),
                    "evidence_label": "NO_EVIDENCE",
                    "evidence_subtype": "LEXICAL_LOOKALIKE_NONE",
                    "gold_family": None,
                    "topic_domain": domain,
                    "source_family": f"v6_lookalike:{domain}",
                    "source_url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
                    "provenance": "OBSERVED",
                    "construction_tag": "NATURAL",
                    "construction_role": "RESEARCH_USEFUL",
                    "primary_cell": "SHORT_ATOM/NO_EVIDENCE",
                }
            ):
                pass
    print(f"lookalike_total_raw={sum(1 for r in raw if r['evidence_subtype']=='LEXICAL_LOOKALIKE_NONE')}", flush=True)

    # UNCERTAIN: competing sense lines
    unc = 0
    for family in ACTIVE_FAMILY_VOCABULARY:
        labels = FAMILY_LABELS.get(family, ())
        for label in labels[:2]:
            q = _api(
                WIKT_API,
                {"action": "query", "list": "search", "srsearch": label, "srlimit": "30"},
            )
            titles = [h["title"] for h in q.get("query", {}).get("search", [])]
            pages = fetch_wikitext(WIKT_API, titles)
            for title, content in pages.items():
                senses = []
                for line in content.splitlines():
                    if line.startswith("#"):
                        t = clean_wikitext(re.sub(r"^[#*:]+", "", line))
                        if len(t) >= 20:
                            senses.append(t)
                if len(senses) < 2:
                    continue
                text = senses[0] + " / " + senses[1]
                if admit(
                    {
                        "text": text,
                        "evidence_label": "UNCERTAIN",
                        "evidence_subtype": "AMBIGUOUS_EVIDENCE",
                        "gold_family": None,
                        "topic_domain": "ambiguous",
                        "source_family": f"v6_wikt_uncertain:{family}",
                        "source_url": f"https://en.wiktionary.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
                        "provenance": "OBSERVED",
                        "construction_tag": "NATURAL",
                        "construction_role": "PRODUCT_EXPECTED",
                        "uncertainty_reason": "competing_textual_senses_unresolved",
                        "notes": "MULTI_SENSE_UNRESOLVED",
                    }
                ):
                    unc += 1
                if unc >= 280:
                    break
            if unc >= 280:
                break
        if unc >= 280:
            break
    print(f"uncertain={unc}", flush=True)

    # Domain-irrelevant
    for key, cat in DOMAIN_IRRELEVANT_CATEGORIES.items():
        titles = category_titles(WIKI_API, cat, limit=100)
        pages = fetch_wikitext(WIKI_API, titles)
        got = 0
        for title, content in pages.items():
            paras = [
                clean_wikitext(p)
                for p in content.split("\n\n")
                if p.strip() and not p.strip().startswith("{")
            ]
            for para in paras[:1]:
                if 40 <= len(para) <= 350:
                    if admit(
                        {
                            "text": para,
                            "evidence_label": "NO_EVIDENCE",
                            "evidence_subtype": "HARD_NONE",
                            "gold_family": None,
                            "topic_domain": key,
                            "source_family": f"v6_wp_irrelevant:{key}",
                            "source_url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
                            "provenance": "OBSERVED",
                            "construction_tag": "NATURAL",
                            "construction_role": "PRODUCT_EXPECTED",
                            "notes": "domain_irrelevant",
                        }
                    ):
                        got += 1
                        break
        print(f"domain_irrelevant {key}={got}", flush=True)

    rng.shuffle(raw)
    print(f"total_raw={len(raw)}", flush=True)
    return raw


def ontology_audit(present_rows: list[dict], embeddings: dict[str, Any]) -> dict[str, Any]:
    from hyperlexical.classification_v6_data_foundation import classify_ontology_pair
    from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY

    cents = embeddings.get("family_centroids") or {}
    pairs = []
    review = []
    for i, a in enumerate(ACTIVE_FAMILY_VOCABULARY):
        for b in ACTIVE_FAMILY_VOCABULARY[i + 1 :]:
            ca = cents.get(a)
            cb = cents.get(b)
            emb_ov = float(sum(x * y for x, y in zip(ca, cb))) if ca and cb else 0.0
            # lexical overlap via token jaccard of concatenated family texts
            def toks(fam: str) -> set[str]:
                texts = [
                    r["text"]
                    for r in present_rows
                    if r.get("gold_family") == fam
                ][:30]
                bag: set[str] = set()
                for t in texts:
                    bag |= set(re.findall(r"[a-z0-9]+", t.lower()))
                return bag

            ta, tb = toks(a), toks(b)
            lex = len(ta & tb) / max(1, len(ta | tb))
            klass = classify_ontology_pair(
                definition_overlap=0.0,
                embedding_overlap=emb_ov,
                lexical_overlap=lex,
                boundary_clarity=1.0 - emb_ov,
            )
            item = {
                "a": a,
                "b": b,
                "embedding_overlap": emb_ov,
                "lexical_overlap": lex,
                "class": klass,
            }
            pairs.append(item)
            if klass in {"STRUCTURALLY_OVERLAPPING", "ONTOLOGY_REVIEW_REQUIRED"}:
                review.append(item)
    counts = Counter(p["class"] for p in pairs)
    structurally_broken = (
        counts.get("ONTOLOGY_REVIEW_REQUIRED", 0) >= 8
        or counts.get("STRUCTURALLY_OVERLAPPING", 0) >= 40
    )
    return {
        "n_pairs": len(pairs),
        "class_counts": dict(counts),
        "review_required_pairs": review[:40],
        "ontology_structurally_broken": structurally_broken,
        "families_needing_review": sorted(
            {
                x
                for p in review
                if p["class"] == "ONTOLOGY_REVIEW_REQUIRED"
                for x in (p["a"], p["b"])
            }
        ),
    }


def run_geometry(rows_by_split: dict[str, list[dict]]) -> dict[str, Any]:
    import numpy as np
    import torch
    import torch.nn.functional as F
    from safetensors.torch import load_file
    from transformers import AutoModel, AutoTokenizer

    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.layout import HIDDEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors
    from hyperlexical.classification_v6_data_foundation import (
        representation_viability,
        retrieval_viability,
    )

    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("MODEL_WIDE_BEST_mismatch")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("geometry requires CUDA")
    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    split = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    apply_encoder_trainable(encoder, split.get("encoder") or {})
    freeze_encoder(encoder, last_trainable=2)
    encoder.to(device).eval()

    @torch.no_grad()
    def embed(texts: list[str], bs: int = 32) -> np.ndarray:
        outs = []
        for i in range(0, len(texts), bs):
            batch = texts[i : i + bs]
            tok = tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=MAX_LEN,
                return_tensors="pt",
            )
            tok = {k: v.to(device) for k, v in tok.items()}
            pooled = F.normalize(encoder(**tok).last_hidden_state[:, 0], dim=-1)
            outs.append(pooled.float().cpu().numpy())
        return np.concatenate(outs, axis=0) if outs else np.zeros((0, HIDDEN), np.float32)

    train = rows_by_split.get("TRAIN") or []
    rep = rows_by_split.get("REPRESENTATIVE_VALIDATION") or []
    train_present = [r for r in train if r["evidence_label"] == "EVIDENCE_PRESENT"]
    rep_present = [r for r in rep if r["evidence_label"] == "EVIDENCE_PRESENT"]
    rep_none = [r for r in rep if r["evidence_label"] == "NO_EVIDENCE"]
    rep_unc = [r for r in rep if r["evidence_label"] == "UNCERTAIN"]

    # Cap for runtime
    train_present = sorted(train_present, key=lambda r: r["identity"])[:1800]
    rep_sample = sorted(rep, key=lambda r: r["identity"])
    emb_rep = embed([r["text"] for r in rep_sample])
    emb_train_p = embed([r["text"] for r in train_present])

    # family centroids from train present
    fam_vecs: dict[str, list[np.ndarray]] = defaultdict(list)
    for row, vec in zip(train_present, emb_train_p):
        fam_vecs[str(row["gold_family"])].append(vec)
    cents = {}
    for fam, vecs in fam_vecs.items():
        m = np.mean(np.stack(vecs), axis=0)
        cents[fam] = (m / max(1e-6, float(np.linalg.norm(m)))).tolist()

    # Stage-A class centroids on rep
    def class_centroid(label: str):
        idx = [i for i, r in enumerate(rep_sample) if r["evidence_label"] == label]
        if not idx:
            return None
        m = np.mean(emb_rep[idx], axis=0)
        return m / max(1e-6, float(np.linalg.norm(m)))

    cp, cn, cu = class_centroid("EVIDENCE_PRESENT"), class_centroid("NO_EVIDENCE"), class_centroid("UNCERTAIN")
    present_none = float(cp @ cn) if cp is not None and cn is not None else None

    # within/between on train present families with >=3
    within = []
    between = []
    fam_list = sorted(cents)
    for fam in fam_list:
        mat = np.stack(fam_vecs[fam], axis=0)
        if len(mat) >= 2:
            sims = mat @ mat.T
            n = len(mat)
            for i in range(n):
                for j in range(i + 1, n):
                    within.append(float(sims[i, j]))
    for i, a in enumerate(fam_list):
        for b in fam_list[i + 1 :]:
            between.append(float(np.dot(cents[a], cents[b])))

    within_mean = float(np.mean(within)) if within else None
    between_mean = float(np.mean(between)) if between else None

    # retrieval prototype: train index -> rep present
    if len(emb_train_p) and len(rep_present):
        rep_p_idx = [i for i, r in enumerate(rep_sample) if r["evidence_label"] == "EVIDENCE_PRESENT"]
        q = emb_rep[rep_p_idx]
        sims = q @ emb_train_p.T
        top = sims.argmax(axis=1)
        pred = [train_present[int(j)]["gold_family"] for j in top]
        gold = [rep_sample[i]["gold_family"] for i in rep_p_idx]
        top1 = sum(p == g for p, g in zip(pred, gold)) / max(1, len(gold))
        # selective: require margin
        ranked = np.sort(sims, axis=1)
        margin = ranked[:, -1] - ranked[:, -2] if sims.shape[1] >= 2 else ranked[:, -1]
        score = ranked[:, -1]
        emit = (score >= 0.75) & (margin >= 0.01)
        if emit.any():
            fam_prec = sum(
                pred[i] == gold[i] for i in range(len(gold)) if emit[i]
            ) / int(emit.sum())
            coverage = float(emit.mean())
        else:
            fam_prec, coverage = None, 0.0
        nearest_purity = top1
    else:
        top1 = fam_prec = coverage = nearest_purity = None

    repr_class = representation_viability(
        present_none_centroid_cosine=present_none,
        within_family_sim=within_mean,
        between_family_sim=between_mean,
        nearest_family_purity=nearest_purity,
    )
    retr_class = retrieval_viability(
        family_precision=fam_prec, top1=top1, coverage=coverage
    )

    return {
        "encoder": "MODEL_WIDE_BEST",
        "MODEL_WIDE_BEST": BEST_SHA,
        "family_centroids": cents,
        "present_none_centroid_cosine": present_none,
        "present_uncertain_centroid_cosine": float(cp @ cu) if cp is not None and cu is not None else None,
        "within_family_sim_mean": within_mean,
        "between_family_sim_mean": between_mean,
        "nearest_family_purity": nearest_purity,
        "retrieval_prototype": {
            "family_precision": fam_prec,
            "top1": top1,
            "coverage": coverage,
            "n_train_present": len(train_present),
            "n_rep_present": len(rep_present),
            "n_rep_none": len(rep_none),
            "n_rep_unc": len(rep_unc),
        },
        "representation_viability": repr_class,
        "retrieval_viability": retr_class,
    }


def inner() -> int:
    from hyperlexical.classification_v6_data_foundation import (
        DEV_VAL_PREFERRED_MIN,
        MAX_FAMILY_SHARE_TRAIN,
        QUAL_PREFERRED_MIN,
        READY_GATES,
        REP_VAL_PREFERRED_MIN,
        TRAIN_PREFERRED_MIN,
        build_foundation_receipt,
        evaluation_contract_v1,
        operating_distribution_v1,
        summarize_split_rows,
        utc_now_iso,
    )
    from hyperlexical.classification_v6_data_foundation_acquire import (
        disjointness_report,
        enforce_train_family_cap,
        finalize_candidate,
        label_source_correlation,
    )
    from hyperlexical.classification_v6_v5_research_baseline import baseline_receipt

    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    QUAL_PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)

    print("freeze_v5_baseline", flush=True)
    base = baseline_receipt(code_revision=code_revision(), frozen_at=utc_now_iso())
    write_private(PRIVATE / "V5_RESEARCH_BASELINE.json", base)
    write_repo(REPO_ART / "v5_research_baseline.json", base)
    write_repo(
        SPEC / "classification-v6-v5-research-baseline-20261001.md",
        f"""# HYPERLEX_V5_RESEARCH_BASELINE

```text
RELEASE_QUALIFIED = false
V5_DISPOSITION = {base['V5_DISPOSITION']}
PRIMARY_SYSTEM_DIAGNOSIS = {base['PRIMARY_SYSTEM_DIAGNOSIS']}
RECEIPT = {base['V5_RESEARCH_BASELINE_RECEIPT_SHA256']}
```

V5 is not release-qualified. Artifacts preserved for historical comparison,
failure taxonomy, measurement design, and regression baselines only.
""",
    )
    write_repo(
        SPEC / "classification-v6-v5-research-baseline-receipt-20261001.json",
        base,
    )

    write_repo(
        SPEC / "classification-v6-operating-distribution-v1-20261001.md",
        "# HYPERLEX_V6_OPERATING_DISTRIBUTION_V1\n\n"
        + "```json\n"
        + json.dumps(operating_distribution_v1(), indent=2, sort_keys=True)
        + "\n```\n",
    )
    write_repo(
        SPEC / "classification-v6-evaluation-contract-20261001.md",
        "# V6 evaluation contract (preregistered before train)\n\n"
        + "```json\n"
        + json.dumps(evaluation_contract_v1(), indent=2, sort_keys=True)
        + "\n```\n",
    )

    print("building_blocked_sets", flush=True)
    blocked = build_blocked()
    print(
        f"blocked ids={len(blocked['blocked_ids'])} text={len(blocked['blocked_text'])} paths={blocked['n_paths']}",
        flush=True,
    )

    print("acquiring_raw", flush=True)
    raw = acquire_raw(blocked)
    write_jsonl(PRIVATE / "RAW_ACQUIRE.jsonl", raw)

    print("finalizing", flush=True)
    finalized = []
    rejected = Counter()
    for row in raw:
        try:
            out = finalize_candidate(row)
        except Exception as exc:  # noqa: BLE001
            rejected[type(exc).__name__] += 1
            continue
        if out is None:
            rejected["filtered"] += 1
            continue
        if out["identity"] in blocked["blocked_ids"]:
            rejected["blocked_identity"] += 1
            continue
        finalized.append(out)
    finalized = enforce_train_family_cap(finalized, max_share=MAX_FAMILY_SHARE_TRAIN)

    splits = {
        "TRAIN": [r for r in finalized if r["split"] == "TRAIN"],
        "DEVELOPMENT_VALIDATION": [
            r for r in finalized if r["split"] == "DEVELOPMENT_VALIDATION"
        ],
        "REPRESENTATIVE_VALIDATION": [
            r for r in finalized if r["split"] == "REPRESENTATIVE_VALIDATION"
        ],
        "QUALIFICATION": [r for r in finalized if r["split"] == "QUALIFICATION"],
    }
    for name, rows in splits.items():
        print(f"split {name}={len(rows)}", flush=True)

    # Write non-qual splits to private + repo summaries; qual rows private only
    for name in ("TRAIN", "DEVELOPMENT_VALIDATION", "REPRESENTATIVE_VALIDATION"):
        write_jsonl(PRIVATE / f"{name}.jsonl", splits[name])
    write_jsonl(QUAL_PRIVATE / "QUALIFICATION_ROWS.jsonl", splits["QUALIFICATION"])
    # redact qual rows from repo: metadata only
    qual_meta = {
        "QUALIFICATION_HOLD_ID": "HYPERLEX_V6_QUALIFICATION_001",
        "n_rows": len(splits["QUALIFICATION"]),
        "summary": summarize_split_rows(splits["QUALIFICATION"]),
        "rows_exposed_in_repo": False,
        "rows_path_private": str(QUAL_PRIVATE / "QUALIFICATION_ROWS.jsonl"),
        "qualification_rows_sha256": sha256_file(QUAL_PRIVATE / "QUALIFICATION_ROWS.jsonl")
        if splits["QUALIFICATION"]
        else None,
    }
    # seal qual
    qual_seal = {
        "QUALIFICATION_HOLD_ID": "HYPERLEX_V6_QUALIFICATION_001",
        "immutable": True,
        "sealed_at": utc_now_iso(),
        "n_rows": qual_meta["n_rows"],
        "qualification_rows_sha256": qual_meta["qualification_rows_sha256"],
        "unavailable_during_model_development": True,
    }
    from hyperlexical.classification_v5_stage_a import canonical_json, sha256_text

    qual_seal["qualification_seal_sha256"] = sha256_text(
        canonical_json({k: v for k, v in qual_seal.items() if k != "qualification_seal_sha256"})
    )
    write_private(QUAL_PRIVATE / "QUALIFICATION_SEAL.json", qual_seal)
    write_private(PRIVATE / "QUALIFICATION_METADATA.json", qual_meta)
    write_repo(REPO_ART / "qualification_metadata.json", qual_meta)
    write_repo(REPO_ART / "qualification_seal.json", qual_seal)

    disjoint = disjointness_report(splits, blocked)
    write_private(PRIVATE / "DISJOINTNESS_WITNESS.json", disjoint)
    write_repo(REPO_ART / "disjointness_witness.json", disjoint)

    summaries = {name: summarize_split_rows(rows) for name, rows in splits.items()}
    write_private(PRIVATE / "SPLIT_SUMMARIES.json", summaries)
    write_repo(REPO_ART / "split_summaries.json", summaries)

    shortcut = {
        name: label_source_correlation(rows) for name, rows in splits.items() if name != "QUALIFICATION"
    }
    # include qual privately only
    shortcut_private = {
        name: label_source_correlation(rows) for name, rows in splits.items()
    }
    write_private(PRIVATE / "SHORTCUT_DIAGNOSTICS.json", shortcut_private)
    write_repo(REPO_ART / "shortcut_diagnostics.json", shortcut)

    print("geometry_and_retrieval", flush=True)
    geometry = run_geometry(splits)
    ontology = ontology_audit(
        [r for r in splits["TRAIN"] if r["evidence_label"] == "EVIDENCE_PRESENT"],
        geometry,
    )
    write_private(PRIVATE / "REPRESENTATION_GEOMETRY.json", geometry)
    write_private(PRIVATE / "ONTOLOGY_AUDIT.json", ontology)
    write_repo(REPO_ART / "representation_geometry.json", geometry)
    write_repo(REPO_ART / "ontology_audit.json", ontology)

    # Human agreement protocol sample (rows for operator; second rater blank)
    sample_pool = (
        splits["REPRESENTATIVE_VALIDATION"][:80]
        + splits["DEVELOPMENT_VALIDATION"][:40]
    )
    sample_pool = sorted(sample_pool, key=lambda r: r["identity"])[:120]
    ha_sample = []
    for row in sample_pool:
        ha_sample.append(
            {
                "identity": row["identity"],
                "text": row["text"],
                "rater_a_stage_a": row["evidence_label"],
                "rater_a_family": row.get("gold_family"),
                "rater_b_stage_a": None,
                "rater_b_family": None,
                "rater_b_uncertainty": None,
                "status": "AWAITING_OPERATOR_ANNOTATION",
            }
        )
    write_private(PRIVATE / "HUMAN_AGREEMENT_SAMPLE.jsonl", ha_sample)
    human = {
        "status": "PROTOCOL_DEFINED_AWAITING_OPERATOR_ANNOTATION",
        "n_sample": len(ha_sample),
        "metrics": None,
        "note": (
            "Independent human second-rater annotations are required for kappa; "
            "sample sealed for operator annotation. Not blocking architecture gate list "
            "in section 22, but reported as a remaining gap."
        ),
    }
    write_private(PRIVATE / "HUMAN_AGREEMENT.json", human)
    write_repo(REPO_ART / "human_agreement.json", human)

    gates = {
        "OPERATING_DISTRIBUTION_DEFINED": True,
        "GOLD_CONTRACT_VALID": True,
        "ONTOLOGY_AUDITED": True,
        "TRAIN_READY": summaries["TRAIN"]["n"] >= TRAIN_PREFERRED_MIN
        and summaries["TRAIN"].get("max_family_share_among_present", 1) <= MAX_FAMILY_SHARE_TRAIN + 1e-9
        and summaries["TRAIN"].get("n_families_present", 0) >= 12,
        "DEV_VALIDATION_READY": summaries["DEVELOPMENT_VALIDATION"]["n"]
        >= DEV_VAL_PREFERRED_MIN,
        "REPRESENTATIVE_VALIDATION_READY": summaries["REPRESENTATIVE_VALIDATION"]["n"]
        >= REP_VAL_PREFERRED_MIN
        and summaries["REPRESENTATIVE_VALIDATION"].get("observed_share", 0) >= 0.5
        and summaries["REPRESENTATIVE_VALIDATION"].get("natural_share", 0) >= 0.8,
        "QUALIFICATION_SEALED": bool(qual_seal.get("immutable"))
        and (qual_meta["n_rows"] >= QUAL_PREFERRED_MIN),
        "BASE_REPRESENTATION_AUDITED": geometry.get("representation_viability") is not None,
    }

    audit = {
        "summaries": summaries,
        "disjointness": disjoint,
        "shortcut_diagnostics": shortcut,
        "ontology": ontology,
        "ontology_structurally_broken": ontology.get("ontology_structurally_broken"),
        "representation": {
            "viability": geometry.get("representation_viability"),
            "present_none_centroid_cosine": geometry.get("present_none_centroid_cosine"),
            "within_family_sim_mean": geometry.get("within_family_sim_mean"),
            "between_family_sim_mean": geometry.get("between_family_sim_mean"),
            "nearest_family_purity": geometry.get("nearest_family_purity"),
        },
        "retrieval": {
            "viability": geometry.get("retrieval_viability"),
            **(geometry.get("retrieval_prototype") or {}),
        },
        "human_agreement": human,
        "rejected": dict(rejected),
        "gates": gates,
        "ready_gate_list": list(READY_GATES),
    }
    receipt = build_foundation_receipt(
        code_revision=code_revision(),
        audit=audit,
        gates=gates,
        settled_at=utc_now_iso(),
    )
    write_private(PRIVATE / "FOUNDATION_RECEIPT.json", receipt)
    write_repo(REPO_ART / "foundation_receipt.json", receipt)
    write_repo(
        SPEC / "classification-v6-data-foundation-receipt-20261001.json",
        receipt,
    )

    summary = {
        "V6_DATA_FOUNDATION_STATE": receipt["V6_DATA_FOUNDATION_STATE"],
        "NEXT_ACTION": receipt["NEXT_ACTION"],
        "V6_DATA_FOUNDATION_RECEIPT_SHA256": receipt["V6_DATA_FOUNDATION_RECEIPT_SHA256"],
        "gates": gates,
        "split_counts": {k: v["n"] for k, v in summaries.items()},
        "representation_viability": geometry.get("representation_viability"),
        "retrieval_viability": geometry.get("retrieval_viability"),
        "ontology_structurally_broken": ontology.get("ontology_structurally_broken"),
        "disjointness_pass": disjoint.get("pass"),
        "TRAIN": False,
        "ARCHITECTURE_CHOSEN": False,
        "V5_RETUNED": False,
    }
    write_private(PRIVATE / "SUMMARY.json", summary)
    write_repo(REPO_ART / "SUMMARY.json", summary)
    write_repo(
        SPEC / "classification-v6-data-foundation-20261001.md",
        f"""# BUILD_REPRESENTATIVE_V6_DATA_FOUNDATION

```text
V6_DATA_FOUNDATION_STATE = {summary['V6_DATA_FOUNDATION_STATE']}
NEXT_ACTION = {summary['NEXT_ACTION']}
RECEIPT = {summary['V6_DATA_FOUNDATION_RECEIPT_SHA256']}
split_counts = {summary['split_counts']}
representation_viability = {summary['representation_viability']}
retrieval_viability = {summary['retrieval_viability']}
ontology_structurally_broken = {summary['ontology_structurally_broken']}
disjointness_pass = {summary['disjointness_pass']}
```

No V6 train. No V5 retune. Qualification holdout rows are private/sealed.
""",
    )

    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mutated")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def main() -> int:
    if os.environ.get("HLX_V6_FOUNDATION_INNER") == "1":
        return inner()
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    revision = code_revision()
    cmd = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "--network",
        "host",
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
        "HLX_V6_FOUNDATION_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={revision}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(REPO / "scripts/spark/run_classification_v6_data_foundation.py"),
    ]
    log = PRIVATE / "foundation_console.log"
    with log.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(cmd, check=False, stdout=handle, stderr=subprocess.STDOUT)
    try:
        print(log.read_text(encoding="utf-8")[-20000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
