# Label taxonomy proposal — evaluation reserve

**Status:** draft for operator review. Not settled. Not applied.  
**Date:** 2026-09-26  
**Shelf:** held-out stream `hs-20260925T211358Z` (339 rows). No row text in this file.  
**Does not:** change `hyperlexical.layout.FAMILIES`, resize the classify head, call Jev, run `attest-apply`, or admit `EVAL_RESERVE`.

The production head stays the nine-way list in `layout.py`: `betting-sharp`, `crypto-degen`, `ai-native`, `brainrot-aura`, `kinship-address`, `political-status`, `gaming-meta`, `workplace-corp`, `none`. Dataset schema `dataset_row.v0.1` keeps that lineage enum, plus `ytd_leaf`. This proposal is the evaluation-label ontology for the reserve. It becomes live only after an operator accepts the definitions.

## Why the current reserve cannot use the old list

On the 339-row shelf the only rights-cleared non-none labels are `gaming-meta` (99), `betting-sharp` (61), and `crypto-degen` (5). Five production families have no settled label. Macro-F1 over a three-class subset is a narrow score. Adding more rows under those three names does not widen it.

Hint-only rows already name `kinship-address`, `political-status`, `workplace-corp`, `brainrot-aura`, and `ai-native`. Those hints are not labels. They show the queued sheet is broader than the Kaikki topic map, which is allowed to emit only betting, crypto, and gaming.

## Four surfaces

Distinctions that are not a stable semantic region stay off the primary label.

| Surface | Role | Values on this proposal |
|---|---|---|
| `semantic_family` | Primary class. One region per row. | The sixteen names below, `none`, or `LABEL_UNRESOLVED`. |
| `attest` | How the label was settled. Orthogonal to family. | `OBSERVED`, `INFERRED`, `UNLABELLED`. Empty attest stays empty. |
| `register` | How the wording sits in the language. | `slang`, `domain-specific`, `high-register`, `general`. Unset until an operator sets it. |
| `function` | What the phrase is doing, when that is not the family. | `address`, `evaluation`, `intensification`, `reference`, `affiliation`, or unset. |

`OBSERVED` / `INFERRED` stay on `attest`. They do not become families. Tone, certainty, and insider/outsider stay off the primary list. A family name is not combined with an attribute (`gaming-meta-observed-negative-insider` is not a class).

`attest` on this shelf is unchanged: 205 `INFERRED`, 134 `UNLABELLED`, 0 `OBSERVED`. This document does not write the attest column.

## Promotion rule

```text
LABEL_PROMOTE(x) =
    definition_clear
    AND operator_agreement_possible
    AND not_redundant_with_existing_label
    AND sufficient_support_exists
```

`sufficient_support_exists` is `NOT_COMPUTABLE`. No numeric minimum is declared. Until that rule passes, a name is `CANDIDATE_LABEL` and `evaluation.enabled` is false. A single-example class is not an evaluation class.

Nothing in this draft is promoted. The sixteen names are the proposed active set for the operator to accept or cut. Acceptance of a definition is not activation for macro-F1.

## Proposed active set (16 non-none)

`none` remains the abstain class. It is not one of the sixteen.

Each block is a definition the operator can settle without a model. Positive and near-miss lines are illustrations of the region. They are not reserve rows and they are not taken from the stream.

### gaming-meta

- **definition:** Jargon of video games, esports, and gamer communities: mechanics, ranked play, balance, party and lobby talk.
- **include:** Terms whose ordinary sense is a game mechanic, a competitive-play judgment, or a gamer-community formula.
- **exclude:** Athletic sports. Betting lines about sports. A meme that merely mentions a game.
- **near-miss:** A sports-competition term. A general insult with no game sense.
- **parent:** production family of the same name. Kaikki topics `video-games`, `computer-games`, `role-playing-games` already map here.
- **evaluation.enabled:** false.

### betting-sharp

- **definition:** Jargon of sports betting, gambling, and poker: odds, lines, bankroll, handicapping.
- **include:** Terms whose ordinary sense is a wager, a line, a stake, or poker-table talk.
- **exclude:** Ordinary sports commentary with no stake. Crypto trading slang. A game mechanic.
- **near-miss:** `sports-competition`. A single word that is also a normal verb.
- **parent:** production family of the same name. Kaikki topics `gambling` and `poker` already map here.
- **evaluation.enabled:** false.

### crypto-degen

- **definition:** Jargon of cryptocurrency, DeFi, NFTs, and speculative token trading.
- **include:** Terms whose ordinary sense is a chain, a token, a trade, or that community's stake in a position.
- **exclude:** Ordinary finance with no token or chain sense. A meme about money in general.
- **near-miss:** `finance-retail` and `market-structure` (both candidates, not active).
- **parent:** production family of the same name.
- **evaluation.enabled:** false.

### internet-slang

- **definition:** Short-lived or platform-native wording that is slang of general internet speech and is not tied to one trade or hobby.
- **include:** Terms a reader places in internet speech without needing a game, a book, a chart, or a workplace.
- **exclude:** A domain term that happens to be posted online. A meme name whose job is the meme itself (`memetic`). A status claim (`social-status`).
- **near-miss:** `brainrot-aura` rows, which mix this family with `memetic` and `social-status`. They stay unresolved rather than all landing here.
- **evaluation.enabled:** false. Support on this shelf: 0 clean rows.

### memetic

- **definition:** A phrase whose primary job is to circulate as a named meme, copypasta, or recognizable bit.
- **include:** The wording is the meme, or a stable mutation of one.
- **exclude:** Ordinary slang that is not a named bit. A domain term that people joke about.
- **near-miss:** `internet-slang`. Humor as a tone is not this family.
- **evaluation.enabled:** false. Support on this shelf: 0 clean rows.

### social-status

- **definition:** Wording whose primary job is to rank people, scenes, or the self: aura, clout, mid, cooked-as-status, and their kin.
- **include:** The term assigns or withholds standing.
- **exclude:** A game rank that is a mechanic (`gaming-meta`). A political allegiance (`politics-civic`, candidate).
- **near-miss:** `approval-disapproval`, when the phrase judges an act rather than a person's standing.
- **evaluation.enabled:** false. Support on this shelf: 0 clean rows.

### relationship-dating

- **definition:** Jargon of dating, romance, and couple-craft as a social practice.
- **include:** Terms whose ordinary sense is a dating move, a romantic role, or couple-status.
- **exclude:** Kinship and address (`bro`, `sis`, family terms). Those are not this family. They do not map here.
- **near-miss:** Production `kinship-address`. Candidate `identity-affiliation`.
- **evaluation.enabled:** false. Support on this shelf: 0.

### approval-disapproval

- **definition:** A stable region of evaluative slang whose job is to praise, dismiss, or rate a thing.
- **include:** The term is a verdict word, not a domain object.
- **exclude:** The same verdict spoken inside a domain, when the domain is the family and evaluation is only the `function`. A gaming phrase that evaluates a play stays `gaming-meta` with `function: evaluation`.
- **near-miss:** `social-status`. Positive versus negative is an attribute, not two families.
- **evaluation.enabled:** false. Support on this shelf: 0.

### conflict-aggression

- **definition:** Jargon of fights, feuds, call-outs, and competitive hostility that is not a sport, a game, or a bet.
- **include:** The term names a conflict move or a hostile stance.
- **exclude:** Athletic competition. In-game combat vocabulary. Criminal procedure (`crime-illicit`, candidate).
- **near-miss:** `sports-competition`. An insult that is only status (`social-status`).
- **evaluation.enabled:** false. Support on this shelf: 0.

### technology-ai

- **definition:** Jargon of AI, machine learning, software builders, and AI-era coinages.
- **include:** Terms whose ordinary sense is a model, a training run, an agent, an eval, or builder talk.
- **exclude:** Ordinary computing words with no community sense. The weak mapper already refuses bare `en:Computing`.
- **near-miss:** Production `ai-native`, which this name would replace only after operator acceptance. The head is not renamed here.
- **evaluation.enabled:** false. This shelf has 5 hint-only rows, 0 labels.

### work-hustle

- **definition:** Jargon of jobs, offices, careers, and hustle culture.
- **include:** Terms whose ordinary sense is workplace status, management talk, or gig-work craft.
- **exclude:** A hobby called a grind. Crypto or betting talk about "the job."
- **near-miss:** Production `workplace-corp`, the same region under the old name.
- **evaluation.enabled:** false. This shelf has 20 hint-only rows, 0 labels.

### sports-competition

- **definition:** Jargon of athletic sports and sporting competition, with no wager and no video game.
- **include:** Terms whose ordinary sense is a play, a position, or a sporting result.
- **exclude:** Betting lines (`betting-sharp`). Video-game play (`gaming-meta`). Bare `en:Sports` stays unlabeled, matching `weak_tag_family.py`.
- **near-miss:** `betting-sharp`.
- **evaluation.enabled:** false. Support on this shelf: 0.

### music-entertainment

- **definition:** Jargon of music scenes, fandom, and stage entertainment.
- **include:** Terms whose ordinary sense is a scene, a track-craft word, or fandom talk.
- **exclude:** A meme that uses a song title. A fashion term.
- **near-miss:** `memetic`. `fashion-aesthetic`.
- **evaluation.enabled:** false. Support on this shelf: 0.

### fashion-aesthetic

- **definition:** Jargon of dress, look, and aesthetic scenes.
- **include:** Terms whose ordinary sense is a look, a garment-community word, or an aesthetic label.
- **exclude:** Status slang with no look. A costume inside a game.
- **near-miss:** `social-status`.
- **evaluation.enabled:** false. Support on this shelf: 0.

### regional-cultural

- **definition:** Wording whose primary identity is a place, a dialect community, or a local scene, rather than a trade.
- **include:** The term is opaque outside that region or dialect, and the region is the region of meaning.
- **exclude:** A domain term that happens to be used in one city. AAVE or dialect material is not dumped here by default; it stays unresolved until an operator can say the region is the family.
- **near-miss:** `internet-slang`.
- **evaluation.enabled:** false. Support on this shelf: 0.

### spiritual-mystic

- **definition:** Jargon of spiritual, occult, and mystic scenes.
- **include:** Terms whose ordinary sense is a practice, a belief-community word, or a ritual formula in that scene.
- **exclude:** Ordinary metaphor ("manifest" as office talk). A meme about fate.
- **near-miss:** `work-hustle` when the word is motivational rather than mystic.
- **evaluation.enabled:** false. Support on this shelf: 0.

## Candidate labels (not active)

These stay `CANDIDATE_LABEL`. They are not evaluation classes. The broader list in the operator note is the pool; this shelf does not justify promoting them.

| Candidate | Holds | Why it is not active |
|---|---|---|
| `politics-civic` | Production `political-status` (20 hint-only rows). | Not in the sixteen. No settled examples. |
| `identity-affiliation` | Production `kinship-address` (20 hint-only rows). | Address and kinship are not `relationship-dating`. The candidate is the holding pen, not a gold family. |
| `finance-retail` | Nothing on this shelf. | Easy to collapse into `crypto-degen`. |
| `market-structure` | Nothing on this shelf. | Easy to collapse into `crypto-degen` or `betting-sharp`. |
| `sexual-romantic` | Nothing on this shelf. | Overlaps `relationship-dating` once that family has a definition. |
| `substance-party` | Nothing on this shelf. | No cluster on this shelf. |
| `crime-illicit` | Nothing on this shelf. | No cluster on this shelf. |
| `health-fitness` | Nothing on this shelf. | No cluster on this shelf. |

`ytd_leaf` stays a schema enum value for the production dataset. It is not a semantic family in this proposal.

## What was not done

- Jev was not called. The lineage rule was not run. No model scored a row.
- `attest-apply` was not run. The attest column stays empty.
- The ledger was not mutated. `EVAL_RESERVE` stays 0.
- `layout.FAMILIES` was not edited.
- `brainrot-aura` was not split by reading phrases.

## Remap of `hs-20260925T211358Z`

Rules, in order. A hint is never upgraded to a label by this file.

1. Rights-cleared row, `label_source=INFERRED`, label equals hint, label is `gaming-meta`, `betting-sharp`, `crypto-degen`, or `none`: `PROPOSED_REMAP` onto the same `semantic_family`. `attest` stays `INFERRED`. Not reserved.
2. Label and hint disagree: `LABEL_UNRESOLVED`.
3. `UNLABELLED`, including every hint-only family: `LABEL_UNRESOLVED`. A proposed target may be recorded for the operator. It is not a label.
4. Reddit and Know Your Meme rows: `RIGHTS_UNRESOLVED` as well as `LABEL_UNRESOLVED`.

| Old label | Hint | Rows | Remap status | Proposed family | Notes |
|---|---|---|---|---|---|
| gaming-meta | gaming-meta | 98 | `PROPOSED_REMAP` | `gaming-meta` | Rights-clear. One disagreeing row is excluded. |
| betting-sharp | betting-sharp | 61 | `PROPOSED_REMAP` | `betting-sharp` | Rights-clear. |
| crypto-degen | crypto-degen | 5 | `PROPOSED_REMAP` | `crypto-degen` | Rights-clear. Support is thin. Evaluation stays off. |
| none | none | 40 | `PROPOSED_REMAP` | `none` | Encyclopedic prose. `register` may be recorded as `high-register` from `source_type`, not from a model. |
| gaming-meta | betting-sharp | 1 | `LABEL_UNRESOLVED` | — | Label/hint collision. |
| UNLABELLED | gaming-meta | 20 | `LABEL_UNRESOLVED` | — | Hint is not a label. |
| UNLABELLED | betting-sharp | 21 | `LABEL_UNRESOLVED` | — | Hint is not a label. Includes rights-unresolved Reddit rows. |
| UNLABELLED | crypto-degen | 6 | `LABEL_UNRESOLVED` | — | All six are Reddit. Rights unresolved. |
| UNLABELLED | workplace-corp | 20 | `LABEL_UNRESOLVED` | `work-hustle` if the operator accepts the rename | Target is a proposal. |
| UNLABELLED | ai-native | 5 | `LABEL_UNRESOLVED` | `technology-ai` if the operator accepts the rename | Target is a proposal. |
| UNLABELLED | kinship-address | 20 | `LABEL_UNRESOLVED` | candidate `identity-affiliation` | Not `relationship-dating`. |
| UNLABELLED | political-status | 20 | `LABEL_UNRESOLVED` | candidate `politics-civic` | Candidate, not active. |
| UNLABELLED | brainrot-aura | 20 | `LABEL_UNRESOLVED` | — | Spans `internet-slang`, `memetic`, and `social-status`. Not split. |
| UNLABELLED | no hint | 2 | `LABEL_UNRESOLVED` | — | Know Your Meme. Rights unresolved. |

Totals: `PROPOSED_REMAP` 204 (164 non-none, 40 `none`). `LABEL_UNRESOLVED` 135. Admitted to the reserve: 0.

### Coverage of the sixteen

| Family | Proposed remap (not gold, not reserved) | Unresolved hints pointing near it |
|---|---|---|
| gaming-meta | 98 | 20 hint-only, plus 1 collision |
| betting-sharp | 61 | 21 hint-only |
| crypto-degen | 5 | 6 hint-only, rights unresolved |
| work-hustle | 0 | 20 `workplace-corp` hints |
| technology-ai | 0 | 5 `ai-native` hints |
| internet-slang | 0 | inside the 20 `brainrot-aura` bundle |
| memetic | 0 | inside the same bundle |
| social-status | 0 | inside the same bundle |
| relationship-dating | 0 | 0 (kinship was not mapped here) |
| approval-disapproval | 0 | 0 |
| conflict-aggression | 0 | 0 |
| sports-competition | 0 | 0 |
| music-entertainment | 0 | 0 |
| fashion-aesthetic | 0 | 0 |
| regional-cultural | 0 | 0 |
| spiritual-mystic | 0 | 0 |

Eleven of the sixteen have no row on this shelf. The taxonomy is wider than the shelf. That is intentional. Empty families are not filled by invention, and they are not evaluation classes.

## Operator settlement

Taxonomy text is ready for review. Row settlement is not ready.

- Accept, cut, or rewrite the sixteen definitions before any attest.
- Accept or reject the two renames (`workplace-corp` → `work-hustle`, `ai-native` → `technology-ai`) before those hints are eligible.
- Decide whether `politics-civic` and `identity-affiliation` stay candidates.
- Leave `brainrot-aura` unresolved until an operator splits it by hand.
- Then, and only then, `attest-apply`. This file does not authorize that command.

`SELECT-003` stays undrafted. GEN-1 was not created. BEST stays `seed-morph78`.
