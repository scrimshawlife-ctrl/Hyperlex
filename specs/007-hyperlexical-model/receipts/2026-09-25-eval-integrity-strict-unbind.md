# Eval integrity — strict unbind and E2 overlap (2026-09-25)

Reporting only. Training recipe unchanged. Ladder selection still reads
`unbind_exact`. `name_gate` unchanged. No gold, holdout ids, or data files.

Base head: `256d1cd4b9a2f1fbaefe199d10cfa0739201785b`.

## Leak check (verified)

Spec 004 TPR probe `snapshot(kind=tpr, n=48, length=4, dim=12, seed=7)` and
`run_probe` / `_split(..., seed=7)` produce 12 test spans:

`test_idx = [0, 6, 12, 16, 18, 36, 41, 43, 44, 45, 46, 47]`

`harvest_unbind` trains on `make_spans(n=24, length=4, seed=7)`, the prefix of
that snapshot. Synthetic fillers are letters `a`–`d` only.

- Same span (index, `item_ids`, and `type_tags`): **5** test indices
  **0, 6, 12, 16, 18**.
- Filler-tuple overlap (the comparison `e2_train_overlap_count` and
  `HLX_E2_DISJOINT` use): **6** test spans. The extra span is test index
  **44** `('d', 'c', 'a', 'b')`, which matches training index **10** on
  fillers only. Type tags differ (`SLOT MARKER TOKEN SLOT` on the training
  span, `MARKER TOKEN SLOT MARKER` on the test span).

## Reporting

Legacy keys are unchanged: `unbind_exact`, `unbind_token_f1`,
`unbind_token_precision`, `unbind_token_recall`, `unbind_slot_f1`.

New keys beside them: `unbind_exact_strict`, `unbind_token_f1_strict`,
`unbind_token_precision_strict`, `unbind_token_recall_strict`,
`unbind_slot_f1_strict`.

Strict gold is the raw lowercased filler string. A `<unk>` prediction is a
miss, including when legacy `mapped_filler` had already rewritten an OOV gold
filler to `<unk>`.

`HLX_E2_DISJOINT` defaults **off**. Set it to `1` to drop harvest spans whose
filler tuple is in the E2 test set. Kept rows keep their original provenance
index. With the flag off, `harvest_unbind` output is unchanged.

Every E2 report includes `e2_train_overlap_count` (6 with the flag off, 0 with
`HLX_E2_DISJOINT=1`).
