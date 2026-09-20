# Resync check — no newer Jev SoT (2026-09-18 21:35Z)

Operator note: dataset might need a Notion resync, or weights a repo resync, after work with Jev. morph56 (`hlx-train-morph56-1789766977`, `HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT=2`) was already up. It was left running.

## What was checked

| Source | Result |
|--|--|
| Notion Operator Hub | last edited 2026-09-13T05:55:31Z. Scoreboard still SoT 4333. |
| Notion Spine Owner | last edited 2026-09-15. Train remote stays `scrimshawlife-ctrl/Hyperlex`. Do not train from the org copy. |
| Notion user "Jev" | no match |
| Notion + connected mail/Slack search | no page or message with a today Hyperlex dataset or Jev weights drop |
| Spark ingest | `~/.hyperlex/hyperlexical/ingest_candidates.jsonl` 4347 lines, mtime 2026-09-18 00:34 MDT |
| Bundled dump | `Hyperlex/data/hyperlex_4333_dump.jsonl` 5019 lines, mtime 2026-09-11 18:37 MDT. The `[harvest_4333_dump] loaded 5019 rows` line is this file, not a new ingest. |
| Civilian export dirty tree | rewritten at morph56 start (15:29 MDT): n=9202, live_included 4316, live_rejected 31. That is `--include-live` of the existing ingest, not a second SoT. |
| `scrimshawlife-ctrl/Hyperlex` `origin/main` | `40acff8` Daniel Meyer 2026-09-17 morph50 PROMOTE docs. No jev author. No safetensors. |
| `Zero-State-LLC/Hyperlex` | `d2fc4b7` Daniel Meyer 2026-09-17 GHA shell-injection fix. Not a dataset. |

BEST symlink remains `hyperlex-encoder-modernbert-base-seed-morph50`. No repo weight to pull.

## Train left in place

GPU ~85% at the check. Epoch 0 best-checkpoint `unbind_exact=0.7787610619469026`, under fair **0.8097345132743363** n=226. Not a gate. `name_gate=false`. No gold added. No Hub.
