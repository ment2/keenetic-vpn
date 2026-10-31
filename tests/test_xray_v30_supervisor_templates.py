"""Read-only tests for STAGED cooperative supervisor init-wrapper templates."""
from pathlib import Path
import subprocess
import unittest

from xray.staging import v30_supervisor_service as b

ROOT = Path(__file__).resolve().parents[1] / "xray/staging/v30_supervisor_templates"
ENTRYPOINTS = {
    "S97xray": ("start", "stop", "restart"),
    "S98xray-wifi": ("wifi-start", "wifi-stop"),
    "S99xray-watchdog": ("watchdog-start", "watchdog-stop"),
    "xray-watchdog.sh": ("watchdog-loop",),
    "xray-wifi-rules.sh": ("wifi-repair",),
}


class StagedSupervisorTemplatesTests(unittest.TestCase):
    def test_staged_shell_scripts_parse_and_have_no_global_kill(self):
        for filename in ENTRYPOINTS:
            with self.subTest(file=filename):
                script=ROOT / filename
                self.assertTrue(script.is_file())
                p=subprocess.run(["sh","-n",str(script)],capture_output=True)
                self.assertEqual(p.returncode,0,p.stderr)
                src=script.read_text()
                self.assertNotIn("killall",src)
                self.assertNotIn("iptables ",src)
                self.assertIn("v30_supervisor_service.py",src)

    def test_every_mutating_entrypoint_routes_through_one_broker(self):
        for name, expected in ENTRYPOINTS.items():
            src=(ROOT / name).read_text()
            for action in expected:
                with self.subTest(file=name,action=action):
                    if action in ("start","stop","restart") and name=="S97xray":
                        self.assertIn('exec /opt/bin/python3 /opt/bin/v30_supervisor_service.py "$1"',src)
                    else:
                        self.assertIn("v30_supervisor_service.py "+action,src)

    def test_broker_has_single_lock_path_and_blocks_unbootstrapped_mutations(self):
        self.assertEqual(b.RouterPaths.lock,
                         Path("/opt/var/run/xray-v30-supervisor.lock"))
        source=Path(b.__file__).read_text()
        self.assertIn("with supervisor_lock(self.p.lock)",source)
        self.assertNotIn("killall xray",source)
        self.assertNotIn("os.kill(",source)
        self.assertIn("actor must be individually bootstrapped",source)

    def test_staged_templates_do_not_claim_prod_ready(self):
        for name in ENTRYPOINTS:
            self.assertIn("STAGED", (ROOT/name).read_text())


if __name__=="__main__":
    unittest.main()
