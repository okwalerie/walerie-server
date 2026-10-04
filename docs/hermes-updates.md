# Daily supervised Hermes updates — HOME-261 / HOME-263

## Schedule and boundaries

The standalone **user systemd** oneshot is scheduled for **05:47 UTC daily**, with up to 15 minutes jitter and 1 minute timer accuracy. `Persistent=false` prevents reboot/login catch-up updates. `updates/maintenance.json` starts **armed=false**. Source fixes and a fresh sampled recovery proof do not establish rollout acceptance: installation/readback, child-workload completion, protected-checkout review, post-supervisor service identity, application/external-channel verification and explicit authorization remain prerequisites. This document describes repository policy, not a claim that the current installed wrapper matches it or maintenance is armed.

Existing timers are retained unchanged: `waler-update-report.timer` reports **OS images only**, at 06:00 plus up to 15 minutes jitter; `waler-monitor-collect.timer` collects host health every minute. Overlap may report transient maintenance health. No second image updater or LLM recurring cron job is created.

The authoritative [managed-source update documentation](https://hermes-agent.nousresearch.com/docs/getting-started/updating) supports `hermes update --plan`, `--check`, and `--backup --yes`. The managed checkout is `/var/home/core/.hermes/hermes-agent`; source channel `main` is intended. Exact installed identity must be read back during an authorized rollout, not inferred from historical version observations.

## Supervisor and decision flow

- Explicit default `HERMES_HOME=/var/home/core/.hermes`. Refuse **idle sibling profile directories as well as non-default runtimes**: upstream backup/config/cron writers enumerate siblings even if no runtime is active. Enumeration mirrors upstream valid named directories and excludes `default` and aliases resolving to the default home. Home mismatch, discovery errors and upstream API drift fail closed. Discovery repeats before install; concurrent profile creation remains a race without an upstream default-only write mode. Do not delete/move profiles to bypass the gate.
- Nonblocking exclusive `fcntl.flock` serializes competing runs. Concurrent apply is a benign deferral. Supervisor-failure handling and recovery acknowledgment share the lock; Hermes retains its own updater locking.
- 2 GiB MemoryHigh, 3 GiB MemoryMax, 512 MiB swap maximum, 150% CPU, 512 tasks, nice 10 and low-priority disk IO bound maintenance resource use. A large build can still hit its cap.
- 50-minute overall oneshot budget, 35-minute update-child budget, 60-second stop cleanup. No automatic retries. Cgroup cleanup bounds orphan update descendants. Failure recording uses **OS Python**, not the potentially damaged Hermes venv.
- **Recovery and profile gates precede any upstream plan/check, even dry-run or no-op.** Upstream checks may reconcile recovery state, so they are not a safe way to bypass an inhibit. An armed eligible run obtains the plan and check. Official obligations are rechecked after check, before recording a no-op. A recognized no-update result needs no backup/drain/install, but is never recovery acknowledgment. Unrecognized checks fail closed.
- Available updates require fresh verified off-host recovery evidence and a clean managed checkout on main before drain. Immediately preapply the wrapper repeats backup, checkout, official-obligation, supervisor-inhibit and profile checks. Apply is exactly `hermes update --backup --yes`, without stdin or gateway IPC mode. It does not skip official state backup or force a branch switch.

## Bounded conversation policy

`gateway.drain_control.write_drain_request` blocks new gateway turns without stopping the process. Our marker belongs to principal `waler-hermes-maintenance`. The supervisor waits up to **10 minutes**, requiring three idle samples, a fresh drain acknowledgment and PID/start-time identity. Timeout cancels only its own marker and **defers without killing a busy conversation**. Another owner's drain is never adopted or cancelled. Unarmed/concurrent/busy deferrals do not create recovery debt.

Runtime classification must be inspected at rollout: an active dashboard unit does not establish that every dashboard process is systemd-owned. Manual `serve` and `dashboard` runtimes have independent official restart obligations. The gateway drain does not gate every dashboard/CLI/desktop session or terminal agent. Child workloads must finish before approved maintenance. Discovery can race with new work; upstream restart has its own bounded, potentially forceful policy. Once code/dependency mutation begins, timeout/OOM may strand the install. Recovery requires operator review, never blind rollback or retry.

## Backup prerequisite

The `waler-recovery-v1` adapter reads the actual backup verifier proof: full restic `snapshot_id`, snapshot `time`, absolute `sample`, `restore_target` and sample `sha256`, followed by adjacent `last-success`. It requires an owned nonsymlink proof, safe modes, coherent proof/completion mtimes, snapshot and verification completion within **26 hours**, and a matching retained restored-sample digest. It never creates or refreshes proof; an old empty completion marker is insufficient. Read the configured receipt path and verifier contract before rollout. A renamed/proposed marker is not evidence.

An absent `backup_contract` retains the legacy host=`waler`, verified=true, `verified_at` adapter; any **explicit unknown contract refuses**. A sampled restore is not complete application recovery or a full repository check. Fresh verified Waler proof does not imply rollout acceptance or homewide laptop backup.

## Protecting unmanaged projects

`.lattice/`, `tinker-atropos/`, `vino/` and `vulpea-journal/` are protected projects. Hermes autostash includes untracked files and could remove directory trees during update. The wrapper refuses dirty/untracked state rather than stashing/deleting/moving it. After ownership and independent backup review, private root-anchored `.git/info/exclude` entries may be separately authorized; other edits/untracked paths still block. Preapply rejects upstream tree collisions with each protected name. Never use broad git clean, reset --hard or automatic source stash to bypass protection.

## Private evidence and recovery

Private state `~/.local/state/hermes-maintenance` is 0700, files 0600: unique run logs, pre-update proof/identity, last check/success, persistent recovery latch, in-progress marker, unique failure history, legacy failure archives and acknowledgment history. Do not publish logs, archives, credentials or restored sample contents. Failed installs/health and supervisor timeout/OOM latch recovery. A stale in-progress marker also inhibits; ordinary cleanup does not erase an interrupted previous run. Failure history is retained across no-op, success and acknowledgment.

The official read-only gate rejects incomplete-install/pull/repair markers, Git operations, armed gateway fleet restart debt, unfinished/unknown receipts and unresolved gateway fleet rows. A reviewed exact receipt digest may permit a **settled historical partial/failed outcome**, never remaining restart debt.

### Independent manual runtime obligations

The gate reads `latest.json`'s `pending_manual_serves`, manual `serve`/`dashboard` rows in `plan.runtimes`, and the independent default-home `serve_restart_pending` directory. Installed upstream stores receipt identity in `detail.create_time` with supervisor=`manual-serve`, restart_via=`respawn-argv`; immutable reminder JSON stores kind/profile/pid/create_time directly. These obligations survive receipt rotation independently of gateway health.

Only upstream's **read-only** process identity probe returning exactly false (recorded incarnation gone, including PID reuse) settles a valid row. Missing receipt creation time can settle only when the PID is provably gone. Live/unknown identity, malformed contracts/JSON, invalid creation time, unreadable storage, symlinks or unrecognized reminder entries block. Settled historical rows/files remain byte-identical: the wrapper does not invoke upstream warning/transfer helpers that create/delete reminders, rewrite receipts, or manufacture successful restart evidence. A matched acknowledgment digest never exempts manual debt.

For recovery, stop the timer and wait for the maintenance supervisor to exit. Inspect private failure/install/receipt/reminder evidence. Separately authorize and perform install repair and owner-controlled relaunch of every owed manual runtime, then verify replacements, local services, exact checkout identity and required application/external channels **after supervisor exit**. For missing identity, establish that the old PID is gone. Corrupt/unreadable reminders require explicit operator-reviewed storage repair with original evidence retained privately; do not silently delete debt. This wrapper offers no automatic reminder repair or runtime restart. Do not run upstream plan/check merely to clear recovery; its reconciliation may mutate official evidence.

### Explicit reviewed acknowledgment

Only after actual recovery, an owned, regular, nonsymlink **0600** review JSON can be passed to `waler-hermes-update --acknowledge-recovery PRIVATE_REVIEW_JSON`. Required fields:

- `schema`: 1; `successful_recovery`: true.
- `reviewer`: nonempty string; `recovery_evidence`: nonempty prose citing actual repair and post-exit verification commands/results, not a fixture/template claim.
- `recovered_at`: timezone timestamp no older than 24 hours and not future-dated.
- `head`: exact full installed checkout SHA.
- `recovery_id`: exact current `recovery-required.json.id`, or `legacy` if no latch exists.

Acknowledgment independently checks official obligations, profile scope, clean checkout, exact head, supervisor inactive/failed state and local health. It rechecks official debt just before publication and binds the acknowledgment to exact receipt/failure digests. It retains failure and acknowledgment history while clearing the local latch/in-progress marker; no update, drain, restart, arming or official receipt/reminder rewrite occurs. It cannot authenticate review prose or prove external delivery. Never write successful review evidence before recovery. A new failure/receipt or unresolved manual obligation blocks again.

Success health means active gateway/dashboard units, fresh PID-verified running gateway identity at the exact installed commit and local HTTP liveness. The historical `/health` probe yielded a 302 authentication redirect; this is **not authenticated deep dashboard health, replacement cgroup/lifetime proof or external channel delivery**. Local unit/journal visibility does not verify push delivery. Any alert handler/provider requires separate installed-byte and delivery acceptance; this source review makes no claim about current notification configuration. Log/backup retention remains a separately reviewed capacity policy.

## Offline verification and authorized rollout boundary

```sh
PYTHONDONTWRITEBYTECODE=1 python3 /var/home/core/walerie-server/updates/test_hermes_update.py
PYTHONDONTWRITEBYTECODE=1 /var/home/core/.hermes/hermes-agent/venv/bin/python /var/home/core/walerie-server/updates/test_hermes_update.py
```

The isolated suite patches subprocesses, uses temporary scratch fixtures and fake upstream modules/identity, and produces no production proof. Source/test success is not installed/live acceptance. After separately authorized installation and readback, unit verification, timer/service status and wrapper dry-run may be inspected under the rollout policy. Dry-run refuses recovery before upstream plan; when eligible it performs actual plan/backup/checkout/PID reads without wrapper evidence writes, drain, apply or restart. Official upstream plan/check side effects must not be mistaken for a universally read-only recovery tool. Maintenance remains unarmed until the parent's independent rollout acceptance and explicit approval.
