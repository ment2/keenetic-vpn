"""RC6 cgroup real-lab capability and standalone shell recovery safeguards."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from xray.lab.v30_rc6_cgroup_v1_lab import no_capability
from xray.lab.v30_rc6_offline_boot_rehearsal import demo
from xray.staging.v30_supervisor_core import FenceError

class RC6IsolationRescue(unittest.TestCase):
    def test_real_cgroup_unavailable_is_reported_as_no_go_not_pass(self):
        with tempfile.TemporaryDirectory() as td:
            status=no_capability(Path(td),"test_not_available")
            result=json.loads((Path(td)/"result.json").read_text())
            self.assertEqual(status,77)
            self.assertEqual(result["status"],"CGROUP_V1_UNAVAILABLE")
            self.assertEqual(result["physical_containment_gate"],"HARD_NO_GO")
            self.assertFalse(result["production_containment_proven"])
            self.assertFalse(result["keenetic_kernel49_verified"])
            self.assertFalse(result["process_inheritance_tested"])
            self.assertEqual(result["router_commands"],[])
    def test_real_sh_recovery_interrupted_corrupt_and_replay(self):
        with tempfile.TemporaryDirectory() as td:
            r=demo(Path(td)/"rc6")
            self.assertEqual(r["status"],"HOST_SHELL_RECOVERY_ONLY")
            self.assertEqual(r["induced_partial_restore_count"],2)
            self.assertEqual(r["restored_origins"],5)
            self.assertTrue(r["no_python_dependency_in_guardian"])
            self.assertTrue(r["entware_usb_simulated_disconnected"])
            for key in ("physical_separate_device_verified",
                        "cold_boot_keenetic_verified",
                        "physical_powerloss_fsync_verified",
                        "production_restore_authorized"):
                self.assertFalse(r[key])
            self.assertEqual(r["router_commands"],[])
    def test_shell_guardian_refuses_any_prod_path_before_write(self):
        from xray.lab import v30_rc6_offline_boot_rehearsal as m
        with tempfile.TemporaryDirectory() as td:
            env={"PATH":"/usr/bin:/bin","V30_RC6_FAULT":""}
            p=subprocess.run(["/bin/sh",str(Path(m.__file__).with_name(
                "v30_rc6_rescue_guardian.sh")),"/opt/etc","/opt/bin"],
                env=env,text=True,capture_output=True,timeout=3)
            self.assertNotEqual(p.returncode,0)
            self.assertIn("refusing non-disposable path",p.stderr)
    def test_test_harness_rejects_production_root(self):
        with self.assertRaises(FenceError):
            demo(Path("/opt/v30-rc6"))
    def test_sh_syntax_checked(self):
        from xray.lab import v30_rc6_offline_boot_rehearsal as m
        script=Path(m.__file__).with_name("v30_rc6_rescue_guardian.sh")
        p=subprocess.run(["/bin/sh","-n",str(script)],capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)
    def test_not_a_boot_hook_or_live_restore_tool(self):
        from xray.lab import v30_rc6_offline_boot_rehearsal as m
        source=Path(m.__file__).with_name("v30_rc6_rescue_guardian.sh").read_text()
        self.assertNotIn("iptables",source.split("set -eu")[-1])
        self.assertNotIn("killall",source.split("set -eu")[-1])
        self.assertNotIn("mount -",source.split("set -eu")[-1])
        self.assertNotIn("reboot",source.split("set -eu")[-1])

if __name__=="__main__":unittest.main()
