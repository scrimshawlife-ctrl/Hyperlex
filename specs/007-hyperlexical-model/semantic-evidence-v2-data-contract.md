# Semantic evidence v2 data contract

The executable definition is `scripts/shadow/hyperlexical/semantic_evidence_v2.py`. Schemas are `specs/007-hyperlexical-model/schemas/hyperlex/semantic-evidence-v2/`. This contract does not encode a model and does not read private surfaces.

## Templates

Parent text, frozen before any performance is observed:

```text
surface: <surface>
part_of_speech: <pos>
definition: <pwn30 gloss>
```

Constituent text:

```text
surface: <constituent surface>
definition: <resolved PWN 3.0 gloss>
```

`template_sha256()` hashes those two format strings. Constituent senses come from an already frozen resolver. The evidence function does not call WSD.

## Features

Order is fixed:

```text
F1  whole_vs_constituent_mean_cosine
F2  whole_vs_constituent_mean_residual
F3  whole_vs_each_constituent_min_similarity
F4  whole_vs_each_constituent_max_similarity
F5  whole_vs_each_constituent_mean_similarity
F6  whole_vs_each_constituent_similarity_variance
F7  constituent_pair_mean_similarity
F8  constituent_pair_min_similarity
F9  constituent_pair_variance
F10 whole_gloss_vs_composed_gloss_similarity
F11 whole_lemma_vs_composed_constituent_similarity
F12 constituent_count
F13 token_count
```

F2 is `1 - cosine(parent, normalized mean of constituent vectors)`. Stored similarities and that residual use 10 decimal places, round half even. Cosine is undefined for a zero vector and the record abstains rather than inventing a value. Pairwise variance is the population variance. F12 and F13 are integer controls. They are not semantic predictors unless a later preregistration says so.

Missing or unresolved constituent structure, fewer than two constituents, or a missing gloss or lemma view yields `evidence_status: UNKNOWN`, `features: null`, and output `UNKNOWN`.

## Composition

The preregistered composition set is:

```text
C1 normalized_mean_v1
C2 weighted_mean_by_constituent_token_span
C3 pairwise_relation_summary
```

C1 is the historical baseline composition. C2 uses positive token-span weights and then L2-normalizes. C3 summarizes constituent pairs. There is no learned attention and no trainable composition layer in this draft.

## Views

Definition view compares the parent gloss representation with the composed constituent glosses. Surface-semantic view compares the parent expression representation with constituent representations. Relational view is the pairwise constituent summary, so one cosine does not carry the decision alone.

## Decision boundary

Feature generation does not emit YES. YES and UNKNOWN belong to a later calibrator. NO is not an output. REJECT and QUARANTINE are not feature targets.

A representation freeze, when one is eventually authorized, must record model name, revision, artifact hash, tokenizer hash, template hash, dtype, device class, batch size, seed, threading, and composition-function version. `representation-freeze.schema.json` is that shape. No freeze file is written by this draft.
