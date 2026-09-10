# Milestones 007 (A5)

**Status**: SHADOW / advisory  
**Notion**: https://app.notion.com/p/3d73e8ba2f5c81e9aac1e7dc992e3481  
**Guidelines**: `engineering.md` · https://app.notion.com/p/3d73e8ba2f5c813db326e3f68ac77ee9  
**Hub**: https://app.notion.com/p/3d73e8ba2f5c81ad89d7c2df8e931a83  
**Locked spec**: `spec.md` — this file does not fork T0/T1/T2

Live classify counts stay on Notion Tasks 007 and local harvest receipts.
A harvest number moving does not rewrite a gate here.

## Name-gate (dataset wall before T1 train)

Operator-settled gold only.

| Bucket | n |
|--------|--:|
| classify family | 2000 |
| unbind | 200 |
| negatives | 200 |

- OBSERVED only after settle. Harvest / tap / weak-tag mapper stay INFERRED.
- `name_gate` stays false until all three buckets are settled.
- Weak harvest inflation is not progress against 2k.

Minimum to *plan* implement remains 200 / 40 / 50 (`spec.md` dataset contract).
Minimum to *name* a T1 card is this table.

## Model tiers (locked spec)

| Tier | Meaning | Name allowed |
|------|---------|--------------|
| T0 | 22–40M encoder baseline | `hyperlex-encoder-*` — not Hyperlexical |
| T1 | 60–150M + unbind heads; E2 beats Spec 004 probe; A1 ceiling 150M; A2 trunk `answerdotai/ModernBERT-base` | first artifact that may be called Hyperlexical |
| T2 | generative LoRA | out of this implement cycle |

## Implement units (plan)

| Unit | Scope |
|------|--------|
| U1 | schema + stub; no `src/hyperlex`; no ModernBERT download |
| U2 | civilian export; no ledger copy into git |
| U3 | recipe + eval on Spark; weights out of git |

## R2 classify → T1

Operator sentence on 2026-09-10: classify round 2 training set.

Exit R2 when:

1. Family-labeled classify rows are settled toward 2k.
2. Unbind 200 and negatives 200 are settled as their own buckets.
3. Collision holds (`skill issue` and other WEAK_HOLD) reviewed, not auto-promoted.
4. Dual-use wall intact: no restricted how-to, no wrap/generate labels in gold.
5. Separate sentence: Spark T1 train. Not this file.

## Does not

Train. Hub upload. Open 006. Call a T0 stub Hyperlexical. Promote tap JSONL to OBSERVED. Implement 008.
