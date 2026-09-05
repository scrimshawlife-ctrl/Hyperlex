# Source identity and upgrades

This distribution is `scrimshawlife-ctrl/Hyperlex`, version `0.4.0`, based on commit
`3e66637836f42348b9bad91e6f8cd46781eb71de` before the local audit-fix commit. Record the actual installed commit
with `git rev-parse HEAD` before installation; do not use a version string alone
as a source identity. Root and hub packaging are distribution surfaces, not a
claim that organizational, personal, or legacy embedded variants are identical.
No personal version is deprecated by this change.

Before switching sources, stop runtime writers, record current source/commit,
review the destination under `${HERMES_HOME:-$HOME/.hermes}`, compare contracts,
and retain a separate backup of outputs, sessions, and local customization.
Do not install two different contracts with the same skill name into one profile.
A successful compatibility check does not grant deployment/publication authority.

The bundled LICENSE controls this distribution. No license grant is changed by
these fixes; earlier grants and third-party notices remain intact.

The installer validates a fresh stage on the target filesystem before replacement,
then reads back the activated contract/version/provenance receipt. Checks use an
isolated temporary home. Legacy `out` contents (including an out symlink) survive.
Backups are unique, keyed by canonical destination under the active Hermes home's
`backups/<skill>/<target-hash>/`; `.install-provenance.json` records source, base
commit, dirty status, version, destination, and skipped checks. Stop writers during
upgrades. Two renames have an absent-target window: this is NOT crash-atomic.
On a reported recovery failure, retain the printed recovery directory and backup;
do not delete it or retry blindly. Inspect the exact target and restore from the
named backup only after validating it. No automatic source migration is implied.
