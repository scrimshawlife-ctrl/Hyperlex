# Engineering guidelines 007 (A5)

**Status**: SHADOW  
**Notion**: https://app.notion.com/p/3d73e8ba2f5c813db326e3f68ac77ee9  
**Milestones**: `milestones.md` · https://app.notion.com/p/3d73e8ba2f5c81e9aac1e7dc992e3481  
**Hub**: https://app.notion.com/p/3d73e8ba2f5c81ad89d7c2df8e931a83

Detector over generator. Dual-use wall copied from 001/003/007.

## Classify (R2)

- One atom per row. Do not blend multi-term bags into one gold label.
- Family label only when the atom is slangish or multiword under the weak mapper rules. Polysemy denylist holds.
- `skill issue` and other collision-holds stay `none` until operator review.
- Negatives are a bucket, not failed classify. Do not stuff them into family counts.
- Provenance: INFERRED until settle. OBSERVED is a settle verb, not an export flag.
- Civilian dual-scheme unbind only. No gloss invent.
- Restricted spans: drop the row. Do not write a wrap, paraphrase, or generate-path label.

## Files

- Gold / harvest receipts: local store (`~/.hyperlex/`), not git.
- Git gets schemas, exporters, tests, hashed civilian **seed** only. The 883-row tracked JSONL is not the train SoT.
- `~/.hyperlex/hyperlexical/ingest_candidates.jsonl` is the local SoT (4333 rows as of 2026-09-10 PT evening). Do not commit it.
- Spark / T1 train uses that local SoT via `export --include-live`, not the tracked seed alone.

## Code

- Home until T13: `scripts/shadow/hyperlexical/`
- Packet: `brier` null, `forecast_eligible` false, `routes_claimed` ⊆ `{form, lexical}`, never `semantic`.
- No chat template. Stub never returns a refusal string.
- CI: stub embeddings only. No Hub download. No Spark in GitHub Actions.
- Trunk freeze is `trunk.md`. No silent swap.

## Merge

- Honesty PRs may lower counts. That is a pass, not a regression.
- Do not merge a PR that sets `name_gate` true.
- Do not merge mock analyze as gold.
- 008 stays a sibling. No sacred-object implement from a 007 classify branch.

## Spark / T1 train (later sentence)

- Box: DGX Spark per `hardware.md`.
- Train only after name-gate true on `milestones.md`.
- E2 vs 004 probe is the T1 *artifact* name gate, separate from the dataset name-gate.
