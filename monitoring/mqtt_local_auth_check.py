"""Local-only MQTT 3.1.1 credential test without publishing messages.

Run from the HA host/container network, not over an unencrypted external LAN.
Prompts privately for a password, prints only the broker response code.
"""
import argparse
import getpass
import socket
import struct

RETURN_CODES = {
    0: "accepted",
    1: "unacceptable_protocol",
    2: "identifier_rejected",
    3: "server_unavailable",
    4: "bad_username_or_password",
    5: "not_authorized",
}

def mqtt_string(s: str) -> bytes:
    b = s.encode("utf-8")
    if len(b) > 65535:
        raise ValueError("string too long")
    return struct.pack("!H", len(b)) + b

def remaining_length(n: int) -> bytes:
    out = bytearray()
    while True:
        d = n % 128
        n //= 128
        if n:
            d |= 0x80
        out.append(d)
        if not n:
            return bytes(out)

def connect_packet(username: str, password: str, client_id="keenetic-monitor-auth-check") -> bytes:
    # MQTT 3.1.1 CONNECT: clean session, username + password.
    body = mqtt_string("MQTT") + bytes([4, 0xC2]) + struct.pack("!H", 10)
    body += mqtt_string(client_id) + mqtt_string(username) + mqtt_string(password)
    return b"\x10" + remaining_length(len(body)) + body

def test_once(host: str, port: int, username: str, password: str) -> int:
    # No insecure client-side logging, no publish, no retained state.
    with socket.create_connection((host, port), timeout=5) as sock:
        sock.settimeout(5)
        sock.sendall(connect_packet(username, password))
        answer = sock.recv(4)
    if len(answer) != 4 or answer[:3] != b"\x20\x02\x00":
        raise RuntimeError("invalid broker response")
    return answer[3]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="core-mosquitto")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--username", default="keenetic_monitor")
    args = parser.parse_args()
    if args.host not in ("core-mosquitto", "127.0.0.1", "localhost"):
        parser.error("local test only: remote plaintext MQTT forbidden")
    pwd = getpass.getpass("MQTT password (not echoed): ")
    try:
        code = test_once(args.host, args.port, args.username, pwd)
        print("MQTT_AUTH", RETURN_CODES.get(code, "unexpected_code_" + str(code)))
    except Exception as exc:
        print("MQTT_AUTH_ERROR", type(exc).__name__)
