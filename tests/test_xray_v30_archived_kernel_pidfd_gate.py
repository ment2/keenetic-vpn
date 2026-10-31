"""Archived Keenetic Linux 4.9 pidfd no-go; never call router."""
import unittest
from xray.lab import v30_archived_kernel_pidfd_gate as gate


class KernelPidfdGateTests(unittest.TestCase):
    def test_archived_router_kernel_cannot_support_staged_pidfd(self):
        r=gate.capability_report("4.9-ndm-5")
        self.assertEqual(r["release_gate"],"OFFLINE_KERNEL_INCOMPATIBLE")
        self.assertFalse(r["staged_supervisor_pidfd_compatible"])
        self.assertFalse(r["pidfd_open_kernel_capable"])
        self.assertFalse(r["pidfd_send_signal_kernel_capable"])
        self.assertFalse(r["production_signal_authorized"])
        self.assertFalse(r["evidence_is_fresh"])
        self.assertEqual(r["production_commands"],[])

    def test_pidfd_minimum_kernel_versions(self):
        cases=[
            ("4.19.10",False,False),("5.0.99",False,False),
            ("5.1.0",True,False),("5.2.25",True,False),
            ("5.3.0",True,True),("6.1.1",True,True),
        ]
        for release,send,opened in cases:
            with self.subTest(release=release):
                r=gate.capability_report(release)
                self.assertEqual(r["pidfd_send_signal_kernel_capable"],send)
                self.assertEqual(r["pidfd_open_kernel_capable"],opened)
                self.assertFalse(r["production_signal_authorized"])

    def test_invalid_kernel_string_no_guess(self):
        for value in ("","unknown","4.9-ndm#bad","Linux 4.9",None):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    gate.parse_release(value)

    def test_archived_job_id_exact(self):
        self.assertEqual(gate.ARCHIVED_JOB,"ea140581-a4db-42f5-ac4d-46c8c6c462ba")

    def test_safe_cli_only_archived(self):
        import subprocess,sys,json
        x=subprocess.run([sys.executable,"-m","xray.lab.v30_archived_kernel_pidfd_gate",
                          "--archived-only"],text=True,capture_output=True,check=True)
        r=json.loads(x.stdout)
        self.assertEqual(r["archived_job_id"],gate.ARCHIVED_JOB)
        self.assertEqual(r["release_gate"],"OFFLINE_KERNEL_INCOMPATIBLE")
        denied=subprocess.run([sys.executable,"-m","xray.lab.v30_archived_kernel_pidfd_gate",
                               "--exec"],capture_output=True)
        self.assertNotEqual(denied.returncode,0)


if __name__=="__main__":
    unittest.main()
