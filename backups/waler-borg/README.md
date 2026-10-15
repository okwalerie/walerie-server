# waler borg backup

Daily encrypted backup of waler to the Hetzner Storage Box, replacing the earlier
restic "recovery lane". The old lane copied ~4 GiB of cold-staged data and ran a
full restore drill into `~/.local/state/waler-backup/` every day, and never pruned it.
That filled the root disk, and from then on the job could not run.

- repo: `ssh://u576392@u576392.your-storagebox.de:23/./backups/waler-borg` (`borg-1.4` on the box), `repokey-blake2`
- passphrase: `~/.config/waler-backup/borg-passphrase`. The passphrase and key export are escrowed in bws project `waler-infra` (`WALER_BORG_PASSPHRASE`, `WALER_BORG_KEY`)
- archives: `rama-*` (written while the rama cluster is stopped) and `waler-*` (everything in `sources` except `excludes`, plus logical dumps)
- consistency: buzz postgres via `pg_dumpall`, and Hermes SQLite via the online backup API. Raw files for both are excluded. There is no other staging.
- retention: 14 daily, 8 weekly, 12 monthly, 3 yearly, per prefix. A `borg check --repository-only` runs on Sundays.
- alerts: if the service fails, or `waler-backup-monitor` finds no success in 36h, `waler-maintenance-alert@` sends a Telegram message via Hermes.

## install

```sh
install -m 0700 waler-backup waler-backup-monitor ~/.local/libexec/
install -m 0600 sources excludes ~/.config/waler-backup/
install -m 0644 systemd/* ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now waler-backup.timer waler-backup-monitor.timer
```

## restore

borg runs under `podman unshare`, so that files owned by rootless-container subuids are readable. Restore the same way so ownership maps back:

```sh
export BORG_REPO=ssh://u576392@u576392.your-storagebox.de:23/./backups/waler-borg BORG_REMOTE_PATH=borg-1.4
export BORG_RSH="ssh -p 23 -i ~/.ssh/id_ed25519" BORG_PASSCOMMAND="cat ~/.config/waler-backup/borg-passphrase"
podman unshare borg list
mkdir -p /mnt/service-data/restore && cd /mnt/service-data/restore
podman unshare borg extract ::waler-YYYY-MM-DDTHH:MM path/inside/archive
```

The legacy restic repo (`backups/waler`) is frozen; its credentials are in `~/.config/waler-backup/restic-legacy/`. Delete the repo once the borg history covers the window you care about.
