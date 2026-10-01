# HYPERLEX_V6_OPERATING_DISTRIBUTION_V1

```json
{
  "OPERATING_DISTRIBUTION_ID": "HYPERLEX_V6_OPERATING_DISTRIBUTION_V1",
  "active_family_vocabulary": [
    "gaming-meta",
    "betting-sharp",
    "crypto-degen",
    "internet-slang",
    "memetic",
    "social-evaluation",
    "relationship-dating",
    "conflict-aggression",
    "technology-ai",
    "workplace-career",
    "sports-competition",
    "music-entertainment",
    "fashion-aesthetic",
    "regional-cultural",
    "spiritual-mystic",
    "identity-affiliation",
    "politics-civic",
    "ai-native"
  ],
  "derived_from": [
    "specs/007-hyperlexical-model/classification-architecture-v3.md",
    "HYPERLEX_STAGE_A_GOLD_IDENTIFIABILITY_CONTRACT_V1",
    "specs/007-hyperlexical-model/classification-v3-evaluation.md",
    "V5 qualification failure system review (negative evidence)"
  ],
  "expected_ambiguity": {
    "exclude_hidden_metadata_uncertainty": true,
    "include_genuine_textual_uncertainty": true,
    "role": "PRODUCT_EXPECTED"
  },
  "expected_domain_irrelevant_traffic": {
    "include_when_admissible": true,
    "role": "PRODUCT_EXPECTED",
    "v5_status": "NOT_ESTABLISHED"
  },
  "expected_domain_mix": {
    "active_family_domains": [
      "gaming-meta",
      "betting-sharp",
      "crypto-degen",
      "internet-slang",
      "memetic",
      "social-evaluation",
      "relationship-dating",
      "conflict-aggression",
      "technology-ai",
      "workplace-career",
      "sports-competition",
      "music-entertainment",
      "fashion-aesthetic",
      "regional-cultural",
      "spiritual-mystic",
      "identity-affiliation",
      "politics-civic",
      "ai-native"
    ],
    "domain_irrelevant": [
      "infrastructure lists",
      "calendar/year pages",
      "generic geographic inventories"
    ],
    "ordinary_no_relation_domains": [
      "mycology",
      "entomology",
      "oceanography",
      "paleontology",
      "cartography",
      "numismatics",
      "philately",
      "archaeology",
      "hydrology",
      "mineralogy",
      "botany",
      "chemistry"
    ],
    "role": "PRODUCT_EXPECTED"
  },
  "expected_family_mix": {
    "also_report_macro_family_metrics": true,
    "bounded_train_max_share": 0.15,
    "forbid_unjustified_ai_native_index_domination": true,
    "historical_failure_example": "ai-native \u2248 42.6% of V5 Stage-B index",
    "representative_validation_uses_natural_prevalence": true,
    "role": "PRODUCT_EXPECTED"
  },
  "expected_text_lengths": {
    "longer_prose_chars": ">160",
    "medium_chars": "40-160",
    "product_mix_note": "Operating traffic mixes short slang atoms, dictionary-like glosses, and conversational/declarative prose; no single band dominates.",
    "role": "PRODUCT_EXPECTED",
    "short_atom_chars": "<40"
  },
  "gold_identifiability_contract": "HYPERLEX_STAGE_A_GOLD_IDENTIFIABILITY_CONTRACT_V1",
  "model_input": [
    "text"
  ],
  "natural_source_types": {
    "diagnostic_only": [
      "matched positive/negative contrast pairs",
      "constructed lookalike batteries",
      "synthetic templates"
    ],
    "product_expected": [
      "naturally occurring slang/meme/domain mentions",
      "conversational fragments",
      "declarative prose with lexical evidence",
      "dictionary-like definitions when self-contained in text"
    ],
    "research_useful": [
      "wiktionary sense lines with explicit English labels",
      "encyclopedia ordinary-domain negatives"
    ]
  },
  "observed_vs_inferred": {
    "qualification_target_observed_min": 0.5,
    "representative_validation_target_observed_min": 0.5,
    "role": "PRODUCT_EXPECTED",
    "train_may_include_inferred": true
  },
  "relation_prevalence": {
    "note": "Operating traffic is majority NO_EVIDENCE / non-entry relative to active-family evidence; PRESENT is the minority retrieval-trigger class.",
    "representative_validation_should_not_force_50_50": true,
    "role": "PRODUCT_EXPECTED"
  },
  "schema": "hyperlex.classification.v6.operating_distribution.v1",
  "short_form_vs_prose": {
    "avoid_overfit_to_matched_definition_pairs": true,
    "include_longer_prose": true,
    "include_medium": true,
    "include_short": true,
    "role": "PRODUCT_EXPECTED"
  },
  "text_registers": {
    "conversational": "PRODUCT_EXPECTED",
    "declarative": "PRODUCT_EXPECTED",
    "dictionary_like": "RESEARCH_USEFUL"
  },
  "v5_negative_lessons": {
    "do_not_dominate_with_paired_contrasts": true,
    "do_not_tune_floors_only_on_matched_dev_surface": true,
    "do_not_use_inferred_template_buckets_as_operating_proxy": true,
    "qualification_is_hard_but_valid_not_pathological": true
  }
}
```
