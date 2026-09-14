# Receipt — famcls41 KEEP → accept22 → famcls42

## famcls41 KEEP
- Init famcls25, data accept21, N=8, LR 5e-6, aux=0.12, upsample=4, 40 ep (best 11)
- family 0.9474 > baseline 0.92105; structure/role/pointer 1.0
- Pin: `~/hlx-private/p1-structure-unbind-famcls41-20260914/`

## accept22
- Built from accept21 + 89 residual gold targeting famcls41's 10 holdout misses
- `rows_sha256=3098a25fff59617c4f129befe2c7c44dfe4a5eddf13a4c98edc296b5aa580a2b`
- Fair famcls41 on accept22-test: family **0.9444444444444444**, structure/role/pointer 1.0

## famcls42 (in flight)
- Init famcls41, prepare accept22, same recipe (aux 0.12)
- Gate: family > 0.9444444444444444 AND structure/role/pointer == 1.0
