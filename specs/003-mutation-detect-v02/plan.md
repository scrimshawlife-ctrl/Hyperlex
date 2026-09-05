# Plan 003 — Mutation detect v0.2

**Spec**: `spec.md`  
**Lane**: SHADOW / advisory  
**Constitution**: stays SHADOW (do not amend)

## Approach
Keep `hyperlex.mutation` as the detector package. Do not fold v0.2 into `analysis/mutation.py` (that file stays `predict_mutations`). Invert `_vowel_drop` for PHONETIC_WARP detect; do not call predict from the parser.

## Layout
```
specs/003-mutation-detect-v02/
  spec.md
  plan.md
  tasks.md
  dual-use-gate.md
src/hyperlex/mutation/
  detect.py          # GAME_ENCODE / CODE_SWITCH / PHONETIC_WARP heuristics
  grammar.py         # wire detect after v0.1 ops, before COMPOSE
  operators.py       # closed marker / particle tables
  watch.py           # watch_score + jsonl writer/reader
  human.py           # --human card
  __init__.py
src/hyperlex/cli.py  # trace --human --watch-jsonl; mutation watch
tests/test_mutation_v02.py
```

`scripts/hlx-mutation` already forwards argv to the package CLI — no second parser.

## Order
1. Spec artifacts (this folder).
2. Parsers + civilian fixture tests.
3. Watch jsonl + tests (fail-open, auto_fire false).
4. `--human` card + tests.
5. CLI + router + SKILL.md (SHADOW advisory).
6. Verify; new PR.

## Dual-use review questions (merge gate)
1. Can a test fixture be reused as a restricted wrap? If yes, delete it.
2. Does any path generate a language-game or code-switched restricted paraphrase? If yes, block merge.
3. Does watch_score write Brier or fire a tool/cron/rune? If yes, block merge.
4. Did we add wrap / compose / asr verbs? If yes, block merge.

## Non-touches
- `.specify/memory/constitution.md`
- Installer / `tests_audit/`
- Spec 001 T1–T11 redo
- Issue / PR #5
- FRAME_WRAP expansion, SAE, COMPOUND
