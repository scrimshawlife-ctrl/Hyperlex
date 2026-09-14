# Receipt — famcls46 KEEP → accept25 → famcls47

## famcls46 KEEP
- Init famcls45 · accept24 · N=8 · LR 5e-6 · aux=0.25 · upsample=8 · 40 ep (best 1)
- family **0.9899** > 0.9545454545454546; structure/role/pointer **1.0**
- Residuals on accept24-test (2): `one shot combo` (gaming→betting), `ser so back onchain` (crypto→betting)

## accept25
- +24 train force-promotes for 2 famcls46 residuals (+ contrastives / hard-negs)
- Fair famcls46: family **0.98989898989899**, structure/role/pointer 1.0

## famcls47 (in flight)
- Init famcls46 · accept25 · same KEEP recipe · baseline 0.98989898989899
