Implemented: read-only recovery diagnostic and synthetic controls; occurrence-aware
preparation (#63); explicit reviewed trainer path (`training_reviewed_loop.py`) that
consumes `PREPARED_NOT_RUNNABLE` plans only, preserves occurrence IDs / pinned
`token_indices` / train-only vocabularies, refuses train-set eval fallback, audits
that consumed example IDs ⊆ selected train IDs, records runtime/recipe identity in

### 2026-09-15 — morph37 warm REJECT_VS_BEST

- Init: `HYPERLEX_INIT_FROM=morph36` (BEST primary) + `HYPERLEX_SAVE_BEST_UNBIND=1`, epochs=40.
- best **0.5317** (ep2) < morph36 BEST **0.5455**; final 0.5014; E2 PASS.
- Decision: **REJECT_VS_BEST**; BEST remains morph36; morph19 still preserved.
- Ladder 0.55 still MISS. Waiting Danny gold. **No more schedule clones without a new lever** (no morph38).
- No invented OBSERVED gold. `name_gate=false`.
