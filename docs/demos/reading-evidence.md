# Reading Hyperlex evidence

<div class="hlx-status" markdown>
<span><span class="hlx-dot"></span><strong>Researcher desk</strong></span>
<span>Static Pages · not live <code>~/.hyperlex/</code></span>
<span>Similarity ≠ Brier</span>
<span>Settle before scoring</span>
</div>

<p class="hlx-lead">
What each number means, what you may claim, and what you must not.
Live operator state is never on this site — only method, samples, and sanitized history.
</p>

<div class="hlx-keyrules" markdown>

**Keep these four rules in view**

1. **`brier: null` is correct** until an operator settles forecasts.
2. **Cosine / vector score is not a probability** of adoption or virality.
3. **Phase 5 is SPECULATIVE** — scenario literature, not measurement.
4. **Atoms, not bags** — `sigma` · `rizz` · `locked in` are separate units.

</div>

---

## Evidence stack

Read **top → bottom**. Higher layers do not “upgrade” lower ones into Brier.

| # | Layer | What it is | Provenance | Brier? |
|---|-------|------------|------------|--------|
| 1 | Ingest | Route, source, query text | OBSERVED / mock | No |
| 2 | Lineage | Family + matched atomic terms | INFERRED | No |
| 3 | Vector neighbors | Embedding-near terms/receipts | INFERRED (hash default) | **Never** |
| 4 | Virality / typology | Analytic scores on receipt | INFERRED / SPECULATIVE | No |
| 5 | Forecasts | Open probabilities | INFERRED until settle | After settle only |
| 6 | Phase 5 | Transmission / multi-agent / risk | **SPECULATIVE** | Always null |
| 7 | Brier series | Score from forecast↔outcome pairs | OBSERVED after settle | **Yes** |

```text
query (atom)
   │
   ▼
ingest ──► analyze ──► lineage + vector_neighbors + virality
   │              │
   │              └── forecasts (open) ──► settle ──► Brier series
   │
   └── Phase 5 (optional · SPECULATIVE · never Brier)
```

**Atomic terms:** free text like `sigma rizz locked in` is **input**, not one lexicon item.
The engine expands to separate atoms. On archive cards, prefer listed **atoms** over a blended “seed.”

---

## Provenance labels

| Label | Means |
|-------|--------|
| **OBSERVED** | Measurement or network capture (or remote embed API) |
| **INFERRED** | Derived offline (hash embeddings, lineage match, hybrid re-rank) |
| **SPECULATIVE** | Scenario / model exploration (Phase 5) |
| **`brier: null`** | Correct default — numeric Brier only after settlement |

Hash model id: `hyperlex.hash_ngram_v1.d256` → always treat as **INFERRED**.

---

## Vector evidence on Pages vs local

| Where | What researchers get |
|-------|----------------------|
| **This page + sample JSON** | How to interpret scores; publish-safe table |
| [Telemetry](../telemetry.md) | Desk map + how-to-read |
| [**Slang lineage map**](../map/index.md) | Interactive constellation · deep links `?term=` / `?family=` |
| [Run history](../archive/index.md) | Sanitized analysis / Phase 5 snapshots |
| [Vector backend](../modules/vectordb.md) | Operator map (sqlite · chroma · promote) |
| **Live local / Cloud** | **Not** mirrored on Pages |

Pages does not stream `~/.hyperlex/chroma` or Chroma Cloud. To publish vector context:
export a sanitized sample, or archive a receipt that already includes `vector_neighbors`.

### Worked sample (local Chroma · publish-safe)

<div class="hlx-specimen" markdown>

<div class="hlx-specimen-head" markdown>
<strong>Specimen · vector search</strong>
<span>schema hyperlex.vector_search.v1 · brier null · INFERRED</span>
</div>

<div class="hlx-specimen-body" markdown>

<p class="hlx-specimen-meta">
query <code>rizz sigma aura</code> · backend chroma (local) · model <code>hyperlex.hash_ngram_v1.d256</code><br>
note: cosine over unit vectors — not a calibrated probability / Brier
</p>

| Rank | Term | Family | Score | Source |
|-----:|------|--------|------:|--------|
| 1 | rizz | brainrot-aura | 0.59 | lineage registry |
| 2 | rizz | brainrot-aura | 0.59 | YTD backfill |
| 3 | aura | brainrot-aura | 0.50 | lineage registry |
| 4 | aura | brainrot-aura | 0.50 | YTD backfill |
| 5 | aura | brainrot-aura | 0.50 | ingest auto-index |

Machine JSON: [`samples/vector-search-rizz-sigma-aura.json`](./samples/vector-search-rizz-sigma-aura.json)

```json
{
  "schema": "hyperlex.vector_search.v1",
  "query": "rizz sigma aura",
  "backend": "chroma",
  "model": "hyperlex.hash_ngram_v1.d256",
  "embed_provenance": "INFERRED",
  "n_hits": 5,
  "brier": null
}
```

</div>
</div>

<div class="hlx-claim-grid" markdown>

<div class="hlx-claim hlx-claim--good" markdown>

**Say this**

*Under offline hash embeddings, “aura” is a near neighbor of the multi-term query in the curated brainrot-aura family.*

</div>

<div class="hlx-claim hlx-claim--bad" markdown>

**Do not say this**

*There is a 50% probability “aura” will go viral.*  
(confuses cosine similarity with Brier / forecasting)

</div>

</div>

Duplicate rows (registry + backfill + autoindex) mean multiple **seed sources** for the same surface form — not triple independent evidence.

---

## Archive cards

On [Run history](../archive/index.md):

| You see | Means |
|---------|--------|
| `analysis` | Receipt-backed analyze / pipeline snapshot |
| `phase5_scenario` | Research sim only — SPECULATIVE |
| **atoms** listed separately | Preferred presentation |
| risk tier | Advisory only — not market advice, not Brier |
| Families | Lineage labels from receipt summaries |
| Brier null / open | Settlement not done (or not exported) |

---

## Claims matrix

| Claim | Supported by | Not supported by |
|-------|--------------|------------------|
| Term belongs to a lineage family (with confidence) | Lineage on receipt | Vector score alone |
| Terms are embedding-near in Hyperlex’s index | Vector neighbors / search | Brier, Phase 5 risk |
| Operator forecast skill over settled events | `score-series` after settle | Open pipeline results |
| Counterfactual transmission / cascade | Phase 5 (SPECULATIVE) | Vector DB, Brier |
| Live web prevalence | Live ingest + external methods | Pages static archive alone |

---

## Pipeline ↔ index (method)

```text
pipeline / ingest / run
   → analyze (vector_neighbors if index warm)
   → receipt
   → vector_index (fail-open · local sqlite or chroma)
   → forecasts · optional Phase 5

bulk:   vector-seed (registry + YTD packs + receipts)
promote: vector-sync → Cloud  (explicit · not auto on ingest)
```

---

## Reproduce the sample

```bash
export HERMES_SKILL_DIR="${HERMES_SKILL_DIR:-$HOME/.hermes/skills/hyperlex}"
HLX="python3 $HERMES_SKILL_DIR/scripts/hyperlex.py"
export HYPERLEX_OFFLINE=1

$HLX vector-seed --backend chroma --db ~/.hyperlex/chroma \
  --through 2026-08 --include-home --include-golden
$HLX vector-search "rizz sigma aura" --backend chroma --db ~/.hyperlex/chroma \
  --kind term --top-k 5
```

## Related

| Topic | Page |
|-------|------|
| Atomic multi-term | [atomic-terms.md](./atomic-terms.md) |
| Brier design | [brier-calibration.md](../brier-calibration.md) |
| Lineages | [slang-lineages.md](../slang-lineages.md) |
| Phase 5 | [phase5.md](../phase5.md) |
| Vector backends | [modules/vectordb.md](../modules/vectordb.md) |
