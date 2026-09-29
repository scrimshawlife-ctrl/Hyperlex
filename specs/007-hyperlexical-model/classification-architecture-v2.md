# HYPERLEX_CLASSIFICATION_ARCHITECTURE_V2

**State**: `CLASSIFICATION_V2_SPEC_DRAFTED`
**Schema**: `hyperlex.classification.v2`
**Packet**: `hyperlex.jev.decision_packet.v1`
**Contract**: `scripts/shadow/hyperlexical/classification_v2.py`
**Lane**: SHADOW specification. Not a SELECT campaign.
**Does not authorize**: training, preregistration, BEST promotion, `JEV_MODE = GATED`

SELECT-006 remains `SETTLED_PASS`. SELECT-007 remains `SETTLED_FAIL`. Neither experiment is reopened. Production BEST stays the reference checkpoint:

```text
9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6
```

This document does not move it.

## Problem

The live classify head is one softmax over `layout.FAMILIES`: eight community names plus `none`. That single distribution is being asked to answer six different questions at once:

```text
does a family apply?
which family applies?
is evidence sufficient?
is the example ambiguous?
is the model uncertain?
is none actually the correct semantic outcome?
```

SELECT-007 showed the cost of treating those as one sampling problem. Capping INFERRED `none` at the OBSERVED `none` count changed training frequency and did not change reserve `predicted_none_rate`. The abstention behavior is in the decision, not in the epoch mix. Another sampling tweak is out of scope.

Spec 007 already forbids a numeric Brier on `hyperlex.hyperlexical.inference.v0.1` and forbids a `brier_head`. This architecture does not relax that rule. Calibration scores below are evaluation metrics. They are not packet fields and they are not a new head.

## Journey

An operator asks Hyperlex what semantic family, if any, a span supports.

The encoder offers applicability, a family distribution over the active vocabulary, and a confidence surface. A deterministic policy then emits one of four outcomes: a family, semantic `NONE`, epistemic `ABSTAIN`, or `AMBIGUOUS`. Those words are not aliases.

When the operator has explicitly enabled shadow mode, a provider-neutral judge may score ambiguity, escalation, or disagreement around that result. The judge's packet is evidence about a probabilistic judgment. It is not the label, not the canon, not the settlement, and not the reserve.

With the judge disabled, which is the default, the same policy still emits a result.

## Workflow

```text
deterministic eligibility filter
        ↓
Hyperlex learned inference
        ↓
deterministic structural validation
        ↓
optional Jev typed judgment          # skipped when JEV = OFF
        ↓
deterministic policy validation
        ↓
emit / abstain / ambiguous / review
```

Eligibility admits only the active families the loaded checkpoint can actually score. Structural validation rejects `none` inside the family distribution, rejects legacy names as if they were active, and rejects a family outside the eligible set. Jev runs only after that filter, only on an operational surface, and only in shadow mode during this specification. Policy validation runs again after the packet. A packet cannot skip a failed check.

Unbind stays on its own heads. This workflow does not retarget role or filler loss.

## State transition

### Specification lifecycle

This pass uses the compact governance vocabulary only as a name for a future validation run. No such run exists, so the architecture is not `PREREGISTERED`.

```text
CLASSIFICATION_V2_SPEC_DRAFTED
        ↓  only when a concrete validation run is preregistered
PREREGISTERED → READY → RUNNING → SETTLED_PASS | SETTLED_FAIL | SETTLED_INVALID
```

This draft does not take that step. It does not recreate source-design, admission-only, loader-authorization, launch-authorization, or standalone threshold states. Evidence checks belong in readiness of that future run, not in extra states here.

### Per-example decision

```text
Q1 evidence insufficient ──────────────► ABSTAIN
Q1 sufficient
Q2 applicability NONE ─────────────────► NONE
Q2 FAMILY_PRESENT
Q3 MULTI_OR_UNCLEAR ───────────────────► AMBIGUOUS
Q3 SINGLE
Q4 strongest eligible family
Q5 family confidence below floor ──────► ABSTAIN
Q5 floor met ──────────────────────────► FAMILY
```

`Q1` is not the same predicate as `Q5`. `Q3` is not the same predicate as `Q5`.

## Decision ontology

| Token | Kind | Meaning |
| --- | --- | --- |
| `ABSTAIN` | epistemic | The system will not emit a semantic decision. |
| `NONE` | semantic | Evidence is sufficient and no active family applies. |
| `AMBIGUOUS` | semantic | More than one family is plausible, or no unique family is supported. This is not low confidence. |
| `FAMILY` | semantic | One eligible active family is supported. `family` carries that name. |

Namespace collisions that must stay explicit:

| Name | Where it lives | What it is not |
| --- | --- | --- |
| v2 `ABSTAIN` | `hyperlex.classification.v2` decision | not the string `none` |
| v2 `NONE` | `hyperlex.classification.v2` decision | not v1 softmax class `none` and not v2 `ABSTAIN` |
| v1 class `none` | `layout.FAMILIES` logit | not a v2 decision. Adapter status: `NOT_A_V2_DECISION` |
| `eval_settlement.ABSTAIN = "none"` | operator settlement token | not v2 `ABSTAIN` and not a classify head |

`OBSERVED` and `INFERRED` are provenance classes. They are not families and the model is not required to predict them. `provenance_context` on a v2 result is caller context: `OBSERVED`, `INFERRED`, or `UNKNOWN` at inference.

## Learned, derived, calibrated, policy, judge

Smallest surface that keeps the four outcomes distinct:

| Question | Kind | Mechanism |
| --- | --- | --- |
| Q2 applicability | learned | 2-way head: `NONE`, `FAMILY_PRESENT` |
| Q4 family identity | learned | softmax over eligible active families only. `none` is not a class |
| Q3 ambiguity | derived now | margin between the top two family probabilities. A learned `SINGLE` / `MULTI_OR_UNCLEAR` head is reserved and its loss stays masked until an explicit ambiguity gold surface exists |
| Q1 evidence | derived + deterministic | applicability confidence against a caller-supplied floor |
| Q5 emission | calibrated + deterministic | family confidence against a separate caller-supplied floor |
| calibration reports | evaluation | ECE, Brier, reliability, margins, coverage, selective risk. Not a head |
| disagreement, escalation, review advice | optional Jev, shadow only | recorded, not canonical |

No default is given for either floor. A zero or one floor is `evidence_floor_unconfigured` or `confidence_floor_unconfigured`. Choosing the floors is a later preregistration, not this draft.

Target encoder remains the Spec 007 trunk: `answerdotai/ModernBERT-base`, hidden 768, pool token 0. Shared encoder, separate task heads. Unbind role and filler heads are unchanged.

```text
ModernBERT encoder
        │
        ├── applicability head          learned, required
        │     NONE | FAMILY_PRESENT
        ├── active-family head          learned, required, masked
        │     current eligible families only
        ├── ambiguity head              reserved, masked until gold
        └── unbind role / filler heads  existing, separate
```

The confidence surface is the calibrated reading of those heads. It is not `brier_head`. `layout.describe` continues to forbid `refusal_head`, `brier_head`, and `chat_template`. The v0.1 inference packet keeps `brier: null`. A v2 result also keeps `brier: null` and `forecast_eligible: false`. v2 does not write `semantic` into Spec 005 `routes_claimed`.

## Deterministic policy

```text
if evidence_insufficient:
    ABSTAIN
elif applicability == NONE:
    NONE
elif ambiguity == MULTI_OR_UNCLEAR:
    AMBIGUOUS
elif family not in eligible or family_confidence < floor:
    ABSTAIN
else:
    FAMILY_X
```

Implemented by `final_decision`. Jev is not an argument. `AMBIGUOUS` and `NONE` clear `family`. A low family confidence on a single supported family is `ABSTAIN`, not `AMBIGUOUS` and not `NONE`.

## Loss

Normative decomposition, without double-counting:

```text
total_loss =
    provenance_weight(row) * applicability_loss(row)
  + ambiguity_weight(row) * ambiguity_loss(row)
  + provenance_weight(row) * family_loss(row)
  + unbind_loss
```

The user's five names map onto that expression as follows.

| Named term | Contract |
| --- | --- |
| `applicability_loss` | CE on `NONE` vs `FAMILY_PRESENT` when a semantic target exists |
| `ambiguity_loss` | CE only when `ambiguity_gold` is `SINGLE` or `MULTI_OR_UNCLEAR`. Otherwise mask 0 |
| `family_loss_on_family_examples` | CE on the active-family head only when `lineage` is a supervised active family |
| `provenance_weighted_weak_supervision` | the per-row multiplier above. Not a second CE |
| `unbind_loss` | existing unbind loss. This contract returns `separate_unchanged` and does not reweight it |

Mask:

- `lineage == none`: applicability target `NONE`. Family loss off. Do not train `none` as a family.
- `lineage` in the supervised active set: applicability target `FAMILY_PRESENT`, family target that lineage.
- legacy head name (`brainrot-aura`, `kinship-address`, `political-status`, `workplace-corp`): no family loss and no silent remap.
- `ABSTAIN` is not a family-head class and not an applicability class.
- `AMBIGUOUS` is not a family-head class. Without explicit ambiguity gold it is only a derived emission.

`supervised_families` defaults to the weight-backed intersection below. A caller may narrow it. It may not add `none` or a name outside `ACTIVE_FAMILIES`.

## OBSERVED / INFERRED

Provenance changes the multiplier. It does not change the target ontology.

| Row | Applicability | Family |
| --- | --- | --- |
| OBSERVED non-none | strong | strong |
| INFERRED non-none | weaker than the OBSERVED pair | weaker than the OBSERVED pair |
| OBSERVED none | strong `NONE` | masked off |
| INFERRED none | weak `NONE`, strictly below OBSERVED none | masked off |

`validate_supervision_weights` is the contract. There is no default weight table in this draft. SELECT-007 does not justify a number: the frequency cap failed its none-rate gate.

Bounds and relations, all required:

- every weight is finite and in `(0, 1]`
- keys are exactly the six supervision keys, no extras
- `observed_non_none_applicability > inferred_non_none_applicability`
- `observed_non_none_family > inferred_non_none_family`
- `observed_none_applicability > inferred_none_applicability`

A future validation run must preregister the six numbers, show OBSERVED and INFERRED metrics separately, and fail closed if a weight set violates the order. Equal weights are `inferred_not_weaker`.

## Active ontology

The family head's label set is the active Hyperlex ontology, not every string that happens to sit in a historical checkpoint.

`eval_settlement.ACTIVE_FAMILIES` is that ontology. `CANDIDATE_FAMILIES` stay inactive. The current v1 head only has trained rows for the intersection:

```text
betting-sharp
crypto-degen
ai-native
gaming-meta
```

`checkpoint_compatibility` emits those and no others. Every other `ACTIVE_FAMILIES` name is `unsupported_active_families` until a later training authorization supplies supervision. This draft does not invent logits for `internet-slang`, `memetic`, `workplace-career`, `politics-civic`, or the rest.

Direct labels already frozen for the weight-backed four stay the only OBSERVED sense-label rule. This spec does not widen them.

## Legacy heads

Historical checkpoints may still contain:

```text
brainrot-aura
kinship-address
political-status
workplace-corp
```

They are compatibility state, not active families. The adapter records them under `legacy_heads` and sets `legacy_remap` to `{}`.

These are not renames:

```text
workplace-corp ≠ workplace-career
political-status ≠ politics-civic
brainrot-aura ≠ memetic
kinship-address ≠ relationship-dating
```

Unknown head strings yield `status: UNSUPPORTED`. Inactive candidate strings on a head also yield `UNSUPPORTED`. The v1 `none` logit is reported as `NOT_A_V2_DECISION` and is dropped from `family_distribution`.

Loading rules:

- read historical tensors, do not write them back
- `historical_artifact_mutated` is false
- do not copy a legacy logit into an active family slot
- do not claim a 19-way trained head
- a v1 response of `none` is not relabeled as v2 `NONE` or v2 `ABSTAIN`; the migration state stays explicit
- BEST is not a v2 checkpoint and is not replaced by a partial adapter

## ABSTAIN

Epistemic. Q1 failed, or Q5 failed, or the argmax family is outside the eligible set. The result's `family` is null. Abstention metrics are coverage, selective accuracy, selective risk, false abstention, and unsafe emission. `ABSTAIN` is not trained as a family and is not semantic `NONE`.

## NONE

Semantic. Q1 passed and the applicability head says no active family applies. Family loss is off. `family` is null. An OBSERVED `none` row supervises this outcome strongly. An INFERRED `none` row supervises it weakly. Neither row teaches the family head a `none` class.

## AMBIGUOUS

Semantic non-uniqueness. Q1 and Q2 passed and the margin, or a future supervised ambiguity head, says the evidence does not pick one family. `family` is null even if an argmax exists. Low family confidence with a wide margin is `ABSTAIN` instead.

Ambiguity gold is not mined from Hyperlex/Jev disagreement, from legacy-head confusion, or from `ai-native` versus `brainrot-aura` on the validation split. Until an explicit surface exists, ambiguity evaluation is unspecified and the learned ambiguity head stays masked. Derived margin is the representation that still lets the policy emit `AMBIGUOUS`.

## Jev role

Jev is a typed probabilistic decision layer. Default `JEV = OFF`. Classification v2 is required to work in that mode. Integration is provider-neutral: the packet names a provider string and does not embed an endpoint, a vendor SDK, or a frozen jevgate prompt.

When a later operator sets `JEV_MODE = SHADOW`, Jev may be asked only these questions, after deterministic eligibility:

| Role | Packet | May affect canonical output |
| --- | --- | --- |
| A. Ambiguity adjudication | `choice` with candidates, probabilities, `abstain_probability` | no |
| B. Abstention / escalation score | `score` with `confidence`, `ambiguity`, `escalation_need` | no |
| C. Family-choice shadow | `choice` compared with the Hyperlex distribution | no |
| D. Review routing | `route` of `accept_automated`, `human_review`, `additional_evidence` | no; the host executes |

A flat choice remains `selected: null`. That is the v2 form of `jev_best_guess = null`. The contract does not argmax a tie into a family.

`jevgate-1` (`src/hyperlex/analysis/jevgate.py`, `--jevgate`, `HYPERLEX_JEVGATE`, tau `0.30333`, model `jev-1.13.0`, frozen prompt sha `0dab5878…`) stays the lexical cascade it already is. This spec does not retune it. `map_legacy_jevgate` records the flag and leaves v2 mode at `OFF` unless the caller separately passes `SHADOW`. `--no-jevgate` forces the legacy cascade off. Neither flag sets `authorizes_v2_gated`. Neither flag writes `canonical_family`.

## Jev non-role

Jev must not be:

```text
ground-truth authority
labeling authority
canonical semantic truth
settlement authority
reserve-construction authority
provenance authority
permission authority
irreversible-action authority
calibration ground truth
```

A packet that carries `canonical_family`, `semantic_family`, `observed_label`, `reserve_gold`, `best`, or `api_key` fails closed with `forbidden_authority_field`. The host does not repair the body.

Production gating is not enabled. `gated_authorized` returns false even if every future precondition is asserted. Those preconditions, all required before a later spec may even consider `JEV_MODE = GATED`, are:

```text
validated provider behavior
probability-schema compliance
measured calibration
known failure modes
latency and cost bounds
exposure-policy compliance
clear fallback
shadow evidence of material value
```

Default remains OFF. A gated mode, if it is ever preregistered, may adjust only named policy inputs and only after deterministic validation. It must not implement `canonical_family = Jev(...)`.

## DecisionPacket

`JevDecisionProvider` returns a `DecisionPacket`. Required fields:

```text
decision_type
candidate_set
probabilities
confidence
provider
model
schema_version
prompt_schema_version
timestamp
input_hash
output_hash
```

`choice` also requires `abstain_probability`. `selected` may be null. Probability-bearing numbers are finite and in `[0, 1]`. Bools are rejected. For `choice`, `sum(probabilities) + abstain_probability` equals 1 within `1e-6`. For `route`, probabilities sum to 1 over the route set. For `score`, the three scores are individually in `[0, 1]` and are not forced to sum to 1.

`output_hash` is SHA-256 of the canonical JSON object without that field (`sort_keys`, no extra whitespace). A mismatch is `output_hash_mismatch`. Out-of-range or non-numeric probabilities are `malformed_probability`. A bad sum is `not_normalized`. A candidate outside the deterministic eligible set is `candidate_outside_eligible`. The implementation records the rejection and leaves the Hyperlex decision in place. It does not clamp, renorm, or drop a key to force a parse.

Provider failure, including unavailable, is `provider_unavailable`. Canonical output stays the deterministic Hyperlex result.

Provenance stored for a real invocation, when one is eventually made outside this draft:

```text
input hash
candidate family set
provider
model
Jev schema version
probability vector
selected choice if any
confidence
reason code
```

That record is evidence about the judgment. It is not semantic provenance and it does not enter `family` or `decision`.

## Exposure

Prohibited surfaces, Jev call count 0:

```text
held_out
evaluation_reserve
settlement
measurement
```

`integrate_jev` on those surfaces discards any supplied packet, sets `rejection = exposure_prohibited`, and does not store `decision_packet_ref`. Reserve construction and settlement stay at zero Jev calls. A future Jev-inclusive system evaluation would need its own preregistration and a reserve isolated from this one. This draft does not create that reserve.

Jev exposure remains a hash fence. Jev does not mint `OBSERVED` labels and does not build reserve gold.

## Shadow mode

`JEV_MODE = SHADOW` runs the judge, stores the packet hash, and compares. It does not change `decision` or `family`. Comparison fields:

```text
family_agreement
hyperlex_abstain_jev_choice
hyperlex_choice_jev_null
adopted = false
```

Aggregate diagnostics a later shadow report may compute, still without changing canon:

```text
agreement rate
family disagreement rate
Hyperlex-abstain / Jev-choice
Hyperlex-choice / Jev-null
ambiguity disagreement
confidence calibration
```

Disagreement is recorded. It is not adopted and it is not ambiguity gold.

## Calibration

Targets: applicability, family confidence, abstention, ambiguity.

Metrics, computed off the packet: ECE, Brier score, reliability curves, margin distributions, coverage versus accuracy, selective risk.

There is no Trutina module in this repository. Trutina is a peer name in `docs/NAMING.md`, not a scorer. This spec does not invent that subsystem and does not treat Jev as the reliability target. Packet Brier stays null under constitution III / G1 / N2 / F7.

## Evaluation

Report each block on its own rows. Do not fold `OBSERVED` and `INFERRED` into one number.

| Block | Metrics | Support |
| --- | --- | --- |
| Applicability | precision, recall, F1 for `NONE` vs `FAMILY_PRESENT` | rows with a semantic target |
| Family | macro-F1, per-family precision, recall, F1, confusion | family examples only. `NONE`, `ABSTAIN`, and `AMBIGUOUS` are not classes in this matrix |
| Abstention | coverage, selective accuracy, selective risk, false abstention rate, unsafe emission rate | emission policy |
| Ambiguity | only after an explicit gold surface exists | disagreement is not that surface |
| Provenance | the same blocks sliced by `OBSERVED` and by `INFERRED` | always separate |

v1 `predicted_none_rate` is not a v2 abstention metric and not a v2 `NONE` metric. A later run that wants either number must define which v2 outcome it counts.

## Migration

Versioned boundary:

```text
hyperlex.classification.v1    layout.FAMILIES softmax, including none
hyperlex.classification.v2    this contract
```

v1 remains the production reference while BEST is the checkpoint above. Adapters:

| From | To | Honest result |
| --- | --- | --- |
| v1 checkpoint tensor | v2 load | `PARTIAL_COMPATIBLE` for the four weight-backed families. Other active names unsupported. File bytes unchanged |
| legacy head | active family | not compatible. `legacy_remap` empty. `UNSUPPORTED` if the caller treats the legacy name as active |
| v1 response `none` | v2 decision | `NOT_A_V2_DECISION`. Do not translate |
| v0.1 inference packet | v2 result | separate schemas. Do not overload `lineage_family` |

`UNSUPPORTED` is a successful refusal. It is not a coerced family.

## Result schema

`hyperlex.classification.v2`:

```text
decision: FAMILY | NONE | ABSTAIN | AMBIGUOUS
family: active family or null
applicability / applicability_score
ambiguity / ambiguity_score
family_distribution          # eligible families only
confidence / family_confidence
provenance_context: OBSERVED | INFERRED | UNKNOWN
stage
brier: null
forecast_eligible: false
jev.mode / invoked / decision_packet_ref / agreement / rejection
```

Raw provider bodies do not appear in those fields. `decision_packet_ref` is the packet `output_hash` or null.

## Invariants

```text
ABSTAIN != NONE
NONE != AMBIGUOUS
AMBIGUOUS != low confidence
OBSERVED / INFERRED != semantic family
Jev judgment != ground truth
Jev judgment != settlement
family classifier does not train NONE as a family
evaluation reserve is independent of Jev exposure
current BEST is not moved by this architecture
```

## Acceptance tests

Executable tests live in `tests/shadow/test_classification_v2.py`. They import the contract only. They do not train, score BEST, or open a socket.

| Test | Proves |
| --- | --- |
| `test_architecture_is_drafted_and_does_not_move_best` | drafted state, GATED unauthorized, BEST reference only |
| `test_decision_ontology_stays_distinct` | ABSTAIN, NONE, AMBIGUOUS, low confidence, and FAMILY take different stages |
| `test_family_loss_is_masked_and_weights_have_no_default` | family mask, weaker INFERRED weights, no default table |
| `test_active_family_adapter_does_not_invent_or_rename` | four emittable families, empty remap, unknown unsupported |
| `test_result_schema_keeps_brier_null` | schema, null Brier, `none` barred from the family distribution |
| `test_jev_disabled_leaves_hyperlex_output_unchanged` | `JEV = OFF` ignores a packet |
| `test_shadow_mode_records_disagreement_without_adoption` | shadow records disagreement and keeps the Hyperlex family |
| `test_jev_null_choice_does_not_force_a_family` | null `selected` does not overwrite |
| `test_malformed_jev_probabilities_fail_closed` | out-of-range, bool, NaN, string, and bad sums do not repair |
| `test_jev_candidate_outside_eligible_set_is_rejected` | legacy candidate cannot enter canon |
| `test_held_out_and_reserve_prohibit_jev_invocation` | held-out, reserve, settlement, and measurement call count 0 |
| `test_provider_unavailable_falls_back_to_hyperlex` | deterministic fallback |
| `test_legacy_jevgate_maps_without_authorizing_gated_mode` | `--jevgate` maps to jevgate-1 and does not enable GATED |
| `test_evidence_floor_is_caller_configured` | no implicit evidence floor |

## Implementation tasks

| # | Task | This draft |
| --- | --- | --- |
| 1 | v2 schemas and interfaces | schemas plus `classification_v2.py` |
| 2 | active-family vocabulary adapter | pure `checkpoint_compatibility`; not wired into a loader |
| 3 | applicability head | not started |
| 4 | family-head mask inside the trainer | mask function only; `loop.py` untouched |
| 5 | ambiguity representation | derived margin only; learned head masked |
| 6 | deterministic decision policy | `final_decision` |
| 7 | provenance-aware loss weights | validator only; no numbers chosen |
| 8 | calibration surface | specified; no new scorer |
| 9 | optional Jev adapter | packet validation; no provider client |
| 10 | Jev shadow mode | `integrate_jev`; default OFF |
| 11 | checkpoint compatibility | read-only adapter; historical files untouched |
| 12 | diagnostics and evaluation tooling | `evaluation_plan` only |

The next implementation action is task 3: add the applicability head beside the existing classify head in the shadow trainer, behind `hyperlex.classification.v2`, without a training run and without moving BEST. Do not open a SELECT id to do that wiring.

## Non-authorization

This specification does not train, does not move BEST, does not reopen SELECT-006 or SELECT-007, does not invent semantic labels from Jev, does not build a reserve with Jev, does not settle with Jev, does not send held-out rows to Jev, does not name a provider inside the canonical schema, does not make Jev mandatory, does not enable production gating, and does not open another experiment queue.
