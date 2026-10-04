#!/usr/bin/env python3
"""Publish only allowlisted lifecycle/health fields; never configuration or secrets."""
import argparse,datetime,html,json,os,re,subprocess
from pathlib import Path

def atom(path,text):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.new');tmp.write_text(text);os.replace(tmp,path)
def collect(repo):
 manifest=json.loads((repo/'services.json').read_text());rows=[]
 for name,item in sorted(manifest['services'].items()):
  unit=item['unit']
  if not re.fullmatch(r'[a-zA-Z0-9_.@-]+\.service',unit):raise ValueError('Invalid unit')
  p=subprocess.run(['systemctl','--user','show',unit,'-p','ActiveState','-p','UnitFileState','-p','NRestarts'],capture_output=True,text=True,timeout=10)
  props=dict(l.split('=',1) for l in p.stdout.splitlines() if '=' in l)
  rows.append({'name':name,'expected':item['state'],'classification':item.get('classification','confirmed'),'observed':props.get('ActiveState','unknown'),'mask':props.get('UnitFileState','unknown'),'restarts':int(props.get('NRestarts','0'))})
 mounts={label:subprocess.run(['mountpoint','-q',str(path)]).returncode==0 for label,path in [('external_service_data',Path('/mnt/service-data')),('podman_storage_bind',Path.home()/'.local/share/containers/storage')]}
 return {'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mounts':mounts,'services':rows}
def publish(repo,out):
 data=collect(repo);esc=html.escape
 rows=''.join('<tr>'+''.join('<td>'+esc(str(r[k]))+'</td>' for k in ['name','expected','classification','observed','mask','restarts'])+'</tr>' for r in data['services'])
 page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><meta http-equiv="refresh" content="300"><title>Waler service lifecycle</title><style>body{font:16px system-ui;max-width:1100px;margin:2rem auto;padding:1rem;background:#101826;color:#eee}table{border-collapse:collapse;width:100%}td,th{padding:.5rem;text-align:left;border-bottom:1px solid #405067}a{color:#8ad}</style><h1>Waler service lifecycle</h1><p>Generated: '+esc(data['generated_at'])+'</p><p>External service drive: '+str(data['mounts']['external_service_data'])+' · Podman storage bind: '+str(data['mounts']['podman_storage_bind'])+'</p><p>Provisional classifications are captured observations, not authorization to retire services. A running process does not prove application health or backup coverage.</p><table><thead><tr><th>Definition</th><th>Expected</th><th>Classification</th><th>Observed</th><th>Startup</th><th>Restarts</th></tr></thead><tbody>'+rows+'</tbody></table><p><a href="server-lifecycle.json">JSON</a> · <a href="https://github.com/okwalerie/walerie-server">Canonical declarations</a></p></html>'
 page=page.replace('<h1>Waler service lifecycle</h1>','<h1>Waler service lifecycle</h1><p id="freshness" role="alert"></p>')
 page+='<script>const observedAt='+json.dumps(data['generated_at'])+';function freshness(){const stale=Date.now()-Date.parse(observedAt)>720000;document.getElementById("freshness").textContent=stale?"STALE OBSERVATIONS — do not assume storage or services are healthy. Check the independent host monitor.":"Observations are recent (not proof of application health).";}freshness();setInterval(freshness,10000);</script>'
 atom(out/'server-lifecycle.json',json.dumps(data,indent=2)+'\n');atom(out/'server-lifecycle.html',page)
 proof=Path.home()/'.local/state/walerie-server/status-proof.json';atom(proof,json.dumps({'generated_at':data['generated_at'],'mounts':data['mounts']})+'\n');os.chmod(proof,0o600)
 print(json.dumps({'services':len(data['services']),'mounts':data['mounts'],'out':str(out)}))
def verify_fresh():
 proof=Path.home()/'.local/state/walerie-server/status-proof.json'
 d=json.loads(proof.read_text());at=datetime.datetime.fromisoformat(d['generated_at']);age=(datetime.datetime.now(datetime.timezone.utc)-at).total_seconds()
 if age<0 or age>720:raise RuntimeError('Lifecycle publication stale; inspect publisher and storage mounts')
 for path in [Path('/mnt/service-data'),Path.home()/'.local/share/containers/storage']:
  if subprocess.run(['mountpoint','-q',str(path)]).returncode:raise RuntimeError('Required storage mount absent')
 print('Lifecycle publication fresh; current storage mounts present')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--out',type=Path);p.add_argument('--verify-fresh',action='store_true');a=p.parse_args()
 if a.verify_fresh:verify_fresh()
 elif a.out:publish(a.repo,a.out)
 else:p.error('--out or --verify-fresh is required')