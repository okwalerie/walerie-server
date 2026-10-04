# Canonical publication scope and deployment ownership

This is a source-publication boundary, not a completed rollout or full recovery certification. GitHub [#9](https://github.com/okwalerie/walerie-server/issues/9) owns canonical infrastructure; [#8](https://github.com/okwalerie/walerie-server/issues/8) owns lifecycle decisions; [#4](https://github.com/okwalerie/walerie-server/issues/4) consumes them for routes; [#3](https://github.com/okwalerie/walerie-server/issues/3) owns recovery contracts; [#10](https://github.com/okwalerie/walerie-server/issues/10) owns Hermes rollout. Publication does not close these issues.

## Included source

- 47 retained Quadlets: 39 containers, four pods, three networks and one build. The capture manifest has 15 active observations, one confirmed paused service and 31 unclassified observations; no retirement inferred from inactivity.
- Lifecycle operations and isolated rollback/dependency/publication-failure regressions; source validation against Waler's installed Podman generator.
- External-disk and graphroot prerequisites for all captured Podman writer types, bounded container retry policy, host mount evidence and non-recursive bootstrap policy.
- Public-safe ingress route declarations, lifecycle status/freshness policy and a metadata-only Hermes-dependent notification helper.
- Default-profile supervised Hermes updater, persistent recovery inhibit, official/manual-runtime obligation guards, idle-sibling refusal and offline tests. Repository policy remains `armed=false`.
- One narrowly scoped Asahi configuration-checkpoint helper and unit; this is not a full laptop or Waler recurring backup.
- Original server notes, disposition matrix and clearly labelled historical roadmap snapshot.

## Single authoritative deployment source

| Canonical source here | Deployed target / owner | Boundary |
|---|---|---|
| `quadlets/*`, `services.json` | `~/.config/containers/systemd/NAME`, named lifecycle operator | `quadlets/` itself is never a generator search path. Review/apply only a named service. Paused/retired definitions remain out of deployed discovery. Manifest changes require review. |
| `units/data-dirs.service` | user unit, named operator | No recursive database ownership repair or bootstrap on absent storage. |
| `scripts/publish-status.py`, `scripts/notify-failure.py`, status/alert units | user units refer to `%h/walerie-server/scripts/*` | The repository checkout is the runtime source for these scripts. No second dotfiles template may deploy the same target. |
| `scripts/service-lifecycle.py` | reviewed CLI entry point to this source | Preserve prior deployed declarations and private transition records; no automatic fleet install. |
| `updates/waler-hermes-update` | `~/.local/libexec/waler-hermes-update` | Reviewed installed copy; compare bytes to canonical source after separately authorized installation. No installation follows from publishing a PR. |
| `updates/maintenance.json` | `/var/home/core/walerie-server/updates/maintenance.json` | The wrapper reads this canonical checkout path directly; review policy changes as operational changes. Keep `armed=false` for this source publication; arming requires separate authorization. |
| `units/waler-backup.timer`, `units/waler-backup.timer.d/schedule.conf` | `~/.config/systemd/user/waler-backup.timer` and its `.d/` drop-in | Schedule only: nightly at 04:00 America/Denver (DST-aware) plus up to 45 min jitter, set by the drop-in over the base unit 03:17 UTC. Installed bytes match this source. `waler-backup.service` and the helpers it runs stay outside this tree (see below). |
| maintenance/status/checkpoint unit files | `~/.config/systemd/user/` | Manual named installation/readback only; no enable/start/restart/daemon-reload performed by this publication. |
| `backups/waler-asahi-checkpoint` | `~/.local/libexec/waler-asahi-checkpoint` | Fixed two-archive checkpoint with private provisioning and retained restore evidence. No blanket backup claim. |
| `host/fstab`, mount observations | root-owned mount configuration | Evidence, not a replacement installer; review exact device and root ownership separately. |
| `ingress/cloudflared-routes.yaml` | root-owned tunnel configuration | Routes only. Merge privately with tunnel identity/credentials; never replace a complete tunnel config with this fragment. Captured `noTLSVerify` is not new TLS-bypass approval. Route/TLS reconciliation belongs to #4. |
| `secrets-required.json` | `~/.config/walerie-server/secrets/*.env` and existing environment-file references | Names only; values provisioned privately, mode 0600. Dotfiles must not publish them. |

Portable shell/editor/agent account assets remain in `okwalerie/dotfiles`. No portable account tree or other Hermes profile is imported here. Local `/var/home/core/.dotfiles` was searched for overlapping server paths/helpers during publication reconciliation; absence of matches is not proof that a remote deployer has converged. Inspect any future dotfiles deployment before enabling it. There is no bulk installer or automatic Git-to-production deployment in this publication.

## Explicit incomplete coverage

The backup timer and its schedule drop-in are canonical here (table above). The installed Waler backup lane still has `waler-backup.service` and these helpers outside this tree: `waler-backup`, `waler-backup-doctor`, `waler-backup-recovery`, `waler-backup-monitor`, `waler-backup-source-guard` and `waler-backup-finalize`, plus private source/exclude/credential provisioning and supervisor policy. They are **not yet canonical here**. The repaired helpers require a separately reviewed port with isolated tests, explicit active/dormant database contracts, readable offline Beads provenance, staging capacity/retention and alert delivery. Do not copy installed scripts indiscriminately, omit mandatory database dumps to pass a backup, or invent proof/escrow coverage. Existing private originals and evidence remain preserved.

Other service managers/app configurations are not exhaustively captured: Frappe/compose and other non-Quadlet applications, Homepage/Gatus private runtime configuration, root tunnel identity, OS staging/report policy, monitoring observer and key escrow remain separate ownership/acceptance work. A captured definition is neither a reproducible local image build nor a data restore contract. No image, application data, generated unit, credential archive or ignored Python bytecode ships.

## Evidence, not current-state assertions

Current issue comments were fetched for #9, #10, #3 and #13 during publication preparation. #10's later comment records prior helper installation while retaining an unknown official receipt outcome (`ok`) and protected-checkout blockers; earlier bodies saying helpers were undeployed are stale. #3's later comment records a successful historical off-host snapshot/sample while retaining recurring-lane gaps. These are attributed records, not fresh runtime checks. No live updater mode, backup/restore, service transition or deployment was run for this publication. Fresh receipt age, installed-byte identity, endpoint health, external notifications and authorization must be re-established for rollout.

## Publication secret policy

Pinned detect-secrets 1.5.0 scans the whole working tree, including untracked source, with online verification disabled; Git internals and generated bytecode are excluded. Tool failure, schema/version drift and candidate findings block publication. Diagnostics retain only file/line/type metadata, never matched bytes or raw scanner errors.

Exactly two inline exceptions in `backups/waler-asahi-checkpoint` are public SHA-256 metadata for the named before/after configuration archives. Both were independently rehashed against the retained private archives before the exception was applied; neither is a credential. Any checksum change requires revalidation of that exact archive. Do not exclude the helper or entropy detector, add broad baselines, or publish archive contents. A clean scanner is defense in depth, not proof of arbitrary secret absence.

## Remaining publication and rollout gates

Independent review must inspect the exact final source tree, including untracked additions and scanner disposition; previous reviews of older hashes do not approve this tree. A parent reviewer can use a staged tree identity to bind approval before commit/push/PR. Do not use `Closes #9`: named rollout, data recovery and operational acceptance remain incomplete. Commit/push/PR require exact remote readback; merge/deployment are separate decisions.
