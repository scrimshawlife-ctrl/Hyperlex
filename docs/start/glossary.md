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

### Hyperlex (repo)
Transitional monorepo shell. Not the public product name — that string
collides with French legaltech CLM / DiliTrust. Paths (`~/.hyperlex/`),
`HYPERLEX_*` env vars, and the `hyperlexical` Python package stay as-is.

### ne0l0gist
Slang **ingest** tool: Crawl4AI harvest, `ingest_tap`, export/settle,
civilian and live phrase harvest. Feeds the Hyperlexical train/eval path.
Not the model product.

### Hermes skill
The **current operator surface**. Packaged for Hermes
(`~/.hermes/skills/hyperlex`). The same Python package also runs as a standalone
CLI via `scripts/hyperlex.py`. The model path (Spec 007) does not replace this
surface until T13 promote — and T13 is not open.

### T0 / T1
Spec 007 encoder tiers. **T0** is a classify baseline (`hyperlex-encoder-*`).
**T1** is the first artifact that *may* be called Hyperlexical, and only after
E2 beats the Spec 004 probe on Spark. Neither tier is a Hub card today.

### SHADOW
An advisory lane that is **not** on `API_V1`. Mutation detect v0.2 and Spec 007
live here. Packets stay `brier: null`. Fail-open: omit the block if inference
fails.

### Hyperlexical (name)
Public **model** product claim for Spec 007 (train / eval / E2 / `name_gate`).
The earned Hub name still requires E2 on Spark (`name_gate` is **false**).
Until then the card is `hyperlex-encoder-*`. Do not call a stub, harvest dump,
or seed smoke Hyperlexical-gated-true. Harvest / ingest is **ne0l0gist**.

### name_gate
Dataset + eval wall before a T1 may be named. Classify volume can be ready
while `name_gate` stays **false**. The name-gate does not flip until E2 passes
on Spark. See [SHADOW encoder](../shadow-hyperlexical.md).

## Hard constraints

| Rule | Meaning |
|------|---------|
| No fabricated Brier | Open runs: `brier: null` |
| Phase 5 speculative | Research only; not measurement |
| Spec 007 SHADOW | Classify volume ready; `name_gate` false; no Hub |
| Naming split | **Hyperlexical** = model claim; **ne0l0gist** = ingest; repo **Hyperlex** is the shell |
| Eight families only | Do not invent a ninth lineage family |
| No Abraxas hard import | Hyperlex never imports Abraxas |
| Local-first storage | `~/.hyperlex/` is the durable store; Pages is static |

## Related

- [Settled Brier only (rationale)](settled-brier.md)
- [Brier design](../brier-calibration.md)
- [Operator loop](../operator-loop.md)
- [Reading evidence](../demos/reading-evidence.md)
