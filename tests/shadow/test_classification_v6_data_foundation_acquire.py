"""CPU tests for V6 foundation acquisition helpers."""

from __future__ import annotations

from collections import Counter

from hyperlexical.classification_v6_data_foundation_acquire import (
    assign_split,
    disjointness_report,
    enforce_train_family_cap,
    finalize_candidate,
    label_source_correlation,
)


def _row(text: str, family: str | None, label: str, split_hint: str | None = None) -> dict:
    raw = {
        "text": text,
        "evidence_label": label,
        "evidence_subtype": "POSITIVE_EVIDENCE"
        if label == "EVIDENCE_PRESENT"
        else "ORDINARY_DOMAIN_NONE",
        "gold_family": family,
        "source_url": f"https://example.test/{text}",
        "source_family": f"test:{family or 'none'}",
        "provenance": "OBSERVED",
        "construction_tag": "NATURAL",
        "topic_domain": family or "mycology",
    }
    out = finalize_candidate(raw)
    assert out is not None
    if split_hint:
        out["split"] = split_hint
    return out


def test_assign_split_bucket_distribution():
    counts = Counter(assign_split(str(i)) for i in range(5000))
    assert counts["TRAIN"] > counts["DEVELOPMENT_VALIDATION"]
    assert counts["REPRESENTATIVE_VALIDATION"] > counts["QUALIFICATION"]
    assert counts["QUALIFICATION"] > 0


def test_train_family_cap():
    families = [
        "memetic",
        "gaming-meta",
        "crypto-degen",
        "internet-slang",
        "technology-ai",
        "sports-competition",
        "music-entertainment",
        "fashion-aesthetic",
        "workplace-career",
        "politics-civic",
    ]
    rows = []
    for fam in families:
        n = 80 if fam == "memetic" else 25
        for i in range(n):
            rows.append(
                _row(
                    f"{fam} example number {i} with enough prose text for celling.",
                    fam,
                    "EVIDENCE_PRESENT",
                    "TRAIN",
                )
            )
    capped = enforce_train_family_cap(rows, max_share=0.15)
    present = [r for r in capped if r["evidence_label"] == "EVIDENCE_PRESENT"]
    shares = Counter(r["gold_family"] for r in present)
    assert len(shares) >= 8
    assert max(shares.values()) / len(present) <= 0.15 + 1e-9
    # Dominant family is reduced vs raw 80/total but may still lead under the share cap.
    assert shares["memetic"] < 80


def test_disjointness_and_shortcut():
    a = _row("Ordinary botanical prose about spores and caps.", None, "NO_EVIDENCE", "TRAIN")
    b = _row(
        "A distinct memetic phrase about viral image macros.",
        "memetic",
        "EVIDENCE_PRESENT",
        "DEVELOPMENT_VALIDATION",
    )
    report = disjointness_report(
        {"TRAIN": [a], "DEVELOPMENT_VALIDATION": [b]},
        {
            "blocked_ids": set(),
            "blocked_src": set(),
            "blocked_near": set(),
            "blocked_text": set(),
        },
    )
    assert report["pass"] is True
    corr = label_source_correlation([a, b] * 15)
    assert corr["n"] == 30
