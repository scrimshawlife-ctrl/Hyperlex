# Local label packet — new atoms only (2026-09-19)

Handled here. Not a Grok call. Not a train. `name_gate=false`. Brier null. No Hub.

Source of candidates: Spark ingest `~/.hyperlex/hyperlexical/ingest_candidates.jsonl` (4347 lines) minus texts already in the civilian unbind export (`unbind` + `classify+unbind`, 4103 texts). morph56 residual dump (41 rows) was not relabeled. Fair gate stays **0.8185840707964602** n=226 (185/226). BEST stays morph56.

## Counts

| | n |
|--|--:|
| reviewed | 460 |
| AUTHORIZE | 25 |
| ABSTAIN | 435 |
| force-train rows | 0 |
| residual rows rewritten | 0 |

Why: `positional_text_split_match` 25, `abstain_punct` 292, `abstain_scaffolding` 53, `abstain_wiki` 37, `abstain_url` 35, `abstain_not_new` 18.

Every AUTHORIZE row: `reparse_ok=true`, `text.split()==gold_fillers`, roles `pos_0..`, `dataset_class_source=INFERRED`, `promoted_to_observed_train=false`. Scheme is positional only. No type_slot row parsed cleanly in this gap.

Held strings are absent from the packet: `using a beard`, `belt out`, `blinged out`.

`skill issue` is **ABSTAIN** (`abstain_not_new`). C37 collision hold. Lineage stays `none`. Not structure gold.

Notion multiword terms, all Epistemic Status NOT_COMPUTABLE, definition null, all **ABSTAIN**: `that's penis`, `aura farming`, `that even`, `lef a word a prayer`.

## What was authorized

INFERRED positional proposals only. Operator still settles OBSERVED. These rows are not in the morph56 val, so they do not shrink n=226, and they are not integrated.

Short atoms: `took an L`, `big W`.

Lineage `none` idioms (family not settled; structure proposal only): `a few roos loose in the top paddock`, `a kangaroo loose in the top paddock`, `a roo loose in the top paddock`, `all that and a bag of chips`, `and the horse you rode in on`, `Banbury story of a cock and a bull`.

Term bags and short usage lines with a lineage already on the ingest row: the other 17. The bag `skill issue touch grass sus ratio diff smurf` does not settle C37.

## What was refused

Wiki, URL, etymology, dictionary scaffolding, punctuation (including emoji and curly quotes), prose over 8 tokens, and ingest `role_scheme=civilian` (`meeting that should have been an email`, `this meeting could have been an email`). Prior ABSTAIN themes stay out.

Files: `20260919-local-label-new-atoms/labeled_new_atoms.jsonl`, `20260919-local-label-new-atoms/LABEL_COUNTS.json`. No force JSONL.

Reconstruction of the 460-row packet is via `LABEL_SHARDS.md` / `labeled_new_atoms.part00.jsonl`–`part05` (zlib.b64 sidecars on this branch; decompress per LABEL_SHARDS.md).

OBSERVED upsample 3 was not launched.
