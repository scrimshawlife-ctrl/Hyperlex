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

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.export import (  # noqa: E402
    _row,
    audit_seed_examples_gold,
    dedupe,
    export_dataset,
    gold_demoted_after_dedupe,
    harvest_backfill,
    harvest_dialect,
    harvest_moltbook,
    harvest_negatives,
    harvest_unbind,
    lexical_split,
    original_gold_unbind_verdict,
    provenance_source_tag,
    summarize_gold_demotions,
)
from hyperlexical.selection_surface import row_id, surface_tokens  # noqa: E402


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


def _ungated_moltbook(root: pathlib.Path) -> list[dict]:
    """Main's harvest_moltbook: every ai-native row is classify+unbind."""
    rows = []
    for name in (
        "moltbook_hyperlexical_rows.jsonl",
        "moltbook_hyperlexical_high.jsonl",
        "moltbook_hyperlexical_high_signal.jsonl",
    ):
        path = root / "data" / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("lineage") != "ai-native":
                continue
            rows.append(
                _row(
                    text=record.get("text", ""),
                    lineage="ai-native",
                    typology=record.get("typology", ["compression"]),
                    stage=record.get("stage", "circulating"),
                    roles=record.get("roles", []),
                    fillers=record.get("fillers", []),
                    role_scheme=record.get("role_scheme"),
                    task="classify+unbind",
                    provenance=record.get("provenance", {"source": "moltbook"}),
                    **{"class": record.get("class", "INFERRED")},
                    license=record.get("license", "MIT (distilled)"),
                )
            )
    return rows


def test_seed_audit_counts_verdicts_and_emits_nothing(tmp_path):
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
    assert audit_seed_examples_gold(tmp_path) == {
        "fallback_label": 1,
        "gold_not_in_text": 1,
        "kept": 1,
    }
    assert harvest_moltbook(tmp_path) == []

    # Curated-seed rows are the path that actually enters the export.
    _write_molt(
        tmp_path,
        [
            _molt_line(
                text="Context note with KDR in the sentence.",
                fillers=["general"],
                provenance={"source": "moltbook-curated-seed", "class": "INFERRED"},
            ),
            _molt_line(
                text="see KDR next",
                fillers=["KDR"],
                roles=["TOKEN"],
                provenance={"source": "moltbook-curated-seed", "class": "INFERRED"},
            ),
        ],
    )
    gated = {row["text"]: row for row in harvest_moltbook(tmp_path)}
    demoted = gated["Context note with KDR in the sentence."]
    assert "kdr" in surface_tokens(demoted["text"])
    assert demoted["task"] == "classify"
    assert demoted["fillers"] == []
    assert demoted["gold_demote_reason"] == "fallback_label"
    assert demoted["provenance"]["source"] == "moltbook-curated-seed"
    kept = gated["see KDR next"]
    assert kept["task"] == "classify+unbind"
    assert kept["fillers"] == ["KDR"]
    assert "gold_demote_reason" not in kept


def test_real_seed_examples_audit_does_not_relabel():
    """Read-only. The committed seed file is not edited and is not harvested."""
    path = ROOT / "data" / "agent_memetics" / "seed_examples.jsonl"
    kdr = []
    general_post = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        label = (rec.get("labels") or {}).get("context_loss")
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
    assert audit_seed_examples_gold(ROOT) == {
        "fallback_label": 5,
        "gold_not_in_text": 21,
        "kept": 0,
    }


def test_demotion_adds_no_new_row_ids(tmp_path):
    """Gated texts match the ungated builder. New ids are demotions of those texts."""
    pack = tmp_path / "data" / "backfill" / "2026"
    pack.mkdir(parents=True)
    (pack / "2026-01-01.json").write_text(
        json.dumps(
            {
                "provenance_default": "INFERRED",
                "terms": [
                    {
                        "term": "a general statement",
                        "family_id": "ai-native",
                        "provenance": "INFERRED",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    _write_molt(
        tmp_path,
        [
            _molt_line(text="a general statement", fillers=["general"]),
            _molt_line(text="alpha beta", fillers=["nope"]),
            _molt_line(text="see KDR next", fillers=["KDR"], roles=["TOKEN"], **{"class": "OBSERVED"}),
            _molt_line(
                text="curated general note",
                fillers=["general"],
                provenance={"source": "moltbook-curated-seed", "class": "INFERRED"},
            ),
        ],
    )
    ungated = _ungated_moltbook(tmp_path)
    gated = harvest_moltbook(tmp_path)
    assert [row["text"] for row in gated] == [row["text"] for row in ungated]
    ungated_ids = {row_id(row) for row in ungated}
    ungated_texts = {row["text"] for row in ungated}
    for before, after in zip(ungated, gated):
        assert after["text"] == before["text"]
        assert after["split"] == before["split"]
        assert after["lineage"] == before["lineage"]
        assert after["typology"] == before["typology"]
        if after.get("gold_demote_reason"):
            assert after["task"] == "classify"
            assert after["fillers"] == []
            assert after["roles"] == []
            assert after["role_scheme"] is None
            assert row_id(after) not in ungated_ids
        else:
            assert row_id(after) == row_id(before)
            assert json.dumps(after, sort_keys=True) == json.dumps(before, sort_keys=True)

    ungated_export = dedupe(harvest_backfill(tmp_path) + ungated)
    gated_export = dedupe(harvest_backfill(tmp_path) + gated)
    assert {row["text"] for row in gated_export} == {row["text"] for row in ungated_export}
    ungated_export_ids = {row_id(row) for row in ungated_export}
    for row in gated_export:
        if row_id(row) not in ungated_export_ids:
            assert row.get("gold_demote_reason")
            assert row["text"] in ungated_texts
            assert row["fillers"] == []


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
    expected = summarize_gold_demotions(molt)
    expected["seed_examples_audit_only"] = audit_seed_examples_gold(ROOT)
    assert bundle["counts"]["gold_demoted"] == expected
    assert expected["seed_examples_audit_only"] == {
        "fallback_label": 5,
        "gold_not_in_text": 21,
        "kept": 0,
    }
    assert not any(provenance_source_tag(row) == "seed_examples" for row in bundle["rows"])
    for source, reasons in bundle["counts"]["gold_demoted"].items():
        if source == "seed_examples_audit_only":
            assert set(reasons) <= {"fallback_label", "gold_not_in_text", "kept"}
        else:
            assert set(reasons) <= {"fallback_label", "gold_not_in_text", "no_gold"}
        assert sum(reasons.values()) > 0
    post, splits = gold_demoted_after_dedupe(bundle["rows"])
    assert bundle["counts"]["gold_demoted_post_dedupe"] == post
    assert bundle["counts"]["gold_demoted_post_dedupe_by_split"] == splits
    assert set(splits) == {"train", "val"}
    assert sum(splits.values()) == sum(sum(reasons.values()) for reasons in post.values())
    skipped = 0
    for name in (
        "moltbook_hyperlexical_rows.jsonl",
        "moltbook_hyperlexical_high.jsonl",
        "moltbook_hyperlexical_high_signal.jsonl",
    ):
        path = ROOT / "data" / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
    assert bundle["counts"]["moltbook_skipped_lines"] == skipped


def _split_text(prefix: str, want: str) -> str:
    for index in range(300):
        text = f"{prefix} {index}"
        if lexical_split(text) == want:
            return text
    raise AssertionError(f"no {want} text for {prefix}")


def test_empty_gold_is_tagged_no_gold_and_bad_json_is_counted(tmp_path):
    empty = _split_text("quiet desk", "val")
    duplicate = _split_text("quiet desk", "val")
    assert empty == duplicate or lexical_split(empty) == "val"
    # Two harvest lines with the same text collapse after dedupe.
    same = empty
    other = _split_text("also quiet", "train")
    assert lexical_split(same) == "val"
    assert lexical_split(other) == "train"
    _write_molt(
        tmp_path,
        [
            "{not json",
            "",
            _molt_line(text=same, fillers=[], roles=[]),
            _molt_line(text=same, fillers=["", None], roles=[]),
            _molt_line(text=other, fillers=[]),
            _molt_line(text="see KDR next", fillers=["KDR"], roles=["TOKEN"], **{"class": "OBSERVED"}),
            json.dumps({"text": "not ai native", "lineage": "brainrot-aura", "fillers": ["general"]}),
        ],
    )
    stats: dict[str, int] = {}
    rows = harvest_moltbook(tmp_path, stats=stats)
    assert stats["moltbook_skipped_lines"] == 1
    empties = [row for row in rows if row["text"] == same]
    assert len(empties) == 2
    for row in empties:
        assert row["task"] == "classify"
        assert row["class"] == "INFERRED"
        assert row["fillers"] == []
        assert row["gold_demote_reason"] == "no_gold"
        assert row["text"] == same
    assert all(row["text"] != "not ai native" for row in rows)
    kept = [row for row in rows if row["text"] == "see KDR next"]
    assert kept[0]["task"] == "classify+unbind"
    assert "gold_demote_reason" not in kept[0]
    assert kept[0]["class"] == "OBSERVED"
    collapsed = dedupe(rows)
    post, splits = gold_demoted_after_dedupe(collapsed)
    assert splits["val"] >= 1
    assert splits["train"] >= 1
    assert post["moltbook"]["no_gold"] == splits["train"] + splits["val"]
    # Pre-dedupe still counts both copies of the val text. Post-dedupe keeps one.
    assert summarize_gold_demotions(rows)["moltbook"]["no_gold"] == 3
    assert splits["val"] == 1


def test_harvest_moltbook_does_not_swallow_non_json_errors(tmp_path):
    _write_molt(
        tmp_path,
        [_molt_line(text="hello __RESTRICTED_FIXTURE__ there", fillers=["hello"])],
    )
    with pytest.raises(ValueError, match="restricted"):
        harvest_moltbook(tmp_path)
    path = tmp_path / "data" / "moltbook_hyperlexical_rows.jsonl"
    path.write_text("[]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not an object"):
        harvest_moltbook(tmp_path)


def test_post_dedupe_counts_do_not_read_test_rows():
    class _SplitOnly:
        def get(self, key, default=None):
            if key != "split":
                raise AssertionError(key)
            return "test"

    val = {
        "split": "val",
        "text": "kept phrase",
        "gold_demote_reason": "no_gold",
        "provenance": {"source": "moltbook"},
        "task": "classify",
        "lineage": "ai-native",
    }
    post, splits = gold_demoted_after_dedupe([_SplitOnly(), val])
    assert splits == {"train": 0, "val": 1}
    assert post == {"moltbook": {"no_gold": 1}}
    assert "UNREAD" not in json.dumps({"post": post, "splits": splits})
