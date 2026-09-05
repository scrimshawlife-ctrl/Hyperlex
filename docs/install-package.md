# Install like graft

Graft: `npm i -g @nanonets/graft` then `graft init` writes a thin skill that calls `graft` on PATH.
Hyperlex is the same shape.

```bash
pip install -e ".[dev]"          # or pip install .
hyperlex init                    # Hermes + OpenClaw + Grok skill dirs
hyperlex init --dry-run
hyperlex init --target hermes --target grok
hyperlex uninstall-skill --target hermes
```

`init` writes only `SKILL.md` (marker `<!-- hyperlex-init -->`) under:

- `~/.hermes/skills/hyperlex/`
- `~/.openclaw/skills/hyperlex/`
- `~/.grok/skills/hyperlex/`
- optional `--target claude` → `~/.claude/skills/hyperlex/`

It does **not** rsync `src/` or `scripts/hyperlex.py`. The agent runs `hyperlex …`.

Reload the agent session after init.

Legacy full-tree install remains `bash install.sh` for hosts that still want the fat skill CLI.
