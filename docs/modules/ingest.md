# Ingest module

## Sources
| Name | Network | Notes |
|------|---------|--------|
| mock | no | Deterministic, query-aware |
| glossary / real / web | yes | Action Network betting glossary |
| glossary_expanded | yes | AN + wiki slang list + urban |
| reddit | yes | old.reddit search |
| urban | yes | Urban Dictionary API |
| wikipedia | yes | REST summary |
| x_search | optional | Bearer token → xurl → structured stub |
| crawl4ai / firecrawl | optional | Crawl4AI |
| combined | yes | Ordered multi-source merge |

## Cache & rate limits
- Disk: `~/.hyperlex/cache/` (`HYPERLEX_CACHE_DIR`)
- Rate state: `~/.hyperlex/rate_limit.json`
- Disable rate wait: `HYPERLEX_NO_RATE_LIMIT=1`
- Offline force: `HYPERLEX_OFFLINE=1`

## Provenance
Every structured ingest attaches `source_fingerprint` (content_hash, locator, adapter_version).
