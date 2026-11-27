"""Disposable execution of sanitized live wrapper control flow.

Never invokes production paths or a real service. Source readback has the
two probe URLs replaced by .invalid fixtures and all /opt paths relocated.
"""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

FIXTURE=Path(__file__).parent/"fixtures/safe-hourly-live-20261127.fixture.txt"
OLD={"fixture_generation":"old","outbounds":[{"tag":"vpn01","protocol":"vless"}]}
NEW={"fixture_generation":"new","outbounds":[{"tag":"vpn04","protocol":"vless"}]}

class LiveWrapperFixtureTests(unittest.TestCase):
    def execute(self, scenario):
        with tempfile.TemporaryDirectory(prefix="v23-wrapper-fixture-") as tmp:
            root=Path(tmp)
            for d in ("opt/bin","opt/sbin","opt/etc/xray","opt/etc/init.d","opt/var/log"):
                (root/d).mkdir(parents=True)
            conf=root/"opt/etc/xray/config.json"
            pending=conf.with_name("config.pending.json")
            backup=conf.with_name("config.lastgood.autoapply.json")
            conf.write_text(json.dumps(OLD))
            old=conf.read_bytes()
            candidate=OLD if scenario=="unchanged" else NEW
            (root/"candidate-input.json").write_text(json.dumps(candidate))
            env={**os.environ,"FIXTURE_ROOT":tmp,"FIXTURE_SCENARIO":scenario}
            def script(rel,body):
                p=root/rel
                p.write_text("#!"+sys.executable+"\n"+body)
                p.chmod(0o700)
            common='import os,sys,json,pathlib\nr=pathlib.Path(os.environ["FIXTURE_ROOT"])\ns=os.environ["FIXTURE_SCENARIO"]\nc=r/"opt/etc/xray/config.json"\n'
            script("opt/bin/xray-update-v23.py",common+'''
if s=="generation_fail": sys.exit(1)
p=pathlib.Path(sys.argv[2])
if s=="empty": p.write_text(""); sys.exit(0)
if s=="no_vless": p.write_text('{"outbounds":[]}'); sys.exit(0)
p.write_bytes((r/"candidate-input.json").read_bytes())
''')
            script("opt/sbin/xray",common+'''
assert sys.argv[1:4]==["run","-test","-config"]
p=pathlib.Path(sys.argv[4])
g=json.loads(p.read_text()).get("fixture_generation")
sys.exit(int((s=="invalid_candidate" and g=="new") or (s=="invalid_rollback" and g=="old")))
''')
            script("opt/etc/init.d/S97xray",common+'''
assert sys.argv[1:]==["restart"]
g=json.loads(c.read_text())["fixture_generation"]
with (r/"restart-trace").open("a") as f: f.write(g+"\\n")
sys.exit(int((s=="restart_fail" and g=="new") or s=="rollback_fail"))
''')
            script("opt/bin/curl",common+'''
g=json.loads(c.read_text())["fixture_generation"]
assert "--socks5-hostname" in sys.argv and "127.0.0.1:10808" in sys.argv
assert sys.argv[-1].endswith(("/204","/401"))
code="204" if sys.argv[-1].endswith("/204") else "401"
if g=="new" and s=="health_fail" and code=="401": code="403"
if g=="new" and s=="internet_fail" and code=="204": code="500"
print(code,end="")
''')
            script("opt/bin/sleep","pass\n")
            raw=FIXTURE.read_text().replace("@ROOT@",tmp).replace("@PYTHON@",shlex.quote(sys.executable))
            self.assertNotIn("@ROOT@",raw)
            self.assertNotIn("@PYTHON@",raw)
            wrapper=root/"wrapper.sh"
            wrapper.write_text(raw)
            result=subprocess.run(["/bin/sh",str(wrapper)],env=env,capture_output=True,timeout=20)
            log=root/"opt/var/log/xray-update.log"
            trace=root/"restart-trace"
            return {"rc":result.returncode,"active":json.loads(conf.read_text()),
                    "backup":backup.read_bytes() if backup.exists() else None,
                    "pending":pending.exists(),"old":old,
                    "trace":trace.read_text().splitlines() if trace.exists() else [],
                    "log":log.read_text() if log.exists() else "",
                    "workdirs":list(conf.parent.glob(".update.*"))}

    def test_apply_success(self):
        r=self.execute("success")
        self.assertEqual((r["rc"],r["active"],r["trace"]),(0,NEW,["new"]))
        self.assertEqual(r["backup"],r["old"])
        self.assertFalse(r["pending"])
        self.assertIn("SUCCESS:",r["log"])
        self.assertFalse(r["workdirs"])

    def test_generation_failure_leaves_old(self):
        for s in ("generation_fail","empty","no_vless","invalid_candidate"):
            with self.subTest(s=s):
                r=self.execute(s)
                self.assertNotEqual(r["rc"],0)
                self.assertEqual(r["active"],OLD)
                self.assertFalse(r["trace"])
                self.assertIsNone(r["backup"])
                self.assertFalse(r["pending"])
                self.assertFalse(r["workdirs"])

    def test_failed_health_or_restart_rolls_back(self):
        for s in ("health_fail","internet_fail","restart_fail"):
            with self.subTest(s=s):
                r=self.execute(s)
                self.assertNotEqual(r["rc"],0)
                self.assertEqual(r["active"],OLD)
                self.assertEqual(r["trace"],["new","old"])
                self.assertEqual(r["backup"],r["old"])
                self.assertIn("ROLLBACK_OK:",r["log"])
                self.assertFalse(r["workdirs"])

    def test_invalid_rollback_blocks_apply(self):
        r=self.execute("invalid_rollback")
        self.assertNotEqual(r["rc"],0)
        self.assertEqual(r["active"],OLD)
        self.assertFalse(r["trace"])
        self.assertTrue(r["pending"])
        self.assertIn("rollback configuration invalid",r["log"])

    def test_unchanged_no_restart(self):
        r=self.execute("unchanged")
        self.assertEqual(r["rc"],0)
        self.assertEqual(r["active"],OLD)
        self.assertFalse(r["trace"])
        self.assertIn("UNCHANGED:",r["log"])

    def test_rollback_restart_failure_is_critical(self):
        r=self.execute("rollback_fail")
        self.assertNotEqual(r["rc"],0)
        self.assertEqual(r["active"],OLD)
        self.assertEqual(r["trace"],["new","old"])
        self.assertIn("CRITICAL:",r["log"])

    @unittest.skipUnless(shutil.which("flock"),"flock required")
    def test_external_cron_lock_prevents_competing_wrapper(self):
        import fcntl
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"lock"
            with p.open("w") as f:
                fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                r=subprocess.run(["flock","-n","-o",str(p),sys.executable,"-c","print('unexpected')"],capture_output=True,timeout=5)
                self.assertNotEqual(r.returncode,0)
                self.assertEqual(r.stdout,b"")
            r=subprocess.run(["flock","-n","-o",str(p),sys.executable,"-c","print('executed')"],capture_output=True,timeout=5)
            self.assertEqual(r.returncode,0)
            self.assertEqual(r.stdout.strip(),b"executed")
