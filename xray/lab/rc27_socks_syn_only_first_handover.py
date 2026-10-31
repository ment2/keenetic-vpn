#!/usr/bin/env python3
"""RC27 disposable FIRST legacy->API SOCKS migration on REAL MIPS Xray.
Run only in unshare -n disposable CI (no NIC/default route, no router).
The legacy Xray keeps its existing listener and TCP flows. Only SYN-starting NEW TCP connections to the fixed local SOCKS port
are candidate-routed by netns-local NAT OUTPUT; all existing non-SYN packets
must retain legacy TCP socket identity and exact response bytes. This is a
falsification experiment, not proof of production VPN/TPROXY migration.
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
    # Legacy RC25 netns had zero conntrack entries and reset established TCP.
    # DO NOT infer "NEW" from conntrack in this experiment: the redirect
    # is SYN-only, matching TCP first-handshake flags instead. If kernel NAT
    # cannot preserve both old and new sessions, fail the real packet test.
    redirect_match = ["-p","tcp","-d","127.0.0.1",
                      "--dport",str(orig_port),"-m","tcp",
                      "--tcp-flags","SYN,RST,ACK","SYN",
                      "-j","REDIRECT","--to-ports",str(new_port)]
    nat_rule = ["iptables","-t","nat","-I","OUTPUT","1",*redirect_match]
    rollback_rule = ["iptables","-t","nat","-D","OUTPUT",*redirect_match]
    def established_socket_witness(sock):
        inode = os.fstat(sock.fileno()).st_ino
        rows = Path("/proc/net/tcp").read_text().splitlines()[1:]
        if not any((fields:=row.split())[9] == str(inode) and fields[3] == "01"
                   for row in rows):
            raise Reject("HARD_NO_GO_OLD_SOCKET_INODE_NOT_ESTABLISHED")
        return inode, sock.getsockname(), sock.getpeername()
    with tempfile.TemporaryDirectory(prefix="rc27-first-migration-") as td:
        try:
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
                legacy_socket_id = established_socket_witness(old_flow)
                print("RC27: OLD_TCP_SOCKET_INODE_ESTABLISHED_BEFORE_SYN_ONLY_CUTOVER",flush=True)
                # RC25 zero conntrack diagnostic is a hard limitation: this
                # test probes whether a strict SYN-only rule can avoid resets.
                ct = exec_("conntrack","-L","-p","tcp",check=False)
                print("RC27_DIAG: PRE_SWITCH_CONNTRACK_ENTRY_COUNT",
                      sum("tcp" in line for line in ct.stdout.splitlines()),flush=True)
                print("RC27: LEGACY_SOCKS_10808_TCP_ESTABLISHED_NO_API",flush=True)
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
                    "\nexcept BlockingIOError: print('RC27: COOPERATIVE_WATCHDOG_FENCED');sys.exit(0)",
                    str(Path(td)/"watchdog-owner.lock"))
                assert "COOPERATIVE_WATCHDOG_FENCED" in monitor.stdout
                print("RC27: COOPERATIVE_WATCHDOG_RESTART_SUPPRESSED_NO_KILLALL",flush=True)
                generation=1
                expected=1
                if generation!=expected or identity(old)!=old_id or identity(candidate)!=candidate_id:
                    raise Reject("pre-switch PID/startticks/generation CAS failed")
                # Require exact rule with SYN-only match, never broad new-flow
                # matching that could reinterpret already-open legacy flows.
                exec_(*nat_rule)
                # iptables-nft may canonicalize the rule and reject -C with
                # noncanonical match args, even when -S confirms installation.
                # Require the exact canonical netns-local rule and nothing else.
                expected_nat = ("-A OUTPUT -d 127.0.0.1/32 -p tcp -m tcp"
                                " --dport 10808 --tcp-flags SYN,RST,ACK SYN"
                                " -j REDIRECT --to-ports 20808")
                actual = exec_("iptables","-t","nat","-S","OUTPUT")
                rules = actual.stdout.splitlines()
                if rules != ["-P OUTPUT ACCEPT", expected_nat]:
                    print("RC27_DIAG: OUTPUT_NAT_RULES",repr(rules),flush=True)
                    raise Reject("HARD_NO_GO_SYN_ONLY_RULE_CANONICAL_READBACK_MISMATCH")
                print("RC27: EXACT_SYN_ONLY_NAT_RULE_CANONICAL_READBACK_CONFIRMED",flush=True)
                generation=2
                try:
                    with socks_connect(orig_port) as new_flow:
                        assert echo(new_flow,b"after-first-migration")=="B"
                        # All existing flows stay pinned to their original Xray.
                        assert echo(old_flow,b"old-still-working")=="A"
                        if established_socket_witness(old_flow)!=legacy_socket_id:
                            raise Reject("HARD_NO_GO_OLD_TCP_SOCKET_ID_CHANGED_AFTER_SYN_CUTOVER")
                        print("RC27: OLD_TCP_SOCKET_INODE_UNCHANGED_POST_SWITCH",flush=True)
                        assert identity(old)==old_id and identity(candidate)==candidate_id
                        print("RC27: PASS_FIRST_INGRESS_SOCKS_NEW_ONLY_TO_API_XRAY_OLD_TCP_DRAINS",flush=True)

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
                        if established_socket_witness(old_flow)!=legacy_socket_id:
                            raise Reject("HARD_NO_GO_OLD_TCP_SOCKET_ID_CHANGED_DURING_FAILURE")
                        print("RC27: PASS_FAILED_CANDIDATE_NEW_REQUEST_BLOCKED_OLD_FLOW_LIVE",flush=True)

                        # Explicit rollback: remove ONLY the test-owned rule.
                        # Established candidate TCP remains bound to candidate.
                        if generation!=2 or identity(old)!=old_id or identity(candidate)!=candidate_id:
                            raise Reject("rollback PID/startticks/generation CAS failed")
                        exec_(*rollback_rule)
                        generation=3
                        with socks_connect(orig_port) as restored:
                            assert echo(restored,b"rollback")=="A"
                        assert echo(old_flow,b"old-survives-rollback")=="A"
                        if established_socket_witness(old_flow)!=legacy_socket_id:
                            raise Reject("HARD_NO_GO_OLD_TCP_SOCKET_ID_CHANGED_AT_ROLLBACK")
                        assert identity(old)==old_id and identity(candidate)==candidate_id
                        print("RC27: PASS_ROLLBACK_SAME_10808_OLD_PROCESS_PID_STARTTICKS_AND_CAS",flush=True)
                except BaseException:
                    # Remove only exact disposable NAT rule, never host/production.
                    exec_(*rollback_rule,check=False)
                    raise
                assert generation==3
                print("RC27: HARD_NO_GO_TPROXY_UDP_UNCOOPERATIVE_WATCHDOG_VENDOR_HARDWARE",flush=True)
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
        raise SystemExit("usage: python3 -m xray.lab.rc27_seamless_first_migration_socks Xray-wrapper")
    first_migration(sys.argv[1])
