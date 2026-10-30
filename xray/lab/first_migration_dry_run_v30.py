"""Read-only, offline dry-run planner for FIRST Xray API migration.

This program never executes shell commands, connects to the router, or changes
files outside the caller-selected output. Input is a synthetic inventory JSON.
The output is an explicit, gated plan, not deployment authorization.
"""
import argparse
import json
from pathlib import Path


class GateError(ValueError):
    pass


REQUIRED = ("config_sha256", "xray_binary_sha256", "pid", "start_ticks",
            "socks_listener", "tproxy_listener", "watchdog_mode",
            "kill_switch", "tproxy_chain", "route_table_100",
            "candidate_test", "candidate_api", "rollback_artifact",
            "outbound_direct_count", "outbound_block_count",
            "subscription_staging_only", "ingress_handoff_proven")


def evaluate(data):
    missing = [key for key in REQUIRED if key not in data]
    if missing:
        raise GateError("missing inventory fields: " + ", ".join(missing))
    failures = []
    for key in ("config_sha256", "xray_binary_sha256"):
        value = data[key]
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            failures.append(key + ": invalid SHA256")
    if not isinstance(data["pid"], int) or data["pid"] <= 1:
        failures.append("invalid PID")
    if not isinstance(data["start_ticks"], int) or data["start_ticks"] <= 0:
        failures.append("missing process start ticks")
    checks = {
        "socks_listener": "127.0.0.1:10808",
        "tproxy_listener": "0.0.0.0:12345",
        "watchdog_mode": "legacy-killall",
    }
    for key, expected in checks.items():
        if data[key] != expected:
            failures.append(f"{key}: expected {expected}")
    for key in ("kill_switch", "tproxy_chain", "route_table_100",
                "candidate_test", "candidate_api", "rollback_artifact",
                "subscription_staging_only"):
        if data[key] is not True:
            failures.append(key + ": gate not satisfied")
    if data["outbound_direct_count"] != 0:
        failures.append("direct/freedom fallback present")
    if not isinstance(data["outbound_block_count"], int) or data["outbound_block_count"] < 1:
        failures.append("no blackhole outbound")
    # Crucial: no zero-downtime first cutover can be claimed from current topology.
    if data["ingress_handoff_proven"] is not True:
        failures.append("unproven exclusive SOCKS/TPROXY handoff: first cutover NOT authorized")
    return {
        "decision": "NOT_AUTHORIZED" if failures else "PRECHECKS_ONLY_NO_DEPLOY",
        "failures": failures,
        "outage_estimate": {
            "minimum": "not established",
            "expected": "short TCP/UDP disruption possible on first restart",
            "maximum": "unbounded until listener/API and routing checks pass or rollback completes",
            "guarantee": "no zero-downtime guarantee",
        },
        "required_manual_approval": True,
        "production_commands": [],
        "phases": [
            "snapshot live process/config hashes and redacted listener/route/iptables inventory",
            "stage API-enabled candidate on distinct localhost ports and validate via run -test",
            "fence legacy watchdog safely and establish PID-specific recovery ownership",
            "recheck generation CAS, process start ticks, SHA256 and kill-switch immediately before cutover",
            "perform approved ingress handoff; do NOT call legacy S97xray restart or killall",
            "probe SOCKS5, TPROXY TCP/UDP, OpenAI via selected VPN, DNS and IPv6 leak paths",
            "if verification fails, execute independently approved, pre-tested rollback",
            "restore watchdog supervision; record final generation, health and journal",
        ],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--inventory", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.inventory.resolve() == args.output.resolve():
        p.error("output must not overwrite inventory")
    data = json.loads(args.inventory.read_text(encoding="utf-8"))
    result = evaluate(data)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(result["decision"])
    return 0 if not result["failures"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
