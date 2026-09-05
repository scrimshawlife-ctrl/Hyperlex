# Source identity and upgrades

This distribution is `scrimshawlife-ctrl/Hyperlex`. Source identity is the
`VERSION` file plus `git rev-parse HEAD` recorded at install time. Do not use a
version string alone. Do not pin a commit SHA in this document; the installed
receipt stores the checkout's HEAD when the source is its own repository root.

Before switching sources, stop runtime writers, record current source and
commit, review the destination under `${HERMES_HOME:-$HOME/.hermes}`, compare
contracts, and retain a separate backup of outputs, sessions, and local
customization. Do not install two different contracts with the same skill name
into one profile. A successful compatibility check does not grant
deployment or publication authority.

The bundled LICENSE controls this distribution. No license grant is changed by
these installer fixes; earlier grants and third-party notices remain intact.

The installer validates a fresh stage on the target filesystem before
replacement, then reads back the activated contract, version, and provenance
receipt. Checks use an isolated temporary home. Legacy `out` contents
(including an `out` symlink) survive. Backups are unique, keyed by canonical
destination under the active Hermes home at `backups/hyperlex/<target-hash>/`.
`.install-provenance.json` records source, base commit, dirty status, version,
destination, and skipped checks.

Stop writers during upgrades. The activation path is a two-rename swap
(displace the live target, then publish the stage). Those two renames have an
absent-target window: this is NOT crash-atomic. On a reported recovery failure,
retain the printed recovery directory and backup; do not delete it or retry
blindly. Inspect the exact target and restore from the named backup only after
validating it. No automatic source migration is implied.

## Interrupted installs and stale locks

SIGKILL or power loss can leave `.<target-name>.install-lock` beside the target.
Locks are never automatically reclaimed: age, an empty directory, or a reused
PID cannot prove that no installer is active. To recover:

1. Stop install launchers and runtime writers. Confirm no installer is active on
   this target (including other sessions or hosts sharing the filesystem).
2. Inspect the exact target, sibling `.<skill>-stage-*` recovery directories
   (especially `previous` and `failed-package`), and target-keyed backups.
   Retain all recovery data until the original installation and outputs are
   accounted for. Restore and validate a complete package first if activation
   was interrupted.
3. Only then set `lock` to the exact path printed in the error and run
   `rmdir -- "$lock"`. This removes only an empty lock; never use recursive
   deletion or remove a lock whose owner or activity is uncertain. Keep
   launchers stopped through inspection and removal to avoid races, then retry
   installation.

Backup copies are staged in `.backup-incomplete-*` outside the target's
selectable backup directory and published by rename after copying and writing
the destination record. Hard termination can leave these incomplete staging
trees; never select one for rollback. Inspect them manually after quiescing
writers. Rollback skips legacy partial entries without a valid matching
destination record.

Git is optional. Archive sources, failed Git lookups, and unrelated enclosing
worktrees record unknown Git fields as JSON `null`, never a false clean claim.
A source-root worktree supplies Git provenance. Receipts distinguish
`source_repository_root` from `source_subdirectory` (`.` for an own checkout).
A dirty-status lookup failure remains `null` even in a recognized worktree.
This repository is Hyperlex only; there is no neon-genie or sigil-forge hub
subtree.
