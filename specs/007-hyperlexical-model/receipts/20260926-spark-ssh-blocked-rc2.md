# Blocker — Spark SSH key missing (2026-09-26)

**Authority:** Danny `continue training according to our updated contents`.  
**Lane:** Spec 007 rc2 prep. No fake local train.

## Probes

| probe | result |
|-------|--------|
| `https://ssh.zer0state.com` | HTTP **200** (Access front door up) |
| `cloudflared access ssh --hostname ssh.zer0state.com` | reaches sshd |
| `ssh spark` / `morpheus@ssh.zer0state.com` | **Permission denied (publickey,password)** — no private key in this Cloud Agent |
| `https://qwen.zer0state.com/v1/models` | HTTP **502** |
| LAN `192.168.12.202` | resolves to AWS internal host; ping loss |
| self-hosted Cursor workers | none connected |

## State

- BEST remains **`seed-morph78`**
- rc2 env + pre-reg + runbook landed in-repo (await Spark host)
- Do **not** invent weights or score spent rc1 holdout

## Unblock

Danny pointed secrets at Cloud Agent `bc-3b73859e-fb9d-42ed-9bff-c651eb3f41af`. From this New Project temp-repo run (`bc-2d049d65-…`):

| probe | result |
|-------|--------|
| `cursor-cloud` `batch-fetch-details` on `bc-3b73859e-…` | **not found or not accessible** (different repo / env scope) |
| This run `CLOUD_AGENT_ALL_SECRET_NAMES` | `GITHUB_TOKEN` only |
| Linked Cursor environment | **none** |

**Preferred:** continue on [bc-3b73859e](https://cursor.com/agents/bc-3b73859e-fb9d-42ed-9bff-c651eb3f41af) (or a new agent on Hyperlex using that same Environment).

**Alternate:** add agent secret `SPARK_SSH_PRIVATE_KEY` (OpenSSH PEM for `morpheus`) to this run, then:

1. Write key → `~/.ssh/id_spark` (mode 600), add `IdentityFile` to `Host spark`
2. `ssh spark 'hostname'` → `spark-bf46`
3. Follow `specs/007-hyperlexical-model/SPARK-RC2-RUN.md` steps 1→5
