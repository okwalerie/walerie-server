"""Offline safety-contract tests; fixtures are not live backup evidence."""
import datetime as dt
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import tempfile
import os
import sys
import types
from contextlib import ExitStack
import unittest
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader('updater', str(Path(__file__).with_name('waler-hermes-update')))
spec = importlib.util.spec_from_loader(loader.name, loader)
assert spec is not None
m = importlib.util.module_from_spec(spec)
with patch.dict(os.environ):
    loader.exec_module(m)
PROFILE_GUARD = m.profile_guard
OFFICIAL_GUARD = m.official_recovery_guard
QUIESCE = m.quiesce
CANCEL_DRAIN = m.cancel_owned_drain


class Safety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.receipt = self.root / 'proof.json'
        self.config = {'armed': False, 'backup_receipt': str(self.receipt),
                       'max_backup_age_hours': 26, 'drain_budget_seconds': 1}
        self.proof = {'host': 'waler', 'verified': True, 'snapshot_id': 'a' * 64,
                      'verified_at': m.now().isoformat()}
        self.config_file = self.root / 'maintenance.json'
        self.config_file.write_text(json.dumps(self.config))
        self.receipt.write_text(json.dumps(self.proof))
        self.receipt.chmod(0o600)
        self.state = self.root / 'state'
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for name, value in [('STATE', self.state), ('CONFIG', self.config_file),
                            ('HERMES', self.root / 'hermes'), ('REPO', self.root / 'checkout'),
                            ('CLI', self.root / 'fake-hermes')]:
            self.stack.enter_context(patch.object(m, name, value))
        self.stack.enter_context(patch.object(m, 'official_recovery_guard'))
        self.stack.enter_context(patch.object(m, 'profile_guard'))
        self.stack.enter_context(patch.object(m, 'cancel_owned_drain'))
        # Even a missed mock cannot call a real CLI, git, systemctl, curl or child.
        self.stack.enter_context(patch.object(m.subprocess, 'run', side_effect=AssertionError('real subprocess forbidden')))
        self.stack.enter_context(patch.object(m.subprocess, 'Popen', side_effect=AssertionError('real child forbidden')))

    def run_main(self, mode='--apply', check='Update available', **overrides):
        self.config['armed'] = True
        self.config_file.write_text(json.dumps(self.config))
        def command(args, timeout=120):
            if '--check' in args:
                return check
            if 'rev-parse' in args:
                return 'a' * 40
            if '--plan' in args:
                return 'OFFLINE plan\n'
            return ''
        with ExitStack() as stack:
            stack.enter_context(patch.object(m, 'command', side_effect=command))
            for name in ['backup_guard', 'clean_guard', 'quiesce', 'install_update', 'health']:
                stack.enter_context(patch.object(m, name, **overrides.get(name, {'return_value': {}})))
            stack.enter_context(patch('sys.argv', ['update', mode]))
            return m.main()

    def tearDown(self):
        self.temp.cleanup()

    def test_valid_proof(self):
        self.assertEqual(m.backup_guard(self.config)['snapshot_id'], 'a' * 64)

    def test_missing_proof(self):
        self.receipt.unlink()
        with self.assertRaises(FileNotFoundError):
            m.backup_guard(self.config)

    def test_stale_and_future_proof(self):
        for offset in [-27, 1]:
            self.proof['verified_at'] = (m.now() + dt.timedelta(hours=offset)).isoformat()
            self.receipt.write_text(json.dumps(self.proof))
            with self.assertRaises(RuntimeError):
                m.backup_guard(self.config)

    def test_incomplete_or_other_host_proof(self):
        for key, value in [('verified', False), ('snapshot_id', 'short'), ('host', 'asahi')]:
            changed = dict(self.proof, **{key: value})
            self.receipt.write_text(json.dumps(changed))
            with self.assertRaises(RuntimeError):
                m.backup_guard(self.config)

    def test_unsafe_proof_permissions(self):
        self.receipt.chmod(0o666)
        with self.assertRaises(RuntimeError):
            m.backup_guard(self.config)

    def test_recovery_receipt_and_restored_digest(self):
        import hashlib
        restored_root = self.root / 'restored'
        sample = Path('/var/home/core/.local/libexec/waler-backup-recovery')
        restored = restored_root / str(sample).lstrip('/')
        restored.parent.mkdir(parents=True)
        restored.write_bytes(b'OFFLINE TEST FIXTURE')
        recovery = {'snapshot_id': 'b' * 64, 'time': m.now().isoformat(),
                    'sample': str(sample), 'restore_target': str(restored_root),
                    'sha256': hashlib.sha256(restored.read_bytes()).hexdigest()}
        self.receipt.write_text(json.dumps(recovery))
        self.receipt.with_name('last-success').touch(mode=0o600)
        self.config['backup_contract'] = 'waler-recovery-v1'
        self.assertEqual(m.backup_guard(self.config)['snapshot_id'], 'b' * 64)
        restored.write_bytes(b'CORRUPTED TEST FIXTURE')
        with self.assertRaises(RuntimeError):
            m.backup_guard(self.config)

    def test_dirty_checkout_blocks_autostash(self):
        with patch.object(m, 'command', return_value='?? precious/untracked/\n'):
            with self.assertRaises(RuntimeError):
                m.clean_guard()

    def test_wrong_branch_blocks(self):
        with patch.object(m, 'command', side_effect=['', 'feature']):
            with self.assertRaises(RuntimeError):
                m.clean_guard()

    def test_dry_run_no_mutation(self):
        with patch.object(m, 'CONFIG', self.config_file), patch.object(m, 'STATE', self.state), \
             patch.object(m, 'command', side_effect=['head', 'TEST plan\n', '', 'main']), \
             patch.object(m, 'runtime', return_value={}), \
             patch.object(m, 'quiesce') as drain, patch.object(m, 'install_update') as update, \
             patch('sys.argv', ['update', '--dry-run']):
            self.assertEqual(m.main(), 0)
            self.assertFalse(self.state.exists())
            drain.assert_not_called()
            update.assert_not_called()

    def test_unarmed_benign_deferral_no_restart(self):
        with patch.object(m, 'CONFIG', self.config_file), patch.object(m, 'STATE', self.state), \
             patch.object(m, 'command', side_effect=['head', 'TEST plan']), \
             patch.object(m, 'cancel_owned_drain'), patch.object(m, 'install_update') as update, \
             patch('sys.argv', ['update', '--apply']):
            self.assertEqual(m.main(), 0)
            self.assertFalse((self.state / 'failure.json').exists())
            self.assertFalse((self.state / 'recovery-required.json').exists())
            self.assertFalse((self.state / 'in-progress.json').exists())
            update.assert_not_called()

    def test_noop_does_not_drain_restart_or_require_backup(self):
        self.config['armed'] = True
        self.config_file.write_text(json.dumps(self.config))
        with patch.object(m, 'CONFIG', self.config_file), patch.object(m, 'STATE', self.state), \
             patch.object(m, 'command', side_effect=['head', 'TEST plan', '✓ Already up to date.']), \
             patch.object(m, 'backup_guard') as backup, patch.object(m, 'quiesce') as drain, \
             patch.object(m, 'cancel_owned_drain'), patch.object(m, 'install_update') as update, \
             patch('sys.argv', ['update', '--apply']):
            self.assertEqual(m.main(), 0)
            backup.assert_not_called()
            drain.assert_not_called()
            update.assert_not_called()
            self.assertEqual(json.loads((self.state / 'last-check.json').read_text())['result'], 'no-update')


    def test_unknown_receipt_contract_rejected(self):
        self.config['backup_contract'] = 'future-or-typo'
        with self.assertRaisesRegex(RuntimeError, 'unknown'):
            m.backup_guard(self.config)

    def test_failed_install_or_health_inhibits_next_day_and_noop(self):
        for stage in ['install_update', 'health']:
            with self.subTest(stage=stage):
                self.assertEqual(self.run_main(**{stage: {'side_effect': RuntimeError('injected ' + stage)}}), 1)
                original = (self.state / 'failure.json').read_bytes()
                tomorrow = m.now() + dt.timedelta(days=1)
                with patch.object(m, 'now', return_value=tomorrow), patch.object(m, 'command') as cmd:
                    with patch('sys.argv', ['update', '--apply']):
                        self.assertEqual(m.main(), 1)
                    cmd.assert_not_called()
                self.assertEqual(self.run_main(check='Already up to date.'), 1)
                self.assertEqual((self.state / 'failure.json').read_bytes(), original)
                self.assertFalse((self.state / 'last-check.json').exists())
                # Reset only fixture state for the next independent failure stage.
                (self.state / 'recovery-required.json').unlink()
                (self.state / 'failure.json').unlink()

    def test_supervisor_timeout_oom_and_history(self):
        self.state.mkdir()
        m.record_failure('earlier install failure')
        original = (self.state / 'failure.json').read_bytes()
        for result in ['timeout', 'oom-kill']:
            with patch.dict(os.environ, SERVICE_RESULT=result), patch('sys.argv', ['update', '--supervisor-failure']):
                self.assertEqual(m.main(), 0)
            self.assertEqual(json.loads((self.state / 'recovery-required.json').read_text())['service_result'], result)
            self.assertEqual(self.run_main(check='Already up to date.'), 1)
        self.assertTrue(any(p.read_bytes() == original for p in (self.state / 'failures').iterdir()))

    def test_supervisor_success_does_not_clear_latch(self):
        self.state.mkdir()
        m.record_failure('injected')
        original = (self.state / 'recovery-required.json').read_bytes()
        with patch.dict(os.environ, SERVICE_RESULT='success'), patch('sys.argv', ['update', '--supervisor-failure']):
            self.assertEqual(m.main(), 0)
        self.assertEqual((self.state / 'recovery-required.json').read_bytes(), original)

    def test_stale_inprogress_and_legacy_failure_block_without_overwrite(self):
        self.state.mkdir()
        for name in ['in-progress.json', 'failure.json']:
            path = self.state / name
            path.write_text('OLD FAILURE FIXTURE')
            self.assertEqual(self.run_main(check='Already up to date.'), 1)
            self.assertEqual(path.read_text(), 'OLD FAILURE FIXTURE')
            path.unlink()

    def test_dryrun_pending_recovery_is_readonly_before_checks(self):
        self.state.mkdir()
        m.record_failure('injected')
        before = {p.relative_to(self.state): p.read_bytes() for p in self.state.rglob('*') if p.is_file()}
        with patch.object(m, 'command') as cmd:
            with patch('sys.argv', ['update', '--dry-run']):
                self.assertEqual(m.main(), 1)
            cmd.assert_not_called()
        after = {p.relative_to(self.state): p.read_bytes() for p in self.state.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_busy_and_concurrent_deferrals_do_not_poison(self):
        self.assertEqual(self.run_main(quiesce={'side_effect': m.Deferred('busy fixture')}), 0)
        self.assertFalse((self.state / 'failure.json').exists())
        with patch.object(m.fcntl, 'flock', side_effect=BlockingIOError):
            self.assertEqual(self.run_main(), 0)
        self.assertFalse((self.state / 'recovery-required.json').exists())

    def test_idle_sibling_enumeration_matches_upstream(self):
        default = m.HERMES
        default.mkdir()
        root = default / 'profiles'
        root.mkdir()
        import re
        profiles = types.ModuleType('hermes_cli.profiles')
        profiles._get_default_hermes_home = lambda: default
        profiles._get_profiles_root = lambda: root
        profiles._PROFILE_ID_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$')
        inventory = types.ModuleType('hermes_cli.update_inventory')
        inventory.collect_runtime_inventory = lambda: types.SimpleNamespace(runtimes=[])
        with patch.dict(sys.modules, {'hermes_cli.profiles': profiles, 'hermes_cli.update_inventory': inventory}):
            PROFILE_GUARD()
            (root / 'idle-sibling').mkdir()
            with self.assertRaisesRegex(RuntimeError, 'sibling profile'):
                PROFILE_GUARD()
            with patch.object(m, 'profile_guard', side_effect=PROFILE_GUARD):
                self.assertEqual(self.run_main(), 1)
            self.assertFalse((self.state / 'pre-update.json').exists())

    def test_sibling_appearing_during_drain_blocks_install(self):
        with patch.object(m, 'profile_guard', side_effect=[None, None, RuntimeError('new sibling')]), \
             patch.object(m, 'install_update') as install:
            # run_main has its own installer mock: retain it via an explicit override.
            self.assertEqual(self.run_main(install_update={'side_effect': AssertionError('must not install')}), 1)
            install.assert_not_called()
        self.assertFalse((self.state / 'last-success.json').exists())

    def ack_command(self, args, timeout=120):
        return 'inactive' if args[0] == 'systemctl' else 'a' * 40

    def review_fixture(self):
        self.state.mkdir(exist_ok=True)
        m.record_failure('fixture failed install')
        data = {'schema': 1, 'successful_recovery': True, 'reviewer': 'offline-test',
                'recovered_at': m.now().isoformat(), 'head': 'a' * 40,
                'recovery_id': json.loads((self.state / 'recovery-required.json').read_text())['id'],
                'recovery_evidence': 'OFFLINE FIXTURE: verified restored install and post-exit service identity'}
        path = self.root / 'review.json'
        path.write_text(json.dumps(data))
        path.chmod(0o600)
        return path, data

    def test_ack_requires_documented_success_and_matching_live_health(self):
        path, data = self.review_fixture()
        for key, bad in [('successful_recovery', False), ('reviewer', ''), ('recovery_evidence', ''),
                         ('head', 'b' * 40), ('recovery_id', 'wrong'), ('schema', 99),
                         ('recovered_at', (m.now() - dt.timedelta(days=2)).isoformat())]:
            path.write_text(json.dumps(dict(data, **{key: bad})))
            with patch.object(m, 'command', side_effect=self.ack_command), patch.object(m, 'clean_guard'), patch.object(m, 'health'):
                with self.assertRaises((RuntimeError, ValueError)):
                    m.acknowledge_recovery(path)
            self.assertTrue((self.state / 'recovery-required.json').exists())
        path.write_text(json.dumps(data))
        with patch.object(m, 'command', side_effect=self.ack_command), patch.object(m, 'clean_guard'), \
             patch.object(m, 'health', side_effect=RuntimeError('unhealthy')):
            with self.assertRaises(RuntimeError):
                m.acknowledge_recovery(path)
        self.assertTrue((self.state / 'recovery-required.json').exists())

    def test_explicit_ack_preserves_failure_history_allows_later_noop(self):
        path, data = self.review_fixture()
        original = (self.state / 'failure.json').read_bytes()
        with patch.object(m, 'command', side_effect=self.ack_command), patch.object(m, 'clean_guard'), \
             patch.object(m, 'health', return_value={'code_sha': 'a' * 40}), \
             patch('sys.argv', ['update', '--acknowledge-recovery', str(path)]):
            self.assertEqual(m.main(), 0)
        self.assertFalse((self.state / 'recovery-required.json').exists())
        self.assertEqual((self.state / 'failure.json').read_bytes(), original)
        self.assertEqual(self.run_main(check='Already up to date.'), 0)
        self.assertTrue(list(self.state.glob('ack-*.json')))
        # A later failure must invalidate the earlier acknowledgment.
        m.record_failure('new failure')
        self.assertEqual(self.run_main(check='Already up to date.'), 1)

    def test_real_quiesce_busy_timeout_and_cleanup_ownership_offline(self):
        m.HERMES.mkdir()
        marker = m.HERMES / '.drain_request.json'
        drain_module = types.ModuleType('gateway.drain_control')
        def write_request(**kwargs):
            marker.write_text(json.dumps(kwargs))
        setattr(drain_module, 'write_drain_request', write_request)
        with patch.dict(sys.modules, {'gateway.drain_control': drain_module}), \
             patch.object(m, 'runtime', return_value={'updated_at': m.now().isoformat(),
                                                     'gateway_state': 'draining', 'active_agents': 1}), \
             patch.object(m.time, 'monotonic', side_effect=[0, 0, 2]), patch.object(m.time, 'sleep'):
            with self.assertRaises(m.Deferred):
                QUIESCE(1)
        self.assertEqual(json.loads(marker.read_text())['principal'], m.PRINCIPAL)
        CANCEL_DRAIN()
        self.assertFalse(marker.exists())
        marker.write_text(json.dumps({'principal': 'other-owner'}))
        with patch.dict(sys.modules, {'gateway.drain_control': drain_module}):
            with self.assertRaises(m.Deferred):
                QUIESCE(1)
        CANCEL_DRAIN()
        self.assertTrue(marker.exists())

    def test_ack_private_mode_and_changed_recovery_refused(self):
        path, data = self.review_fixture()
        path.chmod(0o644)
        with self.assertRaises(RuntimeError):
            m.acknowledge_recovery(path)
        path.chmod(0o600)
        def health(head):
            m.record_failure('new event during review')
            return {}
        with patch.object(m, 'clean_guard'), patch.object(m, 'command', side_effect=self.ack_command), \
             patch.object(m, 'health', side_effect=health):
            with self.assertRaisesRegex(RuntimeError, 'changed during review'):
                m.acknowledge_recovery(path)
        self.assertTrue((self.state / 'recovery-required.json').exists())

    def test_installer_timeout_sets_latch_without_real_process_or_signal(self):
        from unittest.mock import MagicMock
        child = MagicMock()
        child.pid = 424242
        child.wait.side_effect = [m.subprocess.TimeoutExpired('OFFLINE fixture', 2100), 0]
        child.__enter__.return_value = child
        installer = m.install_update
        with patch.object(m.subprocess, 'Popen', return_value=child), patch.object(m.os, 'killpg') as kill:
            self.assertEqual(self.run_main(install_update={'side_effect': installer}), 1)
            kill.assert_called_once_with(child.pid, m.signal.SIGTERM)
        self.assertTrue((self.state / 'recovery-required.json').exists())
        self.assertEqual(self.run_main(check='Already up to date.'), 1)

    def test_ack_requires_supervisor_postexit(self):
        path, _ = self.review_fixture()
        def command(args, timeout=120):
            return 'active' if args[0] == 'systemctl' else 'a' * 40
        with patch.object(m, 'command', side_effect=command), patch.object(m, 'clean_guard'), patch.object(m, 'health') as health:
            with self.assertRaisesRegex(RuntimeError, 'exited'):
                m.acknowledge_recovery(path)
            health.assert_not_called()
        self.assertTrue((self.state / 'recovery-required.json').exists())

    def official_fixture(self):
        modules = {name: types.ModuleType(name) for name in
                   ['hermes_cli._early_recovery', 'hermes_cli.update_cmd_fleet',
                    'pm.environments', 'hermes_cli.process_identity']}
        setattr(modules['hermes_cli._early_recovery'], 'interrupted_pull_marker', lambda repo: repo / 'interrupted')
        setattr(modules['hermes_cli._early_recovery'], 'git_operation_in_progress', lambda repo: None)
        setattr(modules['hermes_cli.update_cmd_fleet'], '_fleet_restart_obligation_armed', lambda: False)
        setattr(modules['pm.environments'], 'install_state_dir', lambda repo: repo / 'install-state')
        from unittest.mock import Mock
        identity = Mock(return_value=True)
        setattr(modules['hermes_cli.process_identity'], '_pid_alive_matches', identity)
        self.stack.enter_context(patch.dict(sys.modules, modules))
        self.stack.enter_context(patch.object(m, 'official_recovery_guard', side_effect=OFFICIAL_GUARD))
        receipt = m.HERMES / 'logs/update_receipts/latest.json'
        receipt.parent.mkdir(parents=True, exist_ok=True)
        data = {'schema': 1, 'outcome': 'success', 'finished_at': m.now().isoformat(),
                'gateway_restart': {'incomplete': False}, 'fleet': [{'state': 'current'}]}
        receipt.write_text(json.dumps(data))
        return receipt, data, identity

    def manual_row(self, kind='serve', durable=False):
        row = {'kind': kind, 'profile': 'default', 'pid': 424242}
        if durable:
            row['create_time'] = 1234.5
        else:
            row.update(supervisor='manual-serve', restart_via='respawn-argv', detail={'create_time': 1234.5})
        return row

    def manual_debt(self, source, kind):
        receipt, data, identity = self.official_fixture()
        if source == 'durable':
            path = m.HERMES / 'serve_restart_pending/424242-0x1.34ap+10.json'
            path.parent.mkdir(exist_ok=True)
            path.write_text(json.dumps(self.manual_row(kind, durable=True)))
        else:
            path = receipt
            row = self.manual_row(kind)
            data.update({'pending_manual_serves': [row]} if source == 'pending' else {'plan': {'runtimes': [row]}})
            receipt.write_text(json.dumps(data))
        return path, identity

    def test_manual_receipt_plan_and_durable_obligations_block_all_modes(self):
        for source in ['pending', 'plan', 'durable']:
            for kind in ['serve', 'dashboard']:
                with self.subTest(source=source, kind=kind), ExitStack() as isolated:
                    # Each case owns an independent fixture and patches.
                    old_stack = self.stack
                    self.stack = isolated
                    try:
                        path, identity = self.manual_debt(source, kind)
                        original = path.read_bytes()
                        with self.assertRaisesRegex(RuntimeError, 'manual serve'):
                            OFFICIAL_GUARD()
                        import hashlib
                        with self.assertRaises(RuntimeError):
                            OFFICIAL_GUARD(reviewed_receipt_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                        for mode in ['--dry-run', '--apply']:
                            with patch.object(m, 'command') as cmd, patch.object(m, 'quiesce') as drain, \
                                 patch.object(m, 'install_update') as install, patch('sys.argv', ['update', mode]):
                                self.assertEqual(m.main(), 1)
                                cmd.assert_not_called()
                                drain.assert_not_called()
                                install.assert_not_called()
                        self.assertFalse((self.state / 'last-check.json').exists())
                        self.assertEqual(path.read_bytes(), original)
                        path.unlink()
                    finally:
                        self.stack = old_stack

    def test_manual_obligations_refuse_ack_until_proven_gone_preserve_evidence(self):
        for source in ['pending', 'plan', 'durable']:
            for kind in ['serve', 'dashboard']:
                with self.subTest(source=source, kind=kind), ExitStack() as isolated:
                    old_stack = self.stack
                    self.stack = isolated
                    try:
                        debt, identity = self.manual_debt(source, kind)
                        review, _ = self.review_fixture()
                        original_debt = debt.read_bytes()
                        original_failure = (self.state / 'failure.json').read_bytes()
                        for state in [True, None]:
                            identity.return_value = state
                            with patch.object(m, 'command') as cmd, patch.object(m, 'health') as health:
                                with self.assertRaises(RuntimeError):
                                    m.acknowledge_recovery(review)
                                cmd.assert_not_called()
                                health.assert_not_called()
                            self.assertTrue((self.state / 'recovery-required.json').exists())
                            self.assertFalse((self.state / 'recovery-acknowledged.json').exists())
                        identity.return_value = False
                        with patch.object(m, 'clean_guard'), patch.object(m, 'command', side_effect=self.ack_command), \
                             patch.object(m, 'health', return_value={'code_sha': 'a' * 40}):
                            m.acknowledge_recovery(review)
                        self.assertEqual(debt.read_bytes(), original_debt)
                        self.assertEqual((self.state / 'failure.json').read_bytes(), original_failure)
                        self.assertEqual(self.run_main(check='Already up to date.'), 0)
                        (self.state / 'recovery-acknowledged.json').unlink()
                        debt.unlink()
                    finally:
                        self.stack = old_stack

    def test_manual_unknown_identity_and_corrupt_contract_fail_closed(self):
        receipt, data, identity = self.official_fixture()
        row = self.manual_row('dashboard')
        row['detail'] = {}
        data['pending_manual_serves'] = [row]
        receipt.write_text(json.dumps(data))
        for state in [True, None]:
            identity.return_value = state
            with self.assertRaises(RuntimeError):
                OFFICIAL_GUARD()
        identity.return_value = False
        OFFICIAL_GUARD()
        identity.assert_called_with(424242, None)
        for pending in [None, {}, [None], [dict(row, pid=True)],
                        [dict(row, detail={'create_time': float('nan')})], [dict(row, restart_via='unknown')]]:
            data['pending_manual_serves'] = pending
            receipt.write_text(json.dumps(data))
            with self.assertRaises(RuntimeError):
                OFFICIAL_GUARD()
        data['pending_manual_serves'] = []
        receipt.write_text(json.dumps(data))
        path = m.HERMES / 'serve_restart_pending/broken.json'
        path.parent.mkdir()
        review, _ = self.review_fixture()
        for content in ['not json', '[]', '{}', json.dumps(dict(self.manual_row(durable=True), create_time=None))]:
            path.write_text(content)
            with self.assertRaises((RuntimeError, ValueError)):
                OFFICIAL_GUARD()
            with patch.object(m, 'command') as cmd, patch.object(m, 'health') as health:
                with self.assertRaises((RuntimeError, ValueError)):
                    m.acknowledge_recovery(review)
                cmd.assert_not_called()
                health.assert_not_called()
            self.assertTrue((self.state / 'recovery-required.json').exists())
            self.assertFalse((self.state / 'recovery-acknowledged.json').exists())
            self.assertEqual(path.read_text(), content)
        path.unlink()
        with patch.object(Path, 'iterdir', side_effect=PermissionError('offline denied')):
            with self.assertRaises(PermissionError):
                OFFICIAL_GUARD()
        path.symlink_to(self.root / 'missing')
        with self.assertRaises(RuntimeError):
            OFFICIAL_GUARD()

    def test_durable_obligation_without_receipt_and_during_ack_health(self):
        debt, identity = self.manual_debt('durable', 'dashboard')
        (m.HERMES / 'logs/update_receipts/latest.json').unlink()
        with self.assertRaises(RuntimeError):
            OFFICIAL_GUARD()
        debt.unlink()
        review, _ = self.review_fixture()
        def health(head):
            debt.write_text(json.dumps(self.manual_row('dashboard', durable=True)))
            return {}
        with patch.object(m, 'clean_guard'), patch.object(m, 'command', side_effect=self.ack_command), \
             patch.object(m, 'health', side_effect=health):
            with self.assertRaisesRegex(RuntimeError, 'manual serve'):
                m.acknowledge_recovery(review)
        self.assertTrue((self.state / 'recovery-required.json').exists())
        self.assertFalse((self.state / 'recovery-acknowledged.json').exists())

    def test_manual_debt_appearing_during_plan_blocks_check_and_dryrun(self):
        receipt, data, identity = self.official_fixture()
        def command(args, timeout=120):
            if '--plan' in args:
                data['pending_manual_serves'] = [self.manual_row('serve')]
                receipt.write_text(json.dumps(data))
                return 'OFFLINE plan'
            if '--check' in args:
                raise AssertionError('must not check')
            return 'a' * 40
        with patch.object(m, 'command', side_effect=command), patch('sys.argv', ['update', '--dry-run']):
            self.assertEqual(m.main(), 1)
        self.assertFalse(self.state.exists())

    def test_manual_debt_appearing_during_check_or_drain_blocks_noop_apply(self):
        receipt, data, identity = self.official_fixture()
        def introduce():
            data['pending_manual_serves'] = [self.manual_row('dashboard')]
            receipt.write_text(json.dumps(data))
        def command(args, timeout=120):
            if '--check' in args:
                introduce()
                return 'Already up to date.'
            return 'a' * 40 if 'rev-parse' in args else ''
        self.config['armed'] = True
        self.config_file.write_text(json.dumps(self.config))
        with patch.object(m, 'command', side_effect=command), patch('sys.argv', ['update', '--apply']):
            self.assertEqual(m.main(), 1)
        self.assertFalse((self.state / 'last-check.json').exists())
        (self.state / 'recovery-required.json').unlink()
        (self.state / 'failure.json').unlink()
        data['pending_manual_serves'] = []
        receipt.write_text(json.dumps(data))
        self.assertEqual(self.run_main(quiesce={'side_effect': lambda seconds: introduce()},
                                      install_update={'side_effect': AssertionError('must not install')}), 1)
        self.assertFalse((self.state / 'pre-update.json').exists())

    def test_official_incomplete_receipt_and_restart_obligations(self):
        modules = {}
        for name in ['hermes_cli._early_recovery', 'hermes_cli.update_cmd_fleet', 'pm.environments']:
            modules[name] = types.ModuleType(name)
        early = modules['hermes_cli._early_recovery']
        early.interrupted_pull_marker = lambda repo: repo / 'interrupted'
        early.git_operation_in_progress = lambda repo: None
        fleet = modules['hermes_cli.update_cmd_fleet']
        fleet._fleet_restart_obligation_armed = lambda: False
        modules['pm.environments'].install_state_dir = lambda repo: repo / 'install-state'
        m.REPO.mkdir()
        with patch.dict(sys.modules, modules):
            OFFICIAL_GUARD()
            marker = m.REPO / '.update-incomplete'
            marker.touch()
            with self.assertRaises(RuntimeError):
                OFFICIAL_GUARD()
            marker.unlink()
            fleet._fleet_restart_obligation_armed = lambda: True
            with self.assertRaises(RuntimeError):
                OFFICIAL_GUARD()
            fleet._fleet_restart_obligation_armed = lambda: False
            receipt = m.HERMES / 'logs/update_receipts/latest.json'
            receipt.parent.mkdir(parents=True)
            for data in [{'schema': 1, 'outcome': 'partial'},
                         {'schema': 1, 'outcome': 'success', 'finished_at': 'fixture', 'gateway_restart': {'incomplete': True}},
                         {'schema': 1, 'outcome': 'success', 'finished_at': 'fixture', 'fleet': [{'state': 'stale'}]}]:
                receipt.write_text(json.dumps(data))
                with self.assertRaises(RuntimeError):
                    OFFICIAL_GUARD()
            # A completed historical failure can be explicitly reviewed, but a
            # new/different receipt and pending fleet obligations cannot inherit it.
            settled = {'schema': 1, 'outcome': 'partial', 'finished_at': 'fixture',
                       'gateway_restart': {'incomplete': False}, 'fleet': [{'state': 'current'}]}
            receipt.write_text(json.dumps(settled))
            import hashlib
            digest = hashlib.sha256(receipt.read_bytes()).hexdigest()
            OFFICIAL_GUARD(reviewed_receipt_sha256=digest)
            settled['fleet'] = [{'state': 'stale'}]
            receipt.write_text(json.dumps(settled))
            with self.assertRaises(RuntimeError):
                OFFICIAL_GUARD(reviewed_receipt_sha256=digest)


if __name__ == '__main__':
    unittest.main()
