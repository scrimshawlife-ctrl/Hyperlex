# Runtime-ready gate — mutation grammar v0.1

**Date:** 2026-09-04  
**Lane:** SHADOW / advisory  
**Code:** on `main`  
**Constitution:** still SHADOW (not promoted)

## Meaning of runtime-ready

After `pip install` + `hyperlex init` (or legacy `bash install.sh`) and agent reload:

1. Route slang measurement to Hyperlex (not ECO generate).
2. Run `hyperlex pipeline "…" --route offline` and read `analysis.mutation_trace` when operators fire.
3. Run isolated `hyperlex mutation trace|predict` as JSON.
4. Keep `brier: null` and `forecast_eligible: false` on grammar packets.
5. Refuse wrap / jailbreak composition.

It does **not** mean GAME_ENCODE parsers, watch jsonl, `--human` cards, constitution promotion, or fat-CLI T5.

## Bar vs tree

| Item | On main |
|------|--------|
| constitution I–X | yes, SHADOW |
| 001 detector + tests + dual-use gate | yes |
| package CLI noun | yes |
| `scripts/hlx-mutation` | yes |
| `hyperlex init` skill wire | yes |
| manifest mutation intents | yes |
| fat `scripts/hyperlex.py mutation` | **no** (use package / alias) |
| result.v1 explicit attach field | **no** (additionalProperties) |
| 000 / 001 CONVERGE stamp | **no** |

## Deferred (v0.2)

- GAME_ENCODE / CODE_SWITCH / PHONETIC_WARP parsers
- `mutation watch` + `~/.hyperlex/mutation_watch.jsonl`
- `--human` card helper
- Constitution promotion off SHADOW

## Integrate

```bash
pip install -e ".[dev]"
hyperlex init --target hermes
hyperlex pipeline "it's giving mid rizz" --route offline
hyperlex mutation trace "it's giving mid rizz"
```
