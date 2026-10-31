"""Linux49 lab-only wrapper integration; never run production init scripts."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from xray.staging.v30_kernel49_cooperative_ledger import Ledger

ROOT=Path(__file__).resolve().parents[1]
TEMPLATES=ROOT/"xray/staging/v30_kernel49_entrypoints"
EXPECTED={
    "S97xray":("S97",["START","STOP","RESTART"]),
    "S98xray-wifi":("S98",["CHECK_TPROXY"]),
    "S99xray-watchdog":("S99",["CHECK_HEALTH"]),
    "xray-watchdog.sh":("watchdog",["CHECK_HEALTH"]),
    "xray-safe-hourly.sh":("cron",["CHECK_HEALTH"]),
    "xray-fc-cron-guard.sh":("cron",["CHECK_HEALTH"]),
}

class Kernel49EntrypointTests(unittest.TestCase):
    def test_all_six_wrappers_parse_and_delegate_no_shell_mutation(self):
        for name,(actor,actions) in EXPECTED.items():
            with self.subTest(name=name):
                path=TEMPLATES/name
                self.assertTrue(path.is_file())
                p=subprocess.run(["sh","-n",str(path)],capture_output=True)
                self.assertEqual(p.returncode,0,p.stderr)
                executable="\n".join(x for x in path.read_text().splitlines()
                                    if not x.lstrip().startswith("#"))
                self.assertIn("XRAY_V30_DISPOSABLE_ROOT",executable)
                self.assertIn("v30_kernel49_cooperative_lab --client",executable)
                self.assertNotIn("killall ",executable)
                self.assertNotIn("iptables ",executable)
                self.assertNotIn("os.kill",executable)

    def test_all_scripts_refuse_when_not_explicit_lab_root(self):
        env=dict(os.environ)
        env.pop("XRAY_V30_DISPOSABLE_ROOT",None)
        for name in EXPECTED:
            with self.subTest(name=name):
                p=subprocess.run(["sh",str(TEMPLATES/name),"start"],
                    env=env,text=True,capture_output=True,timeout=2)
                self.assertNotEqual(p.returncode,0)
                self.assertEqual(p.stdout,"")

    def test_actual_s97_wrapper_stages_request_only(self):
        with tempfile.TemporaryDirectory() as td:
            env={**os.environ,"XRAY_V30_DISPOSABLE_ROOT":td}
            for cmd in ("start","restart","stop"):
                with self.subTest(cmd=cmd):
                    p=subprocess.run(["sh",str(TEMPLATES/"S97xray"),cmd],
                        env=env,text=True,capture_output=True,timeout=4,cwd=ROOT)
                    self.assertEqual(p.returncode,0,p.stderr)
            rows=Ledger(td).read()["pending"]
            self.assertEqual([x["operation"] for x in rows],
                             ["START","RESTART","STOP"])

    def test_health_and_s98_wrappers_enqueue_read_only_only(self):
        with tempfile.TemporaryDirectory() as td:
            env={**os.environ,"XRAY_V30_DISPOSABLE_ROOT":td}
            for name,cmd in [
                ("S98xray-wifi","check"),("S99xray-watchdog","check"),
                ("xray-watchdog.sh",""),("xray-safe-hourly.sh",""),
                ("xray-fc-cron-guard.sh","")]:
                args=["sh",str(TEMPLATES/name)]
                if cmd:args.append(cmd)
                p=subprocess.run(args,env=env,cwd=ROOT,text=True,
                                 capture_output=True,timeout=4)
                self.assertEqual(p.returncode,0,(name,p.stderr))
            rows=Ledger(td).read()["pending"]
            self.assertEqual([x["operation"] for x in rows],
                ["CHECK_TPROXY","CHECK_HEALTH","CHECK_HEALTH",
                 "CHECK_HEALTH","CHECK_HEALTH"])

    def test_s98_cannot_repair_and_watchdog_cannot_restart(self):
        with tempfile.TemporaryDirectory() as td:
            env={**os.environ,"XRAY_V30_DISPOSABLE_ROOT":td}
            for name,op in (("S98xray-wifi","restart"),
                            ("S99xray-watchdog","restart")):
                p=subprocess.run(["sh",str(TEMPLATES/name),op],env=env,
                    cwd=ROOT,capture_output=True,timeout=3)
                self.assertNotEqual(p.returncode,0)
            self.assertFalse(Ledger(td).read()["pending"])


if __name__=="__main__":
    unittest.main()
