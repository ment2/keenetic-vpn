#!/usr/bin/env python3
"""Two real Xray MIPS32LE processes, isolated GitHub runner only.

Tests two distinct SOCKS listeners, simulated client-side ingress selection,
TCP drain, PID/start ticks, candidate crash and rollback. This is NOT a
transparent production SOCKS/TPROXY handoff; no kernel routing is modified.
"""
import argparse
import contextlib
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
from xray.lab.xray_v30_api_continuity import EchoBackend, free_port, socks_connect, echo, wait_port


def start_ticks(pid):
    # /proc/<pid>/stat field 22; comm in parentheses may contain spaces.
    tail = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
    return int(tail[19])


def config(port, echo_port, api_port=None):
    inbounds = [{"tag": "socks", "listen": "127.0.0.1", "port": port,
                 "protocol": "socks", "settings": {"auth": "noauth", "udp": True}}]
    rules = [{"type": "field", "inboundTag": ["socks"], "outboundTag": "echo"},
             {"type": "field", "port": "0-65535", "outboundTag": "blocked"}]
    result = {"log": {"loglevel": "warning"}, "inbounds": inbounds,
              "outbounds": [
                  {"tag": "echo", "protocol": "freedom",
                   "settings": {"redirect": f"127.0.0.1:{echo_port}"}},
                  {"tag": "blocked", "protocol": "blackhole", "settings": {}}],
              "routing": {"rules": rules}}
    if api_port:
        result["api"] = {"tag": "api", "services": ["HandlerService", "RoutingService"]}
        inbounds.append({"tag": "api", "listen": "127.0.0.1", "port": api_port,
                         "protocol": "dokodemo-door", "settings": {"address": "127.0.0.1"}})
        rules.insert(0, {"type": "field", "inboundTag": ["api"], "outboundTag": "api"})
    return result


def run(xray):
    if Path("/opt/etc/xray/config.json").exists() or Path("/opt/etc/init.d/S97xray").exists():
        raise RuntimeError("production environment detected: abort")
    version = subprocess.run([xray, "version"], capture_output=True, text=True, timeout=20, check=True)
    assert "26.2.6" in version.stdout and "linux/mipsle" in version.stdout, version.stdout
    backend = EchoBackend("LAB")
    backend.start()
    ports = [free_port() for _ in range(3)]
    assert len(set(ports + [backend.port])) == 4
    old_port, new_port, api_port = ports
    processes = []
    with tempfile.TemporaryDirectory(prefix="xray-v30-dual-") as td:
        try:
            for name, port, api in (("old", old_port, None), ("new", new_port, api_port)):
                file = Path(td) / f"{name}.json"
                file.write_text(json.dumps(config(port, backend.port, api)))
                subprocess.run([xray, "run", "-test", "-config", str(file)],
                               check=True, timeout=25, stdout=subprocess.DEVNULL)
                p = subprocess.Popen([xray, "run", "-config", str(file)],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                processes.append(p)
                wait_port(port, p, timeout=20)
                print("PROCESS", name, "PID", p.pid, "start_ticks", start_ticks(p.pid), flush=True)
            old, new = processes
            assert old.pid != new.pid
            assert start_ticks(old.pid) != 0 and start_ticks(new.pid) != 0
            with socks_connect(old_port) as old_tcp:
                assert echo(old_tcp, b"before") == "LAB"
                with socks_connect(new_port) as new_tcp:
                    assert echo(new_tcp, b"after") == "LAB"
                assert echo(old_tcp, b"still-old") == "LAB"
                print("DUAL_RESULT: PASS old TCP stays alive while candidate handles new TCP", flush=True)
                # Candidate fails after synthetic client ingress selection.
                new.terminate()
                new.wait(timeout=10)
                assert old.poll() is None
                with socks_connect(old_port) as rollback_tcp:
                    assert echo(rollback_tcp, b"rollback") == "LAB"
                assert echo(old_tcp, b"still-old-after-rollback") == "LAB"
                print("DUAL_RESULT: PASS candidate killed, old process serves rollback TCP", flush=True)
            # Verify candidate death cannot be mistaken for healthy ingress.
            try:
                with socket.create_connection(("127.0.0.1", new_port), timeout=1):
                    raise AssertionError("dead candidate still accepts TCP")
            except ConnectionRefusedError:
                pass
            print("DUAL_RESULT: PASS candidate listener unavailable, no direct fallback", flush=True)
        finally:
            for p in processes:
                if p.poll() is None:
                    p.terminate()
                    try:
                        p.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        p.kill()
                        p.wait(timeout=10)
            backend.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--xray", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        parser.error("explicit --run required")
    run(args.xray)
