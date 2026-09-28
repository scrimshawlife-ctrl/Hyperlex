# Threshold v2 postmortem

`THRESHOLD_V2_POSTMORTEM` is the canonical conclusion for `RUNE.SEMANTIC_COMPOSITIONALITY_THRESHOLD.v2`. It does not rewrite the tracker, the measurement manifest, or any sealed artifact.

```text
surface design:  adequate
support:         adequate
direction:       positive but weak
confound:        passed
precision:       insufficient
Wilson:          insufficient
```

Ready HIGH was 13 and ready SECONDARY was 22. Both floors passed. Direction was `SUPPORTED_DIRECTION`: HIGH mean 0.3506075686, SECONDARY mean 0.3203500904, median difference 0.0366953084, Mann-Whitney U 166.000000, rank-biserial 0.160839, descriptive AUC 0.580420. Confound stops were all false. Sixty candidate thresholds were scored. Predicted-YES support passed for 50, the precision floor for 2, the Wilson lower bound for 0, leave-one-out for 0, the REJECT veto for 1, and the QUARANTINE veto for 47. Fully qualified candidates: 0.

The scalar residual carries directional information and does not carry enough precision for production semantic YES evidence. The gates stay where they are. The next scientific work is a new semantic evidence representation, specified separately as `RUNE.SEMANTIC_COMPOSITIONALITY_EVIDENCE.v2`. That work is drafted and not preregistered.

Threshold value remains null. `threshold_frozen` remains false. Measurement remains `SEALED` at sha256 `78ca09ab14912681d028e8b9b1c77a8daf1d0c8c81561434eb9b6ade45a753e5`. v1 remains `CLOSED_CALIBRATION_DESIGN_INSUFFICIENT`.
