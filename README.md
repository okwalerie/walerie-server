# Waler server infrastructure

Canonical, reviewable declarations for the Waler Fedora CoreOS/uCore server. Portable shell/editor/agent assets remain in `okwalerie/dotfiles`; server Quadlets, mount prerequisites, lifecycle policy, ingress and maintenance live here. A file must have one authoritative deployment source.

## Publication and rollout boundary

This tree captures source policy, not complete deployment/backup coverage. Read `docs/publication-scope.md` for authoritative target ownership and explicitly missing recurring backup/non-Quadlet coverage. Runtime statements below describe prior captured/reported observations, not a fresh acceptance check. Publishing or checking out this tree must not activate paused services, arm maintenance or apply root mount/tunnel configuration.

## Layout

- `quadlets/`: all captured server definitions, including definitions preserved for paused services. This directory is **not** a Quadlet search path.
- `services.json`: lifecycle inventory. Captured inactive services are provisional pending classification, not automatically retired or restarted.
- `secrets-required.json`: generated private environment file names, never values.
- `host/`: observed root-owned mount configuration; not automatically applied.
- `ingress/`: public-safe route declarations; private tunnel identity/credential provisioning is separate.
- `units/`: directory bootstrap and lifecycle status publisher.
- `scripts/`: targeted lifecycle operations, validation and status publishing.
- `updates/`: supervised update policy and systemd units.
- `backups/`: scoped Asahi configuration checkpoint only; the recurring Waler backup/recovery lane is not yet canonically ported (see `docs/publication-scope.md`).
- `docs/`: rollout, recovery and ownership boundaries.

## Lifecycle

- **active**: expected to run; explicit resume/deployment is required.
- **paused**: stopped and masked, original deployment saved privately, canonical definition and data retained.
- **retired**: same non-destructive runtime protection, plus explicit retirement intent. Routes and backup retention must be separately reviewed. No automatic data deletion.

```sh
python3 scripts/service-lifecycle.py lofsite paused --reason 'Missing local image; awaiting recovery'
# Inspect the dry-run, then add --apply to execute the named transition.
python3 scripts/service-lifecycle.py lofsite active --reason 'Image rebuilt and restoration reviewed'
```

Do not resume a service merely because its files exist. Check its image, bind-mounted data, dependencies, private environment files, ingress and backup contract first. Generated network/pod/build units are inventory entries too; operate on dependencies deliberately. Lifecycle tooling does not promise to restore deleted data or rebuild missing images. It does not automatically remove root-owned Cloudflare routes.

`services.json` may also contain **unclassified** observations. That is not a lifecycle decision and must never be used to skip required database backups or silently start stopped dependencies. Inactive build/oneshot units are not automatically paused services.

`lofsite` has been explicitly paused: its local Quadlet was removed from generator discovery and its unit persistently masked. The definition is retained here. No image or data was deleted.

## Validation

On Waler (matching installed Podman generator):

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
PYTHONDONTWRITEBYTECODE=1 python3 updates/test_hermes_update.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check-secrets.py
systemd-analyze --user verify units/*.service units/*.timer updates/*.service updates/*.timer
```

The publication secret gate uses pinned Yelp detect-secrets 1.5.0 over the whole working tree (including untracked source), with candidate online verification disabled and metadata-only diagnostics. It is defense in depth, not proof that arbitrary credentials cannot exist. Review any candidate privately; do not add broad baseline exemptions.

The validator requires every manifest entry to map to a source definition and generated service, prohibits inline environment assignments, and checks fail-closed storage policy. It does not prove application-level health.

## Secrets and ownership

Captured inline `Environment=` values are provisioned privately under `~/.config/walerie-server/secrets/*.env`, mode 0600, outside Git. Existing `EnvironmentFile=` references remain required. Extracted overrides are last to preserve precedence. Never commit environment contents, credential stores, backup passwords, Syncthing API keys, tunnel credential files, or app databases. Restore these through the encrypted backup/secret provisioning contract.

Private originals and transition rollback copies live under `~/.local/state/walerie-server`, mode-restricted. Public templates are not by themselves a complete disaster-recovery backup.

## Live visibility

[Lifecycle and storage status](https://gallery.waler.ie/dashboard/server-lifecycle.html) is linked from Homepage and refreshed every five minutes. JSON contains only allowlisted service names, expected/observed unit state, masks, restart counts and mount booleans. Existing Homepage application health checks are preserved.

## Incremental rollout

The initial capture does not bulk-redeploy containers. Canonical templates add external-disk/graphroot mount checks and bounded retry policy. Apply only named services after backup and dependency checks; verify their generated units and actual endpoints. See `docs/rollout.md`.
