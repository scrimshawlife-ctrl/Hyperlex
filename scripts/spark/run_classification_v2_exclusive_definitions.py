"""Seal HYPERLEX_ACTIVE_FAMILY_EXCLUSIVE_DEFINITION_PASS_V1.

Mines frozen-encoder KEEP collisions, drops/replaces offenders, acquires
mutually exclusive Wiktionary senses, rebuilds the overlay, and reseals
boundary redefinition + the training gate.

Does not train, score the reserve, move BEST, or mutate historical boundaries.
"""

from __future__ import annotations

import hashlib
import json
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
PHASE = Path("/home/morpheus/hlx-private/classification-v2-phase-execution-20260930")
REDEF_DIR = Path("/home/morpheus/hlx-private/classification-v2-boundary-redefinition-20260930")
REDEF = REDEF_DIR / "BOUNDARY_REDEFINITION.json"
REDEF_SHA = "4757d46aa7f0c95732378d5f710cbd1a28d048f60bee2fc35dfb6d5c0fe8cad1"
OVERLAY_V4 = PHASE / "civilian.v0.4.phase.jsonl"
OVERLAY_V4_SHA = "8a934806885fb939f8b4ca26f10ab5bc6600c495d3be77d5a2366dc6c62146e0"
BOUNDARIES = Path(
    "/home/morpheus/hlx-private/classification-v2-boundaries-20260930/FAMILY_SEMANTIC_BOUNDARIES.json"
)
BOUNDARY_SHA = "0ca6f34ce1abf68388e443371672ca36e16028079a175b6775e1968900e1c52f"
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
DEST = Path("/home/morpheus/hlx-private/classification-v2-exclusive-definitions-20260930")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
API = "https://en.wiktionary.org/w/api.php"
UA = "HyperlexClassificationV2Exclusive/1.0 (exclusive definition pass; mediawiki provenance)"
MAX_TITLES = 60
PAUSE = 2.0
BATCH_ID = "HLX-CLASSIFICATION-V2-EXCLUSIVE-20260930"

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
                time.sleep(40 + attempt * 20)
                continue
            raise
        except TimeoutError:
            if attempt < 4:
                time.sleep(10 + attempt * 10)
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


def acquire_exclusive(families: list[str], blocked: dict[str, str], targets: dict[str, int]) -> dict[str, Any]:
    from hyperlexical.classification_v2_acquire import (
        DISCOVERY_QUERIES,
        GLOSS_DISCOVERY,
        classify_wikitext,
        training_row,
    )
    from hyperlexical.classification_v2_exclusive_definitions import (
        REACQUIRE_FAMILIES,
        exclusive_admission_ok,
    )
    from hyperlexical.classification_v2_separability_audit import COLLAPSE_CLUSTER
    from hyperlexical.holdout_guard import normalized_text_sha256

    admitted: dict[str, list[dict[str, Any]]] = {family: [] for family in families}
    exclusions: Counter[str] = Counter()
    seen_titles: set[str] = set()
    seen_digests: set[str] = set()
    discovered = 0
    fetched = 0
    competitors = list(dict.fromkeys([*COLLAPSE_CLUSTER, *REACQUIRE_FAMILIES]))

    for family in families:
        need = int(targets.get(family, 0))
        if need <= 0:
            continue
        queries = [(label, False) for label in DISCOVERY_QUERIES.get(family, ())]
        queries.extend((phrase, True) for phrase in GLOSS_DISCOVERY.get(family, ()))
        for phrase, gloss in queries:
            if len(admitted[family]) >= need:
                break
            titles = _search(phrase, gloss=gloss)
            discovered += len(titles)
            pending = [title for title in titles if title.casefold() not in seen_titles]
            pages = _fetch(pending)
            fetched += len(pages)
            for title, revision in pages.items():
                seen_titles.add(title.casefold())
                decision = classify_wikitext(revision["content"])
                if decision.get("status") != "unique" or decision.get("family") != family:
                    exclusions["not_unique_" + family] += 1
                    continue
                prose = str(decision.get("definition_prose") or "").strip()
                if len(prose) < 24:
                    exclusions["short_prose"] += 1
                    continue
                if not exclusive_admission_ok(
                    family=family,
                    text=prose,
                    competitor_families=competitors,
                ):
                    exclusions["exclusive_core_fail"] += 1
                    continue
                digest = normalized_text_sha256(prose)
                if digest in blocked:
                    exclusions[blocked[digest]] += 1
                    continue
                if digest in seen_digests:
                    exclusions["duplicate"] += 1
                    continue
                row = training_row(title, decision, revision)
                row["provenance"] = dict(row.get("provenance") or {})
                row["provenance"]["batch_id"] = BATCH_ID
                row["provenance"]["phase"] = "EXCLUSIVE_DEFINITION_PASS"
                admitted[family].append(row)
                seen_digests.add(digest)
                print(f"admit {family} {len(admitted[family])}/{need} <- {title}", flush=True)
                if len(admitted[family]) >= need:
                    break
    flat = [row for family in families for row in admitted[family]]
    return {
        "admitted": admitted,
        "counts": {family: len(rows) for family, rows in admitted.items()},
        "discovered": discovered,
        "exclusions": dict(exclusions),
        "fetched": fetched,
        "rows": flat,
    }


def mine_collisions(family_rows: dict[str, list[dict[str, Any]]], family_vectors: dict[str, list[list[float]]], device, threshold: float) -> list[dict[str, Any]]:
    import torch
    from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY
    from hyperlexical.classification_v2_exclusive_definitions import core_hit_count

    def unit(matrix: torch.Tensor) -> torch.Tensor:
        norms = torch.linalg.vector_norm(matrix, dim=1, keepdim=True).clamp_min(1e-12)
        return matrix / norms

    tensors = {}
    for family in ACTIVE_FAMILY_VOCABULARY:
        rows = family_vectors.get(family) or []
        if rows:
            tensors[family] = unit(torch.tensor(rows, dtype=torch.float32, device=device))
    out = []
    families = [family for family in ACTIVE_FAMILY_VOCABULARY if family in tensors]
    for index, left in enumerate(families):
        left_u = tensors[left]
        for right in families[index + 1 :]:
            right_u = tensors[right]
            sim = left_u @ right_u.T
            peak = float(sim.max().item())
            if peak < threshold:
                continue
            # collect all member pairs at/above threshold (cap per family-pair)
            coords = (sim >= threshold).nonzero(as_tuple=False)
            # keep strongest first, max 40 pairs per family pair
            scores = [(float(sim[int(i), int(j)].item()), int(i), int(j)) for i, j in coords]
            scores.sort(reverse=True)
            for cosine, i, j in scores[:40]:
                a_row = family_rows[left][i]
                b_row = family_rows[right][j]
                out.append(
                    {
                        "cosine": cosine,
                        "core_hits_a": core_hit_count(a_row["text"], left),
                        "core_hits_b": core_hit_count(b_row["text"], right),
                        "family_a": left,
                        "family_b": right,
                        "identity_a": a_row["identity"],
                        "identity_b": b_row["identity"],
                        "text_a": a_row["text"],
                        "text_b": b_row["text"],
                    }
                )
    return out


def reseal_boundary_redefinition(
    *,
    overlay_path: Path,
    overlay_sha: str,
    packs: dict[str, Any],
    evidence: dict[str, Any],
    split_pairs: list[dict[str, Any]],
    device,
    encode_texts,
) -> dict[str, Any]:
    from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY, canonical_json, sha256_text
    from hyperlexical.classification_v2_boundary_redefinition import (
        HIGH_OVERLAP_COSINE,
        PRESERVED_NOISE_COUNTS,
        assemble_boundary_redefinition,
        assess_split_candidates,
        build_family_contract,
        build_pairwise_rule,
        classify_training_row,
        enforce_sparse_support_floor,
        filter_keep_rows,
        next_engineering_action,
        preserved_noise_classifications,
        redefinition_contract,
        training_gate_result,
    )
    from hyperlexical.classification_v2_separability_audit import COLLAPSE_CLUSTER, SPARSE_FOCUS, definition_sources
    from hyperlexical.identity_ledger import IdentityLedger, derived_state

    import torch

    def torch_high_overlap_pairs_local(family_vectors, threshold, vocabulary, collapse_cluster):
        def unit(matrix):
            norms = torch.linalg.vector_norm(matrix, dim=1, keepdim=True).clamp_min(1e-12)
            return matrix / norms

        tensors = {}
        for family in vocabulary:
            rows = family_vectors.get(family) or []
            if rows:
                tensors[family] = unit(torch.tensor(rows, dtype=torch.float32, device=device))
        families = [family for family in vocabulary if family in tensors]
        high_pairs = []
        for index, left in enumerate(families):
            left_u = tensors[left]
            for right in families[index + 1 :]:
                peak = float((left_u @ tensors[right].T).max().item())
                if peak >= threshold:
                    high_pairs.append(
                        {
                            "cosine": peak,
                            "family_a": left,
                            "family_b": right,
                            "in_collapse_cluster": left in collapse_cluster and right in collapse_cluster,
                        }
                    )
        collapse_pairs = [pair for pair in high_pairs if pair["in_collapse_cluster"]]
        parent = {family: family for family in collapse_cluster}

        def find(node):
            while parent[node] != node:
                parent[node] = parent[parent[node]]
                node = parent[node]
            return node

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        for pair in collapse_pairs:
            union(pair["family_a"], pair["family_b"])
        components = {}
        for family in collapse_cluster:
            if family in tensors:
                components.setdefault(find(family), []).append(family)
        largest = max((len(v) for v in components.values()), default=0)
        return {
            "collapse_high_overlap_pairs": len(collapse_pairs),
            "high_overlap_pairs": high_pairs,
            "high_overlap_pair_count": len(high_pairs),
            "largest_collapse_component": largest,
            "threshold": threshold,
        }

    rows = [json.loads(line) for line in overlay_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ledger = IdentityLedger.load(str(LEDGER))
    states = {digest: derived_state(record) for digest, record in ledger.identities.items()}
    train_sources = definition_sources(rows, states, split="train")["sources"]
    family_rows = {}
    train_texts = {}
    train_ids = {}
    train_vectors = {}
    for family in ACTIVE_FAMILY_VOCABULARY:
        bundle = train_sources[family]
        texts = [str(row.get("text") or "") for row in bundle["rows"]]
        ids = list(bundle["identities"])
        train_texts[family] = texts
        train_ids[family] = ids
        family_rows[family] = [{"family": family, "identity": i, "text": t} for i, t in zip(ids, texts)]
        train_vectors[family] = encode_texts(texts)

    contracts = {
        family: build_family_contract(
            family, pack=packs.get(family), evidence=evidence.get(family), texts=train_texts[family]
        )
        for family in ACTIVE_FAMILY_VOCABULARY
    }
    overlap_pre = torch_high_overlap_pairs_local(
        train_vectors, HIGH_OVERLAP_COSINE, list(ACTIVE_FAMILY_VOCABULARY), COLLAPSE_CLUSTER
    )
    pair_keys = {
        ("||".join(sorted((p["family_a"], p["family_b"]))), *sorted((p["family_a"], p["family_b"])))
        for p in overlap_pre["high_overlap_pairs"]
    }
    for pair in split_pairs:
        pair_keys.add(
            ("||".join(sorted((pair["family_a"], pair["family_b"]))), *sorted((pair["family_a"], pair["family_b"])))
        )

    pairwise_rules_list = []
    pairwise_rules_map = {}
    for key, a, b in sorted(pair_keys):
        rule = build_pairwise_rule(
            a, b, contract_a=contracts[a], contract_b=contracts[b], texts_a=train_texts[a], texts_b=train_texts[b]
        )
        pairwise_rules_list.append(rule)
        pairwise_rules_map[key] = rule

    classifications = []
    seen_noise = set()
    noise_prefixes = (
        "17d1d192814cdda7", "4df2dd1d7f069ccc", "5dcd520e0f42301b", "2e19997bbcf52f02",
        "8bd78f57167eeb19", "90544f171008d3cf", "bc29c71410e85594",
    )
    for family in ACTIVE_FAMILY_VOCABULARY:
        for row in family_rows[family]:
            result = classify_training_row(
                family=family,
                text=row["text"],
                identity=row["identity"],
                contracts=contracts,
                pairwise_rules=pairwise_rules_map,
            )
            classifications.append(result)
            for prefix in noise_prefixes:
                if row["identity"].startswith(prefix):
                    seen_noise.add(prefix)
    for preset in preserved_noise_classifications():
        if str(preset["identity"]) not in seen_noise:
            classifications.append(preset)
    classifications = enforce_sparse_support_floor(classifications, floor=12)
    status_counts = Counter(row["decision"] for row in classifications)
    kept = filter_keep_rows(family_rows, classifications)
    for family in SPARSE_FOCUS:
        if len(kept[family]) < 12:
            fail(f"sparse floor breached in reseal: {family}={len(kept[family])}")
    support_post = {family: len(kept[family]) for family in ACTIVE_FAMILY_VOCABULARY}
    post_vectors = {
        family: [train_vectors[family][train_ids[family].index(row["identity"])] for row in kept[family]]
        for family in ACTIVE_FAMILY_VOCABULARY
    }
    overlap_post = torch_high_overlap_pairs_local(
        post_vectors, HIGH_OVERLAP_COSINE, list(ACTIVE_FAMILY_VOCABULARY), COLLAPSE_CLUSTER
    )
    pre_lookup = {"||".join(sorted((p["family_a"], p["family_b"]))): p for p in overlap_pre["high_overlap_pairs"]}
    post_lookup = {"||".join(sorted((p["family_a"], p["family_b"]))): p for p in overlap_post["high_overlap_pairs"]}
    all_keys = sorted(set(pre_lookup) | set(post_lookup) | {"||".join(sorted((p["family_a"], p["family_b"]))) for p in split_pairs})
    pair_overlap_table = []
    for key in all_keys:
        a, b = key.split("||")
        pre = pre_lookup.get(key)
        post = post_lookup.get(key)
        pair_overlap_table.append(
            {
                "family_a": a,
                "family_b": b,
                "post_filter_overlap": None if post is None else float(post["cosine"]),
                "pre_filter_overlap": None if pre is None else float(pre["cosine"]),
                "row_count_removed_or_flagged": 0,
            }
        )
    split_assessments = assess_split_candidates(
        split_pairs, pre_pairs=overlap_pre["high_overlap_pairs"], post_pairs=overlap_post["high_overlap_pairs"]
    )
    gate = training_gate_result(pre=overlap_pre, post=overlap_post, support_post=support_post)
    compact = []
    for row in classifications:
        text = row.get("text")
        compact.append(
            {
                "decision": row["decision"],
                "family": row["family"],
                "identity": row["identity"],
                "reasons": row["reasons"],
                "relabel_to": row.get("relabel_to"),
                "text": None if text is None else (text if len(text) <= 160 else text[:157] + "..."),
            }
        )
    compact.sort(key=lambda item: (item["decision"], item["family"], item["identity"]))
    artifact = assemble_boundary_redefinition(
        {
            "family_contracts": contracts,
            "pairwise_rules": pairwise_rules_list,
            "row_classifications": compact,
            "row_status_counts": {
                status: int(status_counts.get(status, 0))
                for status in ("KEEP", "REVIEW", "DROP", "RELABEL_CANDIDATE", "AMBIGUOUS")
            },
            "support_post": support_post,
            "overlap_pre": overlap_pre,
            "overlap_post": overlap_post,
            "pair_overlap_table": pair_overlap_table,
            "split_candidate_assessments": split_assessments,
            "training_gate": gate,
        }
    )
    # Retarget overlay pin in the resealed artifact without mutating historical phase overlay.
    artifact["overlay_sha256"] = overlay_sha
    artifact["exclusive_pass"] = True
    artifact["contract"] = redefinition_contract()
    artifact["contract"]["overlay_sha256"] = overlay_sha
    artifact["next_engineering_action"] = next_engineering_action(artifact)
    artifact["support_pre"] = {family: len(family_rows[family]) for family in ACTIVE_FAMILY_VOCABULARY}
    artifact["pairwise_rule_count"] = len(pairwise_rules_list)
    artifact["family_contract_count"] = len(contracts)
    artifact["preserved_noise_audit"] = PRESERVED_NOISE_COUNTS
    artifact["artifact_sha256"] = sha256_text(
        canonical_json({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    )
    return artifact


def inner() -> int:
    import torch
    from safetensors.torch import load_file
    from transformers import AutoModel, AutoTokenizer

    from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY, canonical_json, sha256_text
    from hyperlexical.classification_v2_acquire_run import blocked_identities
    from hyperlexical.classification_v2_exclusive_definitions import (
        REACQUIRE_FAMILIES,
        SPARSE_FLOOR,
        TARGET_EXCLUSIVE,
        assemble_exclusive_pass,
        exclusive_contract,
        select_collision_replacements,
    )
    from hyperlexical.classification_v2_boundary_redefinition import HIGH_OVERLAP_COSINE
    from hyperlexical.classification_v2_separability_audit import SPARSE_FOCUS, definition_sources
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.holdout_guard import normalized_text_sha256
    from hyperlexical.identity_ledger import IdentityLedger, derived_state
    from hyperlexical.layout import MAX_LEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors

    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if sha256_file(REPAIR / "model.safetensors") != REPAIR_SHA:
        fail("geometry-repair checkpoint changed")
    if sha256_file(OVERLAY_V4) != OVERLAY_V4_SHA:
        fail("phase overlay changed")
    redef = json.loads(REDEF.read_text(encoding="utf-8"))
    if redef.get("artifact_sha256") != REDEF_SHA:
        fail("boundary redefinition hash mismatch")
    boundaries = json.loads(BOUNDARIES.read_text(encoding="utf-8"))
    if boundaries.get("boundary_sha256") != BOUNDARY_SHA:
        fail("historical boundary hash mismatch")

    phase = json.loads((PHASE / "PHASE_EXECUTION.json").read_text(encoding="utf-8"))
    phase_d = json.loads((PHASE / "PHASE_D_SEPARABILITY_AUDIT.json").read_text(encoding="utf-8"))
    packs = {row["family"]: row for row in phase.get("phase_b_boundary_packs") or []}
    evidence = {row["family"]: row for row in phase_d.get("boundary_evidence") or []}
    split_pairs = []
    for decision in phase.get("phase_c_ontology_decisions") or []:
        for pair in decision.get("pair_reviews") or []:
            if pair.get("decision") == "SPLIT_CANDIDATE":
                split_pairs.append(pair)

    rows = [json.loads(line) for line in OVERLAY_V4.read_text(encoding="utf-8").splitlines() if line.strip()]
    ledger = IdentityLedger.load(str(LEDGER))
    states = {digest: derived_state(record) for digest, record in ledger.identities.items()}
    train_sources = definition_sources(rows, states, split="train")["sources"]

    # Use sealed KEEP set from boundary redefinition as the collision mine base.
    keep_ids = {
        row["identity"]
        for row in redef["row_classifications"]
        if row["decision"] == "KEEP" and row.get("text") is not None
    }
    # Also include all train identities for families (mine on full train defs for replace targeting)
    family_rows: dict[str, list[dict[str, Any]]] = {}
    for family in ACTIVE_FAMILY_VOCABULARY:
        bundle = train_sources[family]
        kept = [
            {"family": family, "identity": identity, "text": str(row.get("text") or "")}
            for identity, row in zip(bundle["identities"], bundle["rows"])
            if identity in keep_ids
        ]
        if not kept:
            kept = [
                {"family": family, "identity": identity, "text": str(row.get("text") or "")}
                for identity, row in zip(bundle["identities"], bundle["rows"])
            ]
        family_rows[family] = kept

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("exclusive definition pass requires CUDA")
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

    def encode_texts(texts: list[str], batch_size: int = 32) -> list[list[float]]:
        if not texts:
            return []
        out: list[list[float]] = []
        with torch.no_grad():
            for start in range(0, len(texts), batch_size):
                chunk = texts[start : start + batch_size]
                encoded = tokenizer(
                    chunk, truncation=True, max_length=MAX_LEN, padding=True, return_tensors="pt"
                )
                encoded = {key: value.to(device) for key, value in encoded.items()}
                pooled = encoder(**encoded).last_hidden_state[:, 0].detach().cpu()
                out.extend(row.tolist() for row in pooled)
        return out

    print("encoding KEEP rows for collision mining", flush=True)
    family_vectors = {family: encode_texts([row["text"] for row in family_rows[family]]) for family in ACTIVE_FAMILY_VOCABULARY}
    support = {family: len(family_rows[family]) for family in ACTIVE_FAMILY_VOCABULARY}
    for family in SPARSE_FOCUS:
        if support[family] < SPARSE_FLOOR:
            fail(f"sparse KEEP support below floor before exclusive pass: {family}={support[family]}")

    print("mining cross-family KEEP collisions", flush=True)
    collisions = mine_collisions(family_rows, family_vectors, device, HIGH_OVERLAP_COSINE)
    print(f"member collision pairs: {len(collisions)}", flush=True)
    replacements = select_collision_replacements(collisions, support=support, contracts=redef.get("family_contracts"))
    print(f"replacement decisions: {len(replacements)}", flush=True)
    replace_ids = {row["identity"] for row in replacements}

    # How many exclusive admissions needed per reacquire family
    targets: dict[str, int] = {}
    for family in REACQUIRE_FAMILIES:
        lost = sum(1 for row in replacements if row["family"] == family)
        current = support[family]
        floor = SPARSE_FLOOR if family in SPARSE_FOCUS else 6
        desired = max(floor, min(TARGET_EXCLUSIVE, current))
        after = current - lost
        need = max(0, desired - after) + lost  # restore lost + fill toward desired
        # Cap acquire volume
        targets[family] = min(need, TARGET_EXCLUSIVE)

    print("acquire targets", {k: v for k, v in targets.items() if v}, flush=True)
    blocked = blocked_identities()
    # also block all current overlay digests to avoid reintroducing dropped noise silently
    for row in rows:
        text = str(row.get("text") or "")
        if text:
            blocked.setdefault(normalized_text_sha256(text), "CURRENT_OVERLAY")
    for row in replacements:
        text = str(row.get("text") or "")
        if text:
            blocked[normalized_text_sha256(text)] = "EXCLUSIVE_REPLACE"

    acquire_families = [family for family in REACQUIRE_FAMILIES if targets.get(family, 0) > 0]
    acquired = {"rows": [], "counts": {}, "discovered": 0, "fetched": 0, "exclusions": {}}
    if acquire_families:
        print("acquiring exclusive Wiktionary definitions", flush=True)
        acquired = acquire_exclusive(acquire_families, blocked, targets)

    # Build v0.5 overlay: drop REPLACE/DROP identities from train defs; append acquired.
    # Non-definition rows in overlay are preserved as-is.
    from hyperlexical.classification_v2_boundaries import CLASSIFICATION_TASKS
    from hyperlexical.classification_v2_prototype import PROTOTYPE_WEIGHT, _prose
    from hyperlexical.classification_v2 import EXACT_COPY_FAMILIES
    from hyperlexical.classification_v2_surface import SURFACE_PROSE, surface_form
    from hyperlexical.classification_v2_prototype import _markup_text

    def is_train_definition(row: dict[str, Any]) -> bool:
        if row.get("split") != "train":
            return False
        lineage = str(row.get("lineage") or "")
        if lineage not in ACTIVE_FAMILY_VOCABULARY or row.get("class") not in PROTOTYPE_WEIGHT:
            return False
        if str(row.get("task") or "") not in CLASSIFICATION_TASKS:
            return False
        text = str(row.get("text") or "").strip()
        if not text:
            return False
        if lineage in EXACT_COPY_FAMILIES:
            if _markup_text(text) or surface_form(text) != SURFACE_PROSE:
                return False
        else:
            prose = _prose(row)
            if not prose or text != prose:
                return False
        return True

    new_rows = []
    removed = 0
    for row in rows:
        if is_train_definition(row):
            digest = normalized_text_sha256(str(row.get("text") or ""))
            if digest in replace_ids:
                removed += 1
                continue
        new_rows.append(row)
    for row in acquired["rows"]:
        new_rows.append(row)

    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    overlay_path = DEST / "civilian.v0.5.exclusive.jsonl"
    with overlay_path.open("w", encoding="utf-8") as handle:
        for row in new_rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    overlay_sha = sha256_file(overlay_path)
    print(f"wrote overlay removed={removed} acquired={len(acquired['rows'])} sha={overlay_sha}", flush=True)

    # Verify sparse floors on new overlay train defs
    new_train = definition_sources(new_rows, states, split="train")["sources"]
    support_post_overlay = {family: len(new_train[family]["identities"]) for family in ACTIVE_FAMILY_VOCABULARY}
    for family in SPARSE_FOCUS:
        if support_post_overlay[family] < SPARSE_FLOOR:
            fail(f"sparse overlay support breached: {family}={support_post_overlay[family]}")
    zeros = [family for family in ACTIVE_FAMILY_VOCABULARY if support_post_overlay[family] < 1]
    if zeros:
        fail(f"zero-support families after exclusive overlay: {zeros}")

    print("resealing boundary redefinition on exclusive overlay", flush=True)
    redef_after = reseal_boundary_redefinition(
        overlay_path=overlay_path,
        overlay_sha=overlay_sha,
        packs=packs,
        evidence=evidence,
        split_pairs=split_pairs,
        device=device,
        encode_texts=encode_texts,
    )
    (DEST / "BOUNDARY_REDEFINITION_AFTER_EXCLUSIVE.json").write_text(
        json.dumps(redef_after, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    compact_acquired = []
    for row in acquired["rows"]:
        compact_acquired.append(
            {
                "family": row["lineage"],
                "identity": normalized_text_sha256(str(row.get("text") or "")),
                "page": (row.get("provenance") or {}).get("page"),
                "text": (str(row.get("text") or "")[:160]),
            }
        )
    artifact = assemble_exclusive_pass(
        {
            "replacement_decisions": replacements,
            "acquired_rows": compact_acquired,
            "support_pre": support,
            "support_post_overlay": support_post_overlay,
            "collision_pairs_pre": len({(c["family_a"], c["family_b"]) for c in collisions}),
            "overlay_sha256": overlay_sha,
            "boundary_redefinition": redef_after,
        }
    )
    artifact["acquire_meta"] = {
        "counts": acquired.get("counts"),
        "discovered": acquired.get("discovered"),
        "exclusions": acquired.get("exclusions"),
        "fetched": acquired.get("fetched"),
        "targets": targets,
    }
    artifact["contract"] = exclusive_contract()
    artifact["artifact_sha256"] = sha256_text(
        canonical_json({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    )
    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if boundaries.get("boundary_sha256") != BOUNDARY_SHA:
        fail("historical boundaries mutated")

    (DEST / "EXCLUSIVE_DEFINITIONS.json").write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summary = {
        "destination": str(DEST / "EXCLUSIVE_DEFINITIONS.json"),
        "exclusive_state": artifact["exclusive_state"],
        "artifact_sha256": artifact["artifact_sha256"],
        "overlay_sha256": overlay_sha,
        "replacement_counts": artifact["replacement_counts"],
        "acquired_count": artifact["acquired_count"],
        "support_post_overlay": artifact["support_post_overlay"],
        "overlap_pre": artifact["overlap_pre"],
        "overlap_post": artifact["overlap_post"],
        "overlap_reduction": artifact["overlap_reduction"],
        "training_gate": (artifact.get("training_gate") or {}).get("training_gate"),
        "split_candidate_assessments": artifact.get("split_candidate_assessments"),
        "next_engineering_action": artifact["next_engineering_action"],
        "best_sha256": BEST_SHA,
        "boundary_redefinition_after_sha256": redef_after["artifact_sha256"],
        "train": False,
        "reserve_scored": False,
        "moves_best": False,
    }
    (DEST / "EXCLUSIVE_DEFINITIONS_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2), flush=True)
    return 0


def outer() -> int:
    # Acquire runs on host (needs network); reseal needs GPU docker.
    # Single outer path: host acquire+encode via docker for whole inner.
    script = Path(__file__).resolve()
    command = [
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
        "-e",
        f"PYTHONPATH={REPO}/scripts/shadow",
        "-w",
        str(REPO),
        IMAGE,
        "python3",
        str(script),
        "--inner",
    ]
    print("launching docker exclusive-definition pass", flush=True)
    return subprocess.call(command)


if __name__ == "__main__":
    if "--inner" in sys.argv:
        raise SystemExit(inner())
    raise SystemExit(outer())
