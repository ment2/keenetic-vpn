"""RC22 strict disposable postdeath leak detection: source checks only."""
import pathlib
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNNER=(ROOT/"xray/lab/rc22_mips49_postdeath_runner.sh").read_text()
GUEST=(ROOT/"xray/lab/rc22_mips49_postdeath_packet.sh").read_text()

class RC22PostdeathGate(unittest.TestCase):
    def test_isolated_slirp_and_two_distinct_ports(self):
        self.assertIn("-netdev user,id=isolated,restrict=on",RUNNER)
        self.assertIn("hostfwd=udp:127.0.0.1:19191-:19191",RUNNER)
        self.assertIn("-DPORT=19292",RUNNER)
        self.assertIn("-DPORT=19191",RUNNER)
        self.assertIn('"redirect":"127.0.0.1:19292"',RUNNER)
    def test_guest_mips_kernel_and_raw_xray_real_fixture(self):
        self.assertIn("linux-image-4.9.0-13-4kc-malta",RUNNER)
        self.assertIn("Xray-linux-mips32le.zip",RUNNER)
        self.assertIn("/bin/rc9capwrap raw xray",GUEST)
        self.assertIn("test \"$caps\" = 0000000000002000",GUEST)
    def test_owned_pid_startticks_and_socket_termination(self):
        self.assertIn("xticks2",GUEST)
        self.assertIn('test "$xticks" = "$xticks2"',GUEST)
        self.assertIn('kill -TERM "$xraypid"',GUEST)
        self.assertIn("XRAY_LISTENERS_GONE_AFTER_PARENT_OWNED_SIGNAL",GUEST)
    def test_postdeath_sentinel_is_late(self):
        self.assertLess(GUEST.index("XRAY_LISTENERS_GONE_AFTER_PARENT_OWNED_SIGNAL"),GUEST.index("/lab/echo-orig"))
        self.assertIn("POSTDEATH_SENTINEL_READY_SEND_PROBES",GUEST)
        self.assertIn("POSTDEATH_PROBES_SENT_NO_RETURN_CLAIM",RUNNER)
    def test_packet_counters_must_increase_and_leak_is_hard_no_go(self):
        self.assertIn('test "$after" -gt "$before"',GUEST)
        self.assertIn("OBSERVED_DIRECT_FALLBACK_AFTER_XRAY_DEATH_HARD_NO_GO",GUEST)
        self.assertIn("HARD_NO_GO_DIRECT_BYPASS_AFTER_XRAY_DEATH_OBSERVED",RUNNER)
        self.assertIn("POSTDEATH_NO_SENTINEL_RECEIPT_BOUNDED_LAB_ONLY",RUNNER)
        self.assertNotIn("PRODUCTION_AUTHORIZED",RUNNER)
    def test_does_not_claim_host_udp_success_from_timeout(self):
        self.assertIn("UDP_HOST_RETURN_UNPROVEN_RESTRICT_ON",RUNNER)
        self.assertIn("HARD_NO_GO_HOST_UDP_RETURN_LEGACY_FENCING_VENDOR_HARDWARE",RUNNER)
if __name__=="__main__":
 unittest.main()
