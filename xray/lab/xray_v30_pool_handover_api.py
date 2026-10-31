#!/usr/bin/env python3
"""Real MIPS32LE QEMU API pool handover with preserve-current endpoint policy.

After a ONE-TIME API migration (not done here), refresh a verified pool without
switching the still-qualified active endpoint. Real SOCKS TCP, synthetic loopback
echo VPN stand-ins. No real VLESS, Telegram, TPROXY, UDP or production commands.
"""
import argparse
import contextlib
import json
from pathlib import Path
import subprocess
import tempfile

from xray.lab.pool_reconcile_v30 import reconcile
from xray.lab.pool_generation_v30 import Coordinator, Generation
from xray.lab.xray_v30_api_continuity import (
    EchoBackend, config, echo, free_port, socks_connect, wait_port,
)


def run(xray):
    if Path("/opt/etc/xray/config.json").exists() or Path("/opt/etc/init.d/S97xray").exists():
        raise RuntimeError("production/Entware detected: disposable lab only")
    v = subprocess.run([xray, "version"], text=True, capture_output=True, check=True, timeout=20)
    assert "26.2.6" in v.stdout and "linux/mipsle" in v.stdout
    a, b, c = EchoBackend("A"), EchoBackend("B"), EchoBackend("C")
    for server in (a, b, c):
        server.start()
    process = None
    api_port, socks_port = free_port(), free_port()
    assert len({api_port, socks_port, a.port, b.port, c.port}) == 5
    with tempfile.TemporaryDirectory(prefix="xray-v30-pool-handover-") as temp:
        try:
            cfg = Path(temp) / "xray.json"
            cfg.write_text(json.dumps(config(api_port, socks_port, a.port, b.port, "leastPing")))
            subprocess.run([xray, "run", "-test", "-config", str(cfg)], check=True, timeout=25)
            process = subprocess.Popen([xray, "run", "-config", str(cfg)],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            wait_port(socks_port, process, timeout=25)
            wait_port(api_port, process, timeout=25)

            def api(*args):
                return subprocess.run([xray, "api", args[0], "-s", f"127.0.0.1:{api_port}", *args[1:]],
                                      capture_output=True, text=True, check=True, timeout=25)

            api("bo", "-b", "lab-balancer", "lab-a")
            coordinator = Coordinator(Generation(1, ("fp-a", "fp-b"), "fp-a"))
            with socks_connect(socks_port) as old:
                assert echo(old, b"old") == "A"
                # New subscription changes order/adds C but retains A.
                proposal = coordinator.prepare(("fp-c", "fp-a"))
                assert proposal.plan.keep_active and proposal.plan.action == "keep"
                added = Path(temp) / "added-c.json"
                added.write_text(json.dumps({"outbounds": [{
                    "tag": "lab-c", "protocol": "freedom",
                    "settings": {"redirect": f"127.0.0.1:{c.port}"}
                }]}))
                api("ado", str(added))
                # No BO is issued for a keep plan: explicit A remains sticky.
                state = coordinator.commit(proposal, validated=True, api_healthy=True,
                                           continuity_verified=True)
                assert state.active == "fp-a"
                with socks_connect(socks_port) as unchanged:
                    assert echo(unchanged, b"qualified-original") == "A"
                assert echo(old, b"still-a") == "A"
                print("POOL_API: PASS new qualified pool retains active A; no BO switch", flush=True)

                # A is later removed/disqualified. Old A TCP remains until drain.
                replacement = coordinator.prepare(("fp-c",))
                assert replacement.plan.action == "switch_new_flows" and replacement.plan.selected == "fp-c"
                api("bo", "-b", "lab-balancer", "lab-c")
                with socks_connect(socks_port) as fresh:
                    assert echo(fresh, b"now-c") == "C"
                assert echo(old, b"old-a-survives") == "A"
                coordinator.commit(replacement, validated=True, api_healthy=True,
                                   continuity_verified=True)
                print("POOL_API: PASS changed pool sends new TCP to C; old A TCP survives", flush=True)

                # Synthetic C health gate fails AFTER promotion: use explicit
                # rollback to the known-good, still-running A. Do not remove A.
                api("bo", "-b", "lab-balancer", "lab-a")
                with socks_connect(socks_port) as rolled:
                    assert echo(rolled, b"rollback-a") == "A"
                assert echo(old, b"old-a-after-rollback") == "A"
                print("POOL_API: PASS explicit BO rollback restores new TCP to A", flush=True)
                print("POOL_API: NOT TESTED automatic leastPing, VLESS, UDP, TPROXY, router firewall", flush=True)
        finally:
            if process is not None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
            for server in (a, b, c):
                server.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--xray", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        parser.error("explicit --run required")
    run(args.xray)
