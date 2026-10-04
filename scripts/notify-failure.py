#!/usr/bin/env python3
"""No-LLM, allowlisted-unit maintenance alert; never send journals or config."""
import argparse,datetime,json,os,re,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('unit');p.add_argument('--dry-run',action='store_true');a=p.parse_args()
if not re.fullmatch(r'[A-Za-z0-9_.@-]{1,180}',a.unit):raise SystemExit('Invalid unit identifier')
message='Waler maintenance alert: '+a.unit+' failed. Inspect its systemd status and private recovery log. No automatic destructive retry was performed.'
if a.dry_run:print(message);raise SystemExit(0)
d=Path.home()/'.local/state/walerie-server/alerts';d.mkdir(parents=True,exist_ok=True,mode=0o700);receipt=d/(a.unit+'.json');now=datetime.datetime.now(datetime.timezone.utc)
if receipt.exists():
 previous=json.loads(receipt.read_text());age=(now-datetime.datetime.fromisoformat(previous['at'])).total_seconds()
 if previous.get('sent') and 0<=age<3600:print('Duplicate alert suppressed');raise SystemExit(0)
r=subprocess.run([str(Path.home()/'.local/bin/hermes'),'send','--to','telegram:235941010','--quiet',message],capture_output=True,text=True,timeout=90)
tmp=receipt.with_suffix('.new');tmp.write_text(json.dumps({'unit':a.unit,'at':now.isoformat(),'sent':r.returncode==0,'exit_code':r.returncode})+'\n');os.chmod(tmp,0o600);os.replace(tmp,receipt)
if r.returncode:raise SystemExit('Alert delivery failed; private marker retained; inspect sender independently')
print('Maintenance alert sent without model invocation')
