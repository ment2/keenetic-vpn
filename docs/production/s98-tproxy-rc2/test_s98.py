import importlib.machinery,importlib.util,unittest,subprocess,tempfile
from pathlib import Path
from unittest.mock import patch
p=Path(__file__).with_name('S98xray-wifi'); l=importlib.machinery.SourceFileLoader('s98',str(p)); spec=importlib.util.spec_from_loader(l.name,l); m=importlib.util.module_from_spec(spec); l.exec_module(m)
def lines(rules): return ['-A '+m.CHAIN+' '+' '.join(a) for a in rules]
class Tests(unittest.TestCase):
 def test_empty(self): self.assertEqual(m.chain_plan([]),m.RULES)
 def test_partial(self): self.assertEqual(m.chain_plan(lines(m.RULES[:9])),m.RULES[9:])
 def test_complete(self): self.assertEqual(m.chain_plan(lines(m.RULES)),[])
 def test_canonical(self):
  a=lines(m.RULES); a[-2]=a[-2].replace('-p tcp','-p tcp -m tcp').replace('--on-port','--on-ip 0.0.0.0 --on-port'); self.assertEqual(m.chain_plan(a),[])
 def test_foreign(self):
  with self.assertRaises(m.Error): m.chain_plan(['-A XRAY_WIFI -j ACCEPT'])
 def test_reorder(self):
  a=lines(m.RULES); a[0],a[1]=a[1],a[0]
  with self.assertRaises(m.Error): m.chain_plan(a)
 def test_duplicate(self):
  with self.assertRaises(m.Error): m.chain_plan(lines(m.RULES+[m.RULES[-1]]))
 def test_wrong_mark(self):
  a=lines(m.RULES); a[-1]=a[-1].replace(m.MARK,'0x1/0x1')
  with self.assertRaises(m.Error): m.chain_plan(a)
 def test_identity(self):
  a=dict(pid=703,boot='one',ticks='1',state='S',args=[b'/opt/bin/python3',m.SERVICE.encode(),b'watch']); self.assertEqual(m.role(a),'rc1'); self.assertFalse(m.same(a,{**a,'boot':'two'})); self.assertFalse(m.same(a,{**a,'ticks':'2'})); self.assertIsNone(m.role({**a,'args':[b'other']})); self.assertIsNone(m.role({**a,'state':'Z'}))
 def test_legacy(self): self.assertEqual(m.role(dict(state='S',args=[b'/opt/bin/sh',m.SERVICE.encode(),b'start'])),'legacy')
 def test_guard_fail_no_mutation(self):
  with patch.object(m,'guard',side_effect=m.Error('missing')),patch.object(m,'ensure_module') as module:
   with self.assertRaises(m.Error): m.ensure()
   module.assert_not_called()
 def test_policy_conflict(self):
  with patch.object(m,'run',return_value=subprocess.CompletedProcess([],0,'20000: from all lookup main\n','')) as cmd:
   with self.assertRaises(m.Error): m.ensure_routes()
   self.assertEqual(cmd.call_count,1)
 def test_table_conflict(self):
  with patch.object(m,'run',side_effect=[subprocess.CompletedProcess([],0,'',''),subprocess.CompletedProcess([],0,'default via 10.1.1.1\n','')]) as cmd:
   with self.assertRaises(m.Error): m.ensure_routes()
   self.assertEqual(cmd.call_count,2)
 def test_atomic_record(self):
  with tempfile.TemporaryDirectory() as d:
   with patch.object(m,'PID',Path(d)/'pid'),patch.object(m,'ID',Path(d)/'id'),patch.object(m,'REQUEST',Path(d)/'stop'):
    m.record(dict(pid=77,boot='abc',ticks='22')); self.assertEqual(m.PID.read_text(),'77\n'); self.assertIn('abc',m.ID.read_text()); m.clear_record(); self.assertFalse(m.PID.exists())
 def test_native_chain(self):
  a=lines(m.RULES); a[-2]=a[-2].replace('--tproxy-mark','--on-ip 0.0.0.0 --tproxy-mark'); a[-1]=a[-1].replace('--tproxy-mark','--on-ip 0.0.0.0 --tproxy-mark'); self.assertEqual(m.chain_plan(a),[])
 def test_guard_order(self):
  ks='-N XRAY_KS_HOME\n-A XRAY_KS_HOME -d 192.168.0.0/16 -j RETURN\n-A XRAY_KS_HOME -s 192.168.1.0/24 -i br0 -j DROP\n'
  for f,ok in [('-P FORWARD DROP\n-A FORWARD -j XRAY_KS_HOME\n',True),('-P FORWARD DROP\n-A FORWARD -j ACCEPT\n-A FORWARD -j XRAY_KS_HOME\n',False)]:
   with patch.object(m,'run',side_effect=[subprocess.CompletedProcess([],0,ks,''),subprocess.CompletedProcess([],0,f,'')]):
    if ok: m.guard()
    else:
     with self.assertRaises(m.Error): m.guard()
 def test_jump_plan(self):
  t='-A PREROUTING -s 192.168.1.0/24 -i br0 -p tcp -j XRAY_WIFI'; u=t.replace('-p tcp','-p udp')
  for data,expected in [(u+'\n'+t,[]),(t,['udp']),('', ['tcp','udp'])]:
   with patch.object(m,'ipt',return_value=subprocess.CompletedProcess([],0,data,'')): self.assertEqual(m.jump_plan(),expected)
  for data in [t+'\n'+t, '-A PREROUTING -j RETURN\n'+t,t.replace('br0','br1')]:
   with patch.object(m,'ipt',return_value=subprocess.CompletedProcess([],0,data,'')):
    with self.assertRaises(m.Error): m.jump_plan()
 def test_policy_exact(self):
  with patch.object(m,'run',return_value=subprocess.CompletedProcess([],0,'20000: from 192.168.1.0/24 fwmark '+m.MARK+' lookup 100\n','')):
   with self.assertRaises(m.Error): m.ensure_routes(False)
 def test_missing_table_read_only(self):
  with patch.object(m,'run',side_effect=[subprocess.CompletedProcess([],0,'',''),subprocess.CompletedProcess([],0,'','')]) as c:
   self.assertFalse(m.ensure_routes(False)); self.assertEqual(c.call_count,2)
 def test_native_routes(self):
  with patch.object(m,'run',side_effect=[subprocess.CompletedProcess([],0,'20000: from all fwmark '+m.MARK+' lookup 100 \n',''),subprocess.CompletedProcess([],0,'local default dev lo scope host \n','')]) as c:
   self.assertTrue(m.ensure_routes()); self.assertEqual(c.call_count,2)
 def test_preflight_chain_conflict(self):
  with patch.object(m,'guard'),patch.object(m,'ensure_routes'),patch.object(m,'chain_state',side_effect=m.Error('foreign')),patch.object(m,'ensure_module') as mod:
   with self.assertRaises(m.Error): m.ensure()
   mod.assert_not_called()
 def test_role_rc2(self):
  p=dict(state='S',args=[m.PY.encode(),m.SERVICE.encode(),b'watch',b'7',b'9']); self.assertEqual(m.role(p),'rc2'); self.assertIsNone(m.role({**p,'args':p['args'][:-1]+[b'bad']}))
 def test_stop_bound_to_identity(self):
  import json
  with tempfile.TemporaryDirectory() as d:
   with patch.object(m,'REQUEST',Path(d)/'stop'):
    a=dict(pid=703,boot='one',ticks='1'); m.atomic(m.REQUEST,json.dumps(a)); self.assertTrue(m.requested(a)); self.assertFalse(m.requested({**a,'ticks':'2'})); self.assertFalse(m.requested({**a,'boot':'two'}))
 def test_readiness_record(self):
  with tempfile.TemporaryDirectory() as d:
   with patch.object(m,'PID',Path(d)/'pid'),patch.object(m,'ID',Path(d)/'id'):
    a=dict(pid=703,boot='one',ticks='1'); m.record(a); self.assertTrue(m.ready_record(a)); m.PID.write_text('705'); self.assertFalse(m.ready_record(a))
 def test_lifetime_lock(self):
  import os
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'l'; fd=m.lock_open(path)
   try:
    with self.assertRaises(BlockingIOError): m.lock_open(path)
   finally: os.close(fd)
   fd=m.lock_open(path); os.close(fd); self.assertTrue(path.exists())
 def test_check_read_only(self):
  with patch.object(m,'guard'),patch.object(m,'target_ready',return_value=True),patch.object(m,'ensure_routes',return_value=True) as r,patch.object(m,'chain_state',return_value=[]),patch.object(m,'jump_plan',return_value=[]),patch.object(m,'ipt') as i:
   m.check_live(); r.assert_called_once_with(False); self.assertTrue(all(c.args[0]=='-C' for c in i.call_args_list)); self.assertEqual(i.call_count,11)
 def test_module_already_loaded(self):
  with patch.object(m,'target_ready',return_value=True),patch.object(m,'run') as r:
   m.ensure_module(); r.assert_not_called()
 def test_bad_module_no_insmod(self):
  import os
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'m.ko'; p.write_bytes(b'wrong')
   with patch.object(m,'MODULE',p),patch.object(m,'target_ready',return_value=False),patch.object(m.os,'uname',return_value=os.uname_result(('Linux','x','4.9-ndm-5','x','mips'))),patch.object(m,'run') as r:
    with self.assertRaises(m.Error): m.ensure_module()
    r.assert_not_called()
 def test_module_registration_failure(self):
  import os,hashlib
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'m.ko'; p.write_bytes(b'fixture')
   with patch.object(m,'MODULE',p),patch.object(m,'MODULE_SHA',hashlib.sha256(b'fixture').hexdigest()),patch.object(m,'target_ready',return_value=False),patch.object(m.os,'uname',return_value=os.uname_result(('Linux','x','4.9-ndm-5','x','mips'))),patch.object(m,'run') as r:
    with self.assertRaises(m.Error): m.ensure_module()
    r.assert_called_once_with('/opt/sbin/insmod',str(p))
 def test_real_lock_handoff(self):
  import os,sys,select
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'lock'; fd=m.lock_open(path); rd,wr=os.pipe()
   child=subprocess.Popen([sys.executable,'-c','import os,sys,fcntl; f=int(sys.argv[1]); w=int(sys.argv[2]); fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB); os.write(w,b"R"); sys.stdin.buffer.read(1)',str(fd),str(wr)],pass_fds=(fd,wr),stdin=subprocess.PIPE)
   os.close(wr); os.close(fd)
   try:
    self.assertTrue(select.select([rd],[],[],3)[0]); self.assertEqual(os.read(rd,1),b'R')
    with self.assertRaises(BlockingIOError): m.lock_open(path)
   finally:
    os.close(rd); child.communicate(b'Q',timeout=3)
   fd=m.lock_open(path); os.close(fd)
 def test_no_mutating_iptables_when_healthy(self):
  with patch.object(m,'guard'),patch.object(m,'ensure_routes',return_value=True),patch.object(m,'ensure_module'),patch.object(m,'chain_state',return_value=[]),patch.object(m,'jump_plan',return_value=[]),patch.object(m,'ipt') as i:
   m.ensure(); self.assertTrue(all(c.args[0]=='-C' for c in i.call_args_list)); self.assertEqual(i.call_count,11)
if __name__=='__main__': unittest.main(verbosity=2)
