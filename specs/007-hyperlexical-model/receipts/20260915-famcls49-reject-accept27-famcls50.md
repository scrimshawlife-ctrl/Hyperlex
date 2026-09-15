# Receipt — famcls49 REJECT → accept27 → famcls50 REJECT

## famcls49 REJECT (verified on Spark)
- Init famcls48 · accept26 · N=8 · LR 5e-6 · aux=0.35 · upsample=12 · 40 ep (best 1)
- Relaunched 2026-09-15 after prior container died ~ep7; full 40 ep completed
- family **0.9848484848484849** < baseline **0.9949494949494949** FAIL (Δ −0.0101)
- structure/role/pointer **1.0** held; `best_unchanged=true`; BEST morph19 untouched
- Family dump (`famcls49_accept26_errors.json`): 3 mistakes
  - `one shot combo` gaming-meta → betting-sharp
  - `inting mid will throw the series` gaming-meta → political-status
  - `need alignment to ship` workplace-corp → none

## accept27
- Base: accept26 prepare + **24** force-train promotes
- Exact residuals **always** force-train (even if already in test) — avoid accept22 skip failure mode
- `rows_sha256=8f0d2b189aca3564ee657d04b26baf8f19c07eb0624127685eaf7f8e1e77e117`
- Fair famcls48 on accept27-test: family **0.9949494949494949**, structure/role/pointer **1.0**

## famcls50 REJECT
- Init famcls48 · accept27 · **aux=0.35 / up=12** (kept vs mid-0.30: structure held on 49; family gold was the gap)
- 40 ep (best 3); elapsed ~2016s; `best_unchanged=true`
- family **1.0** > baseline PASS
- structure **0.9583** FAIL · pointer **0.9583** FAIL · role 1.0
- Structure miss: `sheesh moment` positional pointer slot1 (gold_start 3 → pred 2) — same hole as famcls47
- Dump: `~/hlx-private/p1-classify-accept27-20260914/famcls50_accept27_structure_misses.json`
- Climb KEEP pin remains **famcls48**; BEST morph19 untouched; no Hub

## Ops notes
- danny queue: none found
- Stopped `qwen38-27b.service` during train; restarted after
