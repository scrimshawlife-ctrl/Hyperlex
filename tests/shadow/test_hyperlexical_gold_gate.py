"""Original-gold gate for Moltbook and seed_examples unbind export.

Token rule is ``selection_surface.surface_tokens`` / ``lenient_copy_hit``
(the lenient-copy check): whitespace split, text after the first colon,
then ``.lower()``. Not a substring search. Punctuation stays on the token.

``kdr`` inside ``kdrama`` does not match. ``KDR.`` is the token ``kdr.`` and
does not match filler ``KDR``. A colon-tagged atom ``TOKEN:rizz`` does match
filler ``rizz``.
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.export import (  # noqa: E402
    _row,
    export_dataset,
    harvest_backfill,
    harvest_dialect,
    harvest_moltbook,
    harvest_negatives,
    harvest_seed_examples,
    harvest_unbind,
    original_gold_unbind_verdict,
    summarize_gold_demotions,
)
from hyperlexical.selection_surface import surface_tokens  # noqa: E402


def _molt_line(**overrides):
    row = {
        "text": "alpha beta",
        "split": "train",
        "lineage": "ai-native",
        "typology": ["memory"],
        "stage": "circulating",
        "roles": ["episodic"],
        "fillers": ["alpha"],
        "role_scheme": "type_slot",
        "provenance": {"source": "moltbook", "class": "INFERRED"},
        "class": "INFERRED",
        "license": "MIT (distilled)",
    }
    row.update(overrides)
    return json.dumps(row)


def _write_molt(root: pathlib.Path, lines: list[str]) -> None:
    path = root / "data" / "moltbook_hyperlexical_rows.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_placeholder_general_is_demoted_even_when_token_present():
    text = "a general statement"
    assert "general" in surface_tokens(text)
    assert original_gold_unbind_verdict(text, ["general"]) == (False, "fallback_label")
    assert original_gold_unbind_verdict(text, ["General"]) == (False, "fallback_label")
    # A real token in the same row is not kept. The placeholder is not replaced.
    assert original_gold_unbind_verdict(text, ["general", "statement"]) == (False, "fallback_label")


def test_label_absent_from_text_is_demoted_and_present_token_passes():
    assert original_gold_unbind_verdict("alpha beta", ["nope"]) == (False, "gold_not_in_text")
    assert original_gold_unbind_verdict("alpha beta", ["alpha"]) == (True, None)
    assert original_gold_unbind_verdict("see KDR next", ["KDR"]) == (True, None)
    # Every filler must be a token. No partial keep, no substitute label.
    assert original_gold_unbind_verdict("alpha beta", ["alpha", "nope"]) == (False, "gold_not_in_text")


def test_substring_and_punctuation_follow_surface_tokens():
    """Document the existing helper. Do not treat these as new tokenizer rules."""
    assert surface_tokens("kdrama night") == ["kdrama", "night"]
    assert "kdr" not in surface_tokens("kdrama night")
    assert original_gold_unbind_verdict("kdrama night", ["kdr"]) == (False, "gold_not_in_text")
    assert original_gold_unbind_verdict("kdrama night", ["kdrama"]) == (True, None)

    assert surface_tokens("see KDR. next") == ["see", "kdr.", "next"]
    assert "kdr" not in surface_tokens("see KDR. next")
    assert original_gold_unbind_verdict("see KDR. next", ["KDR"]) == (False, "gold_not_in_text")

    # Same helper: prefix before the first colon is not part of the atom.
    assert surface_tokens("TOKEN:rizz later") == ["rizz", "later"]
    assert original_gold_unbind_verdict("TOKEN:rizz later", ["rizz"]) == (True, None)


def test_harvest_moltbook_demotes_placeholder_and_keeps_grounded_token(tmp_path):
    _write_molt(
        tmp_path,
        [
            _molt_line(text="a general statement", fillers=["general"], roles=["episodic"]),
            _molt_line(text="alpha beta", fillers=["nope"], roles=["episodic"]),
            _molt_line(
                text="see KDR next",
                fillers=["KDR"],
                roles=["TOKEN"],
                **{"class": "OBSERVED"},
            ),
            _molt_line(text="kdrama night", fillers=["kdr"], roles=["TOKEN"]),
            _molt_line(text="alpha beta", fillers=["alpha", "nope"], roles=["a", "b"]),
        ],
    )
    rows = harvest_moltbook(tmp_path)
    by_filler_case = {row["text"]: row for row in rows}

    general = by_filler_case["a general statement"]
    assert general["task"] == "classify"
    assert general["fillers"] == []
    assert general["roles"] == []
    assert general["role_scheme"] is None
    assert general["class"] == "INFERRED"
    assert general["gold_demote_reason"] == "fallback_label"
    assert general["provenance"]["source"] == "moltbook"

    # Two rows share this text; both demotions must drop every filler.
    absent_rows = [row for row in rows if row["text"] == "alpha beta"]
    assert len(absent_rows) == 2
    assert all(row["task"] == "classify" for row in absent_rows)
    assert all(row["fillers"] == [] for row in absent_rows)
    assert all(row["gold_demote_reason"] == "gold_not_in_text" for row in absent_rows)
    assert all(row["class"] == "INFERRED" for row in absent_rows)

    kept = by_filler_case["see KDR next"]
    assert kept["task"] == "classify+unbind"
    assert kept["fillers"] == ["KDR"]
    assert kept["roles"] == ["TOKEN"]
    assert kept["role_scheme"] == "type_slot"
    assert kept["class"] == "OBSERVED"
    assert "gold_demote_reason" not in kept

    substring = by_filler_case["kdrama night"]
    assert substring["task"] == "classify"
    assert substring["fillers"] == []
    assert substring["gold_demote_reason"] == "gold_not_in_text"


def test_passing_moltbook_row_matches_ungated_builder(tmp_path):
    """A grounded row is the same object the exporter built before the gate."""
    _write_molt(
        tmp_path,
        [_molt_line(text="see KDR next", fillers=["KDR"], roles=["TOKEN"], **{"class": "OBSERVED"})],
    )
    got = harvest_moltbook(tmp_path)[0]
    expected = _row(
        text="see KDR next",
        lineage="ai-native",
        typology=["memory"],
        stage="circulating",
        roles=["TOKEN"],
        fillers=["KDR"],
        role_scheme="type_slot",
        task="classify+unbind",
        provenance={"source": "moltbook", "class": "INFERRED"},
        **{"class": "OBSERVED"},
        license="MIT (distilled)",
    )
    assert json.dumps(got, sort_keys=True) == json.dumps(expected, sort_keys=True)


def test_seed_fixture_demotes_general_and_does_not_relabel_kdr(tmp_path):
    path = tmp_path / "data" / "agent_memetics" / "seed_examples.jsonl"
    path.parent.mkdir(parents=True)
    records = [
        {
            "text": "Hello from a quiet desk with no technique token.",
            "labels": {"context_loss": "KDR", "memory_tier": ["episodic"]},
        },
        {
            "text": "Context note with KDR in the sentence.",
            "labels": {"context_loss": "general", "memory_tier": ["episodic"]},
        },
        {
            "text": "see KDR next",
            "labels": {"context_loss": "KDR", "memory_tier": ["episodic"], "provenance": True},
        },
        {
            "text": "No context loss label on this seed.",
            "labels": {"context_loss": None, "memory_tier": ["episodic"]},
        },
    ]
    path.write_text("".join(json.dumps(rec) + "\n" for rec in records), encoding="utf-8")
    rows = harvest_seed_examples(tmp_path)
    by_text = {row["text"]: row for row in rows}
    assert "No context loss label on this seed." not in by_text

    ungrounded = by_text["Hello from a quiet desk with no technique token."]
    assert ungrounded["task"] == "classify"
    assert ungrounded["fillers"] == []
    assert ungrounded["class"] == "INFERRED"
    assert ungrounded["gold_demote_reason"] == "gold_not_in_text"
    assert ungrounded["provenance"]["source"] == "seed_examples"

    labeled_general = by_text["Context note with KDR in the sentence."]
    assert "kdr" in surface_tokens(labeled_general["text"])
    assert labeled_general["task"] == "classify"
    assert labeled_general["fillers"] == []
    assert labeled_general["gold_demote_reason"] == "fallback_label"
    assert labeled_general["class"] == "INFERRED"

    grounded = by_text["see KDR next"]
    assert grounded["task"] == "classify+unbind"
    assert grounded["fillers"] == ["KDR"]
    assert grounded["class"] == "INFERRED"
    assert "gold_demote_reason" not in grounded


def test_real_seed_examples_kdr_cases_demote_without_relabel():
    """The committed seed file. Labels are not edited. ``general`` is not retitled ``kdr``."""
    path = ROOT / "data" / "agent_memetics" / "seed_examples.jsonl"
    kdr = []
    general_post = None
    labeled = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        label = (rec.get("labels") or {}).get("context_loss")
        if isinstance(label, str) and label.strip():
            labeled += 1
        if label == "KDR":
            kdr.append(rec)
        if label == "general" and "kdr" in rec["text"].lower():
            assert general_post is None
            general_post = rec

    assert len(kdr) == 5
    lacking = [rec for rec in kdr if "kdr" not in rec["text"].lower()]
    assert len(lacking) == 4
    for rec in lacking:
        assert original_gold_unbind_verdict(rec["text"], ["KDR"]) == (False, "gold_not_in_text")

    # The fifth KDR label contains the letters kdr, but only as ``KDR.``.
    # surface_tokens keeps the period, so the filler is not a token.
    present = [rec for rec in kdr if "kdr" in rec["text"].lower()]
    assert len(present) == 1
    assert "kdr" not in surface_tokens(present[0]["text"])
    assert "kdr." in surface_tokens(present[0]["text"])
    assert original_gold_unbind_verdict(present[0]["text"], ["KDR"]) == (False, "gold_not_in_text")

    assert general_post is not None
    assert "kdr" in surface_tokens(general_post["text"])
    assert original_gold_unbind_verdict(general_post["text"], ["general"]) == (False, "fallback_label")

    rows = harvest_seed_examples(ROOT)
    assert len(rows) == labeled
    kdr_texts = {rec["text"] for rec in kdr}
    harvested_kdr = [row for row in rows if row["text"] in kdr_texts]
    assert len(harvested_kdr) == 5
    assert all(row["task"] == "classify" for row in harvested_kdr)
    assert all(row["fillers"] == [] for row in harvested_kdr)
    assert all(row["roles"] == [] for row in harvested_kdr)
    assert all(row["role_scheme"] is None for row in harvested_kdr)
    assert all(row["class"] == "INFERRED" for row in harvested_kdr)
    assert all(row["gold_demote_reason"] == "gold_not_in_text" for row in harvested_kdr)

    hit = [row for row in rows if row["text"] == general_post["text"]]
    assert len(hit) == 1
    assert hit[0]["task"] == "classify"
    assert hit[0]["fillers"] == []
    assert hit[0]["class"] == "INFERRED"
    assert hit[0]["gold_demote_reason"] == "fallback_label"


def test_backfill_source_bytes_unchanged_while_moltbook_demotes(tmp_path):
    pack = tmp_path / "data" / "backfill" / "2026"
    pack.mkdir(parents=True)
    (pack / "2026-01-01.json").write_text(
        json.dumps(
            {
                "provenance_default": "OBSERVED",
                "terms": [
                    {"term": "no cap fr", "family_id": "brainrot-aura", "provenance": "OBSERVED"}
                ],
            }
        ),
        encoding="utf-8",
    )
    _write_molt(tmp_path, [_molt_line(text="a general statement", fillers=["general"])])

    got = harvest_backfill(tmp_path)
    assert len(got) == 1
    expected = _row(
        text="no cap fr",
        lineage="brainrot-aura",
        typology=["compression", "status"],
        task="classify",
        provenance="backfill:2026-01-01.json",
        **{"class": "OBSERVED"},
        role_scheme=None,
    )
    assert json.dumps(got[0], sort_keys=True) == json.dumps(expected, sort_keys=True)
    assert "gold_demote_reason" not in got[0]
    assert got[0]["class"] == "OBSERVED"

    demoted = harvest_moltbook(tmp_path)
    assert demoted[0]["gold_demote_reason"] == "fallback_label"
    assert demoted[0]["task"] == "classify"


def test_non_moltbook_sources_stay_byte_identical_in_full_export():
    """Dialect, ordinary-prose negatives, and Spec 004 fixtures are not gated."""
    bundle = export_dataset(ROOT)

    def dumped(rows):
        return sorted(json.dumps(row, sort_keys=True) for row in rows)

    dialect = [row for row in bundle["rows"] if row.get("provenance") == "seed:dialect-e6"]
    negatives = [
        row
        for row in bundle["rows"]
        if str(row.get("provenance") or "").startswith("seed:negative-prose")
    ]
    fixtures = [
        row for row in bundle["rows"] if str(row.get("provenance") or "").startswith("004:")
    ]
    assert dumped(dialect) == dumped(harvest_dialect())
    assert dumped(negatives) == dumped(harvest_negatives())
    # Dedupe can drop a fixture whose key was already emitted. Rows that
    # remain must be byte-identical to the ungated harvest, including split.
    harvested_004 = {row["provenance"]: row for row in harvest_unbind()}
    assert fixtures
    for row in fixtures:
        assert json.dumps(row, sort_keys=True) == json.dumps(
            harvested_004[row["provenance"]], sort_keys=True
        )
    assert all("gold_demote_reason" not in row for row in dialect + negatives + fixtures)

    molt = harvest_moltbook(ROOT)
    seeds = harvest_seed_examples(ROOT)
    assert bundle["counts"]["gold_demoted"] == summarize_gold_demotions(molt + seeds)
    assert bundle["counts"]["gold_demoted"]
    for source, reasons in bundle["counts"]["gold_demoted"].items():
        assert set(reasons) <= {"fallback_label", "gold_not_in_text"}
        assert source
        assert sum(reasons.values()) > 0
