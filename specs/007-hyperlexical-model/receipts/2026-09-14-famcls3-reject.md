# REJECTED — famcls3 accept-label resume (2026-09-14)

**Authority:** Spec 007. BEST untouched.

## Fair holdout on accept-prepare test

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| **famcls** (keep) | 1.0 | 1.0 | 1.0 | **0.659** |
| famcls3 | 1.0 | 1.0 | 1.0 | 0.636 |
| majority | | | | 0.568 |

## Verdict

**REJECT famcls3 weights** — family regresses vs famcls on the same test; structure only ties.

**KEEP** operator-accepted prepare as **data pin**:
`~/hlx-private/p1-classify-accept-20260914/prepare`.

Working weight joint remains **famcls**.
