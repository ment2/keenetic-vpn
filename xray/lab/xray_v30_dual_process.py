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
import threading
from xray.lab.xray_v30_api_continuity import EchoBackend, free_port, socks_connect, echo, wait_port


def start_ticks(pid):
    # /proc/<pid>/stat field 22; comm in parentheses may contain spaces.
    tail = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
    return int(tail[19])


def config(port, echo_port, api_port=None, udp_port=None):
    inbounds = [{"tag": "socks", "listen": "127.0.0.1", "port": port,
                 "protocol": "socks", "settings": {"auth": "noauth", "udp": False}}]
    rules = [{"type": "field", "inboundTag": ["socks"], "outboundTag": "echo"},
             {"type": "field", "port": "0-65535", "outboundTag": "blocked"}]
    result = {"log": {"loglevel": "warning"}, "inbounds": inbounds,
              "outbounds": [
                  {"tag": "echo", "protocol": "freedom",
                   "settings": {"redirect": f"127.0.0.1:{echo_port}"}},
                  {"tag": "blocked", "protocol": "blackhole", "settings": {}}],
              "routing": {"rules": rules}}
    if udp_port:
        result["outbounds"].insert(1, {"tag": "udp-echo", "protocol": "freedom",
                                         "settings": {"redirect": f"127.0.0.1:{udp_port}"}})
        rules.insert(0, {"type": "field", "inboundTag": ["socks"],
                         "network": "udp", "outboundTag": "udp-echo"})
    if api_port:
        result["api"] = {"tag": "api", "services": ["HandlerService", "RoutingService"]}
        inbounds.append({"tag": "api", "listen": "127.0.0.1", "port": api_port,
                         "protocol": "dokodemo-door", "settings": {"address": "127.0.0.1"}})
        rules.insert(0, {"type": "field", "inboundTag": ["api"], "outboundTag": "api"})
    return result


class UdpEcho:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("127.0.0.1", 0))
        self.socket.settimeout(0.2)
        self.port = self.socket.getsockname()[1]
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.serve, daemon=True)

    def serve(self):
        while not self.stop.is_set():
            try:
                data, peer = self.socket.recvfrom(4096)
                self.socket.sendto(b"UDP:" + data, peer)
            except socket.timeout:
                continue
            except OSError:
                break

    def start(self):
        self.thread.start()

    def close(self):
        self.stop.set()
        self.socket.close()
        self.thread.join(timeout=2)


def udp_associate(socks_port, payload):
    # SOCKS5 UDP ASSOCIATE, RFC 1928; control TCP remains open.
    with socket.create_connection(("127.0.0.1", socks_port), timeout=15) as control:
        control.settimeout(15)
        control.sendall(b"\\x05\\x01\\x00")
        assert control.recv(2) == b"\\x05\\x00"
        control.sendall(b"\\x05\\x03\\x00\\x01\\x00\\x00\\x00\\x00\\x00\\x00")
        reply = control.recv(64)
        assert len(reply) >= 10 and reply[1] == 0 and reply[3] == 1, reply
        relay_ip = socket.inet_ntoa(reply[4:8])
        relay_port = int.from_bytes(reply[8:10], "big")
        if relay_ip == "0.0.0.0":
            relay_ip = "127.0.0.1"
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
            udp.settimeout(15)
            packet = b"\\x00\\x00\\x00\\x01\\x7f\\x00\\x00\\x01" + (19000).to_bytes(2, "big") + payload
            udp.sendto(packet, (relay_ip, relay_port))
            result, _ = udp.recvfrom(4096)
            assert result[:3] == b"\\x00\\x00\\x00"
            assert result.endswith(b"UDP:" + payload), result
            return result


def run(xray):
    if Path("/opt/etc/xray/config.json").exists() or Path("/opt/etc/init.d/S97xray").exists():
        raise RuntimeError("production environment detected: abort")
    version = subprocess.run([xray, "version"], capture_output=True, text=True, timeout=20, check=True)
    assert "26.2.6" in version.stdout and "linux/mipsle" in version.stdout, version.stdout
    backend = EchoBackend("LAB")
    backend.start()
    udp_backend = UdpEcho()
    udp_backend.start()
    ports = [free_port() for _ in range(3)]
    assert len(set(ports + [backend.port])) == 4
    old_port, new_port, api_port = ports
    processes = []
    with tempfile.TemporaryDirectory(prefix="xray-v30-dual-") as td:
        try:
            for name, port, api in (("old", old_port, None), ("new", new_port, api_port)):
                file = Path(td) / f"{name}.json"
                file.write_text(json.dumps(config(port, backend.port, api, udp_backend.port)))
                subprocess.run([xray, "run", "-test", "-config", str(file)],
                               check=True, timeout=25, stdout=subprocess.DEVNULL)
                p = subprocess.Popen([xray, "run", "-config", str(file)],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                processes.append(p)
                wait_port(port, p, timeout=20)
                print("PROCESS", name, "PID", p.pid, "start_ticks", start_ticks(p.pid), flush=True)
            old, new = processes
            print("DUAL_RESULT: UDP ASSOCIATE pending separate diagnostic; TCP regression kept fail-closed", flush=True)
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
            udp_backend.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--xray", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        parser.error("explicit --run required")
    run(args.xray)
