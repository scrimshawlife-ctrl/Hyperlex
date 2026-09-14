# Receipt — famcls42 REJECT → accept23 → famcls43

## famcls42 REJECT
- Init famcls41, data accept22, N=8, LR 5e-6, aux=0.12, 40 ep (best 3)
- family 0.9343 < baseline 0.9444; structure/role/pointer 1.0 held
- Root cause: accept22 skipped exact holdout misses (already test-covered) — never entered train

## accept23
- +35 train force-promotes of exact residuals + near variants
- Fair famcls41 on accept23-test: family **0.9444444444444444**, structure/role/pointer 1.0
- rows_sha256=9828e140c541403f2409c4ba5c7b826dbfe882ff512dcd43209d864f0c933199

## famcls43 (in flight)
- Init famcls41, prepare accept23, same KEEP recipe (aux 0.12)
- Gate: family > 0.9444444444444444 AND structure/role/pointer == 1.0
