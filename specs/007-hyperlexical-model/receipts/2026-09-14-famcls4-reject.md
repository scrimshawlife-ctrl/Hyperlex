# REJECTED — famcls4 frozen family-head (2026-09-14)

**Authority:** Spec 007. BEST untouched.

## Recipe
Init famcls → accept prepare. Freeze encoder+structure. Train family head only with inverse-frequency CE (40 ep).

## Fair accept-test

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls baseline | 1.0 | 1.0 | 1.0 | **0.659** |
| famcls4 (best ep1) | 1.0 | 1.0 | 1.0 | **0.591** |

## Verdict
**REJECT.** Failed gate family > 0.659.

Weight joint stays **famcls**. Data pin stays **accept prepare**.

## Follow-on
Pause CE/head/sampler thrash. Need more reviewed labels before another resume.
