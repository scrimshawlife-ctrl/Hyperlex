# Intent

## Problem

ADVERSARY P1 review found fail-open gaps on org SoT (`feba4b51`): Claude
helper copy is raw `mkdir`+`cp -f`; `init --target claude` overwrites without
backup/smoke; scored settle is API-open; X API base is unsanitized; Chroma
Cloud writes follow auto-loaded creds; doctor has no SoT-cleared marker;
receipt integrity is a 12-char prefix.

## Proposed outcome

One additive fail-closed PR meeting ADVERSARY P1-1…P1-6:

- Claude init + `install.sh --claude` / `--claude-plugin` helpers are
  transactional (symlink refuse, target-keyed backup, staged smoke /
  UNVERIFIED). Unguarded `copy_claude_helpers` is deleted.
- `settle()` / `settle_and_log()` require token or TTY confirm, non-empty
  `authority.ref`, and non-advisory kind for scored TRUE/FALSE. Piped yes
  without token is refused. No score_log append on refuse. Token is not logged.
- X API base allowlist: `api.twitter.com` / `api.x.com`, https only; custom
  only with explicit escape.
- Cloud vector writes require `HYPERLEX_CLOUD_WRITE=1` or TTY
  `--i-understand-cloud-write`. Auto-loaded `.env` keys are not write permission.
- `doctor` emits `CLAUDE_SOT_CLEARED=` from local pin/provenance (not live
  GitHub). Fail when Claude packaging is claimed and uncleared.
- `receipt.integrity` is full sha256; `emit_receipt(..., validate=True)`
  default; `--no-validate` escape; legacy 12-char only with
  `HYPERLEX_RECEIPT_LEGACY_INTEGRITY=1`.

Out of scope: PyPI publish, new bots/services, exploit PoCs, phenomenology,
chromadb CVE upgrade, score_log FS rewrite / signing, SKILL.md contract
rewrite, official Hermes hub submit.

## Affected users / systems

Hermes / Claude install, operator settlement, X ingest, Chroma Cloud promote,
doctor, receipt goldens, CI.

## Constraints / non-goals

- Public MIT mirror: preserve MIT `LICENSE` (do not copy org proprietary `LICENSE` / `LICENSE_POLICY` / org-only SDLC). Org SoT keeps proprietary license.
- Do not invent CLI `SKILL.md` does not already name except flags named in
  this accepted P1 list (`--settle-token`, `--no-validate`,
  `--i-understand-cloud-write`, `--skip-smoke` on init, X custom-base escape).
- Brier only after operator settlement. No auto-settle.
- No live GitHub fetch as sole SoT-cleared path.
- Cheap folds only: http(s) scheme allowlist for LLM/embed base; `contents: read`
  on `.github/workflows/ci.yml`.

## Open questions

None. Acceptance list is the accepted spec (Cloud Agent task).

## Verified / assumed claims

| Claim | Label | Basis |
|---|---|---|
| Org tip `feba4b515cf7856dd0cb85cdc24291caf1330e1b` has Claude helpers via #10 | `OBSERVED` | `git log -1` on main |
| `install.sh` `copy_claude_helpers` is raw `mkdir`+`cp -f` | `OBSERVED` | `install.sh` |
| `settle()` has no token / TTY / authority.ref gate | `OBSERVED` | `src/hyperlex/calibration/settlement.py` |
| X base is unsanitized env string | `OBSERVED` | `src/hyperlex/intake/x_search.py` |
| Cloud write follows creds without write flag | `OBSERVED` | `src/hyperlex/vectordb/chroma.py` |
| `emit_receipt` uses sha256[:12], `validate=False` default | `OBSERVED` | `src/hyperlex/receipt/__init__.py` |
| Public `scrimshawlife-ctrl@c9233c98` may lag post-#10 | `INFERRED` | task statement; not fetched as sole path |
| score_log remains unsigned FS rewrite | `OBSERVED` | residual, out of scope |

## Author / date

- Author: Cloud Agent (accepted task: P1 fail-closed)
- Date: 2026-09-05
