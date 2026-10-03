#!/usr/bin/env python3
"""Whole-working-tree publication gate. Never print candidate secret bytes."""
import json
import subprocess
from pathlib import Path

VERSION = '1.5.0'


def scan(repo):
    result = subprocess.run(
        ['uvx', '--from', 'detect-secrets==' + VERSION, 'detect-secrets',
         'scan', '--all-files', '--no-verify', '--exclude-files',
         r'(^|/)(\.git|__pycache__)/', '.'],
        cwd=repo, capture_output=True, text=True,
    )
    if result.returncode:
        raise ValueError('Secret scanner failed; publication blocked. Inspect local tool availability.')
    try:
        report = json.loads(result.stdout)
        if not isinstance(report, dict) or report.get('version') != VERSION:
            raise ValueError
        results = report['results']
        if not isinstance(results, dict):
            raise ValueError
        findings = []
        for name, rows in results.items():
            if not isinstance(name, str) or not isinstance(rows, list):
                raise ValueError
            for row in rows:
                if (not isinstance(row, dict)
                        or type(row.get('line_number')) is not int
                        or row['line_number'] < 1
                        or not isinstance(row.get('type'), str)
                        or not row['type']):
                    raise ValueError
                findings.append({'file': name, 'line': row['line_number'], 'type': row['type']})
    except (ValueError, KeyError, TypeError):
        # Do not include raw tool output in diagnostics, even on schema drift.
        raise ValueError('Invalid scanner report; publication blocked.') from None
    return {'scanner': VERSION, 'candidates': len(findings), 'findings': findings}


def main():
    try:
        report = scan(Path(__file__).resolve().parents[1])
    except (ValueError, OSError) as error:
        raise SystemExit(str(error) if isinstance(error, ValueError) else 'Secret scanner unavailable; publication blocked.')
    print(json.dumps(report, indent=2))
    if report['candidates']:
        raise SystemExit('Review candidates privately; do not publish or print matched bytes. No broad baseline exemptions.')


if __name__ == '__main__':
    main()
