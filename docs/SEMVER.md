# Semantic Versioning for Hyperlex

We follow SemVer 2.0 with these additions:

- MAJOR: Breaking changes to public API or JSON schema.
- MINOR: New analysis modules, new ingest sources, new receipt fields (backward compatible).
- PATCH: Bug fixes, improved fallbacks, documentation.

All releases must update this specs repo + implementation in lockstep.

Use scripts/bump_version.py (to be added) modeled on Orchestra.