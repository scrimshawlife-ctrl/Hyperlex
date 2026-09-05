# OWASP / ATLAS mapping — Spec 001

Hyperlex mutation grammar is a **sociolinguistic instrumentation layer**. It is not a WAF, not a guardrail product, and not a red-team harness.

Canonical list referenced: **OWASP GenAI LLM Top 10 2026** (published 2026-08-04). Historical 2025 ids are noted where useful. MITRE ATLAS: AML.T0054 LLM Jailbreak.

## Coverage matrix

| Framework entry | Relevance to slang mutation | What 001 does | What 001 refuses |
|---|---|---|---|
| LLM01:2026 Prompt Injection | Register, dialect, game-encode, frame wraps are *linguistic* injection variants: they change how the model binds intent without a literal “ignore previous instructions.” Direct and indirect injection both travel on mutated surfaces. | Detect operator stacks on attested text. Tag REGISTER_SHIFT / FRAME_WRAP / GAME_ENCODE / CODE_SWITCH when parsers exist. | No payload generation. No bypass recipes. |
| LLM02:2026 Sensitive Information Disclosure | Cant and in-group slang can smuggle sensitive topics past keyword DLP. | SUBSTITUTE + recovered_lemma (civilian tables). Restricted flag redacts stored surface. | No attempt to recover secrets from model output. |
| LLM03:2026 Excessive Agency | A high watch_score must not become an autonomous action. | C10: advisory only. No tool fire from trace. | No agent loop. |
| LLM04:2026 Supply Chain | Machine-generated slang / poisoned slang tables could enter LINEAGE_REGISTRY or fixtures. | `machine_dialect` tag. Fixtures are reviewed civilian lists. | No unattended registry promote. |
| LLM05:2026 Data and Model Poisoning | Narrow harmful finetunes and slang-poisoned corpora are out of Hyperlex runtime. | Provenance labels on packets. | No training-set construction. |
| LLM06:2026 Unbounded Consumption | Language-game / run-on surfaces can inflate tokens. | Optional `layers_touched` includes L4 when present. No decoder bomb tests in-repo. | No stress-generation of long game-encoded strings. |
| LLM07:2026 Misinformation | Irony and frame wraps change apparent claim force. | `irony_flag`, FRAME_WRAP distinct from REGISTER_SHIFT. | No truth scoring of world claims. |
| LLM08:2026 Hidden Context Exposure | Not a slang problem per se. | None. | Out of scope. |
| LLM09:2026 Vector and Embedding Weaknesses | Informal-register subspaces and slang near-duplicates can evade embedding filters. | Future: register feature. v0.1 heuristic only. | No embedding inversion. |
| LLM10:2026 Improper Output Handling | If a host pipes `mutation_trace` or `mutation_prediction` into a tool, that is the host's LLM10. | Packet is data. Hosts must treat it as untrusted structured output. | Hyperlex does not execute trace fields. |
| ATLAS AML.T0054 Jailbreak | Style, encoding, persona, linguistic variation are documented jailbreak techniques. | Cite as threat *class*. Instrument surface operators. | No jailbreak success metric, no ASR leaderboard in this package. |

## 2025 crosswalk (for readers on the prior list)
LLM01 Prompt Injection stays the primary map. 2025 LLM05 Improper Output Handling ≈ 2026 LLM10. 2025 LLM06 Excessive Agency ≈ 2026 LLM03. Do not mix year ids in receipts; store `owasp_llm_top10_year: 2026` if a host adds a mapping field later (non-normative on v0.1 packet).

## Honest limitation
Keyword and embedding filters fail on productive morphology and register. This spec measures that failure *mode* on cultural text. It does not claim to close LLM01.
