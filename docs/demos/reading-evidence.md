# Reading Hyperlex evidence (for researchers)

Pages is a **publish-safe desk**, not a live lab console.  
This page explains what you are looking at, what each number means, and what you
**must not** claim from static site content.

!!! info "Primary store vs Pages"
    **Live operator data** stays in `~/.hyperlex/` (receipts, score log, vector DB).  
    **Pages** shows sanitized snapshots, demos, and method docs only.  
    If a field is missing on Pages, it may still exist locally.

---

## Evidence layers (read top → bottom)

| Layer | What it is | Typical provenance | Brier? |
|-------|------------|--------------------|--------|
| **1. Ingest fingerprint** | Route, source, query text | OBSERVED when network; mock offline | No |
| **2. Lineage match** | Family + matched atomic terms | INFERRED (registry/backfill) | No |
| **3. Vector neighbors** | Cosine-similar terms/receipts | INFERRED (hash embed default) | **Never** |
| **4. Virality / typology** | Analytic scores on the receipt | INFERRED / SPECULATIVE | No |
| **5. Forecasts** | Probabilities awaiting settlement | INFERRED until settled | Only after settle |
| **6. Phase 5** | Transmission / multi-agent / risk sims | **SPECULATIVE** | Always `null` |
| **7. Settled Brier series** | Score from forecast↔outcome pairs | OBSERVED (after operator settle) | **Yes** |

```text
query (atom)
   │
   ▼
ingest ──► analyze ──► lineage + vector_neighbors + virality …
   │              │
   │              └── forecasts (open) ──► settle ──► Brier series
   │
   └── Phase 5 risk (optional, SPECULATIVE, never Brier)
```

**Atomic terms rule:** free text like `sigma rizz locked in` is **input**, not one
lexicon item. The engine expands to separate atoms. On archive cards, prefer
**atoms** listed separately over a blended “seed.”

---

## Provenance vocabulary

| Label | Meaning for a claim |
|-------|---------------------|
| **OBSERVED** | Bound to a measurement or network capture (or a remote embedding API) |
| **INFERRED** | Derived offline by Hyperlex logic (hash embeddings, lineage match, hybrid re-rank) |
| **SPECULATIVE** | Scenario / model exploration (Phase 5). Do not treat as calibrated truth |
| **`brier: null`** | Correct default. Numeric Brier only after settlement |

If a vector hit says `embed_provenance: INFERRED`, the embedding is the offline
hash model (`hyperlex.hash_ngram_v1.d256`), not a trained language model.

---

## How vector evidence appears

### A. On a live analyze / pipeline result (local)

```json
"analysis": {
  "primary_term": "rizz",
  "lineage": { "family_id": "brainrot-aura", "matched_terms": ["rizz"], "confidence": 0.8 },
  "vector_neighbors": {
    "schema": "hyperlex.vector_neighbors.v1",
    "provenance": "INFERRED",
    "brier": null,
    "hits": [
      { "text": "aura", "family_id": "brainrot-aura", "score": 0.49 }
    ]
  }
}
```

| Field | Researcher reading |
|-------|--------------------|
| `hits[].text` | Neighbor term (atomic slang unit) |
| `hits[].family_id` | Lineage family label, if known |
| `hits[].score` | Cosine similarity on unit vectors ∈ ~[0,1] after conversion |
| `brier: null` | Similarity is **not** a probability of cultural adoption |

After each pipeline unit, Hyperlex may also **auto-index** the atom + receipt
into the local vector store (`vector_index` step). That keeps the index warm;
it does not publish to Pages by itself.

### B. On Pages (static)

| Surface | What you get |
|---------|----------------|
| [Telemetry desk](../telemetry.md) | Method map + how-to-read table |
| [Vector DB module](../modules/vectordb.md) | Operator/backend map (sqlite · chroma · promote) |
| [Run history](../archive/index.md) | Sanitized analysis / Phase 5 snapshots |
| **This page + sample JSON** | How to interpret scores without overclaiming |

Pages **does not** stream live Chroma Cloud or your home `~/.hyperlex/chroma`.  
To put vector context on Pages, export a sanitized sample or archive a receipt
that already includes `vector_neighbors`.

### C. Worked sample (local Chroma · publish-safe)

Query: **`rizz sigma aura`** · backend local chroma · hash embeddings · `brier: null`

| Rank | Term | Family | Score | Source |
|------|------|--------|------:|--------|
| 1 | rizz | brainrot-aura | 0.59 | lineage registry |
| 2 | rizz | brainrot-aura | 0.59 | YTD backfill pack |
| 3 | aura | brainrot-aura | 0.50 | lineage registry |
| 4 | aura | brainrot-aura | 0.50 | YTD backfill pack |
| 5 | aura | brainrot-aura | 0.50 | **ingest auto-index** |

Machine sample: [`samples/vector-search-rizz-sigma-aura.json`](./samples/vector-search-rizz-sigma-aura.json)

**How to talk about this in a paper or memo**

- Good: *“Under offline hash embeddings, ‘aura’ is a near neighbor of the multi-term query in the curated brainrot-aura family.”*
- Bad: *“There is a 50% probability ‘aura’ will go viral.”* (that confuses cosine with Brier/forecasting)

Duplicate rows (registry + backfill + autoindex) mean the same surface form was
seeded from multiple **sources** — useful for provenance, not “triple evidence.”

---

## How archive cards present data

On [Run history](../archive/index.md):

| You see | Means |
|---------|--------|
| **`analysis`** | Receipt-backed analyze/pipeline snapshot |
| **`phase5_scenario`** | Research sim only — SPECULATIVE |
| **atoms** `sigma` · `rizz` · `locked in` | Separate lexicon units (preferred) |
| **risk tier** | Advisory hyperstition risk — not market advice, not Brier |
| **Families** | Lineage labels summarized from receipts |
| **Brier null / open receipts** | Settlement not done (or not exported) |

Open a snapshot for narrative + JSON artifacts. Treat Phase 5 as **scenario
literature**, not measurement.

---

## Claims matrix (what researchers may conclude)

| Claim type | Supported by | Not supported by |
|------------|--------------|------------------|
| Term belongs to a lineage family (with confidence) | Lineage match on receipt | Vector score alone |
| Terms are embedding-near in Hyperlex’s local index | Vector neighbors / search | Brier, Phase 5 risk |
| Operator forecast skill over settled events | `score-series` after settle | Open pipeline results |
| Counterfactual transmission / cascade | Phase 5 (SPECULATIVE) | Vector DB, Brier |
| Live memetic prevalence on the open web | Live ingest routes + external methods | Pages static archive alone |

---

## Pipeline ↔ index (method note)

```text
pipeline / ingest / run
   → analyze (may attach vector_neighbors if index warm)
   → receipt
   → vector_index (fail-open; local sqlite or chroma)
   → forecasts (open) · optional Phase 5

bulk: vector-seed (registry + YTD packs + receipts)
promote: vector-sync local chroma → Cloud  (explicit; not auto on ingest)
```

Full operator map: [modules/vectordb.md](../modules/vectordb.md) ·
[operator-loop.md](../operator-loop.md).

---

## Reproduce the sample locally

```bash
export HERMES_SKILL_DIR="${HERMES_SKILL_DIR:-$HOME/.hermes/skills/hyperlex}"
HLX="python3 $HERMES_SKILL_DIR/scripts/hyperlex.py"
export HYPERLEX_OFFLINE=1

$HLX vector-seed --backend chroma --db ~/.hyperlex/chroma \
  --through 2026-08 --include-home --include-golden
$HLX vector-search "rizz sigma aura" --backend chroma --db ~/.hyperlex/chroma \
  --kind term --top-k 5
```

---

## Related

| Topic | Page |
|-------|------|
| Atomic multi-term demos | [atomic-terms.md](./atomic-terms.md) |
| Brier design | [brier-calibration.md](../brier-calibration.md) |
| Lineage families | [slang-lineages.md](../slang-lineages.md) |
| Phase 5 research sims | [phase5.md](../phase5.md) |
| Vector backends | [modules/vectordb.md](../modules/vectordb.md) |
