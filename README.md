# walerie-server

Notes and configuration for reproducing the Waler Fedora CoreOS/uCore server.

## Recorded mutable state

### Ghostty SSH terminfo

**Symptom:** SSH sessions from Ghostty set `TERM=xterm-ghostty`; programs such as `systemctl` fail when the server lacks that terminfo entry.

**Current account-scoped fix** (installed for `core`):

```sh
# Run from a Ghostty client; no sudo required on the server.
infocmp -x xterm-ghostty | ssh core@waler \
  'mkdir -p ~/.terminfo && tic -x -o ~/.terminfo -'
```

Verify:

```sh
ssh core@waler 'TERM=xterm-ghostty tput colors'
```

The entry is deliberately in `~/.terminfo`: this is standard user-level ncurses configuration, survives CoreOS rebases, and avoids layering Ghostty or a custom system image. It is **mutable account state**, not yet image-owned declarative configuration.
