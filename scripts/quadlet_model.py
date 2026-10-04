"""Read-only canonical Quadlet compilation and direct systemd activation edges.

Do not infer Podman references here: the installed generator owns their semantics.
"""
import json
import os
import re
from subprocess import run as generate, TimeoutExpired
from pathlib import Path

GENERATOR = '/usr/libexec/podman/quadlet'
ACTIVATION = {('Unit', key) for key in ('Requires', 'Wants', 'BindsTo', 'Upholds')}
ACTIVATION.add(('Service', 'Sockets'))
# These cause conditional activation/disruption, not ordinary start dependencies.
UNSUPPORTED = {('Unit', key) for key in ('OnFailure', 'OnSuccess', 'Conflicts', 'PropagatesStopTo')}
UNIT_NAME = re.compile(r'[A-Za-z0-9_.:@-]+\.(?:service|target|socket|mount|automount|swap|path|timer|slice|scope|device)')

def generated_units(repo):
    repo = Path(repo).resolve()
    manifest = json.loads((repo / 'services.json').read_text())
    files = {p.name for p in (repo / 'quadlets').iterdir() if p.is_file()}
    if files != {v['file'] for v in manifest['services'].values()}:
        raise ValueError('Manifest/source mismatch')
    try:
        result = generate([GENERATOR, '-user', '-dryrun'],
                          env={**os.environ, 'QUADLET_UNIT_DIRS': str(repo / 'quadlets')},
                          capture_output=True, text=True, timeout=30)
    except (OSError, TimeoutExpired) as exc:
        raise ValueError('Canonical Quadlet generation unavailable') from exc
    if result.returncode:
        raise ValueError('Canonical Quadlet generation failed')
    parts = re.split(r'^---([^\n]+\.service)---\s*$', result.stdout, flags=re.M)
    units = {}
    for name, text in zip(parts[1::2], parts[2::2]):
        if name in units or not UNIT_NAME.fullmatch(name):
            raise ValueError('Invalid/duplicate generated unit')
        units[name] = text
    expected = {v['unit'] for v in manifest['services'].values()}
    if set(units) != expected or len(expected) != len(manifest['services']):
        raise ValueError('Canonical generated unit mismatch')
    return units

def direct_dependencies(text):
    """Extract literal direct start edges from generated systemd, not Quadlet.

    Repeated Unit dependency assignments accumulate; empty assignments are no-ops
    (systemd config_parse_unit_deps). Service Sockets also adds Wants/After edges
    without clearing them on empty values (config_parse_service_sockets).
    Ambiguous names/specifiers/escapes fail closed rather than understate effects.
    Ordering, Requisite and PartOf do not pull units into a start transaction.
    Mount path directives belong to the separately verified storage contract.
    """
    section = ''
    values = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(('#', ';')):
            continue
        if line.endswith('\\'):
            raise ValueError('Generated continuations require separate dependency review')
        if line.startswith('[') and line.endswith(']'):
            section = line[1:-1]
            continue
        if '=' not in line:
            continue
        key, value = (part.strip() for part in line.split('=', 1))
        field = (section, key)
        if field == ('Service', 'Type') and value == 'dbus':
            raise ValueError('Implicit D-Bus socket activation requires separate review')
        if field not in ACTIVATION | UNSUPPORTED:
            continue
        if not value:
            # All fields tracked here add edges, not resettable string lists.
            # This also preserves earlier unsupported conditional/stop effects.
            continue
        names = value.split()
        if any(not UNIT_NAME.fullmatch(name) for name in names):
            raise ValueError('Unsupported generated dependency syntax: ' + key)
        values.setdefault(field, set()).update(names)
    if any(values.get(field) for field in UNSUPPORTED):
        raise ValueError('Conditional activation/stop directives require separate review')
    return sorted(set().union(*(values.get(field, set()) for field in ACTIVATION)))
