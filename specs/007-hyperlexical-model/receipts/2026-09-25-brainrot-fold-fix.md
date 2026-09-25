# Brainrot-aura fold fix (2026-09-25)

Gold correction. Always on. `name_gate` unchanged. Strict unbind metrics and
`HLX_E2_DISJOINT` unchanged. Training recipe defaults unchanged. No
`data/*.jsonl` edit.

## Bug

`harvest_4333_dump` folded `brainrot-aura` into `ai-native`:

```python
if lineage in ("brainrot-aura", "ai-native"):
    lineage = "ai-native"
```

That fold landed in `3dc37b7` (`feat(007): integrate 4333 dump with inline
memetic enrichment; complete T1 prep`, 2026-09-10) with no reason for treating
brainrot-aura as an ai-native coinage. The same fold is baked into
`data/hyperlex_4333_dump.jsonl`: the file has no `lineage=brainrot-aura` rows.
Some ai-native rows still carry `provenance.original_lineage=brainrot-aura`.

## Ruling

On 2026-09-25 the owner ruled that brainrot-aura is its own family
(`layout.FAMILIES[3]`). "brainrot" and "aura" are base terms. "brainrot aura"
is a compound/blend mutation inside that family, not an ai-native coinage.

## Correction

The harvest fold is removed. A dump row labelled ai-native is restored to
brainrot-aura when `provenance.original_lineage` is brainrot-aura. Raw typology
is kept (`provenance.raw_typology`); ai-native typology expansion runs only
when the row stays ai-native.

`undo_dump_brainrot_fold()` runs before dedupe. A notion classify row that is
still ai-native becomes brainrot-aura only when every non-notion, non-test
classify row with the same normalized text says brainrot-aura. Mixed evidence
and no outside evidence stay put. Split is the text hash, so relabelling does
not move a row across splits. The export count is
`dump_brainrot_fold_undone`.

## Export sha

The export `sha256` changes by design. This is a gold correction, not an
accidental dump drift.

## Classify admission

`HLX_CLASSIFY_ADMISSION` defaults **off**. With the flag unset, classify
train/val rows are unchanged and training behaves byte-identically. The train
receipt records `classify_admission: null`.

Set `HLX_CLASSIFY_ADMISSION=1` to drop classify train/val rows whose normalized
text still has more than one lineage, Moltbook rows (source-constant ai-native
label), and demoted rows (`gold_demote_reason`, or fillers `general` / `kdr`).
Counts are written to `receipt["classify_admission"]`.
