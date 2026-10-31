#!/usr/bin/env python3
"""TCP+UDP test echo/client in isolated disposable Linux network namespaces.

Commands:
  server: bind 10.199.72.2:19090 in a named network namespace.
  client: assert TCP and UDP payload arrive through transparent gateway.
  blocked: assert both transports fail after Xray is terminated and FORWARD=DROP.
Lab only: not for production routers. No external Internet destination.
"""
import socket
import sys
import threading
import time

HOST = "10.199.72.2"
PORT = 19090
PAYLOAD_TCP = b"v30-tcp"
PAYLOAD_UDP = b"v30-udp"


def server():
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp.bind((HOST, PORT))
    tcp.listen(10)
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.bind((HOST, PORT))
    print("NETNS: synthetic TCP/UDP server ready", flush=True)
    def accept():
        while True:
            c, _ = tcp.accept()
            def handle(connection):
                with connection:
                    while True:
                        data = connection.recv(4096)
                        if not data: break
                        connection.sendall(b"LAB:" + data)
            threading.Thread(target=handle, args=(c,), daemon=True).start()
    threading.Thread(target=accept, daemon=True).start()
    while True:
        data, src = udp.recvfrom(4096)
        udp.sendto(b"LAB:" + data, src)


def client():
    with socket.create_connection((HOST, PORT), timeout=5) as s:
        s.settimeout(5)
        s.sendall(PAYLOAD_TCP)
        ans = s.recv(4096)
        assert ans == b"LAB:" + PAYLOAD_TCP, ans
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as u:
        u.settimeout(5)
        u.sendto(PAYLOAD_UDP, (HOST, PORT))
        ans, _ = u.recvfrom(4096)
        assert ans == b"LAB:" + PAYLOAD_UDP, ans
    print("KERNEL_TPROXY: PASS IPv4 TCP+UDP through netns mangle/fwmark/table100", flush=True)


def blocked():
    tcp_replied = False
    try:
        with socket.create_connection((HOST, PORT), timeout=2) as s:
            s.settimeout(2)
            s.sendall(PAYLOAD_TCP)
            tcp_replied = s.recv(4096) == b"LAB:" + PAYLOAD_TCP
    except OSError:
        pass
    udp_replied = False
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as u:
        u.settimeout(2)
        u.sendto(PAYLOAD_UDP, (HOST, PORT))
        try:
            ans, _ = u.recvfrom(4096)
            udp_replied = ans == b"LAB:" + PAYLOAD_UDP
        except OSError:
            pass
    assert not tcp_replied and not udp_replied, "direct bypass was possible"
    print("KERNEL_TPROXY: PASS isolated TCP+UDP blocked with dead Xray", flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("server", "client", "blocked"):
        raise SystemExit("usage: server|client|blocked (disposable GitHub runner only)")
    {"server": server, "client": client, "blocked": blocked}[sys.argv[1]]()
