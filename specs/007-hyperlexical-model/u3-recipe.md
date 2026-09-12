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

Civilian val unbind plateaued ~0.23. Flat `HYPERLEX_UNBIND_LOSS_WEIGHT=2` hurt.
This recipe is Hyperlexical train-loop only. ne0l0gist harvest / export SoT
rows stay as-is (no invented OBSERVED gold).

| Env | Default | Effect |
|-----|--------:|--------|
| `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE` | 1 | Repeat OBSERVED unbind **train** rows (1 = identity) |
| `HYPERLEX_UNBIND_INFERRED_CAP` | 0 | Cap INFERRED unbind **train** rows (0 = off). First-seen order. |
| `HYPERLEX_UNBIND_MORPH_MARGIN` | 0.5 | Ranking margin vs a near-morph sibling filler |

Hard-negatives come from fillers **already on** unbind train rows: an explicit
map (aped↔aping, looksmaxxing variants, fanum*, aura*) plus a conservative
same-stem auto pair. Missing sibling surfaces are not invented.

`lexical_split` is a frozen text hash. Adding settled rows mid-experiment
must not reshuffle val — do not change the hash, modulus, or bucket edges.

Receipt fields: `n_unbind_observed`, `n_unbind_inferred`,
`unbind_observed_upsample`, `n_unbind_morph_negatives`. `name_gate` stays
false. BEST checkpoint stays operator-side (`seed-live5`).

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
