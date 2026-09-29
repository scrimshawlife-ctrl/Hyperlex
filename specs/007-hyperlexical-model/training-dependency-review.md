# Training dependency review

Question: is `RUNE.SEMANTIC_COMPOSITIONALITY_THRESHOLD` a hard dependency of the next training run?

Answer from the contracts that exist today: no. The recorded finding is `SEMANTIC_THRESHOLD_NOT_A_HARD_TRAINING_DEPENDENCY`, and the lane state is `SEMANTIC_EVIDENCE_LANE_DECOUPLED_FROM_TRAINING`.

This review does not authorize training, does not seal `HLX-EXP-2026-09-27-SELECT-005`, and does not clear the residual lane's own `BLOCKED_BY_THRESHOLD_V2_CALIBRATION` flag. That flag stays on the threshold tracker as a statement about the threshold lane. Admission does not read it.

## What SELECT-005 actually requires

`HLX-EXP-2026-09-27-SELECT-005` is an unsealed training-schedule experiment. The proposed variable is `train_schedule`: control `max_epochs=40` with early stopping off, against a candidate with `max_epochs=12`, minimum 4 scored epochs, patience 4, and early stopping on. Both arms pin `classify_macro_f1_nonnone`. The spec record is in `evaluation-reserve.md` under the SELECT-005 sections. No preregistration, arm directory, reserve binding, or admission receipt exists. Epochs and gradient steps for that id remain 0. `training_launch_authorized` is false. BEST still names `hyperlex-encoder-modernbert-base-seed-select004`.

`scripts/shadow/hyperlexical/admission.py` admits a run through `experiment_binding`, `launch_gate`, `holdout_reserve`, `pinned_training_input`, `train_reserve_disjointness`, `single_variable`, `best_trunk`, `output_directory`, and `ready`. The reserve slices are classify, classify_observed, classify_non_none, and unbind_clean. The census still has no fresh `EVAL_RESERVE`. Those are the blockers.

`HLX_THRESHOLD_AUTHORIZATION` is a different object. Its schema is `hyperlex.threshold_authorization.v1`. It seals numeric decision thresholds for the select metric of one experiment id. A missing file stays `BLOCKED_PENDING_OPERATOR_AUTHORIZATION`. It does not mention residual scores, precision 0.80, Wilson bounds, or `RUNE.SEMANTIC_COMPOSITIONALITY_THRESHOLD`.

`specs/007-hyperlexical-model/training-contracts.md` governs proposed evidence bundles (source, annotation, split, run, evaluation). It does not require a semantic-compositionality threshold. A valid bundle does not train or promote.

The residual completion module writes `training_readiness: BLOCKED_BY_THRESHOLD_V2_CALIBRATION` onto the threshold tracker and the completion receipt. Nothing in `admission.py` or the training-contract validator consults `residual_threshold_v2_training_readiness`. The semantic threshold is an expansion and evidence lane. It is not a prerequisite for SELECT-005's scientific validity.

## What remains blocked

SELECT-005 stays unsealed because it still has no fresh reserve and no sealed admission receipt. Semantic-evidence v2 stays `SEMANTIC_EVIDENCE_V2_SPEC_DRAFTED`. Measurement for threshold v2 stays sealed. This review does not resume a training run.
