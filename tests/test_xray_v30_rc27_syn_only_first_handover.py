"""RC27 isolated SYN-only first TCP handover: structural anti-false-positive checks."""
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=(ROOT/"xray/lab/rc27_socks_syn_only_first_handover.py").read_text()

class RC27SynOnlyHandover(unittest.TestCase):
    def test_no_production_or_network_outside_unshare(self):
        for item in ("GITHUB_ACTIONS", "refuse production Entware",
                     "non-loopback NIC exists", "default route present"):
            self.assertIn(item,SRC)
    def test_old_listener_keeps_original_port(self):
        self.assertIn("orig_port = 10808",SRC)
        self.assertIn("new_port = 20808",SRC)
        self.assertIn("old_config.write_text",SRC)
        self.assertIn("new_config.write_text",SRC)
        self.assertNotIn("killall xray",SRC)
    def test_syn_only_instead_of_unverified_conntrack_new(self):
        self.assertIn('"--tcp-flags","SYN,RST,ACK","SYN"',SRC)
        self.assertNotIn('"--ctstate", "NEW"',SRC)
        self.assertIn('"REDIRECT","--to-ports",str(new_port)',SRC)
        self.assertIn('exec_(*rollback_rule)',SRC)
        self.assertIn('exec_(*nat_rule)',SRC)
    def test_real_socket_identity_for_legacy_stream(self):
        self.assertIn('os.fstat(sock.fileno()).st_ino',SRC)
        self.assertIn('Path("/proc/net/tcp")',SRC)
        self.assertIn('fields[3] == "01"',SRC)
        self.assertIn("OLD_TCP_SOCKET_INODE_UNCHANGED_POST_SWITCH",SRC)
        self.assertIn("HARD_NO_GO_OLD_TCP_SOCKET_ID_CHANGED_DURING_FAILURE",SRC)
        self.assertIn("HARD_NO_GO_OLD_TCP_SOCKET_ID_CHANGED_AT_ROLLBACK",SRC)
    def test_requires_real_old_and_new_echo(self):
        self.assertIn('echo(new_flow,b"after-first-migration")=="B"',SRC)
        self.assertIn('echo(old_flow,b"old-still-working")=="A"',SRC)
        self.assertIn('echo(old_flow,b"old-survives-rollback")=="A"',SRC)
    def test_candidate_failure_blocks_new_requests(self):
        self.assertIn("b.close()",SRC)
        self.assertIn("dead backend new request succeeded via",SRC)
        self.assertIn("FAILED_CANDIDATE_NEW_REQUEST_BLOCKED_OLD_FLOW_LIVE",SRC)
    def test_generation_pid_and_watchdog(self):
        for marker in ("proc_start_ticks", "generation!=2",
                       "identity(old)!=old_id", "identity(candidate)!=candidate_id",
                       "COOPERATIVE_WATCHDOG_RESTART_SUPPRESSED_NO_KILLALL"):
            self.assertIn(marker,SRC)
    def test_unproven_tproxy_udp_stays_no_go(self):
        self.assertIn("HARD_NO_GO_TPROXY_UDP_UNCOOPERATIVE_WATCHDOG_VENDOR_HARDWARE",SRC)

if __name__=="__main__":
    unittest.main()
