# Model card draft — do not upload

Name after E2: `hyperlex-structure-149m`  
Name before E2: `hyperlex-encoder-modernbert-base`  
Trunk: `answerdotai/ModernBERT-base` (~149M, Apache 2.0)  
License: TBD by operator at Hub gate (trunk is Apache 2.0)  
Trained on: DGX Spark (GB10), offline-capable infer

## What this is

A small **base encoder** (ModernBERT-base + lineage / typology / unbind heads) for attested civilian slang atoms.

Not a chat model. Not a receipt. Not a forecast. `brier` is null until a human settles elsewhere.

## What this is not

- HyperLex 2016 graded-entailment dataset
- Clinical hyperlexia
- NeuSOGA
- A wrap generator
- An uncensored 7B assistant
- MiniLM with extra marketing

## Intended use

Offline detect and structure-unbind on civilian slang. Library helper. JSON packet `hyperlex.hyperlexical.inference.v0.1`.
Unbind reads last-layer token states. Official ModernBERT tokenizer only.

## Out of scope

Restricted how-tos. Jailbreak recipes. Tool fire. Semantic-route claims. Is-a scoring (006).

## Alignment

Uncensored in the Hyperlex sense: no refusal head on civilian slang. Dual-use wall still on. Restricted spans persist as `payload_ref` only.

## Eval

Must pass E0, E4, E5, E6 to exist. Must pass E2 to use the word Hyperlexical.

## Contact

Operator gate. This draft is not a Hub publish.
