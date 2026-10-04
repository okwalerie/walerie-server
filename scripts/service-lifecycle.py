#!/usr/bin/env python3
"""Named non-destructive lifecycle changes. Dry-run unless --apply."""
import argparse,datetime,json,os,re,shutil,subprocess
from pathlib import Path
from quadlet_model import generated_units,direct_dependencies
STATES={'active','paused','retired'}
def resolve(manifest,name):
 key=name if name in manifest['services'] else name+'.container'
 if key not in manifest['services']:raise ValueError('Unknown service: '+name)
 item=manifest['services'][key]
 if item['file']!=Path(item['file']).name or not re.fullmatch(r'[a-zA-Z0-9_.@-]+\.service',item['unit']):raise ValueError('Invalid path or unit')
 return key,item

def requirements(text,home):
 return [Path(l.split('=',1)[1].strip().replace('%h',str(home))) for l in text.splitlines() if l.startswith('EnvironmentFile=') and not l.split('=',1)[1].strip().startswith('-')]
def run(*args):subprocess.run(['systemctl','--user',*args],check=True)
def observe(unit):
 p=subprocess.run(['systemctl','--user','show',unit,'-p','ActiveState','-p','UnitFileState','-p','RequiredBy','-p','BoundBy','-p','DropInPaths'],check=True,capture_output=True,text=True)
 return dict(l.split('=',1) for l in p.stdout.splitlines() if '=' in l)

def write_json(path,data):
 tmp=path.with_suffix(path.suffix+'.new');tmp.write_text(json.dumps(data,indent=2)+'\n');os.chmod(tmp,0o600);os.replace(tmp,path)
def event(home,data):
 p=home/'.local/state/walerie-server/lifecycle.jsonl'
 with p.open('a') as f:f.write(json.dumps(data)+'\n')
 os.chmod(p,0o600)
def mask_kind(props):
 state=props.get('UnitFileState','')
 return 'persistent' if state=='masked' else 'runtime' if state=='masked-runtime' else 'unmasked'
def restore_mask(unit,kind):
 # Clear both layers: a persistent mask can hide a runtime mask and vice versa.
 run('unmask',unit);run('--runtime','unmask',unit)
 if kind=='persistent':run('mask',unit)
 elif kind=='runtime':run('--runtime','mask',unit)
def execute(repo,home,name,state,reason,apply=False,redeploy=False,allow_dependencies=False):
 if not apply:return _execute(repo,home,name,state,reason,False,redeploy,allow_dependencies)
 if home!=Path.home():raise ValueError('Live apply only permitted for current home')
 import fcntl
 d=home/'.local/state/walerie-server';d.mkdir(parents=True,exist_ok=True,mode=0o700)
 with (d/'lifecycle.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  return _execute(repo,home,name,state,reason,True,redeploy,allow_dependencies)
def _execute(repo,home,name,state,reason,apply=False,redeploy=False,allow_dependencies=False):
 if state not in STATES:raise ValueError('Invalid state')
 if not reason.strip():raise ValueError('A reason is required')
 mp=repo/'services.json';manifest=json.loads(mp.read_text());key,item=resolve(manifest,name)
 source=repo/'quadlets'/item['file'];target=home/'.config/containers/systemd'/item['file']
 if not source.is_file():raise ValueError('Missing canonical Quadlet')
 text=source.read_text()
 if state=='active':
  missing=[str(p) for p in requirements(text,home) if not p.is_file()]
  if missing:raise ValueError('Missing private environment files: '+', '.join(missing))
 # Dry-runs query the real manager only for the actual current home; fixtures remain isolated.
 props=observe(item['unit']) if home==Path.home() else {}
 # Desired activation comes only from today's canonical generated declaration;
 # old manager edges describe neither first deployment nor changed references.
 deps=direct_dependencies(generated_units(repo)[item['unit']]) if state=='active' else []
 if state=='active' and props.get('DropInPaths'):raise ValueError('Live unit drop-ins require separate canonical dependency review')
 consumers=sorted(set((props.get('RequiredBy','')+' '+props.get('BoundBy','')).split()))
 activation=[];disruption=[]
 if home==Path.home():
  for unit in sorted(set(deps if state=='active' else [])|set(consumers if state!='active' or redeploy else [])):
   running=observe(unit).get('ActiveState')=='active'
   if state=='active' and unit in deps and not running:activation.append(unit)
   if (state!='active' or redeploy) and unit in consumers and running:disruption.append(unit)
 effects=sorted(set(activation+disruption))
 plan={'dependency_activation':activation,'consumer_disruption':disruption,'effects':effects,'service':key,'from':item['state'],'to':state,'unit':item['unit'],'reason':reason,'apply':apply,'redeploy':redeploy,'data':'retained','source':str(source),'target':str(target),'dependencies':deps,'consumers':consumers,'dependency_review_authorized':allow_dependencies}
 print(json.dumps(plan,indent=2))
 if not apply:return plan
 if home!=Path.home():raise ValueError('Live apply only permitted for current home')
 if state=='active' and props.get('ActiveState')=='active' and not redeploy:raise ValueError('Already running: use --redeploy for an explicitly approved named restart')
 if effects and not allow_dependencies:raise ValueError('Dependency/consumer effects require explicit --allow-dependencies review: '+', '.join(effects))
 if state=='active':
  # Every Podman unit type uses graphroot, not only containers.
  for mount in [Path('/mnt/service-data'),home/'.local/share/containers/storage']:
   if subprocess.run(['mountpoint','-q',str(mount)]).returncode:raise ValueError('Required storage mount absent: '+str(mount))
  image=next((l.split('=',1)[1] for l in text.splitlines() if l.startswith('Image=')), '')
  if image.startswith('localhost/') and subprocess.run(['podman','image','exists',image]).returncode:raise ValueError('Local image missing; rebuild before resume: '+image)
 stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ');backup=home/'.local/state/walerie-server'/('transition-'+stamp);backup.mkdir(parents=True,mode=0o700)
 present=target.exists()
 if present:shutil.copy2(target,backup/target.name);os.chmod(backup/target.name,0o600)
 shutil.copy2(mp,backup/'services.json');os.chmod(backup/'services.json',0o600)
 previous_mask=mask_kind(props)
 # An inconsistent paused/retired declaration still requires protection on failure.
 recovery_mask='persistent' if previous_mask=='unmasked' and plan['from'] in {'paused','retired'} else previous_mask
 record={**plan,'at':stamp,'rollback':str(backup),'previous_runtime':props,'previous_mask':previous_mask,'recovery_mask':recovery_mask,'previous_source_present':present,'phase':'prepared'};write_json(backup/'transition.json',record)
 try:
  if state=='active':
   restore_mask(item['unit'],'unmasked');target.parent.mkdir(parents=True,exist_ok=True);tmp=target.with_suffix(target.suffix+'.new');tmp.write_text(text);os.replace(tmp,target)
   run('daemon-reload');run('reset-failed',item['unit']);run('restart' if redeploy else 'start',item['unit'])
   if observe(item['unit']).get('ActiveState')!='active':raise RuntimeError('Named unit did not become active')
  else:
   run('stop',item['unit'])
   if target.exists():target.unlink()
   run('mask',item['unit']);run('daemon-reload');observed=observe(item['unit'])
   if observed.get('ActiveState')!='inactive' or observed.get('UnitFileState')!='masked':raise RuntimeError('Pause verification failed')
  item.update(state=state,classification='confirmed',reason=reason,changed_at=stamp,retire_authorized=state=='retired',observed=observe(item['unit']))
  # Public manifest contains no sensitive data; preserve its normal readable mode.
  tmp=mp.with_suffix('.new');tmp.write_text(json.dumps(manifest,indent=2)+'\n');os.replace(tmp,mp)
  record['phase']='completed';write_json(backup/'transition.json',record);event(home,record)
 except Exception as exc:
  recovery_errors=[]
  # Attempt each restoration independently; never auto-start old stateful data.
  def recover(label,action):
   try:action()
   except Exception as e:
    recovery_errors.append(type(e).__name__+' '+label)
    record['recovery_verified']=False
  def restore_source():
   if present:shutil.copy2(backup/target.name,target)
   elif target.exists():target.unlink()
  recover('stopping unit',lambda:run('stop',item['unit']))
  recover('restoring source',restore_source)
  recover('restoring mask',lambda:restore_mask(item['unit'],recovery_mask))
  recover('restoring manifest',lambda:shutil.copy2(backup/'services.json',mp))
  recover('reloading manager',lambda:run('daemon-reload'))
  def verify_source():
   if target.exists()!=present or (present and target.read_bytes()!=(backup/target.name).read_bytes()):raise RuntimeError('Source mismatch')
  def verify_manifest():
   if mp.read_bytes()!=(backup/'services.json').read_bytes():raise RuntimeError('Manifest mismatch')
  def verify_runtime():
   observed=observe(item['unit']);record['recovery_observed']=observed
   if 'UnitFileState' not in observed or mask_kind(observed)!=recovery_mask or observed.get('ActiveState')!='inactive':raise RuntimeError('Runtime mismatch')
  recover('verifying restored source',verify_source)
  recover('verifying restored manifest',verify_manifest)
  recover('verifying restored mask/inactive state',verify_runtime)
  record.update(phase='failed',failure=type(exc).__name__,recovery_errors=recovery_errors,recovery_verified=not recovery_errors)
  recover('writing failed transition record',lambda:write_json(backup/'transition.json',record))
  audit_errors=len(recovery_errors)
  recover('writing failed audit event',lambda:event(home,record))
  # An append may succeed before its writer raises. Correct it when possible.
  if len(recovery_errors)>audit_errors:recover('writing corrective failed audit event',lambda:event(home,record))
  # Persist audit failures too when the record writer remains available.
  if recovery_errors:
   record['recovery_verified']=False
   recover('writing recovery errors',lambda:write_json(backup/'transition.json',record))
  raise RuntimeError('Transition failed; prior declaration/mask restoration attempted; no data rollback or auto-start. Inspect '+str(backup)+'; recovery errors '+repr(recovery_errors)) from exc
 return plan
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('service');p.add_argument('state',choices=sorted(STATES));p.add_argument('--reason',required=True);p.add_argument('--apply',action='store_true');p.add_argument('--redeploy',action='store_true');p.add_argument('--allow-dependencies',action='store_true');p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);a=p.parse_args();execute(a.repo,Path.home(),a.service,a.state,a.reason,a.apply,a.redeploy,a.allow_dependencies)
if __name__=='__main__':main()
