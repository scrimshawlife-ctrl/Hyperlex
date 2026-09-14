# Receipt — famcls43 REJECT → famcls44 aux=0.18

## famcls43 REJECT
- Init famcls41, data accept23 (force-train residuals), N=8, LR 5e-6, aux=0.12, 40 ep (best 39)
- family **0.9848** > baseline 0.9444 PASS
- structure **0.9583** FAIL · pointer **0.9583** FAIL · role 1.0 held
- Lesson: force-promoting exact residuals unlocks family; KEEP aux=0.12 no longer holds structure on accept23

## famcls44 (in flight)
- Same init/data/N/LR; **aux=0.18**; baseline still 0.9444444444444444
- Gate: family > 0.9444 AND structure/role/pointer == 1.0
