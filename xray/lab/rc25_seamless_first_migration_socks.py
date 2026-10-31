#!/usr/bin/env python3
"""RC25 disposable FIRST legacy->API SOCKS migration on REAL MIPS Xray.
Run only in unshare -n disposable CI (no NIC/default route, no router).
The legacy Xray keeps its existing listener and TCP flows. Only NEW TCP
connections to the same host-side port are rerouted by netns-local conntrack
NAT OUTPUT to the API-enabled candidate. Not a TPROXY or VPN deployment.
"""
import contextlib
import fcntl
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from xray.lab.xray_v30_api_continuity import (
    EchoBackend, config as api_config, echo, socks_connect, wait_port
)
from xray.lab.xray_v30_dual_process import config as legacy_config
from xray.lab.stable_socks_ingress_v30 import proc_start_ticks


class Reject(RuntimeError):
    pass


def exec_(*args, check=True):
    return subprocess.run(args, text=True, capture_output=True, check=check, timeout=20)


def identity(proc):
    if proc.poll() is not None:
        raise Reject("process exited during migration")
    return proc.pid, proc_start_ticks(proc.pid)


def first_migration(xray):
    if os.environ.get("GITHUB_ACTIONS") != "true" or not os.environ.get("RUNNER_TEMP"):
        raise Reject("ONLY disposable GitHub Actions")
    if Path("/opt/etc/xray/config.json").exists() or Path("/opt/etc/init.d/S97xray").exists():
        raise Reject("refuse production Entware")
    # No non-loopback devices or routes: this test cannot affect host network.
    links = exec_("ip", "-o", "link", "show").stdout
    if any("lo:" not in line for line in links.splitlines()):
        raise Reject("non-loopback NIC exists; network namespace isolation unproven")
    routes = exec_("ip", "-4", "route", "show", "default").stdout.strip()
    if routes:
        raise Reject("default route present in disposable namespace")
    exec_("ip", "link", "set", "lo", "up")
    info = exec_(xray, "version").stdout
    if "26.2.6" not in info or "linux/mipsle" not in info:
        raise Reject("unpinned Xray version/architecture")

    a, b = EchoBackend("A"), EchoBackend("B")
    for backend in (a,b):
        backend.start()
    procs=[]
    lock=None
    orig_port = 10808
    new_port = 20808
    api_port = 21808
    # Conntrack must be loaded BEFORE the old socket is established.
    # Otherwise local loopback connections may be untracked and adding the
    # first nat OUTPUT rule may reinterpret an EXISTING TCP packet as NEW.
    # A RETURN baseline forces nf_conntrack creation without redirect.
    base_rule = ["iptables", "-t", "nat", "-A", "OUTPUT",
                 "-p", "tcp", "-d", "127.0.0.1",
                 "--dport", str(orig_port), "-j", "RETURN"]
    redirect_match = ["-p", "tcp", "-d", "127.0.0.1",
                      "--dport", str(orig_port), "-m", "conntrack",
                      "--ctstate", "NEW", "-j", "REDIRECT",
                      "--to-ports", str(new_port)]
    nat_rule = ["iptables", "-t", "nat", "-I", "OUTPUT", "1", *redirect_match]
    rollback_rule = ["iptables", "-t", "nat", "-D", "OUTPUT", *redirect_match]
    with tempfile.TemporaryDirectory(prefix="rc25-first-migration-") as td:
        try:
            exec_(*base_rule)
            old_config = Path(td)/"legacy.json"
            new_config = Path(td)/"candidate.json"
            # No API in legacy configuration, exactly like current first migration.
            old_config.write_text(json.dumps(legacy_config(orig_port, a.port)))
            new_config.write_text(json.dumps(api_config(api_port, new_port, a.port, b.port)))
            for file in (old_config,new_config):
                exec_(xray, "run", "-test", "-config", str(file))
            old = subprocess.Popen([xray,"run","-config",str(old_config)],
                                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            procs.append(old)
            wait_port(orig_port,old,timeout=20)
            old_id=identity(old)
            with socks_connect(orig_port) as old_flow:
                assert echo(old_flow,b"legacy-before")=="A"
                ct = exec_("conntrack", "-L", "-p", "tcp", check=False)
                if ct.returncode != 0 or not any(
                    "dport=10808" in line and "ESTABLISHED" in line
                    for line in ct.stdout.splitlines()
                ):
                    print("RC25_DIAG: CONNTRACK_RC",ct.returncode,flush=True)
                    print("RC25_DIAG: CONNTRACK_TCP_LINES",repr(ct.stdout[:1800]),flush=True)
                    print("RC25_DIAG: CONNTRACK_ERRORS",repr(ct.stderr[:700]),flush=True)
                    print("RC25_DIAG: NAT_OUTPUT",exec_("iptables","-t","nat","-vnL","OUTPUT").stdout[:1500],flush=True)
                    raise Reject("HARD_NO_GO_OLD_TCP_CONNTRACK_NOT_ESTABLISHED_BEFORE_SWITCH")
                print("RC25: OLD_10808_TCP_CONNTRACK_ESTABLISHED_BEFORE_REDIRECT",flush=True)
                print("RC25: LEGACY_SOCKS_10808_TCP_ESTABLISHED_NO_API",flush=True)
                candidate = subprocess.Popen([xray,"run","-config",str(new_config)],
                                             stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                procs.append(candidate)
                wait_port(new_port,candidate,timeout=20)
                wait_port(api_port,candidate,timeout=20)
                candidate_id=identity(candidate)
                if candidate_id==old_id:
                    raise Reject("identical process identity")
                def api(*args):
                    return exec_(xray,"api",args[0],"-s",f"127.0.0.1:{api_port}",*args[1:])
                api("bo","-b","lab-balancer","lab-b")
                with socks_connect(new_port) as qualified:
                    assert echo(qualified,b"candidate-prepared")=="B"
                # Cooperating lab watchdog MUST acquire the same exclusive flock.
                # Real privileged production watchdog/S97 scripts are NOT involved.
                lock=open(Path(td)/"watchdog-owner.lock","a+")
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                monitor = exec_("python3","-c",
                    "import fcntl,sys;f=open(sys.argv[1],'a+');"
                    "\ntry: fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);sys.exit(51)"
                    "\nexcept BlockingIOError: print('RC25: COOPERATIVE_WATCHDOG_FENCED');sys.exit(0)",
                    str(Path(td)/"watchdog-owner.lock"))
                assert "COOPERATIVE_WATCHDOG_FENCED" in monitor.stdout
                print("RC25: COOPERATIVE_WATCHDOG_RESTART_SUPPRESSED_NO_KILLALL",flush=True)
                generation=1
                expected=1
                if generation!=expected or identity(old)!=old_id or identity(candidate)!=candidate_id:
                    raise Reject("pre-switch PID/startticks/generation CAS failed")
                exec_(*nat_rule)
                generation=2
                try:
                    with socks_connect(orig_port) as new_flow:
                        assert echo(new_flow,b"after-first-migration")=="B"
                        # All existing flows stay pinned to their original Xray.
                        assert echo(old_flow,b"old-still-working")=="A"
                        assert identity(old)==old_id and identity(candidate)==candidate_id
                        print("RC25: PASS_FIRST_INGRESS_SOCKS_NEW_ONLY_TO_API_XRAY_OLD_TCP_DRAINS",flush=True)

                        # The selected candidate backend fails, no implicit direct fallback.
                        b.close()
                        rejected=False
                        try:
                            with socks_connect(orig_port) as broken:
                                result=echo(broken,b"candidate-backend-dead")
                                raise Reject("dead backend new request succeeded via "+result)
                        except (OSError,AssertionError):
                            rejected=True
                        if not rejected:
                            raise Reject("failed candidate leaked/was not blocked")
                        assert echo(old_flow,b"old-during-candidate-failure")=="A"
                        print("RC25: PASS_FAILED_CANDIDATE_NEW_REQUEST_BLOCKED_OLD_FLOW_LIVE",flush=True)

                        # Explicit rollback: remove ONLY the test-owned rule.
                        # Established candidate TCP remains bound to candidate.
                        if generation!=2 or identity(old)!=old_id or identity(candidate)!=candidate_id:
                            raise Reject("rollback PID/startticks/generation CAS failed")
                        exec_(*rollback_rule)
                        generation=3
                        with socks_connect(orig_port) as restored:
                            assert echo(restored,b"rollback")=="A"
                        assert echo(old_flow,b"old-survives-rollback")=="A"
                        assert identity(old)==old_id and identity(candidate)==candidate_id
                        print("RC25: PASS_ROLLBACK_SAME_10808_OLD_PROCESS_PID_STARTTICKS_AND_CAS",flush=True)
                except BaseException:
                    # Remove only exact disposable NAT rule, never host/production.
                    exec_(*rollback_rule,check=False)
                    raise
                assert generation==3
                print("RC25: HARD_NO_GO_TPROXY_UDP_UNCOOPERATIVE_WATCHDOG_VENDOR_HARDWARE",flush=True)
        finally:
            if lock is not None:
                fcntl.flock(lock,fcntl.LOCK_UN)
                lock.close()
            for proc in reversed(procs):
                if proc.poll() is None:
                    proc.terminate()
                    try: proc.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        proc.kill();proc.wait(timeout=8)
            a.close()
            b.close()


if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: python3 -m xray.lab.rc25_seamless_first_migration_socks Xray-wrapper")
    first_migration(sys.argv[1])
