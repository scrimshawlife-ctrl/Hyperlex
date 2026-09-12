# U3 recipe — Spark train / 004 eval (SHADOW)

Status: recipe + harness landed. Weights not trained. E2 not passed.

## Box

NVIDIA DGX Spark, GB10, 128 GB unified, aarch64, `sm_121`.
CI is x86 stub. CI must not fetch the trunk.

## Trunk

`answerdotai/ModernBERT-base` (~149M). Official BPE. Last-layer token states for unbind (C28–C30).
Local snapshot only. `local_files_only=True`. Abort if cache missing.

## Data

Tracked `exports/civilian.v0.1.jsonl` is an 883-row **seed/snapshot**. It is not the train SoT.

```
PYTHONPATH=scripts/shadow python3 -m hyperlexical.export --include-live
```

T1 / E2 trains from the **local SoT** (`~/.hyperlex/hyperlexical/ingest_candidates.jsonl`) via `--include-live`. Omit `--include-live` only for harness wiring against the tracked seed. Operator `--include-live` (2026-09-10 PT evening): n=6506 · classify 2437 · unbind 1345 · negatives 208 · gaps 0/0/0.

Name-gate is still false (E2 Spark-blocked). The word Hyperlexical stays off the card until E2 beats 004 on shared fixtures **and** civilian unbind rows exist.

Do not train on `split=reject`. Do not treat INFERRED typology/stage as OBSERVED gold.

## Unbind recipe (data shape, not a new harvest)

Civilian val unbind plateaued ~0.23 on live5. Morph1 (OBSERVED dump, not
new SoT gold) is **0.321** (115/358): positional 185 / 135 fail, type_slot
173 / 108 fail. Themes: `positional_head_filler_miss` dominant, type_slot
TOKEN miss, residual morph bleed (looksmaxxed↔looksmaxxing, rizzless↔rizz),
status-vocab distractors (bum/bolt/burn/mid) across lineages, many INFERRED
type_slot rows are proper-noun noise. Flat `HYPERLEX_UNBIND_LOSS_WEIGHT=2` hurt.
This recipe is Hyperlexical train-loop only. ne0l0gist harvest / export SoT
rows stay as-is (no invented OBSERVED gold).

| Env | Default | Effect |
|-----|--------:|--------|
| `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE` | 1 | Repeat OBSERVED unbind **train** rows (1 = identity) |
| `HYPERLEX_UNBIND_INFERRED_CAP` | 0 | Cap INFERRED unbind **train** rows (0 = off). First-seen order. Hard low caps can starve morph-negs — do not default a cap. Morph4 `CAP=1000` rejected. |
| `HYPERLEX_UNBIND_INFERRED_WEIGHT` | 1.0 | Soft scale on unbind CE + morph-margin for `class != OBSERVED`. Finite (0, 2]. Default 1.0 = identity. Try **0.4–0.5** on Spark. Does not drop rows. |
| `HYPERLEX_UNBIND_MORPH_MARGIN` | 0.5 | Ranking margin vs a near-morph sibling filler |
| `HYPERLEX_UNBIND_CURRICULUM` | 0 | `1` = scheme-split phases; `0` = full mix every epoch |
| `HYPERLEX_UNBIND_CURRICULUM_POS_EPOCHS` | 1 | When on: exclusive positional / non-type_slot epochs |
| `HYPERLEX_UNBIND_CURRICULUM_TYPE_EPOCHS` | 1 | When on: exclusive type_slot (TOKEN:/SLOT) epochs; remainder = joint |
| `HYPERLEX_UNBIND_FILLER_DENYLIST` | empty | JSON `{lineage: [surface, …]}` for hard-neg / CE distractors only |
| `HYPERLEX_UNBIND_FILLER_DENYLIST_PATH` | unset | Same JSON on disk. Missing/invalid fails closed. |
| `HYPERLEX_UNBIND_HARD_ATOMS_PATH` | unset | Operator JSONL (`text` per line). Env path only — do not commit the file. Missing/unreadable/invalid fails closed. |
| `HYPERLEX_UNBIND_HARD_UPSAMPLE` | 1 | Extra copies of matching already-OBSERVED train unbind rows after the normal OBSERVED upsample. 1 = identity. Try **3–4** after the morph3 plateau. |

Hard-negatives come from fillers **already on** unbind train rows: an explicit
map (aped↔aping, looksmax*, rizz*, fanum* + gated tax/taxed, quiet quit*,
mew*, crash/crashout, aura*) plus a conservative same-stem auto pair.
Missing sibling surfaces are not invented. `tax`/`taxed` pair only when
gold is fanum* lineage. The optional denylist only drops distractors
already in that set — it does not mint slang.

Curriculum is Hyperlexical-loop only and composes with `shape_unbind_train`
(morph hard-negs stay on). Classify batches stay the full train set every
epoch. An empty exclusive phase falls back to the full mix so unbind steps
are not skipped.

Morph1 order lock: **positional → type_slot → joint**. Default phase
lengths stay 1/1 so a 2-epoch smoke still hits both schemes. Longer Spark
cards should spend more early epochs on positional (135/185 fail vs
108/173). `HYPERLEX_UNBIND_INFERRED_CAP` stays **0** (off) unless the
operator opts in — Morph1 INFERRED type_slot noise is not auto-dropped
and is not promoted to OBSERVED gold. Morph4 hard `INFERRED_CAP=1000`
rejected (unbind 0.229; morph_negs 305→187). Prefer
`HYPERLEX_UNBIND_INFERRED_WEIGHT=0.4`–`0.5` so sibling fillers stay in
the train pool. Morph5 map expand (#55) was 0.346 — hold map churn.
Hard low caps can starve morph-negs. Status-vocab bleed is the
optional denylist (`bum` / `bolt` / `burn` / `mid` as distractors only).
BEST checkpoint stays operator-side (`seed-morph3`, unbind≈0.358).

SETTLE×5 promoted class but train `n_unbind_observed` stayed 885. Soft
INFERRED weight (#56) and POS-heavy curriculum did not beat morph3.
After that plateau, set `HYPERLEX_UNBIND_HARD_ATOMS_PATH` to the Spark
operator JSONL (`/home/morpheus/hlx/hard_atoms_train.jsonl`, 59 `text`
rows) and try `HYPERLEX_UNBIND_HARD_UPSAMPLE=3` or `4`. Extra copies are
loop multiplicity of rows already `class==OBSERVED` in the train unbind
pool. The recipe does not invent gold and does not upgrade INFERRED.

`lexical_split` is a frozen text hash. Adding settled rows mid-experiment
must not reshuffle val — do not change the hash, modulus, or bucket edges.

Receipt fields: `n_unbind_observed`, `n_unbind_inferred`,
`unbind_observed_upsample`, `unbind_inferred_weight`,
`n_unbind_morph_negatives`, `unbind_curriculum`, phase boundaries,
n rows per phase, `unbind_hard_atoms_path` (basename),
`unbind_hard_upsample`, `n_unbind_hard_atoms_matched`,
`n_unbind_hard_extra_copies`.
`name_gate` stays false. BEST checkpoint stays operator-side (`seed-morph3`).

## Heads

- classify: linear on pooled 768 (train/val only)
- unbind: linear/MLP on token states → role + filler
- no refusal head, no chat template, no Brier head

## Spark command sketch (operator box only)

```
export HYPERLEX_ALLOW_TRAIN=1
export HYPERLEX_TRUNK_DIR=/path/to/local/ModernBERT-base
PYTHONPATH=scripts/shadow python3 -m hyperlexical.train --offline
```

Without both the env flag and a local trunk dir, `train` exits 2.

## Eval

```
PYTHONPATH=scripts/shadow python3 -m hyperlexical.eval_unbind
```

Compares stub unbind to Spec 004 probe on the same TPR fixtures.
E2 pass = stub/model swap accuracy **strictly greater** than 004 probe swap accuracy on the shared test split.
Current stub is expected to **lose**. That is the gate working.

Civilian `unbind_exact` is all-or-nothing on the full filler list, so a
near-miss looks like a plateau. Val receipts now also emit
`unbind_token_f1` (micro bag-of-filler F1) and `unbind_slot_f1`
(per-position exact, positional / type_slot alignment), plus optional
token precision/recall. Operator ladder on exact is **0.45 / 0.55 / 0.65**;
watch `unbind_token_f1` too. seed-morph8 BEST is observed civilian val
`unbind_exact`≈0.3715 / classify≈0.563 / E2 PASS 1.0 — not new SoT gold.
Stub/digest `eval_unbind` leaves the F1 fields **null** (004 probe swap
has no civilian filler lists). Trunk-forward fills them from the same
aligned lists as exact. `name_gate` stays false.

## Not this unit

Hub upload. NVFP4. MiniLM as trunk. 7B. 006 IsA.
