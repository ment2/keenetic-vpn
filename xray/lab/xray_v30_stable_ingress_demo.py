#!/usr/bin/env python3
"""Real MIPS32LE QEMU dual Xray lab behind one fixed loopback SOCKS TCP port.

NOT TPROXY, UDP, production ingress, kernel leak protection or watchdog proof.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

from xray.lab.stable_socks_ingress_v30 import Backend, StableSocksTcpIngress, proc_start_ticks
from xray.lab.xray_v30_api_continuity import EchoBackend, echo, free_port, socks_connect, wait_port
from xray.lab.xray_v30_dual_process import config


def run(xray):
    if Path("/opt/etc/xray/config.json").exists() or Path("/opt/etc/init.d/S97xray").exists():
        raise RuntimeError("CI runner only; production detected")
    v = subprocess.run([xray, "version"], capture_output=True, text=True, check=True, timeout=20)
    assert "26.2.6" in v.stdout and "linux/mipsle" in v.stdout
    lab = EchoBackend("LAB")
    lab.start()
    processes = []
    ingress = None
    with tempfile.TemporaryDirectory(prefix="xray-v30-stable-ingress-") as td:
        try:
            ports = [free_port(), free_port()]
            assert len(set([*ports, lab.port])) == 3
            for name, port in zip(("old", "candidate"), ports):
                cfg = Path(td) / f"{name}.json"
                cfg.write_text(json.dumps(config(port, lab.port)))  # UDP disabled
                subprocess.run([xray, "run", "-test", "-config", str(cfg)],
                               check=True, timeout=25, stdout=subprocess.DEVNULL)
                p = subprocess.Popen([xray, "run", "-config", str(cfg)],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                processes.append(p)
                wait_port(port, p, timeout=25)
            old, candidate = [Backend(port, p.pid, proc_start_ticks(p.pid))
                              for port, p in zip(ports, processes)]
            ingress = StableSocksTcpIngress(old, candidate).start()
            stable = ingress.port
            with socks_connect(stable) as original:
                assert echo(original, b"old") == "LAB"
                assert ingress.activate(1, old, candidate, candidate_ready=True) == 2
                with socks_connect(stable) as fresh:
                    assert echo(fresh, b"new") == "LAB"
                assert echo(original, b"old-survived") == "LAB"
                assert stable == ingress.port
                print("STABLE_INGRESS: PASS old TCP survives real Xray selector cutover", flush=True)

                processes[1].terminate()
                processes[1].wait(timeout=10)
                failed_closed = False
                try:
                    with socks_connect(stable):
                        pass
                except (OSError, AssertionError):
                    failed_closed = True
                assert failed_closed, "dead candidate unexpectedly served SOCKS"
                print("STABLE_INGRESS: PASS new TCP fails closed after candidate crash", flush=True)

                assert ingress.rollback(2, old, candidate) == "old"
                with socks_connect(stable) as restored:
                    assert echo(restored, b"rollback") == "LAB"
                assert echo(original, b"old-survived-rollback") == "LAB"
                assert stable == ingress.port
                print("STABLE_INGRESS: PASS old restored on SAME TCP ingress port", flush=True)
            print("STABLE_INGRESS: PASS PID/start-ticks and generation gates", flush=True)
            print("STABLE_INGRESS: NOT VERIFIED TPROXY, UDP, DNS, watchdog, kernel fail-closed", flush=True)
        finally:
            if ingress is not None:
                ingress.close()
            for p in processes:
                if p.poll() is None:
                    p.terminate()
                    try:
                        p.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        p.kill()
                        p.wait(timeout=10)
            lab.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--xray", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        parser.error("explicit --run required")
    run(args.xray)
