#!/usr/bin/env python3
"""Disposable dual-Xray MIPS32LE dokodemo-door TCP/UDP lab.

This exercises actual Xray 26.2.6 TCP/UDP forwarding and candidate failure
under QEMU with loopback destinations. It is NOT an iptables TPROXY or
SO_MARK/followRedirect/kernel transparency test, nor stable UDP ingress.
Synthetic 'freedom' is restricted to 127.0.0.1, never an Internet fallback.
NEVER launch on Keenetic production.
"""
import argparse
import contextlib
import json
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import time

from xray.lab.xray_v30_api_continuity import EchoBackend, free_port, wait_port
from xray.lab.stable_socks_ingress_v30 import proc_start_ticks


class UdpEcho:
    def __init__(self, label):
        self.label = label.encode()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("127.0.0.1", 0))
        self.port = self.socket.getsockname()[1]
        self.socket.settimeout(.2)
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.serve, daemon=True)

    def start(self):
        self.thread.start()
        return self

    def serve(self):
        while not self.stop.is_set():
            try:
                data, addr = self.socket.recvfrom(4096)
                self.socket.sendto(self.label + b":" + data, addr)
            except socket.timeout:
                continue
            except OSError:
                break

    def close(self):
        self.stop.set()
        self.socket.close()
        self.thread.join(timeout=2)


def dokodemo_config(tcp_port, udp_port, backend_tcp, backend_udp):
    """Never add an Internet routing fallback. Both targets are loopback."""
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {"listen": "127.0.0.1", "port": tcp_port, "tag": "lab-tcp",
             "protocol": "dokodemo-door",
             "settings": {"address": "127.0.0.1", "port": backend_tcp,
                          "network": "tcp", "followRedirect": False}},
            {"listen": "127.0.0.1", "port": udp_port, "tag": "lab-udp",
             "protocol": "dokodemo-door",
             "settings": {"address": "127.0.0.1", "port": backend_udp,
                          "network": "udp", "followRedirect": False}},
        ],
        "outbounds": [
            {"tag": "lab-loopback", "protocol": "freedom", "settings": {}},
            {"tag": "blocked", "protocol": "blackhole", "settings": {}},
        ],
        "routing": {"rules": [
            {"type": "field", "inboundTag": ["lab-tcp", "lab-udp"],
             "outboundTag": "lab-loopback"},
            {"type": "field", "port": "0-65535", "outboundTag": "blocked"},
        ]},
    }


def udp_roundtrip(port, label, marker):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
        client.bind(("127.0.0.1", 0))
        client.settimeout(3)
        expected = label.encode() + b":" + marker
        # A bounded retry handles UDP listener startup without silent skips.
        for _ in range(5):
            client.sendto(marker, ("127.0.0.1", port))
            try:
                response, _ = client.recvfrom(4096)
                assert response == expected, (response, expected)
                return
            except socket.timeout:
                continue
    raise AssertionError("UDP loopback roundtrip timed out")


def tcp_roundtrip(port, label, marker, existing=None):
    with contextlib.ExitStack() as stack:
        sock = existing if existing is not None else stack.enter_context(
            socket.create_connection(("127.0.0.1", port), timeout=4))
        sock.settimeout(4)
        sock.sendall(marker)
        response = sock.recv(1024)
        assert response == label.encode() + b":" + marker, response


def run(xray):
    if Path("/opt/etc/xray/config.json").exists() or Path("/opt/etc/init.d/S97xray").exists():
        raise RuntimeError("production/Entware environment detected: refuse to run")
    version = subprocess.run([xray, "version"], text=True, capture_output=True,
                             timeout=20, check=True).stdout
    assert "26.2.6" in version and "linux/mipsle" in version, version
    t_old, t_new = EchoBackend("OLD"), EchoBackend("NEW")
    u_old, u_new = UdpEcho("OLD"), UdpEcho("NEW")
    for backend in (t_old, t_new, u_old, u_new):
        backend.start()
    processes = []
    endpoints = []
    try:
        with tempfile.TemporaryDirectory(prefix="xray-v30-dokodemo-") as temp:
            ports = [free_port() for _ in range(4)]
            assert len(set(ports + [t_old.port, t_new.port, u_old.port, u_new.port])) == 8
            for idx, (label, t, u) in enumerate((("OLD", t_old, u_old), ("NEW", t_new, u_new))):
                tcp, udp = ports[idx*2:idx*2+2]
                cfg = Path(temp) / ("old.json" if idx == 0 else "candidate.json")
                cfg.write_text(json.dumps(dokodemo_config(tcp, udp, t.port, u.port)))
                subprocess.run([xray, "run", "-test", "-config", str(cfg)],
                               check=True, timeout=25, stdout=subprocess.DEVNULL)
                p = subprocess.Popen([xray, "run", "-config", str(cfg)],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                processes.append(p)
                wait_port(tcp, p, timeout=25)
                assert proc_start_ticks(p.pid) > 0
                endpoints.append((tcp, udp))
                udp_roundtrip(udp, label, b"initial")
            (old_tcp_port, old_udp_port), (new_tcp_port, new_udp_port) = endpoints
            with socket.create_connection(("127.0.0.1", old_tcp_port), timeout=4) as old_flow:
                tcp_roundtrip(old_tcp_port, "OLD", b"before", old_flow)
                tcp_roundtrip(new_tcp_port, "NEW", b"candidate")
                udp_roundtrip(new_udp_port, "NEW", b"candidate")
                tcp_roundtrip(old_tcp_port, "OLD", b"still-old", old_flow)
                print("DOKODEMO_LAB: PASS real MIPSLE TCP and UDP on both isolated dokodemo listeners", flush=True)
                processes[1].terminate()
                processes[1].wait(timeout=15)
                assert processes[0].poll() is None
                udp_roundtrip(old_udp_port, "OLD", b"after-candidate-failure")
                tcp_roundtrip(old_tcp_port, "OLD", b"persisted", old_flow)
                tcp_roundtrip(old_tcp_port, "OLD", b"new-after-rollback")
                print("DOKODEMO_LAB: PASS old TCP/UDP after candidate crash; old TCP flow survives", flush=True)
                try:
                    with socket.create_connection(("127.0.0.1", new_tcp_port), timeout=1):
                        raise AssertionError("dead candidate unexpectedly accepting TCP")
                except (ConnectionRefusedError, OSError):
                    pass
            print("DOKODEMO_LAB: NOT TESTED kernel TPROXY, followRedirect, fwmark, stable UDP ingress, DNS, IPv6, kill-switch", flush=True)
    finally:
        for p in processes:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait(timeout=10)
        for backend in (t_old, t_new, u_old, u_new):
            backend.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--xray", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        parser.error("--run required (disposable CI only)")
    run(args.xray)
