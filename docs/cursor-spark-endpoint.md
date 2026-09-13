# Cursor ↔ Spark (Qwen) endpoint

Hermes already talks to the operator Spark OpenAI-compatible gateway.
This note is the **local Cursor Desktop** wiring. Cloud Agents do not
read your Mac `~/.cursor/settings.json`.

## Endpoint

| Field | Value |
|-------|--------|
| Base URL | `https://qwen.zer0state.com/v1` |
| Model id | `/model` |
| Auth | Bearer API key (Hermes / Spark; **not** in git) |

Probe (should be `200` with a real key; `401` without):

```bash
curl -sS https://qwen.zer0state.com/v1/models \
  -H "Authorization: Bearer $SPARK_OPENAI_API_KEY"
```

Or: `bash scripts/spark/probe_qwen_endpoint.sh`

## Cursor Desktop (UI — preferred)

1. Cursor Settings → **Models**
2. Enable **OpenAI API Key** → paste full Spark key
3. Enable **Override OpenAI Base URL** → `https://qwen.zer0state.com/v1`
4. **Add model** → `/model`
5. Verify. If TLS/connect errors: Network → **HTTP Compatibility Mode → HTTP/1.1**

Do **not** put the key in the Hyperlex repo.

## Cursor Desktop (`settings.json` — optional)

Exact key names vary by Cursor build. Prefer the Models UI above.
If you edit JSON, keep the key out of shared/dotfiles sync.

Cloud Agent / Hermes scripts should use env instead:

```bash
export OPENAI_BASE_URL=https://qwen.zer0state.com/v1
export OPENAI_API_KEY="$SPARK_OPENAI_API_KEY"   # from secret store / Hermes
export OPENAI_MODEL=/model
```

## Caveats

- Override Base URL is global for OpenAI-format traffic in Desktop.
- Agent mode may send Responses-API shaped bodies; Ask mode is a safer
  first check against a Chat Completions-only Spark proxy.
- This Cloud Agent session cannot flip your local Desktop model picker.
  Add `SPARK_OPENAI_API_KEY` as an environment secret if you want the
  agent VM to call the same gateway for scripts.
