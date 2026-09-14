# Receipt — famcls47 REJECT → famcls48

## famcls47 REJECT
- Init famcls46 · accept25 · N=8 · LR 5e-6 · aux=0.25 · upsample=8 · 40 ep (best 8)
- family **0.9949** > 0.98989898989899 PASS
- structure/pointer **0.9583** FAIL (23/24); role 1.0
- Single miss: `"sheesh moment"` positional pointer off-by-one (slot1 gold_start 3 → pred 2)

## Weight pin
Stays **famcls46** (KEEP). Data stays accept25. BEST untouched.

## famcls48 (in flight)
- Same init/data/baseline; **aux=0.35** · **upsample=12** (raised after structure slip)
- Do not clone identical 0.25/8 recipe
