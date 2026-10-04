import importlib.util,json,tempfile,unittest,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
spec=importlib.util.spec_from_file_location('lifecycle',Path(__file__).parents[1]/'scripts/service-lifecycle.py');assert spec is not None and spec.loader is not None
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class LifecycleTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.repo=self.root/'repo';self.home=self.root/'home';(self.repo/'quadlets').mkdir(parents=True);self.home.mkdir()
  self.manifest={'services':{'demo.container':{'file':'demo.container','unit':'demo.service','state':'active'}}};self.mp=self.repo/'services.json';self.mp.write_text(json.dumps(self.manifest));self.source=self.repo/'quadlets/demo.container';self.source.write_text('[Quadlet]\nDefaultDependencies=false\n[Container]\nImage=example.invalid/demo:1\nEnvironmentFile=%h/private.env\n');self.target=self.home/'.config/containers/systemd/demo.container'
 def tearDown(self):self.tmp.cleanup()
 def provision(self):(self.home/'private.env').write_text('KEY=value')
 def test_pause_dryrun_retains_everything(self):
  before=self.mp.read_bytes();p=m.execute(self.repo,self.home,'demo','paused','maintenance');self.assertFalse(p['apply']);self.assertEqual(before,self.mp.read_bytes());self.assertTrue(self.source.exists())
 def test_retire_dryrun_does_not_delete_data(self):
  d=self.home/'precious';d.write_text('keep');m.execute(self.repo,self.home,'demo','retired','ended');self.assertEqual(d.read_text(),'keep')
 def test_resume_requires_private_environment(self):
  with self.assertRaisesRegex(ValueError,'Missing private'):m.execute(self.repo,self.home,'demo','active','resume')
 def test_resume_plan_with_provisioned_environment(self):
  self.provision();self.assertEqual(m.execute(self.repo,self.home,'demo','active','resume')['to'],'active')
 def test_unknown_service_rejected(self):
  with self.assertRaises(ValueError):m.execute(self.repo,self.home,'../demo','paused','why')
 def test_path_traversal_rejected(self):
  self.manifest['services']['demo.container']['file']='../bad';self.mp.write_text(json.dumps(self.manifest))
  with self.assertRaises(ValueError):m.execute(self.repo,self.home,'demo','paused','why')
 def test_reason_required(self):
  with self.assertRaises(ValueError):m.execute(self.repo,self.home,'demo','paused','')
 def test_live_apply_refuses_other_home(self):
  with self.assertRaisesRegex(ValueError,'current home'):m.execute(self.repo,self.home,'demo','paused','why',True)
 def test_apply_pause_saves_original_and_records_state(self):
  self.target.parent.mkdir(parents=True);self.target.write_text('private original');calls=[]
  with patch.object(m.Path,'home',return_value=self.home),patch.object(m,'run',side_effect=lambda *a:calls.append(a)),patch.object(m,'observe',return_value={'ActiveState':'inactive','UnitFileState':'masked'}):
   m.execute(self.repo,self.home,'demo','paused','maintenance',True)
  self.assertFalse(self.target.exists());self.assertTrue(self.source.exists());self.assertIn(('mask','demo.service'),calls)
  saved=list((self.home/'.local/state/walerie-server').glob('transition-*/demo.container'));self.assertEqual(len(saved),1);self.assertEqual(saved[0].read_text(),'private original');self.assertEqual(saved[0].stat().st_mode & 0o777,0o600)
  self.assertEqual(json.loads(self.mp.read_text())['services']['demo.container']['state'],'paused')
 def test_apply_resume_provisions_only_named_target(self):
  self.provision();calls=[]
  with patch.object(m.Path,'home',return_value=self.home),patch.object(m,'run',side_effect=lambda *a:calls.append(a)),patch.object(m,'observe',side_effect=[{'ActiveState':'inactive'},{'ActiveState':'active'},{'ActiveState':'active'}]),patch.object(m.subprocess,'run',return_value=SimpleNamespace(returncode=0)):
   m.execute(self.repo,self.home,'demo','active','reviewed recovery',True)
  self.assertEqual(self.target.read_text(),self.source.read_text());self.assertIn(('start','demo.service'),calls)
 def test_missing_mount_blocks_before_change(self):
  self.provision();before=self.mp.read_bytes()
  with patch.object(m.Path,'home',return_value=self.home),patch.object(m,'observe',return_value={'ActiveState':'inactive'}),patch.object(m.subprocess,'run',return_value=SimpleNamespace(returncode=1)):
   with self.assertRaisesRegex(ValueError,'storage mount absent'):m.execute(self.repo,self.home,'demo','active','reviewed recovery',True)
  self.assertEqual(before,self.mp.read_bytes());self.assertFalse(self.target.exists())
 def test_existing_active_requires_explicit_redeploy(self):
  self.provision()
  with patch.object(m.Path,'home',return_value=self.home),patch.object(m,'observe',return_value={'ActiveState':'active'}):
   with self.assertRaisesRegex(ValueError,'Already running'):m.execute(self.repo,self.home,'demo','active','reviewed recovery',True)
 def test_explicit_redeploy_restarts_named_unit(self):
  self.provision();calls=[]
  with patch.object(m.Path,'home',return_value=self.home),patch.object(m,'run',side_effect=lambda *a:calls.append(a)),patch.object(m,'observe',return_value={'ActiveState':'active'}),patch.object(m.subprocess,'run',return_value=SimpleNamespace(returncode=0)):
   m.execute(self.repo,self.home,'demo','active','approved redeploy',True,True)
  self.assertIn(('restart','demo.service'),calls);self.assertNotIn(('start','demo.service'),calls)
 def test_failed_resume_restores_pause_and_audits(self):
  self.provision();self.manifest['services']['demo.container']['state']='paused';self.mp.write_text(json.dumps(self.manifest));before=self.mp.read_bytes();calls=[]
  def fake(*a):
   calls.append(a)
   if a[0]=='start':raise RuntimeError('injected start failure')
  with patch.object(m.Path,'home',return_value=self.home),patch.object(m,'run',side_effect=fake),patch.object(m,'observe',return_value={'ActiveState':'inactive','UnitFileState':'masked'}),patch.object(m.subprocess,'run',return_value=SimpleNamespace(returncode=0)):
   with self.assertRaisesRegex(RuntimeError,'Transition failed'):m.execute(self.repo,self.home,'demo','active','reviewed recovery',True)
  self.assertFalse(self.target.exists());self.assertTrue(self.source.exists());self.assertEqual(before,self.mp.read_bytes());self.assertIn(('mask','demo.service'),calls)
  records=list((self.home/'.local/state/walerie-server').glob('transition-*/transition.json'));self.assertEqual(json.loads(records[0].read_text())['phase'],'failed')
 def test_dependency_activation_requires_review(self):
  self.provision();self.source.write_text(self.source.read_text()+'[Unit]\nRequires=database.service\n')
  with patch.object(m.Path,'home',return_value=self.home),patch.object(m,'observe',return_value={'ActiveState':'inactive'}):
   with self.assertRaisesRegex(ValueError,'Dependency/consumer'):m.execute(self.repo,self.home,'demo','active','resume',True)
 def test_wants_only_activation_is_refused_before_mutation(self):
  self.provision();self.source.write_text('[Unit]\nWants=database.service\n[Container]\nImage=example.invalid/demo:1\n')
  before=self.mp.read_bytes()
  with patch.object(m.Path,'home',return_value=self.home),patch.object(m,'observe',side_effect=lambda u:{'ActiveState':'inactive' if u in {'demo.service','database.service'} else 'active'}),patch.object(m,'run') as run:
   plan=m.execute(self.repo,self.home,'demo','active','preview')
   self.assertEqual(plan['dependency_activation'],['database.service'])
   with self.assertRaisesRegex(ValueError,'--allow-dependencies'):m.execute(self.repo,self.home,'demo','active','resume',True)
   run.assert_not_called()
  self.assertEqual(self.mp.read_bytes(),before);self.assertFalse(self.target.exists())
 def test_network_first_deploy_is_refused_before_mutation(self):
  self.provision();self.source.write_text('[Container]\nImage=example.invalid/demo:1\nNetwork=demo.network\n');(self.repo/'quadlets/demo.network').write_text('[Network]\nNetworkName=demo\n')
  self.manifest['services']['demo.network']={'file':'demo.network','unit':'demo-network.service','state':'active'};self.mp.write_text(json.dumps(self.manifest));before=self.mp.read_bytes()
  with patch.object(m.Path,'home',return_value=self.home),patch.object(m,'observe',side_effect=lambda u:{'ActiveState':'inactive' if u in {'demo.service','demo-network.service'} else 'active'}),patch.object(m,'run') as run:
   plan=m.execute(self.repo,self.home,'demo','active','preview')
   self.assertEqual(plan['dependency_activation'],['demo-network.service'])
   with self.assertRaisesRegex(ValueError,'--allow-dependencies'):m.execute(self.repo,self.home,'demo','active','resume',True)
   run.assert_not_called()
  self.assertEqual(self.mp.read_bytes(),before);self.assertFalse(self.target.exists())
 def activation_fixture(self,network=False,redeploy=False,empty_wants=False):
  dependency='new-network.service' if network else 'database.service'
  self.source.write_text('[Unit]\n'+('' if network else 'Wants=database.service\n'+('Wants=\n' if empty_wants else ''))+'[Container]\nImage=example.invalid/demo:1\n'+('Network=new.network\n' if network else ''))
  if network:
   (self.repo/'quadlets/new.network').write_text('[Network]\nNetworkName=new\n')
   self.manifest['services']['new.network']={'file':'new.network','unit':'new-network.service','state':'active'};self.mp.write_text(json.dumps(self.manifest))
  calls=[];active=redeploy
  if redeploy:self.target.parent.mkdir(parents=True);self.target.write_text('[Container]\nImage=example.invalid/demo:1\nNetwork=old.network\n')
  before=self.mp.read_bytes();previous=self.target.read_bytes() if self.target.exists() else None
  def observed(unit):
   if unit=='demo.service':return {'ActiveState':'active' if active else 'inactive','Requires':'old-network.service','Wants':'obsolete.service'}
   return {'ActiveState':'inactive' if unit==dependency else 'active'}
  def command(*args):
   nonlocal active
   calls.append(args)
   if args[0] in {'start','restart'}:active=True
  with patch.object(m.Path,'home',return_value=self.home),patch.object(m,'observe',side_effect=observed),patch.object(m,'run',side_effect=command),patch.object(m.subprocess,'run',return_value=SimpleNamespace(returncode=0)):
   preview=m.execute(self.repo,self.home,'demo','active','preview',False,redeploy)
   self.assertEqual(preview['dependency_activation'],[dependency]);self.assertNotIn('old-network.service',preview['dependencies']);self.assertNotIn('obsolete.service',preview['dependencies'])
   with self.assertRaisesRegex(ValueError,'--allow-dependencies'):m.execute(self.repo,self.home,'demo','active','unreviewed',True,redeploy)
   self.assertEqual(calls,[]);self.assertEqual(self.mp.read_bytes(),before);self.assertEqual(self.target.read_bytes() if self.target.exists() else None,previous)
   self.assertFalse(list((self.home/'.local/state/walerie-server').glob('transition-*')))
   plan=m.execute(self.repo,self.home,'demo','active','reviewed',True,redeploy,True)
  self.assertEqual(plan['dependency_activation'],[dependency]);self.assertEqual(plan['effects'],[dependency]);self.assertTrue(plan['dependency_review_authorized'])
  self.assertEqual([c for c in calls if c[0] in {'start','restart'}],[('restart' if redeploy else 'start','demo.service')]);self.assertFalse(any(dependency in c for c in calls));self.assertEqual(self.target.read_text(),self.source.read_text())
 def test_generated_empty_wants_requires_authorization_and_only_starts_named_unit(self):self.activation_fixture(empty_wants=True)
 def test_generated_empty_wants_redeploy_requires_authorization_and_only_restarts_named_unit(self):self.activation_fixture(redeploy=True,empty_wants=True)
 def test_authorized_wants_resume_only_starts_named_unit(self):self.activation_fixture()
 def test_authorized_network_first_deploy_only_starts_named_unit(self):self.activation_fixture(network=True)
 def test_changed_network_redeploy_reviews_new_not_old_edge(self):self.activation_fixture(network=True,redeploy=True)
 def test_generated_wants_from_canonical_nextcloud_gate_cold_database(self):
  canonical=Path(__file__).parents[1]
  self.source.write_text((canonical/'quadlets/nextcloud-app.container').read_text())
  self.manifest['services']={'nextcloud-app.container':{'file':'demo.container','unit':'demo.service','state':'paused'}}
  for name in ['nextcloud-pod.pod','nextcloud-db.container','nextcloud-redis.container']:
   (self.repo/'quadlets'/name).write_text((canonical/'quadlets'/name).read_text())
   self.manifest['services'][name]=json.loads((canonical/'services.json').read_text())['services'][name]
  self.mp.write_text(json.dumps(self.manifest));calls=[];active=False
  def observed(unit):return {'ActiveState':'inactive' if unit=='nextcloud-db.service' or (unit=='demo.service' and not active) else 'active'}
  def command(*args):
   nonlocal active
   calls.append(args)
   if args[0]=='start':active=True
  with patch.object(m.Path,'home',return_value=self.home),patch.object(m,'requirements',return_value=[]),patch.object(m,'observe',side_effect=observed),patch.object(m,'run',side_effect=command),patch.object(m.subprocess,'run',return_value=SimpleNamespace(returncode=0)):
   preview=m.execute(self.repo,self.home,'nextcloud-app.container','active','cold database preview')
   self.assertEqual(preview['dependency_activation'],['nextcloud-db.service']);self.assertIn('nextcloud-redis.service',preview['dependencies'])
   with self.assertRaisesRegex(ValueError,'--allow-dependencies'):m.execute(self.repo,self.home,'nextcloud-app.container','active','refuse cold bootstrap',True)
   self.assertEqual(calls,[])
   plan=m.execute(self.repo,self.home,'nextcloud-app.container','active','isolated authorization',True,False,True)
  self.assertEqual(plan['effects'],['nextcloud-db.service']);self.assertIn(('start','demo.service'),calls);self.assertFalse(any('nextcloud-db.service' in c for c in calls))
 def test_generation_failure_refuses_before_mutation(self):
  quadlet_model=sys.modules['quadlet_model']
  self.provision();before=self.mp.read_bytes()
  with patch.object(m.Path,'home',return_value=self.home),patch.object(m,'observe',return_value={'ActiveState':'inactive'}),patch.object(m,'run') as run,patch.object(quadlet_model,'generate',return_value=SimpleNamespace(returncode=0,stdout='')):
   with self.assertRaisesRegex(ValueError,'generated unit mismatch'):m.execute(self.repo,self.home,'demo','active','missing output',True)
   run.assert_not_called()
  self.assertEqual(self.mp.read_bytes(),before);self.assertFalse(self.target.exists())
 def test_live_dropins_fail_closed_before_mutation(self):
  self.provision()
  with patch.object(m.Path,'home',return_value=self.home),patch.object(m,'observe',return_value={'ActiveState':'inactive','DropInPaths':'/some/override.conf'}),patch.object(m,'run') as run:
   with self.assertRaisesRegex(ValueError,'drop-ins'):m.execute(self.repo,self.home,'demo','active','unknown overlay',True,False,True)
   run.assert_not_called()
 def test_consumer_stop_requires_review(self):
  with patch.object(m.Path,'home',return_value=self.home),patch.object(m,'observe',side_effect=[{'ActiveState':'active','RequiredBy':'consumer.service'},{'ActiveState':'active'}]):
   with self.assertRaisesRegex(ValueError,'Dependency/consumer'):m.execute(self.repo,self.home,'demo','paused','maintenance',True)
 def pause_failure(self,stage,previous='generated',present=True,restore_fault=None,old_state='active'):
  self.manifest['services']['demo.container']['state']=old_state;self.mp.write_text(json.dumps(self.manifest));before=self.mp.read_bytes()
  self.target.parent.mkdir(parents=True,exist_ok=True)
  if present:self.target.write_text('fixture original')
  calls=[];runtime={'ActiveState':'active','UnitFileState':previous};fired=False
  real_replace=m.os.replace;real_write=m.write_json;real_event=m.event;real_copy=m.shutil.copy2
  def fail(point):
   nonlocal fired
   if point==stage and not fired:fired=True;raise OSError('injected '+point)
  def fake_run(*args):
   calls.append(args);command=args[1] if args[0]=='--runtime' else args[0]
   if command=='stop':runtime['ActiveState']='inactive'
   if command=='mask':runtime['UnitFileState']='masked-runtime' if args[0]=='--runtime' else 'masked';fail('mask')
   if command=='unmask':
    if restore_fault=='mask-command':raise OSError('injected restoration failure')
    if restore_fault!='mask-readback':runtime['UnitFileState']='generated'
   if command=='daemon-reload':
    fail('reload')
    if fired and restore_fault=='reload':raise OSError('injected restore reload failure')
  def observed(unit):
   nonlocal fired
   # Verification failure is an observed mismatch after the mask mutation.
   if stage=='verification' and ('mask','demo.service') in calls and not fired:
    fired=True
    return {'ActiveState':'active','UnitFileState':'masked'}
   if fired and restore_fault=='missing-mask-readback':return {'ActiveState':runtime['ActiveState']}
   return dict(runtime)
  def replace(src,dst):
   real_replace(src,dst)
   if dst==self.mp:fail('manifest')
  def write(path,data):
   if data.get('phase')=='completed':fail('record')
   return real_write(path,data)
  def audit(home,data):
   if data.get('phase')=='completed':fail('audit')
   return real_event(home,data)
  def copy(src,dst):
   restoring=Path(src).parent.name.startswith('transition-')
   if restoring and ((dst==self.target and restore_fault=='source') or (dst==self.mp and restore_fault=='manifest')):raise OSError('injected restore copy failure')
   return real_copy(src,dst)
  with patch.object(m.Path,'home',return_value=self.home),patch.object(m,'run',side_effect=fake_run),patch.object(m,'observe',side_effect=observed),patch.object(m.os,'replace',side_effect=replace),patch.object(m,'write_json',side_effect=write),patch.object(m,'event',side_effect=audit),patch.object(m.shutil,'copy2',side_effect=copy):
   with self.assertRaisesRegex(RuntimeError,'Transition failed'):m.execute(self.repo,self.home,'demo','paused','injected maintenance',True)
  self.assertTrue(fired);self.assertFalse(any(c[0] in {'start','restart'} for c in calls))
  record=json.loads(sorted((self.home/'.local/state/walerie-server').glob('transition-*/transition.json'))[-1].read_text())
  self.assertEqual(record['phase'],'failed');self.assertEqual(record['previous_mask'],m.mask_kind({'UnitFileState':previous}))
  if not restore_fault:
   self.assertEqual(self.mp.read_bytes(),before);self.assertEqual(self.target.exists(),present)
   if present:self.assertEqual(self.target.read_text(),'fixture original')
   expected=previous if previous.startswith('masked') else 'masked' if old_state in {'paused','retired'} else 'generated'
   self.assertEqual(runtime['UnitFileState'],expected);self.assertEqual(record['recovery_errors'],[]);self.assertTrue(record['recovery_verified'])
  else:self.assertFalse(record['recovery_verified']);self.assertTrue(record['recovery_errors'])
  self.assertEqual(record['recovery_observed']['ActiveState'],'inactive')
  audit_data=json.loads((self.home/'.local/state/walerie-server/lifecycle.jsonl').read_text().splitlines()[-1]);self.assertEqual(audit_data['phase'],'failed');self.assertEqual(audit_data['recovery_verified'],record['recovery_verified'])
  self.assertEqual(sorted((self.home/'.local/state/walerie-server').glob('transition-*/transition.json'))[-1].stat().st_mode & 0o777,0o600)
  self.assertEqual((self.home/'.local/state/walerie-server/lifecycle.jsonl').stat().st_mode & 0o777,0o600)
  return record
 def test_failed_pause_restores_each_previous_mask_at_each_failure_stage(self):
  for previous in ['generated','masked','masked-runtime']:
   for stage in ['mask','reload','verification','manifest','record','audit']:
    with self.subTest(previous=previous,stage=stage):
     self.pause_failure(stage,previous)
 def test_failed_pause_restores_absent_source(self):self.pause_failure('audit',present=False)
 def test_failed_pause_preserves_inconsistent_paused_protection(self):
  for state in ['paused','retired']:
   with self.subTest(state=state):self.pause_failure('reload',old_state=state)
 def test_restore_failures_are_audited_and_fail_readback(self):
  for fault in ['mask-command','mask-readback','missing-mask-readback','source','manifest','reload']:
   with self.subTest(fault=fault):
    # Source differs after pause; manifest differs after the committed declaration.
    record=self.pause_failure('manifest',restore_fault=fault)
    if fault in {'mask-readback','source','manifest'}:self.assertTrue(any('verifying restored' in e for e in record['recovery_errors']))
 def resume_fixture(self,persistent=False,runtime_mask=False,fail_start=False):
  self.provision();self.manifest['services']['demo.container']['state']='paused';self.mp.write_text(json.dumps(self.manifest));before=self.mp.read_bytes();calls=[]
  layers={'persistent':persistent,'runtime':runtime_mask};active='inactive'
  def observed(unit):return {'ActiveState':active,'UnitFileState':'masked' if layers['persistent'] else 'masked-runtime' if layers['runtime'] else 'generated'}
  def fake(*args):
   nonlocal active
   calls.append(args);runtime=args[0]=='--runtime';command=args[1] if runtime else args[0]
   if command in {'mask','unmask'}:layers['runtime' if runtime else 'persistent']=command=='mask'
   if command=='stop':active='inactive'
   if command in {'start','restart'}:
    if any(layers.values()):raise OSError('unit remains masked')
    if fail_start:raise OSError('injected start failure')
    active='active'
  with patch.object(m.Path,'home',return_value=self.home),patch.object(m,'run',side_effect=fake),patch.object(m,'observe',side_effect=observed),patch.object(m.subprocess,'run',return_value=SimpleNamespace(returncode=0)):
   if fail_start:
    with self.assertRaisesRegex(RuntimeError,'Transition failed'):m.execute(self.repo,self.home,'demo','active','resume',True)
   else:m.execute(self.repo,self.home,'demo','active','resume',True)
  record_path=next((self.home/'.local/state/walerie-server').glob('transition-*/transition.json'));record=json.loads(record_path.read_text())
  self.assertEqual(record_path.stat().st_mode & 0o777,0o600)
  if fail_start:
   self.assertEqual(self.mp.read_bytes(),before);self.assertFalse(self.target.exists());self.assertEqual(active,'inactive');self.assertTrue(record['recovery_verified']);self.assertEqual(calls.count(('start','demo.service')),1);self.assertNotIn(('restart','demo.service'),calls)
   self.assertEqual(layers,{'persistent':persistent,'runtime':runtime_mask})
  else:
   self.assertEqual(active,'active');self.assertEqual(layers,{'persistent':False,'runtime':False});self.assertEqual(record['phase'],'completed');self.assertEqual(self.target.read_text(),self.source.read_text());self.assertEqual(json.loads(self.mp.read_text())['services']['demo.container']['state'],'active')
  return calls
 def test_successful_resume_clears_persistent_runtime_and_both_mask_layers(self):
  calls=self.resume_fixture(True,True)
  self.assertLess(calls.index(('unmask','demo.service')),calls.index(('start','demo.service')))
  self.assertLess(calls.index(('--runtime','unmask','demo.service')),calls.index(('start','demo.service')))
 def test_successful_resume_clears_runtime_only_mask(self):self.resume_fixture(runtime_mask=True)
 def test_successful_resume_clears_persistent_only_mask(self):self.resume_fixture(persistent=True)
 def test_failed_resume_restores_runtime_mask_without_starting_again(self):
  calls=self.resume_fixture(runtime_mask=True,fail_start=True)
  self.assertIn(('--runtime','mask','demo.service'),calls)
 def test_failed_resume_restores_persistent_mask_without_starting_again(self):self.resume_fixture(persistent=True,fail_start=True)
 def failed_publication_fixture(self,record_fault=False,audit_fault:bool|str=False,retry_fault=False):
  before=self.mp.read_bytes();calls=[];runtime={'ActiveState':'active','UnitFileState':'generated'};real_write=m.write_json;real_event=m.event;writes=0;audits=0
  def fake(*args):
   calls.append(args);command=args[1] if args[0]=='--runtime' else args[0]
   if command=='stop':runtime['ActiveState']='inactive'
   if command=='mask':runtime['UnitFileState']='masked';raise OSError('injected pause failure')
   if command=='unmask':runtime['UnitFileState']='generated'
  def write(path,data):
   nonlocal writes
   if data['phase']=='failed':
    writes+=1
    if (record_fault and writes==1) or (retry_fault and writes>1):raise OSError('injected failed record publication')
   return real_write(path,data)
  def audit(home,data):
   nonlocal audits
   audits+=1
   if audit_fault and audits==1:
    # A writer can append durable evidence and then fail (e.g. chmod).
    if audit_fault!='before':real_event(home,data)
    raise OSError('injected audit publication')
   if audit_fault and retry_fault and audits>1:raise OSError('injected audit retry failure')
   return real_event(home,data)
  with patch.object(m.Path,'home',return_value=self.home),patch.object(m,'run',side_effect=fake),patch.object(m,'observe',side_effect=lambda unit:dict(runtime)),patch.object(m,'write_json',side_effect=write),patch.object(m,'event',side_effect=audit):
   with self.assertRaisesRegex(RuntimeError,'Transition failed'):m.execute(self.repo,self.home,'demo','paused','publication fault',True)
  self.assertEqual(self.mp.read_bytes(),before);self.assertFalse(self.target.exists());self.assertEqual(runtime,{'ActiveState':'inactive','UnitFileState':'generated'});self.assertFalse(any(c[0] in {'start','restart'} for c in calls))
  record_path=next((self.home/'.local/state/walerie-server').glob('transition-*/transition.json'));record=json.loads(record_path.read_text());audit_path=self.home/'.local/state/walerie-server/lifecycle.jsonl';events=[json.loads(line) for line in audit_path.read_text().splitlines()]
  self.assertEqual(record_path.stat().st_mode & 0o777,0o600);self.assertEqual(audit_path.stat().st_mode & 0o777,0o600)
  if record_fault:
   self.assertTrue(all(not e['recovery_verified'] for e in events));self.assertTrue(all(any('writing failed transition record' in error for error in e['recovery_errors']) for e in events))
  if audit_fault and not retry_fault:
   self.assertGreaterEqual(len(events),1 if audit_fault=='before' else 2);self.assertFalse(events[-1]['recovery_verified']);self.assertIn('OSError writing failed audit event',events[-1]['recovery_errors'])
  if not retry_fault:self.assertEqual(record['phase'],'failed');self.assertFalse(record['recovery_verified'])
  return record,events
 def test_failed_record_publication_invalidates_audit_before_retry(self):self.failed_publication_fixture(record_fault=True)
 def test_failed_record_and_retry_leave_only_nonverified_failed_audit(self):
  record,events=self.failed_publication_fixture(record_fault=True,retry_fault=True)
  self.assertEqual(record['phase'],'prepared');self.assertEqual(len(events),1)
 def test_failed_audit_before_append_retries_with_nonverified_evidence(self):
  record,events=self.failed_publication_fixture(audit_fault='before')
  self.assertTrue(all(not e['recovery_verified'] for e in events))
 def test_partial_failed_audit_publication_gets_corrective_event(self):self.failed_publication_fixture(audit_fault=True)
 def test_failed_publication_retries_do_not_emit_true_after_record_failure(self):self.failed_publication_fixture(record_fault=True,audit_fault=True,retry_fault=True)
 def test_redeploy_effects_gate_and_dryrun(self):
  self.provision();self.source.write_text(self.source.read_text()+'[Unit]\nRequires=database.service shared.service\n');before=self.mp.read_bytes()
  def observed(unit):
   if unit=='demo.service':return {'ActiveState':'active','RequiredBy':'consumer.service shared.service idle.service','BoundBy':'consumer.service','Requires':'database.service shared.service'}
   return {'ActiveState':'active' if unit=='consumer.service' else 'inactive'}
  with patch.object(m.Path,'home',return_value=self.home),patch.object(m,'observe',side_effect=observed),patch.object(m,'run') as run:
   plan=m.execute(self.repo,self.home,'demo','active','redeploy preview',False,True)
   self.assertEqual(plan['dependency_activation'],['database.service','shared.service']);self.assertEqual(plan['consumer_disruption'],['consumer.service']);self.assertEqual(plan['effects'],['consumer.service','database.service','shared.service'])
   with self.assertRaisesRegex(ValueError,'--allow-dependencies'):m.execute(self.repo,self.home,'demo','active','unauthorized redeploy',True,True)
   run.assert_not_called()
  self.assertEqual(self.mp.read_bytes(),before);self.assertFalse(self.target.exists());self.assertFalse(list((self.home/'.local/state/walerie-server').glob('transition-*')))
 def test_authorized_consumer_redeploy_restarts_only_named_unit(self):
  self.provision();calls=[]
  def observed(unit):return {'ActiveState':'active','RequiredBy':'consumer.service'} if unit=='demo.service' else {'ActiveState':'active'}
  with patch.object(m.Path,'home',return_value=self.home),patch.object(m,'observe',side_effect=observed),patch.object(m,'run',side_effect=lambda *a:calls.append(a)),patch.object(m.subprocess,'run',return_value=SimpleNamespace(returncode=0)):
   plan=m.execute(self.repo,self.home,'demo','active','authorized redeploy',True,True,True)
  self.assertEqual(plan['consumer_disruption'],['consumer.service']);self.assertIn(('restart','demo.service'),calls);self.assertFalse(any('consumer.service' in c for c in calls));self.assertEqual(self.target.read_text(),self.source.read_text())
 def test_unauthorized_consumer_only_redeploy_is_refused(self):
  self.provision()
  with patch.object(m.Path,'home',return_value=self.home),patch.object(m,'observe',return_value={'ActiveState':'active','BoundBy':'consumer.service'}),patch.object(m,'run') as run:
   with self.assertRaisesRegex(ValueError,'--allow-dependencies'):m.execute(self.repo,self.home,'demo','active','unreviewed redeploy',True,True)
   run.assert_not_called()
if __name__=='__main__':unittest.main()
