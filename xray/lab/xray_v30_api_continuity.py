#!/usr/bin/env python3
"""Isolated Xray 26.2.6 loopback API/BO/TCP continuity laboratory.

Only for disposable CI Linux runners, NEVER for production router.
Uses loopback ports chosen by OS, fake local echo backends, no VPN credentials.
Runs only with explicit --run, and checks absence of production router environment.
"""
import argparse
import contextlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class EchoBackend:
    def __init__(self, label):
        self.label = label
        self.port = free_port()
        self.stop = threading.Event()
        self.server = socket.socket()
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(("127.0.0.1", self.port))
        self.server.listen()
        self.server.settimeout(0.2)
        self.connections = []
        self.thread = threading.Thread(target=self.serve, daemon=True)

    def serve(self):
        while not self.stop.is_set():
            try:
                client, _ = self.server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            self.connections.append(client)
            threading.Thread(target=self.handle, args=(client,), daemon=True).start()

    def handle(self, client):
        with client:
            client.settimeout(0.5)
            while not self.stop.is_set():
                try:
                    data = client.recv(1024)
                    if not data:
                        break
                    client.sendall(self.label.encode() + b":" + data)
                except socket.timeout:
                    continue
                except OSError:
                    break

    def start(self):
        self.thread.start()

    def close(self):
        self.stop.set()
        self.server.close()
        for c in self.connections:
            with contextlib.suppress(OSError):
                c.close()
        self.thread.join(timeout=2)


def config(api_port, socks_port, a_port, b_port, strategy="random"):
    return {
        "log": {"loglevel": "warning"},
        "api": {"tag": "lab-api", "services": ["HandlerService", "RoutingService"]},
        "observatory": {"subjectSelector": ["lab-a", "lab-b"], "probeURL": "http://127.0.0.1:19000", "probeInterval": "1m"},
        "inbounds": [
            {"tag": "lab-api", "listen": "127.0.0.1", "port": api_port,
             "protocol": "dokodemo-door", "settings": {"address": "127.0.0.1"}},
            {"tag": "lab-socks", "listen": "127.0.0.1", "port": socks_port,
             "protocol": "socks", "settings": {"auth": "noauth", "udp": False}},
        ],
        "outbounds": [
            {"tag": "lab-a", "protocol": "freedom",
             "settings": {"redirect": f"127.0.0.1:{a_port}"}},
            {"tag": "lab-b", "protocol": "freedom",
             "settings": {"redirect": f"127.0.0.1:{b_port}"}},
            {"tag": "lab-blocked", "protocol": "blackhole", "settings": {}},
        ],
        "routing": {
            "domainStrategy": "AsIs",
            "balancers": [{"tag": "lab-balancer", "selector": ["lab-a", "lab-b", "lab-c"],
                           "strategy": {"type": strategy}, "fallbackTag": "lab-a"}],
            "rules": [
                {"type": "field", "inboundTag": ["lab-api"], "outboundTag": "lab-api"},
                {"type": "field", "inboundTag": ["lab-socks"], "balancerTag": "lab-balancer"},
                {"type": "field", "port": "0-65535", "outboundTag": "lab-blocked"},
            ],
        },
    }


def socks_connect(port):
    s = socket.create_connection(("127.0.0.1", port), timeout=3)
    s.settimeout(4)
    s.sendall(b"\x05\x01\x00")
    assert s.recv(2) == b"\x05\x00", "SOCKS authentication failed"
    s.sendall(b"\x05\x01\x00\x01\x7f\x00\x00\x01" + (19000).to_bytes(2, "big"))
    response = s.recv(10)
    assert len(response) >= 2 and response[1] == 0, f"SOCKS connect failed: {response!r}"
    return s


def echo(sock, message):
    sock.sendall(message)
    received = sock.recv(1024)
    assert received.endswith(message), f"bad echo: {received!r}"
    return received.split(b":", 1)[0].decode()


def wait_port(port, process, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"lab Xray exited early: {process.returncode}")
        with contextlib.suppress(OSError):
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        time.sleep(0.1)
    raise RuntimeError("lab listener not ready")


def run(xray, strategy="random"):
    if Path("/opt/etc/xray/config.json").exists() or Path("/opt/etc/init.d/S97xray").exists():
        raise RuntimeError("router/Entware detected: lab execution forbidden")
    result = subprocess.run([xray, "version"], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0 and "26.2.6" in result.stdout.splitlines()[0], (
        "lab requires Xray 26.2.6; " + result.stdout[:160])
    a, b, c = EchoBackend("A"), EchoBackend("B"), EchoBackend("C")
    api_port, socks_port = free_port(), free_port()
    assert len({api_port, socks_port, a.port, b.port, c.port}) == 5
    a.start()
    b.start()
    c.start()
    proc = None
    try:
        with tempfile.TemporaryDirectory(prefix="xray-v30-ci-") as td:
            cfg = Path(td) / "lab.json"
            cfg.write_text(json.dumps(config(api_port, socks_port, a.port, b.port, strategy)))
            baseline = json.loads(cfg.read_text())
            variants = {
                "full": baseline,
                "no_api": {**baseline, "api": None,
                           "inbounds": [x for x in baseline["inbounds"] if x["tag"] != "lab-api"],
                           "routing": {**baseline["routing"],
                                       "rules": [x for x in baseline["routing"]["rules"]
                                                 if x.get("outboundTag") != "lab-api"]}},
                "no_balancer": {**baseline,
                                "routing": {**baseline["routing"], "balancers": [],
                                            "rules": [dict(x, outboundTag="lab-a")
                                                      if x.get("balancerTag") else x
                                                      for x in baseline["routing"]["rules"]]}},
            }
            for label, obj in variants.items():
                obj = {k: v for k, v in obj.items() if v is not None}
                vfile = Path(td) / (label + ".json")
                vfile.write_text(json.dumps(obj))
                v = subprocess.run([xray, "run", "-test", "-config", str(vfile)],
                                   capture_output=True, text=True, timeout=10)
                print("CONFIG_MATRIX", label, "exit", v.returncode,
                      (v.stdout + v.stderr)[-350:], flush=True)
            subprocess.run([xray, "run", "-test", "-config", str(cfg)], check=True, timeout=10)
            proc = subprocess.Popen([xray, "run", "-config", str(cfg)],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            wait_port(socks_port, proc)
            wait_port(api_port, proc)
            def api(*args):
                return subprocess.run([xray, "api", args[0], "-s", f"127.0.0.1:{api_port}", *args[1:]],
                                      capture_output=True, text=True, timeout=8, check=True)
            # Force old endpoint A. The first connection is intentionally kept open.
            api("bo", "-b", "lab-balancer", "lab-a")
            old = socks_connect(socks_port)
            try:
                assert echo(old, b"before") == "A"
                api("bo", "-b", "lab-balancer", "lab-b")
                with socks_connect(socks_port) as new:
                    assert echo(new, b"after") == "B"
                assert echo(old, b"still-alive") == "A", "existing TCP connection was disrupted"
                print("LAB_RESULT: PASS old TCP=A after BO; new TCP=B", flush=True)
                added = Path(td) / "add-c.json"
                added.write_text(json.dumps({"outbounds": [
                    {"tag": "lab-c", "protocol": "freedom",
                     "settings": {"redirect": f"127.0.0.1:{c.port}"}}
                ]}))
                api("ado", str(added))
                api("bo", "-b", "lab-balancer", "lab-c")
                with socks_connect(socks_port) as newest:
                    assert echo(newest, b"added") == "C"
                assert echo(old, b"still-alive-after-ado") == "A"
                print("LAB_RESULT: PASS dynamic ADO outbound C; old TCP still A", flush=True)
                # Remove B only after its test socket has closed; never remove active A.
                api("rmo", "lab-b")
                with socks_connect(socks_port) as post_remove:
                    assert echo(post_remove, b"after-drain") == "C"
                assert echo(old, b"still-alive-after-rmo") == "A"
                print("LAB_RESULT: PASS RMO drained B; new TCP=C; old TCP=A", flush=True)
            finally:
                old.close()
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate(timeout=5)
        a.close()
        b.close()
        c.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--xray", required=True)
    parser.add_argument("--run", action="store_true", help="explicit opt-in, CI sandbox only")
    parser.add_argument("--strategy", choices=["random", "leastPing"], default="random")
    args = parser.parse_args()
    if not args.run:
        parser.error("--run required; never execute on production router")
    run(args.xray, args.strategy)


if __name__ == "__main__":
    main()
