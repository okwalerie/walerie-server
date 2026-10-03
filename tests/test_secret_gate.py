"""Offline scanner-contract tests; no online verification or live state writes."""
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('secret_gate', Path(__file__).resolve().parents[1] / 'scripts/check-secrets.py')
assert spec is not None and spec.loader is not None
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class SecretGateTests(unittest.TestCase):
    def scan(self, data, returncode=0):
        output = data if isinstance(data, str) else json.dumps(data)
        result = subprocess.CompletedProcess([], returncode, output, 'private diagnostic fixture')
        with patch.object(gate.subprocess, 'run', return_value=result) as run:
            report = gate.scan(Path('/source'))
        args = run.call_args.args[0]
        self.assertIn('detect-secrets==1.5.0', args)
        self.assertIn('--all-files', args)
        self.assertIn('--no-verify', args)
        self.assertEqual(args[-1], '.')
        self.assertEqual(run.call_args.kwargs['cwd'], Path('/source'))
        return report

    def test_empty_valid_scan(self):
        self.assertEqual(self.scan({'version': '1.5.0', 'results': {}}),
                         {'scanner': '1.5.0', 'candidates': 0, 'findings': []})

    def test_candidate_metadata_only(self):
        report = self.scan({'version': '1.5.0', 'results': {
            'source.py': [{'line_number': 2, 'type': 'fixture', 'untrusted_payload': 'never-display-fixture'}]}})
        self.assertEqual(report['findings'], [{'file': 'source.py', 'line': 2, 'type': 'fixture'}])
        self.assertNotIn('never-display-fixture', json.dumps(report))

    def test_tool_failure_blocks_without_output(self):
        with self.assertRaisesRegex(ValueError, 'Secret scanner failed') as error:
            self.scan('private-output-fixture', returncode=1)
        self.assertNotIn('private-output-fixture', str(error.exception))

    def test_malformed_or_drifted_report_blocks(self):
        for report in ['private-output-fixture', [], {},
                       {'version': '2.0', 'results': {}},
                       {'version': '1.5.0', 'results': []},
                       {'version': '1.5.0', 'results': {'source.py': None}},
                       {'version': '1.5.0', 'results': {'source.py': [{}]}},
                       {'version': '1.5.0', 'results': {'source.py': [{'line_number': True, 'type': 'fixture'}]}},
                       {'version': '1.5.0', 'results': {'source.py': [{'line_number': 0, 'type': 'fixture'}]}}]:
            with self.subTest(report=report), self.assertRaisesRegex(ValueError, 'Invalid scanner report'):
                self.scan(report)


if __name__ == '__main__':
    unittest.main()
