# Source identity and upgrades

This distribution is `scrimshawlife-ctrl/Hyperlex`, version from `VERSION`. Record the actual installed commit
with `git rev-parse HEAD` before installation; do not use a version string alone
as a source identity.

Before switching sources, stop runtime writers, record current source/commit,
review the destination under `${HERMES_HOME:-$HOME/.hermes}`, compare contracts,
and retain a separate backup of outputs, sessions, and local customization.
Do not install two different contracts with the same skill name into one profile.

The installer validates a fresh stage on the target filesystem before replacement,
then reads back the activated contract/version/provenance receipt. Checks use an
isolated temporary home. Legacy `out` contents survive. Backups are unique, keyed
by destination under the active Hermes home `backups/hyperlex/<target-hash>/`.
Stop writers during upgrades. Two renames have an absent-target window: this is
NOT crash-atomic.

On a reported recovery failure, retain the printed recovery directory and backup.
Do not delete it or retry blindly.

## Interrupted installs and stale locks

SIGKILL or power loss can leave `.<target-name>.install-lock` beside the target.
Locks are never automatically reclaimed.

1. Stop install launchers and runtime writers.
2. Inspect the target, sibling stage/recovery directories, and backups.
3. Only then `rmdir -- "$lock"` on the exact empty lock printed in the error.
