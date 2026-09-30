"""AUDIT_V5_UNCERTAIN_LABEL_SURFACE — read-only fail-closed audit.

Does not train, relabel, retune thresholds, consume reserve, or move BEST.
Missing metadata stays missing. Zero-support reasons stay NO_DATA.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
SURFACE = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-negative-evidence-surface-v1r8-20260930"
)
DATASET = SURFACE / "EVIDENCE_SURFACE.jsonl"
DATASET_SHA = "c0fdd82d1734585a7d852318ac5b390cc5e2c50908c0ef9f9eba4b3f7ebedc8b"
PARENT_AUTH = Path(
    "/home/morpheus/hlx-private/classification-v5-stage-a-train-v1r8-20260930"
)
LABEL_PROVENANCE = PARENT_AUTH / "LABEL_PROVENANCE.jsonl"
AUTH_003 = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-train-v1r8-003-focal-20260930"
)
RUN_003 = AUTH_003 / "classification-v5-stage-a-003"
SELECTED = RUN_003 / "selected" / "model.safetensors"
SELECTED_SHA = "dba6d49103d7c895d7febc46c81491a07ea19acd551f86b3a9fd9f0a1c0782a3"
VAL_SCORES = (
    RUN_003
    / "diagnostics"
    / "uncertain_policy_investigation"
    / "VALIDATION_SCORES.jsonl"
)
DEST = RUN_003 / "diagnostics" / "uncertain_label_surface_audit"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
DIAG_NONE = 0.50
DIAG_PRESENT = 0.55

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
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def classify_present_fn(item: dict) -> str:
    p_none = float(item["P_NO_EVIDENCE"])
    p_pres = float(item["P_EVIDENCE_PRESENT"])
    p_unc = float(item["P_UNCERTAIN"])
    margin = float(item["margin_top1_top2"])
    if p_none >= 0.80 and p_pres <= 0.20:
        return "NONE_DOMINATED"
    if item.get("top1") == "UNCERTAIN" or (p_unc >= 0.30 and float(item["entropy"]) >= 0.9):
        return "GENUINELY_UNCERTAIN"
    if margin < 0.10 and max(p_none, p_pres, p_unc) < 0.70:
        return "LOW_MARGIN_PRESENT"
    if 0.20 < p_pres < 0.55 and p_none >= p_pres:
        return "CALIBRATION_SHIFT"
    if p_none >= p_pres:
        return "NONE_DOMINATED"
    return "LOW_MARGIN_PRESENT"


def entropy(probs: dict[str, float]) -> float:
    h = 0.0
    for p in probs.values():
        if p > 0:
            h -= p * math.log(p + 1e-12)
    return h


def audit_inner() -> int:
    import torch
    from torch import nn
    from transformers import AutoModel, AutoTokenizer
    from safetensors.torch import load_file

    from hyperlexical.classification_v2_surface import surface_form, word_count
    from hyperlexical.classification_v5_stage_a import (
        EVIDENCE_LABELS,
        TRAIN_HYPERPARAMS,
        decide_evidence,
        softmax_logits,
    )
    from hyperlexical.classification_v5_stage_a_uncertain_label_surface_audit import (
        FROZEN_AMBIGUITY_REASONS,
        MISSING_FIELD,
        NO_DATA,
        NOT_APPLICABLE,
        NOT_COMPUTABLE,
        OBSERVED_VALUE,
        classify_boundary,
        coverage,
        data_completeness_blocks_clean,
        decide_diagnosis,
        gold_consistency_flag,
        metric_with_denominator,
        reason_support_table,
        required_field_bundle,
        valid_probabilities,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.layout import HIDDEN
    from hyperlexical.save_pretrained import split_weight_tensors

    if sha256_file(DATASET) != DATASET_SHA:
        fail("dataset digest mismatch")
    if sha256_file(SELECTED) != SELECTED_SHA:
        fail("SELECTED digest mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST digest mismatch")
    if not LABEL_PROVENANCE.exists():
        fail("label provenance missing")
    if not VAL_SCORES.exists():
        fail("parent validation scores missing; run uncertain-policy investigate first")

    rows = load_jsonl(DATASET)
    prov_by_id: dict[str, dict] = {}
    with LABEL_PROVENANCE.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                item = json.loads(line)
                prov_by_id[str(item["identity"])] = item

    uncertain_rows = [
        r for r in rows if str(r.get("evidence_label")) == "UNCERTAIN"
    ]
    present_rows = [
        r for r in rows if str(r.get("evidence_label")) == "EVIDENCE_PRESENT"
    ]
    none_rows = [r for r in rows if str(r.get("evidence_label")) == "NO_EVIDENCE"]

    # 1. Per-row audit records (metadata)
    audited = []
    missing_field_counts: Counter = Counter()
    train_reason = Counter()
    val_reason = Counter()
    n_missing_required = 0
    n_reason_observed = 0

    for row in uncertain_rows:
        identity = str(row.get("identity") or "")
        lp_row = prov_by_id.get(identity) or {}
        lp = lp_row.get("label_provenance") if isinstance(lp_row.get("label_provenance"), dict) else None
        source_prov = lp_row.get("source_provenance")
        if source_prov is None:
            source_prov = row.get("provenance")
        bundle = required_field_bundle(
            row, label_provenance=lp, source_provenance=source_prov
        )
        if bundle["audit_row_state"] == MISSING_FIELD:
            n_missing_required += 1
            for field in bundle["missing_required_fields"]:
                missing_field_counts[field] += 1
        if bundle["ambiguity_reason_state"] == OBSERVED_VALUE:
            n_reason_observed += 1
            reason = bundle["fields"]["ambiguity_reason"]
            if row.get("split") == "train":
                train_reason[reason] += 1
            elif row.get("split") == "validation":
                val_reason[reason] += 1

        # Optional fields — never invent
        domain = row.get("topic_domain")
        domain_state = OBSERVED_VALUE if domain not in (None, "") else MISSING_FIELD
        paired = row.get("paired_positive_identity")
        if paired in (None, "", []):
            # pairwise acquisition only
            paired_state = NOT_APPLICABLE if row.get("pair_group_id") in (None, "") else MISSING_FIELD
            paired_value = None
        else:
            paired_state = OBSERVED_VALUE
            paired_value = paired
        family = row.get("active_family_support")
        family_state = OBSERVED_VALUE if family not in (None,) else MISSING_FIELD
        # definition_style is not a stored field
        definition_style_state = MISSING_FIELD

        form = surface_form(str(row.get("text") or ""))
        tokens = word_count(str(row.get("text") or ""))

        audited.append(
            {
                "identity": identity,
                "text": row.get("text"),
                "split": row.get("split"),
                "audit_row_state": bundle["audit_row_state"],
                "fields": bundle["fields"],
                "field_states": bundle["field_states"],
                "missing_required_fields": bundle["missing_required_fields"],
                "optional": {
                    "active_family_support": {
                        "value": family,
                        "field_state": family_state,
                    },
                    "paired_identities": {
                        "value": paired_value,
                        "field_state": paired_state,
                    },
                    "domain": {"value": domain, "field_state": domain_state},
                    "definition_style": {
                        "value": None,
                        "field_state": definition_style_state,
                    },
                    "evidence_spans": {
                        "value": row.get("evidence_spans"),
                        "field_state": OBSERVED_VALUE
                        if row.get("evidence_spans") not in (None,)
                        else MISSING_FIELD,
                    },
                },
                "surface_form": form,
                "token_length": tokens,
                "source_url_present": bool(row.get("source_url")),
            }
        )

    reason_table = reason_support_table(train_reason, val_reason)
    write_private(
        DEST / "UNCERTAIN_ROWS.jsonl",
        "\n".join(json.dumps(item, sort_keys=True) for item in audited) + "\n",
    )

    # Support summary
    support = {
        "UNCERTAIN_train_count": sum(1 for r in uncertain_rows if r.get("split") == "train"),
        "UNCERTAIN_validation_count": sum(
            1 for r in uncertain_rows if r.get("split") == "validation"
        ),
        "by_ambiguity_reason": reason_table,
        "by_source": dict(Counter(
            (a["fields"]["source_identity"] if a["field_states"]["source_identity"] == OBSERVED_VALUE else MISSING_FIELD)
            for a in audited
        )),
        "by_domain": dict(Counter(
            (a["optional"]["domain"]["value"]
             if a["optional"]["domain"]["field_state"] == OBSERVED_VALUE
             else MISSING_FIELD)
            for a in audited
        )),
        "by_ATOM_PROSE": dict(Counter(a["surface_form"] for a in audited)),
        "by_provenance": dict(Counter(
            (a["fields"]["source_provenance"]
             if a["field_states"]["source_provenance"] == OBSERVED_VALUE
             else MISSING_FIELD)
            for a in audited
        )),
        "by_label_authority": dict(Counter(
            (a["fields"]["label_authority"]
             if a["field_states"]["label_authority"] == OBSERVED_VALUE
             else MISSING_FIELD)
            for a in audited
        )),
        "by_label_derivation": dict(Counter(
            (a["fields"]["label_derivation"]
             if a["field_states"]["label_derivation"] == OBSERVED_VALUE
             else MISSING_FIELD)
            for a in audited
        )),
    }
    write_private(DEST / "SUPPORT_SUMMARY.json", support)

    # Completeness
    n_unc = len(uncertain_rows)
    missing_required_frac = n_missing_required / n_unc if n_unc else 1.0
    reason_cov = n_reason_observed / n_unc if n_unc else 0.0

    # Load val scores for PRESENT FN cohorts + probability on val UNCERTAIN
    val_score_by_id = {
        str(item["identity"]): item for item in load_jsonl(VAL_SCORES)
    }

    # Score all UNCERTAIN with SELECTED for head-signal (train+val)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("CUDA required for frozen representation/probability audit")

    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tokenizer.padding_side = "right"
    # SELECTED reconstruct for probabilities
    encoder_sel = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    warm = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    apply_encoder_trainable(encoder_sel, warm.get("encoder") or {})
    head = nn.Linear(HIDDEN, len(EVIDENCE_LABELS))
    packed = split_weight_tensors(load_file(str(SELECTED), device="cpu"))
    apply_encoder_trainable(encoder_sel, packed.get("encoder") or {})
    head_w = packed.get("evidence_head") or {}
    with torch.no_grad():
        head.weight.copy_(head_w["weight"])
        head.bias.copy_(head_w["bias"])
    encoder_sel.to(device)
    head.to(device)
    encoder_sel.eval()
    head.eval()

    unc_probs: dict[str, dict] = {}
    max_len = int(TRAIN_HYPERPARAMS["max_len"])
    with torch.no_grad():
        for row in uncertain_rows:
            encoded = tokenizer(
                [str(row["text"])],
                padding=True,
                truncation=True,
                max_length=max_len,
                return_tensors="pt",
            )
            encoded = {k: v.to(device) for k, v in encoded.items()}
            pooled = encoder_sel(**encoded).last_hidden_state[:, 0]
            logits = head(pooled)[0].detach().cpu().tolist()
            probs = softmax_logits(logits)
            ordered = sorted(probs.items(), key=lambda item: item[1], reverse=True)
            decision = decide_evidence(
                float(probs["EVIDENCE_PRESENT"]),
                none_threshold=DIAG_NONE,
                present_threshold=DIAG_PRESENT,
            )
            payload = {
                "P_NO_EVIDENCE": probs["NO_EVIDENCE"],
                "P_EVIDENCE_PRESENT": probs["EVIDENCE_PRESENT"],
                "P_UNCERTAIN": probs["UNCERTAIN"],
                "entropy": entropy(probs),
                "top1": ordered[0][0],
                "top2": ordered[1][0],
                "margin_top1_top2": ordered[0][1] - ordered[1][1],
                "decision_scalar_0_50_0_55": decision,
            }
            valid, state = valid_probabilities(payload)
            unc_probs[str(row["identity"])] = {
                **payload,
                "probability_state": state,
                "valid": valid,
            }

    # Free SELECTED encoder before BEST embed pass (memory)
    del encoder_sel, head
    torch.cuda.empty_cache()

    # Frozen BEST embeddings for representation NN
    encoder_best = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    apply_encoder_trainable(
        encoder_best,
        split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu")).get("encoder")
        or {},
    )
    encoder_best.to(device)
    encoder_best.eval()

    @torch.no_grad()
    def embed_rows(row_list: list[dict]) -> torch.Tensor:
        vectors = []
        bs = 32
        for start in range(0, len(row_list), bs):
            batch = row_list[start : start + bs]
            encoded = tokenizer(
                [str(r["text"]) for r in batch],
                padding=True,
                truncation=True,
                max_length=256,
                return_tensors="pt",
            )
            encoded = {k: v.to(device) for k, v in encoded.items()}
            pooled = encoder_best(**encoded).last_hidden_state[:, 0]
            pooled = torch.nn.functional.normalize(pooled, dim=-1)
            vectors.append(pooled.cpu())
        return torch.cat(vectors, dim=0) if vectors else torch.empty(0, HIDDEN)

    unc_sorted = sorted(uncertain_rows, key=lambda r: str(r["identity"]))
    present_sorted = sorted(present_rows, key=lambda r: str(r["identity"]))
    none_sorted = sorted(none_rows, key=lambda r: str(r["identity"]))
    emb_unc = embed_rows(unc_sorted)
    emb_present = embed_rows(present_sorted)
    emb_none = embed_rows(none_sorted)

    present_ids = [str(r["identity"]) for r in present_sorted]
    none_ids = [str(r["identity"]) for r in none_sorted]
    unc_ids = [str(r["identity"]) for r in unc_sorted]

    # Representation diagnostics per UNCERTAIN row
    rep_by_id: dict[str, dict] = {}
    n_rep_ok = 0
    if emb_unc.numel() and emb_present.numel() and emb_none.numel():
        sim_p = emb_unc @ emb_present.T
        sim_n = emb_unc @ emb_none.T
        for i, identity in enumerate(unc_ids):
            np_cos = float(sim_p[i].max().item())
            nn_cos = float(sim_n[i].max().item())
            np_idx = int(sim_p[i].argmax().item())
            nn_idx = int(sim_n[i].argmax().item())
            margin = np_cos - nn_cos
            klass, bstate = classify_boundary(np_cos, nn_cos)
            rep_by_id[identity] = {
                "nearest_present_cosine": np_cos,
                "nearest_none_cosine": nn_cos,
                "present_minus_none_margin": margin,
                "nearest_present_identity": present_ids[np_idx],
                "nearest_none_identity": none_ids[nn_idx],
                "boundary_class": klass,
                "boundary_state": bstate,
            }
            if bstate == OBSERVED_VALUE:
                n_rep_ok += 1
    else:
        for identity in unc_ids:
            rep_by_id[identity] = {
                "nearest_present_cosine": NOT_COMPUTABLE,
                "nearest_none_cosine": NOT_COMPUTABLE,
                "present_minus_none_margin": NOT_COMPUTABLE,
                "nearest_present_identity": None,
                "nearest_none_identity": None,
                "boundary_class": None,
                "boundary_state": NOT_COMPUTABLE,
                "blocker": "embedding_pool_unavailable",
            }

    # Gold consistency + boundary flags
    gold_flags = Counter()
    boundary_counts = Counter()
    for item in audited:
        identity = item["identity"]
        rep = rep_by_id.get(identity) or {
            "boundary_class": None,
            "boundary_state": NOT_COMPUTABLE,
        }
        flag = gold_consistency_flag(
            audit_row_state=item["audit_row_state"],
            fields=item["fields"],
            boundary_class=rep.get("boundary_class"),
            boundary_state=str(rep.get("boundary_state")),
        )
        # If required fields missing and reason missing → REASON_UNDERDEFINED already
        if item["audit_row_state"] == MISSING_FIELD and "ambiguity_reason" in item[
            "missing_required_fields"
        ]:
            flag = "REASON_UNDERDEFINED"
        item["gold_consistency_flag"] = flag
        item["representation"] = rep
        gold_flags[flag] += 1
        if rep.get("boundary_class"):
            boundary_counts[rep["boundary_class"]] += 1
        elif rep.get("boundary_state") == NOT_COMPUTABLE:
            boundary_counts[NOT_COMPUTABLE] += 1

    write_private(
        DEST / "GOLD_CONSISTENCY.json",
        {
            "flags": dict(gold_flags),
            "n": n_unc,
            "rule": "diagnostic_flags_only_no_relabel",
        },
    )
    write_private(
        DEST / "REPRESENTATION_BOUNDARY.json",
        {
            "boundary_class_counts": dict(boundary_counts),
            "encoder": "frozen_BEST_modernbert_cls",
            "best_sha256": BEST_SHA,
            "n_uncertain_embedded": len(unc_ids),
            "n_present_pool": len(present_ids),
            "n_none_pool": len(none_ids),
            "coverage": coverage(n_rep_ok, n_unc),
        },
    )

    # Rewrite UNCERTAIN_ROWS with enriched fields
    write_private(
        DEST / "UNCERTAIN_ROWS.jsonl",
        "\n".join(json.dumps(item, sort_keys=True) for item in audited) + "\n",
    )

    # 4–5 PRESENT FN comparisons using validation scores
    present_fn = {
        "GENUINELY_UNCERTAIN": [],
        "NONE_DOMINATED": [],
        "CALIBRATION_SHIFT": [],
        "LOW_MARGIN_PRESENT": [],
    }
    for item in val_score_by_id.values():
        if item.get("evidence_label") != "EVIDENCE_PRESENT":
            continue
        if item.get("decision_scalar_0_50_0_55") == "EVIDENCE_PRESENT":
            continue
        tax = classify_present_fn(item)
        present_fn.setdefault(tax, []).append(item)

    # Embed PRESENT FN cohorts vs UNCERTAIN centroid / gold labels
    def mean_sim_to_pool(query_rows: list[dict], pool_emb: torch.Tensor) -> dict:
        if not query_rows or pool_emb.numel() == 0:
            return {
                "mean_nearest_cosine": NO_DATA if not query_rows else NOT_COMPUTABLE,
                "n_eligible": 0,
                "state": NO_DATA if not query_rows else NOT_COMPUTABLE,
            }
        # map identities to surface rows for text
        by_id = {str(r["identity"]): r for r in rows}
        qrows = [by_id[str(i["identity"])] for i in query_rows if str(i["identity"]) in by_id]
        if not qrows:
            return {
                "mean_nearest_cosine": NOT_COMPUTABLE,
                "n_eligible": 0,
                "state": NOT_COMPUTABLE,
                "blocker": "fn_identities_not_in_surface",
            }
        qemb = embed_rows(qrows)
        sims = qemb @ pool_emb.T
        nearest = sims.max(dim=1).values.tolist()
        return {
            "mean_nearest_cosine": statistics.fmean(nearest),
            "median_nearest_cosine": statistics.median(nearest),
            "n_eligible": len(nearest),
            "state": OBSERVED_VALUE,
        }

    genuinely = present_fn.get("GENUINELY_UNCERTAIN") or []
    none_dom = present_fn.get("NONE_DOMINATED") or []
    # Expected sealed counts from prior investigate
    if len(genuinely) != 39:
        # soft note — taxonomy recomputed; record actual
        pass

    cmp_gen = {
        "n_genuinely_uncertain_present_fn": len(genuinely),
        "nearest_to_gold_UNCERTAIN": mean_sim_to_pool(genuinely, emb_unc),
        "nearest_to_gold_PRESENT": mean_sim_to_pool(genuinely, emb_present),
        "nearest_to_gold_NONE": mean_sim_to_pool(genuinely, emb_none),
    }
    # resemblance label
    if all(
        isinstance(cmp_gen[k].get("mean_nearest_cosine"), float)
        for k in (
            "nearest_to_gold_UNCERTAIN",
            "nearest_to_gold_PRESENT",
            "nearest_to_gold_NONE",
        )
    ):
        scores = {
            "gold UNCERTAIN": cmp_gen["nearest_to_gold_UNCERTAIN"]["mean_nearest_cosine"],
            "gold PRESENT": cmp_gen["nearest_to_gold_PRESENT"]["mean_nearest_cosine"],
            "gold NONE": cmp_gen["nearest_to_gold_NONE"]["mean_nearest_cosine"],
        }
        closest = max(scores, key=scores.get)
        # boundary conflict if closer to UNCERTAIN than PRESENT by margin and high cos
        conflict = (
            scores["gold UNCERTAIN"] >= scores["gold PRESENT"] + 0.01
            and scores["gold UNCERTAIN"] >= 0.85
            and len(genuinely) >= 10
        )
        cmp_gen["resembles_most"] = closest
        cmp_gen["PRESENT_UNCERTAIN_BOUNDARY_CONFLICT"] = bool(conflict)
        cmp_gen["mean_cosine_by_gold"] = scores
    else:
        cmp_gen["resembles_most"] = NOT_COMPUTABLE
        cmp_gen["PRESENT_UNCERTAIN_BOUNDARY_CONFLICT"] = False
        cmp_gen["blocker"] = "representation_comparison_incomplete"

    cmp_none = {
        "n_none_dominated_present_fn": len(none_dom),
        "nearest_to_gold_UNCERTAIN": mean_sim_to_pool(none_dom, emb_unc),
        "nearest_to_gold_PRESENT": mean_sim_to_pool(none_dom, emb_present),
        "nearest_to_gold_NONE": mean_sim_to_pool(none_dom, emb_none),
    }
    if all(
        isinstance(cmp_none[k].get("mean_nearest_cosine"), float)
        for k in (
            "nearest_to_gold_UNCERTAIN",
            "nearest_to_gold_PRESENT",
            "nearest_to_gold_NONE",
        )
    ):
        scores = {
            "UNCERTAIN-like": cmp_none["nearest_to_gold_UNCERTAIN"]["mean_nearest_cosine"],
            "PRESENT-like": cmp_none["nearest_to_gold_PRESENT"]["mean_nearest_cosine"],
            "NONE-like": cmp_none["nearest_to_gold_NONE"]["mean_nearest_cosine"],
        }
        cmp_none["classification"] = max(scores, key=scores.get)
        cmp_none["mean_cosine_by_class"] = scores
    else:
        cmp_none["classification"] = NOT_COMPUTABLE

    write_private(
        DEST / "PRESENT_FN_COMPARISON.json",
        {
            "GENUINELY_UNCERTAIN": cmp_gen,
            "NONE_DOMINATED": cmp_none,
            "taxonomy_counts_recomputed": {k: len(v) for k, v in present_fn.items()},
            "note": "Diagnostic comparison only; no relabel.",
        },
    )

    # 6. Surface/source balance — UNCERTAIN vs PRESENT vs NONE
    def class_balance(label_rows: list[dict], name: str) -> dict:
        forms = Counter(surface_form(str(r["text"])) for r in label_rows)
        prov = Counter(str(r.get("provenance") or MISSING_FIELD) for r in label_rows)
        domains = Counter()
        n_domain_missing = 0
        for r in label_rows:
            d = r.get("topic_domain")
            if d in (None, ""):
                n_domain_missing += 1
            else:
                domains[str(d)] += 1
        sources = Counter(str(r.get("source_bucket") or MISSING_FIELD) for r in label_rows)
        lengths = [word_count(str(r["text"])) for r in label_rows]
        # definition_style stored field absent → MISSING_FIELD; do not invent rates as stored
        return {
            "n": len(label_rows),
            "ATOM_PROSE": dict(forms),
            "provenance": dict(prov),
            "source_top": dict(sources.most_common(15)),
            "domain_top": dict(domains.most_common(15)),
            "n_domain_missing": n_domain_missing,
            "domain_coverage": coverage(len(label_rows) - n_domain_missing, len(label_rows)),
            "token_length": {
                "mean": statistics.fmean(lengths) if lengths else NO_DATA,
                "median": statistics.median(lengths) if lengths else NO_DATA,
                "n_eligible": len(lengths),
            },
            "definition_style": {
                "field_state": MISSING_FIELD,
                "note": "definition_style not stored on surface rows; not derived in this audit",
            },
            "label": name,
        }

    balance = {
        "UNCERTAIN": class_balance(uncertain_rows, "UNCERTAIN"),
        "EVIDENCE_PRESENT": class_balance(present_rows, "EVIDENCE_PRESENT"),
        "NO_EVIDENCE": class_balance(none_rows, "NO_EVIDENCE"),
        "isolation_flags": [],
    }
    # Source skew: UNCERTAIN almost entirely one provenance/source family
    unc_prov = balance["UNCERTAIN"]["provenance"]
    if unc_prov:
        top_share = max(unc_prov.values()) / max(1, balance["UNCERTAIN"]["n"])
        if top_share >= 0.90:
            balance["isolation_flags"].append("UNCERTAIN_PROVENANCE_ISOLATED")
    unc_src = balance["UNCERTAIN"]["source_top"]
    if unc_src:
        # all under v5_src_inf_AMBIGUOUS*
        ambig_src = sum(v for k, v in unc_src.items() if "AMBIGUOUS_EVIDENCE" in str(k))
        if ambig_src / max(1, balance["UNCERTAIN"]["n"]) >= 0.90:
            balance["isolation_flags"].append("UNCERTAIN_SOURCE_FAMILY_ISOLATED")
    write_private(DEST / "SURFACE_SOURCE_BALANCE.json", balance)

    # 8. Head-signal by ambiguity reason
    head_by_reason = {}
    n_prob_ok = 0
    for reason in FROZEN_AMBIGUITY_REASONS:
        ids = [
            a["identity"]
            for a in audited
            if a["field_states"].get("ambiguity_reason") == OBSERVED_VALUE
            and a["fields"].get("ambiguity_reason") == reason
        ]
        if not ids:
            head_by_reason[reason] = {
                "reason_state": NO_DATA,
                "support": 0,
                "mean_P_UNCERTAIN": NO_DATA,
                "UNCERTAIN_recall": NO_DATA,
                "mean_entropy": NO_DATA,
                "argmax_distribution": NO_DATA,
                "n_eligible": 0,
                "n_excluded_missing": 0,
                "n_excluded_invalid": 0,
            }
            continue
        p_uncs = []
        ents = []
        decisions = []
        top1s = []
        n_excl_inv = 0
        for identity in ids:
            payload = unc_probs.get(identity)
            if not payload or payload.get("probability_state") != OBSERVED_VALUE:
                n_excl_inv += 1
                continue
            p_uncs.append(payload["P_UNCERTAIN"])
            ents.append(payload["entropy"])
            decisions.append(payload["decision_scalar_0_50_0_55"])
            top1s.append(payload["top1"])
            n_prob_ok += 1
        if not p_uncs:
            head_by_reason[reason] = {
                "reason_state": OBSERVED_VALUE,
                "support": len(ids),
                "mean_P_UNCERTAIN": NOT_COMPUTABLE,
                "UNCERTAIN_recall": NOT_COMPUTABLE,
                "mean_entropy": NOT_COMPUTABLE,
                "argmax_distribution": NOT_COMPUTABLE,
                "n_eligible": 0,
                "n_excluded_missing": 0,
                "n_excluded_invalid": n_excl_inv,
                "blocker": "probability_state_invalid_or_missing",
            }
            continue
        recall = sum(1 for d in decisions if d == "UNCERTAIN") / len(decisions)
        head_by_reason[reason] = {
            "reason_state": OBSERVED_VALUE,
            "support": len(ids),
            "mean_P_UNCERTAIN": metric_with_denominator(
                statistics.fmean(p_uncs),
                n_eligible=len(p_uncs),
                n_excluded_invalid=n_excl_inv,
            ),
            "UNCERTAIN_recall": metric_with_denominator(
                recall, n_eligible=len(decisions), n_excluded_invalid=n_excl_inv
            ),
            "mean_entropy": metric_with_denominator(
                statistics.fmean(ents),
                n_eligible=len(ents),
                n_excluded_invalid=n_excl_inv,
            ),
            "argmax_distribution": dict(Counter(top1s)),
            "coverage": coverage(len(p_uncs), len(ids)),
        }
    # Unique-count fix: n_prob_ok counted per reason row; recompute global
    n_prob_ok = sum(
        1
        for identity, payload in unc_probs.items()
        if payload.get("probability_state") == OBSERVED_VALUE
    )
    write_private(DEST / "HEAD_SIGNAL_BY_REASON.json", head_by_reason)

    # Coverages
    prob_cov = coverage(n_prob_ok, n_unc)
    rep_cov = coverage(n_rep_ok, n_unc)
    reason_coverage = coverage(n_reason_observed, n_unc)

    under_supported = [
        reason
        for reason, row in reason_table.items()
        if "UNDER_SUPPORTED_REASON" in row["flags"] and row["reason_state"] != NO_DATA
    ]
    # Also zero-support reasons are under-supported by definition
    under_supported_all = [
        reason
        for reason, row in reason_table.items()
        if "UNDER_SUPPORTED_REASON" in row["flags"]
    ]

    boundary_conflict = bool(cmp_gen.get("PRESENT_UNCERTAIN_BOUNDARY_CONFLICT"))
    source_skew = "UNCERTAIN_SOURCE_FAMILY_ISOLATED" in balance["isolation_flags"] or (
        "UNCERTAIN_PROVENANCE_ISOLATED" in balance["isolation_flags"]
    )
    # Mixed: multiple distinct issues among reason under-support (zeros), skew, too_* flags
    too_present = gold_flags.get("TOO_PRESENT_LIKE", 0)
    too_none = gold_flags.get("TOO_NONE_LIKE", 0)
    mixed_surface = (
        len(under_supported_all) >= 2
        and source_skew
        and (too_present + too_none) > 0
    ) or (source_skew and len([r for r in under_supported_all if reason_table[r]["reason_state"] == NO_DATA]) >= 4)

    data_blocker = data_completeness_blocks_clean(
        uncertain_missing_required_frac=missing_required_frac,
        probability_coverage=prob_cov["coverage"]
        if isinstance(prob_cov["coverage"], float)
        else 0.0,
        representation_coverage=rep_cov["coverage"]
        if isinstance(rep_cov["coverage"], float)
        else 0.0,
        ambiguity_reason_coverage=reason_coverage["coverage"]
        if isinstance(reason_coverage["coverage"], float)
        else 0.0,
    )

    # Clean only if no under-supported reasons with data issues, no skew, no conflict,
    # high semantically_clean share, and no data blocker.
    clean_share = gold_flags.get("SEMANTICALLY_CLEAN", 0) / max(1, n_unc)
    clean_enough = (
        not data_blocker
        and not boundary_conflict
        and not source_skew
        and not under_supported_all
        and clean_share >= 0.80
    )

    # Decision nuance: all non-MULTIPLE reasons are NO_DATA/under-supported →
    # surface is under-supported for the frozen reason vocabulary even if one reason is large.
    if not data_blocker and not boundary_conflict:
        if len([r for r in under_supported_all if reason_table[r]["reason_state"] == NO_DATA]) >= 4:
            # Four+ frozen reasons have zero support → under-supported surface
            primary, next_action = (
                "UNCERTAIN_SURFACE_UNDER_SUPPORTED",
                "EXPAND_V5_UNCERTAIN_SURFACE",
            )
            # But if also source skew, prefer mixed remediation
            if source_skew and (too_none + too_present) / max(1, n_unc) >= 0.25:
                primary, next_action = (
                    "MIXED_UNCERTAIN_SURFACE_FAILURE",
                    "REMEDIATE_V5_UNCERTAIN_SURFACE",
                )
            elif source_skew:
                primary, next_action = (
                    "MIXED_UNCERTAIN_SURFACE_FAILURE",
                    "REMEDIATE_V5_UNCERTAIN_SURFACE",
                )
        else:
            primary, next_action = decide_diagnosis(
                data_completeness_blocker=data_blocker,
                under_supported_reasons=under_supported_all,
                boundary_conflict=boundary_conflict,
                source_skew=source_skew,
                mixed_surface_issues=mixed_surface,
                clean_enough=clean_enough,
            )
    else:
        primary, next_action = decide_diagnosis(
            data_completeness_blocker=data_blocker,
            under_supported_reasons=under_supported_all,
            boundary_conflict=boundary_conflict,
            source_skew=source_skew,
            mixed_surface_issues=mixed_surface or source_skew,
            clean_enough=clean_enough,
        )

    no_data_cohorts = [
        reason
        for reason, row in reason_table.items()
        if row["reason_state"] == NO_DATA
    ]
    not_computable = []
    if definition_style_state := MISSING_FIELD:
        not_computable.append(
            {
                "metric": "definition_style_balance",
                "blocker": "definition_style_field_not_stored",
                "state": NOT_COMPUTABLE,
            }
        )
    low_coverage = []
    for name, cov in (
        ("probability_diagnostics", prob_cov),
        ("representation_diagnostics", rep_cov),
        ("ambiguity_reason", reason_coverage),
    ):
        if cov.get("aggregate_state") == "LOW_COVERAGE":
            low_coverage.append({"aggregate": name, **cov})

    dataset_change_justified = primary in {
        "UNCERTAIN_SURFACE_UNDER_SUPPORTED",
        "UNCERTAIN_BOUNDARY_CONFLICT",
        "UNCERTAIN_SOURCE_SKEW",
        "MIXED_UNCERTAIN_SURFACE_FAILURE",
    }
    architecture_change_justified = False  # audit does not authorize architecture change

    summary = {
        "AUDIT": "AUDIT_V5_UNCERTAIN_LABEL_SURFACE",
        "AUDIT_STATE": "COMPLETE",
        "TRAIN": False,
        "RELABEL": False,
        "BEST": "UNCHANGED",
        "BEST_SHA256": BEST_SHA,
        "RESERVE": "unused",
        "RESERVE_CONSUMED": False,
        "SELECTED_CHECKPOINT_SHA256": SELECTED_SHA,
        "DATASET_SHA256": DATASET_SHA,
        "GOLD_LABEL_MAPPING_RULE": "HYPERLEX_V5_STAGE_A_GOLD_LABEL_MAPPING_V1",
        "SUPPORT_SUMMARY": {
            "UNCERTAIN_train_count": support["UNCERTAIN_train_count"],
            "UNCERTAIN_validation_count": support["UNCERTAIN_validation_count"],
            "by_ambiguity_reason": reason_table,
            "by_provenance": support["by_provenance"],
            "by_ATOM_PROSE": support["by_ATOM_PROSE"],
        },
        "GOLD_CONSISTENCY_FLAGS": dict(gold_flags),
        "REPRESENTATION_BOUNDARY_COUNTS": dict(boundary_counts),
        "PRESENT_FN_COMPARISON": {
            "GENUINELY_UNCERTAIN": cmp_gen,
            "NONE_DOMINATED": cmp_none,
        },
        "SURFACE_ISOLATION_FLAGS": balance["isolation_flags"],
        "HEAD_SIGNAL_BY_REASON": {
            k: {
                "reason_state": v.get("reason_state"),
                "support": v.get("support"),
                "mean_P_UNCERTAIN": v.get("mean_P_UNCERTAIN"),
                "UNCERTAIN_recall": v.get("UNCERTAIN_recall"),
                "argmax_distribution": v.get("argmax_distribution"),
            }
            for k, v in head_by_reason.items()
        },
        "PRIMARY_DIAGNOSIS": primary,
        "NEXT_ACTION": next_action,
        "SMALLEST_JUSTIFIED_REMEDIATION": next_action,
        "DATASET_CHANGE_JUSTIFIED": dataset_change_justified,
        "ARCHITECTURE_CHANGE_JUSTIFIED": architecture_change_justified,
        "DATA_COMPLETENESS_BLOCKER": data_blocker,
        "REQUIRED_FIELD_COMPLETENESS": {
            "n_uncertain": n_unc,
            "n_missing_required_rows": n_missing_required,
            "missing_required_frac": missing_required_frac,
            "missing_field_counts": dict(missing_field_counts),
        },
        "PROBABILITY_DIAGNOSTIC_COVERAGE": prob_cov,
        "REPRESENTATION_DIAGNOSTIC_COVERAGE": rep_cov,
        "AMBIGUITY_REASON_COVERAGE": reason_coverage,
        "NO_DATA_COHORTS": no_data_cohorts,
        "NOT_COMPUTABLE_METRICS": not_computable,
        "LOW_COVERAGE_AGGREGATES": low_coverage,
        "CRITICAL_INVARIANT": (
            "Absence of evidence in the dataset is not evidence for NO_EVIDENCE, "
            "and missing metadata is never a semantic label."
        ),
        "private_diagnostics_dir": str(DEST),
    }
    write_private(DEST / "SUMMARY.json", summary)
    write_private(AUTH_003 / "UNCERTAIN_LABEL_SURFACE_AUDIT_SUMMARY.json", summary)

    auth = json.loads((AUTH_003 / "AUTHORIZATION.json").read_text(encoding="utf-8"))
    auth["UNCERTAIN_LABEL_SURFACE_AUDIT"] = "COMPLETE"
    auth["UNCERTAIN_LABEL_SURFACE_PRIMARY_DIAGNOSIS"] = primary
    auth["NEXT_ACTION"] = next_action
    auth["TRAIN"] = False
    auth["BEST"] = "UNCHANGED"
    auth["RESERVE"] = "unused"
    auth["RESERVE_CONSUMED"] = False
    write_private(AUTH_003 / "AUTHORIZATION.json", auth)

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def main() -> int:
    if os.environ.get("HLX_V5_STAGE_A_AUDIT_INNER") == "1":
        DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
        return audit_inner()

    if sha256_file(DATASET) != DATASET_SHA:
        fail("dataset digest mismatch")
    if sha256_file(SELECTED) != SELECTED_SHA:
        fail("SELECTED digest mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST digest mismatch")
    print(
        json.dumps(
            {
                "AUDIT": "AUDIT_V5_UNCERTAIN_LABEL_SURFACE",
                "TRAIN": False,
                "RELABEL": False,
                "SELECTED_SHA": SELECTED_SHA,
                "DATASET_SHA": DATASET_SHA,
                "BEST_SHA": BEST_SHA,
                "launch": "docker_gpu_readonly_audit",
            },
            indent=2,
            sort_keys=True,
        ),
        flush=True,
    )
    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    cmd = [
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
        "HLX_V5_STAGE_A_AUDIT_INNER=1",
        "--entrypoint",
        "python3",
        IMAGE,
        str(
            REPO
            / "scripts/spark/run_classification_v5_stage_a_uncertain_label_surface_audit.py"
        ),
    ]
    log_path = AUTH_003 / "uncertain_label_surface_audit_console.log"
    with log_path.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(
            cmd, check=False, stdout=handle, stderr=subprocess.STDOUT
        )
    try:
        print(log_path.read_text(encoding="utf-8")[-20000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
