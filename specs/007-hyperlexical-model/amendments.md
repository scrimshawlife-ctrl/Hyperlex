# Amendments 007

## A1 — C6 ceiling 150M (2026-09-09)

**Operator sentence:** `amend 007 C6 to 150M`

| Before | After |
|--------|-------|
| T1 ≤ 130M | T1 ≤ 150M |
| ModernBERT-base 149M = teacher or amend | ModernBERT-base 149M = legal T1 trunk |

Still out: 7B product card, ModernBERT-large 395M as T1, Spark 200B ceiling as a size argument (C24).

Reason: ModernBERT-base is the better slang-token / MLM unbind trunk vs MiniLM WordPiece. 19M over the old cap. Spark memory is not the reason.

Touches: C6, C24, spec tiers/G2, hardware, trunk-candidates, analyze, checklist, tasks.
