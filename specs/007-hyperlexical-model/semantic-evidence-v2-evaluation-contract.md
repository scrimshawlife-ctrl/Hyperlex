# Semantic evidence v2 evaluation contract

No evaluation is authorized by this draft. The order, once a preregistration exists, is:

```text
1. coverage
2. directional separation
3. cross-validated calibration stability
4. precision
5. Wilson lower bound
6. HIGH recall
7. REJECT veto
8. QUARANTINE veto
```

Support floors stay ready HIGH at least 12 and ready SECONDARY at least 8. Precision floor stays 0.80. Wilson lower bound stays 0.50. REJECT predicted YES and QUARANTINE predicted YES stay 0. HIGH is the positive class and SECONDARY is the negative class. REJECT and QUARANTINE are vetoes after the fit, not standard negatives.

The comparative requirement against the frozen v2 scalar residual is `BASELINE_COMPARISON_REQUIRED`. A candidate reports baseline, candidate, and delta on the same rows. Beating AUC 0.580420 is not yet a hard gate. A family advances only when direction is supported, the frozen confound stops do not fire, leave-one-out behavior is stable, and the report shows a material improvement with a plausible route to the precision and Wilson floors. Early representation exploration does not have to freeze a threshold.

Model-combination experiments use leave-one-out on the small ready support. Folds do not select a different representation. Representation-family selection happens outside the final threshold surface. The selection order, to be frozen before execution, is safety eligibility, cross-validated precision potential, Wilson lower-bound potential, directional AUC, then the simpler representation.

Candidate calibrators, after the feature vector is frozen, are a single-feature threshold baseline, L2 logistic regression, and a monotonic or constrained linear score. Hyperparameters are frozen before calibration evaluation. Measurement is not a tuning set. Deep classifiers are out of this first comparison.

Every report includes the MiniLM plus `normalized_mean_v1` plus `1 - cosine` baseline.

Training is not resumed because this lane exists. A later handoff state `SEMANTIC_EVIDENCE_READY_FOR_TRAINING_INTEGRATION` would require the evaluation chain to succeed, and a separate training spec would then decide any effect on unbind source construction, negatives, sampling, curriculum, or loss weighting. Those choices are not in this contract.
