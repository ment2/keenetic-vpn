#!/usr/bin/env python3
import argparse
import json
import os
import socket
import subprocess
import tempfile
import time
from pathlib import Path

XRAY = "/opt/sbin/xray"
CURL = "/opt/bin/curl"

def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

def probe(outbound):
    port = free_port()
    config = {
        "log": {"loglevel": "warning"},
        "inbounds": [{
            "tag": "probe-in",
            "listen": "127.0.0.1",
            "port": port,
            "protocol": "socks",
            "settings": {"auth": "noauth", "udp": False}
        }],
        "outbounds": [dict(outbound, tag="probe-out")],
        "routing": {
            "rules": [{
                "type": "field",
                "inboundTag": ["probe-in"],
                "outboundTag": "probe-out"
            }]
        }
    }

    with tempfile.TemporaryDirectory(
        prefix="xray-probe-"
    ) as td:
        path = Path(td) / "config.json"
        path.write_text(json.dumps(config))
        os.chmod(path, 0o600)

        try:
            test = subprocess.run(
                [XRAY, "run", "-test", "-config", str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10
            )
            if test.returncode:
                return {"status": "invalid_config"}

            proc = subprocess.Popen(
                [XRAY, "run", "-config", str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except (OSError, subprocess.TimeoutExpired):
            return {"status": "startup_error"}

        try:
            for _ in range(30):
                if proc.poll() is not None:
                    return {"status": "xray_exited"}
                with socket.socket() as s:
                    if s.connect_ex(("127.0.0.1", port)) == 0:
                        break
                time.sleep(0.2)
            else:
                return {"status": "startup_timeout"}

            env = {
                k: v for k, v in os.environ.items()
                if k.lower() not in (
                    "http_proxy", "https_proxy",
                    "all_proxy", "no_proxy"
                )
            }

            cmd = [
                CURL,
                "--silent", "--show-error", "--fail",
                "--noproxy", "",
                "--proxy", f"socks5h://127.0.0.1:{port}",
                "--connect-timeout", "7",
                "--max-time", "20",
                "https://ipwho.is/"
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=23,
                env=env
            )

            if result.returncode:
                return {"status": "network_error"}

            if len(result.stdout) > 8192:
                return {"status": "invalid_response"}

            data = json.loads(result.stdout)

            if (
                data.get("success") is not True
                or not isinstance(data.get("ip"), str)
                or not isinstance(data.get("country_code"), str)
                or len(data["country_code"]) != 2
            ):
                return {"status": "geo_unavailable"}

            return {
                "status": "ok",
                "ip": data["ip"],
                "country_code": data["country_code"].upper()
            }

        except (OSError, ValueError,
                subprocess.TimeoutExpired):
            return {"status": "probe_error"}

        finally:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="/opt/etc/xray/config.json"
    )
    parser.add_argument("--limit", type=int, default=1)
    args = parser.parse_args()

    if not 1 <= args.limit <= 100:
        parser.error("--limit must be 1..100")

    cfg = json.loads(
        Path(args.config).read_text()
    )

    servers = [
        x for x in cfg.get("outbounds", [])
        if x.get("protocol") == "vless"
    ]

    print("servers_in_config:", len(servers), flush=True)

    for i, server in enumerate(
        servers[:args.limit], 1
    ):
        result = probe(server)
        print(json.dumps({
            "index": i,
            "tag": server.get("tag"),
            **result
        }), flush=True)

if __name__ == "__main__":
    main()
