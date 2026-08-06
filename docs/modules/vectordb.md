# Vector DB (SQLite + Chroma)

**Status:** v0.4.0+  
**Default:** SQLite at `~/.hyperlex/vector.db`  
**Opt-in:** local Chroma (`~/.hyperlex/chroma`) or Chroma Cloud  
**CLI:** `vector-seed` · `vector-search` · `vector-stats` · `vector-export` · `vector-import` · `vector-sync`

!!! tip "Researchers"
    For how to **interpret** scores, provenance, and Pages samples — not just
    operate the backend — read
    [Reading Hyperlex evidence](../demos/reading-evidence.md).

Hyperlex keeps a **seedable vector index** for semantic search over:

- lineage registry terms  
- YTD backfill pack terms (`data/backfill/2026/`)  
- receipt text (query + observed preview + matched terms)

Similarity is **not** a calibrated probability and **never** invents Brier.

## Backends

| Backend | Path / target | When |
|---------|---------------|------|
| **sqlite** (default) | `~/.hyperlex/vector.db` (`HYPERLEX_VECTOR_DB`) | Offline default; stdlib only |
| **chroma local** | `~/.hyperlex/chroma` (`--db` or `HYPERLEX_CHROMA_PATH`) | Local ANN / iterate before promote |
| **chroma cloud** | Cloud collection `hyperlex` | After local looks good; needs API key |

```text
registry + backfill packs + receipts
        │
        ▼
  vector-seed  ──sqlite──►  ~/.hyperlex/vector.db
        │
        └──chroma──►  ~/.hyperlex/chroma   (local)
                            │
                            │  vector-sync --to cloud
                            ▼
                      Chroma Cloud (collection hyperlex)
```

## Auto-index on ingest (pipeline)

**Now (local):** every `pipeline` / `run` / `ingest` unit fail-open indexes
primary/matched terms + the receipt into the configured **local** backend
(`HYPERLEX_VECTOR_BACKEND=sqlite|chroma`). Receipt emit uses the same path.

| Switch | Behavior |
|--------|----------|
| `HYPERLEX_VECTOR=auto` (default) | Index if sqlite DB or local chroma dir already exists |
| `HYPERLEX_VECTOR=1` | Always index (creates store) |
| `HYPERLEX_VECTOR=0` | Off |

Result units may include `vector_index: { n_upserted, backend, brier: null }` and
step `vector_index`. Failures never break ingest.

**Future / opt-in:** automatic Cloud promote after ingest is **not** default
(network + cost). Operators still run:

```bash
$HLX vector-sync --from-path ~/.hyperlex/chroma --to cloud
```

A later `HYPERLEX_VECTOR_PROMOTE=1` (or cron after daily seed) can wire promote;
design keeps Cloud write off the hot ingest path unless explicitly enabled.

```text
ingest / pipeline / run
        │
        ├─ analyze (+ vector_neighbors if index warm)
        ├─ receipt
        └─ vector_index  ──►  sqlite or local chroma   (fail-open)
                                    │
                     manual / future promote
                                    ▼
                              Chroma Cloud
```

## Recommended: bulk backfill local Chroma

Full offline seed (registry + YTD packs + home/golden receipts):

```bash
export HERMES_SKILL_DIR="${HERMES_SKILL_DIR:-$HOME/.hermes/skills/hyperlex}"
HLX="python3 $HERMES_SKILL_DIR/scripts/hyperlex.py"
export HYPERLEX_OFFLINE=1

# Local Chroma backfill
$HLX vector-seed \
  --backend chroma \
  --db ~/.hyperlex/chroma \
  --through 2026-08 \
  --include-home \
  --include-golden

$HLX vector-stats --backend chroma --db ~/.hyperlex/chroma
$HLX vector-search "sharp steam revenge" --backend chroma --db ~/.hyperlex/chroma --kind term
$HLX vector-search "rizz locked in" --backend chroma --db ~/.hyperlex/chroma --kind term
```

Same content into default SQLite:

```bash
$HLX vector-seed --through 2026-08 --include-home --include-golden
$HLX vector-stats
```

### Seed sources

| Flag | Default | Source |
|------|---------|--------|
| (registry) | on | `LINEAGE_REGISTRY` |
| (backfill) | on | `data/backfill/YYYY/` packs |
| `--through 2026-08` | `2026-08` | Cap pack months |
| `--include-home` | on | `~/.hyperlex/receipts` |
| `--include-golden` | off | `examples/receipts/golden` |
| `--no-registry` / `--no-backfill` / `--no-receipts` | — | Skip a source |

## Promote local → Cloud (no re-embed)

When local search looks right, **copy embeddings as-is**:

```bash
# One-shot (creds from ~/.hermes/.env — auto-loaded by CLI)
$HLX vector-sync --from-path ~/.hyperlex/chroma --to cloud

# Or staged backup
$HLX vector-export --backend chroma --db ~/.hyperlex/chroma -o ~/.hyperlex/exports/good.jsonl
$HLX vector-import -i ~/.hyperlex/exports/good.jsonl --cloud

$HLX vector-stats --cloud
$HLX vector-search "rizz sigma" --backend chroma --kind term   # no --db → Cloud if path env unset
```

!!! warning "Local path wins over Cloud"
    If `HYPERLEX_CHROMA_PATH` is set, Chroma commands target **local** unless you pass
    `--cloud` / `force_cloud` (used by `vector-sync --to cloud` and `vector-stats --cloud`).
    Unset local path when searching Cloud without those flags.

## Env (Hermes)

CLI auto-loads `~/.hermes/.env` then `~/.hyperlex/.env` (process env wins).

| Variable | Meaning |
|----------|---------|
| `HYPERLEX_VECTOR_BACKEND` | `sqlite` (default) or `chroma` |
| `HYPERLEX_VECTOR_DB` | SQLite file path |
| `HYPERLEX_CHROMA_PATH` / `CHROMA_PATH` | Local Chroma persist dir |
| `CHROMA_API_KEY` or `HYPERLEX_CHROMA_API_KEY` | Cloud API key (required for Cloud) |
| `CHROMA_TENANT` / `HYPERLEX_CHROMA_TENANT` | Optional if Cloud can infer |
| `CHROMA_DATABASE` / `HYPERLEX_CHROMA_DATABASE` | e.g. `Demo` |
| `HYPERLEX_CHROMA_COLLECTION` | Collection name (default `hyperlex`) |
| `HYPERLEX_EMBED_PROVIDER` | `hash` (default) or `openai_compatible` |
| `HYPERLEX_OFFLINE=1` | Blocks remote embeddings |

Optional deps: `pip install 'hyperlex[runtime]'` (includes `chromadb`).

## Embeddings

| Provider | When | Notes |
|----------|------|--------|
| **hash** (default) | always offline | Deterministic n-grams (`hyperlex.hash_ngram_v1.d256`) |
| **openai_compatible** | opt-in | `HYPERLEX_EMBED_PROVIDER=openai_compatible` + base URL/key |

Promote/sync **preserves** existing embeddings (no re-hash on Cloud copy).

## CLI map

| Command | Purpose |
|---------|---------|
| `vector-seed` | Seed registry / backfill / receipts |
| `vector-search "…"` | Cosine (sqlite) or Chroma search |
| `vector-stats` | Counts; add `--cloud` for Cloud |
| `vector-export -o file.jsonl` | Dump rows + embeddings |
| `vector-import -i file.jsonl` | Load dump (`--cloud` for Cloud) |
| `vector-sync --from-path DIR --to cloud` | Promote local Chroma → Cloud |

See [commands.md](../commands.md).

## Library

```python
from hyperlex import vector_seed_all, vector_search
from hyperlex.vectordb import export_vectors, import_vectors, sync_vectors

# SQLite default
report = vector_seed_all(through="2026-08", include_home=True)
hits = vector_search("rizz aura", kind="term", top_k=5)

# Local Chroma
report = vector_seed_all(backend="chroma", path="~/.hyperlex/chroma", through="2026-08")
sync_vectors(from_backend="chroma", from_path="~/.hyperlex/chroma", to_cloud=True)
```

## Hybrid lineage re-rank

When a vector DB is present (`HYPERLEX_VECTOR=auto|1`), `match_lineage` combines:

```text
hybrid_confidence = min(0.98, lexical_confidence + vector_boost)
```

- `vector_boost` is a **capped** family mass from term neighbors (max +0.12)
- Near-miss lexical candidates can be rescued if hybrid clears the threshold
- Still **INFERRED**, still **not Brier**

Disable: `HYPERLEX_VECTOR=0` or `match_lineage(..., use_vector=False)`.

## Hard rules

1. Similarity scores are **not** probabilities and **not** Brier.  
2. Hash embeddings are **INFERRED**; remote embeddings are **OBSERVED** (network).  
3. Vector DB never rewrites receipt integrity hashes.  
4. SQLite uses linear cosine scan (fine at current scale); Chroma uses HNSW cosine.  
5. Secrets stay in `~/.hermes/.env` — never commit API keys.

## Hermes seed prompt (short)

```text
Hyperlex: backfill local Chroma. HYPERLEX_OFFLINE=1.
vector-seed --backend chroma --db ~/.hyperlex/chroma --include-golden --include-home --through 2026-08
vector-stats --backend chroma --db ~/.hyperlex/chroma
vector-search "rizz" --backend chroma --db ~/.hyperlex/chroma --kind term
When good: vector-sync --from-path ~/.hyperlex/chroma --to cloud
Never invent Brier.
```
