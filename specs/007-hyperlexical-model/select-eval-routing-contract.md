# SELECT evaluation routing contract

`SELECT_005_SETTLEMENT_ROUTING_CONTRACT_EXTENSION_AUTHORIZATION` freezes a derivative path from one canonical settlement to SELECT reserve slices.

Canonical settlement and SELECT routing stay separate. A routing record references a settlement by `row_id` and `source_settlement_hash`. It does not rewrite `settlement/events.jsonl`, and it is not an identity-ledger event.

Procedure id: `select_eval_routing_v1`. Schema: `hyperlex.eval_routing.v1`. Routing version: `v1`.

## State

`ROUTING_CONTRACT_DRAFTED` names the family. `ROUTING_CONTRACT_FROZEN` is this specification plus the schema. `ROUTING_VALIDATION_COMPLETE` means the reference corpus validates and two reconstructions are byte-identical.

Failure states are `ROUTING_SCHEMA_FAILURE`, `ROUTING_SEMANTIC_VALIDATION_FAILURE`, and `ROUTING_NONDETERMINISTIC`.

## Store

Routing records live in the private evaluation evidence store at `eval-reserve-20260926/routing/events.jsonl`, append-only, mode 0600. They are not mixed into the identity ledger and not appended to `settlement/events.jsonl`. This pass writes no routing events.

## Fields

`task` is the training-label task. The canonical vocabulary is `classify` and `unbind`.

`class` is the registry attest class. The canonical vocabulary is `OBSERVED` and `INFERRED`, the same pair as settlement `attest`. It is not the semantic family and not the operator decision. Routing copies `attest`. A metadata `class` that differs from `attest` is `CLASS_PROMOTION_REFUSED`. `INFERRED` is not promoted to `OBSERVED`.

`lineage` is the semantic family copied from settlement `semantic_family`. The vocabulary is `none` plus the active evaluation families. `none` is the abstain family. It is not a registry class.

`unbind_clean` is the boolean already computed by `soft_ceiling.clean_surface`. Routing copies it only when `task` is `unbind` and `unbind_clean_derivation` is `soft_ceiling.clean_surface`. It is not set because a reserve slice is empty.

`rights_state` is the settlement rights string. Routing does not reinterpret a license. The cleared token is `CC-BY-SA`, from `wiktionary_category` and `wikipedia_prose` only.

`provenance_state` is `COMPLETE` or `INCOMPLETE`. `COMPLETE` requires a non-empty `source_identity` and a non-empty settlement `provenance`. Missing provenance is not inferred.

## Slice rules

The predicate is `identity_ledger.slices_of`. One routing record has one task. That record may enter every classify slice it satisfies. `unbind_clean` does not co-occur with a classify slice on the same record, because those slices require different tasks.

Settlement exclusions still win before routing. `TRAIN_CONSUMED`, `EVAL_SPENT`, `EVAL_ABANDONED`, the pinned export, unresolved rights, and a non-admissible decision are unchanged. Routing is consulted only when the settlement would otherwise be `SLICE_LABELS_ABSENT`.

`classify` requires decision `ACCEPT`, `RECLASSIFY`, or `NONE`, rights `CC-BY-SA`, provenance `COMPLETE`, and `task` `classify`.

`classify_observed` requires `classify` and registry `class` `OBSERVED`.

`classify_non_none` requires `classify` and `lineage` outside `""` and `none`.

`unbind_clean` requires `task` `unbind` and the frozen `unbind_clean` flag true.

`UNRESOLVED` is not routable. `NONE` can enter `classify` and can enter `unbind_clean` when the frozen flag is true. `NONE` does not enter `classify_non_none`, because its family is `none`. `ACCEPT` and `RECLASSIFY` use the same slice predicate. Routing does not repeat the settlement family's proposed-evidence check.

Rights other than `CC-BY-SA` are `INELIGIBLE` with `RIGHTS_NOT_CLEARED`. Provenance that is not `COMPLETE` is `INELIGIBLE` with `PROVENANCE_INCOMPLETE`.

## What routing does not read

Routing refuses `reserve_counts`, `desired_slice`, `routed_counts`, `current_reserve_deficits`, `planning_targets`, `admission_floors`, `prediction`, `model_score`, `candidate_score`, `model_error`, `residual`, `semantic_evidence`, and `threshold_v2`. The same settlement produces the same record whether or not a slice quota is open. Candidate scores, threshold-v2 residuals, and semantic-evidence features are not inputs.

No RNG. The procedure hash is the sha256 of the canonical rule table. Two calls on the same frozen inputs are byte-identical.

## Admission

`census(..., routing_by_row=...)` joins a validated routing record when the settlement itself has no `task`. Omitting the map preserves the previous census. `admit_training_run` still consumes a sealed reserve binding. It does not require routing records, so SELECT-004 bindings stay valid. This pass does not recensus the 339 settlements and does not create a SELECT-005 admission receipt.

## Other schemas

`hyperlex.threshold_authorization.v1` and `hyperlex.admission.v1` now have JSON Schema documents. Historical artifacts are `VALIDATE_ONLY`. SELECT-005 metric numbers stay unset. `HLX_THRESHOLD_AUTHORIZATION` remains `BLOCKED_PENDING_OPERATOR_AUTHORIZATION`.

## Next transition

`SELECT_005_FRESH_SOURCE_HARVEST_AND_ROUTING_AUTHORIZATION` waits on a box exposure snapshot no older than 6 hours. This pass does not refresh that snapshot and does not harvest.
