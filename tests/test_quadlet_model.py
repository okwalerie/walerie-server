"""Canonical generation is the test seam; no Podman reference mapping mocks."""
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
model = importlib.import_module('quadlet_model')
REPO = Path(__file__).parents[1]

class CanonicalModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.units = model.generated_units(REPO)

    def test_actual_nextcloud_requires_wants_and_pod_binding(self):
        self.assertEqual(model.direct_dependencies(self.units['nextcloud-app.service']), [
            'data-dirs.service', 'nextcloud-db.service', 'nextcloud-pod-pod.service',
            'nextcloud-redis.service', 'podman-user-wait-network-online.service'])

    def test_actual_forgejo_implicit_network(self):
        self.assertIn('forgejo-network.service', model.direct_dependencies(self.units['forgejo.service']))

    def test_actual_rama_build_pod_and_wants(self):
        deps = model.direct_dependencies(self.units['rama-supervisor.service'])
        self.assertIn('rama-runtime-build.service', deps)
        self.assertIn('rama-pod.service', deps)
        self.assertIn('rama-conductor.service', deps)

    def test_actual_generated_pod_wants_all_members(self):
        deps = model.direct_dependencies(self.units['nextcloud-pod-pod.service'])
        for unit in ['nextcloud-app.service', 'nextcloud-db.service', 'nextcloud-redis.service']:
            self.assertIn(unit, deps)

    def test_nonservice_direct_activation_not_discarded(self):
        self.assertIn('network-online.target', model.direct_dependencies(self.units['lofsite.service']))

    def test_full_canonical_tree_is_parseable(self):
        expected = {v['unit'] for v in json.loads((REPO/'services.json').read_text())['services'].values()}
        self.assertEqual(set(self.units), expected)
        for text in self.units.values():
            model.direct_dependencies(text)

    def test_direct_semantics_accumulation_section_ordering_and_sockets(self):
        text = '''[Unit]
Requires=old.service
Requires=
Requires=database.service
Wants=cache.service
Wants=database.service
BindsTo=pod.service
Upholds=worker.service
After=ordering-only.service
Requisite=already-running.service
PartOf=parent.service
[Service]
Sockets=api.socket
Sockets=
Sockets=second.socket
[X-Container]
Wants=not-a-systemd-edge.service
'''
        self.assertEqual(model.direct_dependencies(text), [
            'api.socket', 'cache.service', 'database.service', 'old.service', 'pod.service',
            'second.socket', 'worker.service'])

    def offline_unit_dump(self, root, text):
        """Verify in systemd-analyze's test manager; never connect to a live bus."""
        unit = root / 'demo.service'
        unit.write_text(text)
        result = subprocess.run(['systemd-analyze', '--user', 'verify', str(unit)],
                                env={**os.environ, 'SYSTEMD_UNIT_PATH': str(root),
                                     'SYSTEMD_LOG_LEVEL': 'debug', 'SYSTEMD_LOG_COLOR': '0'},
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('→ Unit demo.service:', result.stdout)
        return result.stdout.split('→ Unit demo.service:', 1)[1].split('→ Unit ', 1)[0]

    def test_empty_dependencies_without_prior_edges_are_noops(self):
        text = ('[Unit]\nRequires=\nWants=\nBindsTo=\nUpholds=\n'
                'OnFailure=\nOnSuccess=\nConflicts=\nPropagatesStopTo=\n'
                '[Service]\nSockets=\n')
        self.assertEqual(model.direct_dependencies(text), [])

    def test_empty_unit_dependencies_match_offline_systemd(self):
        for key in ('Requires', 'Wants', 'BindsTo', 'Upholds', 'OnFailure',
                    'OnSuccess', 'Conflicts', 'PropagatesStopTo'):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'cold.service').write_text(
                    '[Unit]\nDefaultDependencies=no\n[Service]\nExecStart=/usr/bin/true\n')
                text = ('[Unit]\nDefaultDependencies=no\n'
                        f'{key}=cold.service\n{key}=\n'
                        '[Service]\nExecStart=/usr/bin/true\n')
                dump = self.offline_unit_dump(root, text)
                self.assertRegex(dump, rf'(?m)^\s*{key}: cold\.service \(origin-file\)')
                if key in {'Requires', 'Wants', 'BindsTo', 'Upholds'}:
                    self.assertEqual(model.direct_dependencies(text), ['cold.service'])
                else:
                    with self.assertRaisesRegex(ValueError, 'Conditional activation/stop'):
                        model.direct_dependencies(text)

    def test_empty_sockets_match_offline_systemd(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'api.socket').write_text(
                '[Unit]\nDefaultDependencies=no\n[Socket]\n'
                'ListenStream=127.0.0.1:9999\nService=demo.service\n')
            text = ('[Unit]\nDefaultDependencies=no\n[Service]\n'
                    'ExecStart=/usr/bin/true\nSockets=api.socket\nSockets=\n')
            dump = self.offline_unit_dump(root, text)
            self.assertRegex(dump, r'(?m)^\s*Wants: api\.socket \(origin-file\)')
            self.assertEqual(model.direct_dependencies(text), ['api.socket'])

    def test_generated_empty_wants_match_offline_systemd(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'quadlets').mkdir()
            (root / 'quadlets/demo.container').write_text(
                '[Unit]\nDefaultDependencies=no\nWants=cold.service\nWants=\n'
                '[Quadlet]\nDefaultDependencies=false\n'
                '[Container]\nImage=example.invalid/demo:1\n')
            (root / 'services.json').write_text(json.dumps({'services': {
                'demo.container': {'file': 'demo.container', 'unit': 'demo.service'}}}))
            text = model.generated_units(root)['demo.service']
            self.assertIn('Wants=cold.service\nWants=\n', text)
            (root / 'cold.service').write_text(
                '[Unit]\nDefaultDependencies=no\n[Service]\nExecStart=/usr/bin/true\n')
            dump = self.offline_unit_dump(root, text)
            self.assertRegex(dump, r'(?m)^\s*Wants: cold\.service \(origin-file\)')
            self.assertEqual(model.direct_dependencies(text), ['cold.service'])

    def test_ambiguous_and_conditional_edges_fail_closed(self):
        for text in ['[Unit]\nWants=worker@%i.service', '[Unit]\nRequires="quoted.service"',
                     '[Unit]\nWants=first.service \\\n second.service',
                     '[Unit]\nOnFailure=alert.service', '[Unit]\nOnSuccess=followup.service',
                     '[Unit]\nConflicts=other.service', '[Unit]\nPropagatesStopTo=child.service',
                     '[Service]\nType=dbus']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                model.direct_dependencies(text)

    def test_generator_failure_partial_output_and_unavailability_fail_closed(self):
        outcomes = [SimpleNamespace(returncode=1, stdout=''),
                    SimpleNamespace(returncode=0, stdout='---forgejo.service---\n[Unit]\n'),
                    SimpleNamespace(returncode=0, stdout=''),
                    OSError('missing generator'), model.TimeoutExpired(model.GENERATOR, 30)]
        for outcome in outcomes:
            with self.subTest(outcome=outcome):
                failure = outcome if isinstance(outcome, Exception) else None
                with patch.object(model, 'generate', side_effect=failure, return_value=outcome), self.assertRaises(ValueError):
                    model.generated_units(REPO)

if __name__ == '__main__':
    unittest.main()
