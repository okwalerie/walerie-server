#!/usr/bin/env python3
"""Validate canonical inputs without changing live systemd units."""
import json,re
from pathlib import Path
from quadlet_model import generated_units,direct_dependencies
repo=Path(__file__).resolve().parents[1];manifest=json.loads((repo/'services.json').read_text());files={p.name for p in (repo/'quadlets').iterdir() if p.is_file()}
expected={v['file'] for v in manifest['services'].values()}
if files!=expected:raise SystemExit('Manifest/source mismatch: '+repr(files^expected))
for key,item in manifest['services'].items():
 if item['state'] not in {'active','paused','retired','unclassified'}:raise SystemExit('Invalid state '+key)
 text=(repo/'quadlets'/item['file']).read_text()
 if re.search(r'(?im)^Environment=',text):raise SystemExit('Inline environment prohibited: '+key)
 if re.search(r'-----BEGIN .*PRIVATE KEY-----|\b(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,})',text):raise SystemExit('Credential-like bytes: '+key)
 for requirement in ['ExecStartPre=/usr/bin/mountpoint -q /mnt/service-data','ExecStartPre=/usr/bin/mountpoint -q %h/.local/share/containers/storage']:
  if requirement not in text:raise SystemExit('Missing fail-closed Podman writer policy '+key)
 if item['file'].endswith('.container') and 'StartLimitBurst=5' not in text:raise SystemExit('Missing bounded restart policy '+key)
if 'ExecStartPre=/usr/bin/mountpoint -q /mnt/service-data' not in (repo/'units/data-dirs.service').read_text():raise SystemExit('Bootstrap must fail closed on missing disk')
generated=generated_units(repo)
for text in generated.values():direct_dependencies(text)
print(json.dumps({'definitions':len(files),'generated_units':len(generated),'manifest_entries':len(expected),'status':'passed'}))
