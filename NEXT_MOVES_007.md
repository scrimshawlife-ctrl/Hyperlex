# 007 Hyperlexical T1 Data Prep - Next Moves Plan (2026-09-11)

## Current State
- Civilian: 5857 rows (exceeds 2500)
- High-signal: 1481 (enriched eff=0.368)
- Heavy 4333-dump (ai-native, memory/provenance)
- Efficiency missing in main civilian export
- Eval done (high-signal + unbind stub baseline)
- Docs/MANIFEST/Notion updated

## Prioritized Plan (execute in order)
1. **Enrich full civilian** with memetic_efficiency + memory_tiers (post-process via detect_memetic_patterns on rows missing it).
2. **Refresh high-signal** from enriched civilian (apply same filters).
3. **Re-run official export** (to ensure clean pipeline output if harvest can be improved, but primarily validate).
4. **Copy training artifacts to exports/** (high-signal, ai-native, 4333 subset, eval report).
5. **Run full evals**:
   - High-signal metrics (post-refresh)
   - eval_unbind harness
   - Shadow pytest (export + eval)
   - Preflight check
6. **Update docs**:
   - MANIFEST.json (training_prep + last_eval)
   - dataset-harvest.md (plan execution + new numbers)
   - AARON-SPARK-TRAIN.md if needed for training notes
7. **Update Notion parity** on key pages.
8. **Verify**:
   - Splits (train/val/test)
   - Quotas vs harvest.md (classify volume, unbind readiness)
   - Schema completeness (roles/fillers, provenance, efficiency)
9. **Final readiness**:
   - Note for Spark train (oversample high-signal for memory signals)
   - Any remaining gaps (e.g., more unbind atoms if possible)
10. **Cleanup** (optional): prune temp, commit summary if git.

## Success Criteria
- Civilian has efficiency/tiers on 100% ai-native/memory rows
- High-signal >=1400 with avg eff >0.3
- Exports/ has all training artifacts
- Docs reflect exact counts
- Evals show strong ai-native/memory signal
- Ready to hand to train.py / Spark

## Risks/Notes
- 4333 rows are mostly INFERRED; preserve as-is.
- Unbind readiness low (~22%); that's data reality for slang atoms.
- Re-export may be needed if harvest_4333_dump updated to call analysis.
