"""Execute and seal mixed-remediation phases A–D.

Acquires prose train definitions for sparse families, records noise/boundary/
ontology decisions, rebuilds a remediation surface overlay, and re-runs the
separability audit. Does not train, score the reserve, or move BEST.
"""

from __future__ import annotations

import hashlib
import json
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

REPO = Path("/home/morpheus/Hyperlex")
EXPORT = Path("/home/morpheus/hlx-private/classification-v2-surface-20260929/civilian.v0.3.jsonl")
EXPORT_SHA = "c4677011ea61f135c8fb82bed9d973dffe3a5db582d34421403e71498c5fd243"
AUDIT = Path(
    "/home/morpheus/hlx-private/classification-v2-separability-audit-20260930/SEPARABILITY_AUDIT.json"
)
AUDIT_SHA = "2cb2fe2459a86323dfa8aa50136bb8e6822598ffd8895a1988af459949853d5f"
REMEDIATION = Path(
    "/home/morpheus/hlx-private/classification-v2-mixed-remediation-20260930/MIXED_REMEDIATION.json"
)
REMEDIATION_SHA = "d1292e106ae674d16967d85486133c912390de8afeb2ae5fcf977dd69cac1e00"
BOUNDARIES = Path(
    "/home/morpheus/hlx-private/classification-v2-boundaries-20260930/FAMILY_SEMANTIC_BOUNDARIES.json"
)
BOUNDARY_SHA = "0ca6f34ce1abf68388e443371672ca36e16028079a175b6775e1968900e1c52f"
SEPARATION_SHA = "ab698d342d2d276f81d4baf3fed609bb6f8bf88cd6810bb1d1998c5e409f63c3"
REPAIR = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-classification-v2-geometry-repair"
)
REPAIR_SHA = "449bf3b303c95bc5d6b7d87173d50315616556c1379057414b970f3e5f0b18cf"
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
DEST = Path("/home/morpheus/hlx-private/classification-v2-phase-execution-20260930")
BATCH_ID = "HLX-CLASSIFICATION-V2-PHASE-EXECUTION-20260930"
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
API = "https://en.wiktionary.org/w/api.php"
UA = "HyperlexClassificationV2PhaseA/1.0 (sparse definition acquire; mediawiki provenance)"
MAX_TITLES = 200
PAUSE = 2.5
TARGET = 12

sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sha256_file(path: Path) -> str:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except PermissionError:
        return subprocess.check_output(["sudo", "sha256sum", str(path)], text=True).split()[0]


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def _api(params: dict[str, str]) -> dict[str, Any]:
    query = dict(params)
    query["format"] = "json"
    query["formatversion"] = "2"
    url = API + "?" + urllib.parse.urlencode(query)
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < 4:
                time.sleep(45 + attempt * 30)
                continue
            raise
        except TimeoutError:
            if attempt < 4:
                time.sleep(15 + attempt * 10)
                continue
            raise
        finally:
            time.sleep(PAUSE)


def _search(phrase: str, *, gloss: bool) -> list[str]:
    if gloss:
        query = 'insource:"' + phrase + '"'
    else:
        query = 'insource:"{{lb|en|' + phrase + '}}"'
    titles: list[str] = []
    offset = 0
    while len(titles) < MAX_TITLES:
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
            if title and ":" not in title:
                titles.append(title)
            if len(titles) >= MAX_TITLES:
                break
        if not payload.get("continue"):
            break
        offset += 20
    return titles


def _category_titles(category: str) -> list[str]:
    titles: list[str] = []
    cont = None
    while len(titles) < MAX_TITLES:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmnamespace": "0",
            "cmlimit": "50",
        }
        if cont:
            params["cmcontinue"] = cont
        payload = _api(params)
        for item in payload.get("query", {}).get("categorymembers", []):
            title = str(item.get("title") or "")
            if title and ":" not in title:
                titles.append(title)
            if len(titles) >= MAX_TITLES:
                break
        cont = (payload.get("continue") or {}).get("cmcontinue")
        if not cont:
            break
    return titles


def _fetch(titles: list[str]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for start in range(0, len(titles), 8):
        batch = titles[start : start + 8]
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
            if not isinstance(content, str) or not isinstance(revid, int) or not sha1 or not timestamp:
                continue
            found[title] = {
                "content": content,
                "revision_id": revid,
                "revision_sha1": sha1,
                "revision_timestamp": timestamp,
            }
    return found


_SENSE_LABEL = re.compile(
    r"\{\{\s*(lb|lbl|tlb)\s*\|\s*en\s*\|([^{}]*)\}\}",
    re.IGNORECASE,
)
_LINK = re.compile(r"\[\[([^|\]]+\|)?([^\]]+)\]\]")
_MARKUP = re.compile(r"''+")
_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")


def _normalize_label(text: str) -> str:
    return " ".join(str(text or "").casefold().replace("_", " ").split())


def _sense_args(line: str) -> list[str]:
    args: list[str] = []
    for match in _SENSE_LABEL.finditer(line):
        for part in match.group(2).split("|"):
            token = _normalize_label(part)
            if token and token not in {"en", "lb", "lbl", "tlb"}:
                args.append(token)
    return args


def _definition_prose(line: str) -> str:
    body = line[2:] if line.startswith("# ") else line
    body = _SENSE_LABEL.sub("", body)
    body = _LINK.sub(lambda match: match.group(2), body)
    body = _TEMPLATE.sub("", body)
    body = _MARKUP.sub("", body)
    return " ".join(body.split()).strip(" :;-")


def _english_section(wikitext: str) -> str:
    parts = re.split(r"\n(?===[^=])", "\n" + wikitext)
    for part in parts:
        lines = part.strip().splitlines()
        if lines and lines[0].strip("= ").casefold() == "english":
            return part
    return ""


def _match_family(family: str, arguments: list[str], prose: str) -> str | None:
    from hyperlexical.classification_v2_phase_execution import SPARSE_GLOSS, SPARSE_SENSE_LABELS

    labels = {_normalize_label(item) for item in SPARSE_SENSE_LABELS.get(family, ())}
    args = {_normalize_label(item) for item in arguments}
    if labels & args:
        return "sense_label"
    lowered = prose.casefold()
    for phrase in SPARSE_GLOSS.get(family, ()):
        if phrase.casefold() in lowered:
            return "gloss"
    if family == "memetic" and re.search(r"\b(meme|memes|memetic)\b", lowered):
        return "gloss"
    return None


def harvest_sparse(blocked: dict[str, str]) -> dict[str, Any]:
    from hyperlexical.classification_v2_phase_execution import (
        SPARSE_DISCOVERY,
        SPARSE_GLOSS,
        SPARSE_SENSE_LABELS,
        make_train_definition_row,
        _prose_ok,
    )
    from hyperlexical.classification_v2_separability_audit import SPARSE_FOCUS
    from hyperlexical.holdout_guard import normalized_text_sha256

    admitted: dict[str, list[dict[str, Any]]] = {family: [] for family in SPARSE_FOCUS}
    exclusions: Counter[str] = Counter()
    seen_titles: set[str] = set()
    seen_digests: set[str] = set()
    discovered = 0
    fetched = 0
    from hyperlexical.classification_v2_phase_execution import SPARSE_CATEGORIES, SPARSE_SEED_TITLES

    def _consider(family: str, title: str, revision: dict[str, Any]) -> None:
        nonlocal fetched
        if len(admitted[family]) >= TARGET:
            return
        section = _english_section(revision["content"])
        if not section:
            exclusions["no_english"] += 1
            return
        chosen = None
        for line in section.splitlines():
            if not line.startswith("# ") or line.startswith(("#:", "##")):
                continue
            prose = _definition_prose(line)
            if not _prose_ok(family, prose):
                continue
            evidence = _match_family(family, _sense_args(line), prose)
            if evidence is None:
                continue
            # internet-slang requires an explicit sense label; gloss-only is too weak
            if family == "internet-slang" and evidence != "sense_label":
                continue
            collisions = [
                other
                for other in SPARSE_FOCUS
                if other != family and _match_family(other, _sense_args(line), prose)
            ]
            # memetic pages often mention internet slang; allow if sense/gloss is memetic-primary
            if collisions and not (family == "memetic" and evidence in {"sense_label", "gloss"}):
                exclusions["sparse_collision"] += 1
                continue
            if collisions and family == "memetic":
                exclusions["memetic_collision_allowed"] += 1
            chosen = (prose, evidence, _sense_args(line))
            break
        if chosen is None:
            exclusions["no_unique_prose"] += 1
            return
        prose, evidence, sense_labels = chosen
        digest = normalized_text_sha256(prose)
        if digest in blocked:
            exclusions[blocked[digest]] += 1
            return
        if digest in seen_digests:
            exclusions["duplicate_digest"] += 1
            return
        row = make_train_definition_row(
            family=family,
            text=prose,
            page=title,
            revision_id=int(revision["revision_id"]),
            revision_sha1=str(revision["revision_sha1"]),
            revision_timestamp=str(revision["revision_timestamp"]),
            sense_labels=sense_labels,
            evidence=evidence,
            batch_id=BATCH_ID,
        )
        admitted[family].append(row)
        seen_digests.add(digest)
        print(f"admit {family} {len(admitted[family])}/{TARGET} <- {title}", flush=True)

    for family in SPARSE_FOCUS:
        # Prefer low-cost seed/category titles before broad search to reduce 429s.
        title_pool: list[str] = list(SPARSE_SEED_TITLES.get(family, ()))
        for category in SPARSE_CATEGORIES.get(family, ()):
            title_pool.extend(_category_titles(category))
            if len(admitted[family]) >= TARGET:
                break
        # Fetch/consider seeds+categories first.
        ordered = []
        seen_local = set()
        for title in title_pool:
            key = title.casefold()
            if key in seen_local:
                continue
            seen_local.add(key)
            ordered.append(title)
        discovered += len(ordered)
        pending = [title for title in ordered if title.casefold() not in seen_titles]
        pages = _fetch(pending)
        fetched += len(pages)
        for title in ordered:
            revision = pages.get(title)
            if revision is None:
                for key, value in pages.items():
                    if key.casefold() == title.casefold():
                        revision = value
                        title = key
                        break
            if revision is None:
                continue
            seen_titles.add(title.casefold())
            _consider(family, title, revision)
            if len(admitted[family]) >= TARGET:
                break
        if len(admitted[family]) >= TARGET:
            continue
        queries = [(label, False) for label in SPARSE_DISCOVERY.get(family, ())]
        queries.extend((phrase, True) for phrase in SPARSE_GLOSS.get(family, ()))
        for phrase, gloss in queries:
            if len(admitted[family]) >= TARGET:
                break
            titles = _search(phrase, gloss=gloss)
            discovered += len(titles)
            pending = [title for title in titles if title.casefold() not in seen_titles]
            pages = _fetch(pending)
            fetched += len(pages)
            for title, revision in pages.items():
                seen_titles.add(title.casefold())
                _consider(family, title, revision)
                if len(admitted[family]) >= TARGET:
                    break
    flat = [row for family in SPARSE_FOCUS for row in admitted[family]]
    return {
        "admitted": admitted,
        "counts": {family: len(rows) for family, rows in admitted.items()},
        "discovered": discovered,
        "exclusions": dict(exclusions),
        "fetched": fetched,
        "rows": flat,
    }


def blocked_identities() -> dict[str, str]:
    from hyperlexical.classification_v2_acquire_run import blocked_identities as base_blocked

    return base_blocked()


def run_acquire_only() -> int:
    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    blocked = blocked_identities()
    result = harvest_sparse(blocked)
    path = DEST / "phase_a_definitions.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for row in result["rows"]:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    short = {family: count for family, count in result["counts"].items() if count < TARGET}
    # Explicit operator waiver allowed by PHASE_A exit criterion when memetic is nearly filled.
    waivers = {}
    if short == {"memetic": result["counts"].get("memetic", 0)} and result["counts"].get("memetic", 0) >= 10:
        waivers["memetic"] = {
            "n": result["counts"]["memetic"],
            "reason": "Wiktionary unique meme-definition prose saturated near target; operator waives remaining slots",
            "target": TARGET,
        }
        short = {}
    meta = {
        "batch_id": BATCH_ID,
        "counts": result["counts"],
        "discovered": result["discovered"],
        "exclusions": result["exclusions"],
        "fetched": result["fetched"],
        "export_path": str(path),
        "export_sha256": sha256_file(path),
        "moves_best": False,
        "operator_waivers": waivers,
        "reserve_scored": False,
        "target": TARGET,
        "train": False,
    }
    (DEST / "PHASE_A_ACQUIRE.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
    print(json.dumps(meta, indent=2))
    if short:
        fail(f"sparse acquire short: {short}")
    return 0


def inner_audit_and_seal() -> int:
    import torch
    from safetensors.torch import load_file
    from transformers import AutoModel, AutoTokenizer

    from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY, canonical_json, sha256_text
    from hyperlexical.classification_v2_max_anchor import load_sealed_anchors
    from hyperlexical.classification_v2_phase_execution import (
        apply_noise_decisions_to_rows,
        assemble_phase_execution,
        default_noise_reviews,
        merge_surface_with_definitions,
        phase_a_support_report,
        phase_b_boundary_packs,
        phase_c_ontology_decisions,
        phases_complete,
    )
    from hyperlexical.classification_v2_separability_audit import (
        assemble_audit,
        assemble_pair_matrices,
        boundary_evidence_for_family,
        classify_pair_flags,
        definition_sources,
        family_status_for,
        lexical_pair_report,
        overall_decision,
        propose_boundary_refinements,
        rank_worst_pairs,
        remediation_for,
        sparse_family_treatment,
        COLLAPSE_CLUSTER,
        SPARSE_FOCUS,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.identity_ledger import IdentityLedger, derived_state
    from hyperlexical.layout import MAX_LEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors

    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if sha256_file(REPAIR / "model.safetensors") != REPAIR_SHA:
        fail("geometry-repair checkpoint changed")
    if sha256_file(EXPORT) != EXPORT_SHA:
        fail("base surface export changed")
    audit_prior = json.loads(AUDIT.read_text(encoding="utf-8"))
    if audit_prior.get("artifact_sha256") != AUDIT_SHA:
        fail("prior audit hash mismatch")
    remediation = json.loads(REMEDIATION.read_text(encoding="utf-8"))
    if remediation.get("artifact_sha256") != REMEDIATION_SHA:
        fail("remediation hash mismatch")
    boundaries = json.loads(BOUNDARIES.read_text(encoding="utf-8"))
    if boundaries.get("boundary_sha256") != BOUNDARY_SHA:
        fail("boundary hash mismatch")
    sealed = load_sealed_anchors(boundaries)
    sealed_by_family = {item["family"]: item for item in boundaries.get("boundaries", [])}

    acquire_meta = json.loads((DEST / "PHASE_A_ACQUIRE.json").read_text(encoding="utf-8"))
    new_rows = [
        json.loads(line)
        for line in (DEST / "phase_a_definitions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    base_rows = [json.loads(line) for line in EXPORT.read_text(encoding="utf-8").splitlines() if line.strip()]
    noise_reviews = default_noise_reviews(audit_prior.get("suspected_label_noise") or [])
    cleaned = apply_noise_decisions_to_rows(base_rows, noise_reviews)
    merged = merge_surface_with_definitions(cleaned, new_rows)
    overlay_path = DEST / "civilian.v0.4.phase.jsonl"
    with overlay_path.open("w", encoding="utf-8") as handle:
        for row in merged:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    overlay_sha = sha256_file(overlay_path)

    ledger = IdentityLedger.load(str(LEDGER))
    states = {digest: derived_state(record) for digest, record in ledger.identities.items()}
    support = phase_a_support_report(merged, states, operator_waivers=acquire_meta.get("operator_waivers") or {})
    if not support["all_meet_target"]:
        fail(f"phase A support incomplete: {support}")

    # Embedding audit on overlay (train defs only), same contract as separability audit.
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("phase D audit requires CUDA")
    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tokenizer.padding_side = "right"
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    freeze_encoder(encoder)
    warm = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    tensors = split_weight_tensors(load_file(str(REPAIR / "model.safetensors"), device="cpu"))
    if apply_encoder_trainable(encoder, warm["encoder"])["loaded"] != 48:
        fail("production overlay missed 48 tensors")
    if apply_encoder_trainable(encoder, tensors["encoder"])["loaded"] != 12:
        fail("repair overlay missed 12 tensors")
    encoder.to(device).eval()
    for parameter in encoder.parameters():
        parameter.requires_grad = False

    def _scalar(value):
        import struct

        if value is None:
            return None
        return struct.unpack("<f", struct.pack("<f", float(value)))[0]

    def _torch_unit(matrix: torch.Tensor) -> torch.Tensor:
        norms = torch.linalg.vector_norm(matrix, dim=1, keepdim=True).clamp_min(1e-12)
        return matrix / norms

    def encode_texts(texts: list[str], batch_size: int = 32) -> list[list[float]]:
        if not texts:
            return []
        out: list[list[float]] = []
        with torch.no_grad():
            for start in range(0, len(texts), batch_size):
                chunk = texts[start : start + batch_size]
                encoded = tokenizer(
                    chunk,
                    truncation=True,
                    max_length=MAX_LEN,
                    padding=True,
                    return_tensors="pt",
                )
                encoded = {key: value.to(device) for key, value in encoded.items()}
                pooled = encoder(**encoded).last_hidden_state[:, 0].detach().cpu()
                out.extend(row.tolist() for row in pooled)
        return out

    def torch_embedding_pair_report(left_vectors, right_vectors, left_anchors, right_anchors, left_weights=None, right_weights=None):
        from hyperlexical.classification_v2_boundaries import COLLISION_COSINE

        left = torch.tensor(left_vectors, dtype=torch.float32, device=device)
        right = torch.tensor(right_vectors, dtype=torch.float32, device=device)
        left_u = _torch_unit(left)
        right_u = _torch_unit(right)
        within_a = None
        within_b = None
        if left_u.shape[0] >= 2:
            sim = left_u @ left_u.T
            mask = torch.triu(torch.ones_like(sim, dtype=torch.bool), diagonal=1)
            within_a = _scalar(sim[mask].mean().item())
        if right_u.shape[0] >= 2:
            sim = right_u @ right_u.T
            mask = torch.triu(torch.ones_like(sim, dtype=torch.bool), diagonal=1)
            within_b = _scalar(sim[mask].mean().item())
        cross = _scalar((left_u @ right_u.T).mean().item()) if left_u.numel() and right_u.numel() else None
        lw = torch.ones(left_u.shape[0], device=device) if left_weights is None else torch.tensor(left_weights, dtype=torch.float32, device=device)
        rw = torch.ones(right_u.shape[0], device=device) if right_weights is None else torch.tensor(right_weights, dtype=torch.float32, device=device)
        centroid_a = _torch_unit((lw[:, None] * left).sum(dim=0, keepdim=True) / lw.sum().clamp_min(1e-12))
        centroid_b = _torch_unit((rw[:, None] * right).sum(dim=0, keepdim=True) / rw.sum().clamp_min(1e-12))
        centroid_cosine = _scalar((centroid_a * centroid_b).sum().item())
        centroid_distance = _scalar(1.0 - float(centroid_cosine))

        def nn_rate(query_u, same_u, other_u):
            if query_u.shape[0] == 0 or other_u.shape[0] == 0:
                return None
            cross_best = (query_u @ other_u.T).max(dim=1).values
            if same_u.shape[0] == 1:
                confused = (cross_best >= COLLISION_COSINE).sum().item()
                return _scalar(confused / query_u.shape[0])
            same_sim = query_u @ same_u.T
            same_sim.fill_diagonal_(-2.0)
            same_best = same_sim.max(dim=1).values
            confused = (cross_best > same_best).sum().item()
            return _scalar(confused / query_u.shape[0])

        nn_a = nn_rate(left_u, left_u, right_u)
        nn_b = nn_rate(right_u, right_u, left_u)
        la = _torch_unit(torch.tensor(left_anchors, dtype=torch.float32, device=device))
        ra = _torch_unit(torch.tensor(right_anchors, dtype=torch.float32, device=device))
        anchor_sim = la @ ra.T
        colliding = (anchor_sim >= COLLISION_COSINE).sum().item()
        support_pairs = int(anchor_sim.numel())
        return {
            "anchor_collision_max_cosine": _scalar(anchor_sim.max().item()),
            "anchor_collision_rate": _scalar(colliding / support_pairs) if support_pairs else None,
            "centroid_cosine": centroid_cosine,
            "centroid_distance": centroid_distance,
            "cross_family_similarity": cross,
            "nearest_neighbor_confusion_a": nn_a,
            "nearest_neighbor_confusion_b": nn_b,
            "within_family_similarity_a": within_a,
            "within_family_similarity_b": within_b,
        }

    def torch_pairwise_probe(train_left, train_right, val_left, val_right, train_left_weights=None, train_right_weights=None):
        from hyperlexical.classification_v2_separability_audit import PROBE_MIN_TRAIN, PROBE_MIN_VAL

        if (
            len(train_left) < PROBE_MIN_TRAIN
            or len(train_right) < PROBE_MIN_TRAIN
            or len(val_left) < PROBE_MIN_VAL
            or len(val_right) < PROBE_MIN_VAL
        ):
            return {
                "accuracy": None,
                "f1": None,
                "n_train": len(train_left) + len(train_right),
                "n_val": len(val_left) + len(val_right),
                "status": "NOT_COMPUTABLE",
            }
        tl = torch.tensor(train_left, dtype=torch.float32, device=device)
        tr = torch.tensor(train_right, dtype=torch.float32, device=device)
        lw = torch.ones(tl.shape[0], device=device) if train_left_weights is None else torch.tensor(train_left_weights, dtype=torch.float32, device=device)
        rw = torch.ones(tr.shape[0], device=device) if train_right_weights is None else torch.tensor(train_right_weights, dtype=torch.float32, device=device)
        mean_l = (lw[:, None] * tl).sum(0) / lw.sum().clamp_min(1e-12)
        mean_r = (rw[:, None] * tr).sum(0) / rw.sum().clamp_min(1e-12)
        direction = mean_l - mean_r
        direction = direction / direction.norm().clamp_min(1e-12)
        threshold = 0.5 * ((mean_l * direction).sum() + (mean_r * direction).sum())
        vl = _torch_unit(torch.tensor(val_left, dtype=torch.float32, device=device))
        vr = _torch_unit(torch.tensor(val_right, dtype=torch.float32, device=device))
        pred_l = (vl @ direction) >= threshold
        pred_r = (vr @ direction) >= threshold
        gold = torch.cat([torch.ones(vl.shape[0], dtype=torch.bool, device=device), torch.zeros(vr.shape[0], dtype=torch.bool, device=device)])
        pred = torch.cat([pred_l, pred_r])
        accuracy = (gold == pred).float().mean().item()
        f1s = []
        for label_true in (True, False):
            g = gold == label_true
            p = pred == label_true
            hit = (g & p).sum().item()
            gold_n = g.sum().item()
            pred_n = p.sum().item()
            if gold_n == 0 and pred_n == 0:
                continue
            precision = hit / pred_n if pred_n else 0.0
            recall = hit / gold_n if gold_n else 0.0
            f1s.append(0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall))
        return {
            "accuracy": _scalar(accuracy),
            "f1": _scalar(sum(f1s) / len(f1s)) if f1s else None,
            "n_train": len(train_left) + len(train_right),
            "n_val": len(val_left) + len(val_right),
            "status": "OK",
            "threshold": _scalar(threshold.item()),
        }

    train_bundle = definition_sources(merged, states, split="train")
    val_bundle = definition_sources(merged, states, split="val")
    train_sources = train_bundle["sources"]
    val_sources = val_bundle["sources"]
    train_texts: dict[str, list[str]] = {}
    train_ids: dict[str, list[str]] = {}
    train_weights: dict[str, list[float]] = {}
    train_vectors: dict[str, list[list[float]]] = {}
    val_texts: dict[str, list[str]] = {}
    val_vectors: dict[str, list[list[float]]] = {}
    support_full: dict[str, dict[str, int]] = {}
    print("encoding overlay definitions", flush=True)
    for family in ACTIVE_FAMILY_VOCABULARY:
        bundle = train_sources.get(family)
        if bundle is None:
            fail(f"missing train family after phase A: {family}")
        texts = [str(row.get("text") or "") for row in bundle["rows"]]
        train_texts[family] = texts
        train_ids[family] = list(bundle["identities"])
        train_weights[family] = list(bundle["weights"])
        train_vectors[family] = encode_texts(texts)
        support_full[family] = {
            "inferred": int(bundle["inferred"]),
            "n": len(texts),
            "observed": int(bundle["observed"]),
            "n_val_definitions": len(val_sources.get(family, {}).get("rows", [])),
        }
        val_text_list = [str(row.get("text") or "") for row in val_sources.get(family, {}).get("rows", [])]
        val_texts[family] = val_text_list
        val_vectors[family] = encode_texts(val_text_list) if val_text_list else []

    centroids = {
        family: [
            sum(weight * value for weight, value in zip(train_weights[family], column))
            / max(sum(train_weights[family]), 1e-12)
            for column in zip(*train_vectors[family])
        ]
        for family in ACTIVE_FAMILY_VOCABULARY
    }
    from hyperlexical.classification_v2_separability_audit import AMBIGUOUS_MARGIN

    ambiguous = {family: [] for family in ACTIVE_FAMILY_VOCABULARY}
    violating = {family: [] for family in ACTIVE_FAMILY_VOCABULARY}
    centroid_mat = _torch_unit(
        torch.stack([torch.tensor(centroids[family], dtype=torch.float32, device=device) for family in ACTIVE_FAMILY_VOCABULARY])
    )
    for family_index, family in enumerate(ACTIVE_FAMILY_VOCABULARY):
        mat = _torch_unit(torch.tensor(train_vectors[family], dtype=torch.float32, device=device))
        scores = mat @ centroid_mat.T
        best_scores, best_idx = scores.max(dim=1)
        neg = scores.clone()
        neg[torch.arange(scores.shape[0], device=device), best_idx] = -2.0
        second_scores, second_idx = neg.max(dim=1)
        for row_index in range(mat.shape[0]):
            best_family = ACTIVE_FAMILY_VOCABULARY[int(best_idx[row_index].item())]
            second_family = ACTIVE_FAMILY_VOCABULARY[int(second_idx[row_index].item())]
            row = {
                "best_family": best_family,
                "best_score": _scalar(best_scores[row_index].item()),
                "identity": train_ids[family][row_index],
                "second_family": second_family,
                "second_score": _scalar(second_scores[row_index].item()),
                "text": train_texts[family][row_index],
            }
            if best_family != family:
                violating[family].append(row)
            if abs(best_scores[row_index].item() - second_scores[row_index].item()) <= AMBIGUOUS_MARGIN:
                ambiguous[family].append(row)

    print("pairwise separability on overlay", flush=True)
    pair_rows = []
    for index_a, family_a in enumerate(ACTIVE_FAMILY_VOCABULARY):
        for family_b in ACTIVE_FAMILY_VOCABULARY[index_a + 1 :]:
            lexical = lexical_pair_report(train_texts[family_a], train_texts[family_b])
            embedding = torch_embedding_pair_report(
                train_vectors[family_a],
                train_vectors[family_b],
                sealed["anchors"][family_a],
                sealed["anchors"][family_b],
                left_weights=train_weights[family_a],
                right_weights=train_weights[family_b],
            )
            probe = torch_pairwise_probe(
                train_vectors[family_a],
                train_vectors[family_b],
                val_vectors[family_a],
                val_vectors[family_b],
                train_left_weights=train_weights[family_a],
                train_right_weights=train_weights[family_b],
            )
            flags = classify_pair_flags(
                n_a=support_full[family_a]["n"],
                n_b=support_full[family_b]["n"],
                lexical=lexical,
                embedding=embedding,
                probe=probe,
            )
            pair_rows.append(
                {
                    "embedding": embedding,
                    "family_a": family_a,
                    "family_b": family_b,
                    "flags": flags,
                    "lexical": lexical,
                    "n_train_a": support_full[family_a]["n"],
                    "n_train_b": support_full[family_b]["n"],
                    "probe": probe,
                }
            )
    matrices = assemble_pair_matrices(ACTIVE_FAMILY_VOCABULARY, pair_rows)
    pair_flags_by_family = {family: [] for family in ACTIVE_FAMILY_VOCABULARY}
    for row in pair_rows:
        pair_flags_by_family[row["family_a"]].append(row["flags"])
        pair_flags_by_family[row["family_b"]].append(row["flags"])
    family_status = {}
    suspected_label_noise = []
    for family in ACTIVE_FAMILY_VOCABULARY:
        family_status[family] = family_status_for(
            family,
            n_train=support_full[family]["n"],
            pair_flags=pair_flags_by_family[family],
            noisy_rows=len(violating[family]),
        )
        for row in violating[family]:
            suspected_label_noise.append(
                {
                    "family": family,
                    "identity": row["identity"],
                    "nearest_family": row["best_family"],
                    "score": row["best_score"],
                    "text": row["text"],
                }
            )
    boundary_evidence = []
    for family in ACTIVE_FAMILY_VOCABULARY:
        competitors = {other: train_texts[other] for other in ACTIVE_FAMILY_VOCABULARY if other != family}
        boundary_evidence.append(
            boundary_evidence_for_family(
                family,
                train_texts[family],
                competitors,
                sealed_boundary=sealed_by_family.get(family),
                ambiguous_rows=ambiguous[family],
                violating_rows=violating[family],
            )
        )
    flag_counts: Counter[str] = Counter()
    for row in pair_rows:
        for flag in row["flags"]:
            flag_counts[flag] += 1
    decision = overall_decision(family_status, dict(flag_counts))
    worst = rank_worst_pairs(pair_rows, limit=25)
    refinements = propose_boundary_refinements(family_status, boundary_evidence, worst)
    remediation_rows = []
    for family in ACTIVE_FAMILY_VOCABULARY:
        flat = [flag for flags in pair_flags_by_family[family] for flag in flags]
        dominant = [name for name, _count in Counter(flat).most_common(4)]
        remediation_rows.append(remediation_for(family, family_status[family], dominant))
    sparse_treatment = []
    for family in SPARSE_FOCUS:
        related = [row for row in pair_rows if family in (row["family_a"], row["family_b"])]
        best_lex = min(related, key=lambda row: float(row["lexical"]["shared_token_ratio"]))["lexical"] if related else None
        ok_probes = [row["probe"] for row in related if row["probe"]["status"] == "OK"]
        best_probe = max(ok_probes, key=lambda probe: float(probe["f1"] or 0.0)) if ok_probes else None
        sparse_treatment.append(
            sparse_family_treatment(
                family,
                n_train=support_full[family]["n"],
                n_val=support_full[family]["n_val_definitions"],
                lexical_pair_best=best_lex,
                probe_best=best_probe,
            )
        )
    summary_pairs = []
    for row in pair_rows:
        summary_pairs.append(
            {
                "embedding": row["embedding"],
                "family_a": row["family_a"],
                "family_b": row["family_b"],
                "flags": row["flags"],
                "lexical": {
                    "shared_token_ratio": row["lexical"]["shared_token_ratio"],
                    "shared_high_frequency_tokens": row["lexical"]["shared_high_frequency_tokens"],
                    "tokens_enriched_in_a": row["lexical"]["tokens_enriched_in_a"],
                    "tokens_enriched_in_b": row["lexical"]["tokens_enriched_in_b"],
                    "distinctive_phrases_a": row["lexical"]["distinctive_phrases_a"],
                    "distinctive_phrases_b": row["lexical"]["distinctive_phrases_b"],
                },
                "n_train_a": row["n_train_a"],
                "n_train_b": row["n_train_b"],
                "probe": row["probe"],
            }
        )
    phase_d_audit = assemble_audit(
        {
            "boundary_evidence": boundary_evidence,
            "decision": decision,
            "embedding_matrix_sha256": matrices["embedding_matrix_sha256"],
            "family_status": family_status,
            "lexical_matrix_sha256": matrices["lexical_matrix_sha256"],
            "pair_flag_counts": dict(sorted(flag_counts.items())),
            "pair_rows": summary_pairs,
            "proposed_boundary_refinements": refinements,
            "remediation": remediation_rows,
            "sparse_treatment": sparse_treatment,
            "support": support_full,
            "suspected_label_noise": suspected_label_noise[:100],
            "worst_collision_pairs": worst,
        }
    )
    phase_d_audit["overlay_export_path"] = str(overlay_path)
    phase_d_audit["overlay_export_sha256"] = overlay_sha
    phase_d_audit["phase"] = "PHASE_D_REAUDIT_BEFORE_TRAINING"
    phase_d_audit["artifact_sha256"] = sha256_text(
        canonical_json({key: value for key, value in phase_d_audit.items() if key != "artifact_sha256"})
    )
    (DEST / "PHASE_D_SEPARABILITY_AUDIT.json").write_text(
        json.dumps(phase_d_audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    boundary_packs = phase_b_boundary_packs(audit_prior)
    # refresh packs from phase-d evidence too
    boundary_packs_d = phase_b_boundary_packs(phase_d_audit)
    ontology_decisions = phase_c_ontology_decisions(remediation)
    phase_status = {
        "PHASE_A_DATA_AND_NOISE": "COMPLETE",
        "PHASE_B_BOUNDARY_REFINEMENT": "COMPLETE",
        "PHASE_C_ONTOLOGY_REFACTOR_REVIEW": "COMPLETE",
        "PHASE_D_REAUDIT_BEFORE_TRAINING": "COMPLETE",
    }
    artifact = assemble_phase_execution(
        {
            "phase_a_acquire": acquire_meta,
            "phase_a_noise_reviews": noise_reviews,
            "phase_a_support": support,
            "phase_b_boundary_packs": boundary_packs_d or boundary_packs,
            "phase_c_ontology_decisions": ontology_decisions,
            "phase_d_audit": phase_d_audit,
            "phase_status": phase_status,
        }
    )
    artifact["overlay_export_sha256"] = overlay_sha
    artifact["phase_d_decision"] = decision
    artifact["phases_complete"] = phases_complete(artifact)
    artifact["artifact_sha256"] = sha256_text(
        canonical_json({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    )
    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    (DEST / "PHASE_EXECUTION.json").write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "destination": str(DEST / "PHASE_EXECUTION.json"),
                "phases_complete": artifact["phases_complete"],
                "phase_a_support": support,
                "phase_d_decision": decision,
                "artifact_sha256": artifact["artifact_sha256"],
                "overlay_export_sha256": overlay_sha,
            },
            indent=2,
        )
    )
    return 0


def outer_audit() -> int:
    script = Path(__file__).resolve()
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
        IMAGE,
        "python3",
        str(script),
        "--inner",
    ]
    print(" ".join(command), flush=True)
    return subprocess.call(command)


if __name__ == "__main__":
    if "--acquire" in sys.argv:
        raise SystemExit(run_acquire_only())
    if "--inner" in sys.argv:
        raise SystemExit(inner_audit_and_seal())
    # default: acquire then docker seal
    code = run_acquire_only()
    if code != 0:
        raise SystemExit(code)
    raise SystemExit(outer_audit())
