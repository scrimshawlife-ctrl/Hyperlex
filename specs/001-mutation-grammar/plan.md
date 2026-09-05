# Plan 001 — Mutation grammar

**Spec**: `specs/001-mutation-grammar/spec.md`  
**Lane**: SHADOW  
**Implement**: not in this commit

## Approach
Additive module. Do not rewrite `src/hyperlex/analysis/mutation.py` into a generator of adversarial stacks. Keep `predict_mutations` as civilian next-form engine. Add a sibling parser.

## Layout
```
src/hyperlex/mutation/
  __init__.py
  operators.py      # enum + lineage map
  packet.py         # dataclass + to_dict
  grammar.py        # parse attested text → packet
  watch.py          # watch_score + pair counters
  lineage_graph.py  # optional DAG edges v0.1 stub
schemas/mutation_trace.v0.1.schema.json
tests/test_mutation_grammar.py
```

Wire:
- `detect_memetic_patterns` after lineage: call parse on query + recovered terms.
- CLI `mutation-trace`.
- Docs: glossary row, slang-lineages operator table addendum, STATUS line.
- SKILL.md When to Use: mutation trace / grammar watch (detector).

## Phase order
1. Schema + enum + packet + tests.
2. Parser L2/L3/L5 only (affix, lexical substitute, register heuristics).
3. watch_score + lexicon vs novel-op counters (in-memory / receipt-derived).
4. Analyze attachment + CLI.
5. Restricted-flag redaction tests.
6. Docs + skill contract.
7. Converge / operator review. Hold production.

## Risks
- Dual-use bleed from expanding `predict_mutations` operators. Mitigation: constitution VII; no new prediction ops in 001.
- Register heuristics will be crude offline. Label INFERRED.
- Watch_score Goodhart. Ship the pair, not the single metric.
