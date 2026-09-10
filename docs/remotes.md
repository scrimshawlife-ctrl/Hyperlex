# Remotes — personal vs org

**Source of truth:** `scrimshawlife-ctrl/Hyperlex` (`main`).

**Intended org twin:** `Zero-State-LLC/Hyperlex` — advertised on zer0state.com, **not created or not visible** as of 2026-09-09 (API 404). This connector cannot create org repos (`403` needs org admin).

Until the org repo exists, do not treat the org URL as a clone target.

## After an org owner creates `Zero-State-LLC/Hyperlex`

```bash
cd Hyperlex
git remote add org git@github.com:Zero-State-LLC/Hyperlex.git
git push org main
git push org --tags
```

Keep one SoT. Default: personal `main` first, then:

```bash
./scripts/push-org.sh
```

That script refuses if `org` remote is missing.

## Do not

- Diverge two `main`s
- Train or publish Hub cards from a stale org clone
- Point Aaron at the 404 org URL
