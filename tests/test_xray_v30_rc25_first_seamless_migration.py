"""RC25 first migration source safety gates, separate from actual packet CI."""
import pathlib
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
S=(ROOT/"xray/lab/rc25_seamless_first_migration_socks.py").read_text()
class RC25FirstMigrationContracts(unittest.TestCase):
 def test_disposable_namespace_only(self):
  self.assertIn('GITHUB_ACTIONS',S)
  self.assertIn('non-loopback NIC exists',S)
  self.assertIn('default route present',S)
  self.assertIn('refuse production Entware',S)
 def test_legacy_listener_is_not_closed(self):
  self.assertIn('old_config.write_text',S)
  self.assertIn('new_config.write_text',S)
  self.assertIn('orig_port = 10808',S)
  self.assertIn('new_port = 20808',S)
  self.assertNotIn('killall',S.replace("NO_KILLALL",""))
 def test_new_connections_only_forwarding(self):
  self.assertIn('"nat", "-A", "OUTPUT"',S)
  self.assertIn('"REDIRECT", "--to-ports"',S)
  self.assertIn('nat_rule[:3]+["-D"]+nat_rule[4:]',S)
  self.assertIn('old-still-working',S)
 def test_real_candidate_death_and_rollback(self):
  self.assertIn('b.close()',S)
  self.assertIn('dead backend new request succeeded',S)
  self.assertIn('rollback',S)
  self.assertIn('old-survives-rollback',S)
 def test_identity_and_generation_gate(self):
  self.assertIn('proc_start_ticks',S)
  self.assertIn('identity(old)!=old_id',S)
  self.assertIn('identity(candidate)!=candidate_id',S)
  self.assertIn('generation!=2',S)
 def test_only_cooperative_watchdog(self):
  self.assertIn('fcntl.LOCK_EX|fcntl.LOCK_NB',S)
  self.assertIn('COOPERATIVE_WATCHDOG_FENCED',S)
  self.assertIn('HARD_NO_GO_TPROXY_UDP_UNCOOPERATIVE_WATCHDOG_VENDOR_HARDWARE',S)
if __name__=="__main__":unittest.main()
