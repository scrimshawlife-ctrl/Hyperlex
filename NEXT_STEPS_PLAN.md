# Hyperlex + Moltbook Continuation Plan

## Current State (as of last session)
- 18 curated seeds from Moltbook agent discourse (memory, context loss, provenance, rented cognition, etc.)
- Classifiers: classify_compression_type, compute_context_friction, detect_memetic_memory_patterns (improved tiers with seed boost + direct matches), compute_memetic_efficiency_score
- Top-level memetic_efficiency in detect results
- arXiv cross-refs (Eywa, ECHO, Agent Zero Memory, etc.) wired for Moltbook
- Curation script: scripts/curate_moltbook_seeds.py
- Heartbeat integration (logs efficiency/tiers)
- 20 tests passing
- Fresh batch results
- Docs/symbolic partially updated
- Feature branch: feat/moltbook-agent-memetics-assimilation (pushed, PR compare ready)

## Recommended Continuations (aggregated from history)
1. **Grow dataset aggressively** (periodic from logs/batch + fresh fetches)
2. **Strengthen virality scoring** with efficiency/friction (make it hybrid with memetic signals)
3. **Improve classification robustness** (reduce 'unknown' tiers, more synonyms, better boosting from seeds/arXiv)
4. **Deeper arXiv integration** (pull specific concepts, use in markers or few-shot)
5. **Expand integration points** (CLI, receipts, main scoring, synthesis)
6. **Update all docs/symbolic** (README, SKILL.md, SKELETON.md, HANDOFF.md, examples)
7. **Run experiments & verify** (larger batches, stats on efficiency, tests for new paths)
8. **Automation** (enhance heartbeat for auto-curation, regular scoring)
9. **Polish & release prep** (version bump, full test, branch updates for PR)

## Execution Plan (step-by-step, to be executed now)
1. Fetch fresh Moltbook memory/agent posts (10+), distill 4-5 new high-signal seeds, append, rebuild index (target 23+ seeds).
2. Enhance compute_virality_score to natively blend memetic_efficiency and friction (update hybrid_score).
3. Expand tier synonyms and context_loss_techniques with terms from new posts + arXiv (e.g. "rented", "export", "bitemporal", "surprise-driven").
4. Improve seed boosting logic and add arXiv concept markers to classify_*/detect_* functions.
5. Pull 2-3 arXiv abstracts (using web tools or curl) and hardcode key phrases into analysis for boosting.
6. Add memetic_efficiency and memory fields to top-level result and update synthesis/receipts more deeply.
7. Enhance CLI (__main__.py) with subcommands or flags for --memory-analysis, --efficiency.
8. Update heartbeat to periodically curate high-eff items and run batch scoring.
9. Run large batch (10+ posts), compute stats (avg efficiency, tier distribution), save to out/.
10. Update docs: expand README, SKILL.md (version to 1.7), symbolic/* (add new functions to skeleton), add to examples/.
11. Add 2-3 new tests for virality blend, arXiv boost, CLI.
12. Full pytest + manual verification runs.
13. Commit all to main + feature branch, push feature.
14. Update PR_MOLTBOOK_MEMETICS.md with new items.
15. Final status report + any blockers.

## Acceptance
- 23+ seeds
- Efficiency influencing virality
- <10% 'unknown' tiers on memory topics
- All tests pass (22+)
- Fresh batch + stats
- Docs current
- Feature branch updated
