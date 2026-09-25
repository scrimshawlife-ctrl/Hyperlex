# Selection-surface audit

Published verdict: **NO_RULE_MATCH** (candidate `NO_RULE_MATCH`, reproduce matched).

Eval only. The test split was discarded and not scored. Brier is null.
Test rows discarded: 793.

## Release unbind val

n_rows=221 n_scored=221
provenance={"harvested": 137, "templated": 84}
source={"004": 1, "civilian_template": 32, "dict:moltbook": 24, "dict:moltbook-curated-seed": 6, "live": 158}
sibling={"no_sibling": 27, "sibling": 194}

## Unbind exact

| model | slice | exact | n | wilson95 |
|---|---|---:|---:|---|
| morph65 | all | 0.8371040723981901 | 221 | [0.7827346844803535, 0.8799544867317228] |
| morph65 | harvested | 0.7664233576642335 | 137 | [0.6889031936585825, 0.8294100971241876] |
| morph65 | templated | 0.9523809523809523 | 84 | [0.8838668496724167, 0.9813282531905099] |
| morph65 | sibling | 0.8247422680412371 | 194 | [0.7650858912381933, 0.8717876981048531] |
| morph65 | no_sibling | 0.9259259259259259 | 27 | [0.7663040731697686, 0.9794453459390113] |
| morph78 | all | 0.8642533936651584 | 221 | [0.8128287815559554, 0.9032313296195098] |
| morph78 | harvested | 0.781021897810219 | 137 | [0.7046291889884262, 0.8420848300564137] |
| morph78 | templated | 1.0 | 84 | [0.95626827158534, 1.0] |
| morph78 | sibling | 0.845360824742268 | 194 | [0.7878292837132588, 0.8894807240007747] |
| morph78 | no_sibling | 1.0 | 27 | [0.8754449702581328, 1.0] |
| rc1 | all | 0.8552036199095022 | 221 | [0.8027399103495929, 0.8955298875047426] |
| rc1 | harvested | 0.7664233576642335 | 137 | [0.6889031936585825, 0.8294100971241876] |
| rc1 | templated | 1.0 | 84 | [0.95626827158534, 1.0] |
| rc1 | sibling | 0.8350515463917526 | 194 | [0.7764228722982922, 0.8806689262302478] |
| rc1 | no_sibling | 1.0 | 27 | [0.8754449702581328, 1.0] |

## Controls on all

unbind_copy_token exact=0.8642533936651584 n=221 wilson95=[0.8128287815559554, 0.9032313296195098]
strict_slot_copy exact=0.8597285067873304 token_f1=0.9345991561181435 slot_f1=0.9345991561181435 n=221

## Known selection surfaces

broad_clean: n_scored=51 expected=51 match=True provenance={"harvested": 1, "templated": 50}
force_fair: n_scored=141 expected=164 match=False provenance={"harvested": 86, "templated": 55}
train_val_strict: n_scored=140 expected=140 match=True provenance={"harvested": 85, "templated": 55}

Wilson beside exact and the lenient copy baseline is the row-hit interval. Wilson beside token-F1 and slot-F1 is the micro-recall interval (tp/gold).
A first run stays HOLD. Re-run from a second checkout of the same SHA with `--reproduce` pointing at the first JSON. The candidate is published only when rows match.
