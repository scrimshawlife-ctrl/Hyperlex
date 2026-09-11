# 007 Hyperlexical T1 Training Readiness

**Date**: 2026-09-11
**Civilian**: 5857 rows (specs/007-hyperlexical-model/exports/civilian.v0.1.jsonl)
**High-signal oversample**: 1501 rows (exports/training/training_high_signal.jsonl)
  - avg_efficiency: 0.278
  - ai-native: 1101 (73.4%)
  - from_4333_dump: 1135 (75.6%)
  - hyperstition_ish: 18 (1.2%)
  - unbind_ready (roles+fillers): 328 (21.9%)
**Key subsets**:
- training_ai_native.jsonl (1101+)
- training_4333_dump.jsonl (full 4333 provenance)
**Evals**:
- high_signal_eval.json (above metrics)
- eval_unbind_report.json (stub baseline vs 004 probe; e2_pass=false expected)
**Pipeline**:
- harvest_4333_dump now calls detect_memetic_patterns inline → efficiency, memory_tiers, compression_type populated at export time.
- All rows have required schema + extensions (provenance, typology, stage).
**Best practices followed**:
- Ranked sources (Notion 4333 as high-value ai-native + memory/provenance).
- Strict provenance.
- Dedup + full classification.
- High-signal for oversampling memory signals.
- Honest counts (no label upgrades).
**Next**:
- Load civilian + oversample high-signal in train.
- Use HYPERLEX_ALLOW_TRAIN=1 + local trunk for Spark run.
- Re-eval after training (E2 gate vs 004 probe).

Artifacts in exports/training/ ready for use.
