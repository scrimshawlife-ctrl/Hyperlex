# Classification v4 — balanced fresh reserve acquisition

```text
HYPERLEX_CLASSIFICATION_V4_BALANCED_RESERVE_ACQUIRE_V1 = ACQUIRE_READY
parent = HYPERLEX_CLASSIFICATION_V3_EVIDENCE_GATE (SETTLED_FAIL)
BEST = UNCHANGED
spent_v2_reserve_reuse = false
spent_v3_reserve_reuse = false
train = false
score_reserve = false
recalibrate = false
n = 176
n_none = 48
n_present = 128
n_distinct_active_families = 16
max_single_family_share_of_present = 0.0625
rows_sha256 = dd224047b331cd13b5a6893519907f9998620a482b0d17f29b3444b46794eb82
receipt_sha256 = 1998f409f5350bb296bd6a84e2be23411c0986177f7b4b1ca53b5b08b1bae9f5
```

Opened after v3 `RESERVE_FAIL` on a skewed AVAILABLE scoop (internet-slang 97 /
none 8 / memetic 4). Remaining fresh AVAILABLE classify identities in the
forward hub after spent-v3 exclusion: **0**. Another scoop is impossible.
A later evidence-gate climb needs a **balanced** Wiktionary acquire first.

## Failure mode being remediated

| Failure | v3 reserve |
|---|---|
| false_evidence_entry_rate_on_none | 0.25 on n_none=8 |
| family_emission_precision | 0.0 |
| composition | internet-slang dominated; none poverty |

Do not retune Stage A/B thresholds against the spent v3 reserve. Do not move BEST.

## Preregistered balance floors (before fetch)

```text
min_n >= 120
min_none >= 40
min_present >= 80
min_distinct_active_families >= 12
min_per_covered_family >= 3
max_single_family_share_of_present <= 0.20
```

Discovery caps (also frozen before fetch):

```text
DISCOVERY_PER_FAMILY = 8
DISCOVERY_NONE = 48
```

Floors are not fitted from spent v3 metrics. If unmet → `ACQUIRE_QUOTA_UNFILLED`
and continue acquire under the same floors. Do not relax floors.

## Permanent exclusions

| Pin | sha256 / value |
|---|---|
| spent v2 reserve rows | `8c527644…416ed36` |
| spent v3 reserve rows | `abb8bf22…9d39b937` |
| spent v3 manifest | `4a13d7a7…abc2ef5` |
| spent v3 eval receipt | `61daa473…0fd914ec` |
| v3 evidence surface | `7339c044…0d2d3a` |
| BEST | `9fba0f66…bbd97f6` |

Also exclude every ledger identity already `TRAIN_CONSUMED`, `EVAL_RESERVE`,
`EVAL_BOUND`, `EVAL_SPENT`, or `EVAL_ABANDONED`.

## Source recipe

```text
source_family = wiktionary_labeled_sense
rights = CC-BY-SA
provenance = MediaWiki action=query prop=revisions rvprop=ids|timestamp|sha1|content
class = OBSERVED when exactly one authorized sense-label family matches
```

NONE / `HARD_NONE` candidates require an ordinary-domain sense label from the
frozen `NONE_SENSE_LABELS` set (botany, chemistry, …) and no active-family hit.

Forward 18-family ontology (`HLX_V2_FORWARD_ONTOLOGY=1`). `honorific` /
`derogatory` / `endearing` map to `social-evaluation`.

## Dispositions

| Disposition | Meaning |
|---|---|
| `ACQUIRE_READY` | floors met; freeze acquire rows as the fresh promotion-reserve pool |
| `ACQUIRE_QUOTA_UNFILLED` | keep discovering under frozen floors |
| `ACQUIRE_INVALID` | isolation/provenance/duplicate failure |

## Explicit non-goals (this pass)

```text
do not train Stage A/B
do not score spent v2 or spent v3 again
do not retune thresholds
do not move BEST
do not open a new evidence-gate train until ACQUIRE_READY and a separate climb auth
```

## Climb result (2026-09-30)

Authorized one-shot score under frozen Stage A/B → `RESERVE_FAIL`
(false_entry=0.4167, emission=0.4545). See `classification-v4-final-settlement.md`.
Do not retune against this reserve.

## Authorization ladder

```text
v3 SETTLED_FAIL + STOP preserved
  -> mark spent v3 identities evaluation_spent
  -> PREREGISTER balance floors / sense-label maps / exclusion pins
  -> fetch Wiktionary under discovery caps
  -> ACQUIRE_READY | ACQUIRE_QUOTA_UNFILLED | ACQUIRE_INVALID
  -> (later, separate auth) evidence-gate climb + one-shot score of sealed acquire
```
