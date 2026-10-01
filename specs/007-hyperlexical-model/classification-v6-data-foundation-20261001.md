# BUILD_REPRESENTATIVE_V6_DATA_FOUNDATION

```text
V6_DATA_FOUNDATION_STATE = V6_DATA_FOUNDATION_PARTIAL
NEXT_ACTION = REVISE_HYPERLEX_V6_ONTOLOGY_BEFORE_MODELING
RECEIPT = 8ea02186f28afd517c25fef2782e6e5930523ac403ecd01087734c4616383357

split_counts =
  TRAIN 2796
  DEVELOPMENT_VALIDATION 506
  REPRESENTATIVE_VALIDATION 1250
  QUALIFICATION 486

gates (all true) =
  OPERATING_DISTRIBUTION_DEFINED
  GOLD_CONTRACT_VALID
  ONTOLOGY_AUDITED
  TRAIN_READY
  DEV_VALIDATION_READY
  REPRESENTATIVE_VALIDATION_READY
  QUALIFICATION_SEALED
  BASE_REPRESENTATION_AUDITED

disjointness_pass = true
ontology_structurally_broken = true
representation_viability = BASE_REPRESENTATION_INADEQUATE
retrieval_viability = RETRIEVAL_NOT_VIABLE
```

No V6 train. No V5 retune. Qualification holdout rows are private/sealed.

## Why PARTIAL (not READY)

Volume/role gates and audits completed, but ontology geometry under frozen
`MODEL_WIDE_BEST` remains structurally broken (152/153 family pairs
`ONTOLOGY_REVIEW_REQUIRED`; between-family centroid similarity ≈ 0.980 >
within-family ≈ 0.822). Representation and exemplar-retrieval prototypes are
not viable on the representative surface. Human second-rater agreement remains
awaiting operator annotation (protocol + 120-row sample sealed).
