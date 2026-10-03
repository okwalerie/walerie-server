# Deployment, mount ordering, and recovery

## Current storage contract

Waler mounts a Hetzner external ext4 volume at `/mnt/service-data` (canonical `/var/mnt/service-data`). Rootless Podman graphroot is a separate bind mount of `/mnt/service-data/podman-storage` onto `~/.local/share/containers/storage`.

`host/fstab` is captured evidence, including the persistent mount and bind dependency. `host/podman-storage-mount-observed.txt` records the generated system unit and root-owned ordering drop-in. These are not portable defaults: review disk identity, swap path and mountpoints for a new machine. Do not blindly replace a machine's entire fstab.

Root systemd mounts the volume and graphroot; the user manager runs rootless containers. User-unit ordering alone cannot mount a root-owned disk. Canonical container definitions therefore combine `RequiresMountsFor` with explicit `mountpoint -q` pre-start checks on both the volume and graphroot. Missing storage causes failure rather than creating fresh data on the root disk. The failure is bounded (five attempts per five minutes, restart delay at least 30 seconds).

`units/data-dirs.service` creates stable roots, not a license to recursively chown app-owned databases. Its canonical version removes the old recursive Supermemory ownership change. Do not rerun bootstrap against mapped UID data without review.

## Before named deployment/resume

1. Confirm a fresh verified off-host backup and retain the previous unit privately.
2. Check `mountpoint -q /mnt/service-data` and `mountpoint -q ~/.local/share/containers/storage`.
3. Check the named image exists or has an approved pinned pull/build path; local images cannot be recovered by pulling `localhost`.
4. Verify actual old application state exists under its bind paths. Empty directories may bootstrap a new instance.
5. Provision required private environment files, preserving mode 0600. Check SELinux labels and `:Z`/`:z` policy.
6. Inspect dependencies, routes and any stop hooks before a restart.
7. Dry-run `scripts/service-lifecycle.py NAME active --reason ...`; only then explicitly apply that named transition.
8. Read back the unit, check application health and external endpoint, regenerate lifecycle status. Commit manifest changes after review.

No blanket container auto-updates are enabled. Database version changes and localhost-built images need service-specific contracts.

## Pause and retire

The targeted tool saves the live Quadlet and manifest under a private timestamped transition directory, stops the unit, removes its Quadlet from deployed discovery, persistently masks it, verifies inactive/masked state, then records the manifest transition. Canonical definitions and data remain intact. Existing stop hooks run; review their ingress implications. A failed apply reports its rollback directory; do not claim the transition succeeded or blindly retry.

Retirement requires an explicit reason. It does **not** delete data, forget backup snapshots or remove root-owned routes. Reconcile dependency and backup expectations separately: a retired database may need offline retained-data backups instead of a mandatory live SQL dump, while a required active database failure must still fail loudly.

For an explicit resume the tool requires private environment files, mount readback, local-image availability, unmasking and a named service start. An already-running unit requires **`--redeploy`**, which performs a named restart rather than silently accepting a no-op start. Dry-runs show direct dependency/consumer names; activation of stopped dependencies or stopping active consumers requires explicit **`--allow-dependencies`** after review. Indirect effects still need operator review; the tool never automatically unmasks a dependency fleet.

The desired direct activation model is compiled afresh by the installed Quadlet generator (`-user -dryrun`) against the canonical tree, without reloading or writing the live manager. The planner and validator share this one compiler/model; no handwritten Pod/Network/Image reference mapping or old manager activation graph is used. Generated `[Unit]` `Requires`, `Wants`, `BindsTo`, `Upholds` and `[Service]` `Sockets` are reviewed, including non-service unit names and generator-added dependencies (network readiness helpers and pod member Wants, for example). The manager supplies current states and direct stop-bound consumers only. Missing/partial generation, ambiguous dependency syntax, continuations, conditional activation/stop directives and live unit drop-ins fail closed rather than accepting an incomplete activation plan. Ordering-only `After`/`Before`, `Requisite` and `PartOf` do not themselves activate dependencies. Path-derived mount requirements remain under the separate root mount/storage contract above; systemd default/implicit dependencies, external unit configuration, hooks and transitive effects still require operator review. This is not a certification of the full effective systemd transaction graph or permission to bootstrap a cold database.

Every apply is locked and has a private pre-mutation transition record with prior mask/runtime/source-presence evidence. Authorized activation clears both persistent and runtime masks on the named unit only. On failure the tool independently attempts to stop the unit, restore source/manifest and restore the prior **effective** persistent/runtime/unmasked policy, then reads back source, manifest, inactive state and mask. An inconsistent paused/retired but unmasked declaration is recovered protectively persistently masked. Hidden simultaneous mask-layer topology is not preserved. Recovery/evidence publication errors invalidate `recovery_verified`; corrective audit publication is bounded and cannot erase an earlier append or overcome permanent writer failure. It never auto-starts potentially upgraded database data. Inspect recovery errors in the private record; unit rollback does not undo application data/schema changes.

## Visibility

`waler-infra-status.timer` publishes public-safe lifecycle/mount fields every five minutes; no configuration values or credentials are exposed. Unclassified entries are observations, not pause/retirement authorization or permission to skip backups. The page warns after twelve minutes of stale observations. A separate `waler-infra-status-health.timer`, running independently of the external disk, checks a root-disk publication receipt and the actual mountpoints; its failure triggers a metadata-only Telegram home-channel alert via `hermes send`, without a model invocation. If the Hermes installation or platform credentials are themselves broken, delivery can fail; a private alert receipt and systemd failure remain. No independent second-provider alert path is claimed.

## Rollback boundaries

Reverting Git changes restores declarations, not deleted data or an upgraded database schema. Host fstab changes need root-level review; encrypted credentials must remain independently recoverable. Original server notes including Ghostty terminfo are preserved in `previous-server-notes.md`.
