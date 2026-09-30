"""Seal HYPERLEX_ACTIVE_FAMILY_POST_MERGE_RESIDUAL_REVIEW_V1.

Read-only residual diagnosis after APPLY_ONTOLOGY_MERGE_PAIR. Does not mutate
ontology, train, score the reserve, or move BEST.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
MERGE_DIR = Path("/home/morpheus/hlx-private/classification-v2-ontology-merge-pair-20260930")
MERGE = MERGE_DIR / "ONTOLOGY_MERGE_PAIR.json"
MERGE_SHA = "c901badb70c0c72f1af20fe4dd0b64bcbdfad917568682e9abb2cc9321ad69d5"
EXPORT = MERGE_DIR / "civilian.v0.6.merge.jsonl"
EXPORT_SHA = "a8c064151973d7b2b9f439dc9fab499c69c2dd8a22a19206d7f486d970975130"
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
DEST = Path("/home/morpheus/hlx-private/classification-v2-post-merge-residual-review-20260930")

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


def main() -> int:
    from hyperlexical.classification_v2 import canonical_json, sha256_text
    from hyperlexical.classification_v2_ontology_merge_pair import (
        FORWARD_ACTIVE_FAMILY_VOCABULARY,
        FORWARD_COLLAPSE_CLUSTER,
        KEEP_FAMILY,
        MERGED_LABEL,
    )
    from hyperlexical.classification_v2_post_merge_residual_review import (
        MERGE_PAIR_ARTIFACT_SHA,
        analyze_se_rd,
        assemble_residual_review,
        decide_residual_recommendation,
        degree_table,
        largest_component_members,
        residual_review_contract,
    )
    from hyperlexical.classification_v2_separability_audit import definition_sources
    from hyperlexical.identity_ledger import IdentityLedger, derived_state

    if MERGE_PAIR_ARTIFACT_SHA != MERGE_SHA:
        fail("merge artifact pin drift")
    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if sha256_file(EXPORT) != EXPORT_SHA:
        fail("merge export changed")
    merge = json.loads(MERGE.read_text(encoding="utf-8"))
    if merge.get("artifact_sha256") != MERGE_SHA:
        fail("merge artifact hash mismatch")
    if merge.get("merge_application_state") != "APPLIED":
        fail("merge not applied")

    pairs = list(merge.get("overlap_post_pairs") or [])
    if len(pairs) != int(merge["overlap_post"]["high_overlap_pair_count"]):
        fail("overlap pair count mismatch")

    top_pairs = sorted(
        pairs,
        key=lambda item: (
            -float(item.get("cosine") or 0.0),
            str(item.get("family_a")),
            str(item.get("family_b")),
        ),
    )[:20]
    degrees = degree_table(pairs)
    component = largest_component_members(pairs, FORWARD_COLLAPSE_CLUSTER)

    rows = [
        json.loads(line)
        for line in EXPORT.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    ledger = IdentityLedger.load(str(LEDGER))
    states = {digest: derived_state(record) for digest, record in ledger.identities.items()}
    train_sources = definition_sources(
        rows, states, split="train", vocabulary=FORWARD_ACTIVE_FAMILY_VOCABULARY
    )["sources"]
    texts_se = [str(row.get("text") or "") for row in train_sources[MERGED_LABEL]["rows"]]
    texts_rd = [str(row.get("text") or "") for row in train_sources[KEEP_FAMILY]["rows"]]
    se_rd_cosine = None
    for pair in pairs:
        if {pair.get("family_a"), pair.get("family_b")} == {MERGED_LABEL, KEEP_FAMILY}:
            se_rd_cosine = float(pair["cosine"])
            break
    se_rd = analyze_se_rd(texts_se=texts_se, texts_rd=texts_rd, cosine=se_rd_cosine)

    reduction = {
        "absolute_reduction": merge.get("overlap_absolute_reduction"),
        "percentage_reduction": merge.get("overlap_percentage_reduction"),
    }
    recommendation = decide_residual_recommendation(
        se_rd=se_rd,
        degrees=degrees,
        overlap_post=merge["overlap_post"],
        overlap_reduction_pct=float(reduction["percentage_reduction"] or 0.0),
        collapse_pre=int(merge["overlap_pre"]["largest_collapse_component"]),
        collapse_post=int(merge["overlap_post"]["largest_collapse_component"]),
    )
    artifact = assemble_residual_review(
        {
            "degrees": degrees,
            "largest_component": component,
            "overlap_post": merge["overlap_post"],
            "overlap_pre": merge["overlap_pre"],
            "overlap_reduction": reduction,
            "recommendation": recommendation,
            "se_rd_analysis": se_rd,
            "top_pairs": top_pairs,
        }
    )
    artifact["contract"] = residual_review_contract()
    artifact["artifact_sha256"] = sha256_text(
        canonical_json({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    )

    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")

    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    destination = DEST / "POST_MERGE_RESIDUAL_REVIEW.json"
    destination.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "artifact_sha256": artifact["artifact_sha256"],
        "best_sha256": BEST_SHA,
        "collapse_component_after": artifact["collapse_component_after"],
        "collapse_component_before": artifact["collapse_component_before"],
        "destination": str(destination),
        "hub_families": artifact.get("hub_families"),
        "largest_component_members": artifact["largest_component_members"],
        "merge_pair_artifact_sha256": MERGE_SHA,
        "moves_best": False,
        "next_engineering_action": artifact["next_engineering_action"],
        "overlap_percentage_reduction": artifact["overlap_percentage_reduction"],
        "overlap_post": artifact["overlap_post"],
        "overlap_pre": artifact["overlap_pre"],
        "primary_recommendation": artifact["primary_recommendation"],
        "rationale": artifact["rationale"],
        "relationship_dating_lexically_distinct": se_rd["lexically_distinct"],
        "relationship_dating_status": artifact["relationship_dating_status"]["family"],
        "residual_blockers": artifact["residual_blockers"],
        "se_rd_cosine": se_rd.get("cosine"),
        "top_hubs": degrees[:6],
        "train": False,
        "training_gate": artifact["training_gate"],
        "reserve_scored": False,
        "applies_ontology_change": False,
    }
    (DEST / "POST_MERGE_RESIDUAL_REVIEW_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
