# Uncensored contract 007

Locked 2026-09-09 with the Spark home-box amendment.

## Meaning (normative)

**Uncensored** here means the encoder and heads do not refuse, rewrite, or drop **civilian attested slang** because a chat-safety template would.

That includes vulgar, dialect, tribal, irony, camouflage, sacred-slang, and identity-routing packets that Hyperlex already treats as load-bearing atoms.

It does **not** mean:

- a wrap / jailbreak / ASR generator
- reconstructable restricted payloads
- dropping constitution VII (detector over generator)
- dropping 001 C6 persistence redaction
- a chat model with the safety layer peeled off and sold as Hyperlex

## Required (T0/T1)

1. **Base weights**, not an instruct-chat checkpoint, as the encoder trunk.
2. **No chat template** in infer.py. No system prompt. No assistant turn.
3. **No refusal head**. A forward pass always returns a packet (or omits the analyze block). It does not return `I cannot analyze that`.
4. **Tokenizer**: no safety-remap of civilian slang tokens to UNK / dummy as a filter. Ordinary OOV is fine.
5. **Train on attested civilian atoms** including informal register. Weak LLM slang is still not E2 gold (C20).
6. Hub card says: detect-only, no chat, no refusal on civilian slang, dual-use wall intact.

## Forbidden (still)

- generate / wrap / compose / asr / encode verbs
- restricted how-to fixtures in git
- surface persistence when `restricted_intent_suspected`
- teaching the model to emit attack strings so it can “understand” them
- calling an aligned chat LM and scraping refusals as negatives for “uncensoring”

## Test (E6)

Add to eval gates when U1 lands:

- Dialect / informal / vulgar civilian fixtures produce a valid packet, not an empty refusal.
- Restricted-intent fixtures still redact `surface` and keep `payload_ref`.
- Packet never contains a chat refusal string in lieu of heads.

If E6 dialect fixtures start failing because a safety-tuned trunk was swapped in, that trunk is out of spec.
