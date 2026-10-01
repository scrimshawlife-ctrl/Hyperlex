"""CPU tests for V6 human ontology settlement."""

from __future__ import annotations

from hyperlexical.classification_v6_human_ontology_settlement import (
    FINAL_ONTOLOGY_ID,
    NEXT_REBUILD,
    STABILITY_CRITERIA,
    annotate_protocol_a,
    annotate_protocol_b,
    build_settlement_receipt,
    dual_annotate_rows,
    agreement_report,
    final_ontology,
    settle_boundaries,
)


def test_criteria_frozen_and_dual_protocols_independent():
    assert STABILITY_CRITERIA["frozen_before_review"] is True
    text = "A derogatory insult about a dating partner on a betting odds forum."
    a = annotate_protocol_a(text)
    b = annotate_protocol_b(text)
    assert a["rater"] != b["rater"]
    assert "evaluative_stance" in a["functions"] or "evaluative_stance" in b["functions"]


def test_identity_context_and_settlement_ready():
    rows = [
        {"identity": "1", "text": "An Abkhazian; a native or inhabitant of Abkhazia."},
        {"identity": "2", "text": "Casino blackjack odds and bookmaker vig."},
        {"identity": "3", "text": "Bitcoin airdrop on the ethereum blockchain."},
        {"identity": "4", "text": "Romantic dating and courtship between partners."},
        {"identity": "5", "text": "A pejorative slur used as an insult."},
        {"identity": "6", "text": "The slaughter of animals to limit disease."},
        {"identity": "7", "text": "Software programming debugger for computer code."},
        {"identity": "8", "text": "LLM prompt for an agentic assistant."},
        {"identity": "9", "text": "Image macro meme and copypasta format."},
        {"identity": "10", "text": "I bet that it rains tomorrow."},
    ]
    ann = dual_annotate_rows(rows)
    rep = agreement_report(ann)
    assert rep["n_rows"] == 10
    settlement = settle_boundaries(rep, ann)
    assert settlement["identity_affiliation"]["decision"] == "CONTEXT_ONLY"
    assert settlement["evaluative_vs_relational"]["decision"] == "SEPARATE_COMPATIBLE_LABELS"
    assert "STRICT_GAMBLING" in settlement["gambling_vs_crypto"]["decision"]
    final = final_ontology(settlement)
    assert final["FINAL_ONTOLOGY_ID"] == FINAL_ONTOLOGY_ID
    assert final["structure"] == "HIERARCHICAL_MULTI_LABEL"
    receipt = build_settlement_receipt(
        code_revision="deadbeef",
        annotated=ann,
        agreement=rep,
        settlement=settlement,
        migration_counts={"AUTO_MIGRATABLE": 1},
        resettlement_queue={"NEEDS_ROW_LEVEL_HUMAN_RESETTLEMENT": 0},
        geometry={"used_to_decide": False},
        support_viable=True,
        settled_at="2026-10-01T00:00:00Z",
    )
    assert receipt["V6_ONTOLOGY_STATE"] == "V6_ONTOLOGY_READY"
    assert receipt["NEXT_ACTION"] == NEXT_REBUILD
    assert receipt["GEOMETRY_USED_TO_DECIDE_ONTOLOGY"] is False
    assert receipt["QUAL_ROWS_INSPECTED"] is False
