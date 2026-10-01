# HYPERLEX_V6_FAMILY_ONTOLOGY_V1

```json
{
  "ONTOLOGY_LINEAGE_ID": "HYPERLEX_V6_FAMILY_ONTOLOGY_V1",
  "cardinality": {
    "domain_labels": "multi-label (0..n)",
    "exclusive_flat_argmax": false,
    "function_labels": "multi-label (0..n)",
    "mediation_labels": "multi-label (0..1 typical)"
  },
  "deprecated": [
    {
      "action": "DEPRECATE",
      "decidability": "NEEDS_HUMAN_AGREEMENT_EVIDENCE",
      "from": [
        "regional-cultural"
      ],
      "id": "deprecated.regional_variety",
      "reason": "Primarily variety metadata; often CONTEXT_DEPENDENT as family gold."
    },
    {
      "action": "DEPRECATE_AS_EXCLUSIVE",
      "decidability": "NEEDS_HUMAN_AGREEMENT_EVIDENCE",
      "from": [
        "identity-affiliation"
      ],
      "id": "deprecated.identity_affiliation_exclusive",
      "reason": "Identity/affiliation is not a stable exclusive flat family; map to evaluative_stance and/or politics when text-identifiable, else leave for human resettlement."
    }
  ],
  "domains": [
    {
      "from": [
        "gaming-meta"
      ],
      "id": "domain.gaming",
      "identifiability": "TEXT_IDENTIFIABLE",
      "label": "gaming",
      "positive_core": "gameplay / gamer-community evidence"
    },
    {
      "from": [
        "betting-sharp"
      ],
      "id": "domain.gambling",
      "identifiability": "TEXT_IDENTIFIABLE",
      "label": "gambling_betting",
      "positive_core": "wagering-market evidence"
    },
    {
      "from": [
        "crypto-degen"
      ],
      "id": "domain.crypto",
      "identifiability": "TEXT_IDENTIFIABLE",
      "label": "crypto_markets",
      "positive_core": "crypto-asset / chain-market evidence"
    },
    {
      "from": [
        "sports-competition"
      ],
      "id": "domain.sports",
      "identifiability": "TEXT_IDENTIFIABLE",
      "label": "sports",
      "positive_core": "athletic sports evidence"
    },
    {
      "from": [
        "music-entertainment"
      ],
      "id": "domain.entertainment",
      "identifiability": "TEXT_IDENTIFIABLE",
      "label": "entertainment_media",
      "positive_core": "music / film / TV entertainment evidence"
    },
    {
      "from": [
        "fashion-aesthetic"
      ],
      "id": "domain.fashion",
      "identifiability": "TEXT_IDENTIFIABLE",
      "label": "fashion_style",
      "positive_core": "clothing / aesthetic-style evidence"
    },
    {
      "from": [
        "workplace-career"
      ],
      "id": "domain.workplace",
      "identifiability": "TEXT_IDENTIFIABLE",
      "label": "workplace",
      "positive_core": "workplace / career / org evidence"
    },
    {
      "from": [
        "politics-civic"
      ],
      "id": "domain.politics",
      "identifiability": "TEXT_IDENTIFIABLE",
      "label": "politics_civic",
      "positive_core": "political / civic institutional evidence"
    },
    {
      "from": [
        "spiritual-mystic"
      ],
      "id": "domain.spiritual",
      "identifiability": "TEXT_IDENTIFIABLE",
      "label": "spiritual_esoteric",
      "positive_core": "occult / astrology / spiritual practice evidence"
    },
    {
      "children": [
        {
          "from": [
            "ai-native"
          ],
          "id": "domain.technology.ai_discourse",
          "identifiability": "TEXT_IDENTIFIABLE",
          "label": "ai_discourse",
          "positive_core": "AI-agent / LLM / prompt community evidence"
        }
      ],
      "from": [
        "technology-ai"
      ],
      "id": "domain.technology",
      "identifiability": "TEXT_IDENTIFIABLE",
      "label": "technology",
      "positive_core": "computing / software / systems evidence"
    }
  ],
  "functions": [
    {
      "from": [
        "social-evaluation"
      ],
      "id": "function.evaluative_stance",
      "identifiability": "TEXT_IDENTIFIABLE",
      "label": "evaluative_stance",
      "positive_core": "praise / insult / pejoration / prestige judgment"
    },
    {
      "from": [
        "relationship-dating"
      ],
      "id": "function.relational_intimacy",
      "identifiability": "TEXT_IDENTIFIABLE",
      "label": "relational_intimacy",
      "positive_core": "romantic / dating / intimate partnership evidence"
    },
    {
      "from": [
        "conflict-aggression"
      ],
      "id": "function.conflictive_force",
      "identifiability": "TEXT_IDENTIFIABLE",
      "label": "conflictive_force",
      "positive_core": "hostility / violence / combat framing"
    },
    {
      "from": [
        "memetic"
      ],
      "id": "function.memetic_form",
      "identifiability": "TEXT_IDENTIFIABLE",
      "label": "memetic_form",
      "positive_core": "meme format / macro / copypasta / template virality"
    }
  ],
  "mediation": [
    {
      "from": [
        "internet-slang"
      ],
      "id": "mediation.internet_register",
      "identifiability": "MIXED",
      "label": "internet_register",
      "note": "Optional co-label; never exclusive Stage-B decision alone.",
      "positive_core": "internet-mediated informal register / netspeak"
    }
  ],
  "minimum_support_rule": {
    "MIN_DEV_SUPPORT": 8,
    "MIN_REP_SUPPORT": 15,
    "MIN_TRAIN_SUPPORT": 40,
    "applies_to": "active definitive leaves used for learning/eval"
  },
  "rationale": "Geometry (between>within), retrieval non-viability, and 152 review pairs are consistent with overlapping dimensions forced into exclusive buckets. Separating DOMAIN \u00d7 FUNCTION \u00d7 MEDIATION with hierarchy for AI\u2282technology is the smallest structure that preserves useful distinctions without unstable exclusive boundaries. Flat reduction alone cannot express legitimate co-occurrence (e.g., sports+gambling, gaming+conflict, politics+memetic).",
  "semantic_levels": {
    "domain": "aboutness / community topic",
    "function": "pragmatic or relational force",
    "mediation": "optional register/channel marker"
  },
  "structure": "HIERARCHICAL_MULTI_LABEL",
  "structure_code": "D"
}
```
