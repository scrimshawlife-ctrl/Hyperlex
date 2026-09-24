# Remotes — personal vs org

**OBSERVED:** the canonical train and work remote is
`scrimshawlife-ctrl/Hyperlex` (`main`). Diligence pointer:
[CANONICAL.md](CANONICAL.md). Product naming SoT: [NAMING.md](NAMING.md).

**Company mirror:** `Zero-State-LLC/Hyperlex` exists and may lag. Do not treat
it as the train source of truth. Do not clone it for Spark train or Hub work.
After naming/docs land on personal `main`, sync org only via intentional push
below — do not smash.

## Optional org mirror push

If you maintain the org remote:

```bash
cd Hyperlex
git remote add org git@github.com:Zero-State-LLC/Hyperlex.git
git push org main
git push org --tags
```

Keep one source of truth. Default: personal `main` first, then:

```bash
./scripts/push-org.sh
```

That script refuses if the `org` remote is missing.

## Don't

- Diverge two `main`s
- Train or publish Hub cards from a stale org clone
- Point operators at the org URL as the work remote
