# Ingest module

## Prefer routes over adapter names

```bash
python3 scripts/hyperlex.py sources
python3 scripts/hyperlex.py ingest "sharp steam" --route offline
python3 scripts/hyperlex.py analyze "sharp steam" --route live
python3 scripts/hyperlex.py run "rizz" --route offline
python3 scripts/hyperlex.py run "locked in" --route offline
```

| Route | Canonical source | Network |
|-------|------------------|---------|
| `offline` / `mock` / `default` | `mock` | no |
| `live` | `combined` | yes |
| `glossary` | `glossary` | yes |
| `social` | `x_search` | yes |

API: `resolve_source`, `pick_source`, `list_sources`, `ROUTE_PRESETS` in
`hyperlex.intake.sources`.

## Canonical sources

| Name | Network | Notes |
|------|---------|--------|
| mock | no | Deterministic, query-aware |
| glossary | yes | Action Network betting glossary |
| glossary_expanded | yes | AN + wiki slang list + urban |
| reddit | yes | old.reddit search |
| urban | yes | Urban Dictionary API |
| wikipedia | yes | REST summary |
| x_search | optional | Bearer token → xurl → structured stub |
| crawl4ai | optional | Crawl4AI (alias: firecrawl) |
| combined | yes | Ordered multi-source merge |

### Aliases

| Alias | Canonical |
|-------|-----------|
| real, web, an | glossary |
| glossaries, expanded | glossary_expanded |
| x, twitter | x_search |
| firecrawl, crawl | crawl4ai |
| offline, local, test | mock |
| all, multi, live | combined |

## Pipeline

```text
CLI --route / --source
        ↓
 resolve_source / pick_source   (aliases, offline force)
        ↓
 ingest_signal  →  raw string
 fetch_ingest   →  structured + source + route metadata
        ↓
 detect_memetic_patterns (always structured path)
```

`HYPERLEX_OFFLINE=1` forces mock for any network source.

## Cache & rate limits

- Disk: `~/.hyperlex/cache/` (`HYPERLEX_CACHE_DIR`)
- Rate state: `~/.hyperlex/rate_limit.json`
- Disable rate wait: `HYPERLEX_NO_RATE_LIMIT=1`
- Offline force: `HYPERLEX_OFFLINE=1`

## Provenance

Every structured ingest attaches `source_fingerprint` (content_hash, locator,
adapter_version) plus route resolution metadata (`requested_source`, `route`,
`offline_forced`).
