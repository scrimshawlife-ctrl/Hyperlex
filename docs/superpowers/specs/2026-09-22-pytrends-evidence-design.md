# Design: Google Trends evidence on Hyperlex routes

**Date:** 2026-09-22
**Status:** Accepted. Implementation plan: `docs/superpowers/plans/2026-09-22-pytrends-evidence.md`
**Scope:** Spec 1, evidence only
**Repo:** `scrimshawlife-ctrl/Hyperlex` at `e1f5935`

## Intent

When an operator runs `--route trends` or `--route live`, attach an observed Google Trends packet for the term they already asked about. The packet records interest-over-time and related queries. Language ingest stays on the existing `combined` source. Virality scores and Brier stay as they are.

Spec 2, a discovery queue built from rising queries, is a later spec. This packet stores related queries so that spec can read them. This spec does not write a harvest queue, call `trending_searches()`, or add a cron.

## Operator surface

No new command. `scripts/hyperlex.py` and `python -m hyperlex` already forward `--route` into `fetch_ingest`. Adding the route preset is enough for both entry points.

```bash
pip install -e ".[trends]"
python3 scripts/hyperlex.py analyze "rizz" --route trends
python3 scripts/hyperlex.py run "rizz" --route live
```

Demo, wizard, and the default `run` route stay `offline`. This spec does not retarget them. A plain `mock` fetch, and routes `offline`, `glossary`, and `social`, do not call Trends.

## Components

| Unit | Responsibility |
|---|---|
| `src/hyperlex/intake/trends.py` | The only module that imports pytrends. Maps responses to plain dicts. `attach_trends` decides whether a packet is added. |
| `src/hyperlex/intake/sources.py` | Route preset `trends` → language source `combined`. Error text for an unknown route lists `trends`. |
| `src/hyperlex/intake/cache.py` | TTL and minimum interval for source `trends`. Non-blocking rate helpers. Existing `wait_for_rate_limit` is unchanged and is not used here. |
| `src/hyperlex/intake/__init__.py` | `fetch_ingest` calls `attach_trends` after the language fingerprint is built. |
| `src/hyperlex/analysis/__init__.py` | `detect_memetic_patterns` copies `ingest_data["trends"]` to top-level `result["trends"]` when the key is present. |
| `pyproject.toml` | Optional extra `trends = ["pytrends>=4.9"]`. |
| `docs/modules/ingest.md` | Route table row for `trends`. |
| `tests/test_trends_evidence.py` | The cases in Testing. |
| `tests/fixtures/trends_rizz.json` | Interest series, one top query, one rising query whose value is `Breakout`. |

`result["ingest"]` stays the language audit subset it is today. The Trends packet is not copied into that subset and not placed under `result["analysis"]`. `result.v1` already allows additional properties, so the top-level key needs no schema change.

`pipeline.run_one` already calls `detect_memetic_patterns`, so analyze, run, and the pipeline pick up the same copy.

## Route behavior

`trends` is a route name, not a `SOURCE_CATALOG` text source. Interest numbers never enter `raw_signal`.

| Route | Language source | Trends key |
|---|---|---|
| `--route trends` | `combined`, or `mock` when `HYPERLEX_OFFLINE=1` | Always present. A miss is `not_computable` with a reason. |
| `--route live` | `combined`, or `mock` when offline | Present when pytrends imports and the process is online. Omitted when the extra is missing or the process is offline. |
| `offline`, `mock`, `default`, `glossary`, `social` | unchanged | Key omitted. No Trends call. |

`attach_trends` reads the resolved route name (`trends` or `live`), not the language source name. `source=combined` without one of those routes does not fetch Trends.

## Data flow

`fetch_ingest` finishes the language string, terms, and language `source_fingerprint` first. `attach_trends` then adds `trends` without changing `raw_signal`, `extracted_terms`, or that fingerprint. `analysis_canonical_hash` therefore stays stable when a Trends packet appears.

Decision order inside `attach_trends`:

1. Route is not `trends` or `live`: return the ingest dict unchanged.
2. Offline (`HYPERLEX_OFFLINE` or the resolver's `offline_forced`): `--route trends` sets `not_computable` / `offline`. `--route live` omits the key. Cache is not read.
3. Extra check. `find_spec("pytrends")` is `None`, or import raises `ModuleNotFoundError`: `--route trends` sets `trends_extra_missing`. `--route live` omits the key. Any other import exception, on either route, sets `fetch_failed` and `error_class`.
4. Query is empty after strip, or longer than 100 characters: `query_rejected`. A query of exactly 100 characters is allowed. The client is not called.
5. Fresh disk cache hit: return a copy with `cached: true`. The cache file is not rewritten, and the rate file is not updated.
6. Rate window closed: `rate_limited`. The client is not called. An expired cache entry is a miss. Expired packets are not served.
7. Fetch, then cache when status is `ok` or `empty`.

## Packet

Schema name: `hyperlex.trends_evidence.v1`. Every packet has the same keys.

| Field | Rule |
|---|---|
| `status` | `ok`, `empty`, or `not_computable`. |
| `reason` | `null` on `ok`. `below_trends_threshold` on `empty`. Otherwise `offline`, `trends_extra_missing`, `query_rejected`, `rate_limited`, or `fetch_failed`. |
| `query` | Stripped operator query. Case is preserved. |
| `geo` | `HYPERLEX_TRENDS_GEO`, or `""` for worldwide. Whitespace-only is `""`. |
| `timeframe` | `HYPERLEX_TRENDS_TIMEFRAME`, or `today 3-m`. |
| `cached` | `true` only when the packet was served from an unexpired cache entry. |
| `fetched_at` | ISO timestamp. On a cache hit, the timestamp stored in the cached packet. |
| `interest_over_time` | List of `{date, value, partial}`. `date` is `YYYY-MM-DD`. `value` is an int from 0 through 100, inclusive. A whole-number float or numpy integer is stored as a Python int. A non-whole number or NaN is dropped. `partial` is a bool. |
| `related_queries` | `{top: [...], rising: [...]}`. Each row is `{query, value}`. A numeric value is stored as an int. A string value is stored as a string, including `Breakout`. |
| `dropped_rows` | Count of interest points that were not ints in 0..100. Those points are removed. |
| `truncated` | `true` when either related list was longer than 25 before the cap. Each list keeps at most 25 rows. |
| `scale` | `interest` is `relative_0_100_within_this_request`. `note` says the peak in this window is 100, values are not probabilities, and values are not comparable across separate fetches. |
| `claims` | On `ok` and `empty`, both statements are `OBSERVED`. On `not_computable`, both are `NOT_COMPUTABLE`. Statements are `interest_over_time` and `related_queries`. |
| `brier` | Always `null`. |
| `error_class` | Exception class name when reason is `fetch_failed`. Otherwise `null`. |
| `source_fingerprint` | From `provenance.source_fingerprint` over the canonical JSON of the packet with this field removed. `source` is `trends`. Locator is `hyperlex://trends?geo=<geo>&timeframe=<percent-encoded timeframe>`. |

Status `empty` means the Google call succeeded and both lists are empty, or every interest point was dropped and both related lists are empty. That is an observation, not an error. `reason` is `below_trends_threshold`.

Status `ok` means at least one interest point or one related query remains.

## pytrends call

Default client, used when no client is injected:

- `TrendReq(hl="en-US", tz=0, timeout=(5, 20), retries=2, backoff_factor=0.3)`.
- `build_payload([query], timeframe=timeframe, geo=geo)`. One keyword. No category and no `gprop` override.
- Read `interest_over_time` and `related_queries` in that single attempt. If either call raises, the whole packet is a failure. There is no second retry loop and no partial packet.
- Import pytrends inside the live fetch function, not at module import.

The injected client protocol:

```python
def fetch(self, query: str, *, geo: str, timeframe: str) -> dict:
    """Return interest_over_time and related_queries in the packet's row shape.
    Raise on transport failure. Empty lists mean Google returned no rows.
    """
```

HTTP status 429, or a message containing `code 429`, becomes reason `rate_limited`. The exception message and response body are not stored. Any other exception becomes `fetch_failed` with `error_class` set to the exception class name.

## Cache and rate limit

Use the existing files: `~/.hyperlex/cache/` (`HYPERLEX_CACHE_DIR`) and `~/.hyperlex/rate_limit.json` (`HYPERLEX_RATE_LIMIT_PATH`).

- Register `SOURCE_TTL["trends"] = 21600` (6 hours) and `SOURCE_MIN_INTERVAL["trends"] = 60.0`.
- Cache key is `trends:{query}|{geo}|{timeframe}` via the existing `cache_key` helper, which lowercases the query portion. The packet's `query` field keeps the original case.
- Store the packet as a JSON string through `set_cached` / `get_cached`. A corrupt cached string is a miss.
- Cache status `ok` and `empty` only. Do not cache `not_computable`.
- Add `rate_window_open(source) -> bool` and `stamp_rate_limit(source) -> None`. Neither sleeps. `HYPERLEX_NO_RATE_LIMIT=1` makes `rate_window_open` return true. `HYPERLEX_SOURCE_MIN_INTERVAL_TRENDS` overrides the 60-second interval through the existing `min_interval_for`.
- Stamp the rate file on every network attempt, success or failure. A cache hit does not stamp.
- Two processes can race on the rate file the same way other sources already can. This spec does not add a lock.

## Failure boundary

`attach_trends` catches its own failures. A Trends problem does not raise out of `fetch_ingest`, and the language analysis still returns. Nothing from Trends is printed to stdout.

`provenance.brier` on the analysis result stays `null`. Trends fields are not inputs to virality, hyperstition stage, market-signal actionable labels, or `analysis_canonical_hash`.

`emit_receipt` already copies the full result and hashes that body. When `result["trends"]` is present, the receipt file includes it and the receipt integrity digest covers it. This spec does not change the receipt hasher. `run_one` reloads `unit["result"]` from that receipt, so the reloaded result still contains `trends`.

## Testing

The default suite does not call Google and does not import pytrends. Tests point `HYPERLEX_CACHE_DIR` and `HYPERLEX_RATE_LIMIT_PATH` at `tmp_path`.

| Test | Asserts |
|---|---|
| Route resolve | `--route trends` selects language source `combined`, records `route=trends`, and `list_sources()` includes the route. |
| Offline CLI | `scripts/hyperlex.py run rizz --route trends --no-phase5` with `HYPERLEX_OFFLINE=1`, `--receipt-dir` under `tmp_path`, and `HYPERLEX_SCORE_LOG` under `tmp_path`. Exits 0. `rizz` stays one atom, so the packet hoists `result`. Assert `result.trends.status=not_computable`, `result.trends.reason=offline`, and `result.provenance.brier` is null. |
| Omission | `--route offline` and a plain mock fetch omit `trends`. |
| Extra missing | Route `trends` returns `trends_extra_missing`. Route `live` omits the key. |
| Injected client | Fixture produces `ok`, keeps `Breakout` as a string, sets `brier` null, and writes a cache entry. |
| Cache hit | The second call does not call the client. |
| Rate window | A stamp newer than 60 seconds skips the client with reason `rate_limited`. |
| Rejection | An empty query and a 101-character query return `query_rejected` and do not call the client. A 100-character query is not rejected for length. |
| Empty answer | Empty fixture returns `empty` / `below_trends_threshold` and is cached. |
| Bad points | A value outside 0–100 increments `dropped_rows` and is removed. |
| Exceptions | A generic error returns `fetch_failed` plus `error_class` and is not cached. A 429 returns `rate_limited` and stamps the rate file. |
| Hash stability | Calling `attach_trends` leaves `raw_signal` and the language `source_fingerprint` unchanged. |
| Result copy | With `fetch_ingest` monkeypatched to include `trends`, `detect_memetic_patterns` sets top-level `result["trends"]` and leaves `provenance.brier` null. |

Success-path coverage is the Python API with an injected client. The subprocess test covers the offline route only. No test is marked to hit the live Trends site.

## Out of scope

- Spec 2 discovery queue, `trending_searches()`, and candidate dedup against the local corpus.
- Changing virality math, Brier, settlement, or the receipt hasher.
- A Trends text source inside `combined`.
- Proxy, cookie, or category configuration.
- A new JSON schema file. Tests assert the packet keys directly.
- A package version bump.
- Serving an expired cache entry while the rate window is closed.
- Retargeting demo, wizard, or the default offline route.
