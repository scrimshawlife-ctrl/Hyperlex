# V6 evaluation contract (preregistered before train)

```json
{
  "distribution_shift_reporting": {
    "always_report_side_by_side": [
      "DEVELOPMENT_VALIDATION",
      "REPRESENTATIVE_VALIDATION"
    ],
    "large_delta_is_first_class_failure_signal": true
  },
  "preregistered_before_train": true,
  "stage_a": [
    "false_entry",
    "PRESENT_recall",
    "NONE_recall",
    "UNCERTAIN_recall",
    "macro_F1"
  ],
  "stage_b": [
    "family_precision",
    "macro_family_F1",
    "top1",
    "top2",
    "selective_accuracy",
    "coverage"
  ],
  "system": [
    "end_to_end_family_precision",
    "end_to_end_family_recall",
    "abstention",
    "Stage_A_induced_errors",
    "Stage_B_induced_errors",
    "compound_errors"
  ]
}
```
