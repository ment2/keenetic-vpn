"""Minimal MQTT 3.1.1 QoS1 publisher over LAN, no third-party modules.

Password must be loaded locally from a root-only file. No retries by default.
"""
import json
import socket
import struct
from pathlib import Path

def _field(text):
    raw = text.encode("utf-8")
    if len(raw) > 65535:
        raise ValueError("MQTT string too long")
    return struct.pack("!H", len(raw)) + raw

def _remaining(value):
    if not 0 <= value <= 268435455:
        raise ValueError("MQTT size")
    result = bytearray()
    while True:
        byte = value % 128
        value //= 128
        result.append(byte | (128 if value else 0))
        if not value:
            return bytes(result)

def _recv_exact(sock, amount):
    chunks = bytearray()
    while len(chunks) < amount:
        part = sock.recv(amount - len(chunks))
        if not part:
            raise ConnectionError("broker closed connection")
        chunks.extend(part)
    return bytes(chunks)

def _packet(kind, payload):
    return bytes([kind]) + _remaining(len(payload)) + payload

def publish_once(*, host, port, username, password, topic, payload, client_id="keenetic-traffic-monitor", retain=False):
    if not isinstance(topic, str) or not (topic.startswith("keenetic/vpn-monitor/v1/") or (topic.startswith("homeassistant/sensor/keenetic6059_") and topic.endswith("/config"))) or any(c in topic for c in "+#\x00"):
        raise ValueError("topic not allowed")
    if not 1 <= port <= 65535:
        raise ValueError("port")
    data = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode()
    if len(data) > (32768 if topic == "keenetic/vpn-monitor/v1/dynamic_rc2" else 4096):
        raise ValueError("payload too large")
    connect = (_field("MQTT") + b"\x04\xc2" + struct.pack("!H", 20)
               + _field(client_id) + _field(username) + _field(password))
    # QoS1, optional retain for Home Assistant discovery only, packet identifier 1
    message = _field(topic) + b"\x00\x01" + data
    with socket.create_connection((host, port), timeout=5) as sock:
        sock.settimeout(5)
        sock.sendall(_packet(0x10, connect))
        if _recv_exact(sock, 4) != b"\x20\x02\x00\x00":
            raise PermissionError("MQTT CONNECT rejected")
        sock.sendall(_packet(0x33 if retain else 0x32, message))
        if _recv_exact(sock, 4) != b"\x40\x02\x00\x01":
            raise RuntimeError("MQTT PUBACK absent")
        sock.sendall(b"\xe0\x00")

def load_password(path):
    p = Path(path)
    st = p.stat()
    if st.st_mode & 0o077:
        raise PermissionError("credentials file must not be group/world accessible")
    return p.read_text(encoding="utf-8").rstrip("\r\n")
