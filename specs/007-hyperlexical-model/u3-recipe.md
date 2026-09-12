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
| `HYPERLEX_UNBIND_INFERRED_CAP` | 0 | Cap INFERRED unbind **train** rows (0 = off). First-seen order. Hard low caps can starve morph-negs — do not default a cap. |
| `HYPERLEX_UNBIND_MORPH_MARGIN` | 0.5 | Ranking margin vs a near-morph sibling filler |
| `HYPERLEX_UNBIND_CURRICULUM` | 0 | `1` = scheme-split phases; `0` = full mix every epoch |
| `HYPERLEX_UNBIND_CURRICULUM_POS_EPOCHS` | 1 | When on: exclusive positional / non-type_slot epochs |
| `HYPERLEX_UNBIND_CURRICULUM_TYPE_EPOCHS` | 1 | When on: exclusive type_slot (TOKEN:/SLOT) epochs; remainder = joint |
| `HYPERLEX_UNBIND_FILLER_DENYLIST` | empty | JSON `{lineage: [surface, …]}` for hard-neg / CE distractors only |
| `HYPERLEX_UNBIND_FILLER_DENYLIST_PATH` | unset | Same JSON on disk. Missing/invalid fails closed. |

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
rejected (unbind 0.229; morph_negs 305→187); expand `MORPH_CLUSTERS`
instead. Hard low caps can starve morph-negs. Status-vocab bleed is the
optional denylist (`bum` / `bolt` / `burn` / `mid` as distractors only).
BEST checkpoint stays operator-side (`seed-morph3`, unbind≈0.358).

`lexical_split` is a frozen text hash. Adding settled rows mid-experiment
must not reshuffle val — do not change the hash, modulus, or bucket edges.

Receipt fields: `n_unbind_observed`, `n_unbind_inferred`,
`unbind_observed_upsample`, `n_unbind_morph_negatives`,
`unbind_curriculum`, phase boundaries, n rows per phase.
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

## Not this unit

Hub upload. NVFP4. MiniLM as trunk. 7B. 006 IsA.
