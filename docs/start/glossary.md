# Glossary

Short definitions for Hyperlex jargon. Link here whenever a term appears cold.

## Core terms

### Settled Brier only
A **Brier score** measures forecast skill after outcomes are known. Hyperlex
**never** invents a Brier number on open analysis. Pipeline / analyze / Phase 5
keep `provenance.brier = null` until an operator runs `settle` and then
`score-series`. See [settled-brier.md](settled-brier.md).

### Atomic terms
A multi-word bag like `sigma rizz locked in` is **input text**, not one slang
item. The engine splits it into separate **atoms** (`sigma` · `rizz` ·
`locked in`) and runs one result unit per atom. Phrases that are single lexicon
entries (e.g. `locked in`) stay one atom.

### Receipt
An integrity-hashed JSON artifact of an analysis run. The hash covers the
canonical body so later edits are detectable. Primary durable output for serious
use. Stored under `~/.hyperlex/receipts/` (and optionally exported to Pages).

### Lineage family
A phylogenetic group of related slang (e.g. `brainrot-aura`, `betting-sharp`).
Not a flat dictionary. Match attaches `family_id`, matched atoms, confidence,
and operator. Overview: [slang lineage map](../map/index.md).

### Hyperstition
A narrative about a signal that begins to produce the behavior it describes
(self-reinforcing cultural loop). Scored as a research/advisory signal; not
market advice.

### Phase 5
Research tooling: cultural transmission, multi-agent memetics, hyperstition
risk, phylogeny scaffolds. Always **SPECULATIVE** · always `brier: null`.
See [phase5.md](../phase5.md).

### Forecast
A probability claim bound to a receipt (e.g. from lineage confidence). Open
until settlement. Not a Brier score by itself.

### Settlement
Operator-recorded outcome for a forecast (`TRUE` / `FALSE` / `VOID`). Required
before Brier can be computed.

### Vector neighbors
Cosine-similar terms/receipts from the local vector index (sqlite or chroma).
Similarity is **not** a probability of virality and **never** Brier.
See [reading evidence](../demos/reading-evidence.md).

### Mutation trace
Detector-side operator stack on attested text (`AFFIX`, `SUBSTITUTE`,
`REGISTER_SHIFT`, `COMPOSE`, …). Attached as `analysis.mutation_trace`.
Always `brier: null` and `forecast_eligible: false`.
CLI: `mutation trace "<text>"` (alias `mutation-trace`).
Does not call `predict_mutations`. Restricted flag redacts `surface_span`.

### Mutation prediction
Speculative **next surface forms** of a slang atom (compression, derivation,
irony templates, family compounds). Attached as `analysis.mutation_prediction`.
Always `provenance: SPECULATIVE` and `brier: null`. CLI: `mutation predict "<term>"`
(alias `mutation-predict`).

### RUNE.HLX.*
Relay envelope naming for Hyperlex-shaped signals in host systems. Optional
interop; not required for offline CLI use.

### Hermes skill
Hyperlex is packaged as a skill installable into Hermes
(`~/.hermes/skills/hyperlex`). The same Python package also runs as a standalone
CLI via `scripts/hyperlex.py`.

## Hard constraints

| Rule | Meaning |
|------|---------|
| No fabricated Brier | Open runs: `brier: null` |
| Phase 5 speculative | Research only; not measurement |
| No Abraxas hard import | Hyperlex never imports Abraxas |
| Local-first storage | `~/.hyperlex/` is the durable store; Pages is static |

## Related

- [Settled Brier only (rationale)](settled-brier.md)
- [Brier design](../brier-calibration.md)
- [Operator loop](../operator-loop.md)
- [Reading evidence](../demos/reading-evidence.md)
