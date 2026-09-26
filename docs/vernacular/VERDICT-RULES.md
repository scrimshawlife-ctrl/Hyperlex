# Vernacular verdict rules — `metrics-rule-v1.4`

Status: in use since 2026-09-25 PT. This page describes, in plain language, how the Vernacular export decides a verdict for
each tracked slang term. The machine-readable Jev question contracts are in [`contracts/`](contracts/).

This page holds rules only. It contains no posts, no author handles, no term example posts, no holdout ids and no database
contents. Any example below is either a term name used to illustrate a ruling, or clearly marked as synthetic.

## 1. The four verdicts

| Verdict | Meaning | Who decides |
|---|---|---|
| **PASS** | Real slang with one coherent meaning, and the evidence shows real, independent, sustained use. | Jev says slang, then the deterministic rule finds at least one evidence path and no guard flag. |
| **OBSERVE** | Real slang, but the evidence is not strong enough yet (or it is a meaningless meme, see §5). Keep watching. | Jev says slang, then the rule finds no evidence path, or a guard flag, or the null-meaning cap applies. |
| **QUARANTINE** | Not a slang term, or the record is unusable: a proper name, a hashtag or tag, only an ordinary non-slang sense, a sentence fragment, or incoherent/polluted meanings. | Jev. Final. |
| **HOLD** | Meaning empty, unknown or unconfirmed; several unrelated senses with none dominant; or Jev is unsure. Abstain and fail closed. | Jev. Final. |

## 2. Two steps: Jev decides, the rule measures

**Step 1: Jev** ([`jev_vote_contract.json`](contracts/jev_vote_contract.json)) answers one question: is this real slang with
one coherent slang meaning? The answer is one of `SLANG_COHERENT`, `SLANG_NULL_MEANING`, `QUARANTINE`, `HOLD`.

- Jev sees the recorded meanings, meaning history, variants and a few sample posts. It does **not** see volume, adoption,
  lifecycle or scores, so popularity cannot bias the slang judgment.
- A top probability below 0.5 becomes HOLD.
- Borderline voting: if the first answer's top probability is between 0.35 and 0.65 (inclusive), two more independent calls
  are made and the majority (at least 2 of 3) wins. No majority means HOLD.
- **Jev decides slang vs QUARANTINE/HOLD. Nothing downstream overrides it.** QUARANTINE and HOLD are final: the rule never
  upgrades them, and a dictionary entry never overrides Jev (a term with a matching dictionary entry that Jev quarantines
  stays QUARANTINE).

**Step 2: the deterministic rule** runs only when Jev says `SLANG_COHERENT` (or `SLANG_NULL_MEANING`, see §5).
A term is **PASS** if at least one evidence path is met **and** no guard flag is raised. Otherwise it is **OBSERVE**.

## 3. Evidence is counted on slang-sense posts only

Each post is labelled by Jev ([`jev_sense_contract.json`](contracts/jev_sense_contract.json)) as using the term in its slang
sense (`SLANG_SENSE`, which includes mentioning or explaining the slang) or as an unrelated same-spelling use (`OTHER_SENSE`:
a name, school, company, ticker, technical term, literal word or another language). Answers below 0.5 are `UNKNOWN` and are
excluded. For a term with an operator definition, posts are labelled against that definition instead (a slang sense not in
the definition counts as `OTHER_SENSE`).

All the author, week, day, community and attestation counts below use **slang-sense posts only**.

## 4. Evidence paths

Every path requires real, independent use. The core minimum is **at least 3 distinct slang-sense authors over at least
2 active weeks**.

| Path | Condition (all on slang-sense posts) | Idea |
|---|---|---|
| **A_BROAD_ADOPTION** | ≥ 8 authors **and** ≥ 3 communities **and** ≥ 2 active weeks | Many people in several communities, more than one week. |
| **B_PERSISTENT_USE** | ≥ 3 authors **and** ≥ 3 active weeks **and** a lifespan of ≥ 14 days | Few but independent users who keep using it for more than two weeks. |
| **C — attested** | ≥ 3 authors **and** ≥ 2 active weeks **and** one attestation source (below) | People explain it (or the operator or a dictionary does), plus minimal independent use. |
| **D_LINEAGE** | ≥ 1 tracked compound relation (child or parent term) **and** ≥ 3 authors **and** ≥ 2 active weeks | A generative term (for example aura → aura farming), plus minimal independent use. |

**Path C attestation sources.** Only one C label is recorded, checked in this order:

1. **`C_ATTESTED`**: ≥ 2 independent people in the corpus explaining the term (definition-style posts or explainer accounts).
2. **`attested_operator`**: otherwise, the operator has defined the term.
3. **`attested_dictionary`**: otherwise, an Urban Dictionary, Green's Dictionary of Slang or Wiktionary sense **matches** the
   term's slang-sense meaning ([`jev_dictionary_contract.json`](contracts/jev_dictionary_contract.json): one MATCH/DIFFERENT
   question per dictionary sense; a sense counts only at MATCH with p ≥ 0.6).

An operator definition or a matching dictionary sense fills **only the "≥ 2 explainers" part** of path C. The ≥ 3 slang-sense
authors, the ≥ 2 active weeks and every guard still apply, and neither changes Jev's answer. Only the matching sense counts:
a different sense of the same spelling (for example "slay" meaning "to kill") does not. An unmatched dictionary hit count
never counts toward path C.

**What is never a path.** Raw volume (number of posts), velocity and search-trend scores are recorded for information but
appear in no path. Repetition alone can never produce PASS.

## 5. Guard flags (any one blocks PASS)

| Flag | Raised when |
|---|---|
| `ONE_AUTHOR_DEPENDENCE` | One author wrote more than half of the slang-sense posts. |
| `BOTLIKE_REPETITION` | Half or more of the posts are identical copies (after removing URLs and handles). |
| `SINGLE_BURST` | Fewer than 2 active days, or 80 % or more of the posts fall on one day. |
| `FIXTURE_EVIDENCE` | Half or more of the evidence is test/fixture data. |
| `DORMANT_OR_UNDATED` | No use in the last 60 days (measured against the newest post in the database), or no dated post. |
| `LOW_SENSE_PURITY` | Fewer than 30 % of the posts use the slang sense **and** fewer than 8 slang-sense authors. |
| `SENSE_UNVERIFIED` | More than half of the posts have no usable sense label, or none do. |
| `NULL_MEANING_CAP` | Jev answered `SLANG_NULL_MEANING` (see below). Always OBSERVE. |

**Meaningless memes are capped at OBSERVE.** Operator ruling 2026-09-25: a real slang term whose point is that it means
nothing (for example "67") is answered `SLANG_NULL_MEANING` by Jev and is always **OBSERVE**, even if an evidence path is met.
The paths are still recorded. A term that merely has a vague, mild or emotional meaning (an intensifier, general approval)
is *not* null-meaning.

## 6. Compounds are mutations

Operator ruling 2026-09-25: when a phrase combines two base terms, it is a **mutation** of those terms, not a separate
adoption and not a member of an unrelated family. Example: "brain rot" and "aura" are terms; "brain rot aura" is a mutation
of the two. Compounds count as mutation/lineage evidence for their parents (path D), not as independent adoption. (An
earlier export folded "brainrot aura" into the `ai-native` family; that was a bug, fixed in Hyperlex PR #123.)

## 7. Meaning: context first, operator as fallback

- The meaning of a term is worked out **from context first**: Jev picks among the recorded glosses (or short meanings quoted
  verbatim from the term's own slang-sense posts) the one the posts support
  ([`jev_meaning_contract.json`](contracts/jev_meaning_contract.json)). Jev never writes a meaning, so nothing is invented.
  A resolved context meaning is `INFERRED`.
- The operator is asked **only when context cannot settle it** (`UNRESOLVED`, and the verdict is not QUARANTINE). A term the
  operator says they don't know is marked `operator_unknown` and is not asked again.
- Precedence of meanings: operator definition (`OBSERVED`) > context (`INFERRED`) > none (`UNRESOLVED`).
- A context meaning is not attestation and never changes a verdict.
- **An operator definition counts as attestation** (`attested_operator`, §4), **but real use is still required**: the posts
  must still show ≥ 3 slang-sense authors over ≥ 2 weeks with no guard flag.

## 8. Fail-closed behaviour

- A Jev error, a missing answer or an out-of-set answer leaves the term's note untouched. No verdict is guessed.
- A slang answer with no metrics row, a missing sense label or a missing dictionary judgment also leaves the note untouched.
- Any vote error in borderline voting fails the term closed; partial vote sets are never used.
- A verdict is a label only and never triggers publishing.
- Any threshold change requires bumping the rule version.

## 9. Version history

| Version | Date (PT) | Change |
|---|---|---|
| metrics-rule-v1 | 2026-09-25 10:39 | Deterministic PASS/OBSERVE rule with paths A–D and guards. |
| v1.1 | 2026-09-25 10:43 | Null-meaning cap (meaningless memes → OBSERVE). |
| v1.2 | 2026-09-25 10:50 | Evidence on slang-sense posts only; `LOW_SENSE_PURITY` and `SENSE_UNVERIFIED` guards; borderline 3-vote majority. |
| v1.3 | 2026-09-25 10:57 | Operator definition satisfies path C's explainer part (`attested_operator`). |
| **v1.4** | 2026-09-25 11:20 | A sense-matched Urban Dictionary / Green's / Wiktionary entry does too (`attested_dictionary`); the unmatched dictionary hit count no longer feeds path C. |

## Contracts in this folder

| File | Contract | Question |
|---|---|---|
| [`contracts/jev_vote_contract.json`](contracts/jev_vote_contract.json) | `rebuilt-v3.2-metrics` | Verdict vote: real slang with one coherent meaning? (with borderline voting) |
| [`contracts/jev_sense_contract.json`](contracts/jev_sense_contract.json) | `rebuilt-sense-v1` | Per post: slang sense or unrelated same-spelling use? |
| [`contracts/jev_meaning_contract.json`](contracts/jev_meaning_contract.json) | `rebuilt-meaning-v2` | Which recorded meaning do the posts support? |
| [`contracts/jev_dictionary_contract.json`](contracts/jev_dictionary_contract.json) | `rebuilt-dictmatch-v1` | Per dictionary sense: same slang sense as the corpus usage? |

Each JSON file is a sanitized published copy: its `_publication` block names the source file and its sha256. The contracts
embed no real posts; the `synthetic_example` blocks are invented placeholders (the made-up term "zorblet" and posts marked
`SYNTHETIC`).
