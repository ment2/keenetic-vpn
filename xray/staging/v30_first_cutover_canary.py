#!/usr/bin/env python3
"""PROPOSED, NOT YET APPROVED OR DEPLOYED: bounded first API cutover CANARY.

Only a reversible trial: legacy Xray 10808/12345 -> API-enabled Xray for 15s,
then ALWAYS restore legacy. Does not change active config, init, iptables or
routing. May disconnect clients. Must not be installed/executed until the owner
approves the exact file hash and command after independent review.

The detached guardian is a single point of failure; no reboot, power loss,
real TPROXY packet forwarding, DNS/IPv6 leak, or worst-case recovery time proof
is claimed by offline CI. Treat code as release candidate, NOT production-ready.
"""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time


BACKUP = Path("/opt/var/backups/xray-v30-precutover-20261031-1045Z")
STATE_DIR = Path("/opt/var/run/xray-v30-canary")
STATE = STATE_DIR / "state.json"
READY = STATE_DIR / "guardian-ready.json"
LOCK = STATE_DIR / "txn.lock"
ACTIVE = Path("/opt/etc/xray/config.json")
XRAY = Path("/opt/sbin/xray")
WD_PIDFILE = Path("/opt/var/run/xray-watchdog.pid")
WIFI_PIDFILE = Path("/opt/var/run/xray-wifi.pid")
BACKUP_MANIFEST_SHA = "f27c336f66f1bbb9ef22a82f7e8aa84f80f9bee808b3a87abf6a5372e79d5c62"
BIN_SHA = "680db07db2b5d53080bfecb8752bc830c6a890367aa3bc57d42d4660506591f2"
BASE_SHA = "66d074f32fffbf4a251576c8297714e9647174546e9e73e5bf27cf2768efe6d7"
WD_SHA = "dddcc1d324e30b91df041378645ada869a18b4d35f2842383e5d319fc859e08"
WIFI_SHA = "6742e5e7f2a2bd41b85e9975371e7c46e66f0cfc6f5f843bf2c5dc1434c53601"


class GateError(RuntimeError):
    pass


def checksum(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for data in iter(lambda: f.read(1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def proc_state_and_ticks(pid):
    if not isinstance(pid, int) or pid <= 1:
        return None, None
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return fields[0], int(fields[19])
    except (OSError, ValueError, IndexError):
        return None, None


def ticks(pid):
    state, started = proc_state_and_ticks(pid)
    # Linux zombies retain their start_ticks until reaped. A detached guardian
    # is NOT the parent of the candidate and must treat a zombie as exited.
    return None if state in (None, "Z", "X") else started


def watcher_paused(identity):
    if not isinstance(identity, list) or len(identity) != 2:
        return False
    state, started = proc_state_and_ticks(identity[0])
    return started == identity[1] and state in ("T", "t")


def identity_live(pid, start_ticks):
    return ticks(pid) == start_ticks


def command_text(pid):
    try:
        return Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\x00", b" ").decode(errors="replace")
    except OSError:
        return ""


def owned_xray_pids():
    result = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            exe = (entry / "exe").resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        if exe == XRAY:
            result.append(int(entry.name))
    return sorted(result)


def pid_from_file(path, expected_substring):
    pid = int(Path(path).read_text().strip())
    start = ticks(pid)
    if start is None or expected_substring not in command_text(pid):
        raise GateError("PIDFILE identity invalid: " + path.name)
    return [pid, start]


def call(args, timeout=15):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=True).stdout


def safe_kernel():
    rules = call(["/opt/sbin/iptables", "-t", "mangle", "-S", "XRAY_WIFI"])
    if not all(s in rules for s in ("TPROXY", "--on-port 12345",
                                   "0x40000000/0x40000000")):
        raise GateError("TPROXY TCP/UDP policy absent")
    if "-p tcp" not in rules or "-p udp" not in rules:
        raise GateError("both TPROXY protocols required")
    ks = call(["/opt/sbin/iptables", "-S", "XRAY_KS_HOME"])
    if "-j DROP" not in ks or "-i br0" not in ks:
        raise GateError("Home fail-closed rule not found")
    iprule = call(["ip", "rule", "show"])
    if "0x40000000/0x40000000" not in iprule or "lookup 100" not in iprule:
        raise GateError("policy routing missing")
    table = call(["ip", "route", "show", "table", "100"])
    if "local default dev lo" not in table:
        raise GateError("TPROXY local route missing")
    ipv6 = call(["/opt/sbin/ip6tables", "-S", "FORWARD"])
    if "-P FORWARD DROP" not in ipv6:
        raise GateError("IPv6 forward policy not DROP")


def listeners_owned(pid):
    out = call(["netstat", "-lnptu"], timeout=8)
    rows = [row for row in out.splitlines() if f"{pid}/xray" in row]
    return (
        any(row.startswith("tcp") and "127.0.0.1:10808" in row for row in rows)
        and any(row.startswith("tcp") and ":12345" in row for row in rows)
        and any(row.startswith("udp") and ":12345" in row for row in rows)
    )


def verify_backup():
    if checksum(BACKUP / "manifest.json") != BACKUP_MANIFEST_SHA:
        raise GateError("private backup manifest changed")
    entries = json.loads((BACKUP / "manifest.json").read_text())["entries"]
    if len(entries) != 11:
        raise GateError("incomplete private backup")
    for e in entries:
        path = BACKUP / e["path"].lstrip("/")
        if checksum(path) != e["sha256"]:
            raise GateError("backup SHA mismatch")
    if checksum(BACKUP / "opt/etc/xray/config.json") != BASE_SHA:
        raise GateError("old config backup SHA mismatch")
    if checksum(ACTIVE) != BASE_SHA or checksum(XRAY) != BIN_SHA:
        raise GateError("active config or Xray binary changed")
    if checksum("/opt/bin/xray-watchdog.sh") != WD_SHA:
        raise GateError("legacy watchdog source changed")
    if checksum("/opt/etc/init.d/S98xray-wifi") != WIFI_SHA:
        raise GateError("wifi rule repair source changed")


def preflight(expected_pid, expected_ticks, expected_config_sha):
    if os.geteuid() != 0:
        raise GateError("root required")
    if expected_config_sha != BASE_SHA:
        raise GateError("expected SHA does not match pinned old config")
    if not identity_live(expected_pid, expected_ticks):
        raise GateError("old Xray PID/start_ticks changed")
    if owned_xray_pids() != [expected_pid] or not listeners_owned(expected_pid):
        raise GateError("unexpected process or non-exclusive SOCKS/TPROXY listeners")
    if "run -config /opt/etc/xray/config.json" not in command_text(expected_pid):
        raise GateError("old process command identity changed")
    verify_backup()
    safe_kernel()
    watchdog = pid_from_file(WD_PIDFILE, "/opt/bin/xray-watchdog.sh")
    wifi = pid_from_file(WIFI_PIDFILE, "/opt/etc/init.d/S98xray-wifi")
    if len({expected_pid, watchdog[0], wifi[0]}) != 3:
        raise GateError("watcher identity collision")
    return watchdog, wifi


def atomic_write(path, data):
    path = Path(path)
    temp = path.with_name("." + path.name + f".{os.getpid()}.tmp")
    with temp.open("w", encoding="utf-8") as f:
        os.chmod(temp, 0o600)
        json.dump(data, f, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def read_state():
    if STATE.is_symlink():
        raise GateError("unsafe journal symlink")
    return json.loads(STATE.read_text())


def state_update(**updates):
    data = read_state()
    data.update(updates)
    atomic_write(STATE, data)
    return data


@contextlib.contextmanager
def transaction_lock():
    STATE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(STATE_DIR, 0o700)
    with LOCK.open("a+") as f:
        os.chmod(LOCK, 0o600)
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def guarded_signal(identity, sig, expected_cmd):
    if not isinstance(identity, list) or len(identity) != 2:
        raise GateError("missing process identity")
    pid, start = identity
    if not identity_live(pid, start) or expected_cmd not in command_text(pid):
        raise GateError("PID/start_ticks/cmdline mismatch; no signal delivered")
    os.kill(pid, sig)


def wait_exit(pid, start_ticks, seconds):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        if not identity_live(pid, start_ticks):
            return True
        time.sleep(0.2)
    return not identity_live(pid, start_ticks)


def candidate_config():
    with ACTIVE.open(encoding="utf-8") as f:
        cfg = json.load(f)
    if cfg.get("api") or len(cfg.get("inbounds", [])) != 2 or len(cfg.get("outbounds", [])) != 8:
        raise GateError("base config unexpected or already API-enabled")
    if any(x.get("protocol") == "freedom" or x.get("tag") == "direct"
           for x in cfg["outbounds"]):
        raise GateError("internet direct fallback forbidden")
    existing = {x.get("tag") for x in cfg["inbounds"] + cfg["outbounds"]}
    if "v30-local-api" in existing:
        raise GateError("API tag collision")
    cfg["api"] = {"tag": "v30-local-api", "services": ["HandlerService", "RoutingService"]}
    cfg["inbounds"].append({
        "tag": "v30-local-api", "listen": "127.0.0.1",
        "port": 19090, "protocol": "dokodemo-door",
        "settings": {"address": "127.0.0.1"}
    })
    cfg["routing"].setdefault("rules", []).insert(
        0, {"type": "field", "inboundTag": ["v30-local-api"],
            "outboundTag": "v30-local-api"})
    target = STATE_DIR / "config.api.json"
    atomic_write(target, cfg)
    subprocess.run([str(XRAY), "run", "-test", "-config", str(target)],
                   check=True, timeout=20, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)
    return target


def tcp_check(port):
    with socket.create_connection(("127.0.0.1", port), timeout=2):
        return True


def socks_openai_check():
    command = ["/opt/bin/curl", "--socks5-hostname", "127.0.0.1:10808",
               "--connect-timeout", "4", "--max-time", "9",
               "-sS", "-o", "/dev/null", "-w", "%{http_code}",
               "https://api.openai.com/v1/models"]
    return call(command, timeout=12).strip() == "401"


def restore(reason):
    with transaction_lock():
        s = read_state()
        if s["phase"] in ("restored", "blocked"):
            return s["phase"]
        # Never change firewall, table100 or kill-switch.
        # Validate backup and binary even if candidate is broken.
        try:
            verify_backup()
            candidate = s.get("candidate")
            if candidate and identity_live(*candidate):
                guarded_signal(candidate, signal.SIGTERM, "config.api.json")
                if not wait_exit(*candidate, seconds=8):
                    raise GateError("candidate did not exit; do NOT SIGKILL")
            unexpected = owned_xray_pids()
            old = s["old"]
            if identity_live(*old):
                if unexpected != [old[0]]:
                    raise GateError("unexpected Xray still running")
                pid = old[0]
            else:
                if unexpected:
                    raise GateError("unknown Xray owns possible production ports")
                log = (STATE_DIR / "old-restore.log").open("a")
                try:
                    process = subprocess.Popen([str(XRAY), "run", "-config", str(ACTIVE)],
                                               stdin=subprocess.DEVNULL, stdout=log,
                                               stderr=subprocess.STDOUT, start_new_session=True)
                finally:
                    log.close()
                pid = process.pid
            until = time.monotonic() + 12
            while time.monotonic() < until:
                if ticks(pid) and listeners_owned(pid):
                    break
                time.sleep(0.3)
            else:
                raise GateError("old TCP/UDP listeners not restored")
            if not socks_openai_check():
                raise GateError("old SOCKS VPN probe failed")
            # Only resume original watchdog and S98 AFTER old Xray recovered.
            guarded_signal(s["wifi"], signal.SIGCONT, "/opt/etc/init.d/S98xray-wifi")
            guarded_signal(s["watchdog"], signal.SIGCONT, "/opt/bin/xray-watchdog.sh")
            state_update(phase="restored", reason=reason, restored_pid=pid,
                         restored_start_ticks=ticks(pid))
            return "restored"
        except Exception as exc:
            # Fail closed: never disable VPN-enforcing kernel policies or use direct.
            state_update(phase="blocked", reason=type(exc).__name__ + ": " + str(exc))
            return "blocked"


def guardian():
    # Detached independent process must be armed BEFORE old Xray is touched.
    s = read_state()
    if s.get("phase") != "armed" or s.get("expires") is None:
        raise GateError("guardian journal not armed")
    atomic_write(READY, {"pid": os.getpid(), "start_ticks": ticks(os.getpid())})
    while time.time() < s["expires"]:
        time.sleep(0.25)
        s = read_state()
        if s["phase"] in ("restored", "blocked"):
            return
        if s["phase"] in ("fenced", "legacy_stopping", "legacy_stopped",
                          "candidate_running", "canary_verified"):
            if not watcher_paused(s["watchdog"]) or not watcher_paused(s["wifi"]):
                restore("guardian_detected_unfenced_watchdog_or_S98")
                return
    restore("autonomous_guard_deadline")


def trial(args):
    if not args.accept_network_interruption:
        raise GateError("exact command approval required; no implicit cutover")
    watchdog, wifi = preflight(args.expected_old_pid, args.expected_old_ticks,
                                args.expected_config_sha)
    if STATE.exists():
        raise GateError("previous journal exists: inspect/resolve before new trial")
    if READY.exists():
        raise GateError("previous guardian exists")
    with transaction_lock():
        candidate_config()
        atomic_write(STATE, {
            "phase": "armed", "old": [args.expected_old_pid, args.expected_old_ticks],
            "watchdog": watchdog, "wifi": wifi, "candidate": None,
            "expires": time.time() + 90, "schema": 1
        })
    log = (STATE_DIR / "guardian.log").open("a")
    try:
        process = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--guardian"],
            stdin=subprocess.DEVNULL, stdout=log,
            stderr=subprocess.STDOUT, start_new_session=True)
    finally:
        log.close()
    until = time.monotonic() + 4
    while time.monotonic() < until:
        if READY.exists():
            ready = json.loads(READY.read_text())
            if ready.get("pid") == process.pid and identity_live(
                    process.pid, ready["start_ticks"]):
                break
        time.sleep(0.1)
    else:
        raise GateError("independent guardian failed to arm; old Xray untouched")

    try:
        with transaction_lock():
            guarded_signal(watchdog, signal.SIGSTOP, "/opt/bin/xray-watchdog.sh")
            guarded_signal(wifi, signal.SIGSTOP, "/opt/etc/init.d/S98xray-wifi")
            state_update(phase="fenced")
            # Must prove the watchdog and S98 *actually stopped* before
            # terminating the only production listener. SIGSTOP delivery alone
            # is not proof of fencing.
            for _ in range(15):
                if watcher_paused(watchdog) and watcher_paused(wifi):
                    break
                time.sleep(0.1)
            else:
                raise GateError("watchdog or S98 did not enter stopped state")
            safe_kernel()
            if owned_xray_pids() != [args.expected_old_pid]:
                raise GateError("competing Xray after watcher fence")
            guarded_signal([args.expected_old_pid, args.expected_old_ticks],
                           signal.SIGTERM, "run -config /opt/etc/xray/config.json")
            state_update(phase="legacy_stopping")
        if not wait_exit(args.expected_old_pid, args.expected_old_ticks, 8):
            raise GateError("legacy did not stop, no escalation")
        with transaction_lock():
            state_update(phase="legacy_stopped")
            log = (STATE_DIR / "candidate.log").open("a")
            try:
                p = subprocess.Popen(
                    [str(XRAY), "run", "-config", str(STATE_DIR / "config.api.json")],
                    stdin=subprocess.DEVNULL, stdout=log,
                    stderr=subprocess.STDOUT, start_new_session=True)
            finally:
                log.close()
            start_ticks = ticks(p.pid)
            if start_ticks is None:
                raise GateError("candidate failed before identity capture")
            state_update(candidate=[p.pid, start_ticks], phase="candidate_running")
        until = time.monotonic() + 10
        while time.monotonic() < until:
            if identity_live(p.pid, start_ticks) and listeners_owned(p.pid):
                break
            time.sleep(0.2)
        else:
            raise GateError("candidate not owner of TCP/UDP 10808/12345")
        if not tcp_check(19090) or not socks_openai_check():
            raise GateError("API or SOCKS reachability failed")
        safe_kernel()
        with transaction_lock():
            state_update(phase="canary_verified")
        # CANARY only, always restore old. Never write init/production config.
        for _ in range(15):
            current = read_state()
            if current["phase"] != "canary_verified":
                raise GateError("guard already initiated rollback")
            if not (watcher_paused(watchdog) and watcher_paused(wifi)):
                raise GateError("legacy watchdog/S98 fence lost during canary")
            safe_kernel()
            time.sleep(1)
    except Exception as exc:
        print("TRIAL_GATE_FAILED:", type(exc).__name__, str(exc), flush=True)
    outcome = restore("trial_completed_or_failed")
    print("TRIAL_END=" + outcome + " (must be restored, otherwise use local SSH)", flush=True)
    if outcome != "restored":
        raise GateError("recovery incomplete; check guardian journal over local SSH")


def main():
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--plan", action="store_true")
    action.add_argument("--trial", action="store_true")
    action.add_argument("--rollback", action="store_true")
    action.add_argument("--guardian", action="store_true")
    parser.add_argument("--expected-old-pid", type=int)
    parser.add_argument("--expected-old-ticks", type=int)
    parser.add_argument("--expected-config-sha")
    parser.add_argument("--accept-network-interruption", action="store_true")
    args = parser.parse_args()
    if args.guardian:
        guardian()
    elif args.rollback:
        print("ROLLBACK=" + restore("manual_emergency"), flush=True)
    else:
        if args.expected_old_pid is None or args.expected_old_ticks is None:
            parser.error("exact old PID and start_ticks required")
        if args.plan:
            watchdog, wifi = preflight(args.expected_old_pid, args.expected_old_ticks,
                                        args.expected_config_sha)
            print("READ_ONLY_PRECHECK_OK")
            print("WATCHDOG_PID_TICKS=" + ":".join(map(str, watchdog)))
            print("S98_PID_TICKS=" + ":".join(map(str, wifi)))
            print("GUARD_NOT_ARMED; NO_CHANGE; NO_APPROVAL")
        else:
            trial(args)


if __name__ == "__main__":
    main()
