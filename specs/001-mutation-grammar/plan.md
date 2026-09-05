# Plan 001 — Mutation grammar

**Spec**: `spec.md` + `clarify.md`  
**Lane**: SHADOW  
**Implement**: not in this commit

## Approach
Sibling package `hyperlex.mutation`. Do not fold detection into `analysis/mutation.py`. That file stays `predict_mutations`.

## Layout
```
src/hyperlex/mutation/
  __init__.py
  operators.py
  packet.py
  grammar.py
  watch.py
  lineage_graph.py      # stub ok in v0.1
schemas/mutation_trace.v0.1.schema.json   # already added
tests/test_mutation_grammar.py
```

Wire after lineage inside `detect_memetic_patterns`. Receipt emit runs redaction helper first.

## Order
1. Packet + schema tests (restricted `allOf`).
2. L2/L3/L5 parser + COMPOSE.
3. watch_score + pair counters.
4. Analyze attachment + CLI.
5. Docs / SKILL / STATUS.
6. Operator review.

## Dual-use review questions (merge gate)
1. Can a test fixture be reused as a restricted wrap? If yes, delete it.
2. Does any path call `predict_mutations` after restricted flag? If yes, block merge.
3. Does watch_score get written into a Brier field? If yes, block merge.
