# morph67 residual gold — METHOD label (2026-09-21)

**Authority:** operator continue after morph67 REJECT. METHOD = morph43. `name_gate=false`.

## Source

morph67 best-epoch residuals (n=8): OBSERVED 1 / INFERRED 7 (type_slot 4 / positional 4).
Dump: `~/hlx-private/p1-spark-morph67-40ep-sot-flip-20260921/residual-morph67.jsonl`.

## Label

| | n |
|--|--:|
| AUTHORIZE | 2 |
| ABSTAIN | 6 |

- AUTHORIZE reason: `positional_text_split_match` (text.split() == gold)
- ABSTAIN reason: `abstain_scaffolding_wiki_etym` (wiki/etym/quotations/synonym/Armenian/Google Trends)

AUTHORIZE texts:

1. `[Out:] Mega yachts [In:] Mega gyatt`
2. `an egg's age`

## Expand

Built `force_train_morph68_expanded.jsonl` / `hard_atoms_train_morph68.jsonl` from morph66 base:

| | |
|--|--:|
| force_base → force_new | 164 → **166** |
| **force_added** | **2** |
| hard_base → hard_new | 206 → **208** |
| **hard_added** | **2** |

Harvest OBSERVED append for both AUTHORIZE (`HARVEST_APPEND_SUMMARY.json`). Force moves **166/166**; val after force **197**.

## Fair (morph65 on morph68 surface)

| | |
|--|--|
| exact | **0.9695431472081218** (191/197) |
| prior fair n=199 | 0.9698492462311558 |
| path | `~/hlx/fair-eval-morph65-morph68.json` |

## Next

morph68 one-knob = this force/hard expand. Warm morph65; UPSAMPLE=8 + SECOND_SLOT=2 held. PIN iff best > fair on n=197 and E2 exact 1.0.

Private: `~/hlx-private/p1-spark-morph67-residual-label-20260921/` + morph68 dump.
