# Receipt — famcls47 REJECT → famcls48 aux=0.35/up=12

## famcls47 REJECT
- Init famcls46 · accept25 · N=8 · LR 5e-6 · aux=0.25 · upsample=8 · 40 ep (best 8)
- family **0.9949494949494949** > baseline 0.98989898989899 PASS
- structure **0.9583** FAIL · pointer **0.9583** FAIL · role 1.0
- `best_unchanged=true`; BEST morph19 untouched
- Structure miss: `sheesh moment` positional pointer slot1 (3→2)
- Dump: `~/hlx-private/p1-classify-accept25-20260914/famcls47_accept25_structure_misses.json`

## Next
- famcls48: same init/data; **aux=0.35** upsample=**12**; gate family > 0.98989898989899 + structure/role/pointer 1.0
- Weight pin remains famcls46 until a KEEP clears structure again
