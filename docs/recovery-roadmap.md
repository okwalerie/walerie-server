Canonical tracker: https://github.com/okwalerie/walerie-server/issues/13

**Historical issue-body snapshot, not current runtime state.** Preserved below without rewriting prior notes. Later issue comments supersede parts of this snapshot: #3 records successful scoped recovery evidence; #9 records lifecycle fixes; #10 records helper deployment with unresolved acceptance blockers. Follow the current issue threads and `publication-scope.md`; this file does not establish current backup freshness, installed-byte identity, service health or maintenance authorization.

# Waler recovery roadmap

This is the consolidated index, not an additional implementation issue. Keep acceptance criteria and closure evidence in the linked owner issues.

## Consolidation rules
- #8 owns lifecycle/image decisions; #4 consumes them for routes/TLS. They are related, not duplicate work.
- #3 owns backup/restore evidence; #10 cannot activate without verified protection. A configuration checkpoint is not a full Asahi backup.
- #5 owns local Gatus notifications; #6 owns an independent observer. Local monitoring cannot detect its own host outage.
- #9 owns canonical server declarations; portable account data remains in dotfiles under #11 reconciliation.
- No existing issue was closed as a duplicate: no true duplicate was found. #2 was closed only after an actual non-destructive repair and live verification.

## P0 — protection and safe foundations
- [ ] [3 — Repair the failing Waler backup lane and verify a staged restore](https://github.com/okwalerie/walerie-server/issues/3)
- [ ] [9 — Publish canonical Waler infrastructure and finish safe lifecycle rollout](https://github.com/okwalerie/walerie-server/issues/9)
- [ ] [10 — Safely update Hermes and enable guarded daily maintenance](https://github.com/okwalerie/walerie-server/issues/10)
- [ ] [12 — Diagnose failed OS staging and keep server update policies explicit](https://github.com/okwalerie/walerie-server/issues/12)

## P1 — intended services, convergence, monitoring and laptop protection
- [ ] [8 — Decide restore or retirement for dormant stacks and reconcile Quadlet image references](https://github.com/okwalerie/walerie-server/issues/8)
- [ ] [4 — Triage existing failed Homepage/Gatus service routes and Cockpit TLS mismatch](https://github.com/okwalerie/walerie-server/issues/4)
- [x] [2 — Investigate Syncthing folder pull error without deleting data or changing sync semantics](https://github.com/okwalerie/walerie-server/issues/2)
- [ ] [5 — Configure Gatus notifications with sensible failure and recovery thresholds](https://github.com/okwalerie/walerie-server/issues/5)
- [ ] [6 — Add off-host detection for Waler outages and missing heartbeats](https://github.com/okwalerie/walerie-server/issues/6)
- [ ] [11 — Establish Asahi historical backup and finish portable dotfile reconciliation](https://github.com/okwalerie/walerie-server/issues/11)

## P2 — controlled upgrades and new capability
- [ ] [7 — Review and safely apply the reported nginx container image update](https://github.com/okwalerie/walerie-server/issues/7)
- [ ] [1 — Deploy Calibre-Web on Waler with persistent library storage and Homepage integration](https://github.com/okwalerie/walerie-server/issues/1)

## Dependencies and execution
1. #3 successful backup + sampled restore before broad rollout; #9 lifecycle safety fixes/review can proceed in parallel.
2. #10 recovery latch/profile guards and tests now; actual upgrade and daily arming only after #3 and final review/source protection.
3. #12 diagnose OS/QEMU errors independently; no automatic reboot or reset-failed-only success.
4. #8 supplies one intended-state decision table; #4 repairs only intended-active routes/certificates. No blanket starting of stopped apps.
5. #5 needs approved alert destination/policy and verified failure/recovery delivery; #6 additionally needs an off-host observer choice.
6. #11 establishes actual historical laptop protection and publishes reviewed portable source; Syncthing is transport, not backup.
7. #7 controlled nginx rollout only after image/rollback review. #1 Calibre needs library/access-policy preflight and backup inclusion before rollout.

## Verified completed work
- #2: blocking object was a regular five-byte `.orgids` containing only `nil`. Its bytes were privately backed up and relocated outside sync; no document deletion, ignore-rule change, database reset or device/folder change. Both org/dev then showed zero pull errors and 100% completion for the connected peer.
- lofsite remains persistently paused/masked, definition/data retained. Canonical capture has 47 definitions, but is not yet published or bulk-deployed.
- Four Asahi ChezMoi target conflicts reconciled; source publication and full historical backup remain pending.

## Clear work currently executing
- Dedicated workers: lifecycle prior-mask rollback and redeploy-consumer authorization; updater recovery inhibition/idle-profile refusal; exact failed backup/finalizer diagnosis and verified recovery.
- These are started, not yet verified complete. Hermes remains unarmed. Do not advance backup freshness from a partial/error snapshot.

## Decisions still needed
- Active vs paused/retired per dormant stack and data-retention intent (#8).
- Gatus notification destination/policy and independent observer/provider (#5/#6).
- Full laptop backup inclusion/credential recovery, portable-source review (#11).
- Calibre library location/read-write/access policy (#1).

## Deferred separate decision
- [Keep/archive/delete custom ChatGPT Linux packaging](https://github.com/okwalerie/codex-desktop-bin/issues/5). Already filed; do not duplicate or delete the repository as part of this recovery.
